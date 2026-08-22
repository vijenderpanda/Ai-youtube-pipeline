#!/usr/bin/env python3
"""sfx_mix.py — synthesize the ep3 SFX kit and mix it onto a built master.

The manifest's film.sfx events carry @beatN+x anchors; beats resolve from the
MEASURED clock (the props file's segment durations), same rule as everything
else in the film pipeline. SFX ride ~9 dB under the -14 LUFS VO spine so they
punctuate without fighting the read.

Usage:
  python3 sfx_mix.py --manifest films/lpa.manifest.json \
      --props ../../renders_out/props_ep_lpa_draft.json \
      --video renders/ep_lpa_draft_outro.mp4 --out renders/ep_lpa_draft_sfx.mp4
"""
import argparse, json, subprocess, tempfile
from pathlib import Path
import numpy as np

SR = 48000

def env(n, a=0.004, r=0.12):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    if na: e[:na] = np.linspace(0, 1, na)
    if nr and nr < n: e[-nr:] = np.linspace(1, 0, nr)
    return e

def noise(n): return np.random.default_rng(7).standard_normal(n)

def lowpass(x, cut):
    f = np.fft.rfft(x); fr = np.fft.rfftfreq(len(x), 1 / SR)
    f[fr > cut] *= np.exp(-(fr[fr > cut] - cut) / (cut * 0.5))
    return np.fft.irfft(f, len(x))

def tone(freq, dur, decay=6.0):
    t = np.arange(int(dur * SR)) / SR
    return np.sin(2 * np.pi * freq * t) * np.exp(-t * decay)

def synth(name):
    if name == "knife_cut":
        n = int(0.22 * SR)
        wh = lowpass(noise(n), 2600) * env(n, 0.002, 0.16) * 0.5
        th = tone(95, 0.22, 14) * 0.9
        return wh + th
    if name == "digit_slam":
        return tone(52, 0.5, 5) * 1.0 + lowpass(noise(int(0.5 * SR)), 900) * env(int(0.5 * SR), 0.001, 0.4) * 0.25
    if name in ("tax_tick", "tax_tick_hard"):
        n = int(0.09 * SR)
        cl = lowpass(noise(n), 5200) * env(n, 0.001, 0.06) * 0.5 + tone(1050, 0.09, 30) * 0.4
        if name == "tax_tick_hard":
            low = tone(70, 0.2, 12) * 0.6
            out = np.zeros(max(len(cl), len(low)))
            out[:len(cl)] += cl * 1.25
            out[:len(low)] += low
            return out
        return cl
    if name == "whoosh_up":
        n = int(0.35 * SR)
        x = noise(n)
        sweep = np.interp(np.arange(n), [0, n], [500, 3800])
        f = np.fft.rfft(x); fr = np.fft.rfftfreq(n, 1 / SR)
        f[fr > 2200] *= 0.2
        x = np.fft.irfft(f, n) * env(n, 0.12, 0.1)
        return x * 0.45
    if name == "credit_chime":
        return (tone(523, 0.7, 4) + tone(659, 0.7, 4) * 0.8 + tone(784, 0.7, 4) * 0.6) * 0.4
    if name == "ring_close":
        n = int(0.6 * SR)
        wh = lowpass(noise(n), 3000) * env(n, 0.25, 0.2) * 0.3
        return wh + (tone(659, 0.6, 5) + tone(988, 0.6, 5) * 0.7) * 0.35
    return np.zeros(int(0.1 * SR))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--props", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--gain_db", type=float, default=-9.0)
    a = ap.parse_args()

    man = json.load(open(a.manifest))
    props = json.load(open(a.props))

    def find_segs(o):
        if isinstance(o, dict):
            if "segments" in o and isinstance(o["segments"], list):
                return o["segments"]
            for v in o.values():
                r = find_segs(v)
                if r is not None: return r
        if isinstance(o, list):
            for v in o:
                r = find_segs(v)
                if r is not None: return r
    segs = find_segs(props)
    starts = [0.0]
    for s in segs: starts.append(starts[-1] + s["dur"])
    total = starts[-1]

    def resolve(at):
        if isinstance(at, (int, float)): return float(at)
        if isinstance(at, str) and at.startswith("@beat"):
            head, _, off = at[5:].partition("+")
            return starts[int(head)] + (float(off) if off else 0.0)
        raise ValueError(at)

    # probe video duration (film + outro; sfx only lands inside the film)
    dur = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", a.video]).strip())
    mix = np.zeros(int(dur * SR) + SR)

    n_placed = 0
    for ev in man.get("film", {}).get("sfx", []):
        if "_note" in ev: continue
        t0 = resolve(ev["at"])
        if t0 >= total: continue
        w = synth(ev["name"])
        i = int(t0 * SR)
        if i >= len(mix): continue
        end = min(i + len(w), len(mix))
        mix[i:end] += w[: end - i]
        n_placed += 1
    peak = np.abs(mix).max() or 1.0
    mix = mix / peak * (10 ** (a.gain_db / 20))

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        import wave
        wv = wave.open(f.name, "w")
        wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(SR)
        wv.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
        wv.close()
        sfx_wav = f.name

    subprocess.run([
        "ffmpeg", "-nostdin", "-loglevel", "error", "-y",
        "-i", a.video, "-i", sfx_wav,
        "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:normalize=0[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        a.out], check=True)
    print(f">> SFX: {n_placed} events mixed at {a.gain_db} dB -> {a.out}")

if __name__ == "__main__":
    main()
