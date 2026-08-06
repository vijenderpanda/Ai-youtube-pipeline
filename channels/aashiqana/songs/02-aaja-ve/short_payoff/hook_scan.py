#!/usr/bin/env python3
"""Objective hook-bar picker for Aaja Ve — method copied from the Aug-5 Baarish cut
(channels/aashiqana/songs/01-baarish-aur-tum/short_hook/hook_scan.py).

volumedetect over sliding 2s windows of the mix AND of the demucs vocal stem,
then score each aligned lyric line by the loudest 2s window inside it.
Threaded only for wall-clock; the ffmpeg invocation is identical to the reference.
"""
import json, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
SONG = os.path.join(ROOT, "..", "track", "aaja_ve_final.mp3")
VOX = os.path.join(ROOT, "..", "track", "demucs", "htdemucs", "aaja_ve_final", "vocals.wav")
TIMING = os.path.join(ROOT, "..", "lyrics", "timing_karaoke.json")
WIN, HOP, DUR = 2.0, 0.5, 213.92


def vol(src, ss, t):
    p = subprocess.run(["ffmpeg", "-v", "info", "-ss", f"{ss:.2f}", "-t", f"{t:.2f}", "-i", src,
                        "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"mean_volume: (-?[\d.]+) dB", p.stderr)
    x = re.search(r"max_volume: (-?[\d.]+) dB", p.stderr)
    return (float(m.group(1)) if m else -99.0, float(x.group(1)) if x else -99.0)


def scan(src, tag):
    ts = []
    t = 0.0
    while t + WIN <= DUR:
        ts.append(round(t, 2))
        t += HOP
    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(lambda tt: vol(src, tt, WIN), ts))
    grid = [{"t": tt, "mean": r[0], "max": r[1]} for tt, r in zip(ts, res)]
    json.dump(grid, open(os.path.join(ROOT, f"grid_{tag}.json"), "w"), indent=0)

    lines = json.load(open(TIMING))["lines"]
    rows = []
    for i, ln in enumerate(lines):
        s, e = ln["s"], ln["e"]
        inside = [g for g in grid if g["t"] >= s - 0.25 and g["t"] + WIN <= e + 0.5]
        if not inside:
            inside = [g for g in grid if abs(g["t"] - s) < 1.0]
        best = max(inside, key=lambda g: g["mean"])
        rows.append({"i": i, "s": s, "e": e, "text": ln["text"],
                     "best_t": best["t"], "mean": best["mean"], "max": best["max"]})
    json.dump(rows, open(os.path.join(ROOT, f"lines_{tag}.json"), "w"), indent=1)

    print(f"\n=== {tag} : lyric lines ranked by loudest 2s window ===")
    for r in sorted(rows, key=lambda r: -r["mean"]):
        print(f"{r['mean']:7.2f} dB mean | {r['max']:6.2f} peak | win@{r['best_t']:6.1f}s | "
              f"line[{r['i']:2d}] {r['s']:6.2f}-{r['e']:6.2f} | {r['text']}")
    print(f"\n=== {tag} : top 12 global 2s windows ===")
    for g in sorted(grid, key=lambda g: -g["mean"])[:12]:
        print(f"{g['mean']:7.2f} dB @ {g['t']:6.1f}s (peak {g['max']:.2f})")
    return grid, rows


if __name__ == "__main__":
    scan(SONG, "mix")
    scan(VOX, "vocals")
