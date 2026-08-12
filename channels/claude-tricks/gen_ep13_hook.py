#!/usr/bin/env python3
"""EP13 hook illustration (in-house PIL — Leonardo is token-blocked).

One rule card at the top, a magenta fan-out, three fresh chat bubbles below
already wearing the rule. Reads in 0.4s at thumb size: "set once -> every chat".
1080x1350, matches the hook_art aspect used by ep11/ep12.
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

CH = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(CH, "assets", "ep13", "hook_art")
os.makedirs(OUT, exist_ok=True)
FONTS = os.path.join(CH, "..", "..", "remotion-studio", "public", "fonts")
PLAYFAIR = os.path.join(FONTS, "PlayfairDisplay-Italic.ttf")
HELV = "/System/Library/Fonts/HelveticaNeue.ttc"

W, H = 1080, 1920
INK = (11, 11, 16); CARD = (26, 26, 34); EDGE = (54, 54, 66)
MAG = (224, 33, 138); LIME = (198, 255, 62); WHITE = (238, 240, 245); DIM = (138, 144, 158)


def f(path, size, idx=None):
    try:
        return ImageFont.truetype(path, size, index=idx) if idx is not None \
            else ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.truetype(HELV, size)


def main():
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im)

    # magenta bloom behind the rule card
    glow = Image.new("RGB", (W, H), INK)
    ImageDraw.Draw(glow).ellipse([160, 520, 920, 960], fill=(90, 12, 55))
    im = Image.blend(im, glow.filter(ImageFilter.GaussianBlur(110)), 0.85)
    d = ImageDraw.Draw(im)

    lab = f(HELV, 34, 0)
    rule_f = f(HELV, 44, 2)
    bub_f = f(HELV, 34, 0)

    # --- the ONE rule card -------------------------------------------------
    d.rounded_rectangle([90, 570, 990, 850], radius=34, fill=CARD, outline=MAG, width=5)
    d.text((136, 612), "INSTRUCTIONS FOR CLAUDE", font=lab, fill=MAG)
    d.text((136, 690), "Short bullet points.", font=rule_f, fill=WHITE)
    d.text((136, 752), "No preamble, no fluff.", font=rule_f, fill=WHITE)
    d.rounded_rectangle([820, 764, 950, 820], radius=28, fill=LIME)
    sv = f(HELV, 30, 2)
    d.text((852, 776), "SAVED", font=sv, fill=(12, 12, 16))

    # --- fan-out -----------------------------------------------------------
    for x in (250, 540, 830):
        d.line([(540, 860), (x, 1030)], fill=MAG, width=6)
        d.ellipse([x - 9, 1021, x + 9, 1039], fill=MAG)

    # --- three brand-new chats already obeying it --------------------------
    for i, x in enumerate((80, 390, 700)):
        d.rounded_rectangle([x, 1070, x + 300, 1450], radius=28, fill=CARD, outline=EDGE, width=3)
        d.text((x + 26, 1108), f"NEW CHAT {i + 1}", font=f(HELV, 26, 2), fill=DIM)
        for j in range(4):
            y = 1186 + j * 56
            d.ellipse([x + 28, y + 10, x + 42, y + 24], fill=LIME)
            d.rounded_rectangle([x + 58, y + 11, x + 58 + (200 - 34 * (j % 3)), y + 23],
                                radius=6, fill=(96, 100, 114))

    # --- kicker ------------------------------------------------------------
    pf = f(PLAYFAIR, 62)
    txt = "set it once"
    d.text(((W - d.textlength(txt, font=pf)) / 2, 1580), txt, font=pf, fill=LIME)
    sub = f(HELV, 36, 0)
    t2 = "every chat after it, formatted your way"
    d.text(((W - d.textlength(t2, font=sub)) / 2, 1690), t2, font=sub, fill=DIM)

    p = os.path.join(OUT, "set_once.jpg")
    im.save(p, quality=94)
    print("wrote", p)


if __name__ == "__main__":
    main()
