#!/usr/bin/env python3
"""Render the title card, then overlay all word-cards (timed, faded, corner-placed) onto the episode.
Efficient: each card is a FINITE input that exists only during its window (delayed via setpts),
so ffmpeg doesn't process 6 full-length streams. preset veryfast."""
import subprocess, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def font(size, cands):
    for p in cands:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: pass
    return ImageFont.load_default()

WORDF = ["/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf", "/System/Library/Fonts/SFNSRounded.ttf"]
TEAL=(47,182,168); INK=(43,58,66); CORAL=(255,122,90); CREAM=(255,248,236)

def globe(w,h):
    im=Image.new("RGBA",(w,h),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.ellipse([2,2,w-2,h-2],fill=(126,200,227),outline=INK,width=3)
    d.ellipse([w*0.12,h*0.22,w*0.48,h*0.55],fill=(126,190,120)); d.ellipse([w*0.5,h*0.5,w*0.86,h*0.86],fill=(126,190,120))
    m=Image.new("L",(w,h),0); ImageDraw.Draw(m).ellipse([0,0,w-1,h-1],fill=255); im.putalpha(m)
    return im

def title_card(out):
    W,H=1040,300; pad=30
    card=Image.new("RGBA",(W,H),(0,0,0,0))
    sh=Image.new("RGBA",(W,H),(0,0,0,0)); ImageDraw.Draw(sh).rounded_rectangle([pad,pad+10,W-pad+6,H-pad+12],radius=44,fill=(0,0,0,95))
    card=Image.alpha_composite(card, sh.filter(ImageFilter.GaussianBlur(12)))
    d=ImageDraw.Draw(card)
    d.rounded_rectangle([pad,pad,W-pad,H-pad],radius=42,fill=CREAM+(250,),outline=TEAL,width=7)
    card.alpha_composite(globe(122,122),(pad+34,(H-122)//2))
    tx=pad+34+122+30
    d.text((tx,78),"Hello Around the World",font=font(60,WORDF),fill=INK)
    d.text((tx,162),"Say Hello in 5 Languages!",font=font(38,WORDF),fill=CORAL)
    card.save(out)

C="channels/language-abc/assets/cards/"
title_card(C+"card_title.png"); print("title card rendered")

V="channels/language-abc/renders/ep01_motion_full.mp4"
OUT="channels/language-abc/renders/ep01_final.mp4"
# (png, start, end, x, width)
cards=[("card_title.png",1.5,9.0,440,1040),
       ("card_hello.png",13,20,46,660),
       ("card_hola.png",21,30.5,1214,660),
       ("card_bonjour.png",32,41.5,46,660),
       ("card_hallo.png",43,52.5,1214,660),
       ("card_namaste.png",54,63.5,1214,660)]
cmd=["ffmpeg","-y","-i",V]
for png,st,en,x,w in cards:
    cmd+=["-loop","1","-t",f"{en-st:.2f}","-i",C+png]     # finite: only its own window
parts=[]
for i,(png,st,en,x,w) in enumerate(cards,start=1):
    dur=en-st
    parts.append(f"[{i}:v]fps=30,scale={w}:-1,format=rgba,"
                 f"fade=t=in:st=0:d=0.4:alpha=1,fade=t=out:st={dur-0.4:.2f}:d=0.4:alpha=1,"
                 f"setpts=PTS+{st}/TB[c{i}]")
prev="0:v"
for i,(png,st,en,x,w) in enumerate(cards,start=1):
    o="vout" if i==len(cards) else f"b{i}"
    parts.append(f"[{prev}][c{i}]overlay={x}:40:eof_action=pass:repeatlast=0[{o}]")
    prev=o
cmd+=["-filter_complex",";".join(parts),"-map","[vout]","-map","0:a",
      "-c:v","libx264","-crf","20","-preset","veryfast","-pix_fmt","yuv420p","-c:a","copy",OUT]
print("overlaying cards (veryfast)...")
subprocess.run(cmd,check=True)
print("DONE",OUT)
