#!/usr/bin/env python3
"""In-house artifact-panel mock (1080x1920) for the AI Unpacked "wall of text -> artifact" Short.

Four states, same grammar as make_chat_mock.py (docs/PRODUCTION-PLAYBOOK.md §13):
  wall   - the ask, and an unreadable wall of dim body text in the message column
  ask    - same wall, with the one-line fix typed in the composer
  panel  - the artifact panel opening on the right, rendering the plan as a clean doc
  done   - the finished artifact, with copy / download controls visible

House rules baked in, identical to §13:
  - NO vendor name, NO logo, NO lookalike branding. Neutral dark UI on the
    channel's own palette (magenta #E0218A + yellow accent, dark-ink base).
  - A small ILLUSTRATIVE footer INSIDE the caption-safe band, so a step chip can
    never cover the disclosure.
  - Caption-safe layout: nothing meaningful above y=200 or below y=1620 at 1x —
    the chips live in the dead space, never on the artifact being taught.
  - Rendered at 2x and downscaled LANCZOS, low-frequency dither only.

Usage:
  make_artifact_mock.py --state wall  -o out.png
  make_artifact_mock.py --all-into channels/claude-tricks/assets/ep31
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
WALL = (118, 118, 132)          # the deliberately low-contrast wall body text

FOOTER = "ILLUSTRATIVE — IN-HOUSE MOCK, NOT A PRODUCT SCREENSHOT"
SAFE_TOP, SAFE_BOT = 216, 1620

ASK = "Give me a 2-week beginner meal plan with a shopping list"
FIX = "put that in an artifact"

# The wall: real sentences, set small and dim so it reads as WORK, not content.
WALL_LINES = [
    "Sure! Here's a two-week beginner meal plan. I've kept the",
    "ingredients simple and overlapping so nothing goes to waste.",
    "",
    "Week 1 — Monday: Breakfast is oats with banana and a spoon of",
    "peanut butter. Lunch is a chicken salad wrap. Dinner is pasta",
    "with tomato sauce and a side salad. Tuesday: Breakfast is",
    "scrambled eggs on toast. Lunch is leftover pasta. Dinner is",
    "baked salmon with rice and broccoli. Wednesday: Breakfast is",
    "greek yogurt with berries. Lunch is a tuna sandwich. Dinner is",
    "stir-fried vegetables with tofu and noodles. Thursday:",
    "Breakfast is oats again. Lunch is a chicken salad wrap. Dinner",
    "is chilli with rice. Friday: Breakfast is scrambled eggs.",
    "Lunch is leftover chilli. Dinner is homemade pizza.",
    "",
    "Week 2 — Monday: Breakfast is a smoothie with banana, spinach",
    "and oats. Lunch is a lentil soup with bread. Dinner is roast",
    "chicken with potatoes. Tuesday: Breakfast is toast with eggs.",
    "Lunch is leftover roast chicken. Dinner is fish tacos.",
    "",
    "Shopping List — Produce: bananas, spinach, tomatoes, broccoli,",
    "mixed salad, berries, potatoes, onions, garlic, lemons.",
    "Protein: chicken breast, salmon fillets, tuna, eggs, tofu,",
    "minced beef. Pantry: oats, pasta, rice, noodles, lentils,",
    "peanut butter, tinned tomatoes, olive oil, tortillas.",
]

DOC_TITLE = "2-Week Beginner Meal Plan"
DOC_BODY = [
    ("h", "WEEK 1"),
    ("b", "Mon — Oats · Chicken wrap · Pasta"),
    ("b", "Tue — Eggs · Leftover pasta · Salmon"),
    ("b", "Wed — Yogurt · Tuna sandwich · Stir-fry"),
    ("b", "Thu — Oats · Chicken wrap · Chilli"),
    ("b", "Fri — Eggs · Leftover chilli · Pizza"),
    ("h", "SHOPPING LIST"),
    ("c", "Produce — bananas, spinach, broccoli"),
    ("c", "Protein — chicken, salmon, eggs, tofu"),
    ("c", "Pantry — oats, pasta, rice, lentils"),
]


def font(key, px):
    return ImageFont.truetype(str(FONTS[key]), px * S)


def tw(draw, text, f):
    """Width only — never renders (a measure pass that draws leaves ghost ink)."""
    return draw.textlength(text, font=f)


def tracked_w(draw, text, f, track):
    return sum(draw.textlength(ch, font=f) + track * S for ch in text)


def tracked(draw, xy, text, f, fill, track):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=f, fill=fill)
        x += tw(draw, ch, f) + track * S
    return x


def bg(size):
    """Vertical ink gradient + a soft magenta glow, low-frequency noise on top."""
    w, h = size
    top = np.array(INK_TOP, dtype=np.float32)
    bot = np.array(INK_BOT, dtype=np.float32)
    ramp = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None]
    img = top[None, None, :] * (1 - ramp) + bot[None, None, :] * ramp
    img = np.repeat(img, w, axis=1)

    small = np.random.default_rng(24).normal(0, 3.0, (h // 40, w // 40)).astype(np.float32)
    up = Image.fromarray(np.clip(small + 128, 0, 255).astype(np.uint8)) \
        .resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(w // 90))
    noise = (np.array(up, dtype=np.float32)[:, :, None] - 128.0) * 0.30
    img = np.clip(img + noise, 0, 255).astype(np.uint8)
    base = Image.fromarray(img, "RGB")

    glow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(glow).ellipse(
        [int(-0.18 * w), int(0.40 * h), int(0.72 * w), int(0.72 * h)], fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(int(0.10 * w))).point(lambda v: int(v * 0.14))
    return Image.composite(Image.new("RGB", (w, h), MAGENTA), base, glow)


def header(d):
    """Decorative chrome in the caption dead zone above y=200."""
    d.ellipse([60 * S, 108 * S, 116 * S, 164 * S], fill=(29, 29, 40))
    d.ellipse([80 * S, 128 * S, 96 * S, 144 * S], fill=MAGENTA)
    tracked(d, (140 * S, 121 * S), "AI ASSISTANT", font("ui_sb", 24), FAINT, 3.2)
    d.line([(0, 200 * S), (W * S, 200 * S)], fill=(30, 30, 42), width=2)


def footer(d, y):
    f = font("display", 27)
    fw = tracked_w(d, FOOTER, f, 4.0)
    tracked(d, ((W * S - fw) // 2, y * S), FOOTER, f, (104, 104, 120), 4.0)
    assert y + 30 <= SAFE_BOT, f"footer at {y} breaks the caption-safe band"


def composer(d, text=None, hot=False):
    """Bottom composer bar. Decorative in the dead zone below y=1620."""
    d.rounded_rectangle([60 * S, 1690 * S, 1020 * S, 1800 * S], radius=55 * S,
                        fill=(19, 19, 30),
                        outline=(MAGENTA if hot else (36, 36, 48)), width=(3 if hot else 2) * S)
    f = font("ui_sb" if text else "ui", 38)
    d.text((116 * S, 1720 * S), text or "Ask anything", font=f,
           fill=(TXT if text else (74, 74, 88)))
    if text:  # a caret, so the line reads as JUST typed
        cx = 116 * S + tw(d, text, f) + 10 * S
        d.rounded_rectangle([cx, 1716 * S, cx + 4 * S, 1770 * S], radius=2 * S, fill=MAGENTA)
    d.ellipse([916 * S, 1706 * S, 1004 * S, 1794 * S], fill=MAGENTA)
    cx, cy = 960 * S, 1750 * S
    d.polygon([(cx, cy - 22 * S), (cx - 20 * S, cy + 2 * S), (cx + 20 * S, cy + 2 * S)], fill=TXT)
    d.rounded_rectangle([cx - 6 * S, cy - 6 * S, cx + 6 * S, cy + 22 * S], radius=3 * S, fill=TXT)


def user_bubble(d, y, text, max_w=760):
    """Right-aligned ask bubble. Returns its bottom edge (1x)."""
    f = font("ui", 40)
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if tw(d, t, f) > max_w * S and cur:
            lines.append(cur); cur = w_
        else:
            cur = t
    lines.append(cur)
    pad_x, pad_y, lh = 36, 26, 54
    bw = max(tw(d, ln, f) for ln in lines) + 2 * pad_x * S
    bh = lh * S * len(lines) + 2 * pad_y * S
    x1 = 1020 * S
    d.rounded_rectangle([x1 - bw, y * S, x1, y * S + bh], radius=34 * S,
                        fill=(53, 16, 31), outline=MAGENTA + (120,), width=2 * S)
    ty = y * S + pad_y * S
    for ln in lines:
        d.text((x1 - bw + pad_x * S, ty), ln, font=f, fill=TXT)
        ty += lh * S
    return y + bh / S


def draw_wall(d, top, dim=1.0):
    """The unusable answer: dense, low-contrast, running past the fold."""
    f = font("ui", 27)
    lh = 40
    col = tuple(int(c * dim) for c in WALL)
    d.ellipse([60 * S, top * S, 104 * S, (top + 44) * S], fill=(26, 26, 36),
              outline=(46, 46, 60), width=2 * S)
    d.ellipse([74 * S, (top + 14) * S, 90 * S, (top + 30) * S], fill=(86, 86, 104))
    y = top
    for ln in WALL_LINES:
        if y > SAFE_BOT - 40:
            break
        if ln:
            d.text((128 * S, y * S), ln, font=f, fill=col)
        y += lh
    return y


def artifact_panel(d, x0, controls=False, alpha=255):
    """The artifact side panel: a clean, formatted, scrollable document."""
    x1, y0, y1 = 1040, 250, 1560
    d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], radius=30 * S,
                        fill=(26, 24, 33), outline=MAGENTA + (alpha,), width=3 * S)
    # panel title bar
    d.rounded_rectangle([x0 * S, y0 * S, x1 * S, (y0 + 92) * S], radius=30 * S,
                        fill=(34, 30, 44))
    d.rectangle([x0 * S, (y0 + 60) * S, x1 * S, (y0 + 92) * S], fill=(34, 30, 44))
    d.text(((x0 + 34) * S, (y0 + 26) * S), DOC_TITLE, font=font("ui_sb", 36), fill=TXT)
    d.line([(x0 * S, (y0 + 92) * S), (x1 * S, (y0 + 92) * S)], fill=(52, 46, 66), width=2 * S)

    f_h = font("ui_sb", 32)
    f_b = font("ui", 31)
    y = y0 + 130
    for kind, txt in DOC_BODY:
        if kind == "h":
            y += 16
            tracked(d, ((x0 + 34) * S, y * S), txt, f_h, YELLOW, 2.4)
            y += 58
        elif kind == "b":
            d.ellipse([(x0 + 40) * S, (y + 16) * S, (x0 + 52) * S, (y + 28) * S], fill=MAGENTA)
            d.text(((x0 + 72) * S, y * S), txt, font=f_b, fill=TXT)
            y += 56
        else:  # checkbox row
            d.rounded_rectangle([(x0 + 38) * S, (y + 8) * S, (x0 + 66) * S, (y + 36) * S],
                                radius=6 * S, outline=(96, 92, 112), width=2 * S)
            d.text(((x0 + 84) * S, y * S), txt, font=f_b, fill=TXT)
            y += 56

    if controls:
        # copy / download pills — the "one click" the payoff line promises
        py = y1 - 108
        for i, label in enumerate(("Copy", "Download")):
            f = font("ui_sb", 30)
            pw = tw(d, label, f) + 92 * S
            px = (x0 + 34) * S + i * (pw + 24 * S)
            d.rounded_rectangle([px, py * S, px + pw, (py + 68) * S], radius=34 * S,
                                fill=(53, 16, 31), outline=MAGENTA, width=2 * S)
            # glyph
            gx = px + 30 * S
            if i == 0:
                d.rounded_rectangle([gx - 10 * S, (py + 20) * S, gx + 8 * S, (py + 46) * S],
                                    radius=4 * S, outline=TXT, width=2 * S)
                d.rounded_rectangle([gx - 2 * S, (py + 26) * S, gx + 16 * S, (py + 52) * S],
                                    radius=4 * S, fill=(53, 16, 31), outline=TXT, width=2 * S)
            else:
                d.line([(gx + 2 * S, (py + 18) * S), (gx + 2 * S, (py + 42) * S)], fill=TXT, width=3 * S)
                d.polygon([(gx - 10 * S, (py + 34) * S), (gx + 14 * S, (py + 34) * S),
                           (gx + 2 * S, (py + 50) * S)], fill=TXT)
            d.text((px + 56 * S, (py + 16) * S), label, font=f, fill=TXT)
    return y1


def build(state, out):
    canvas = bg((W * S, H * S))
    d = ImageDraw.Draw(canvas, "RGBA")
    header(d)

    if state in ("wall", "ask"):
        y = user_bubble(d, 240, ASK)
        end = draw_wall(d, y + 40)
        footer(d, min(end + 26, SAFE_BOT - 30))
        composer(d, FIX if state == "ask" else None, hot=(state == "ask"))

    else:  # panel / done — the artifact opens over the chat column
        user_bubble(d, 240, ASK, max_w=380)
        draw_wall(d, 470, dim=0.42)
        x0 = 300 if state == "panel" else 150
        # a soft scrim so the panel reads as ON TOP of the conversation
        scrim = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(scrim).rectangle([0, 0, W * S, H * S], fill=(8, 7, 12, 150))
        canvas.alpha_composite(scrim) if canvas.mode == "RGBA" else canvas.paste(
            Image.alpha_composite(canvas.convert("RGBA"), scrim).convert("RGB"), (0, 0))
        d = ImageDraw.Draw(canvas, "RGBA")
        artifact_panel(d, x0, controls=(state == "done"))
        footer(d, SAFE_BOT - 30)
        composer(d)

    canvas.convert("RGB").resize((W, H), Image.LANCZOS).save(out, "PNG")
    return out


STATES = ("wall", "ask", "panel", "done")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out")
    ap.add_argument("--state", choices=STATES, default="wall")
    ap.add_argument("--all-into", help="render all four states into this directory")
    a = ap.parse_args()
    if a.all_into:
        dst = Path(a.all_into); dst.mkdir(parents=True, exist_ok=True)
        for s in STATES:
            print("OK", build(s, dst / f"mock_{s}.png"))
        return
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    build(a.state, out)
    print("OK", out)


if __name__ == "__main__":
    main()
