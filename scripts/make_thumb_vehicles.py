#!/usr/bin/env python3
"""Rumble Trucks thumbnails from existing assets (cut Rev from his master + energy background)."""
import os
from PIL import Image, ImageDraw, ImageFont
W, H = 1280, 720
OUT = "channels/vehicles/assets/thumbnail"; os.makedirs(OUT, exist_ok=True)
WORDF = ["/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf", "/System/Library/Fonts/SFNSRounded.ttf"]
RED=(214,45,40); CORAL=(255,110,70); YELLOW=(255,205,55); INK=(40,36,38); SKY=(140,200,232)

def font(s):
    for p in WORDF:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, s)
            except Exception: pass
    return ImageFont.load_default()

def cut(src, thresh=62):
    im = Image.open(src).convert("RGB"); w, h = im.size
    SENT = (7, 254, 3)
    for s in [(1,1),(w-2,1),(1,h-2),(w-2,h-2),(w//2,1),(1,h//2),(w-2,h//2),(w//2,h-2)]:
        try: ImageDraw.floodfill(im, s, SENT, thresh=thresh)
        except Exception: pass
    rgba = im.convert("RGBA"); px = rgba.load()
    for y in range(h):
        for x in range(w):
            if px[x,y][:3] == SENT: px[x,y] = (0,0,0,0)
    bb = rgba.getbbox(); return rgba.crop(bb) if bb else rgba

def grad(top, bot):
    g = Image.new("RGB", (W, H)); d = ImageDraw.Draw(g)
    for y in range(H):
        t = y/H; d.line([(0,y),(W,y)], fill=tuple(int(top[i]*(1-t)+bot[i]*t) for i in range(3)))
    return g.convert("RGBA")

def dust(im, spots):
    d = ImageDraw.Draw(im, "RGBA")
    for cx, cy, s in spots:
        for dx, dy, r in [(0,0,64),(74,8,52),(-64,10,50),(32,-30,44)]:
            d.ellipse([cx+dx*s-r*s, cy+dy*s-r*s, cx+dx*s+r*s, cy+dy*s+r*s], fill=(255,255,255,225))
    return im

def big(d, xy, t, f, fill, sw=13, stroke=(255,255,255)):
    x, y = xy
    d.text((x+7, y+9), t, font=f, fill=(30,26,28)); d.text((x, y), t, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke)

rev = cut("channels/vehicles/assets/character/canonical/rev_master.jpg")
def revimg(h): return rev.resize((int(rev.width*h/rev.height), h))

def vA():
    im = dust(grad(SKY, (240,220,175)), [(1040,150,1.5),(210,140,1.2)])
    d = ImageDraw.Draw(im, "RGBA")
    p = revimg(560); im.alpha_composite(p, (0, 150))
    big(d, (600,100), "REV!", font(235), CORAL, 15)
    big(d, (606,365), "Monster Truck", font(82), RED, 8)
    d.rounded_rectangle([606,490,1010,568], radius=38, fill=YELLOW+(255,))
    d.text((634,502), "for KIDS", font=font(56), fill=INK)
    im.convert("RGB").save(f"{OUT}/thumb_A.jpg", quality=92)

def vB():
    im = dust(grad((255,178,92), (243,222,172)), [(960,545,1.6),(300,545,1.4)])
    d = ImageDraw.Draw(im, "RGBA")
    big(d, (56,34), "REV", font(150), RED, 12)
    big(d, (322,60), "the Monster Truck!", font(66), (55,52,62), 6)
    p = revimg(520); im.alpha_composite(p, ((W-p.width)//2, 195))
    im.convert("RGB").save(f"{OUT}/thumb_B.jpg", quality=92)

def bg_jump(src):
    im = Image.open(src).convert("RGB"); w, h = im.size; tgt = W/H
    if w/h > tgt:  # crop width
        nw = int(h*tgt); x0 = (w-nw)//2; im = im.crop((x0,0,x0+nw,h))
    else:          # crop height
        nh = int(w/tgt); y0 = (h-nh)//2; im = im.crop((0,y0,w,y0+nh))
    return im.resize((W,H)).convert("RGBA")

def fitfont(text, maxw, start=180, mins=40):
    tmp = ImageDraw.Draw(Image.new("RGB",(10,10)))
    s = start
    while s > mins:
        f = font(s)
        if tmp.textbbox((0,0), text, font=f)[2] <= maxw: return f
        s -= 4
    return font(mins)

def vC():
    # Action thumbnail: Rev mid-jump (matches title "Rev's Big Jump!"), headline in top-left sky
    im = bg_jump("channels/vehicles/assets/scenes/rev_jump_0.jpg")  # already has motion dust on the right
    d = ImageDraw.Draw(im, "RGBA")
    big(d, (48,24), "REV'S", fitfont("REV'S",240,96), RED, 9)
    big(d, (46,116), "BIG",  fitfont("BIG",440,168),  CORAL, 15)
    big(d, (46,286), "JUMP!", fitfont("JUMP!",440,168), CORAL, 15)
    d.rounded_rectangle([48,632,404,706], radius=37, fill=YELLOW+(255,))
    d.text((78,644), "for KIDS", font=font(54), fill=INK)
    im.convert("RGB").save(f"{OUT}/thumb_C.jpg", quality=92)

if __name__ == "__main__":
    vA(); vB(); vC()
    a = Image.open(f"{OUT}/thumb_A.jpg"); b = Image.open(f"{OUT}/thumb_B.jpg"); c3 = Image.open(f"{OUT}/thumb_C.jpg")
    c = Image.new("RGB", (W, H*3+24), (20,20,20)); c.paste(a,(0,0)); c.paste(b,(0,H+12)); c.paste(c3,(0,2*H+24)); c.save(f"{OUT}/thumb_compare.jpg", quality=90)
    print("cutout size:", rev.size, "| thumbs:", [f for f in os.listdir(OUT) if f.endswith('.jpg')])
