#!/usr/bin/env python3
"""ep1_thumb.py — thumbnail options for longform ep1 (1280x720, champagne lane).
Host cutout + phone w/ real app + big time type. 3 variants -> renders/longform/."""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CH = os.path.dirname(HERE)
sys.path.insert(0, CH)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(CH)), "scripts"))
import build_longform_segment as lf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

A = os.path.join(CH, "assets", "longform_ep1")
R = os.path.join(CH, "renders", "longform")
W, H = 1280, 720
INK = (15, 14, 12)


def base():
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im)
    for r in range(900, 0, -6):
        a = int(26 * r / 900)
        d.ellipse([W - 400 - r, H // 2 - r, W - 400 + r, H // 2 + r],
                  fill=(15 + a, 14 + int(a * 0.8), 12 + int(a * 0.35)))
    return im


def phone_card(hshot, ph_h):
    shot = Image.open(os.path.join(A, hshot)).convert("RGB")
    ph_w = int(ph_h * shot.width / shot.height)
    shot = shot.resize((ph_w, ph_h), Image.LANCZOS)
    r = int(ph_h * 0.09)
    card = Image.new("RGBA", (ph_w + 16, ph_h + 16), (0, 0, 0, 0))
    m = Image.new("L", (ph_w, ph_h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, ph_w, ph_h], radius=r, fill=255)
    body = Image.new("RGBA", (ph_w + 16, ph_h + 16), (0, 0, 0, 0))
    ImageDraw.Draw(body).rounded_rectangle([0, 0, ph_w + 16, ph_h + 16],
                                           radius=r + 8, fill=(20, 20, 24, 255))
    card.alpha_composite(body)
    card.paste(shot, (8, 8), m)
    return card


def host(hh):
    c = Image.open(os.path.join(A, "cutout_close.png"))
    c = c.crop(c.getbbox())  # tight to the person — no invisible margins
    sc = hh / c.height
    return c.resize((int(c.width * sc), hh), Image.LANCZOS)


def big(d, txt, xy, size, fill, stroke=(0, 0, 0)):
    f = ImageFont.truetype(lf.FONT_ANTON, size)
    d.text(xy, txt, font=f, fill=fill, stroke_width=max(4, size // 28),
           stroke_fill=stroke)
    return d.textlength(txt, font=f)


def v1():
    im = base()
    hc = host(600)
    im.paste(hc, (W - hc.width + 40, H - 600), hc)
    ph = phone_card("shot_home.png", 520)
    im.paste(ph, (560, 120), ph)
    d = ImageDraw.Draw(im)
    big(d, "3H 48M", (48, 140), 150, lf.ACCENT)
    big(d, "IDEA → APP STORE", (52, 340), 58, (240, 240, 244))
    big(d, "ZERO CODE BY HAND", (52, 430), 42, (170, 168, 160))
    return im


def v2():
    im = base()
    hc = host(640)
    im.paste(hc, (-30, H - 640), hc)
    ph = phone_card("shot_home.png", 560)
    im.paste(ph, (940, 90), ph)
    d = ImageDraw.Draw(im)
    big(d, "I SHIPPED THIS", (400, 110), 76, (240, 240, 244))
    big(d, "IN 3H 48M", (400, 220), 120, lf.ACCENT)
    big(d, "iPHONE APP - REAL RECEIPTS", (404, 390), 40, (170, 168, 160))
    return im


def v3():
    im = base()
    ph = phone_card("shot_detail.png", 600)
    im.paste(ph, (480, 70), ph)
    hc = host(560)
    im.paste(hc, (W - hc.width + 30, H - 560), hc)
    d = ImageDraw.Draw(im)
    big(d, "3", (80, 50), 280, lf.ACCENT)
    big(d, "HOURS", (95, 370), 90, (240, 240, 244))
    big(d, "TO THE APP STORE", (84, 500), 48, (170, 168, 160))
    return im


if __name__ == "__main__":
    for i, fn in enumerate([v1, v2, v3], 1):
        p = os.path.join(R, f"ep1_thumb_v{i}.jpg")
        fn().convert("RGB").save(p, quality=92)
        print(p)
    sheet = Image.new("RGB", (W, H * 3 + 40), (0, 0, 0))
    for i in range(3):
        sheet.paste(Image.open(os.path.join(R, f"ep1_thumb_v{i + 1}.jpg")),
                    (0, i * (H + 20)))
    sheet.save(os.path.join(R, "ep1_thumbs_sheet.jpg"), quality=88)
    print("sheet done")
