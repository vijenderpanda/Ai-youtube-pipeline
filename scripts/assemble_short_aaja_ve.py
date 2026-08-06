#!/usr/bin/env python3
"""9:16 Short for 'Aaja Ve' — hook cold-open, vertical center-crop of the hero motion clips.

Audio starts just before the first sung hook (aligned at 4.08s) so the vocal lands
in the first second. Frame zero is the S07 red-dress reveal (thumbnail-grade).

Usage: python3 scripts/assemble_short_aaja_ve.py [--start 3.6] [--dur 28] [--out ...]
"""
import argparse, os, subprocess

BASE = "channels/aashiqana/songs/02-aaja-ve"
CLIPS = f"{BASE}/renders/clips"
CLIP_ORDER = ["s07_motion", "s11_motion", "s01_motion", "s10_motion", "s12_motion"]
W, H, FPS = 1080, 1920, 30
T = 0.6


def probe(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", p], capture_output=True, text=True)
    return float(r.stdout.strip())


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(p.stderr[-1500:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--song", default=f"{BASE}/track/aaja_ve_final.mp3")
    ap.add_argument("--start", type=float, default=3.6)
    ap.add_argument("--dur", type=float, default=28.0)
    ap.add_argument("--out", default=f"{BASE}/renders/aaja_ve_short_base.mp4")
    a = ap.parse_args()
    work = f"{BASE}/renders/work_short"; os.makedirs(work, exist_ok=True)

    segs = []
    for i, name in enumerate(CLIP_ORDER):
        src = f"{CLIPS}/{name}.mp4"; d = max(2.0, probe(src) - 0.2)
        dst = f"{work}/s{i}_{name}.mp4"
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"fps={FPS},setsar=1,format=yuv420p")
        run(["ffmpeg", "-y", "-i", src, "-t", f"{d:.3f}", "-vf", vf, "-an",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", dst])
        segs.append((dst, probe(dst)))

    inputs = []; use = []; acc = 0.0
    for dst, d in segs:
        contrib = d if not use else d - T
        use.append((dst, d)); acc += contrib
        if acc >= a.dur:
            break
    dur = min(a.dur, acc)
    for dst, _ in use:
        inputs += ["-i", dst]
    fc = []; prev = "0:v"; accd = use[0][1]
    for k in range(1, len(use)):
        off = accd - T
        fc.append(f"[{prev}][{k}:v]xfade=transition=fade:duration={T}:offset={off:.3f}[v{k}]")
        prev = f"v{k}"; accd = accd + use[k][1] - T
    vlab = f"[{prev}]" if len(use) > 1 else "[0:v]"
    cmd = ["ffmpeg", "-y"] + inputs + ["-ss", f"{a.start}", "-t", f"{dur}", "-i", a.song]
    aidx = len(use)
    if fc:
        cmd += ["-filter_complex", ";".join(fc), "-map", vlab]
    else:
        cmd += ["-map", "0:v"]
    cmd += ["-map", f"{aidx}:a", "-af", f"afade=t=in:st=0:d=0.4,afade=t=out:st={dur-1.2:.2f}:d=1.2",
            "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", a.out]
    run(cmd)
    print(">> DONE", a.out, f"{probe(a.out):.1f}s")


if __name__ == "__main__":
    main()
