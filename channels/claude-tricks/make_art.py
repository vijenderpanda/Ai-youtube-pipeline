#!/usr/bin/env python3
"""AI Unpacked channel art: avatar (800x800) + banner (2560x1440, text in the 1546x423 safe area)."""
import os
from PIL import Image, ImageDraw, ImageFont

CH = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(CH, "assets", "channel"); os.makedirs(OUT, exist_ok=True)
INK = (14, 14, 20); MAG = (224, 33, 138); WHITE = (238, 240, 245); DIM = (140, 146, 160)
GREEN = (80, 220, 140)

def ffont(size, cands=("/System/Library/Fonts/Supplemental/Impact.ttf",
                       "/System/Library/Fonts/Supplemental/Arial Black.ttf")):
    for p in cands:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: pass
    return ImageFont.load_default()

def mono(size):
    return ffont(size, ("/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Courier.ttc"))

# ---- avatar: Sol in a magenta ring on ink ----
def avatar():
    D = 800
    im = Image.new("RGB", (D, D), INK)
    sol = Image.open(os.path.join(CH, "assets", "character", "host_face.jpg")).convert("RGB")
    s = min(sol.size)
    sol = sol.crop(((sol.width - s)//2, (sol.height - s)//2, (sol.width + s)//2, (sol.height + s)//2))
    face = 620; sol = sol.resize((face, face))
    mask = Image.new("L", (face, face), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, face, face], fill=255)
    off = (D - face)//2
    im.paste(sol, (off, off), mask)
    d = ImageDraw.Draw(im)
    d.ellipse([off-14, off-14, off+face+14, off+face+14], outline=MAG, width=22)
    p = os.path.join(OUT, "avatar_final.jpg"); im.save(p, quality=95); print("wrote", p)

# ---- banner: safe-area centered lockup ----
def banner():
    W, H = 2560, 1440
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im)
    for i in range(0, H, 5):
        d.line([(0, i), (W, i)], fill=(18, 18, 26), width=1)
    # safe area 1546x423 centered
    sx, sy = (W-1546)//2, (H-423)//2
    # sol at left of safe area
    sol = Image.open(os.path.join(CH, "assets", "character", "host_face.jpg")).convert("RGB")
    s = min(sol.size)
    sol = sol.crop(((sol.width - s)//2, (sol.height - s)//2, (sol.width + s)//2, (sol.height + s)//2))
    face = 320; sol = sol.resize((face, face))
    mask = Image.new("L", (face, face), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, face, face], fill=255)
    fy = sy + (423-face)//2
    im.paste(sol, (sx+10, fy), mask)
    d.ellipse([sx+2, fy-8, sx+18+face, fy+face+8], outline=MAG, width=12)
    # text lockup
    tx = sx + face + 80
    d.text((tx, sy+70), "AI", font=ffont(170), fill=WHITE)
    d.text((tx+235, sy+70), "UNPACKED", font=ffont(170), fill=MAG)
    d.text((tx+4, sy+270), "No hype. Just what actually works.", font=ffont(52,
           ("/System/Library/Fonts/HelveticaNeue.ttc",)), fill=DIM)
    d.text((tx+4, sy+345), ">_ a new AI trick every day", font=mono(40), fill=GREEN)
    p = os.path.join(OUT, "banner_final.jpg"); im.save(p, quality=95); print("wrote", p)

avatar(); banner()
