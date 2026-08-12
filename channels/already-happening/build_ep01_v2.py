#!/usr/bin/env python3
"""build_ep01_v2.py — PRO cut for "Already Happening" Ep01.

Upgrades over v1: real Hailuo motion footage (not Ken Burns stills), running
word-by-word captions with teal keyword color-pops (synced to the VO word
timings), a subtle cinematic grade, light grain, VO + ducked bed @ -14 LUFS.
1080x1920 @30fps.
"""
import json, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
MOT = os.path.join(HERE, "assets", "ep01", "motion")
VO = os.path.join(HERE, "renders", "ep01", "vo")
OUT = os.path.join(HERE, "renders", "ep01")
TMP = tempfile.mkdtemp(prefix="ah_v2_")
W, H, FPS = 1080, 1920, 30
TEAL = (34, 211, 238)
AMBER = (255, 179, 40)
WHITE = (245, 248, 250)
MUSIC = os.path.join(HERE, "..", "claude-tricks", "assets", "music", "bed_active.mp3")
TAIL = 0.45
GAP = 0.45

# beat -> (motion clip, vo stem)
BEATS = [
    ("cinematic-first-person-driving-p_1f195505.mp4", "beat1"),
    ("cinematic-documentary-shot-a-whi_1f195500.mp4", "beat2"),
    ("cinematic-tracking-shot-a-white-_1f1954fa.mp4",  "beat3"),
    ("cinematic-slow-forward-dolly-sle_1f1954d7.mp4",  "beat4"),
    ("cinematic-slow-push-in-through-a_1f1954f4.mp4",  "beat5"),
    ("cinematic-first-person-pov-insid_1f1954ed.mp4",  "beat6"),
]
HOT = {"FIFTY","THOUSAND","NO","ONE","WHEEL","DEMO","TUESDAY","TODAY","PHOENIX",
       "FRANCISCO","AUSTIN","MILLIONS","FIVE","YEARS","NINETY","SECONDS","CHEAPER",
       "THIRD","PARKING","PARKS","HOMES","STREETS","GARAGE","ROOM","AI","ROUTE",
       "SPEED","PRIORITY","GIVE","NEVER","LAND","OWN"}

def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

def probe(path):
    return float(subprocess.check_output(
        ["ffprobe","-v","error","-show_entries","format=duration","-of","default=nk=1:nw=1",path]).strip())

def font(sz):
    for p in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/System/Library/Fonts/HelveticaNeue.ttc"]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, sz)
            except Exception: pass
    return ImageFont.load_default()

FBIG = font(58)
TRACK = 3

def _measure(word, f):
    d = ImageDraw.Draw(Image.new("RGBA",(4,4)))
    return sum(d.textlength(c, font=f)+TRACK for c in word) - TRACK

def color_for(word):
    return TEAL if word.upper() in HOT else WHITE

def draw_word(d, x, y, word, col, f):
    for c in word:
        d.text((x+2, y+3), c, font=f, fill=(0,0,0,180))   # shadow
        d.text((x, y), c, font=f, fill=col+(255,))
        x += d.textlength(c, font=f) + TRACK
    return x

def caption_png(visible_words, path):
    """Full-frame transparent PNG: the visible words on up to 2 centered lines,
    lower third, with a soft dark pill behind for legibility."""
    im = Image.new("RGBA",(W,H),(0,0,0,0)); d = ImageDraw.Draw(im)
    # wrap into lines <= ~ W*0.82
    maxw = W*0.82
    lines, cur, curw = [], [], 0
    for wd in visible_words:
        ww = _measure(wd, FBIG) + _measure(" ", FBIG)
        if curw+ww > maxw and cur:
            lines.append(cur); cur, curw = [], 0
        cur.append(wd); curw += ww
    if cur: lines.append(cur)
    lines = lines[-2:]  # keep last 2 lines max
    lh = 78
    total_h = lh*len(lines)
    y0 = int(H*0.70)
    # pill
    widths = [sum(_measure(w,FBIG)+_measure(" ",FBIG) for w in ln)-_measure(" ",FBIG) for ln in lines]
    pill_w = int(max(widths)+80); pill_h = total_h+46
    px0 = (W-pill_w)//2; py0 = y0-24
    d.rounded_rectangle([px0,py0,px0+pill_w,py0+pill_h], radius=26, fill=(8,10,14,168))
    for i, ln in enumerate(lines):
        lw = widths[i]; x = (W-lw)//2; y = y0 + i*lh
        for wd in ln:
            x = draw_word(d, x, y, wd, color_for(wd), FBIG)
            x += _measure(" ", FBIG)
    im.save(path)

