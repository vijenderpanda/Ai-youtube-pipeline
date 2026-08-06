#!/usr/bin/env python3
"""
probe_frames.py — measure what is ACTUALLY on the shipped frames, so overlay
placement and camera zoom are decisions instead of intuition.

Two recurring playbook rules both come down to the same missing measurement:

  §4  "the step chip must NEVER cover the content the beat is teaching" — and
      a corner chosen from a proxy clip is not a decision (Ep11, Ep23, Ep24).
  §10c "measure the ink, then set the zoom caps — don't trust the defaults":
      a mobile chat answer runs edge to edge, so a fixed 1.08 push slices the
      outermost characters (Ep24).

Both were done by hand, per episode, and Ep24 proved that hand-fitting against
a stand-in clip gets the answer wrong. This does them off the real file.

  # widest safe punch zoom + center for a window of a recording
  python3 scripts/probe_frames.py ink CLIP.mp4 --window 38.2 45.1

  # which corner a step chip can live in during a beat (lower score = emptier)
  python3 scripts/probe_frames.py corner CLIP.mp4 --window 20.0 24.0 \
      --label "STEP 1/3 — THE FIX"

Scores are the fraction of chip-rect pixels carrying ink. 0.00 = the corner is
empty for the whole window, which is the only score that fully satisfies the
rule; anything above ~0.01 means the chip would sit on something.
"""
import argparse, json, shutil, subprocess, sys

import numpy as np

FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
W, H = 1080, 1920

# StepChip geometry, mirrored from remotion-studio/src/Short.tsx: 40px inset,
# top:170 / bottom:560, fontSize 40 Anton + 10px/26px padding + 4px border.
CHIP_INSET, CHIP_TOP, CHIP_BOTTOM, CHIP_H = 40, 170, 560, 76
CHIP_CHAR_W = 17.5          # measured average Anton advance at 40px
CHIP_PAD_W = 60


def frames(path, t0, t1, fps=2):
    """Decode [t0, t1) at `fps` as 1080x1920 grayscale arrays."""
    cmd = [FFMPEG, "-v", "error", "-ss", str(t0), "-t", str(max(0.05, t1 - t0)),
           "-i", path, "-vf", f"fps={fps},scale={W}:{H}:flags=bilinear,format=gray",
           "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    n = len(raw) // (W * H)
    if not n:
        sys.exit(f"no frames decoded from {path} in [{t0}, {t1}]")
    return np.frombuffer(raw[:n * W * H], np.uint8).reshape(n, H, W)


def ink_mask(fr, thresh=34):
    """Boolean mask of pixels that differ from the frame's background level.

    Works for either polarity (dark UI with light text, or the reverse): the
    background is the modal level, ink is whatever sits far from it.
    """
    bg = np.median(fr)
    return np.abs(fr.astype(np.int16) - int(bg)) > thresh


def cmd_ink(a):
    fr = frames(a.clip, a.window[0], a.window[1], a.fps)
    # --region restricts the measurement to the pixels that MUST survive the
    # crop. Persistent app chrome (a nav pill at x=24, a footer disclaimer)
    # otherwise pins the ink span to the full frame and reports zoom_cap 1.00
    # for every window — technically true, useless as a camera. Ep24 made the
    # same call by hand when it sacrificed the composer's far-left "+" icon.
    rx0, ry0, rx1, ry1 = a.region
    cx0, cy0 = int(rx0 * W), int(ry0 * H)
    cx1, cy1 = int(rx1 * W), int(ry1 * H)
    cols = np.zeros(W, bool)
    rows = np.zeros(H, bool)
    for f in fr:
        m = np.zeros((H, W), bool)
        m[cy0:cy1, cx0:cx1] = ink_mask(f[cy0:cy1, cx0:cx1], a.thresh)
        cols |= m.sum(axis=0) > a.min_px
        rows |= m.sum(axis=1) > a.min_px
    if not cols.any():
        sys.exit("no ink found — check --thresh / the window")
    x0, x1 = np.argmax(cols) / W, (W - np.argmax(cols[::-1])) / W
    y0, y1 = np.argmax(rows) / H, (H - np.argmax(rows[::-1])) / H
    # a centred crop at zoom z shows 1/z of each axis, so the widest zoom that
    # still contains the ink is 1/span (98% of it, for a margin)
    cap = min(1.0 / max(1e-3, x1 - x0), 1.0 / max(1e-3, y1 - y0)) * 0.98
    out = {"frames": len(fr), "window": a.window,
           "ink": [round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4)],
           "center": [round((x0 + x1) / 2, 3), round((y0 + y1) / 2, 3)],
           "zoom_cap": round(cap, 3),
           "edge_margin_px": [int(x0 * W), int(W - x1 * W)]}
    print(json.dumps(out, indent=2))
    return out


def cmd_corner(a):
    label = a.label or ""
    cw = int(len(label) * CHIP_CHAR_W + CHIP_PAD_W) if label else a.chip_w
    rects = {
        "tl": (CHIP_INSET, CHIP_TOP, CHIP_INSET + cw, CHIP_TOP + CHIP_H),
        "tr": (W - CHIP_INSET - cw, CHIP_TOP, W - CHIP_INSET, CHIP_TOP + CHIP_H),
        "bl": (CHIP_INSET, H - CHIP_BOTTOM - CHIP_H, CHIP_INSET + cw, H - CHIP_BOTTOM),
        "br": (W - CHIP_INSET - cw, H - CHIP_BOTTOM - CHIP_H, W - CHIP_INSET, H - CHIP_BOTTOM),
    }
    fr = frames(a.clip, a.window[0], a.window[1], a.fps)
    scores = {}
    for k, (x0, y0, x1, y1) in rects.items():
        worst = 0.0
        for f in fr:
            m = ink_mask(f[y0:y1, max(0, x0):x1], a.thresh)
            worst = max(worst, float(m.mean()))
        scores[k] = round(worst, 4)
    best = min(scores, key=scores.get)
    print(json.dumps({"window": a.window, "chip_w": cw, "frames": len(fr),
                      "scores": scores, "best": best,
                      "clean": [k for k, v in scores.items() if v <= 0.005]},
                     indent=2))
    return scores


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    for name in ("ink", "corner"):
        p = sub.add_parser(name)
        p.add_argument("clip")
        p.add_argument("--window", nargs=2, type=float, required=True,
                       metavar=("T0", "T1"))
        p.add_argument("--fps", type=float, default=2.0)
        p.add_argument("--thresh", type=int, default=34)
        if name == "ink":
            p.add_argument("--min-px", type=int, default=3,
                           help="pixels per column/row before it counts as ink")
            p.add_argument("--region", nargs=4, type=float,
                           default=[0.0, 0.0, 1.0, 1.0],
                           metavar=("X0", "Y0", "X1", "Y1"),
                           help="normalized box the ink must survive inside "
                                "(default whole frame)")
        else:
            p.add_argument("--label", help="chip text (sets the probed width)")
            p.add_argument("--chip-w", type=int, default=520)
    a = ap.parse_args()
    (cmd_ink if a.mode == "ink" else cmd_corner)(a)


if __name__ == "__main__":
    main()
