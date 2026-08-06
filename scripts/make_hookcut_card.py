#!/usr/bin/env python3
"""End card for a Shorts hook cut: 1080x1920 title card in channel type.

Background is a blurred, darkened frame from the cut itself so the card reads as the
song settling rather than a hard cut to a slate. Shorts links barely click — the card
is a retention pointer, not a CTA button.

Usage:
  python3 scripts/make_hookcut_card.py --bg frame.jpg --title "BAARISH AUR TUM" \
      --sub "full song on the channel" --brand AASHIQANA --out card.png
"""
import argparse
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
FB = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
FI = "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"
GOLD = (240, 196, 92, 255)
WHITE = (255, 246, 250, 255)
PINK = (244, 206, 220, 255)


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def cover(img, w, h):
    iw, ih = img.size
    s = max(w / iw, h / ih)
    img = img.resize((int(iw * s), int(ih * s)), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def tracked_width(d, text, fnt, track):
    """Measure only — never draw to measure (a measure pass that draws leaves ghost ink)."""
    if not track:
        bb = d.textbbox((0, 0), text, font=fnt)
        return bb[2] - bb[0]
    return sum(d.textlength(ch, font=fnt) + track for ch in text) - track


def centered(d, cx, y, text, fnt, fill, so=4, track=0):
    if track:
        widths = [d.textlength(ch, font=fnt) + track for ch in text]
        x = cx - (sum(widths) - track) / 2
        for ch, wch in zip(text, widths):
            for dx, dy in ((so, so), (-so, so), (so, -so), (-so, -so)):
                d.text((x + dx, y + dy), ch, font=fnt, fill=(0, 0, 0, 190))
            d.text((x, y), ch, font=fnt, fill=fill)
            x += wch
        return
    bb = d.textbbox((0, 0), text, font=fnt)
    x = cx - (bb[2] - bb[0]) / 2 - bb[0]
    for dx, dy in ((so, so), (-so, so), (so, -so), (-so, -so), (0, so), (0, -so)):
        d.text((x + dx, y + dy), text, font=fnt, fill=(0, 0, 0, 190))
    d.text((x, y), text, font=fnt, fill=fill)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bg", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--sub", required=True)
    ap.add_argument("--brand", default="AASHIQANA")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    bg = cover(Image.open(a.bg).convert("RGB"), W, H).filter(ImageFilter.GaussianBlur(34))
    card = bg.convert("RGBA")
    scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scrim)
    for i in range(H):                       # deep monsoon-ink scrim, heaviest mid-frame
        t = abs(i - H * 0.5) / (H * 0.5)
        sd.line([(0, i), (W, i)], fill=(9, 6, 16, int(172 - 66 * t ** 1.6)))
    card = Image.alpha_composite(card, scrim)
    d = ImageDraw.Draw(card)

    words = a.title.split()
    if len(words) > 2:                        # break long titles onto two elegant lines
        mid = max(1, len(words) // 2)   # "BAARISH / AUR TUM", matching the channel art
        lines = [" ".join(words[:mid]), " ".join(words[mid:])]
    else:
        lines = [a.title]

    # autoshrink: no glyph may approach the 1080 edge — drop the size, never clip
    MAXW, TRACK = W - 2 * 96, 10
    fs = 108
    while fs > 48 and max(tracked_width(d, ln, font(FB, fs), TRACK) for ln in lines) > MAXW:
        fs -= 2
    tf, lh = font(FB, fs), int(fs * 1.20)
    bf, sf = font(FB, 40), font(FI, 52)

    # centred, vertically balanced stack: wordmark / rule / title / rule / sub
    brand_h, sub_h = 46, 62
    block = brand_h + 74 + len(lines) * lh + 58 + sub_h
    y = (H - block) // 2

    centered(d, W // 2, y, a.brand, bf, PINK, so=3, track=14)
    y += brand_h + 36
    d.line([(W // 2 - 150, y), (W // 2 + 150, y)], fill=GOLD[:3] + (150,), width=2)
    y += 38

    for ln in lines:
        centered(d, W // 2, y, ln, tf, GOLD, track=TRACK)
        y += lh

    y += 30
    d.line([(W // 2 - 90, y), (W // 2 + 90, y)], fill=GOLD[:3] + (120,), width=2)
    y += 28
    centered(d, W // 2, y, a.sub, sf, PINK, so=3)

    card.convert("RGB").save(a.out)
    print(">> wrote", a.out)


if __name__ == "__main__":
    main()
