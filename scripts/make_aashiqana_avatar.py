#!/usr/bin/env python3
"""Aashiqana channel avatars (1024x1024, circle-safe). 3 variants."""
import os, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = "channels/aashiqana/brand"; os.makedirs(OUT, exist_ok=True)
FB = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
FR = "/System/Library/Fonts/Supplemental/Georgia.ttf"
S = 1024
GOLD = (232,195,106); ROSE = (244,198,218); CREAM=(255,246,250)
def f(p,s):
    try: return ImageFont.truetype(p,s)
    except Exception: return ImageFont.load_default()

def grad(c1,c2,c3):
    img = Image.new("RGB",(S,S),c1); d=ImageDraw.Draw(img)
    for y in range(S):
        t=y/S
        if t<0.5:
            k=t/0.5; c=tuple(int(c1[i]+(c2[i]-c1[i])*k) for i in range(3))
        else:
            k=(t-0.5)/0.5; c=tuple(int(c2[i]+(c3[i]-c2[i])*k) for i in range(3))
        d.line([(0,y),(S,y)],fill=c)
    return img

def ring(d, col=GOLD, w=10, pad=40):
    d.ellipse([pad,pad,S-pad,S-pad], outline=col, width=w)

def ctext(d,cx,y,txt,fnt,fill,so=4,track=0):
    if track:
        # letter-spaced
        widths=[d.textlength(ch,font=fnt) for ch in txt]
        tot=sum(widths)+track*(len(txt)-1); x=cx-tot/2
        for ch,wd in zip(txt,widths):
            for dx,dy in [(so,so),(-so,so),(so,-so),(-so,-so)]:
                d.text((x+dx,y+dy),ch,font=fnt,fill=(0,0,0,160))
            d.text((x,y),ch,font=fnt,fill=fill); x+=wd+track
        return
    bb=d.textbbox((0,0),txt,font=fnt); w=bb[2]-bb[0]; x=cx-w//2
    for dx,dy in [(so,so),(-so,so),(so,-so),(-so,-so),(0,so)]:
        d.text((x+dx,y+dy),txt,font=fnt,fill=(0,0,0,170))
    d.text((x,y),txt,font=fnt,fill=fill)

def umbrella(d,cx,cy,w,col=GOLD):
    r=w//2
    d.pieslice([cx-r,cy-r,cx+r,cy+r],180,360,fill=col)  # dome
    # ribs
    for a in range(0,5):
        x=cx-r + a*(w//4)
        d.line([(cx,cy-r),(x,cy)],fill=(120,80,40),width=3)
    d.line([(cx,cy-r),(cx,cy)],fill=(120,80,40),width=3)
    # pole + hook
    d.line([(cx,cy-r),(cx,cy+r)],fill=col,width=10)
    d.arc([cx-30,cy+r-20,cx+2,cy+r+20],0,120,fill=col,width=10)
    # rain
    for i,x in enumerate(range(cx-r+30,cx+r-10,40)):
        yy=cy+30+(i%2)*18
        d.line([(x,yy),(x-8,yy+34)],fill=ROSE,width=5)

# Variant 1: A monogram
img=grad((36,12,40),(120,28,82),(190,90,60)); d=ImageDraw.Draw(img,"RGBA")
ring(d)
ctext(d,S//2,S//2-260,"A",f(FB,560),GOLD,so=6)
ctext(d,S//2,S-215,"AASHIQANA",f(FR,74),CREAM,so=3,track=10)
img.save(f"{OUT}/avatar_A.png")

# Variant 2: umbrella motif
img=grad((30,14,44),(96,30,92),(210,120,70)); d=ImageDraw.Draw(img,"RGBA")
ring(d, col=ROSE, w=8)
umbrella(d,S//2,S//2-70,360,GOLD)
ctext(d,S//2,S-235,"AASHIQANA",f(FB,86),CREAM,so=4,track=8)
img.save(f"{OUT}/avatar_umbrella.png")

# Variant 3: couple photo crop + ring + wordmark
def cover(im,W,H):
    iw,ih=im.size; s=max(W/iw,H/ih); im=im.resize((int(iw*s),int(ih*s)),Image.LANCZOS)
    x=(im.width-W)//2; y=int((im.height-H)*0.30)
    return im.crop((x,y,x+W,y+H))
photo=cover(Image.open("channels/aashiqana/songs/01-baarish-aur-tum/characters/couple_twoshot_0.jpg").convert("RGB"),S,S)
ov=Image.new("RGBA",(S,S),(0,0,0,0)); od=ImageDraw.Draw(ov)
for y in range(S):
    a=int(210*max(0,(y-S*0.5)/(S*0.5))**1.3); od.line([(0,y),(S,y)],fill=(20,6,20,a))
img=Image.alpha_composite(photo.convert("RGBA"),ov); d=ImageDraw.Draw(img,"RGBA")
ring(d, col=GOLD, w=12, pad=26)
ctext(d,S//2,S-210,"AASHIQANA",f(FB,84),CREAM,so=4,track=8)
img.convert("RGB").save(f"{OUT}/avatar_photo.jpg",quality=92)
print("saved avatar_A.png, avatar_umbrella.png, avatar_photo.jpg")
