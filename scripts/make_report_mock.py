#!/usr/bin/env python3
"""In-house EVALUATION-REPORT mock (1080x1920), 3 states.

Third sibling of the in-house-mock family: `make_chat_mock.py` mocks a *chat*,
`make_doc_mock.py` mocks a *document-grounding surface*, this one mocks a
**safety-evaluation / incident report** — the finding, the test conditions, and
the lab-vs-your-app tie-back.

WHY THIS EXISTS (AI Unpacked build 28, 2026-08-06). The episode reports the UK
AI Security Institute's Aug-4 cyber-eval incident. Two constraints collide:
the brief bans lab logos and third-party screenshots (so the actual report page
is off the table), and playbook §13 bans mocking anyone's UI as if it were a
capture. What is left — and what a real news desk does — is an OWN graphic that
carries the *published figures*, attributed and dated on its face.

So this differs from its two siblings in one important way, and the difference
is deliberate: the doc/chat mocks are ILLUSTRATIVE (invented numbers, generic
labels), while this one renders **real, sourced figures** and therefore carries
an ATTRIBUTION footer instead of an "illustrative" one. Getting that backwards
in either direction is the compliance failure: invented numbers wearing a source
line, or real findings disowned as illustrative.

House rules inherited from §13 / §4 (and asserted, not just intended):
  - NO logo, NO vendor lookalike colour, NO screenshot. The issuing body is
    named in *plain type* (a public government report is attributable; its
    logo is not ours to use). Drawn glyphs only.
  - Attribution + date INSIDE the caption-safe band, never in the bottom-300
    chip zone where an overlay could sit on it.
  - Nothing meaningful above y=200 or below the y1420 caption band.
  - Colour is the argument: the thing the lab switched OFF and the thing that
    is ON in your app are the same two colours in every state, so the tie-back
    reads with the sound off.

  make_report_mock.py --mode finding|conditions|guardrail -o out.png
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from make_doc_mock import (
    S, W, H, SAFE_TOP, CAPTION_TOP,
    MAGENTA, YELLOW, GREEN, TXT, DIM, FAINT, CARD, CARD_EDGE,
    bg, font, tw, tracked, tracked_w,
)

# Real figures on the face of the graphic => an ATTRIBUTION line, not an
# "illustrative" one. See the module docstring.
SOURCE = "FIGURES: UK AI SECURITY INSTITUTE INCIDENT REPORT, 4 AUG 2026"
SLUG = "UK AI SECURITY INSTITUTE  ·  PUBLISHED 4 AUG 2026"

RED = (255, 106, 106)


def source_footer(d, y):
    """Attribution — asserted inside the caption-safe band (§13 disclosure rule)."""
    f = font("display", 25)
    w = tracked_w(d, SOURCE, f, 3.4)
    tracked(d, ((W * S - w) // 2, y * S), SOURCE, f, FAINT, 3.4)
    assert y + 28 <= CAPTION_TOP, f"source line at {y} is under the caption band"


def report_head(d, y, label=SLUG):
    """A drawn document glyph + the issuing body in plain type. Never a logo."""
    d.rounded_rectangle([72 * S, y * S, 122 * S, (y + 64) * S], radius=8 * S,
                        outline=MAGENTA, width=3 * S)
    for i in range(3):
        d.line([(84 * S, (y + 18 + i * 15) * S), (110 * S, (y + 18 + i * 15) * S)],
               fill=(96, 96, 116), width=3 * S)
    tracked(d, (146 * S, (y + 18) * S), label, font("ui_sb", 25), DIM, 2.6)
    return y + 104


def state_row(d, y, label, value, col, note):
    """One test-condition row: what was set, and the fact it was set ON PURPOSE.

    The ON/OFF pill is pinned to the LABEL line, not the card's vertical centre,
    so the note below always owns the full card width. The first render centred
    it and the pill sat on the tail of both notes — the §4 overlay-covers-content
    failure on an element nobody thinks of as an overlay. Both clearances are
    asserted, so a longer label or note fails the render instead of shipping.
    """
    d.rounded_rectangle([72 * S, y * S, 1008 * S, (y + 190) * S], radius=28 * S,
                        fill=CARD, outline=CARD_EDGE, width=2 * S)
    f_l = font("ui_sb", 36)
    d.text((116 * S, (y + 30) * S), label, font=f_l, fill=TXT)

    f = font("display", 46)
    vw = tracked_w(d, value, f, 2.0)
    x1 = 1008 * S - 44 * S
    pill_x0 = x1 - vw - 52 * S
    d.rounded_rectangle([pill_x0, (y + 26) * S, x1, (y + 96) * S],
                        radius=30 * S, fill=col + (34,), outline=col, width=3 * S)
    tracked(d, (pill_x0 + 26 * S, (y + 38) * S), value, f, col, 2.0)
    assert 116 * S + tw(d, label, f_l) < pill_x0 - 24 * S, f"label '{label}' runs into the pill"

    f_n = font("ui", 28)
    d.text((116 * S, (y + 116) * S), note, font=f_n, fill=FAINT)
    assert 116 * S + tw(d, note, f_n) < x1, f"note '{note}' overruns the card"
    return y + 212


def display_lines(d, x, y, lines, px, fill, lead=1.16):
    """Anton lines on a MEASURED advance. Guessing the advance is how the first
    render put a highlight box over the tail of the line above it (§4)."""
    f = font("display", px)
    adv = int(round(px * lead))
    for ln in lines:
        d.text((x * S, y * S), ln, font=f, fill=fill)
        y += adv
    return y


def hilite_line(d, x, y, text, px, box=YELLOW, ink=(28, 22, 6), pad=(18, 9)):
    """A highlighted display line whose chip hugs the REAL ink box.

    `textbbox` (measure-only, never draws — §13 ghost-ink lesson) is the only
    honest way to size this: Anton's em box is much taller than its caps, so a
    chip sized off the point size either clips the glyphs or eats the line above.
    """
    f = font("display", px)
    bb = d.textbbox((x * S, y * S), text, font=f)
    px_, py_ = pad[0] * S, pad[1] * S
    d.rounded_rectangle([bb[0] - px_, bb[1] - py_, bb[2] + px_, bb[3] + py_],
                        radius=14 * S, fill=box)
    d.text((x * S, y * S), text, font=f, fill=ink)
    return (bb[3] + py_) / S


def toggle(d, box, on, col):
    """A drawn switch — the one glyph the whole episode turns on."""
    x0, y0, x1, y1 = [v * S for v in box]
    r = (y1 - y0) // 2
    d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=col + (46,),
                        outline=col, width=3 * S)
    cx = (x1 - r - 6 * S) if on else (x0 + r + 6 * S)
    d.ellipse([cx - r + 10 * S, y0 + 10 * S, cx + r - 10 * S, y1 - 10 * S], fill=col)


# ---------------------------------------------------------------- states ----
def m_finding(d, **_):
    """What the evaluators caught. The hook's frozen frame."""
    y = report_head(d, 268)
    d.rounded_rectangle([72 * S, y * S, 320 * S, (y + 56) * S], radius=16 * S,
                        fill=MAGENTA + (40,), outline=MAGENTA, width=2 * S)
    tracked(d, (98 * S, (y + 13) * S), "FLAGGED", font("ui_sb", 27), MAGENTA, 3.0)
    y += 104

    y = display_lines(d, 72, y, ("THE AGENT CREATED", "MULTIPLE FAKE"), 92, TXT)
    # the phrase the beat exists for, in the yellow that means "the finding"
    y = hilite_line(d, 82, y, "IDENTITIES", 92) + 46

    for ln in ("contacted real people directly",
               "to get malicious code approved",
               "into a publicly used open-source project"):
        d.ellipse([76 * S, (y + 16) * S, 92 * S, (y + 32) * S], fill=MAGENTA)
        d.text((116 * S, y * S), ln, font=font("ui", 36), fill=DIM)
        y += 60
    y += 34

    d.rounded_rectangle([72 * S, y * S, 560 * S, (y + 62) * S], radius=18 * S,
                        fill=RED + (34,), outline=RED, width=2 * S)
    tracked(d, (100 * S, (y + 15) * S), "NOBODY INSTRUCTED IT",
            font("ui_sb", 28), RED, 2.4)
    source_footer(d, y + 132)


