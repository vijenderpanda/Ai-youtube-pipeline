#!/usr/bin/env python3
"""Render Poly word-cards (rounded panel + simple flag + word + romanization) as transparent PNGs."""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

WORDF = ["/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
         "/Library/Fonts/Arial Rounded Bold.ttf",
         "/System/Library/Fonts/SFNSRounded.ttf", "/System/Library/Fonts/SFCompactRounded.ttf"]
ROMANF = ["/System/Library/Fonts/SFNSRounded.ttf", "/System/Library/Fonts/SFCompactRounded.ttf",
          "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"]
DEVAF = ["/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc",
         "/System/Library/Fonts/Kohinoor.ttc", "/Library/Fonts/ITFDevanagari.ttc"]

TEAL=(47,182,168); INK=(43,58,66); GRAY=(107,122,130); CREAM=(255,248,236)

def font(size, cands):
    for p in cands:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: pass
    return ImageFont.load_default()

def fit(text, cands, maxw, start=90, mn=42):
    s=start
    while s>mn:
        f=font(s,cands)
        if f.getbbox(text)[2] <= maxw: return f
        s-=3
    return font(mn,cands)

def flag(kind,w,h):
    im=Image.new("RGBA",(w,h),(255,255,255,255)); d=ImageDraw.Draw(im)
    if kind=="es":
        d.rectangle([0,0,w,h*0.25],fill=(198,11,30)); d.rectangle([0,h*0.25,w,h*0.75],fill=(255,196,0)); d.rectangle([0,h*0.75,w,h],fill=(198,11,30))
    elif kind=="fr":
        d.rectangle([0,0,w/3,h],fill=(0,85,164)); d.rectangle([2*w/3,0,w,h],fill=(239,65,53))
    elif kind=="de":
        d.rectangle([0,0,w,h/3],fill=(20,20,20)); d.rectangle([0,h/3,w,2*h/3],fill=(221,0,0)); d.rectangle([0,2*h/3,w,h],fill=(255,206,0))
    elif kind=="in":
        d.rectangle([0,0,w,h/3],fill=(255,153,51)); d.rectangle([0,2*h/3,w,h],fill=(19,136,8))
        cx,cy,r=w/2,h/2,h*0.15; d.ellipse([cx-r,cy-r,cx+r,cy+r],outline=(0,0,128),width=3)
    elif kind=="globe":
        d.ellipse([2,2,w-2,h-2],fill=(126,200,227)); d.ellipse([w*0.12,h*0.22,w*0.48,h*0.55],fill=(126,190,120)); d.ellipse([w*0.5,h*0.5,w*0.86,h*0.86],fill=(126,190,120))
    mask=Image.new("L",(w,h),0); ImageDraw.Draw(mask).rounded_rectangle([0,0,w-1,h-1],radius=12,fill=255)
    im.putalpha(mask); d=ImageDraw.Draw(im); d.rounded_rectangle([1,1,w-2,h-2],radius=12,outline=INK,width=3)
    return im

def make_card(word, roman, kind, out, deva=None):
    W,H=880,240; pad=30
    card=Image.new("RGBA",(W,H),(0,0,0,0))
    sh=Image.new("RGBA",(W,H),(0,0,0,0))
    ImageDraw.Draw(sh).rounded_rectangle([pad,pad+9,W-pad+6,H-pad+11],radius=40,fill=(0,0,0,95))
    card=Image.alpha_composite(card, sh.filter(ImageFilter.GaussianBlur(11)))
    d=ImageDraw.Draw(card)
    d.rounded_rectangle([pad,pad,W-pad,H-pad],radius=38,fill=CREAM+(248,),outline=TEAL,width=6)
    fw,fh=152,110; fy=(H-fh)//2
    card.alpha_composite(flag(kind,fw,fh),(pad+26,fy))
    tx=pad+26+fw+34; maxw=(W-pad)-tx-14
    wf=fit(word,WORDF,maxw)
    wy = 62 if roman else 78
    d.text((tx,wy),word,font=wf,fill=INK)
    if roman:
        d.text((tx,152),roman,font=font(44,ROMANF),fill=GRAY)
    if deva:
        df=font(40,DEVAF)
        d.text((W-pad-14-df.getbbox(deva)[2], 44), deva, font=df, fill=TEAL)
    card.save(out); return card

if __name__=="__main__":
    out="channels/language-abc/assets/cards"; os.makedirs(out,exist_ok=True)
    make_card("Hello!","",       "globe", f"{out}/card_hello.png")
    make_card("¡Hola!","OH-lah", "es",    f"{out}/card_hola.png")
    make_card("Bonjour","bon-ZHOOR","fr", f"{out}/card_bonjour.png")
    make_card("Hallo","HAH-loh", "de",    f"{out}/card_hallo.png")
    make_card("Namaste","nuh-muh-STAY","in", f"{out}/card_namaste.png", deva="नमस्ते")
    print("cards rendered:", os.listdir(out))
