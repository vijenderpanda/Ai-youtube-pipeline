#!/usr/bin/env python3
"""Tu Hi Hai remaster v2 (VJ notes 2026-08-13):
- trim 30.9s instrumental intro -> vocal hits ~2.0s (hooky start)
- captions = Talab-style 2-3 word chunks, true whisper word sync (LONG-FORM ONLY style)
- hooky opener: charged close-up first
- C01 replaced by re-rolled twirl (C01v2 if present)
"""
import json, os, subprocess, tempfile, unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))
M = os.path.join(BASE, "_motion_remaster")
SONG_FULL = os.path.join(BASE, "renders", "d7e8b8d0-45dd-4d74-b1c0-e54dfe7a6711.mp3")
SONG = os.path.join(BASE, "renders", "song_lf_hookcut.mp3")
WORDS = os.path.join(BASE, "lyrics", "words_remaster.json")
BASE_OUT = os.path.join(BASE, "renders", "base_motion_remaster_v2.mp4")
FINAL = os.path.join(BASE, "renders", "aashiqana_tu_hi_hai_remaster_v2.mp4")
TRIM = 30.9
XF = 0.7
W, H = 1920, 1080

C01 = "C01v2_twirl" if os.path.exists(os.path.join(M, "C01v2_twirl.mp4")) else "C01_spin_away"

# hooky opener: charged pull close-up first, vocal lands at ~2s over it
SEQ = [
    ("C03_pull_pushin", 1.0), (C01, 1.0), ("C02_spin_back", 1.0),
    ("C05_umbrella_laugh", 1.0), ("C04_lean_closer", 0.75), ("C06_walk_away", 0.75),
    ("C08_chai_steam", 1.0), ("C07_cafe_tuck", 0.75), ("C05_umbrella_laugh", 0.6), ("C08_chai_steam", 0.7),
    ("C09_behind_hold", 0.75), ("C10_chin_lift", 1.0), ("C11_she_rises", 0.75), ("C13_forehead_sway", 0.6),
    ("C06_walk_away", 0.6), ("C03_pull_pushin", 0.6), (C01, 0.75), ("C09_behind_hold", 0.6),
    ("C10_chin_lift", 0.6), ("C11_she_rises", 0.6), ("C04_lean_closer", 0.6),
    ("C12_hills_run", 1.0), ("C12_hills_run", 0.6), ("C02_spin_back", 0.75),
    ("C13_forehead_sway", 0.5), ("C06_walk_away", 0.5), ("C13_forehead_sway", 0.55),
    ("C09_behind_hold", 0.5), ("C04_lean_closer", 0.5), ("C12_hills_run", 0.5),
]

def probe(p):
    return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","csv=p=0",p],capture_output=True,text=True).stdout.strip())

# 1) trim song
subprocess.run(["ffmpeg","-y","-loglevel","error","-ss",str(TRIM),"-i",SONG_FULL,
    "-af","afade=t=in:st=0:d=0.4","-c:a","libmp3lame","-q:a","2",SONG],check=True)
song_dur = probe(SONG)
print(f"trimmed song: {song_dur:.1f}s (vocal at ~2.0s)")

# 2) chunk words -> ASS
words = [w for w in json.load(open(WORDS)) if w["s"] >= TRIM - 0.5]
for w in words: w["s"] = max(0.0, w["s"] - TRIM); w["e"] = max(0.0, w["e"] - TRIM)

def roman(dev):
    try:
        from indic_transliteration import sanscript
        r = sanscript.transliterate(dev, sanscript.DEVANAGARI, sanscript.ISO)
        r = unicodedata.normalize("NFD", r)
        r = "".join(c for c in r if not unicodedata.combining(c))
        return r.replace("ṁ","n").replace("ḥ","h")
    except Exception:
        return ""

chunks = []
cur = []
for w in words:
    if cur and (w["s"] - cur[-1]["e"] > 0.6 or len(cur) >= 3):
        chunks.append(cur); cur = []
    cur.append(w)
if cur: chunks.append(cur)

def ts(t):
    h = int(t//3600); m = int(t%3600//60); s = t%60
    return f"{h}:{m:02d}:{s:05.2f}"

ass = ["[Script Info]","ScriptType: v4.00+","PlayResX: 1920","PlayResY: 1080","",
 "[V4+ Styles]",
 "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Alignment, MarginL, MarginR, MarginV, Outline, Shadow, BorderStyle, Encoding",
 "Style: dev,Kohinoor Devanagari,92,&H00FFFFFF,&H00000000,&H7F000000,-1,0,2,60,60,150,4,2,1,1",
 "Style: rom,Georgia,52,&H0078D6FF,&H00000000,&H7F000000,-1,0,2,60,60,86,3,1,1,1","",
 "[Events]","Format: Layer, Start, End, Style, MarginL, MarginR, MarginV, Text"]
for i,ch in enumerate(chunks):
    s = ch[0]["s"]; e = ch[-1]["e"] + 0.25
    if i+1 < len(chunks): e = min(e, chunks[i+1][0]["s"] - 0.05)
    dev = " ".join(w["w"] for w in ch)
    rom = roman(dev)
    ass.append(f"Dialogue: 0,{ts(s)},{ts(e)},dev,,0,0,150,{dev}")
    if rom: ass.append(f"Dialogue: 0,{ts(s)},{ts(e)},rom,,0,0,86,{rom}")
ASS = os.path.join(BASE, "lyrics", "chunks_lf.ass")
open(ASS,"w").write("\n".join(ass))
print(f"{len(chunks)} caption chunks -> {ASS}")

# 3) base build
work = tempfile.mkdtemp(prefix="rem2_")
segs = []; total = 0.0
for i,(name,speed) in enumerate(SEQ):
    src = os.path.join(M, name + ".mp4")
    if not os.path.exists(src): print("skip", name); continue
    o = f"{work}/s{i}.mp4"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",src,
        "-vf",f"setpts=PTS/{speed},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30",
        "-an","-c:v","libx264","-crf","18","-pix_fmt","yuv420p",o],check=True)
    d = probe(o); segs.append((o,d)); total += d
    if total - XF*len(segs) > song_dur + 6: break
