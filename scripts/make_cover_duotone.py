#!/usr/bin/env python3
"""
Build the AI Unpacked cover background (the FROZEN "Poster Duotone" intro card).

Maps a host photo to a dark magenta duotone (shadow #08050c -> highlight #47203d)
sized 1080x1920, cover-cropped with an adjustable horizontal focus so the host
stays in frame. Reusable: rerun whenever the host photo changes.

Usage:
  python3 scripts/make_cover_duotone.py \
    --photo channels/claude-tricks/assets/host/ref_avatar_hey_gen_1.jpg \
    --out remotion-studio/public/cover_bg_duotone.jpg [--focus 0.62]
"""
import argparse
from PIL import Image, ImageEnhance

W, H = 1080, 1920
SHADOW = (8, 5, 12)
HIGHLIGHT = (71, 32, 61)


def duotone_lut(shadow, highlight):
    lut = []
    for ch in range(3):
        lut += [round(shadow[ch] + (highlight[ch] - shadow[ch]) * (i / 255)) for i in range(256)]
    return lut


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--photo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--focus", type=float, default=0.5,
                    help="horizontal crop center 0..1 (0=left, 1=right; raise to keep a right-side subject)")
    ap.add_argument("--shadow", default=None, help="hex e.g. 08050c")
    ap.add_argument("--highlight", default=None, help="hex e.g. 47203d")
    a = ap.parse_args()
    shadow = tuple(int(a.shadow[i:i+2], 16) for i in (0, 2, 4)) if a.shadow else SHADOW
    highlight = tuple(int(a.highlight[i:i+2], 16) for i in (0, 2, 4)) if a.highlight else HIGHLIGHT

    im = Image.open(a.photo).convert("RGB")
    # cover-fill 1080x1920
    scale = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    # crop: horizontal focus (keep a right-side subject), keep the bottom of frame
    x = round((im.width - W) * a.focus)
    im = im.crop((x, im.height - H, x + W, im.height))

    # grayscale + slight contrast lift so the face reads through the tint
    g = ImageEnhance.Contrast(im.convert("L")).enhance(1.08)
    # duotone: map luminance across the shadow->highlight ramp
    out = Image.merge("RGB", (g, g, g)).point(duotone_lut(shadow, highlight))
    out.save(a.out, quality=92)
    print(f">> {a.out} ({out.size}) focus={a.focus} shadow={shadow} highlight={highlight}")


if __name__ == "__main__":
    main()
