#!/usr/bin/env python3
"""
make_still_hold.py — turn an approved STILL into a calm held beat.

Playbook §13 "Opening pacing" says the intro/title overlay must hold 2.5-4s as
its own readable beat, "in dead space or over a calm frame — never over busy
motion". The calmest possible frame under a title card is a frozen one, but a
dead-still frame for 3-5s reads as a freeze bug, and Short.tsx's `kind:"image"`
segment has no camera. So: bake the still into a clip with a push so slow it is
felt rather than seen (default 1.000 -> 1.030 over the whole beat).

Ken Burns craft is the playbook's (§15): supersample 2x first, and zoompan is
allowed here precisely because this IS a true push-in on a still.

  python3 scripts/make_still_hold.py --still channels/claude-tricks/assets/ep25/hook_board.png \\
      --dur 5.12 --out channels/claude-tricks/assets/ep25/hook_board_hold.mp4
"""
import argparse, shutil, subprocess

FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
W, H = 1080, 1920


def build(still, dur, out, fps=30, push=0.030, crf=17):
    n = int(round(dur * fps))
    vf = (
        f"scale={W*2}:{H*2}:flags=lanczos,"
        f"zoompan=z='min({1+push},1+{push}*on/{max(n-1,1)})':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d=1:s={W}x{H}:fps={fps},setsar=1,format=yuv420p"
    )
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(fps), "-t", str(dur), "-i", still,
           "-vf", vf, "-r", str(fps), "-frames:v", str(n),
           "-c:v", "libx264", "-crf", str(crf), "-preset", "slow", "-pix_fmt", "yuv420p", out]
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(">> HOLD", out)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", required=True)
    ap.add_argument("--dur", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--push", type=float, default=0.030)
    ap.add_argument("--crf", type=int, default=17)
    a = ap.parse_args()
    build(a.still, a.dur, a.out, a.fps, a.push, a.crf)
