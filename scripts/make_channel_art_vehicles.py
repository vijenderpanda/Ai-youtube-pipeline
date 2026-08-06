#!/usr/bin/env python3
"""Rumble Trucks channel art: banner (2560x1440, wordmark in center safe area) + avatar (800x800, Rev's face)."""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

CH = "channels/vehicles"
OUT = f"{CH}/assets/channel"; os.makedirs(OUT, exist_ok=True)
TOWN = f"{CH}/assets/scenes/rt_town_0.jpg"
REV = f"{CH}/assets/character/canonical/rev_master.jpg"

FONTS = ["/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
         "/System/Library/Fonts/SFNSRounded.ttf",
         "/System/Library/Fonts/Supplemental/Arial Bold.ttf"]
RED=(214,45,40); CORAL=(255,110,70); YELLOW=(255,205,55); INK=(28,24,26); CREAM=(255,249,235)

def font(sz):
    for p in FONTS:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, sz)
            except Exception: pass
    return ImageFont.load_default()

def cover(img, W, H):
    iw, ih = img.size; s = max(W/iw, H/ih)
    img = img.resize((int(iw*s), int(ih*s)))
    x = (img.width-W)//2; y = (img.height-H)//2
    return img.crop((x, y, x+W, y+H))

def cut(src, thresh=62):
    im = Image.open(src).convert("RGB"); w, h = im.size; SENT = (7,254,3)
    for s in [(1,1),(w-2,1),(1,h-2),(w-2,h-2),(w//2,1),(1,h//2),(w-2,h//2),(w//2,h-2)]:
        try: ImageDraw.floodfill(im, s, SENT, thresh=thresh)
        except Exception: pass
    rgba = im.convert("RGBA"); px = rgba.load()
    for y in range(h):
        for x in range(w):
            if px[x,y][:3] == SENT: px[x,y] = (0,0,0,0)
    bb = rgba.getbbox(); return rgba.crop(bb) if bb else rgba

def radial(size, inner, outer):
    img = Image.new("RGB", (size, size)); px = img.load()
    cx = cy = size/2; maxr = (cx*cx+cy*cy)**0.5
    for y in range(size):
        for x in range(size):
            r = ((x-cx)**2+(y-cy)**2)**0.5/maxr
            px[x,y] = tuple(int(inner[i]*(1-r)+outer[i]*r) for i in range(3))
    return img

def banner():
    W, H = 2560, 1440
    img = cover(Image.open(TOWN).convert("RGB"), W, H)
    # soft dark scrim behind the wordmark, kept inside the center safe area
    ov = Image.new("RGBA", (W, H), (0,0,0,0)); d = ImageDraw.Draw(ov)
    pw, ph = 1620, 470; x0, y0 = (W-pw)//2, int(H*0.5-ph/2)
    d.rounded_rectangle([x0, y0, x0+pw, y0+ph], radius=80, fill=(20,16,22,135))
    ov = ov.filter(ImageFilter.GaussianBlur(38))
    img = Image.alpha_composite(img.convert("RGBA"), ov)
    # Rev peeking in the bottom-left desktop-only margin
    rev = cut(REV); rh = 380; rp = rev.resize((int(rev.width*rh/rev.height), rh))
    img.alpha_composite(rp, (36, H-rh-24))
    img = img.convert("RGB"); d = ImageDraw.Draw(img); cx = W//2
    d.text((cx, int(H*0.44)), "RUMBLE TRUCKS", font=font(190), fill=CREAM,
           anchor="mm", stroke_width=10, stroke_fill=(150,26,22))
    d.text((cx, int(H*0.565)), "High-energy truck songs for kids!", font=font(70),
           fill=YELLOW, anchor="mm", stroke_width=6, stroke_fill=INK)
    img.save(f"{OUT}/banner_final.jpg", quality=92)
    print(">> saved banner_final.jpg", img.size)

def avatar():
    S = 800
    bg = radial(S, (206,232,250), (120,186,226)).convert("RGBA")
    rev = cut(REV); rw = 730; rp = rev.resize((rw, int(rev.height*rw/rev.width)))
    # center Rev's face (~32% down the cutout) near the visual center of the circle
    face_y = int(0.32*rp.height); y = int(0.46*S) - face_y
    bg.alpha_composite(rp, ((S-rw)//2, y))
    bg.convert("RGB").save(f"{OUT}/avatar_final.jpg", quality=92)
    print(">> saved avatar_final.jpg", (S,S))

if __name__ == "__main__":
    banner(); avatar()
