#!/usr/bin/env python3
"""Channel avatar + banner for 'Learn with Poly' from existing assets (no generation)."""
import os, sys
sys.path.insert(0, "scripts")
from word_cards import flag, font, WORDF, TEAL, INK, CREAM
from PIL import Image, ImageDraw
CORAL = (255, 122, 90)
OUT = "channels/language-abc/assets/channel"; os.makedirs(OUT, exist_ok=True)
POLY = "channels/language-abc/assets/character/poly_cut.png"

def grad(W, H, top, bot):
    g = Image.new("RGB", (W, H)); d = ImageDraw.Draw(g)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(top[i]*(1-t)+bot[i]*t) for i in range(3)))
    return g.convert("RGBA")

def clouds(im, spots):
    d = ImageDraw.Draw(im, "RGBA")
    for cx, cy, s in spots:
        for dx, dy, r in [(0, 0, 60), (70, 8, 52), (-62, 10, 50), (30, -30, 44)]:
            d.ellipse([cx+dx*s-r*s, cy+dy*s-r*s, cx+dx*s+r*s, cy+dy*s+r*s], fill=(255, 255, 255, 235))
    return im

def big(d, xy, t, f, fill, sw, stroke=(255, 255, 255)):
    x, y = xy
    d.text((x+6, y+8), t, font=f, fill=(40, 55, 62))
    d.text((x, y), t, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke)

def polyimg(h):
    p = Image.open(POLY); return p.resize((int(p.width*h/p.height), h))

# ---- AVATAR 800x800 (displays as a circle) ----
av = grad(800, 800, (174, 224, 230), (255, 247, 232))
d = ImageDraw.Draw(av, "RGBA")
for i, c in enumerate([(230, 80, 70), (240, 150, 60), (250, 205, 70), (120, 190, 120), (90, 150, 220)]):
    r = 520 - i*34
    d.arc([400-r, 500-r, 400+r, 500+r], 200, 340, fill=c+(255,), width=26)
p = polyimg(600); av.alpha_composite(p, (400 - p.width//2, 800 - 600 + 20))
av.convert("RGB").save(f"{OUT}/avatar.png", quality=95)

# ---- BANNER 2560x1440 (safe area 1546x423 centered) ----
W, H = 2560, 1440
bn = clouds(grad(W, H, (174, 224, 230), (255, 247, 232)), [(1950, 300, 1.4), (2250, 560, 1.1), (520, 250, 1.2)])
d = ImageDraw.Draw(bn, "RGBA")
d.ellipse([150, 120, 370, 340], fill=(255, 224, 130, 255))  # sun
p = polyimg(470); bn.alpha_composite(p, (560, (H-470)//2 - 10))
tx = 560 + p.width + 60
big(d, (tx, 545), "Learn with Poly", font(150, WORDF), CORAL, 10)
big(d, (tx, 725), "Songs, ABCs & first words in 5 languages", font(54, WORDF), TEAL, 4)
x, y = tx, 838
for w_, k in [("Hola", "es"), ("Bonjour", "fr"), ("Hallo", "de"), ("Namaste", "in")]:
    fw, fh = 84, 58
    bn.alpha_composite(flag(k, fw, fh), (x, y))
    wf = font(46, WORDF)
    d.text((x+fw+12, y+6), w_, font=wf, fill=INK)
    x += fw + 12 + wf.getbbox(w_)[2] + 46
bn.convert("RGB").save(f"{OUT}/banner.png", quality=92)
print("saved:", os.listdir(OUT))
