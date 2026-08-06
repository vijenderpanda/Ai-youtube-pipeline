#!/usr/bin/env python3
"""Channel-style annotation of a REAL captured frame (AI Unpacked).

House rule this exists to protect (docs/PRODUCTION-PLAYBOOK.md §10b):
  "Redact PII in place, never edit the vendor UI. Blurring PII is fine;
   relabelling or mocking a vendor screen is not."

So this tool only ever *adds* a marker in the frame's dead space. It never
touches the vendor pixels:
  - the annotation is drawn on a transparent 2x layer, LANCZOS-downscaled
    (§10c supersample rule) and alpha-composited over the untouched capture,
    so every vendor pixel outside the marker stays bit-exact;
  - `--under BASELINE,INKBOT,X0,X1` marks the ink band of a sentence; the bar is
    placed BELOW the band and then HARD-CLIPPED to the dead space between that
    line's descenders and the next line, so no glyph row can be touched at all.
    (A soft glow was tried and rejected: gaussian spread tinted the descender
    rows, which is exactly the "altered the vendor text" line we don't cross.
    Flat yellow on a near-black UI already carries maximum contrast.)

Colour is the argument (§13): the channel yellow accent under the sentence that
carries the point, no arrows and no callout chips.

Usage:
  annotate_capture.py IN.png OUT.png --under 1329,1335,34,1029 --under 1381,1381,33,237
"""
import argparse

from PIL import Image, ImageDraw

S = 2  # supersample factor for the annotation layer only

YELLOW = (255, 216, 77)
BAR_H = 8  # 1x px — reads at phone size without crowding the next line
BASE_DROP = 12  # 1x px below the text baseline
CLIP_PAD = 3  # 1x px of dead space kept below the bar


def marker(layer_draw, x0, x1, y_top, h, fill):
    """Rounded-cap marker bar, drawn in supersampled space."""
    layer_draw.rounded_rectangle(
        [x0 * S, y_top * S, x1 * S, (y_top + h) * S - 1],
        radius=(h * S) // 2,
        fill=fill,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument(
        "--under",
        action="append",
        required=True,
        metavar="BASELINE,INKBOT,X0,X1",
        help="one per wrapped line: text baseline y, ink bottom y (incl. descenders), ink x span",
    )
    ap.add_argument("--bar-h", type=int, default=BAR_H)
    ap.add_argument("--drop", type=int, default=BASE_DROP)
    args = ap.parse_args()

    base = Image.open(args.src).convert("RGB")
    W, H = base.size

    layer = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    bands = []

    for spec in args.under:
        baseline, ink_bot, x0, x1 = (int(v) for v in spec.split(","))
        y_top = baseline + args.drop
        if y_top < ink_bot + 2:  # never let the bar ride the descenders
            y_top = ink_bot + 2
        marker(d, x0, x1, y_top, args.bar_h, YELLOW + (255,))
        bands.append((ink_bot + 1, y_top + args.bar_h + CLIP_PAD))

    # Hard-clip to the measured dead space: any row that is not strictly between
    # a marked line's descenders and its bar is erased, so a glyph row cannot be
    # touched even by antialiasing.
    keep = Image.new("L", (W * S, H * S), 0)
    kd = ImageDraw.Draw(keep)
    for top, bot in bands:
        kd.rectangle([0, top * S, W * S, bot * S - 1], fill=255)
    layer.putalpha(Image.composite(layer.split()[3], Image.new("L", keep.size, 0), keep))

    ann = layer.resize((W, H), Image.LANCZOS)
    out = base.convert("RGBA")
    out.alpha_composite(ann)
    out.convert("RGB").save(args.dst)
    print(f"wrote {args.dst} {W}x{H}  clip bands={bands}")


if __name__ == "__main__":
    main()