def fit_clip(src, target, out):
    clip = probe(src)
    if target <= clip:
        vf = f"scale={W}:{H},trim=0:{target},setpts=PTS-STARTPTS"
    else:
        f = target/clip
        vf = f"scale={W}:{H},setpts={f:.4f}*PTS"
    run(["ffmpeg","-y","-i",src,"-vf",vf,"-an","-t",str(target),"-r",str(FPS),
         "-c:v","libx264","-crf","17","-preset","medium","-pix_fmt","yuv420p",out])

def build_segment(idx, clip, vo_stem, dur):
    base = os.path.join(TMP, f"fit_{idx}.mp4"); fit_clip(os.path.join(MOT,clip), dur, base)
    words = json.load(open(os.path.join(VO, vo_stem+".words.json")))
    # group words into caption lines of <=5 words
    lines, cur = [], []
    for wjson in words:
        cur.append(wjson)
        if len(cur) >= 5:
            lines.append(cur); cur=[]
    if cur: lines.append(cur)
    # build overlay png list with enable windows: within a line, words appear one by one
    pngs, wins = [], []
    for li, ln in enumerate(lines):
        line_end = ln[-1]["end"] + 0.35
        if li < len(lines)-1:
            line_end = min(line_end, lines[li+1][0]["start"])
        for wi in range(len(ln)):
            vis = [w["w"] for w in ln[:wi+1]]
            p = os.path.join(TMP, f"cap_{idx}_{li}_{wi}.png"); caption_png(vis, p)
            start = ln[wi]["start"]
            end = ln[wi+1]["start"] if wi+1 < len(ln) else line_end
            pngs.append(p); wins.append((start, end))
    # overlay all caption pngs onto the fitted clip
    inputs = ["-i", base]
    for p in pngs: inputs += ["-i", p]
    fc = []; prev = "[0:v]"
    for i,(s,e) in enumerate(wins):
        lbl = "[v]" if i==len(wins)-1 else f"[o{i}]"
        fc.append(f"{prev}[{i+1}:v]overlay=0:0:enable='between(t,{s:.2f},{e:.2f})'{lbl}")
        prev = lbl
    seg = os.path.join(TMP, f"seg_{idx}.mp4")
    if wins:
        run(["ffmpeg","-y",*inputs,"-filter_complex",";".join(fc),"-map","[v]",
             "-t",str(dur),"-c:v","libx264","-crf","17","-preset","medium","-pix_fmt","yuv420p",seg])
    else:
        os.replace(base, seg)
    return seg

def main():
    os.makedirs(OUT, exist_ok=True)
    segs, vo_parts, durs = [], [], []
    for i,(clip,vo) in enumerate(BEATS):
        d = json.load(open(os.path.join(VO,vo+".words.json")))
        dur = (d[-1]["end"] if d else 2.0) + TAIL
        durs.append(dur)
        segs.append(build_segment(i, clip, vo, dur))
        vo_parts.append(os.path.join(VO, vo+".wav"))
    # concat
    listf = os.path.join(TMP,"segs.txt"); open(listf,"w").write("".join(f"file '{s}'\n" for s in segs))
    concat = os.path.join(TMP,"concat.mp4")
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",listf,
         "-c:v","libx264","-crf","17","-preset","medium","-pix_fmt","yuv420p",concat])
    # cinematic grade: subtle contrast/sat + light grain + vignette
    graded = os.path.join(TMP,"graded.mp4")
    run(["ffmpeg","-y","-i",concat,"-vf",
         "eq=contrast=1.05:saturation=1.07,noise=alls=4:allf=t,vignette=PI/5.5",
         "-c:v","libx264","-crf","18","-preset","medium","-pix_fmt","yuv420p",graded])
    # VO track with gaps
    sil = os.path.join(TMP,"sil.wav")
    run(["ffmpeg","-y","-f","lavfi","-i","anullsrc=r=44100:cl=mono","-t",str(GAP),"-c:a","pcm_s16le",sil])
    ap=[]
    for p in vo_parts: ap += [p, sil]
    al=os.path.join(TMP,"vo.txt"); open(al,"w").write("".join(f"file '{p}'\n" for p in ap))
    vofull=os.path.join(TMP,"vo_full.wav")
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",al,"-c:a","pcm_s16le",vofull])
    # mux VO + ducked bed, master -14 LUFS
    out=os.path.join(OUT,"ep01_v2.mp4")
    fc=("[1:a]volume=6dB[v0];[2:a]volume=-19dB[m];"
        "[v0][m]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]")
    run(["ffmpeg","-y","-i",graded,"-i",vofull,"-stream_loop","-1","-i",MUSIC,
         "-filter_complex",fc,"-map","0:v","-map","[a]","-c:v","copy","-c:a","aac","-b:a","192k",
         "-ar","48000","-movflags","+faststart","-shortest",out])
    print(f"OK -> {out}  (~{sum(durs):.1f}s)")

if __name__ == "__main__":
    main()
