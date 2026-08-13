#!/usr/bin/env python3
"""EP14 hook illustration (in-house PIL — Leonardo is token-blocked).

The whole episode in one 0.4s read: a scan goes in, a VERDICT comes out, and
the doctor slot in the middle is empty. 1080x1920, matches the hook_art aspect
used by ep11/ep12/ep13.

Compliance: no FDA seal, no vendor name, no device logo, no real patient data.
"""
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from make_doc_mock import S, W, MAGENTA, YELLOW, TXT, DIM, FAINT, CARD, CARD_EDGE  # noqa: E402
from make_doc_mock import font, tw, tracked, tracked_w, bg  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_ep14_mock import retina_glyph  # noqa: E402

CH = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(CH, "assets", "ep14", "hook_art")
H = 1920
GREEN_X = (255, 106, 106)


def main():
    os.makedirs(OUT, exist_ok=True)
    canvas = bg((W * S, H * S), glow_box=[int(-0.1 * W * S), int(0.34 * H * S),
                                          int(1.05 * W * S), int(0.72 * H * S)])
    layer = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")

    # ---- 1. the scan going in --------------------------------------------
    d.rounded_rectangle([210 * S, 430 * S, 870 * S, 900 * S], radius=34 * S,
                        fill=CARD, outline=CARD_EDGE, width=3 * S)
    retina_glyph(d, (300, 470, 780, 860), YELLOW)
    f_lab = font("display", 28)
    w = tracked_w(d, "YOUR SCAN", f_lab, 4.0)
    tracked(d, ((W * S - w) // 2, 358 * S), "YOUR SCAN", f_lab, FAINT, 4.0)

    # ---- 2. the EMPTY doctor slot ----------------------------------------
    d.line([(540 * S, 906 * S), (540 * S, 966 * S)], fill=MAGENTA, width=6 * S)
    # dashed outline = the step that is NOT there
    bx0, by0, bx1, by1 = 210, 972, 870, 1152
    for x in range(bx0 * S, bx1 * S, 34 * S):
        d.line([(x, by0 * S), (min(x + 18 * S, bx1 * S), by0 * S)], fill=(96, 96, 116), width=4 * S)
        d.line([(x, by1 * S), (min(x + 18 * S, bx1 * S), by1 * S)], fill=(96, 96, 116), width=4 * S)
    for y in range(by0 * S, by1 * S, 34 * S):
        d.line([(bx0 * S, y), (bx0 * S, min(y + 18 * S, by1 * S))], fill=(96, 96, 116), width=4 * S)
        d.line([(bx1 * S, y), (bx1 * S, min(y + 18 * S, by1 * S))], fill=(96, 96, 116), width=4 * S)

    f_slot = font("ui_sb", 46)
    t = "NO DOCTOR HERE"
    # NO strikethrough: striking "NO DOCTOR HERE" reads as a double negative.
    # The dashed, empty box already says "this step does not happen".
    d.text(((W * S - tw(d, t, f_slot)) // 2, 1032 * S), t, font=f_slot, fill=GREEN_X)

    d.line([(540 * S, 1158 * S), (540 * S, 1218 * S)], fill=MAGENTA, width=6 * S)

    # ---- 3. the verdict coming out ---------------------------------------
    d.rounded_rectangle([210 * S, 1224 * S, 870 * S, 1400 * S], radius=34 * S,
                        fill=(53, 16, 31), outline=MAGENTA, width=5 * S)
    f_v = font("ui_sb", 56)
    t2 = "DIAGNOSED"
    d.text(((W * S - tw(d, t2, f_v)) // 2, 1276 * S), t2, font=f_v, fill=YELLOW)

    canvas = Image.alpha_composite(canvas.convert("RGBA"), layer).convert("RGB")

    # ---- kicker, outside the stack ---------------------------------------
    d2 = ImageDraw.Draw(canvas)
    f_k = font("ui", 38)
    k = "and it's been legal since 2018"
    d2.text(((W * S - tw(d2, k, f_k)) // 2, 1500 * S), k, font=f_k, fill=DIM)

    p = os.path.join(OUT, "no_doctor.jpg")
    canvas.resize((W, H), Image.LANCZOS).save(p, quality=94)
    print("wrote", p)


if __name__ == "__main__":
    main()
