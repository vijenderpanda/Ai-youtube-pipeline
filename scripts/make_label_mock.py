#!/usr/bin/env python3
"""In-house CONTENT-LABEL mock (1080x1920), 4 states.

Fourth member of the in-house-mock family: `make_chat_mock.py` mocks a *chat*,
`make_doc_mock.py` a *document-grounding surface*, `make_report_mock.py` a
*safety-evaluation report* — this one mocks **content provenance labelling**:
the badge on a piece of media, what the two label classes mean, the date the
duty became enforceable, and the penalty ceiling.

WHY THIS EXISTS (AI Unpacked build 29, 2026-08-06). The episode explains EU AI
Act Article 50 for beginners. Two constraints collide, the same way they did on
build 28: the brief bans EU logo lockups (an institutional emblem is not ours
to use, and a lockup implies endorsement), and playbook §13 bans mocking
anyone's UI as if it were a capture — which rules out screenshotting the
Commission's own Code-of-Practice icon sheet. What is left is an OWN graphic
carrying the published facts, attributed and dated on its face.

Like `make_report_mock.py` and UNLIKE the chat/doc siblings, every number here
is REAL and sourced, so these states carry an **ATTRIBUTION** footer, never an
"ILLUSTRATIVE" one (playbook §13, Ep28: inventing numbers under a source line
and disowning sourced findings as illustrative are both lies, in opposite
directions).

House rules inherited from §13 / §4 (asserted, not just intended):
  - NO emblem, NO flag, NO institutional lockup, NO screenshot. The instrument
    is named in *plain type*; every glyph — including the "AI" badge — is drawn
    here and is deliberately GENERIC, so it can never be mistaken for the
    official Code-of-Practice icon set.
  - The `badge` state's "photo" is a drawn abstract field, never a stock image:
    a mock of a labelled picture must not put a real photographer's frame (or a
    real person's face) under the word "deepfake".
  - Attribution + date INSIDE the caption-safe band, never in the bottom-300
    chip zone where an overlay could sit on it.
  - Nothing meaningful above y=200 or below the y1420 caption band.
  - Colour is the argument: magenta = fully synthetic, yellow = human work an
    AI touched. The same two colours carry that meaning in every state, so the
    distinction reads with the sound off.

  make_label_mock.py --mode badge|inforce|kinds|penalty -o out.png
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from make_doc_mock import (
    S, W, H, SAFE_TOP, CAPTION_TOP,
    MAGENTA, YELLOW, GREEN, TXT, DIM, FAINT, CARD,
    bg, font, tw, tracked, tracked_w,
)

# Real, published facts on the face of the graphic => ATTRIBUTION, not
# "illustrative". Plain type names the instrument; no emblem. See docstring.
SOURCE = "SOURCE: EU AI ACT ART. 50 — APPLICABLE 2 AUGUST 2026"
SLUG = "REGULATION (EU) 2024/1689  ·  ARTICLE 50"

RED = (255, 106, 106)


def source_footer(d, y):
    """Attribution — asserted inside the caption-safe band (§13 disclosure rule)."""
    f = font("display", 25)
    w = tracked_w(d, SOURCE, f, 3.4)
    tracked(d, ((W * S - w) // 2, y * S), SOURCE, f, FAINT, 3.4)
    assert y + 28 <= CAPTION_TOP, f"source line at {y} is under the caption band"


def pill(d, x, y, text, col, px=28, pad=(28, 15), track=2.4):
    """A status pill sized from the MEASURED tracked width.

    The first render hardcoded the right edge and "UNLABELLED DEEPFAKES" ran its
    last letter through the border — the §4 overlay-covers-content failure
    wearing a hat, on the one chip naming the enforcement target. Never guess a
    chip's width when the string is a variable.
    """
    f = font("ui_sb", px)
    w = tracked_w(d, text, f, track)
    d.rounded_rectangle([x * S, y * S, x * S + w + 2 * pad[0] * S, (y + px + 2 * pad[1]) * S],
                        radius=18 * S, fill=col + (34,), outline=col, width=2 * S)
    tracked(d, (x * S + pad[0] * S, (y + pad[1] + 1) * S), text, f, col, track)
    return y + px + 2 * pad[1]


def instrument_head(d, y, label=SLUG):
    """A drawn statute glyph + the instrument in plain type. Never an emblem."""
    d.rounded_rectangle([72 * S, y * S, 122 * S, (y + 64) * S], radius=8 * S,
                        outline=MAGENTA, width=3 * S)
    for i in range(3):
        d.line([(84 * S, (y + 18 + i * 15) * S), (110 * S, (y + 18 + i * 15) * S)],
               fill=(96, 96, 116), width=3 * S)
    tracked(d, (146 * S, (y + 18) * S), label, font("ui_sb", 25), DIM, 2.6)
    return y + 104


def ai_badge(d, box, col=MAGENTA, filled=True):
    """The generic label chip. Deliberately NOT the official icon set — a drawn
    rounded square with the letters A I, in our own palette."""
    x0, y0, x1, y1 = [v * S for v in box]
    r = int((y1 - y0) * 0.28)
    d.rounded_rectangle([x0, y0, x1, y1], radius=r,
                        fill=col + (54,) if filled else None,
                        outline=col, width=4 * S)
    f = font("display", int((y1 - y0) / S * 0.50))
    label = "AI"
    wpx = tracked_w(d, label, f, 4.0)
    # optical centring: Anton's em box sits low, so nudge up off the caps height
    bb = d.textbbox((0, 0), label, font=f)
    tracked(d, (x0 + ((x1 - x0) - wpx) / 2, y0 + ((y1 - y0) - (bb[3] - bb[1])) / 2 - bb[1]),
            label, f, col, 4.0)


def display_lines(d, x, y, lines, px, fill, lead=1.16):
    """Anton lines on a MEASURED advance (§13: guessing the advance is how a
    highlight box lands on the tail of the line above it)."""
    f = font("display", px)
    adv = int(round(px * lead))
    for ln in lines:
        d.text((x * S, y * S), ln, font=f, fill=fill)
        y += adv
    return y


def hilite_line(d, x, y, text, px, box=YELLOW, ink=(28, 22, 6), pad=(18, 9)):
    """A highlighted display line whose chip hugs the REAL ink box (textbbox
    measures, never draws — the ghost-ink lesson)."""
    f = font("display", px)
    bb = d.textbbox((x * S, y * S), text, font=f)
    px_, py_ = pad[0] * S, pad[1] * S
    d.rounded_rectangle([bb[0] - px_, bb[1] - py_, bb[2] + px_, bb[3] + py_],
                        radius=14 * S, fill=box)
    d.text((x * S, y * S), text, font=f, fill=ink)
    return (bb[3] + py_) / S


def media_tile(d, y, h=520):
    """A DRAWN stand-in for a piece of published media.

    Never a stock photo and never a face: this tile is what the word "deepfake"
    ends up pointing at, and putting a real person's frame there would assert
    something about that person. An abstract field asserts nothing.
    """
    x0, x1 = 72, 1008
    d.rounded_rectangle([x0 * S, y * S, x1 * S, (y + h) * S], radius=28 * S,
                        fill=CARD, outline=(52, 44, 66), width=3 * S)
    # abstract "content": soft magenta/violet arcs, no subject, no horizon
    for i, (cx, cy, r, col, a) in enumerate((
            (300, 0.42, 210, MAGENTA, 74), (640, 0.62, 260, (140, 90, 220), 64),
            (830, 0.34, 150, YELLOW, 44), (470, 0.78, 190, MAGENTA, 40))):
        yy = y + h * cy
        d.ellipse([(cx - r) * S, (yy - r) * S, (cx + r) * S, (yy + r) * S],
                  fill=col + (a,))
    ai_badge(d, (x1 - 148, y + h - 148, x1 - 28, y + h - 28))
    return y + h


# ---------------------------------------------------------------- states ----
def m_badge(d, **_):
    """The hook's frozen frame: a piece of media wearing the label."""
    y = instrument_head(d, 250, "WHAT YOU WILL START SEEING")
    y = media_tile(d, y) + 52
    y = display_lines(d, 72, y, ("THAT LITTLE BADGE",), 88, TXT)
    y = hilite_line(d, 82, y, "IS THE LAW NOW", 88) + 46
    d.text((72 * S, y * S), "on images, video, audio and text a system generates",
           font=font("ui", 36), fill=DIM)
    source_footer(d, y + 108)


