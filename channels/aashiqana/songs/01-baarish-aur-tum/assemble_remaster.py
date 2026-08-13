#!/usr/bin/env python3
"""Tu Hi Hai long-form remaster base assembler.
Sequences the 13 Hailuo motion clips (with reprises + slo-mo) across the full
4:17 track, xfade 0.7s, 1920x1080@30, song audio with end fade.
Output = base for scripts/lyric_karaoke.py.
"""
import os, subprocess, tempfile

BASE = os.path.dirname(os.path.abspath(__file__))
M = os.path.join(BASE, "_motion_remaster")
SONG = os.path.join(BASE, "renders", "d7e8b8d0-45dd-4d74-b1c0-e54dfe7a6711.mp3")
OUT = os.path.join(BASE, "renders", "base_motion_remaster_1080.mp4")
XF = 0.7
W, H = 1920, 1080

# (clip, speed) — story arc: rain street -> cafe -> rooftop -> slow reprises -> hills -> outro
SEQ = [
    ("C06_walk_away", 0.75), ("C01_spin_away", 1.0), ("C02_spin_back", 1.0),
    ("C03_pull_pushin", 0.75), ("C05_umbrella_laugh", 1.0), ("C04_lean_closer", 0.75),
    ("C08_chai_steam", 1.0), ("C07_cafe_tuck", 0.75), ("C05_umbrella_laugh", 0.6),
    ("C08_chai_steam", 0.7), ("C07_cafe_tuck", 0.6),
    ("C09_behind_hold", 0.75), ("C10_chin_lift", 1.0), ("C11_she_rises", 0.75), ("C13_forehead_sway", 0.6),
    ("C06_walk_away", 0.6), ("C03_pull_pushin", 0.6), ("C01_spin_away", 0.75), ("C09_behind_hold", 0.6),
    ("C10_chin_lift", 0.6), ("C11_she_rises", 0.6), ("C04_lean_closer", 0.6), ("C02_spin_back", 0.75),
    ("C12_hills_run", 1.0), ("C12_hills_run", 0.6), ("C05_umbrella_laugh", 0.75), ("C01_spin_away", 0.6),
    ("C13_forehead_sway", 0.5), ("C06_walk_away", 0.5), ("C13_forehead_sway", 0.55),
    ("C09_behind_hold", 0.5), ("C04_lean_closer", 0.5), ("C12_hills_run", 0.5),
]

def probe(p):
    return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","csv=p=0",p],capture_output=True,text=True).stdout.strip())

song_dur = probe(SONG)
work = tempfile.mkdtemp(prefix="remaster_")
segs = []
total = 0.0
for i,(name,speed) in enumerate(SEQ):
    src = os.path.join(M, name + ".mp4")
    if not os.path.exists(src):
        print("skip missing", name); continue
    o = f"{work}/s{i}.mp4"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",src,
        "-vf",f"setpts=PTS/{speed},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30",
        "-an","-c:v","libx264","-crf","18","-pix_fmt","yuv420p",o],check=True)
    d = probe(o)
    segs.append((o,d)); total += d
    if total - XF*len(segs) > song_dur + 8: break
print(f"{len(segs)} segments, raw total {total:.1f}s vs song {song_dur:.1f}s")

# one-pass xfade chain
inputs = []
for o,_ in segs: inputs += ["-i", o]
fc = []
prev = "0:v"; t = segs[0][1] - XF
for i in range(1, len(segs)):
    outl = f"v{i}"
    fc.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={XF}:offset={t:.3f}[{outl}]")
    prev = outl
    t += segs[i][1] - XF
fc.append(f"[{prev}]trim=0:{song_dur:.2f},setpts=PTS-STARTPTS,fade=t=out:st={song_dur-1.5:.2f}:d=1.5[vout]")
cmd = (["ffmpeg","-y","-loglevel","error"] + inputs + ["-i",SONG,
    "-filter_complex",";".join(fc),
    "-map","[vout]","-map",f"{len(segs)}:a",
    "-af",f"afade=t=out:st={song_dur-2.5:.2f}:d=2.5",
    "-c:v","libx264","-crf","18","-pix_fmt","yuv420p","-c:a","aac","-b:a","256k",
    "-t",f"{song_dur:.2f}", OUT])
subprocess.run(cmd, check=True)
print(">> DONE", OUT, probe(OUT), "s")
