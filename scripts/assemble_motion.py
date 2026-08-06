#!/usr/bin/env python3
"""
Assemble short motion clips into a crossfaded music video.

Each scene clip (~5s) is BOOMERANGed (forward+reverse = seamless loop) and looped
to its target duration, all scenes are crossfaded, then the song is muxed in.

shots json: [{"clip":"channels/.../mo_s00.mp4","dur":12}, ...]
Usage:
  python3 scripts/assemble_motion.py --shots channels/language-abc/songs/01_motion_shots.json \
      --audio channels/language-abc/songs/song01_bed.mp3 \
      --out channels/language-abc/renders/ep01_motion_full.mp4
"""
import argparse, json, os, subprocess, tempfile
FPS = 30; W, H = 1920, 1080

def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

def make_scene(clip, dur, out):
    """Boomerang the clip, then loop it to `dur` seconds at WxH."""
    boom = out + ".boom.mp4"
    run(["ffmpeg", "-y", "-i", clip, "-filter_complex",
         f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
         f"setsar=1,fps={FPS},split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1[v]",
         "-map", "[v]", "-an", "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
         "-pix_fmt", "yuv420p", boom])
    run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", boom, "-t", f"{dur}", "-r", str(FPS),
         "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-pix_fmt", "yuv420p", out])
    os.remove(boom)

def assemble(clips, durs, out, T=1.0):
    n = len(clips)
    if n == 1:
        run(["ffmpeg", "-y", "-i", clips[0], "-c", "copy", out]); return
    cmd = ["ffmpeg", "-y"]
    for c in clips:
        cmd += ["-i", c]
    fparts = []; prev = "0:v"; acc = durs[0]
    for i in range(1, n):
        offset = acc - T
        outlbl = "vout" if i == n - 1 else f"x{i}"
        fparts.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={T}:offset={offset:.3f}[{outlbl}]")
        prev = outlbl; acc += durs[i] - T
    cmd += ["-filter_complex", ";".join(fparts), "-map", "[vout]",
            "-c:v", "libx264", "-crf", "19", "-preset", "medium", "-pix_fmt", "yuv420p", out]
    run(cmd)

def add_audio(video, audio, out):
    vdur = float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", video]).strip())
    fo = max(vdur - 3, 0)
    run(["ffmpeg", "-y", "-i", video, "-i", audio, "-filter_complex",
         f"[1:a]afade=t=in:st=0:d=2,afade=t=out:st={fo:.2f}:d=3[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", required=True)
    ap.add_argument("--audio")
    ap.add_argument("--out", required=True)
    ap.add_argument("--transition", type=float, default=1.0)
    a = ap.parse_args()
    shots = json.load(open(a.shots))
    tmp = tempfile.mkdtemp(prefix="mo_scenes_")
    scene_files = []; durs = []
    for i, s in enumerate(shots):
        sf = os.path.join(tmp, f"scene_{i:02d}.mp4")
        print("scene", i, s["clip"], s["dur"])
        make_scene(s["clip"], float(s["dur"]), sf)
        scene_files.append(sf); durs.append(float(s["dur"]))
    silent = a.out.replace(".mp4", "_silent.mp4")
    assemble(scene_files, durs, silent, T=a.transition)
    if a.audio:
        add_audio(silent, a.audio, a.out)
    else:
        os.replace(silent, a.out)
    print(">> DONE:", a.out)

if __name__ == "__main__":
    main()