def m_inforce(d, **_):
    """The date, and the thing everyone gets wrong: what was deferred was not this."""
    y = instrument_head(d, 300)
    y += 10
    y = pill(d, 72, y, "APPLICABLE NOW", GREEN) + 52

    y = display_lines(d, 72, y, ("TRANSPARENCY DUTIES",), 88, TXT)
    y = hilite_line(d, 82, y, "SINCE 2 AUG 2026", 88) + 54

    for col, ln in ((GREEN, "enforceable by national authorities"),
                    (GREEN, "not delayed by the Digital Omnibus"),
                    (YELLOW, "one grace: machine-readable marking on")):
        d.ellipse([76 * S, (y + 16) * S, 92 * S, (y + 32) * S], fill=col)
        d.text((116 * S, y * S), ln, font=font("ui", 36), fill=DIM)
        y += 58
    d.text((116 * S, y * S), "systems already on sale — to 2 Dec 2026",
           font=font("ui", 36), fill=DIM)
    source_footer(d, y + 122)


def m_kinds(d, **_):
    """The two label classes. Colour is the argument (§13).

    The inner label stays the INSTRUMENT, not a restatement of the beat: the
    step chip over this beat already reads "TWO KINDS OF LABEL", and the first
    cut put that exact string on the frame three times (chip + chrome header +
    this line). An overlay does not have to *cover* content to be a defect —
    duplicating it is the same §4 failure with the volume turned down.
    """
    y = instrument_head(d, 286)
    y += 16
    for title, sub, col, filled in (
        ("FULLY AI-GENERATED", "the whole thing came out of a model", MAGENTA, True),
        ("AI-ASSISTED", "real work, edited or touched up by AI", YELLOW, False),
    ):
        # 224 tall, not 292: the first render left ~70px of dead frame under the
        # sub-line in both cards, which reads as a layout accident rather than
        # air. Height is derived from the badge (120) + its two 40px insets.
        d.rounded_rectangle([72 * S, y * S, 1008 * S, (y + 224) * S], radius=32 * S,
                            fill=CARD, outline=col + (110,), width=3 * S)
        ai_badge(d, (116, y + 52, 236, y + 172), col, filled)
        f = font("display", 60)
        d.text((280 * S, (y + 54) * S), title, font=f, fill=TXT)
        assert 280 * S + tw(d, title, f) < 992 * S, f"card title overruns: {title}"
        fs = font("ui", 32)
        d.text((280 * S, (y + 132) * S), sub, font=fs, fill=DIM)
        # assert the SUB too, not just the title — the first pass only guarded
        # the display line and the longer sub-line was the one that crowded the
        # card edge.
        assert 280 * S + tw(d, sub, fs) < 992 * S, f"card sub overruns: {sub}"
        y += 268
    y += 8
    d.text((72 * S, y * S), "both carry a label. only one is fully synthetic.",
           font=font("ui", 38), fill=TXT)
    source_footer(d, y + 116)


