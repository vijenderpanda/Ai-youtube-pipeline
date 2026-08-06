#!/usr/bin/env python3
"""In-house generic chat mock (1080x1920) for AI Unpacked "weak result in frame 1" hooks.

House rules baked in (docs/PRODUCTION-PLAYBOOK.md §13 in-house data-mock grammar):
  - NO vendor name, NO logo, NO lookalike branding. Neutral dark chat UI on the
    channel's own palette (magenta #E0218A + yellow accent, dark-ink base).
  - A small ILLUSTRATIVE footer, placed INSIDE the caption-safe band so a chip can
    never cover the disclosure.
  - Caption-safe layout: nothing meaningful above y=200 or below y=1620 at 1x
    (§10c layout rule — chips live in the dead space, never on the content).
  - Rendered at 2x and downscaled LANCZOS (§10c supersample rule), low-frequency
    noise only, to keep gradients from banding.

Usage:
  make_chat_mock.py -o out.png
  make_chat_mock.py -o out.png --user "line one" --user "line two" \
                    --lead "Sure - quick question first:" \
                    --ask "What kind of work" --ask "do you do?"
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO = Path(__file__).resolve().parent.parent
W, H = 1080, 1920
S = 2  # supersample factor

FONTS = {
    "ui": Path.home() / "Library/Fonts/Poppins-Regular.ttf",
    "ui_sb": Path.home() / "Library/Fonts/Poppins-SemiBold.ttf",
    "display": REPO / "remotion-studio/public/fonts/Anton.ttf",
}

MAGENTA = (224, 33, 138)
YELLOW = (255, 216, 77)
INK_TOP = (11, 10, 16)
INK_BOT = (21, 16, 27)
TXT = (247, 247, 250)
DIM = (150, 150, 164)
FAINT = (104, 104, 120)

DEF_USER = ["I run a daily AI channel.", "What should I post tomorrow?"]
DEF_LEAD = "Sure — quick question first:"
DEF_ASK = ["What kind of work", "do you do?"]
FOOTER = "ILLUSTRATIVE — IN-HOUSE MOCK, NOT A PRODUCT SCREENSHOT"


def font(key, px):
    return ImageFont.truetype(str(FONTS[key]), px * S)


def tw(draw, text, f):
    """Width only — never renders (a measure pass that draws leaves ghost ink)."""
    return draw.textlength(text, font=f)


def tracked_w(draw, text, f, track):
    return sum(draw.textlength(ch, font=f) + track * S for ch in text)


def bg(size):
    """Vertical ink gradient + a soft magenta glow, low-frequency noise on top."""
    w, h = size
    top = np.array(INK_TOP, dtype=np.float32)
    bot = np.array(INK_BOT, dtype=np.float32)
    ramp = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None]
    img = top[None, None, :] * (1 - ramp) + bot[None, None, :] * ramp
    img = np.repeat(img, w, axis=1)

    # anti-banding dither only: low-frequency and low-amplitude. Anything louder
    # reads as film grain on a UI screenshot, which is exactly wrong here.
    small = np.random.default_rng(24).normal(0, 3.0, (h // 40, w // 40)).astype(np.float32)
    up = Image.fromarray(np.clip(small + 128, 0, 255).astype(np.uint8)) \
        .resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(w // 90))
    noise = (np.array(up, dtype=np.float32)[:, :, None] - 128.0) * 0.30
    img = np.clip(img + noise, 0, 255).astype(np.uint8)
    base = Image.fromarray(img, "RGB")

    # soft magenta bloom behind the assistant bubble — brand warmth, not a wash
    glow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(glow).ellipse(
        [int(-0.18 * w), int(0.40 * h), int(0.72 * w), int(0.72 * h)], fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(int(0.10 * w))).point(lambda v: int(v * 0.14))
    return Image.composite(Image.new("RGB", (w, h), MAGENTA), base, glow)


def tracked(draw, xy, text, f, fill, track):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=f, fill=fill)
        x += tw(draw, ch, f) + track * S
    return x


def build(user_lines, lead, ask_lines, out):
    canvas = bg((W * S, H * S))
    d = ImageDraw.Draw(canvas, "RGBA")

    f_hdr = font("ui_sb", 24)
    f_user = font("ui", 46)
    f_lead = font("ui", 40)
    f_ask = font("ui_sb", 66)
    f_foot = font("display", 27)
    f_ph = font("ui", 38)

    # ---- header (decorative; lives in the caption dead zone above y=200) ----
    d.ellipse([60 * S, 108 * S, 116 * S, 164 * S], fill=(29, 29, 40))
    d.ellipse([80 * S, 128 * S, 96 * S, 144 * S], fill=MAGENTA)
    tracked(d, (140 * S, 121 * S), "AI ASSISTANT", f_hdr, FAINT, 3.2)
    d.line([(0, 200 * S), (W * S, 200 * S)], fill=(30, 30, 42), width=2)

    # ---- measure everything first, then centre the block in the safe band ----
    pad_x, pad_y, gap = 44, 34, 14
    lh_u, lh_a = 62, 84
    SAFE_TOP, SAFE_BOT, BUBBLE_GAP, FOOT_GAP = 216, 1620, 76, 74

    bw = max(tw(d, ln, f_user) for ln in user_lines) + 2 * pad_x * S
    bh = lh_u * S * len(user_lines) + 2 * pad_y * S
    abw = max([tw(d, lead, f_lead)] + [tw(d, ln, f_ask) for ln in ask_lines]) + 2 * pad_x * S
    abh = (52 + gap) * S + lh_a * S * len(ask_lines) + 2 * pad_y * S
    foot_h = 30
    block = bh + BUBBLE_GAP * S + abh + FOOT_GAP * S + foot_h * S
    top = SAFE_TOP * S + ((SAFE_BOT - SAFE_TOP) * S - block) // 2

    # ---- user bubble (right) : the context the host DID give ----
    bx1, by1 = 1020 * S, top
    bx0, by1b = bx1 - bw, by1 + bh
    d.rounded_rectangle([bx0, by1, bx1, by1b], radius=40 * S,
                        fill=(53, 16, 31), outline=MAGENTA + (120,), width=2 * S)
    y = by1 + pad_y * S
    for i, ln in enumerate(user_lines):
        d.text((bx0 + pad_x * S, y), ln, font=f_user, fill=TXT)
        if i == 0:  # yellow marker under the role they just stated
            d.rounded_rectangle(
                [bx0 + pad_x * S, y + 56 * S, bx0 + pad_x * S + tw(d, ln, f_user), y + 64 * S],
                radius=4 * S, fill=YELLOW)
        y += lh_u * S

    # ---- assistant bubble (left) : it asks for what it was just told ----
    ay0 = by1b + BUBBLE_GAP * S
    d.ellipse([60 * S, ay0, 116 * S, ay0 + 56 * S], fill=(26, 26, 36),
              outline=(46, 46, 60), width=2 * S)
    d.ellipse([78 * S, ay0 + 18 * S, 98 * S, ay0 + 38 * S], fill=(86, 86, 104))

    ax0 = 148 * S
    d.rounded_rectangle([ax0, ay0, ax0 + abw, ay0 + abh], radius=40 * S,
                        fill=(23, 23, 32), outline=(38, 38, 52), width=2 * S)
    y = ay0 + pad_y * S
    d.text((ax0 + pad_x * S, y), lead, font=f_lead, fill=DIM)
    y += (52 + gap) * S
    for ln in ask_lines:
        d.text((ax0 + pad_x * S, y), ln, font=f_ask, fill=YELLOW)
        y += lh_a * S
    abh_end = ay0 + abh

    # ---- ILLUSTRATIVE footer: inside the safe band, never under a chip ----
    fy = abh_end + FOOT_GAP * S
    fw = tracked_w(d, FOOTER, f_foot, 4.0)
    tracked(d, ((W * S - fw) // 2, fy), FOOTER, f_foot, (104, 104, 120), 4.0)
    assert fy / S + foot_h <= SAFE_BOT, f"footer at {fy/S:.0f} breaks the caption-safe band"

    # ---- composer bar (decorative; caption dead zone below y=1620) ----
    d.rounded_rectangle([60 * S, 1690 * S, 1020 * S, 1800 * S], radius=55 * S,
                        fill=(19, 19, 30), outline=(36, 36, 48), width=2 * S)
    d.text((116 * S, 1720 * S), "Ask anything", font=f_ph, fill=(74, 74, 88))
    d.ellipse([916 * S, 1706 * S, 1004 * S, 1794 * S], fill=MAGENTA)
    cx, cy = 960 * S, 1750 * S
    d.polygon([(cx, cy - 22 * S), (cx - 20 * S, cy + 2 * S), (cx + 20 * S, cy + 2 * S)], fill=TXT)
    d.rounded_rectangle([cx - 6 * S, cy - 6 * S, cx + 6 * S, cy + 22 * S], radius=3 * S, fill=TXT)

    canvas.resize((W, H), Image.LANCZOS).save(out, "PNG")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--user", action="append")
    ap.add_argument("--lead")
    ap.add_argument("--ask", action="append")
    a = ap.parse_args()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    build(a.user or DEF_USER, a.lead or DEF_LEAD, a.ask or DEF_ASK, out)
    print("OK", out)


if __name__ == "__main__":
    main()
