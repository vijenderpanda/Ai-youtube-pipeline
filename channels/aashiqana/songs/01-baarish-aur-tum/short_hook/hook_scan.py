#!/usr/bin/env python3
"""Objective hook-bar picker: volumedetect over sliding 2s windows of the mix,
then score each aligned lyric line by the loudest 2s window inside it."""
import json, re, subprocess, sys

SONG = "renders/song.mp3"
TIMING = "lyrics/timing_final.json"
WIN, HOP, DUR = 2.0, 0.5, 203.76

def vol(src, ss, t):
    p = subprocess.run(["ffmpeg","-v","info","-ss",f"{ss:.2f}","-t",f"{t:.2f}","-i",src,
                        "-af","volumedetect","-f","null","-"],capture_output=True,text=True)
    m = re.search(r"mean_volume: (-?[\d.]+) dB", p.stderr)
    x = re.search(r"max_volume: (-?[\d.]+) dB", p.stderr)
    return (float(m.group(1)) if m else -99.0, float(x.group(1)) if x else -99.0)

src = sys.argv[1] if len(sys.argv) > 1 else SONG
grid = []
t = 0.0
while t + WIN <= DUR:
    mean, mx = vol(src, t, WIN)
    grid.append({"t": round(t,2), "mean": mean, "max": mx})
    t += HOP
json.dump(grid, open(f"short_hook/grid_{'vocals' if 'vocal' in src else 'mix'}.json","w"), indent=0)

lines = json.load(open(TIMING))["lines"]
rows = []
for i, ln in enumerate(lines):
    s, e = ln["s"], ln["e"]
    inside = [g for g in grid if g["t"] >= s-0.25 and g["t"]+WIN <= e+0.5]
    if not inside: inside = [g for g in grid if abs(g["t"]-s) < 1.0]
    best = max(inside, key=lambda g: g["mean"])
    rows.append({"i":i,"s":s,"e":e,"text":ln["text"],
                 "best_t":best["t"],"mean":best["mean"],"max":best["max"]})
rows.sort(key=lambda r: -r["mean"])
print(f"=== {src} : lyric lines ranked by loudest 2s window ===")
for r in rows:
    print(f"{r['mean']:7.2f} dB mean | {r['max']:6.2f} peak | win@{r['best_t']:6.1f}s | line[{r['i']:2d}] {r['s']:6.2f}-{r['e']:6.2f} | {r['text']}")
json.dump(rows, open(f"short_hook/lines_{'vocals' if 'vocal' in src else 'mix'}.json","w"), indent=1)
print("\n=== top 12 global 2s windows ===")
for g in sorted(grid, key=lambda g:-g["mean"])[:12]:
    print(f"{g['mean']:7.2f} dB @ {g['t']:6.1f}s (peak {g['max']:.2f})")
