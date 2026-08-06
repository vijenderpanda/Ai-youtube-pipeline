#!/usr/bin/env python3
"""AI Unpacked banner v2 — statement-first (ref: @vaibhavsisinty header).
2560x1440, all text inside the 1546x423 centered safe area. 3 variants."""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

CH = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(CH, "assets", "channel")
INK = (14, 14, 20); MAG = (224, 33, 138); WHITE = (238, 240, 245)
DIM = (150, 156, 170); GREEN = (80, 220, 140); YELLOW = (255, 214, 10)
W, H = 2560, 1440
SX, SY, SW, SH = (W-1546)//2, (H-423)//2, 1546, 423   # safe area

def ffont(size, cands=("/System/Library/Fonts/Supplemental/Arial Black.ttf",
                       "/System/Library/Fonts/Supplemental/Impact.ttf")):
    for p in cands:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: pass
    return ImageFont.load_default()

def helv(size):
    return ffont(size, ("/System/Library/Fonts/HelveticaNeue.ttc",))

def mono(size):
    return ffont(size, ("/System/Library/Fonts/Menlo.ttc",))

def base():
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im)
    for y in range(0, H, 5):
        d.line([(0, y), (W, y)], fill=(18, 18, 26), width=1)
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(glow).ellipse([W//2-700, H//2-380, W//2+700, H//2+380], fill=(46, 10, 32))
    glow = glow.filter(ImageFilter.GaussianBlur(220))
    return Image.blend(im, glow, 0.55)

def studio_face(width, height):
    """right-panel crop from the magenta studio photo, blended left edge"""
    src = Image.open(os.path.expanduser("~/Downloads/ref_avatar_hey_gen_1.jpg")).convert("RGB")
    sw, sh = src.size            # 832x1248
    ar = width/height
    ch_ = int(sw/ar) if sw/ar <= sh else sh
    cw = int(ch_*ar)
    crop = src.crop((sw-cw, 180, sw, 180+ch_)).resize((width, height), Image.LANCZOS)
    mask = Image.new("L", (width, height), 255)
    md = ImageDraw.Draw(mask)
    for x in range(width//3):
        md.line([(x, 0), (x, height)], fill=int(255*x/(width//3)))
    return crop, mask

# ---- A: pure statement (closest to Vaibhav) ----
def banner_a():
    im = base(); d = ImageDraw.Draw(im)
    line2 = "JUST WHAT ACTUALLY WORKS."
    s2 = 150
    while d.textlength(line2, font=ffont(s2)) > SW - 60:
        s2 -= 4
    f2 = ffont(s2)
    d.text((SX+10, SY+26), "NO HYPE.", font=ffont(150), fill=WHITE)
    tw2 = d.textlength(line2, font=f2)
    d.rectangle([SX+4, SY+206, SX+44+tw2, SY+206+s2+40], fill=MAG)
    d.text((SX+24, SY+226), line2, font=f2, fill=WHITE)
    d.text((SX+12, SY+SH-30), ">_ one AI skill unpacked every day", font=mono(44), fill=GREEN, anchor="lm")
    im.save(os.path.join(OUT, "banner_v2_A.jpg"), quality=95)

# ---- B: statement + face right ----
def banner_b():
    im = base()
    fw, fh = 760, 900
    crop, mask = studio_face(fw, fh)
    im.paste(crop, (SX+SW-fw+120, (H-fh)//2), mask)
    d = ImageDraw.Draw(im)
    d.text((SX+10, SY+10), "AI, MINUS", font=ffont(140), fill=WHITE)
    d.text((SX+10, SY+150), "THE HYPE.", font=ffont(140), fill=MAG)
    d.text((SX+14, SY+318), "Daily 60-second skills — tested on camera,", font=helv(46), fill=DIM)
    d.text((SX+14, SY+374), "shipped before the hype cycle catches up.", font=helv(46), fill=DIM)
    im.save(os.path.join(OUT, "banner_v2_B.jpg"), quality=95)

# ---- C: lockup + daily schedule chip ----
def banner_c():
    im = base(); d = ImageDraw.Draw(im)
    d.text((SX+8, SY+30), "AI", font=ffont(160), fill=WHITE)
    d.text((SX+235, SY+30), "UNPACKED", font=ffont(160), fill=MAG)
    d.text((SX+12, SY+220), "No hype. Just what actually works.", font=helv(56), fill=WHITE)
    chip_y = SY+SH-100
    chip_txt = "NEW SHORT DAILY · 4 PM IST"
    cw = d.textlength(chip_txt, font=ffont(46))
    d.rounded_rectangle([SX+8, chip_y, SX+72+cw, chip_y+82], radius=20, outline=YELLOW, width=5)
    d.text((SX+40, chip_y+41), chip_txt, font=ffont(46), fill=YELLOW, anchor="lm")
    im.save(os.path.join(OUT, "banner_v2_C.jpg"), quality=95)

banner_a(); banner_b(); banner_c()

# contact sheet: full banner + safe-area crop (what most devices show)
sheet = Image.new("RGB", (1620, 3*430+40), (30, 30, 36))
dr = ImageDraw.Draw(sheet)
for i, n in enumerate(["A", "B", "C"]):
    im = Image.open(os.path.join(OUT, f"banner_v2_{n}.jpg"))
    full = im.resize((760, 428))
    safe = im.crop((SX, SY, SX+SW, SY+SH)).resize((800, 219))
    y = 20+i*430
    sheet.paste(full, (10, y))
    sheet.paste(safe, (790, y+100))
    dr.text((800, y+60), f"{n} — safe area (TV crop above, mobile crop below)", fill=(255,255,255))
sheet.save(os.path.join(OUT, "banner_v2_sheet.jpg"), quality=90)
print("done")
