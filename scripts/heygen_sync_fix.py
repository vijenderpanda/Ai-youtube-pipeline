#!/usr/bin/env python3
"""
heygen_sync_fix.py — measure and correct HeyGen's lip-sync error, which is BOTH a
constant offset and a rate drift.

Measured on this account, 2026-09-02, across two independent generations of the same
host: the mouth leads its own audio by ~200 ms at t=0 and the lead GROWS to ~440 ms by
t=18 s. That is a ~1.3% rate error, not a fixed offset, so `tpad`/`itsoffset` alone
cannot fix it — it only trades an early opening for a late ending. Symptom: the cut
"feels weird" at one end however you shift it.

Correction is therefore two-part:
    setpts=RATE*PTS      walks the accumulating lead back over the runtime
    tpad start_duration  removes the residual constant offset at t=0

Verify, never assume: run scripts/lipsync_visual.py on sliding windows afterwards and
check there is no monotonic trend left. Gate the HOST CLIP, not the composite — in a
SEAM cut the face is absent ~50% of the runtime and the correlation falls below the
tool's own confidence floor.

    python3 scripts/heygen_sync_fix.py in.mp4 out.mp4 --rate 1.013 --offset 0.20
"""
import argparse, subprocess, sys

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("dst")
ap.add_argument("--rate", type=float, default=1.013, help="setpts multiplier; >1 slows the picture")
ap.add_argument("--offset", type=float, default=0.20, help="seconds of head pad for the residual")
ap.add_argument("--w", type=int, default=1080); ap.add_argument("--h", type=int, default=1920)
ap.add_argument("--fps", type=int, default=30)
a = ap.parse_args()

vf = (f"setpts={a.rate}*PTS,scale={a.w}:{a.h}:flags=lanczos,fps={a.fps},"
      f"tpad=start_mode=clone:start_duration={a.offset}")
r = subprocess.run(["ffmpeg", "-v", "error", "-i", a.src, "-vf", vf, "-an",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-y", a.dst])
if r.returncode:
    sys.exit(r.returncode)
print(f"ok  rate {a.rate}  offset {a.offset}s  -> {a.dst}")
print("    now verify: python3 scripts/lipsync_visual.py <clip muxed with the VO> --start N --dur 4")
