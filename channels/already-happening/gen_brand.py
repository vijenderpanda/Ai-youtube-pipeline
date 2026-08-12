#!/usr/bin/env python3
"""gen_brand.py — channel icon + banner for "Already Happening".
Icon = "Horizon Signal" mark (double up-chevron breaking a horizon line), reads
at 32px. Banner = dark electric-teal cinematic gradient + faint motif + wordmark.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

TEAL=(34,211,238); HI=(107,245,228); BG=(10,15,20)
OUT="channels/already-happening/assets/brand"
import os; os.makedirs(OUT,exist_ok=True)

def font(sz,bold=True):
    for p in (["/System/Library/Fonts/Supplemental/Arial Bold.ttf"] if bold else ["/System/Library/Fonts/Supplemental/Arial.ttf"]):
        if os.path.exists(p):
            try: return ImageFont.truetype(p,sz)
            except: pass
    return ImageFont.load_default()

def radial(w,h,cx,cy,inner,outer,r):
    yy,xx=np.mgrid[0:h,0:w]
    dist=np.sqrt(((xx-cx)/w)**2+((yy-cy)/h)**2)/r
    t=np.clip(dist,0,1)[...,None]
    return (np.array(inner)*(1-t)+np.array(outer)*t).astype('uint8')

def chevron(d,cx,apex_y,half,drop,w,col):
    d.line([(cx-half,apex_y+drop),(cx,apex_y),(cx+half,apex_y+drop)],fill=col,width=w,joint="curve")
    r=w//2
    for px,py in [(cx-half,apex_y+drop),(cx+half,apex_y+drop),(cx,apex_y)]:
        d.ellipse([px-r,py-r,px+r,py+r],fill=col)

def icon():
    S=800
    base=Image.fromarray(radial(S,S,S*0.5,S*0.42,(16,26,32),BG,1.15),"RGB").convert("RGBA")
    glow=Image.new("RGBA",(S,S),(0,0,0,0)); gd=ImageDraw.Draw(glow)
    mark=Image.new("RGBA",(S,S),(0,0,0,0)); md=ImageDraw.Draw(mark)
    # horizon line
    for dd in (gd,md):
        dd.line([(238,512),(562,512)],fill=TEAL+(255,),width=12)
    # double up-chevron
    for dd in (gd,md):
        chevron(dd,400,398,120,104,30,TEAL+(255,))
        chevron(dd,400,300,120,104,30,TEAL+(255,))
    # tips highlight
    for px,py in [(400,398),(400,300)]:
        md.ellipse([px-13,py-13,px+13,py+13],fill=HI+(255,))
    glow=glow.filter(ImageFilter.GaussianBlur(22))
    out=Image.alpha_composite(base,glow); out=Image.alpha_composite(out,mark)
    out.convert("RGB").save(f"{OUT}/icon.png",quality=95)
    # circular preview @ 160
    prev=out.resize((160,160)); m=Image.new("L",(160,160),0); ImageDraw.Draw(m).ellipse([0,0,160,160],fill=255)
    circ=Image.new("RGBA",(160,160),(0,0,0,0)); circ.paste(prev,(0,0),m); circ.convert("RGB").save(f"{OUT}/icon_circle160.png")
    print("icon.png + preview")

def draw_tracked(d,cx,y,text,f,fill,track):
    widths=[d.textlength(c,font=f)+track for c in text]; total=sum(widths)-track
    x=cx-total/2
    for c,w in zip(text,widths):
        d.text((x+2,y+3),c,font=f,fill=(0,0,0,160)); d.text((x,y),c,font=f,fill=fill); x+=w

def banner():
    W,H=2560,1440
    base=Image.fromarray(radial(W,H,W*0.5,H*0.92,(14,30,36),(6,10,14),1.25),"RGB").convert("RGBA")
    # faint big horizon-chevron motif, right-of-center, low opacity
    motif=Image.new("RGBA",(W,H),(0,0,0,0)); mo=ImageDraw.Draw(motif)
    mo.line([(W*0.30,H*0.62),(W*0.70,H*0.62)],fill=TEAL+(40,),width=8)
    chevron(mo,int(W*0.5),int(H*0.30),260,220,26,TEAL+(38,)); chevron(mo,int(W*0.5),int(H*0.10),260,220,26,TEAL+(30,))
    motif=motif.filter(ImageFilter.GaussianBlur(3))
    im=Image.alpha_composite(base,motif); d=ImageDraw.Draw(im)
    # vignette
    vig=Image.new("L",(W,H),0); ImageDraw.Draw(vig).ellipse([-W*0.2,-H*0.35,W*1.2,H*1.35],fill=255)
    vig=vig.filter(ImageFilter.GaussianBlur(220)); dark=Image.new("RGBA",(W,H),(4,7,10,150))
    im=Image.composite(im,Image.alpha_composite(im,dark),vig)
    d=ImageDraw.Draw(im)
    cx=W//2
    # small mark above wordmark
    sm=Image.new("RGBA",(W,H),(0,0,0,0)); smd=ImageDraw.Draw(sm)
    chevron(smd,cx,int(H*0.40)-6,26,22,10,TEAL+(255,)); chevron(smd,cx,int(H*0.40)-28,26,22,10,TEAL+(255,))
    im=Image.alpha_composite(im,sm.filter(ImageFilter.GaussianBlur(0)))
    d=ImageDraw.Draw(im)
    draw_tracked(d,cx,int(H*0.44),"ALREADY HAPPENING",font(118),(238,242,246,255),10)
    draw_tracked(d,cx,int(H*0.575),"THE NEAR FUTURE — ALREADY HERE",font(44),(150,162,172,255),6)
    # schedule chip
    sch="NEW SHORTS   ·   TUE / WED / THU"
    f2=font(40); tw=sum(d.textlength(c,font=f2)+4 for c in sch)-4
    d.rounded_rectangle([cx-tw/2-34,int(H*0.66)-8,cx+tw/2+34,int(H*0.66)+64],radius=36,outline=TEAL+(255,),width=3)
    draw_tracked(d,cx,int(H*0.66),sch,f2,TEAL+(255,),4)
    im.convert("RGB").save(f"{OUT}/banner.png",quality=92)
    print("banner.png")

icon(); banner()
