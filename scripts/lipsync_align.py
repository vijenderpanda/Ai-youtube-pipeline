#!/usr/bin/env python3
"""
lipsync_align.py — measure (and fix) the offset between a lip-synced host clip
and the episode's master VO, off the audio itself.

WHY THIS EXISTS (AI Unpacked Ep25 v4, 2026-08-05). A HeyGen render is driven by
an audio slice, and it comes back with that audio NOT at t=0: the render adds a
lead (measured 123 ms on the line-2 clip, 234 ms on the lines-7/8 clip of the
same episode — it is per-render, not a constant). The assembler then places the
clip at the VO line boundary with in-point 0.00, which puts the host's MOUTH
that many milliseconds behind the voice. Nothing in the pipeline noticed:
the clip's own audio is muted in the render, its duration looks right, and the
poster frames look right. Ep25 v2 and v3 both shipped the payoff beat 234 ms out
of sync this way.

234 ms is not subtle. Audio-ahead-of-video is the direction the eye catches
first (detection threshold is ~45 ms that way vs ~125 ms the other), so this is
the single cheapest lip-sync defect a Pipeline-B episode can have.

MEASURE, never eyeball: cross-correlate the clip's audio envelope against the
master VO from the beat's in-point. A real answer has a sharp peak (corr > ~0.9)
and agrees with every silence boundary in both files to a few ms; a flat or
ambiguous peak means the render is not a straight time-shift of the slice and no
in-point can fix it (re-render, or leave it and say so).

  # what is the offset?
  python3 scripts/lipsync_align.py measure \
      channels/claude-tricks/assets/ep25/host_payoff.mp4 \
      channels/claude-tricks/assets/ep25/vo_v2.wav --at 21.711

  # cut a sync-corrected, tail-padded copy the spec can point at with @0.00
  python3 scripts/lipsync_align.py cut \
      channels/claude-tricks/assets/ep25/host_payoff.mp4 \
      --lag 0.234 --dur 6.153 \
      --out channels/claude-tricks/assets/ep25/host_payoff_sync.mp4

`cut` clone-holds the clip's last frame if the shift runs past its end (a
lead eats exactly that much off the tail). Check that the hold lands in a SILENT
stretch of the VO with the mouth already closed — a frozen mouth under a spoken
word is a worse artifact than the offset you were fixing.
"""
import argparse, shutil, subprocess, sys

import numpy as np

FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
SR = 16000


def pcm(args):
    cmd = [FFMPEG, "-v", "error"] + args + ["-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.float32)


def envelope(x, win=160):
    return np.convolve(np.abs(x), np.ones(win) / win, "same")


def measure(clip, vo, at, search=0.7):
    a = envelope(pcm(["-i", clip]))
    b = envelope(pcm(["-ss", str(at), "-t", str(len(a) / SR + 0.4), "-i", vo]))
    n = min(len(a), len(b))
    if n < SR // 2:
        sys.exit("not enough audio to correlate")
    a, b = a[:n], b[:n]
    a = (a - a.mean()) / (a.std() + 1e-9)
    b = (b - b.mean()) / (b.std() + 1e-9)
    cc = np.correlate(a, b, "full") / n
    mid = len(b) - 1
    R = int(search * SR)
    lags = range(-R, R)
    best = max(lags, key=lambda L: cc[mid + L])
    return best / SR, float(cc[mid + best])


def cut(clip, lag, dur, out, fps=30, pad=1.0):
    """Trim `clip` from `lag` for `dur`, clone-holding the last frame if needed."""
    vf = (f"fps={fps},setsar=1,tpad=stop_mode=clone:stop_duration={pad},"
          f"trim=start={lag}:end={lag + dur},setpts=PTS-STARTPTS,format=yuv420p")
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-i", clip, "-vf", vf, "-an",
           "-r", str(fps), "-frames:v", str(int(round(dur * fps))),
           "-c:v", "libx264", "-crf", "17", "-preset", "slow",
           "-pix_fmt", "yuv420p", out]
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)
    print(f">> SYNC CUT lag={lag}s dur={dur}s", out)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    m = sub.add_parser("measure"); m.add_argument("clip"); m.add_argument("vo")
    m.add_argument("--at", type=float, required=True,
                   help="VO time the beat starts at (the line boundary)")
    c = sub.add_parser("cut"); c.add_argument("clip")
    c.add_argument("--lag", type=float, required=True)
    c.add_argument("--dur", type=float, required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--fps", type=int, default=30)
    a = ap.parse_args()
    if a.mode == "measure":
        lag, corr = measure(a.clip, a.vo, a.at)
        print(f"lag = {lag * 1000:+.1f} ms (positive = clip audio/lips LATER "
              f"than the VO)   corr = {corr:.4f}")
        if corr < 0.85:
            print("!! weak peak — this render may not be a pure time-shift of "
                  "the driver slice; do NOT trust a single in-point fix")
    else:
        cut(a.clip, a.lag, a.dur, a.out, a.fps)
