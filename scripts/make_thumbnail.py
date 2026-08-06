#!/usr/bin/env python3
"""
Thumbnail maker for Lulla — 1280x720, brand font, legibility scrim.
Usage:
  python3 scripts/make_thumbnail.py --img assets/thumbnail/thumb01_1.jpg \
    --title "Goodnight" --sub "Little Light" --tag "Bedtime Songs for Babies" \
    --out assets/thumbnail/thumb01_final_A.jpg
"""
import argparse
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
FONT_CANDIDATES = [
    "assets/fonts/FredokaOne-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
    "/System/Library/Fonts/SFNSRounded.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]
CREAM = (253, 246, 227)
AMBER = (255, 199, 110)

def load_font(size):
    for p in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()

def cover(img):
    iw, ih = img.size
    s = max(W / iw, H / ih)
    img = img.resize((int(iw * s), int(ih * s)))
    x = (img.width - W) // 2
    y = (img.height - H) // 2
    return img.crop((x, y, x + W, y + H))

def right_scrim(img, start=0.40, strength=190):
    scrim = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(scrim)
    for x in range(W):
        a = int(max(0.0, (x - W * start) / (W * (1 - start))) * strength)
        d.line([(x, 0), (x, H)], fill=min(a, strength))
    dark = Image.new("RGB", (W, H), (18, 18, 42))
    return Image.composite(dark, img, scrim)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--img", required=True)
    ap.add_argument("--title", default="Goodnight")
    ap.add_argument("--sub", default="Little Light")
    ap.add_argument("--tag", default="Bedtime Songs for Babies")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    img = cover(Image.open(a.img).convert("RGB"))
    img = right_scrim(img)
    d = ImageDraw.Draw(img)
    f_title = load_font(132)
    f_sub = load_font(88)
    f_tag = load_font(40)
    rx = W - 64

    def line(y, text, font, fill):
        d.text((rx, y), text, font=font, fill=fill, anchor="rm",
               stroke_width=4, stroke_fill=(18, 18, 42))

    line(255, a.title, f_title, CREAM)
    line(370, a.sub, f_sub, AMBER)
    line(460, a.tag, f_tag, CREAM)
    img.save(a.out, quality=92)
    print(">> saved", a.out)

if __name__ == "__main__":
    main()
