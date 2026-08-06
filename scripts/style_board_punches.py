#!/usr/bin/env python3
"""
style_board_punches.py — build the multi-punch sidecar for a board recording,
run scripts/style_punch.py, and sweep the styled output for edge clipping.

Why a helper instead of a hand-written JSON: every zoom here is derived from
the ink extents scripts/record_board_demo.py measured on the live page, and
the punch windows are derived from the recorder's own marks. A hand-picked
zoom is how a label gets cropped.

The zoom bound: the board's content column is x 84..520 of a 540px viewport
(= 168..1040 of the 1080px output). A punch wider than 1080/872 = 1.238 starts
slicing that column, so every window is capped below it and the resulting
guaranteed margin is printed (and re-measured on real pixels by the sweep).
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT_W, OUT_H = 1080, 1920
PUNCH_IN, PUNCH_OUT = 0.55, 0.65
MIN_GAP = 1.5  # brief: windows incl. ramps must be >= 1.5s apart


def col_extent(meta):
    """Content-column ink extent in OUTPUT px, from the recorder's boxes."""
    b = meta["geometry"]["bin_box_viewport"]
    x0, x1 = b["x"] * 2, (b["x"] + b["w"]) * 2
    return x0, x1


def zoom_for(x0, x1, margin_px):
    """Largest zoom keeping [x0,x1] inside the frame with >= margin_px of
    final-frame margin on each side.  final margin = (OUT_W - span*z)/2."""
    span = x1 - x0
    return round((OUT_W - 2 * margin_px) / span, 3)


def build(meta, tail_pad=0.4):
    m, g, dur = meta["marks"], meta["geometry"], meta["duration"]
    x0, x1 = col_extent(meta)
    cx = round((x0 + x1) / 2 / OUT_W, 4)

    punches = [
        {"t0": m["progress_hold_start"], "t1": m["progress_hold_end"],
         "center": [cx, g["progress_center"][1]],
         "zoom": zoom_for(x0, x1, 26), "label": "progress-label"},
        {"t0": m["chip_hold_start"], "t1": m["chip_hold_end"],
         "center": [cx, g["chip_hold"]["center"][1]],
         "zoom": zoom_for(x0, x1, 26), "label": "green-filmstrip-chip"},
        {"t0": m["bin_hold_start"], "t1": min(m["bin_hold_end"], dur - PUNCH_OUT - tail_pad),
         "center": [cx, g["bin_center"][1]],
         "zoom": zoom_for(x0, x1, 38), "label": "bin-grid"},
    ]
    for p in punches:
        p["t0"] = round(float(p["t0"]), 3)
        p["t1"] = round(float(p["t1"]), 3)

    # enforce the spacing the brief asks for, in the recording, not in a blend
    for a, b in zip(punches, punches[1:]):
        gap = (b["t0"] - PUNCH_IN) - (a["t1"] + PUNCH_OUT)
        if gap < MIN_GAP:
            sys.exit(f"ABORT: punches {a['label']} -> {b['label']} are {gap:.2f}s apart "
                     f"with ramps included (need >= {MIN_GAP}s) — re-record with more space.")
    return {"duration": dur, "punches": punches, "_column": [x0, x1]}


def camera_margins(tl, duration, fps=30):
    """Analytic check: does the camera ever cut INTO the content column?

    The board's own chrome (the icon rail) lives left of the column and is
    fair game to crop — a global ink sweep can't tell that crop apart from a
    sliced label, and reports margin 0 the moment a punch eats the rail. So
    the label check runs on the camera path itself, against the measured
    column extent, and the pixel sweep below is left to police the right edge
    where nothing but content lives.
    """
    sys.path.insert(0, str(ROOT / "scripts"))
    from style_punch import PunchCamera

    cam = PunchCamera(tl, duration)
    x0c, x1c = tl["_column"]
    worst = {"margin": 10 ** 9}
    for i in range(int(duration * fps) + 1):
        t = i / fps
        z, cx, _cy = cam.at(t)
        cw = OUT_W / z
        x0 = min(max(cx * OUT_W - cw / 2.0, 0.0), OUT_W - cw)
        left = (x0c - x0) * z          # final-frame px from left edge to column
        right = (x0 + cw - x1c) * z    # …and from column to right edge
        mn = min(left, right)
        if mn < worst["margin"]:
            worst = {"margin": round(mn, 1), "t": round(t, 2), "zoom": round(z, 3),
                     "left": round(left, 1), "right": round(right, 1)}
    return worst


def sweep(path, fps_list=(2, 5), thresh=42):
    """Pixel sweep of the styled output: min distance from ink to the RIGHT
    frame edge (plus informational left/top/bottom), over every sampled frame.

    Ink = pixels brighter than `thresh` on this dark UI. Right is the gated
    side: nothing but board content lives there, so a right margin going to 0
    means a punch really did overshoot. Left is informational (the icon rail
    is cropped on purpose); top/bottom likewise, since a scrolling page runs
    off both by definition.
    """
    worst = {"margin": 10**9}
    for fps in fps_list:
        proc = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"fps={fps}",
             "-pix_fmt", "gray", "-f", "rawvideo", "-"],
            capture_output=True)
        buf = proc.stdout
        n = len(buf) // (OUT_W * OUT_H)
        arr = np.frombuffer(buf[: n * OUT_W * OUT_H], dtype=np.uint8).reshape(n, OUT_H, OUT_W)
        for i in range(n):
            ink = arr[i] > thresh
            cols = np.where(ink.any(axis=0))[0]
            rows = np.where(ink.any(axis=1))[0]
            if not len(cols) or not len(rows):
                continue
            left, right = int(cols[0]), int(OUT_W - 1 - cols[-1])
            top, bottom = int(rows[0]), int(OUT_H - 1 - rows[-1])
            if right < worst["margin"]:
                worst = {"margin": right, "fps": fps, "frame": i, "t": round(i / fps, 2),
                         "right": right, "left_informational": left,
                         "top_informational": top, "bottom_informational": bottom}
        print(f"  swept {n} frames @ {fps}fps")
    return worst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw")
    ap.add_argument("out")
    ap.add_argument("--meta", help="raw_board.raw.json (default: <raw>.raw.json)")
    ap.add_argument("--min-margin", type=int, default=12)
    a = ap.parse_args()

    raw = Path(a.raw)
    meta = json.loads(Path(a.meta or raw.with_suffix(".raw.json")).read_text())
    tl = build(meta)
    tl_path = raw.with_suffix(".timeline.json")
    tl_path.write_text(json.dumps(tl, indent=2))
    print(json.dumps(tl, indent=2))

    cam_worst = camera_margins(tl, meta["duration"])
    print("camera vs content column:", json.dumps(cam_worst))
    if cam_worst["margin"] < a.min_margin:
        sys.exit(f"ABORT: the camera crops the content column to {cam_worst['margin']}px "
                 f"at t={cam_worst['t']}s — lower the zoom.")

    subprocess.run([sys.executable, str(ROOT / "scripts" / "style_punch.py"),
                    str(raw), str(a.out), "--timeline", str(tl_path)], check=True)

    print("edge sweep:")
    worst = sweep(a.out)
    print("  min right-edge ink margin:", json.dumps(worst))
    if worst["margin"] < a.min_margin:
        sys.exit(f"ABORT: ink reaches within {worst['margin']}px of the right frame edge "
                 f"at t={worst.get('t')}s — a punch is clipping content.")
    Path(str(a.out) + ".sweep.json").write_text(
        json.dumps({"pixel_sweep": worst, "camera_vs_column": cam_worst}, indent=2))


if __name__ == "__main__":
    main()
