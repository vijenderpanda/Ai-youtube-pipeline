#!/usr/bin/env python3
"""Generic delegation glyph card (1080x1920) — AI Unpacked, agentic-shopping episode.

The one idea, with the sound off: **the chain of delegation ends at a human.**
YOU -> AI AGENT -> YOUR CART flows left to right, then the chain stops at a dashed
boundary and the last node — the magenta PAY button with a fingertip on it — sits
on the far side of it, labelled "THIS ONE STAYS YOURS".

House rules (docs/PRODUCTION-PLAYBOOK.md §13 in-house mock grammar) inherited by
importing make_chat_mock's palette/background/measure helpers, so there is one
grammar and not two:
  - GENERIC glyphs only. No vendor name, wordmark, logo, lookalike UI or lookalike
    brand colour; the cart is a plain trapezoid basket + handle + two wheels, with
    no smile, swoosh or arrow curve anywhere on the card.
  - NO numbers, NO percentages, NO bars. A numeric comparison on this channel goes
    through the locked StatBars Remotion component as a native `stat:` beat —
    pre-baking a chart into a 9:16 pane is banned.
  - Channel palette only: dark ink base, magenta #E0218A, yellow accent, Anton type.
  - Colour is the argument (§13): yellow marks exactly the two words the VO stresses
    — YOU and PAY — and nothing else. Magenta marks the one node that never leaves
    the human. Everything else is white or dim, so the eye lands where the ear does.
  - Caption/chip safety (§4, §10c): every drawn element is asserted clear of BOTH
    StepChip bands (40px inset, top 170 / bottom 560 -> y 170-246 and y 1284-1344)
    across the full width, and clear of the bottom caption band. The bottom third is
    deliberately empty — that is where the burned-in caption lives on a |full beat.
  - Text is measured with draw.textlength(); nothing is ever drawn at alpha 0 to
    measure it (a measure pass that draws leaves ghost ink).
  - Rendered at 2x and downscaled LANCZOS (§10c supersample rule).

Usage:
  make_glyph_delegation.py -o out.png
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from make_chat_mock import (
    DIM, MAGENTA, S, TXT, W, H, YELLOW,
    bg, font, tracked, tracked_w, tw,
)

# ---- labels -----------------------------------------------------------------
# Deliberately NOT phrased like a step chip. Playbook line "an overlay does not
# have to COVER content to be a defect — printing the SAME STRING twice is the same
# failure": this beat's likely chips are the episode's rule lines, so no label here
# repeats one, and the card carries no title/eyebrow at all.
NODES = ["YOU", "AI AGENT", "YOUR CART"]
KICKER = "THIS ONE STAYS YOURS"
PAY = "PAY"

# ---- geometry (1x px; everything is scaled by S at draw time) ----------------
CHIP_TOP_BAND = (170, 246)      # StepChip top rect, mirrored from Short.tsx
CHIP_BOT_BAND = (1284, 1344)    # StepChip bottom rect (H - 560 - 76 .. H - 560)
CAPTION_TOP = 1500              # nothing essential below this — captions live here

TILE = 250
TILE_Y0 = 398
CX = [185, 540, 895]            # tile centres: 3x250 + 2x105 gaps, 60px side margin
LABEL_Y = 674
RULE_Y = 800
KICKER_Y = 862
BTN = (320, 940, 760, 1070)     # the one magenta node — the click that stays human
FINGER_TIP = (700, 1004)
FINGER_END = (900, 1152)

STROKE = 7                      # 1x outline weight for every glyph
LINE = (132, 132, 156)          # neutral glyph ink
TILE_EDGE = (70, 70, 92)


def _px(*vals):
    return [v * S for v in vals]


def _tile(d, cx, edge=TILE_EDGE):
    x0, y0 = cx - TILE // 2, TILE_Y0
    d.rounded_rectangle(_px(x0, y0, x0 + TILE, y0 + TILE), radius=34 * S,
                        outline=edge, width=3 * S)
    return x0, y0


def _person(d, cx):
    """Generic person outline: head + shoulders. No face, no gender cues."""
    cy = TILE_Y0 + TILE // 2
    d.ellipse(_px(cx - 34, cy - 92, cx + 34, cy - 24), outline=LINE, width=STROKE * S)
    # shoulders: an upper semicircle, so the figure reads as a person, not a lollipop
    d.arc(_px(cx - 74, cy + 4, cx + 74, cy + 152), start=180, end=360,
          fill=LINE, width=STROKE * S)


def _agent(d, cx):
    """Generic assistant: a neutral rounded square with two dot eyes + antenna.

    Explicitly not any vendor's mark — a square head is the most common public-domain
    'machine' glyph there is, and it carries no colour of its own.
    """
    cy = TILE_Y0 + TILE // 2
    d.rounded_rectangle(_px(cx - 72, cy - 46, cx + 72, cy + 68), radius=24 * S,
                        outline=LINE, width=STROKE * S)
    for dx in (-28, 28):
        d.ellipse(_px(cx + dx - 11, cy - 8, cx + dx + 11, cy + 14), fill=LINE)
    d.line(_px(cx, cy - 86, cx, cy - 50), fill=LINE, width=STROKE * S)
    d.ellipse(_px(cx - 12, cy - 106, cx + 12, cy - 82), outline=LINE, width=STROKE * S)


def _cart(d, cx):
    """Plain cart outline: trapezoid basket, straight handle, two wheels.

    Deliberately boring. No curved arrow, no smile, no wordmark — the whole point of
    baking this in-house is that it cannot be mistaken for a retailer's icon.
    """
    cy = TILE_Y0 + TILE // 2
    bx0, bx1, by0, by1 = cx - 62, cx + 74, cy - 30, cy + 36
    inset = 16
    d.line([*_px(bx0, by0), *_px(bx1, by0)], fill=LINE, width=STROKE * S)
    d.line([*_px(bx1, by0), *_px(bx1 - inset, by1)], fill=LINE, width=STROKE * S)
    d.line([*_px(bx1 - inset, by1), *_px(bx0 + inset, by1)], fill=LINE, width=STROKE * S)
    d.line([*_px(bx0 + inset, by1), *_px(bx0, by0)], fill=LINE, width=STROKE * S)
    # handle
    d.line([*_px(bx0, by0), *_px(bx0 - 26, by0 - 34)], fill=LINE, width=STROKE * S)
    d.line([*_px(bx0 - 26, by0 - 34), *_px(bx0 - 54, by0 - 34)], fill=LINE, width=STROKE * S)
    for wx in (bx0 + inset + 12, bx1 - inset - 12):
        d.ellipse(_px(wx - 15, by1 + 16, wx + 15, by1 + 46), outline=LINE, width=STROKE * S)


def _arrow(d, x0, x1, y):
    """Flow arrow. Points away from YOU — the work moves outward, not back."""
    head = 26
    d.line([*_px(x0, y), *_px(x1 - head, y)], fill=LINE, width=STROKE * S)
    d.polygon([(x1 * S, y * S), ((x1 - head) * S, (y - 15) * S),
               ((x1 - head) * S, (y + 15) * S)], fill=LINE)


def _dashed_rule(d, y, x0, x1, dash=26, gap=20):
    """The boundary the delegation does not cross."""
    x = x0
    while x < x1:
        d.line([*_px(x, y), *_px(min(x + dash, x1), y)], fill=(78, 78, 100), width=3 * S)
        x += dash + gap


def _capsule(d, p0, p1, r, fill):
    d.line([*_px(*p0), *_px(*p1)], fill=fill, width=2 * r * S)
    for (px, py) in (p0, p1):
        d.ellipse(_px(px - r, py - r, px + r, py + r), fill=fill)


def _finger(d, ink):
    """A fingertip pressing PAY. Outline is drawn as a slightly larger white capsule
    with the ink capsule punched inside it — a stroked rotated capsule PIL can't do
    directly, and stroking by hand would leave seams at the joins."""
    _capsule(d, FINGER_TIP, FINGER_END, 32, TXT)
    _capsule(d, FINGER_TIP, FINGER_END, 26, ink)
    # a knuckle crease across the finger, so it reads as a finger and not a peg.
    # Drawn perpendicular to the finger's own axis, otherwise it reads as a stray tick.
    kx, ky = FINGER_TIP[0] + 74, FINGER_TIP[1] + 54
    ux, uy = FINGER_END[0] - FINGER_TIP[0], FINGER_END[1] - FINGER_TIP[1]
    n = (ux * ux + uy * uy) ** 0.5
    px_, py_ = -uy / n * 22, ux / n * 22
    d.line([*_px(kx - px_, ky - py_), *_px(kx + px_, ky + py_)], fill=TXT + (150,), width=4 * S)
    # tap ripples on the button side of the tip
    for r, a in ((52, 150), (74, 90)):
        d.arc(_px(FINGER_TIP[0] - r, FINGER_TIP[1] - r,
                  FINGER_TIP[0] + r, FINGER_TIP[1] + r),
              start=118, end=282, fill=TXT + (a,), width=4 * S)


def build(out):
    canvas = bg((W * S, H * S))
    ink = canvas.getpixel((W * S // 2, 1000 * S))  # sample the base for the finger fill
    d = ImageDraw.Draw(canvas, "RGBA")

    f_label = font("display", 52)
    f_kick = font("display", 44)
    f_pay = font("display", 78)

    # ---- the chain: YOU -> AI AGENT -> YOUR CART ----------------------------
    for i, cx in enumerate(CX):
        _tile(d, cx)
    _person(d, CX[0])
    _agent(d, CX[1])
    _cart(d, CX[2])

    mid = TILE_Y0 + TILE // 2
    for a, b in ((0, 1), (1, 2)):
        _arrow(d, CX[a] + TILE // 2 + 22, CX[b] - TILE // 2 - 22, mid)

    # labels: YOU is one of the two words the VO stresses, so YOU is the only yellow
    # thing in the chain. Measured, then centred — never drawn twice.
    label_bot = LABEL_Y
    for i, (cx, txt) in enumerate(zip(CX, NODES)):
        col = YELLOW if i == 0 else TXT
        wdt = tw(d, txt, f_label)
        assert wdt <= (TILE + 40) * S, f"label {txt!r} is wider than its tile"
        d.text((cx * S - wdt / 2, LABEL_Y * S), txt, font=f_label, fill=col)
        label_bot = max(label_bot, LABEL_Y + 62)

    # ---- the boundary, then the node that never leaves the human ------------
    _dashed_rule(d, RULE_Y, 190, 890)

    kw = tracked_w(d, KICKER, f_kick, 4.0)
    tracked(d, ((W * S - kw) // 2, KICKER_Y * S), KICKER, f_kick, TXT, 4.0)

    bx0, by0, bx1, by1 = BTN
    d.rounded_rectangle(_px(bx0, by0, bx1, by1), radius=30 * S, fill=MAGENTA,
                        outline=(240, 82, 170), width=3 * S)
    pw = tw(d, PAY, f_pay)
    # PAY sits left of the button's centre so the fingertip never lands on the word
    d.text((478 * S - pw / 2, (by0 + 22) * S), PAY, font=f_pay, fill=YELLOW)
    assert 478 + pw / (2 * S) < FINGER_TIP[0] - 40, "the fingertip crowds the PAY word"

    _finger(d, ink)

    # ---- safety asserts: chips and captions can never sit on the content ----
    content_top, content_bot = TILE_Y0, FINGER_END[1] + 34
    for name, (b0, b1) in (("top chip", CHIP_TOP_BAND), ("bottom chip", CHIP_BOT_BAND)):
        assert content_bot <= b0 or content_top >= b1, \
            f"content y{content_top}-{content_bot} intersects the {name} band {b0}-{b1}"
    assert content_bot < CAPTION_TOP, \
        f"content reaches y{content_bot}, into the caption band at {CAPTION_TOP}"
    assert content_top > CHIP_TOP_BAND[1], "content starts inside the top chip band"
    assert label_bot < RULE_Y < KICKER_Y < by0, "the boundary is out of reading order"

    canvas.resize((W, H), Image.LANCZOS).save(out, "PNG")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    build(out)
    print("OK", out)


if __name__ == "__main__":
    main()
