#!/usr/bin/env python3
"""Generate Aashiqana channel art: long-form thumbnail (1280x720) + banner (2560x1440)."""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = "channels/aashiqana/songs/01-baarish-aur-tum"
OUT = "channels/aashiqana/brand"; os.makedirs(OUT, exist_ok=True)
FB = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
FI = "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"
FR = "/System/Library/Fonts/Supplemental/Georgia.ttf"
def font(path, size):
    try: return ImageFont.truetype(path, size)
    except Exception: return ImageFont.load_default()

def cover(img, W, H):
    iw, ih = img.size; s = max(W/iw, H/ih)
    img = img.resize((int(iw*s), int(ih*s)), Image.LANCZOS)
    x = (img.width-W)//2; y = (img.height-H)//2
    return img.crop((x, y, x+W, y+H))

def center_text(d, cx, y, text, fnt, fill, shadow=(0,0,0,200), so=3):
    bb = d.textbbox((0,0), text, font=fnt); w = bb[2]-bb[0]
    x = cx - w//2
    for dx,dy in [(so,so),(-so,so),(so,-so),(-so,-so),(0,so),(0,-so)]:
        d.text((x+dx,y+dy), text, font=fnt, fill=shadow)
    d.text((x,y), text, font=fnt, fill=fill); return w

# ---- Thumbnail 1280x720 ----
W,H = 1280,720
bg = cover(Image.open(f"{BASE}/scenes/scene_rooftop_1.jpg").convert("RGB"), W, H)
ov = Image.new("RGBA",(W,H),(0,0,0,0)); od = ImageDraw.Draw(ov)
# bottom gradient scrim
for i in range(H):
    a = int(200 * max(0,(i-H*0.35)/(H*0.65))**1.4)
    od.line([(0,i),(W,i)], fill=(10,4,12,a))
th = Image.alpha_composite(bg.convert("RGBA"), ov)
d = ImageDraw.Draw(th)
center_text(d, W//2, H-235, "BAARISH", font(FB,120), (255,246,250,255))
center_text(d, W//2, H-120, "AUR TUM", font(FB,120), (255,214,232,255))
center_text(d, W//2, H-285, "— A rain love song —", font(FI,40), (240,220,230,255), so=2)
th.convert("RGB").save(f"{OUT}/thumb_baarish.jpg", quality=92)

# ---- Banner 2560x1440 (safe area 1546x423 centered) ----
W,H = 2560,1440
bg = cover(Image.open(f"{BASE}/scenes/scene_hills_1.jpg").convert("RGB"), W, H)
bg = bg.filter(ImageFilter.GaussianBlur(3))
ov = Image.new("RGBA",(W,H),(0,0,0,0)); od = ImageDraw.Draw(ov)
od.rectangle([0,0,W,H], fill=(8,4,12,120))
# darken center band for text
cy = H//2
for i in range(H):
    a = int(150 * max(0,1-abs(i-cy)/(H*0.30)))
    od.line([(0,i),(W,i)], fill=(8,4,12,a))
bn = Image.alpha_composite(bg.convert("RGBA"), ov)
d = ImageDraw.Draw(bn)
center_text(d, W//2, cy-150, "Aashiqana", font(FB,190), (255,246,250,255))
center_text(d, W//2, cy+70, "Original Hindi Love Songs", font(FI,64), (255,222,236,255), so=2)
center_text(d, W//2, cy+150, "New romantic melodies every week", font(FR,44), (225,215,225,255), so=2)
bn.convert("RGB").save(f"{OUT}/banner.jpg", quality=90)
print("saved", f"{OUT}/thumb_baarish.jpg", "and", f"{OUT}/banner.jpg")
