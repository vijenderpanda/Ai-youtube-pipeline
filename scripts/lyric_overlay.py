#!/usr/bin/env python3
"""
Overlay romanized lyric lower-thirds (PNG via PIL) onto a finished cut.
Timing comes from a JSON: {"lines":[{"t":sec,"text":"..."}]}.
Second-pass only (no re-render of the base montage), so timing is cheap to iterate.

Usage:
  python3 scripts/lyric_overlay.py --base base_cut_1080.mp4 --timing timing.json --out final.mp4
          [--w 1920 --h 1080 --hold 6 --min 2.5]
"""
import argparse, json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

FONTS = [
    "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/System/Library/Fonts/Supplemental/Palatino.ttc",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]
def load_font(size):
    for f in FONTS:
        if os.path.exists(f):
            try: return ImageFont.truetype(f, size)
            except Exception: pass
    return ImageFont.load_default()

def render_png(text, path, W, H):
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    d = ImageDraw.Draw(img)
    fs = max(34, int(W*0.030))
    font = load_font(fs)
    # measure
    bb = d.textbbox((0,0), text, font=font)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    y = int(H*0.80)
    x = (W - tw)//2
    # soft scrim band behind text for legibility
    band_h = int(th*3.2); band_y = y - int(th*1.0)
    scrim = Image.new("RGBA",(W,band_h),(0,0,0,0))
    sd = ImageDraw.Draw(scrim)
    for i in range(band_h):
        a = int(120 * (1 - abs(i-band_h/2)/(band_h/2))**1.3)
        sd.line([(0,i),(W,i)], fill=(0,0,0,a))
    img.alpha_composite(scrim,(0,band_y))
    # shadow + text
    for dx,dy in [(0,3),(3,0),(0,-2),(-2,0),(2,2),(-2,2)]:
        d.text((x+dx,y+dy), text, font=font, fill=(0,0,0,190))
    d.text((x,y), text, font=font, fill=(255,244,248,255))
    img.save(path)

def probe_dur(path):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                        "-of","default=nw=1:nk=1",path],capture_output=True,text=True)
    return float(r.stdout.strip())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--timing", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--w", type=int, default=1920)
    ap.add_argument("--h", type=int, default=1080)
    ap.add_argument("--hold", type=float, default=6.0)
    ap.add_argument("--min", type=float, default=2.5)
    a = ap.parse_args()
    lines = json.load(open(a.timing))["lines"]
    vdur = probe_dur(a.base)
    tmp = os.path.join(os.path.dirname(a.out), "_lyr_png"); os.makedirs(tmp, exist_ok=True)
    items=[]
    for i,ln in enumerate(lines):
        s = float(ln["t"])
        nxt = float(lines[i+1]["t"]) if i+1 < len(lines) else vdur
        e = min(s + a.hold, nxt - 0.15, vdur)
        if e - s < a.min: e = min(s + a.min, vdur)
        png = os.path.join(tmp, f"l{i:02d}.png")
        render_png(ln["text"], png, a.w, a.h)
        items.append((png, s, e))
    # build ffmpeg overlay chain
    cmd=["ffmpeg","-y","-i",a.base]
    for png,_,_ in items: cmd += ["-i", png]
    fc=[]; prev="0:v"
    for k,(png,s,e) in enumerate(items, start=1):
        lbl=f"o{k}"
        fc.append(f"[{prev}][{k}:v]overlay=0:0:enable='between(t,{s:.2f},{e:.2f})'[{lbl}]")
        prev=lbl
    cmd += ["-filter_complex",";".join(fc),"-map",f"[{prev}]","-map","0:a",
            "-c:v","libx264","-preset","medium","-crf","19","-pix_fmt","yuv420p",
            "-c:a","copy","-movflags","+faststart",a.out]
    print(f"overlaying {len(items)} lyric lines...")
    p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode!=0:
        sys.stderr.write(p.stderr[-1500:]); raise SystemExit("overlay failed")
    print(">> DONE", a.out, f"{probe_dur(a.out):.1f}s")

if __name__=="__main__":
    main()