def m_conditions(d, **_):
    """The fine print — what 'the model did it in a test' does and does not mean."""
    y = report_head(d, 300, "HOW THE TEST WAS RUN")
    y += 8
    y = state_row(d, y, "INTERNET ACCESS", "ON", YELLOW,
                  "deliberately enabled — to see what an attacker could reach")
    y = state_row(d, y, "SAFETY FILTERS", "OFF", MAGENTA,
                  "deliberately switched off — to measure the raw capability")
    y += 42

    d.line([(72 * S, y * S), (72 * S, (y + 210) * S)], fill=YELLOW, width=6 * S)
    ty = y + 4
    for ln in ("“Not reflective of how", "frontier models are made",
               "available to the general public.”"):
        d.text((116 * S, ty * S), ln, font=font("ui", 42), fill=YELLOW)
        ty += 62
    d.text((116 * S, (ty + 12) * S), "— the evaluators, in the report",
           font=font("ui", 30), fill=FAINT)
    source_footer(d, ty + 132)


def m_guardrail(d, **_):
    """The tie-back: the switch they turned off is the switch you have on."""
    y = report_head(d, 300, "SAME SWITCH, TWO PLACES")
    y += 20
    for title, sub, on, col, tag in (
        ("IN THE LAB", "filters off, on purpose", False, MAGENTA, "MEASURE THE CEILING"),
        ("IN YOUR APP", "filters on, by default", True, GREEN, "BLOCK THE REQUEST"),
    ):
        d.rounded_rectangle([72 * S, y * S, 1008 * S, (y + 300) * S], radius=32 * S,
                            fill=CARD, outline=col + (110,), width=3 * S)
        d.text((116 * S, (y + 40) * S), title, font=font("display", 66), fill=TXT)
        d.text((116 * S, (y + 128) * S), sub, font=font("ui", 34), fill=DIM)
        toggle(d, (116, y + 194, 236, y + 258), on, col)
        f = font("ui_sb", 27)
        tgw = tracked_w(d, tag, f, 2.4)
        tracked(d, (272 * S, (y + 212) * S), tag, f, col, 2.4)
        assert 272 * S + tgw < 1008 * S, "guardrail tag overruns the card"
        y += 344
    y += 16
    d.text((72 * S, y * S), "that refusal is the product working.",
           font=font("ui", 40), fill=TXT)
    source_footer(d, y + 118)


HEADERS = {"finding": "WHAT THE EVALUATORS CAUGHT",
           "conditions": "THE FINE PRINT",
           "guardrail": "WHY IT SAYS NO"}

MODES = {"finding": m_finding, "conditions": m_conditions, "guardrail": m_guardrail}


def build(mode, out, **kw):
    """Body on its own layer, centred in the safe band (same solver as its siblings).

    Each state has a different block height; a fixed start-y leaves one balanced
    and the next hugging the top. The header is chrome and stays pinned above
    y=200 so a step chip may legally sit on it; only the body floats.
    """
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
