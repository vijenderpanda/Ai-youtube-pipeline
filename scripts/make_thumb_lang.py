#!/usr/bin/env python3
"""Build YouTube thumbnails for the Language channel from existing assets (no generation)."""
import os, sys
sys.path.insert(0, "scripts")
from word_cards import flag, font, WORDF, TEAL, INK, CREAM
CORAL = (255, 122, 90)
from PIL import Image, ImageDraw, ImageFilter

W, H = 1280, 720
POLY = "channels/language-abc/assets/character/poly_cut.png"
OUT = "channels/language-abc/assets/thumbnail"
os.makedirs(OUT, exist_ok=True)

def grad(top, bot):
    g = Image.new("RGB", (W, H)); d = ImageDraw.Draw(g)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(top[i]*(1-t)+bot[i]*t) for i in range(3)))
    return g.convert("RGBA")

def sun_clouds(im):
    d = ImageDraw.Draw(im, "RGBA")
    d.ellipse([60, 40, 190, 170], fill=(255, 224, 130, 255))        # sun
    for cx, cy, s in [(980, 120, 1.0), (1120, 220, 0.8), (760, 90, 0.7)]:
        for dx, dy, r in [(0, 0, 46), (52, 6, 40), (-46, 8, 38), (24, -22, 34)]:
            d.ellipse([cx+dx*s-r*s, cy+dy*s-r*s, cx+dx*s+r*s, cy+dy*s+r*s], fill=(255, 255, 255, 230))
    return im

def big(d, xy, text, f, fill, sw=10, stroke=(255, 255, 255)):
    x, y = xy
    d.text((x+7, y+9), text, font=f, fill=(40, 55, 62))  # shadow
    d.text((x, y), text, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke)

def chip(word, kind, cw=300):
    ch = 96; im = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([2, 2, cw-2, ch-2], radius=28, fill=CREAM+(255,), outline=TEAL, width=5)
    fw, fh = 78, 54; im.alpha_composite(flag(kind, fw, fh), (20, (ch-fh)//2))
    f = font(46, WORDF)
    while f.getbbox(word)[2] > cw-120: f = font(f.size-2, WORDF)
    d.text((20+fw+16, (ch-f.getbbox(word)[3])//2 - 6), word, font=f, fill=INK)
    return im

def poly_img(h):
    p = Image.open(POLY); return p.resize((int(p.width*h/p.height), h))

def variant_A():
    im = sun_clouds(grad((174, 224, 230), (255, 247, 232)))
    d = ImageDraw.Draw(im, "RGBA")
    p = poly_img(560); im.alpha_composite(p, (10, 60))
    big(d, (560, 70), "HELLO!", font(190, WORDF), CORAL, sw=12)
    big(d, (566, 300), "in 5 languages", font(70, WORDF), TEAL, sw=6)
    chips = [("¡Hola!", "es"), ("Bonjour", "fr"), ("Hallo", "de"), ("Namaste", "in")]
    x = 20
    for w_, k in chips:
        c = chip(w_, k, 305); im.alpha_composite(c, (x, H-118)); x += 315
    im.convert("RGB").save(f"{OUT}/thumb_A.jpg", quality=92)

def variant_B():
    im = sun_clouds(grad((255, 214, 158), (255, 247, 232)))
    d = ImageDraw.Draw(im, "RGBA")
    p = poly_img(600); im.alpha_composite(p, (W-p.width-10, 70))
    big(d, (60, 66), "SAY", font(120, WORDF), TEAL, sw=9)
    big(d, (60, 190), "HELLO!", font(200, WORDF), CORAL, sw=12)
    for i, (w_, k) in enumerate([("¡Hola!", "es"), ("Bonjour", "fr"), ("Hallo", "de"), ("Namaste", "in")]):
        c = chip(w_, k, 300); im.alpha_composite(c, (60 + (i % 2)*315, 452 + (i//2)*116))
    im.convert("RGB").save(f"{OUT}/thumb_B.jpg", quality=92)

if __name__ == "__main__":
    variant_A(); variant_B()
    # side-by-side compare
    a = Image.open(f"{OUT}/thumb_A.jpg"); b = Image.open(f"{OUT}/thumb_B.jpg")
    cmp = Image.new("RGB", (W, H*2+12), (20, 20, 20))
    cmp.paste(a, (0, 0)); cmp.paste(b, (0, H+12)); cmp.save(f"{OUT}/thumb_compare.jpg", quality=90)
    print("thumbnails:", os.listdir(OUT))