def m_penalty(d, **_):
    """The enforcement target and the ceiling."""
    y = instrument_head(d, 300, "WHAT ENFORCEMENT GOES AFTER")
    y += 8
    y = pill(d, 72, y, "UNLABELLED DEEPFAKES", RED) + 56

    y = display_lines(d, 72, y, ("PENALTIES REACH",), 88, TXT)
    y = hilite_line(d, 82, y, "€15M", 88) + 40
    d.text((72 * S, y * S), "or 3% of worldwide annual turnover —",
           font=font("ui", 38), fill=DIM)
    d.text((72 * S, (y + 54) * S), "whichever is higher.",
           font=font("ui", 38), fill=DIM)
    y += 138
    d.line([(72 * S, y * S), (72 * S, (y + 116) * S)], fill=YELLOW, width=6 * S)
    d.text((116 * S, (y + 4) * S), "the duty is on whoever", font=font("ui", 40), fill=YELLOW)
    d.text((116 * S, (y + 60) * S), "publishes it, not just the model.",
           font=font("ui", 40), fill=YELLOW)
    source_footer(d, y + 200)


# Chrome headers are deliberately DISTINCT from the step-chip labels an episode
# is likely to put over these beats (see m_kinds' docstring) — "IN FORCE — NOT
# DEFERRED" and "THE ENFORCEMENT TARGET" both moved here after the first cut
# landed them next to an identical chip.
HEADERS = {"badge": "CONTENT LABELS",
           "inforce": "THE DATE THAT MATTERS",
           "kinds": "READING THE LABEL",
           "penalty": "PENALTIES"}

MODES = {"badge": m_badge, "inforce": m_inforce, "kinds": m_kinds, "penalty": m_penalty}


def build(mode, out, **kw):
    """Body on its own layer, centred in the safe band (same solver as its
    siblings — each state has a different block height, so a fixed start-y
    leaves one balanced and the next hugging the top). The header is chrome and
    stays pinned above y=200 so a step chip may legally sit on it."""
    from make_doc_mock import header as chrome_header

    canvas = bg((W * S, H * S))
    layer = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    MODES[mode](ImageDraw.Draw(layer, "RGBA"), **kw)

    box = layer.getbbox()
    if box:
        _, top_px, _, bot_px = box
        block_h = bot_px - top_px
        want_top = SAFE_TOP * S + ((CAPTION_TOP - SAFE_TOP) * S - block_h) // 2
        dy = int(want_top - top_px)
        if dy:
            shifted = Image.new("RGBA", layer.size, (0, 0, 0, 0))
            shifted.paste(layer.crop((0, top_px, W * S, bot_px)), (0, top_px + dy))
            layer = shifted
        # A mock is authored, not captured — there is no excuse for content under
        # the karaoke caption band (§4, Ep26). Fail the render instead.
        assert want_top >= SAFE_TOP * S, f"{mode}: block starts above the safe band"
        assert want_top + block_h <= CAPTION_TOP * S, \
            f"{mode}: block ends at y{(want_top+block_h)/S:.0f}, under the caption band"

    head = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    chrome_header(ImageDraw.Draw(head, "RGBA"), HEADERS[mode])
    canvas = Image.alpha_composite(canvas.convert("RGBA"),
                                   Image.alpha_composite(head, layer)).convert("RGB")
    canvas.resize((W, H), Image.LANCZOS).save(out, "PNG")
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
