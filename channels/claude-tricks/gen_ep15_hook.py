#!/usr/bin/env python3
"""EP15 hook illustration (in-house PIL — Leonardo is token-blocked).

The whole episode in one 0.4s muted read: the SHAPE of the answer changes. A
dense grey wall (you described the style) sits above a two-line bright block
(you pasted one example). No words need to be read for the contrast to land at
240px feed size — that is the entire job of this frame.

1080x1920, matches the hook_art aspect used by ep11/ep12/ep13/ep14.

The engine burns the hook LINES + KICKER over this art (Short.tsx hook block),
so nothing is drawn in the burn zone and no kicker string is baked in — a baked
kicker plus the spec's kicker is the same string printed twice (playbook #29).
"""
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from make_doc_mock import S, W, MAGENTA, YELLOW, TXT, DIM, CARD, CARD_EDGE  # noqa: E402
from make_doc_mock import font, tw, tracked, bg  # noqa: E402

CH = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(CH, "assets", "ep15", "hook_art")
H = 1920

WALL = ["We are thrilled to announce a transformative",
        "evolution of our pricing framework, carefully",
        "designed to deliver enhanced value to our",
        "valued customers across every segment."]
SHORT = ["new pricing is live.", "small teams pay less."]


def main():
    os.makedirs(OUT, exist_ok=True)
    canvas = bg((W * S, H * S), glow_box=[int(-0.12 * W * S), int(0.44 * H * S),
                                          int(1.02 * W * S), int(0.80 * H * S)])
    layer = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")

    # ---- 1. what describing the style gets you: a grey wall ---------------
    y = 620
    d.rounded_rectangle([96 * S, y * S, 984 * S, (y + 292) * S], radius=30 * S,
                        fill=CARD, outline=CARD_EDGE, width=3 * S)
    tracked(d, (140 * S, (y + 32) * S), "YOU DESCRIBED THE STYLE",
            font("display", 26), (255, 106, 106), 3.6)
    f = font("ui", 30)
    for i, ln in enumerate(WALL):
        d.text((140 * S, (y + 88 + i * 46) * S), ln, font=f, fill=DIM)
    y += 292

    # ---- 2. the swap ------------------------------------------------------
    d.line([(540 * S, (y + 26) * S), (540 * S, (y + 82) * S)], fill=MAGENTA, width=7 * S)
    for dx in (-18, 18):
        d.line([(540 * S, (y + 88) * S), ((540 + dx) * S, (y + 58) * S)],
               fill=MAGENTA, width=7 * S)
    y += 108

    # ---- 3. what pasting ONE example gets you: two short bright lines -----
    d.rounded_rectangle([96 * S, y * S, 984 * S, (y + 236) * S], radius=30 * S,
                        fill=(53, 16, 31), outline=MAGENTA, width=5 * S)
    tracked(d, (140 * S, (y + 30) * S), "YOU PASTED 1 EXAMPLE",
            font("display", 26), MAGENTA, 3.6)
    f2 = font("ui_sb", 40)
    for i, ln in enumerate(SHORT):
        d.text((140 * S, (y + 86 + i * 60) * S), ln, font=f2, fill=TXT)
    y += 236

    # ---- 4. the rule, as a chip (no kicker string — the engine burns that)
    chip = "SHOW IT · DON'T DESCRIBE IT"
    fc = font("ui_sb", 30)
    cw = int(tw(d, chip, fc)) + 60 * S
    cx0 = (W * S - cw) // 2
    d.rounded_rectangle([cx0, (y + 44) * S, cx0 + cw, (y + 108) * S], radius=32 * S,
                        fill=YELLOW + (30,), outline=YELLOW, width=3 * S)
    d.text((cx0 + 30 * S, (y + 58) * S), chip, font=fc, fill=YELLOW)

    canvas = Image.alpha_composite(canvas.convert("RGBA"), layer).convert("RGB")
    p = os.path.join(OUT, "style_swap.jpg")
    canvas.resize((W, H), Image.LANCZOS).save(p, quality=94)
    print("wrote", p)


if __name__ == "__main__":
    main()
