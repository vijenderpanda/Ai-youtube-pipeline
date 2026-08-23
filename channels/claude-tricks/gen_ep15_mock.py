#!/usr/bin/env python3
"""EP15 in-house PROMPT-TEARDOWN mock (1080x1920), 5 states.

Fifth sibling of the in-house-mock family (data -> StatBars, chat ->
make_chat_mock, documents -> make_doc_mock, evaluation -> make_report_mock,
clinical -> gen_ep14_mock). This one mocks a **chat prompt + its reply** for the
"describing the style loses to pasting one example" episode.

The whole episode is a SHAPE contrast, so every state is authored to read
sound-off at 240px feed size: the DESCRIBED reply is a dense 4-line grey wall,
the EXAMPLE reply is two short bright lines. A muted viewer never has to read a
word to see which one changed.

COMPLIANCE (playbook §13):
  - NO vendor name, NO logo, NO lookalike chrome. Neutral dark chat surface on
    the channel palette. Every string is written by us, so the ILLUSTRATIVE
    footer (not an attribution line) is the correct disclosure.
  - Nothing meaningful above y=200 or below the y1420 caption band — asserted in
    build() by the same safe-band checks make_doc_mock uses.

Chrome headers are DISTINCT from the beat captions that play over them
(playbook #29: printing the same string twice is a §4 defect).

  gen_ep15_mock.py --mode ask|generic|paste|matched|compare -o out.png
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from make_doc_mock import (  # noqa: E402
    S, W, MAGENTA, YELLOW, GREEN, TXT, DIM, FAINT, CARD, CARD_EDGE,
    INK_TOP, bg, font, tw, tracked, tracked_w, SAFE_BOT, CAPTION_TOP,
    SAFE_TOP, header as doc_header,
)

RED = (255, 106, 106)
FOOTER = "ILLUSTRATIVE — IN-HOUSE MOCK, NOT A PRODUCT SCREENSHOT"

REQUEST = "Write a post about our new pricing."
GENERIC = ["We are thrilled to announce a transformative",
           "evolution of our pricing framework, carefully",
           "designed to deliver enhanced value to our",
           "valued customers across every segment."]
SAMPLE = ["new pricing is live. cheaper for small teams.",
          "nothing else changed."]
MATCHED = ["new pricing is live. small teams pay less.",
           "same features. no sales call. that's it."]


def footer(d, y):
    """ILLUSTRATIVE disclosure — asserted inside the caption-safe band."""
    f = font("display", 25)
    w = tracked_w(d, FOOTER, f, 3.2)
    tracked(d, ((W * S - w) // 2, y * S), FOOTER, f, FAINT, 3.2)
    assert y + 28 <= SAFE_BOT, f"footer at {y} breaks the caption-safe band"


def pill(d, x, y, text, col, filled=False, px=26, right=None):
    """Pill sized to its TEXT — a fixed box silently clips a longer label."""
    f = font("ui_sb", px)
    w = int(tw(d, text, f)) + 44 * S
    h = 52 * S
    x0 = (right * S - w) if right is not None else x * S
    d.rounded_rectangle([x0, y * S, x0 + w, y * S + h], radius=h // 2,
                        fill=col if filled else col + (34,), outline=col, width=2 * S)
    d.text((x0 + 22 * S, y * S + 12 * S), text, font=f,
           fill=INK_TOP if filled else col)
    return y + 52


def label(d, x, y, text, col=FAINT, px=25):
    tracked(d, (x * S, y * S), text, font("display", px), col, 3.4)
    return y + 40


def bubble(d, y, lines, *, accent, size=34, pad=32, lead=48, mine=False):
    """A chat bubble. `mine` = the user side (tighter, magenta edge)."""
    f = font("ui", size)
    wmax = max(tw(d, ln, f) for ln in lines)
    x0 = 72 * S
    x1 = min(1008 * S, x0 + int(wmax) + 2 * pad * S)
    h = 2 * pad * S + lead * S * (len(lines) - 1) + int(size * 1.3) * S
    d.rounded_rectangle([x0, y * S, x1, y * S + h], radius=28 * S, fill=CARD,
                        outline=accent + (150,) if mine else CARD_EDGE,
                        width=(3 if mine else 2) * S)
    for i, ln in enumerate(lines):
        d.text((x0 + pad * S, y * S + pad * S + i * lead * S), ln, font=f,
               fill=TXT if mine else DIM)
    return y + h // S + 20


# ---------------------------------------------------------------- states ----
def m_ask(d, **_):
    """BEFORE state: the style is DESCRIBED. Adjectives, no example."""
    y = 300
    y = label(d, 72, y, "YOU ASK") + 14
    y = bubble(d, y, [REQUEST], accent=MAGENTA, mine=True) + 16
    y = label(d, 72, y, "AND YOU DESCRIBE THE STYLE") + 14
    y = bubble(d, y, ["Make it friendly, punchy and human.",
                      "Not corporate."], accent=MAGENTA, mine=True) + 10

    # the adjectives, isolated — the thing this episode is accusing
    x = 72
    for word in ("FRIENDLY", "PUNCHY", "HUMAN"):
        f = font("ui_sb", 26)
        w = int(tw(d, word, f)) + 44 * S
        d.rounded_rectangle([x * S, y * S, x * S + w, (y + 52) * S], radius=26 * S,
                            fill=YELLOW + (30,), outline=YELLOW, width=2 * S)
        d.text((x * S + 22 * S, (y + 12) * S), word, font=f, fill=YELLOW)
        x += w // S + 16
    y += 76
    d.text((72 * S, y * S), "3 adjectives. 0 examples.", font=font("ui", 34), fill=FAINT)
    footer(d, y + 74)


def m_generic(d, **_):
    """The cost: a dense grey wall that sounds like nobody."""
    y = 330
    y = label(d, 72, y, "WHAT COMES BACK") + 14
    y = bubble(d, y, GENERIC, accent=CARD_EDGE) + 18
    pill(d, 72, y, "READS LIKE A PRESS RELEASE", RED)
    y += 84
    d.text((72 * S, y * S), "Every adjective obeyed. None of them heard.",
           font=font("ui", 34), fill=FAINT)
    footer(d, y + 74)


def m_paste(d, **_):
    """The one move: same ask, one example of the voice pasted in."""
    y = 292
    y = label(d, 72, y, "SAME ASK") + 14
    y = bubble(d, y, [REQUEST], accent=MAGENTA, mine=True) + 16
    y = label(d, 72, y, "ONE CHANGE — PASTE SOMETHING YOU WROTE", MAGENTA) + 14
    y = bubble(d, y, ["Match this:"] + SAMPLE, accent=MAGENTA, mine=True) + 18
    pill(d, 72, y, "1 EXAMPLE · 0 ADJECTIVES", MAGENTA)
    footer(d, y + 104)


def m_matched(d, **_):
    """PAYOFF state: the reply takes the shape of the example."""
    y = 330
    y = label(d, 72, y, "WHAT COMES BACK NOW", GREEN) + 14
    y = bubble(d, y, MATCHED, accent=GREEN, size=36) + 18
    pill(d, 72, y, "SAME LENGTH · SAME RHYTHM · YOUR VOICE", GREEN)
    y += 84
    d.text((72 * S, y * S), "Nothing was described. One thing was shown.",
           font=font("ui", 34), fill=FAINT)
    footer(d, y + 74)


def m_compare(d, **_):
    """The one-frame muted payoff: dense grey wall vs two short bright lines."""
    y = 268
    # --- top: described
    d.rounded_rectangle([72 * S, y * S, 1008 * S, (y + 300) * S], radius=28 * S,
                        fill=CARD, outline=CARD_EDGE, width=2 * S)
    label(d, 108, y + 30, "YOU DESCRIBED IT", RED)
    f = font("ui", 30)
    for i, ln in enumerate(GENERIC):
        d.text((108 * S, (y + 86 + i * 46) * S), ln, font=f, fill=DIM)
    y += 300 + 34

    d.line([(540 * S, y * S), (540 * S, (y + 44) * S)], fill=MAGENTA, width=6 * S)
    y += 66

    # --- bottom: pasted one example
    d.rounded_rectangle([72 * S, y * S, 1008 * S, (y + 262) * S], radius=28 * S,
                        fill=(53, 16, 31), outline=MAGENTA, width=4 * S)
    label(d, 108, y + 30, "YOU PASTED 1 EXAMPLE", MAGENTA)
    f2 = font("ui_sb", 36)
    for i, ln in enumerate(MATCHED):
        d.text((108 * S, (y + 92 + i * 56) * S), ln, font=f2, fill=TXT)
    y += 262 + 26
    pill(d, 0, y, "SHOW, DON'T DESCRIBE", YELLOW, right=1008)
    footer(d, y + 84)


HEADERS = {"ask": "YOUR PROMPT", "generic": "THE REPLY",
           "paste": "YOUR PROMPT, ONE LINE LONGER", "matched": "THE REPLY, REWIRED",
           "compare": "SIDE BY SIDE"}
MODES = {"ask": m_ask, "generic": m_generic, "paste": m_paste,
         "matched": m_matched, "compare": m_compare}


def build(mode, out):
    """Body on a transparent layer, then centred in the safe band (make_doc_mock)."""
    canvas = bg((W * S, 1920 * S))
    layer = Image.new("RGBA", (W * S, 1920 * S), (0, 0, 0, 0))
    MODES[mode](ImageDraw.Draw(layer, "RGBA"))

    box = layer.getbbox()
    if box:
        _, top_px, _, bot_px = box
        block_h = bot_px - top_px
        want_top = SAFE_TOP * S + ((SAFE_BOT - SAFE_TOP) * S - block_h) // 2
        dy = int(want_top - top_px)
        if dy:
            shifted = Image.new("RGBA", layer.size, (0, 0, 0, 0))
            shifted.paste(layer.crop((0, top_px, W * S, bot_px)), (0, top_px + dy))
            layer = shifted
        assert want_top >= SAFE_TOP * S, f"{mode}: block starts above the safe band"
        assert want_top + block_h <= CAPTION_TOP * S, \
            f"{mode}: block ends at y{(want_top+block_h)/S:.0f}, under the caption band"

    head = Image.new("RGBA", (W * S, 1920 * S), (0, 0, 0, 0))
    doc_header(ImageDraw.Draw(head, "RGBA"), HEADERS[mode])
    canvas = Image.alpha_composite(canvas.convert("RGBA"),
                                   Image.alpha_composite(head, layer)).convert("RGB")
    canvas.resize((W, 1920), Image.LANCZOS).save(out, "PNG")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=sorted(MODES))
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    build(a.mode, out)
    print("OK", out)


if __name__ == "__main__":
    main()
