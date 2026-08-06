#!/usr/bin/env python3
"""Aashiqana Shorts thumbnail: frame zero + a restrained gold Georgia title treatment.

Playbook 5: the Shorts feed shows NO custom thumbnail — frame zero is the de-facto one.
So the source here is always frame 0 of the shipped cut, never a re-render, and the type
NEVER touches the picture: every glyph lands in the caption dead zone BELOW the lyric
band (the chip-over-content rule generalises to any overlay). The band's gold hairlines
are auto-detected, so the dead zone is measured off the real frame, not assumed.

The dead zone is only half dark in this cut (pale mint on the right), so a monsoon-ink
gradient scrim is laid over that strip alone — enough for #F0C45C to read at grid size,
and it stops at the hairline so the couple is untouched.

Usage:
  python3 scripts/make_thumb_aashiqana.py --frame frame0.png \
      --title "BAARISH AUR TUM" --sub "Baarish ban ke tu…" --out thumbnail.jpg
"""
import argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FB = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
FI = "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"
GOLD = (240, 196, 92, 255)          # #F0C45C — channel gold, same value as the end card
PINK = (244, 206, 220, 255)


def font(path, size):
    return ImageFont.truetype(path, size)


def band_bottom(img):
    """y of the lower gold hairline; type must start below it. -1 if no band found."""
    a = np.asarray(img.convert("RGB")).astype(int)
    rb = (a[:, :, 0] - a[:, :, 2]).mean(axis=1)
    rows = [y for y in range(H // 2, H) if rb[y] > 60]
    return max(rows) if rows else -1


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
                d.text((x + dx, y + dy), ch, font=fnt, fill=(0, 0, 0, 200))
            d.text((x, y), ch, font=fnt, fill=fill)
            x += wch
        return
    bb = d.textbbox((0, 0), text, font=fnt)
    x = cx - (bb[2] - bb[0]) / 2 - bb[0]
    for dx, dy in ((so, so), (-so, so), (so, -so), (-so, -so), (0, so), (0, -so)):
        d.text((x + dx, y + dy), text, font=fnt, fill=(0, 0, 0, 200))
    d.text((x, y), text, font=fnt, fill=fill)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--sub", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--zone-top", type=int, default=0, help="override the dead-zone top y")
    a = ap.parse_args()

    base = Image.open(a.frame).convert("RGB")
    if base.size != (W, H):
        base = base.resize((W, H), Image.LANCZOS)

    top = a.zone_top or (band_bottom(base) + 2)
    if not (H * 0.5 < top < H - 200):
        raise SystemExit(f"!! no usable dead zone below the band (top={top})")
    zone = H - top
    print(f">> caption dead zone: y {top}-{H} ({zone}px)")

    card = base.convert("RGBA")
    scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scrim)
    for y in range(top, H):                  # ink ramps in fast, then holds — reads as design
        t = min(1.0, (y - top) / 150.0)
        sd.line([(0, y), (W, y)], fill=(9, 6, 16, int(70 + 145 * t ** 0.8)))
    card = Image.alpha_composite(card, scrim)
    d = ImageDraw.Draw(card)

    # autoshrink: no glyph may approach the 1080 edge — drop the size, never clip
    MAXW, TRACK = W - 2 * 96, 11
    fs = 84
    while fs > 44 and tracked_width(d, a.title, font(FB, fs), TRACK) > MAXW:
        fs -= 2
    tf, sf = font(FB, fs), font(FI, 46)

    title_h, sub_h, gap = int(fs * 1.06), 58, 30
    block = title_h + gap + 2 + gap + sub_h
    y = top + (zone - block) // 2
    if y + block > H - 90:                    # never crowd the very bottom edge
        y = H - 90 - block

    centered(d, W // 2, y, a.title, tf, GOLD, track=TRACK)
    y += title_h + gap
    d.line([(W // 2 - 110, y), (W // 2 + 110, y)], fill=GOLD[:3] + (135,), width=2)
    y += gap + 2
    centered(d, W // 2, y, a.sub, sf, PINK, so=3)

    out = card.convert("RGB")
    for q in (92, 88, 84, 80):
        out.save(a.out, "JPEG", quality=q, subsampling=0, optimize=True)
        import os
        if os.path.getsize(a.out) < 2_000_000:
            print(f">> wrote {a.out} q={q} {os.path.getsize(a.out)/1e6:.2f}MB")
            return
    raise SystemExit("!! could not fit under 2MB")


if __name__ == "__main__":
    main()
