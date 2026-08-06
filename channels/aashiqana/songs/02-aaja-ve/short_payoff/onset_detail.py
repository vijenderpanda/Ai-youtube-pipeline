#!/usr/bin/env python3
"""Frame-level onset forensics on the demucs vocal stem.

RMS alone cannot tell a voiced 'Aa-' attack from (a) a reverb tail of the
previous line or (b) an inhale/breath before the chant. So per 20ms frame we
also compute:
  voiced_ratio = E(80-1000 Hz) / E(2k-8k Hz)   -- high => voiced vowel,
                                                  low  => breath / noise
  flux         = positive spectral flux        -- attack transient
A true chant attack = RMS step out of the floor WITH voiced_ratio going high.
"""
import os, subprocess, sys
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
VOX = os.path.join(ROOT, "..", "track", "demucs", "htdemucs", "aaja_ve_final", "vocals.wav")
SR = 48000
N = 960  # 20 ms


def pcm(src, ss, dur):
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{ss:.3f}", "-t", f"{dur:.3f}", "-i", src,
                        "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True)
    return np.frombuffer(p.stdout, dtype="<f4").astype(np.float64)


def frames(ss, dur):
    x = pcm(VOX, ss, dur)
    k = len(x) // N
    f = x[:k * N].reshape(k, N)
    t = ss + np.arange(k) * (N / SR)
    rms = np.sqrt((f ** 2).mean(axis=1))
    db = 20 * np.log10(np.maximum(rms, 1e-9))
    w = np.hanning(N)
    S = np.abs(np.fft.rfft(f * w, axis=1))
    freq = np.fft.rfftfreq(N, 1 / SR)
    lo = S[:, (freq >= 80) & (freq < 1000)].sum(axis=1)
    hi = S[:, (freq >= 2000) & (freq < 8000)].sum(axis=1)
    vr = 20 * np.log10(np.maximum(lo, 1e-9) / np.maximum(hi, 1e-9))
    flux = np.concatenate([[0.0], np.maximum(np.diff(S, axis=0), 0).sum(axis=1)])
    return t, db, vr, flux


def onset(prior, back=2.0, fwd=1.5, floor_db=-26.0, hot_db=-19.0, voiced_db=6.0):
    """First frame where the stem steps out of a real floor into hot+voiced audio."""
    t, db, vr, fx = frames(prior - back, back + fwd)
    for i in range(2, len(db) - 4):
        quiet_before = db[i - 2:i].max() <= floor_db
        hot_after = db[i + 1:i + 4].min() >= hot_db - 4 and db[i + 1:i + 4].max() >= hot_db
        voiced = vr[i + 1:i + 4].max() >= voiced_db
        if quiet_before and hot_after and voiced:
            return dict(t=round(float(t[i]), 3), pre_db=round(float(db[i - 1]), 2),
                        post_db=round(float(db[i + 2]), 2),
                        step_db=round(float(db[i + 2] - db[i - 1]), 2),
                        voiced_ratio_db=round(float(vr[i + 2]), 2))
    return None


def dump(label, a, b):
    t, db, vr, fx = frames(a, b - a)
    print(f"\n--- {label}  [{a:.2f},{b:.2f}] : t / rms_dB / voiced_ratio_dB (+ = voiced) ---")
    for tt, d, v, f in zip(t, db, vr, fx):
        tag = "VOICED" if v >= 6 else ("breath?" if d > -26 else "")
        print(f"{tt:8.3f} {d:7.2f} {v:7.2f} {tag}")


if __name__ == "__main__":
    CH = [4.08, 16.10, 38.94, 68.20, 79.10, 100.92, 151.88, 163.80, 184.68]
    print("=== detected voiced onsets vs timing_karaoke priors (all chorus lines) ===")
    for p in CH:
        o = onset(p)
        if o:
            print(f"prior {p:7.2f} -> onset {o['t']:7.3f}  ({o['t']-p:+.3f}s)  "
                  f"{o['pre_db']:6.2f} -> {o['post_db']:6.2f} dB  step +{o['step_db']:.2f}  "
                  f"voiced {o['voiced_ratio_db']:+.1f} dB")
        else:
            print(f"prior {p:7.2f} -> NO CLEAN ONSET (no floor->hot voiced step in window)")
    if len(sys.argv) > 2:
        dump("zoom", float(sys.argv[1]), float(sys.argv[2]))
