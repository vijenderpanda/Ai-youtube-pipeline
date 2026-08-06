#!/usr/bin/env python3
"""song_energy.py — rank a channel's songs by how ANIMATED they are, objectively.

Built for the Lulla 1-hour compilation (Playbook §11/§13: the long-form binder),
where the running order is the whole product: a sleep aid has to start at the
most awake song and end at the sleepiest, and "which of these six is liveliest"
is not a thing to decide by memory of a mix you heard days ago.

No librosa on this machine, so the three measures are computed from scratch on a
mono 22.05kHz downmix (numpy + soundfile, both already present):

  tempo_bpm      autocorrelation peak of the spectral-flux onset envelope,
                 searched over 40-160 BPM (a lullaby lives at the bottom of that)
  onset_rate     onsets/sec after adaptive-median peak picking — how BUSY the
                 arrangement is, which is not the same thing as how fast it is
                 (a 90 BPM song with a plucked ostinato out-fidgets a 110 BPM pad)
  centroid_hz    mean spectral centroid = brightness. Bright = awake; a song that
                 rolls off dark reads as further into the night.
  lra            loudness range via ffmpeg ebur128 — dynamic songs (big choruses)
                 pull a listener back up; flat ones let them sink.

`animation` is the mean of those four min-max normalised across the set — a
RELATIVE score, only meaningful within one call, which is exactly the question
being asked ("order THESE six"). Ties are broken by onset_rate, the measure that
most directly matches what a half-asleep listener notices.

Usage:
  python3 scripts/song_energy.py FILE [FILE ...] [--json out.json]

The order printed is the wind-down order: most animated first.
"""
import argparse
import json
import subprocess
import sys
import re
from pathlib import Path

import numpy as np

SR = 22050
N_FFT = 1024
HOP = 256


def decode_mono(path, sr=SR):
    """ffmpeg -> raw float32 mono at `sr`. Handles mp3/mp4/wav uniformly.

    `-vn` is not optional: these inputs are usually finished mp4 masters, and
    without it ffmpeg tries to put a video stream into an f32le container and
    dies with "Output file does not contain any stream".
    """
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr),
         "-f", "f32le", "-"],
        capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg decode failed for {path}: {p.stderr[:300]}")
    return np.frombuffer(p.stdout, dtype=np.float32).astype(np.float64)


def stft_mag(x, n_fft=N_FFT, hop=HOP):
    if len(x) < n_fft:
        raise RuntimeError("clip shorter than one FFT frame")
    win = np.hanning(n_fft)
    n_frames = 1 + (len(x) - n_fft) // hop
    # stride trick beats a python loop by ~50x on a 3-minute song
    idx = np.arange(n_fft)[None, :] + hop * np.arange(n_frames)[:, None]
    frames = x[idx] * win
    return np.abs(np.fft.rfft(frames, axis=1))


def onset_envelope(mag):
    """Spectral flux: sum of positive frame-to-frame magnitude increases."""
    flux = np.diff(mag, axis=0)
    flux = np.maximum(flux, 0.0).sum(axis=1)
    if flux.max() > 0:
        flux = flux / flux.max()
    return flux


def tempo_bpm(env, sr=SR, hop=HOP, lo=40, hi=160):
    """Autocorrelation of the onset envelope, restricted to a musical lag range."""
    e = env - env.mean()
    ac = np.correlate(e, e, mode="full")[len(e) - 1:]
    fps = sr / hop
    lag_lo = max(1, int(fps * 60.0 / hi))
    lag_hi = min(len(ac) - 1, int(fps * 60.0 / lo))
    if lag_hi <= lag_lo:
        return None
    seg = ac[lag_lo:lag_hi]
    return float(60.0 * fps / (lag_lo + int(np.argmax(seg))))


