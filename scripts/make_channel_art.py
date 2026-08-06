#!/usr/bin/env python3
"""Make YouTube channel art: banner (2560x1440 + wordmark, safe-area centered) and avatar (800x800)."""
import argparse
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
    "/System/Library/Fonts/SFNSRounded.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]
CREAM = (253, 246, 227)
AMBER = (255, 199, 110)
NIGHT = (18, 18, 42)

def load_font(sz):
    for p in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(p, sz)
        except Exception:
            continue
    return ImageFont.load_default()

def cover(img, W, H):
    iw, ih = img.size
    s = max(W / iw, H / ih)
    img = img.resize((int(iw * s), int(ih * s)))
    x = (img.width - W) // 2
    y = (img.height - H) // 2
    return img.crop((x, y, x + W, y + H))

def banner(src, out):
    W, H = 2560, 1440
    img = cover(Image.open(src).convert("RGB"), W, H)
    # soft scrim panel behind text (kept within the center safe area)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    pw, ph = 1600, 430
    x0, y0 = (W - pw) // 2, int(H * 0.5 - ph / 2)
    d.rounded_rectangle([x0, y0, x0 + pw, y0 + ph], radius=70, fill=(18, 18, 42, 130))
    ov = ov.filter(ImageFilter.GaussianBlur(34))
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    d = ImageDraw.Draw(img)
    cx = W // 2
    d.text((cx, int(H * 0.44)), "Lulla's Moonlit Garden", font=load_font(120),
           fill=CREAM, anchor="mm", stroke_width=6, stroke_fill=NIGHT)
    d.text((cx, int(H * 0.56)), "Calm bedtime songs for little ones", font=load_font(56),
           fill=AMBER, anchor="mm", stroke_width=4, stroke_fill=NIGHT)
    img.save(out, quality=92)
    print(">> saved", out)

def avatar(src, out):
    img = cover(Image.open(src).convert("RGB"), 800, 800)
    img.save(out, quality=92)
    print(">> saved", out)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--banner_src", required=True)
    ap.add_argument("--avatar_src", required=True)
    ap.add_argument("--outdir", default="assets/channel")
    a = ap.parse_args()
    banner(a.banner_src, f"{a.outdir}/banner_final.jpg")
    avatar(a.avatar_src, f"{a.outdir}/avatar_final.jpg")
