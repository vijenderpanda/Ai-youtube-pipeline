#!/usr/bin/env python3
"""EP13 hook illustration (in-house PIL — Leonardo is token-blocked).

A single meter that is visibly OVER-FILLED past the normal cap, with the
expiry date stamped under it. Reads in 0.4s at thumb size:
"my limit is bigger than normal, and it has a deadline".
1080x1920, matches the hook_art aspect used by ep11/ep12.

  python3 channels/claude-tricks/gen_ep13_boost_hook.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

CH = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(CH, "assets", "ep13", "hook_art")
os.makedirs(OUT, exist_ok=True)
HELV = "/System/Library/Fonts/HelveticaNeue.ttc"

W, H = 1080, 1920
INK = (11, 11, 16); CARD = (26, 26, 34); EDGE = (54, 54, 66)
MAG = (224, 33, 138); LIME = (198, 255, 62)
WHITE = (238, 240, 245); DIM = (138, 144, 158)


def f(size, idx=None):
    try:
        return ImageFont.truetype(HELV, size, index=idx) if idx is not None \
            else ImageFont.truetype(HELV, size)
    except Exception:
        return ImageFont.load_default()


def ctr(d, y, text, font, fill):
    w = d.textbbox((0, 0), text, font=font)[2]
    d.text(((W - w) // 2, y), text, font=font, fill=fill)


def main():
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)

    # soft magenta glow behind the meter so the over-fill reads as "energy"
    glow = Image.new("RGB", (W, H), INK)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([-140, 1100, W + 140, 1620], fill=(58, 12, 38))
    from PIL import ImageFilter
    img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(120)), 0.85)
    d = ImageDraw.Draw(img)

    # NOTE (playbook §4 / AI Unpacked #29): the episode's `hook.lines` overlay
    # already prints the headline and the deadline. Baking either into the art
    # too renders the SAME STRING twice on one frame — a §4 defect even though
    # nothing is occluded. The art carries the METER ONLY; the overlay owns
    # every word. Do not re-add a headline or an "ENDS AUG 19" pill here.
    ctr(d, 760, "WEEKLY CLAUDE CODE LIMIT", f(46, 3), DIM)

    # --- the meter -----------------------------------------------------
    BX, BW, BY, BH = 110, W - 220, 1080, 150
    d.rounded_rectangle([BX, BY, BX + BW, BY + BH], 26, fill=CARD, outline=EDGE, width=3)

    # normal cap sits at 2/3 of the track; the boosted fill runs past it
    cap_x = BX + int(BW * 0.666)
    d.rounded_rectangle([BX, BY, BX + BW, BY + BH], 26, fill=MAG)

    # the "normal" marker line + label
    d.line([cap_x, BY - 40, cap_x, BY + BH + 40], fill=WHITE, width=5)
    d.text((cap_x + 18, BY + BH + 54), "NORMAL", font=f(38, 3), fill=WHITE)
    d.text((cap_x + 18, BY + BH + 100), "CAP", font=f(38, 3), fill=WHITE)

    # the overflow segment, called out in lime
    d.text((BX + 30, BY + 44), "YOU ARE HERE", font=f(44, 3), fill=(255, 255, 255))
    ov = int(BW * 0.79)
    d.polygon([(BX + ov, BY - 74), (BX + ov - 26, BY - 122), (BX + ov + 26, BY - 122)],
              fill=LIME)
    lw = d.textbbox((0, 0), "+50%", font=f(84, 3))[2]
    d.text((BX + ov - lw // 2, BY - 216), "+50%", font=f(84, 3), fill=LIME)

    p = os.path.join(OUT, "boost_ends.jpg")
    img.save(p, quality=94)
    print(p)


if __name__ == "__main__":
    main()
