#!/usr/bin/env python3
"""Master outro card (Ep11 style, reusable) — a question-CTA sting: host disc +
big Playfair-italic QUESTION + cyan comment pill + magenta SUBSCRIBE pill +
"one AI trick, every single day". This is the v16.4/Ep11 outro treatment; every
episode gets its OWN question (Ep numbers/questions are per-episode). Renders a
PIL still -> gentle Ken-Burns mp4 (1080x1920 @30fps, ~4.2s).

Usage:
  python3 gen_outro_card.py --out assets/ep12/outro_card.mp4 \
    --q "Notion, Obsidian|or Google Docs?" --pill "Comment yours 👇"
"""
import argparse, os, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops, ImageOps

CH = os.path.dirname(os.path.abspath(__file__))
PLAYFAIR = os.path.join(CH, "..", "..", "remotion-studio", "public", "fonts", "PlayfairDisplay-Italic.ttf")
ANTON = os.path.join(CH, "..", "..", "remotion-studio", "public", "fonts", "Anton.ttf")
HELV = "/System/Library/Fonts/HelveticaNeue.ttc"
W, H = 1080, 1920
MAG = (224, 33, 138); CYAN = (34, 211, 238); WHITE = (238, 240, 245); DIM = (150, 156, 170)


def f(path, size):
    try: return ImageFont.truetype(path, size)
    except Exception: return ImageFont.truetype(HELV, size)


def center(d, txt, font, y, fill):
    w = d.textlength(txt, font=font); d.text(((W - w) / 2, y), txt, font=font, fill=fill)


def pill(d, cy, label, font, fill, ink, outline=None, glow_img=None):
    tw = d.textlength(label, font=font); pw = tw + 120; ph = 96
    x0 = (W - pw) / 2; box = [x0, cy - ph / 2, x0 + pw, cy + ph / 2]
    if outline:
        d.rounded_rectangle(box, radius=ph / 2, fill=fill, outline=outline, width=4)
    else:
        d.rounded_rectangle(box, radius=ph / 2, fill=fill)
    d.text(((W - tw) / 2, cy - font.size * 0.62), label, font=font, fill=ink)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="output mp4 (relative to channel dir ok)")
    ap.add_argument("--q", required=True, help="question, lines split by '|'")
    ap.add_argument("--pill", default="Comment yours 👇")
    ap.add_argument("--avatar", default="assets/channel/avatar_host_v3.jpg")
    a = ap.parse_args()

    # ---- background: dark with a breathing magenta bloom behind the avatar ----
    bg = Image.new("RGB", (W, H))
    px = bg.load()
    for y in range(H):
        t = y / H
        px_row = (int(20 - 8 * t), int(16 - 6 * t), int(30 - 12 * t))
        for x in range(W): px[x, y] = tuple(max(0, c) for c in px_row)
    bloom = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(bloom).ellipse([W / 2 - 460, 120, W / 2 + 460, 1040], fill=(120, 20, 74))
    bg = ImageChops.screen(bg, bloom.filter(ImageFilter.GaussianBlur(180)))
    d = ImageDraw.Draw(bg, "RGBA")

    # ---- host avatar disc with magenta ring, top-center ----
    R = 150; cx, cy = W // 2, 430
    av = Image.open(os.path.join(CH, a.avatar)).convert("RGB")
    av = ImageOps.fit(av, (R * 2, R * 2), Image.LANCZOS)
    mask = Image.new("L", (R * 2, R * 2), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, R * 2, R * 2], fill=255)
    d.ellipse([cx - R - 10, cy - R - 10, cx + R + 10, cy + R + 10], outline=MAG, width=8)
    bg.paste(av, (cx - R, cy - R), mask)
    d = ImageDraw.Draw(bg, "RGBA")

    # ---- big Playfair-italic question ----
    qlines = a.q.split("|")
    qf = f(PLAYFAIR, 108); ly = 690
    for ln in qlines:
        center(d, ln, qf, ly, WHITE); ly += 128

    # ---- cyan comment pill + magenta SUBSCRIBE pill ----
    pill(d, ly + 90, a.pill, f(HELV, 52), (12, 20, 26, 255), CYAN, outline=CYAN)
    pill(d, ly + 260, "SUBSCRIBE", f(ANTON, 60), MAG, WHITE)
    center(d, "one AI trick, every single day", f(HELV, 40), ly + 360, DIM)

    out = a.out if os.path.isabs(a.out) else os.path.join(CH, a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    jpg = out.rsplit(".", 1)[0] + ".jpg"
    bg.convert("RGB").save(jpg, quality=93)
    # gentle Ken-Burns push -> mp4 (~4.2s to match ep11 outro_card length)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", jpg,
        "-vf", ("scale=2160:3840,zoompan=z='1+0.06*on/126':x='(iw-iw/zoom)/2':"
                "y='(ih-ih/zoom)/2':d=126:s=1080x1920:fps=30"),
        "-t", "4.2", "-c:v", "libx264", "-pix_fmt", "yuv420p", out], check=True)
    print(">> outro card:", out)


if __name__ == "__main__":
    main()
