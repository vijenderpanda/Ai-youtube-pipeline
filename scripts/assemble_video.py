#!/usr/bin/env python3
"""
Assemble a calm motion-graphics video from still scenes.

- Ken Burns (slow zoom/pan) per shot
- Crossfade transitions between shots
- Optional audio mux (loops/trims to length + gentle fade in/out)

Usage:
  python3 scripts/assemble_video.py --shots songs/01_shots.json --out renders/song01_silent.mp4
  python3 scripts/assemble_video.py --shots songs/01_shots.json --audio songs/song01.wav --out renders/song01.mp4

shots json: [{"img": "assets/scenes/s01_hill_1.jpg", "dur": 6, "motion": "zoom_in"}, ...]
motion ∈ zoom_in | zoom_out | pan_left | pan_right
"""
import argparse, json, os, subprocess, tempfile
from ffmpeg_util import venc  # GPU (NVENC) encode when available, else libx264

FPS = 30
W, H = 1920, 1080

def run(cmd):
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)

def probe_dur(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path])
    return float(out.strip())

def ken_burns(img, dur, motion, out):
    frames = int(dur * FPS)
    base = f"scale=2688:1536:force_original_aspect_ratio=increase,crop=2688:1536,setsar=1"
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    if motion == "zoom_in":
        z, x, y = "min(1.0+0.0009*on,1.15)", cx, cy
    elif motion == "zoom_out":
        z, x, y = "if(eq(on,0),1.15,max(1.15-0.0009*on,1.0))", cx, cy
    elif motion == "pan_left":
        z, x, y = "1.10", f"(iw-iw/zoom)*(1-on/{frames})", cy
    elif motion == "pan_right":
        z, x, y = "1.10", f"(iw-iw/zoom)*(on/{frames})", cy
    else:
        z, x, y = "min(1.0+0.0009*on,1.15)", cx, cy
    zp = f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS}"
    vf = f"{base},{zp},format=yuv420p"
    # NOTE: -t and -r MUST be output options (after -i). As input options they
    # multiply zoompan frames per input frame -> runaway clip length.
    run(["ffmpeg", "-y", "-loop", "1", "-i", img, "-vf", vf,
         "-t", str(dur), "-r", str(FPS),
         *venc("20", "veryfast"),
         "-pix_fmt", "yuv420p", out])

def assemble(clips, durs, out, T=1.0):
    n = len(clips)
    inputs = []
    for c in clips:
        inputs += ["-i", c]
    if n == 1:
        run(["ffmpeg", "-y", "-i", clips[0], "-c", "copy", out]); return
    fc, prev = [], "[0:v]"
    for i in range(1, n):
        off = sum(durs[:i]) - i * T
        out_lbl = "[vout]" if i == n - 1 else f"[x{i}]"
        fc.append(f"{prev}[{i}:v]xfade=transition=fade:duration={T}:offset={off:.3f}{out_lbl}")
        prev = out_lbl
    run(["ffmpeg", "-y"] + inputs + ["-filter_complex", ";".join(fc),
         "-map", "[vout]", *venc("19", "medium"),
         "-pix_fmt", "yuv420p", out])

def add_audio(video, audio, out):
    # Assumes the (silent) video is >= audio length; output is cut to the
    # audio length via -shortest, so build enough shots to cover the song.
    adur = probe_dur(audio)
    fo = max(0.1, adur - 3.0)
    run(["ffmpeg", "-y", "-i", video, "-i", audio,
         "-filter_complex", f"[1:a]afade=t=in:st=0:d=2,afade=t=out:st={fo:.2f}:d=3[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-shortest", out])

def apply_breathe(vin, vout, amp=0.045, period=5.0):
    # Gentle global warm-glow "breathe": a very subtle brightness + saturation
    # sine oscillation at ~breathing rate. Reads as Lulla's glow softly pulsing,
    # giving the calm scenes a hint of life without any character animation.
    b = f"{amp}*sin(2*PI*t/{period})"
    s = f"1+{amp * 1.4}*sin(2*PI*t/{period})"
    vf = f"eq=brightness='{b}':saturation='{s}':eval=frame"
    run(["ffmpeg", "-y", "-i", vin, "-vf", vf, "-an",
         *venc("19", "medium"), "-pix_fmt", "yuv420p", vout])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", required=True)
    ap.add_argument("--audio", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--transition", type=float, default=1.0)
    ap.add_argument("--breathe", type=float, default=0.0, help="glow-breathe amplitude (e.g. 0.045); 0 = off")
    ap.add_argument("--breathe_period", type=float, default=5.0)
    args = ap.parse_args()

    shots = json.load(open(args.shots))
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="lulla_clips_")
    clips, durs = [], []
    for i, s in enumerate(shots):
        clip = os.path.join(tmp, f"clip_{i:02d}.mp4")
        ken_burns(s["img"], s["dur"], s.get("motion", "zoom_in"), clip)
        clips.append(clip); durs.append(s["dur"])

    silent = args.out.replace(".mp4", "_silent.mp4")
    assemble(clips, durs, silent, args.transition)

    stage = silent
    if args.breathe > 0:
        breathed = args.out.replace(".mp4", "_breathe.mp4")
        apply_breathe(silent, breathed, args.breathe, args.breathe_period)
        stage = breathed

    if args.audio:
        add_audio(stage, args.audio, args.out)
    elif stage != args.out:
        os.replace(stage, args.out)

    total = sum(durs) - (len(durs) - 1) * args.transition
    print(f">> DONE: {args.out}  (~{total:.1f}s, {len(clips)} shots, breathe={args.breathe})")

if __name__ == "__main__":
    main()
