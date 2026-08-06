#!/usr/bin/env python3
"""Precise vocal onsets + tempo/beat grid, from the demucs stems (numpy only)."""
import numpy as np, soundfile as sf, sys, json

VOX="short_hook/demucs/htdemucs/song/vocals.wav"
INST="short_hook/demucs/htdemucs/song/no_vocals.wav"

def env(path, hop=256):
    x, sr = sf.read(path, dtype="float32")
    if x.ndim > 1: x = x.mean(1)
    n = len(x)//hop
    e = np.sqrt((x[:n*hop].reshape(n,hop)**2).mean(1) + 1e-12)
    return e, sr/hop, sr

def onset_near(e, fps, t, back=1.5, fwd=1.0):
    """first frame after t-back where energy crosses 12% of the local max, sustained 60ms"""
    a, b = int((t-back)*fps), int((t+fwd)*fps)
    seg = e[a:b]
    thr = 0.12*seg.max()
    sus = max(1, int(0.06*fps))
    for i in range(len(seg)-sus):
        if (seg[i:i+sus] > thr).all():
            return (a+i)/fps
    return t

def tempo(e, fps):
    d = np.diff(e, prepend=e[0]); d[d<0]=0
    d = (d - d.mean())/ (d.std()+1e-9)
    ac = np.correlate(d, d, "full")[len(d)-1:]
    lo, hi = int(60/180*fps), int(60/60*fps)   # 60..180 BPM
    lag = lo + int(np.argmax(ac[lo:hi]))
    return 60.0*fps/lag, ac, lag

ve, vfps, sr = env(VOX)
ie, ifps, _  = env(INST)
bpm, ac, lag = tempo(ie, ifps)
beat = 60.0/bpm
print(f"tempo estimate: {bpm:.2f} BPM  (beat {beat:.3f}s, bar4 {4*beat:.3f}s)")

for t in [float(x) for x in sys.argv[1:]] or [161.45, 114.02, 118.34, 123.60, 130.95, 173.14]:
    print(f"  aligned {t:7.2f}  ->  vocal onset {onset_near(ve, vfps, t):7.3f}")

# rough downbeat phase: strongest instrumental-onset comb over the grid
d = np.diff(ie, prepend=ie[0]); d[d<0]=0
best=None
for ph in np.arange(0, 4*beat, 0.02):
    idx=((np.arange(ph, 200, 4*beat))*ifps).astype(int); idx=idx[idx<len(d)]
    s=d[idx].sum()
    if best is None or s>best[1]: best=(ph,s)
print(f"downbeat phase ~{best[0]:.3f}s  (bars at {best[0]:.3f} + n*{4*beat:.3f})")
def snap(t):
    n=round((t-best[0])/(4*beat)); return best[0]+n*4*beat
for t in [168.30, 113.90, 135.0]:
    print(f"  splice cand {t:.2f} -> nearest bar {snap(t):.3f}")
