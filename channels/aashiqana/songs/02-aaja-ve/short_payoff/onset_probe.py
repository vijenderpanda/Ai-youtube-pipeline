#!/usr/bin/env python3
"""20ms-RMS onset probe on the demucs vocal stem.

Step 3 of the hook-bar decision: a 2s volumedetect window can win on dB and still
be wrong. A true chant attack sits on a visible step in the 20ms RMS envelope
(roughly -29 dB -> -19 dB inside one or two frames). If there is no step the
timing-prior number is fiction and we re-scan finely around it.
"""
import os, subprocess, sys
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
VOX = os.path.join(ROOT, "..", "track", "demucs", "htdemucs", "aaja_ve_final", "vocals.wav")
MIX = os.path.join(ROOT, "..", "track", "aaja_ve_final.mp3")
SR = 48000
FRAME = 0.020  # 20 ms


def pcm(src, ss, dur):
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{ss:.3f}", "-t", f"{dur:.3f}", "-i", src,
                        "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True)
    return np.frombuffer(p.stdout, dtype="<f4")


def envelope(src, ss, dur):
    x = pcm(src, ss, dur)
    n = int(SR * FRAME)
    k = len(x) // n
    f = x[:k * n].reshape(k, n)
    rms = np.sqrt((f.astype(np.float64) ** 2).mean(axis=1))
    db = 20 * np.log10(np.maximum(rms, 1e-9))
    t = ss + np.arange(k) * FRAME
    return t, db


def report(label, prior, pre=1.2, post=1.2):
    t, db = envelope(VOX, prior - pre, pre + post)
    print(f"\n=== {label}: vocal-stem 20ms RMS envelope around prior {prior:.2f}s ===")
    for tt, d in zip(t, db):
        mark = "  <-- prior" if abs(tt - prior) < FRAME / 2 else ""
        bar = "#" * max(0, int((d + 60) / 1.5))
        print(f"{tt:8.3f}  {d:7.2f} dB {bar}{mark}")
    # largest positive step over a 2-frame (40ms) span, searched around the prior
    best = None
    for i in range(2, len(db) - 1):
        step = db[i] - db[i - 2]
        if db[i] > -22.0 and (best is None or step > best[0]):
            best = (step, t[i], db[i - 2], db[i])
    if best:
        print(f"  strongest 40ms step: +{best[0]:.2f} dB at t={best[1]:.3f}s "
              f"({best[2]:.2f} -> {best[3]:.2f} dB)")
    return t, db


def find_onset(prior, search=0.9, floor=-29.0, rise_to=-19.0):
    """Fine 0.1s-resolution onset: first 20ms frame after which the envelope
    climbs from <=floor to >=rise_to within 2 frames and stays hot."""
    t, db = envelope(VOX, prior - search, 2 * search)
    for i in range(len(db) - 4):
        if db[i] <= floor and db[i + 2] >= rise_to and db[i + 3] >= rise_to - 3:
            return t[i], db[i], db[i + 2], db[i + 2] - db[i]
    # relaxed: biggest 40ms rise that ends hot
    cand = [(db[i + 2] - db[i], t[i], db[i], db[i + 2])
            for i in range(len(db) - 3) if db[i + 2] >= rise_to]
    if cand:
        s, tt, a, b = max(cand)
        return tt, a, b, s
    return None


if __name__ == "__main__":
    for name, prior in (("C1 chorus-3 (default)", 151.88), ("C2 chorus-2 (fallback)", 68.20)):
        report(name, prior)
        o = find_onset(prior)
        print(f"  -> detected onset {o[0]:.3f}s  ({o[1]:.2f} -> {o[2]:.2f} dB, step +{o[3]:.2f} dB)"
              if o else "  -> NO STEP FOUND")