print(f"{len(segs)} segments, raw {total:.1f}s vs song {song_dur:.1f}s")

inputs = []
for o,_ in segs: inputs += ["-i", o]
fc = []; prev = "0:v"; t = segs[0][1] - XF
for i in range(1, len(segs)):
    fc.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={XF}:offset={t:.3f}[v{i}]")
    prev = f"v{i}"; t += segs[i][1] - XF
fc.append(f"[{prev}]trim=0:{song_dur:.2f},setpts=PTS-STARTPTS,fade=t=out:st={song_dur-1.5:.2f}:d=1.5[vout]")
subprocess.run(["ffmpeg","-y","-loglevel","error"] + inputs + ["-i",SONG,
    "-filter_complex",";".join(fc),
    "-map","[vout]","-map",f"{len(segs)}:a",
    "-af",f"afade=t=out:st={song_dur-2.5:.2f}:d=2.5,volume=-0.7dB",
    "-c:v","libx264","-crf","18","-pix_fmt","yuv420p","-c:a","aac","-b:a","256k",
    "-t",f"{song_dur:.2f}", BASE_OUT],check=True)
print(">> base", probe(BASE_OUT))

# 4) burn captions via PIL PNG overlays (no libass in this ffmpeg)
from PIL import Image, ImageDraw, ImageFont

def font(paths, size):
    for p in paths:
        try: return ImageFont.truetype(p, size)
        except Exception: pass
    return None

F_DEV = ["/System/Library/Fonts/Kohinoor.ttc", "/System/Library/Fonts/Supplemental/Kohinoor.ttc"]
F_ROM = ["/System/Library/Fonts/Supplemental/Georgia Bold.ttf"]
fdev = font(F_DEV, 88); from_ = font(F_ROM, 46)

png_dir = os.path.join(work, "chunks"); os.makedirs(png_dir, exist_ok=True)
events = []
for i,ch in enumerate(chunks):
    s = ch[0]["s"]; e = ch[-1]["e"] + 0.25
    if i+1 < len(chunks): e = min(e, chunks[i+1][0]["s"] - 0.05)
    if e <= s: e = s + 0.4
    dev = " ".join(w["w"] for w in ch); rom = roman(dev)
    img = Image.new("RGBA",(W,H),(0,0,0,0)); d = ImageDraw.Draw(img)
    y = 880
    if fdev:
        bb = d.textbbox((0,0),dev,font=fdev,stroke_width=5)
        d.text(((W-(bb[2]-bb[0]))//2 - bb[0], y), dev, font=fdev, fill=(255,255,255,255),
               stroke_width=5, stroke_fill=(0,0,0,235))
        y += (bb[3]-bb[1]) + 14
    if rom and from_:
        bb = d.textbbox((0,0),rom,font=from_,stroke_width=4)
        d.text(((W-(bb[2]-bb[0]))//2 - bb[0], y), rom, font=from_, fill=(255,214,120,255),
               stroke_width=4, stroke_fill=(0,0,0,235))
    p = f"{png_dir}/c{i:03d}.png"; img.save(p)
    events.append((p, s, e))

cur = BASE_OUT
BATCH = 25
for bi in range(0, len(events), BATCH):
    batch = events[bi:bi+BATCH]
    nxt = FINAL if bi + BATCH >= len(events) else f"{work}/pass{bi}.mp4"
    inputs = ["-i", cur]
    for p,_,_ in batch: inputs += ["-i", p]
    fc = []; prev = "0:v"
    for j,(p,s,e) in enumerate(batch):
        lbl = f"o{j}" if j < len(batch)-1 else "vout"
        fc.append(f"[{prev}][{j+1}:v]overlay=0:0:enable='between(t,{s:.2f},{e:.2f})'[{lbl}]")
        prev = lbl
    subprocess.run(["ffmpeg","-y","-loglevel","error"] + inputs +
        ["-filter_complex",";".join(fc),"-map","[vout]","-map","0:a",
         "-c:v","libx264","-crf","18","-pix_fmt","yuv420p","-c:a","copy", nxt],check=True)
    cur = nxt
    print(f"caption pass {bi//BATCH+1} done")
print(">> DONE", FINAL, probe(FINAL))
