#!/usr/bin/env python3
"""Agent-does-a-chore chat mock (1080x1920) — AI Unpacked, agentic-shopping episode.

Same house grammar as `make_chat_mock.py` (docs/PRODUCTION-PLAYBOOK.md §13) — it
imports that module's palette, background and text helpers so there is exactly one
chat grammar, not two. What differs is the beat: instead of "the AI re-asks what you
told it", the user delegates a shopping chore, the assistant narrates doing it, and
then STOPS at the human (payment stays with the user).

Compliance (this episode names two real companies in the VO, so the graphic must be
scrupulously generic):
  - No vendor name / wordmark / logo / lookalike UI / lookalike brand colour. The
    retailer in the mock is the plainly fictional "ONLINE STORE".
  - Channel palette only: dark ink base, magenta #E0218A send button, yellow accent.
  - ILLUSTRATIVE footer pinned INSIDE the caption-safe band at y=1245, never in the
    bottom dead zone where an overlay chip would sit on the disclosure.
  - Prices are invented, which is exactly what the ILLUSTRATIVE footer discloses.

Craft (§13 "colour is the argument"): a yellow marker under the delegated instruction,
and the two moments that answer it — "ADDED TO CART" and the hand-back-to-human line —
in the SAME yellow. The eye links ask → action with the sound off, no arrows or chips.

Usage:
  make_chat_mock_agent_cart.py -o out.png
"""
import argparse
from pathlib import Path

from PIL import ImageDraw

from make_chat_mock import (
    FAINT, FOOTER, MAGENTA, S, TXT, W, H, YELLOW, DIM,
    bg, font, tracked, tracked_w, tw,
)

# The delegation — one sentence, split for the bubble, marker under both lines.
USER = ["Find the cheapest one of these", "and put it in my cart."]
# The chore, narrated. Dim = the work, yellow = the two things the user cares about.
NARR = ["Compared 6 sellers on ONLINE STORE.", "Lowest: $24.00 (was $31.50)."]
DONE = "ADDED TO CART"
HANDBACK = ["Ready when you are —", "you tap pay."]

SAFE_TOP, FOOTER_Y, FOOT_GAP = 216, 1245, 80
BUBBLE_GAP = 76
MAX_RIGHT = 1020  # bubbles never cross this; matches the composer bar below


