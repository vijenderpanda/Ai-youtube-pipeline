#!/usr/bin/env python3
"""
Karaoke lyric overlay: white line + gold left->right sweep synced to each line's sung window.
Per line: white PNG + gold PNG -> xfade wipeleft clip (sweep over [s,e], gold holds a tail),
PTS-shifted to s and overlaid on the base video.

Usage:
  python3 scripts/lyric_karaoke.py --base base.mp4 --timing timing_karaoke.json --out final.mp4
          [--w 1920 --h 1080 --tail 0.6]
"""
import argparse, json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

FONTS = [
    "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/Library/Fonts/Arial.ttf",
]
WHITE=(255,244,248,255); GOLD=(240,196,92,255)
FPS=30

def load_font(size):
    for f in FONTS:
        if os.path.exists(f):
            try: return ImageFont.truetype(f, size)
            except Exception: pass
    return ImageFont.load_default()

def render_pair(text, wpath, gpath, W, H, fs=None):
    fs = fs or max(34, int(W*0.030))
    font = load_font(fs)
    probe = Image.new("RGBA",(W,H)); pd = ImageDraw.Draw(probe)
    bb = pd.textbbox((0,0), text, font=font)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    pad = int(th*1.2)
    bw, bh = tw + pad*2, th + pad*2
    bw += bw % 2; bh += bh % 2   # even dims for yuva
    for path, fill in ((wpath, WHITE), (gpath, GOLD)):
        img = Image.new("RGBA",(bw,bh),(0,0,0,0)); d = ImageDraw.Draw(img)
        sc = Image.new("RGBA",(bw,bh),(0,0,0,0)); sd=ImageDraw.Draw(sc)
        for i in range(bh):
            a = int(120*(1-abs(i-bh/2)/(bh/2))**1.3)
            sd.line([(0,i),(bw,i)], fill=(0,0,0,a))
        img.alpha_composite(sc)  # same scrim on BOTH so the wipe is invisible on bg
        x, y = pad-bb[0], pad-bb[1]
        for dx,dy in [(0,3),(3,0),(0,-2),(-2,0),(2,2),(-2,2)]:
            d.text((x+dx,y+dy), text, font=font, fill=(0,0,0,190))
        d.text((x,y), text, font=font, fill=fill)
        img.save(path)
    return bw, bh

def probe_dur(path):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                        "-of","default=nw=1:nk=1",path],capture_output=True,text=True)
    return float(r.stdout.strip())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True); ap.add_argument("--timing", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--w", type=int, default=1920); ap.add_argument("--h", type=int, default=1080)
    ap.add_argument("--tail", type=float, default=0.6)
    # vertical cuts need bigger type placed lower than the 16:9 default
    ap.add_argument("--fs", type=int, default=0, help="font size override (0 = W*0.030)")
    ap.add_argument("--yfrac", type=float, default=0.80,
                    help="vertical centre of the text block as a fraction of H")
    a = ap.parse_args()
    lines = json.load(open(a.timing))["lines"]
    vdur = probe_dur(a.base)
    tmp = os.path.join(os.path.dirname(a.out), "_kar_png"); os.makedirs(tmp, exist_ok=True)

    inputs = ["-i", a.base]; fc = []; prev = "0:v"; n = 1; used = 0
    for i, ln in enumerate(lines):
        s, e, text = float(ln["s"]), float(ln["e"]), ln["text"]
        if s >= vdur - 0.5: continue
        e = min(e, vdur - 0.2)
        D = max(0.5, e - s)
        clip = D + a.tail
        wp = os.path.join(tmp, f"w{i:02d}.png"); gp = os.path.join(tmp, f"g{i:02d}.png")
        bw, bh = render_pair(text, wp, gp, a.w, a.h, a.fs or None)
        X = (a.w - bw)//2; Y = int(a.h*a.yfrac) - bh//2
        inputs += ["-loop","1","-t",f"{clip:.2f}","-i", wp,
                   "-loop","1","-t",f"{clip:.2f}","-i", gp]
        wi, gi = n, n+1; n += 2
        fc.append(f"[{wi}:v]fps={FPS},format=rgba[w{i}]")
        fc.append(f"[{gi}:v]fps={FPS},format=rgba[g{i}]")
        fc.append(f"[w{i}][g{i}]xfade=transition=wiperight:duration={D:.2f}:offset=0,format=rgba,setpts=PTS+{s:.2f}/TB[k{i}]")
        # vis_s: hold the line off screen until its beat is up, WITHOUT moving the sweep.
        # A line whose vocal starts under a title card must appear part-filled — the gold
        # is a record of what has already been sung, so re-anchoring it would be a lie.
        vis = max(s, float(ln.get("vis_s", s)))
        fc.append(f"[{prev}][k{i}]overlay={X}:{Y}:eof_action=pass:enable='between(t,{vis:.2f},{s+clip:.2f})'[b{i}]")
        prev = f"b{i}"; used += 1
    cmd = ["ffmpeg","-y"] + inputs + ["-filter_complex",";".join(fc),
           "-map",f"[{prev}]","-map","0:a",
           "-c:v","libx264","-preset","medium","-crf","19","-pix_fmt","yuv420p",
           "-c:a","copy","-movflags","+faststart","-t",f"{vdur:.3f}", a.out]
    print(f"karaoke overlay: {used} lines...")
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.stderr.write(p.stderr[-2000:]); raise SystemExit("karaoke overlay failed")
    print(">> DONE", a.out, f"{probe_dur(a.out):.1f}s")

if __name__ == "__main__":
    main()
