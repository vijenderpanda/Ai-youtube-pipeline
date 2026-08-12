#!/usr/bin/env python3
"""Generic connected-motion Short assembler.
Cross-dissolves an ordered list of motion clips over a word-first hookcut, with
bilingual Kohinoor lyric cards. Reusable across songs.

  python assemble_motion_generic.py --clips a.mp4,b.mp4,c.mp4,d.mp4 \
      --audio hookcut.mp3 --lyrics timing.json --out short.mp4
"""
import argparse, json, os, subprocess, sys, tempfile
REPO = os.path.abspath(__file__)
while REPO != "/" and not os.path.isdir(os.path.join(REPO, ".git")):
    REPO = os.path.dirname(REPO)
os.chdir(REPO)
W, H = 1080, 1920

def probe(p):
    return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","csv=p=0",p],capture_output=True,text=True).stdout.strip())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", required=True, help="comma-separated clip paths, in order")
    ap.add_argument("--audio", required=True)
    ap.add_argument("--lyrics", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--xf", type=float, default=0.5)
    a = ap.parse_args()
    CLIPS = [c.strip() for c in a.clips.split(",")]
    for c in CLIPS:
        if not os.path.exists(c): sys.exit(f"missing clip {c}")
    XF = a.xf
    work = tempfile.mkdtemp(prefix="motiongen_")

    norm = []
    for i,c in enumerate(CLIPS):
        o = f"{work}/n{i}.mp4"
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",c,
            "-vf",f"scale={W}:-2:force_original_aspect_ratio=increase,crop={W}:{H},fps=30",
            "-an","-c:v","libx264","-crf","18","-pix_fmt","yuv420p",o],check=True)
        norm.append(o)
    durs=[probe(n) for n in norm]
    inputs=[]
    for n in norm: inputs+=["-i",n]
    fc=[]; prev="0:v"; offset=durs[0]-XF
    for i in range(1,len(norm)):
        lbl=f"x{i}"
        fc.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={XF}:offset={offset:.3f}[{lbl}]")
        prev=lbl; offset+=durs[i]-XF
    montage=f"{work}/montage.mp4"
    subprocess.run(["ffmpeg","-y","-loglevel","error"]+inputs+
        ["-filter_complex",";".join(fc),"-map",f"[{prev}]","-c:v","libx264","-crf","18",
         "-pix_fmt","yuv420p","-r","30",montage],check=True)
    mdur=probe(montage)

    from PIL import Image, ImageDraw, ImageFont
    def font(cands,size):
        for p in cands:
            if os.path.exists(p):
                try: return ImageFont.truetype(p,size)
                except: pass
        return None
    fhi=font(["/System/Library/Fonts/Kohinoor.ttc","/System/Library/Fonts/Supplemental/Kohinoor.ttc"],62)
    fro=font(["/System/Library/Fonts/Supplemental/Georgia Bold.ttf"],52)
    lines=json.load(open(a.lyrics))["lines"]
    def card(ln,idx):
        img=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(img)
        def ctr(t,ft,y,fill):
            if not t or not ft: return y
            bb=d.textbbox((0,0),t,font=ft,stroke_width=5); w=bb[2]-bb[0]
            d.text(((W-w)//2-bb[0],y),t,font=ft,fill=fill,stroke_width=5,stroke_fill=(0,0,0,235))
            return y+(bb[3]-bb[1])+16
        y=1350
        y=ctr(ln.get("hi",""),fhi,y,(255,255,255,255))
        ctr(ln.get("text",""),fro,y,(255,214,120,255))
        p=f"{work}/card{idx}.png"; img.save(p); return p
    cards=[(card(l,i),l) for i,l in enumerate(lines)]
    inp=["-i",montage]; fc=[]; prev="0:v"
    for i,(p,l) in enumerate(cards):
        inp+=["-i",p]
        fc.append(f"[{prev}][{i+1}:v]overlay=0:0:enable='between(t,{l['s']:.2f},{min(l['e'],mdur):.2f})'[v{i}]")
        prev=f"v{i}"
    capv=f"{work}/capped.mp4"
    subprocess.run(["ffmpeg","-y","-loglevel","error"]+inp+["-filter_complex",";".join(fc),
        "-map",f"[{prev}]","-c:v","libx264","-crf","18","-pix_fmt","yuv420p",capv],check=True)
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",capv,"-i",a.audio,
        "-map","0:v","-map","1:a","-c:v","copy","-c:a","aac","-b:a","192k",
        "-shortest","-movflags","+faststart",a.out],check=True)
    print(">> DONE",a.out,f"{probe(a.out):.2f}s")

if __name__=="__main__":
    main()