def onset_rate(env, sr=SR, hop=HOP):
    """Adaptive-median peak picking — count real attacks per second.

    A fixed threshold miscounts across songs mastered at different levels; the
    local median is what makes this comparable between tracks.
    """
    if len(env) < 32:
        return 0.0
    w = 31
    pad = np.pad(env, (w // 2, w // 2), mode="edge")
    med = np.array([np.median(pad[i:i + w]) for i in range(len(env))])
    thresh = med + 0.06
    peaks = 0
    i = 1
    min_gap = int((sr / hop) * 0.10)          # 100ms refractory
    last = -min_gap
    while i < len(env) - 1:
        if env[i] > thresh[i] and env[i] >= env[i - 1] and env[i] > env[i + 1] \
                and (i - last) >= min_gap:
            peaks += 1
            last = i
        i += 1
    dur = len(env) * hop / sr
    return float(peaks / dur) if dur else 0.0


def spectral_centroid(mag, sr=SR, n_fft=N_FFT):
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    energy = mag.sum(axis=1)
    live = energy > (energy.max() * 0.02)     # ignore silence/fade frames
    if not live.any():
        return None
    m = mag[live]
    return float(((m * freqs).sum(axis=1) / np.maximum(m.sum(axis=1), 1e-9)).mean())


def ebur128(path):
    """Integrated loudness + loudness range, straight from ffmpeg."""
    p = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(path), "-af", "ebur128=peak=true",
         "-f", "null", "-"], capture_output=True, text=True)
    err = p.stderr
    out = {}
    for key, pat in (("lufs_i", r"I:\s*(-?[\d.]+) LUFS"),
                     ("lra", r"LRA:\s*(-?[\d.]+) LU"),
                     ("peak_db", r"Peak:\s*(-?[\d.]+) dBFS")):
        m = re.findall(pat, err)
        if m:
            out[key] = float(m[-1])
    return out


def norm(vals):
    """Min-max to 0..1; a flat set becomes all-0.5 rather than a divide-by-zero."""
    v = np.array([x if x is not None else np.nan for x in vals], dtype=float)
    if np.all(np.isnan(v)):
        return [0.5] * len(vals)
    lo, hi = np.nanmin(v), np.nanmax(v)
    if hi - lo < 1e-9:
        return [0.5] * len(vals)
    out = (v - lo) / (hi - lo)
    return [0.5 if np.isnan(x) else float(x) for x in out]


def analyse(path):
    x = decode_mono(path)
    mag = stft_mag(x)
    env = onset_envelope(mag)
    row = {
        "file": str(path),
        "name": Path(path).name,
        "duration_s": round(len(x) / SR, 2),
        "tempo_bpm": tempo_bpm(env),
        "onset_rate": onset_rate(env),
        "centroid_hz": spectral_centroid(mag),
    }
    row.update(ebur128(path))
    for k in ("tempo_bpm", "onset_rate", "centroid_hz"):
        if row.get(k) is not None:
            row[k] = round(row[k], 2)
    return row


def main():
    ap = argparse.ArgumentParser(description="Rank songs most-animated-first (wind-down order).")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json", help="write the full table here")
    args = ap.parse_args()

    rows = []
    for f in args.files:
        if not Path(f).is_file():
            sys.exit(f"!! not a file: {f}")
        print(f".. analysing {Path(f).name}", flush=True)
        rows.append(analyse(f))

    n_tempo = norm([r.get("tempo_bpm") for r in rows])
    n_onset = norm([r.get("onset_rate") for r in rows])
    n_cent = norm([r.get("centroid_hz") for r in rows])
    n_lra = norm([r.get("lra") for r in rows])
    for i, r in enumerate(rows):
        r["animation"] = round(float(np.mean([n_tempo[i], n_onset[i], n_cent[i], n_lra[i]])), 3)

    rows.sort(key=lambda r: (-r["animation"], -(r.get("onset_rate") or 0)))

    print()
    print(f"  {'#':<3}{'song':<32}{'BPM':>7}{'onset/s':>9}{'centroid':>10}"
          f"{'LRA':>7}{'LUFS':>8}{'animation':>11}")
    for i, r in enumerate(rows, 1):
        print(f"  {i:<3}{r['name']:<32}{_f(r.get('tempo_bpm')):>7}{_f(r.get('onset_rate')):>9}"
              f"{_f(r.get('centroid_hz'), 0):>10}{_f(r.get('lra')):>7}"
              f"{_f(r.get('lufs_i')):>8}{r['animation']:>11.3f}")
    print()
    print("  ^ wind-down order: play top-to-bottom, most animated first.")

    if args.json:
        Path(args.json).write_text(json.dumps(
            {"order": [r["name"] for r in rows], "rows": rows}, indent=2) + "\n")
        print(f".. wrote {args.json}")


def _f(v, nd=1):
    return "?" if v is None else f"{v:.{nd}f}"


if __name__ == "__main__":
    main()