def build(out):
    canvas = bg((W * S, H * S))
    d = ImageDraw.Draw(canvas, "RGBA")

    f_hdr = font("ui_sb", 24)
    f_user = font("ui", 48)
    f_narr = font("ui", 42)
    f_done = font("ui_sb", 72)
    f_hand = font("ui_sb", 48)
    f_foot = font("display", 27)
    f_ph = font("ui", 38)

    # ---- header: chrome, lives in the caption dead zone above y=200 ----
    d.ellipse([60 * S, 108 * S, 116 * S, 164 * S], fill=(29, 29, 40))
    d.ellipse([80 * S, 128 * S, 96 * S, 144 * S], fill=MAGENTA)
    tracked(d, (140 * S, 121 * S), "AI ASSISTANT", f_hdr, FAINT, 3.2)
    d.line([(0, 200 * S), (W * S, 200 * S)], fill=(30, 30, 42), width=2)

    # ---- measure first, then centre the block in the band above the footer ----
    pad_x, pad_y = 44, 34
    lh_u, lh_n, lh_d, lh_h = 72, 58, 92, 62
    gap_nd, gap_dh = 22, 16  # narration→ADDED, ADDED→hand-back

    bw = max(tw(d, ln, f_user) for ln in USER) + 2 * pad_x * S
    bh = lh_u * S * len(USER) + 2 * pad_y * S

    abw = max([tw(d, ln, f_narr) for ln in NARR]
              + [tw(d, DONE, f_done)]
              + [tw(d, ln, f_hand) for ln in HANDBACK]) + 2 * pad_x * S
    abh = (lh_n * len(NARR) + gap_nd + lh_d + gap_dh
           + lh_h * len(HANDBACK)) * S + 2 * pad_y * S

    ax0 = 148 * S
    assert bw <= (MAX_RIGHT - 60) * S, f"user bubble {bw/S:.0f}px overflows the safe column"
    assert ax0 + abw <= MAX_RIGHT * S, \
        f"assistant bubble ends at {(ax0 + abw)/S:.0f}px, past the {MAX_RIGHT}px column"

    block = bh + BUBBLE_GAP * S + abh
    band_bot = (FOOTER_Y - FOOT_GAP) * S
    top = SAFE_TOP * S + (band_bot - SAFE_TOP * S - block) // 2
    assert top >= SAFE_TOP * S, "block taller than the safe band — shorten the copy"

    # ---- user bubble (right): the chore they delegated ----
    bx1, by0 = MAX_RIGHT * S, top
    bx0, by1 = bx1 - bw, by0 + bh
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=40 * S,
                        fill=(53, 16, 31), outline=MAGENTA + (120,), width=2 * S)
    y = by0 + pad_y * S
    for ln in USER:
        d.text((bx0 + pad_x * S, y), ln, font=f_user, fill=TXT)
        # yellow marker under the whole instruction — this is the ask the eye follows
        d.rounded_rectangle(
            [bx0 + pad_x * S, y + 63 * S, bx0 + pad_x * S + tw(d, ln, f_user), y + 71 * S],
            radius=4 * S, fill=YELLOW)
        y += lh_u * S

    # ---- assistant bubble (left): the chore done, then the stop at the human ----
    ay0 = by1 + BUBBLE_GAP * S
    d.ellipse([60 * S, ay0, 116 * S, ay0 + 56 * S], fill=(26, 26, 36),
              outline=(46, 46, 60), width=2 * S)
    d.ellipse([78 * S, ay0 + 18 * S, 98 * S, ay0 + 38 * S], fill=(86, 86, 104))

    d.rounded_rectangle([ax0, ay0, ax0 + abw, ay0 + abh], radius=40 * S,
                        fill=(23, 23, 32), outline=(38, 38, 52), width=2 * S)
    y = ay0 + pad_y * S
    for ln in NARR:
        d.text((ax0 + pad_x * S, y), ln, font=f_narr, fill=DIM)
        y += lh_n * S
    y += gap_nd * S
    d.text((ax0 + pad_x * S, y), DONE, font=f_done, fill=YELLOW)
    y += (lh_d + gap_dh) * S
    for ln in HANDBACK:
        d.text((ax0 + pad_x * S, y), ln, font=f_hand, fill=YELLOW)
        y += lh_h * S
    assert y <= band_bot, f"assistant bubble ends at {y/S:.0f}px, into the footer"

    # ---- ILLUSTRATIVE footer: inside the caption-safe band, never under a chip ----
    fw = tracked_w(d, FOOTER, f_foot, 4.0)
    tracked(d, ((W * S - fw) // 2, FOOTER_Y * S), FOOTER, f_foot, (104, 104, 120), 4.0)
    assert FOOTER_Y + 30 <= 1620, "footer breaks the caption-safe band"

    # ---- composer bar: chrome, caption dead zone below y=1620 ----
    d.rounded_rectangle([60 * S, 1690 * S, 1020 * S, 1800 * S], radius=55 * S,
                        fill=(19, 19, 30), outline=(36, 36, 48), width=2 * S)
    d.text((116 * S, 1720 * S), "Ask anything", font=f_ph, fill=(74, 74, 88))
    d.ellipse([916 * S, 1706 * S, 1004 * S, 1794 * S], fill=MAGENTA)
    cx, cy = 960 * S, 1750 * S
    d.polygon([(cx, cy - 22 * S), (cx - 20 * S, cy + 2 * S), (cx + 20 * S, cy + 2 * S)], fill=TXT)
    d.rounded_rectangle([cx - 6 * S, cy - 6 * S, cx + 6 * S, cy + 22 * S], radius=3 * S, fill=TXT)

    from PIL import Image
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
