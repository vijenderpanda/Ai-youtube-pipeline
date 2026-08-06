#!/usr/bin/env python3
"""In-house generic "chat with your documents" mock (1080x1920), 4 states.

Sibling of `make_chat_mock.py` (which mocks a *chat*); this one mocks the
document-grounding surface — sources, a cited answer, a compute cell, a rollout
board — for any beat about "give an AI your files".

WHY THIS EXISTS (AI Unpacked build 27, 2026-08-06). The episode's demo was
planned as a real screen recording of Google's Gemini Notebook. The plan-time
preflight (`record_demo.py --preflight`) came back **LOGGED_OUT**: the whole
product sits behind a Google sign-in the operator's recorder profile does not
have, and `--setup-profile` is a headed, human-only step. Playbook §10b's
standing rule — *never claim on camera what the account cannot show* — leaves
exactly one legal visual: an in-house mock.

House rules baked in (playbook §13 in-house-mock grammar, §4 caption safety):
  - NO vendor name, NO logo, NO lookalike colour, NO screenshot of anyone's UI.
    Neutral dark surface on the channel's own palette (magenta #E0218A + yellow).
  - An ILLUSTRATIVE footer INSIDE the caption-safe band (y<=1620), so an overlay
    chip can never cover the disclosure — the one thing that must stay readable.
  - Nothing meaningful above y=200 or below y=1620; those are the chip/caption
    dead zones.
  - Colour is the argument: the claim and the citation that grounds it are the
    SAME yellow, so the eye links them with the sound off — no arrows needed.
  - Supersample 2x, LANCZOS down, low-frequency dither only (§10c).

  make_doc_mock.py --mode sources|answer|compute|rollout -o out.png
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
    "mono": Path("/System/Library/Fonts/Menlo.ttc"),
}

MAGENTA = (224, 33, 138)
YELLOW = (255, 216, 77)
GREEN = (86, 214, 138)
INK_TOP = (11, 10, 16)
INK_BOT = (21, 16, 27)
TXT = (247, 247, 250)
DIM = (150, 150, 164)
FAINT = (104, 104, 120)
CARD = (23, 23, 32)
CARD_EDGE = (38, 38, 52)

FOOTER = "ILLUSTRATIVE — IN-HOUSE MOCK, NOT A PRODUCT SCREENSHOT"
SAFE_TOP, SAFE_BOT = 216, 1620
CAPTION_TOP = 1420   # karaoke band starts ~1440 (§4); nothing meaningful below this


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


def bg(size, glow_box=None):
    """Vertical ink gradient + a soft magenta bloom, low-frequency dither."""
    w, h = size
    top = np.array(INK_TOP, dtype=np.float32)
    bot = np.array(INK_BOT, dtype=np.float32)
    ramp = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None]
    img = np.repeat(top[None, None, :] * (1 - ramp) + bot[None, None, :] * ramp, w, axis=1)

    small = np.random.default_rng(27).normal(0, 3.0, (h // 40, w // 40)).astype(np.float32)
    up = Image.fromarray(np.clip(small + 128, 0, 255).astype(np.uint8)) \
        .resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(w // 90))
    img = np.clip(img + (np.array(up, dtype=np.float32)[:, :, None] - 128.0) * 0.30, 0, 255)
    base = Image.fromarray(img.astype(np.uint8), "RGB")

    glow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(glow).ellipse(
        glow_box or [int(-0.18 * w), int(0.38 * h), int(0.78 * w), int(0.74 * h)], fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(int(0.10 * w))).point(lambda v: int(v * 0.14))
    return Image.composite(Image.new("RGB", (w, h), MAGENTA), base, glow)


def header(d, label):
    """Decorative app chrome; lives ABOVE the safe band so a chip can sit on it."""
    d.rounded_rectangle([60 * S, 106 * S, 118 * S, 164 * S], radius=16 * S, fill=(29, 29, 40))
    d.rounded_rectangle([76 * S, 122 * S, 102 * S, 148 * S], radius=5 * S,
                        outline=MAGENTA, width=3 * S)
    tracked(d, (140 * S, 121 * S), label, font("ui_sb", 24), FAINT, 3.2)
    d.line([(0, 200 * S), (W * S, 200 * S)], fill=(30, 30, 42), width=2)


def footer(d, y):
    """ILLUSTRATIVE disclosure — asserted inside the caption-safe band."""
    f = font("display", 27)
    w = tracked_w(d, FOOTER, f, 4.0)
    tracked(d, ((W * S - w) // 2, y * S), FOOTER, f, FAINT, 4.0)
    assert y + 30 <= SAFE_BOT, f"footer at {y} breaks the caption-safe band"


def doc_card(d, box, name, meta, accent=None, tick=False):
    """A generic source card. Deliberately NOT a file-type logo — a drawn page."""
    x0, y0, x1, y1 = [v * S for v in box]
    d.rounded_rectangle([x0, y0, x1, y1], radius=26 * S, fill=CARD,
                        outline=(accent or CARD_EDGE) + ((150,) if accent else ()),
                        width=(3 if accent else 2) * S)
    # drawn page glyph (never a trademarked file icon)
    px0, py0 = x0 + 34 * S, y0 + 30 * S
    pw, ph = 54 * S, 68 * S
    d.rounded_rectangle([px0, py0, px0 + pw, py0 + ph], radius=8 * S,
                        outline=accent or (92, 92, 110), width=3 * S)
    for i in range(3):
        d.line([(px0 + 12 * S, py0 + (20 + i * 15) * S),
                (px0 + pw - 12 * S, py0 + (20 + i * 15) * S)],
               fill=accent or (72, 72, 90), width=3 * S)
    d.text((px0 + pw + 28 * S, y0 + 30 * S), name, font=font("ui_sb", 38), fill=TXT)
    d.text((px0 + pw + 28 * S, y0 + 76 * S), meta, font=font("ui", 28), fill=FAINT)
    if tick:
        cx, cy = x1 - 52 * S, (y0 + y1) // 2
        d.ellipse([cx - 22 * S, cy - 22 * S, cx + 22 * S, cy + 22 * S], fill=GREEN)
        d.line([(cx - 10 * S, cy), (cx - 2 * S, cy + 9 * S)], fill=INK_TOP, width=4 * S)
        d.line([(cx - 2 * S, cy + 9 * S), (cx + 11 * S, cy - 9 * S)], fill=INK_TOP, width=4 * S)


def cite_chip(d, xy, n):
    """A yellow [n] citation chip — the same yellow as the claim it grounds."""
    x, y = xy
    f = font("ui_sb", 26)
    label = str(n)
    w = tw(d, label, f) + 26 * S
    d.rounded_rectangle([x, y, x + w, y + 38 * S], radius=10 * S, fill=YELLOW)
    d.text((x + 13 * S, y + 2 * S), label, font=f, fill=(28, 22, 6))
    return x + w


# ---------------------------------------------------------------- states ----
def m_sources(d, reveal=2):
    """reveal 1 = the files have landed; reveal 2 = the question is asked.

    Two consecutive beats on the SAME still read as a freeze bug, and both of
    this episode's source beats are one still's worth of subject. A progressive
    reveal makes the second beat a real state change (files → question) instead
    of 7 seconds of frozen frame with a slow push over it.
    """
    y = 300
    d.text((72 * S, y * S), "3 sources added", font=font("ui", 34), fill=DIM)
    y += 70
    for name, meta in (("QUARTERLY-NUMBERS.PDF", "18 pages · uploaded"),
                       ("TEAM-NOTES.PDF", "6 pages · uploaded"),
                       ("EXPENSES.CSV", "412 rows · uploaded")):
        doc_card(d, (72, y, 1008, y + 132), name, meta, tick=True)
        y += 154
    if reveal < 2:
        footer(d, y + 60)
        return
    y += 46
    d.text((72 * S, y * S), "You asked", font=font("ui", 30), fill=FAINT)
    y += 52
    qx0, qy0 = 72, y
    lines = ["Which quarter grew fastest,", "and where is that in my files?"]
    qh = 24 + 62 * len(lines) + 24
    d.rounded_rectangle([qx0 * S, qy0 * S, 1008 * S, (qy0 + qh) * S], radius=32 * S,
                        fill=(53, 16, 31), outline=MAGENTA + (120,), width=2 * S)
    ty = qy0 + 24
    for ln in lines:
        d.text((qx0 * S + 38 * S, ty * S), ln, font=font("ui", 42), fill=TXT)
        ty += 62
    footer(d, qy0 + qh + 74)


def m_answer(d, **_):
    y = 290
    for name in ("QUARTERLY-NUMBERS.PDF", "TEAM-NOTES.PDF", "EXPENSES.CSV"):
        f = font("ui", 24)
        w = tw(d, name, f) + 34 * S
        d.rounded_rectangle([72 * S, y * S, 72 * S + w, (y + 44) * S], radius=14 * S,
                            fill=(28, 28, 38), outline=CARD_EDGE, width=2 * S)
        d.text((89 * S, (y + 7) * S), name, font=f, fill=DIM)
        y += 58
    y += 34

    ax0, ax1 = 72, 1008
    body = [("Q3 grew fastest — up ", None), ("18% on revenue", 1),
            (", driven by the new plan tier", None), (" the team notes flag", 2), (".", None)]
    # simple wrap over the styled runs, so a citation chip never orphans on a line
    f_a = font("ui", 44)
    lh = 66
    pad = 38
    laid, line, lx = [], [], 0.0
    maxw = (ax1 - ax0 - 2 * pad) * S
    for text, cite in body:
        for word in text.split(" "):
            if not word:
                continue
            wpx = tw(d, word + " ", f_a)
            if lx + wpx > maxw and line:
                laid.append(line); line, lx = [], 0.0
            line.append((word, None)); lx += wpx
        if cite:
            cw = tw(d, str(cite), font("ui_sb", 26)) + 26 * S + 8 * S
            if lx + cw > maxw and line:
                laid.append(line); line, lx = [], 0.0
            line.append((None, cite)); lx += cw
    if line:
        laid.append(line)

    ah = pad + lh * len(laid) + pad
    d.rounded_rectangle([ax0 * S, y * S, ax1 * S, (y + ah) * S], radius=32 * S,
                        fill=CARD, outline=CARD_EDGE, width=2 * S)
    ty = y + pad
    for ln in laid:
        tx = (ax0 + pad) * S
        for word, cite in ln:
            if cite:
                tx = cite_chip(d, (tx, ty * S + 10 * S), cite) + 8 * S
                continue
            hot = word.strip(",.").rstrip("%").replace("18", "18") and word.startswith("18%")
            col = YELLOW if word.startswith("18%") else TXT
            d.text((tx, ty * S), word + " ", font=f_a, fill=col)
            if col == YELLOW:  # the claim wears the citation's colour
                d.rounded_rectangle([tx, ty * S + 56 * S, tx + tw(d, word, f_a), ty * S + 63 * S],
                                    radius=3 * S, fill=YELLOW)
            tx += tw(d, word + " ", f_a)
        ty += lh
    y += ah + 40

    d.text((72 * S, y * S), "every claim traces back to a source", font=font("ui", 30), fill=FAINT)
    footer(d, y + 80)


def m_compute(d, **_):
    y = 300
    d.text((72 * S, y * S), "runs on your sources", font=font("ui", 34), fill=DIM)
    y += 76

    code = ["load('EXPENSES.CSV')",
            "by_quarter = group(rows, 'quarter')",
            "growth = pct_change(by_quarter.total)",
            "chart(growth)"]
    f_c = font("mono", 30)
    ch = 34 + 52 * len(code) + 34
    d.rounded_rectangle([72 * S, y * S, 1008 * S, (y + ch) * S], radius=26 * S,
                        fill=(15, 15, 22), outline=CARD_EDGE, width=2 * S)
    ty = y + 34
    for i, ln in enumerate(code):
        d.text((100 * S, ty * S), f"{i+1}", font=f_c, fill=(70, 70, 88))
        d.text((146 * S, ty * S), ln, font=f_c, fill=(198, 214, 232))
        ty += 52
    y += ch + 44

    # RUN pill + running state — our own magenta, no vendor control lookalike
    d.rounded_rectangle([72 * S, y * S, 300 * S, (y + 78) * S], radius=39 * S, fill=MAGENTA)
    cx, cy = 128 * S, (y + 39) * S
    d.polygon([(cx - 12 * S, cy - 18 * S), (cx - 12 * S, cy + 18 * S), (cx + 18 * S, cy)], fill=TXT)
    d.text((166 * S, (y + 18) * S), "RUN", font=font("ui_sb", 34), fill=TXT)
    d.text((330 * S, (y + 20) * S), "executing…", font=font("ui", 34), fill=YELLOW)
    y += 78 + 54

    d.text((72 * S, y * S), "It writes the code and runs it —", font=font("ui", 40), fill=TXT)
    d.text((72 * S, (y + 58) * S), "you never leave the notebook.", font=font("ui", 40), fill=TXT)
    footer(d, y + 160)


def m_rollout(d, **_):
    y = 320
    d.text((72 * S, y * S), "code execution rollout", font=font("ui", 34), fill=DIM)
    y += 90
    rows = [("TOP TIER", "AVAILABLE NOW", True),
            ("BUSINESS PLANS", "AVAILABLE NOW", True),
            ("PAID TIER", "COMING WEEKS", False),
            ("FREE TIER", "READ + CITE ONLY", False)]
    for label, state, live in rows:
        d.rounded_rectangle([72 * S, y * S, 1008 * S, (y + 128) * S], radius=26 * S,
                            fill=CARD, outline=CARD_EDGE, width=2 * S)
        d.text((116 * S, (y + 28) * S), label, font=font("ui_sb", 38), fill=TXT)
        col = GREEN if live else YELLOW
        f_s = font("ui_sb", 28)
        sw = tw(d, state, f_s) + 44 * S
        d.rounded_rectangle([1008 * S - 44 * S - sw, (y + 40) * S, 1008 * S - 44 * S, (y + 88) * S],
                            radius=24 * S, fill=col + (36,), outline=col, width=2 * S)
        d.text((1008 * S - 44 * S - sw + 22 * S, (y + 47) * S), state, font=f_s, fill=col)
        y += 150
    y += 30
    d.text((72 * S, y * S), "reading your files stayed free.", font=font("ui", 38), fill=TXT)
    footer(d, y + 110)


HEADERS = {"sources": "YOUR DOCUMENTS", "answer": "GROUNDED ANSWER",
           "compute": "CLOUD COMPUTER", "rollout": "WHO HAS IT"}

MODES = {"sources": m_sources, "answer": m_answer, "compute": m_compute, "rollout": m_rollout}


def build(mode, out, **kw):
    """Draw the body on its own transparent layer, then CENTRE it in the safe band.

    Each state has a different block height, so a fixed start-y leaves one state
    balanced and the next one hugging the top with 900px of dead frame below it
    (measured on the first `answer` render). The header is app chrome and stays
    pinned above y=200; only the body floats.
    """
    canvas = bg((W * S, H * S))
    ImageDraw.Draw(canvas, "RGBA")  # base for the gradient

    layer = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer, "RGBA")
    MODES[mode](dl, **kw)

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
        # SAFE_BOT is the outer bound, but the karaoke caption band itself sits at
        # y 1440-1517 (§4) — Ep26 shipped a caption sitting on the very sentence
        # its beat existed to prove. A mock is authored, not captured, so there is
        # no excuse for content under the band: fail the render instead.
        assert want_top >= SAFE_TOP * S, f"{mode}: block starts above the safe band"
        assert want_top + block_h <= CAPTION_TOP * S, \
            f"{mode}: block ends at y{(want_top+block_h)/S:.0f}, under the caption band"

    head = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    header(ImageDraw.Draw(head, "RGBA"), HEADERS[mode])
    canvas = Image.alpha_composite(canvas.convert("RGBA"),
                                   Image.alpha_composite(head, layer)).convert("RGB")
    canvas.resize((W, H), Image.LANCZOS).save(out, "PNG")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=sorted(MODES))
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--reveal", type=int, default=2,
                    help="sources mode: 1 = files only, 2 = files + the question")
    a = ap.parse_args()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    build(a.mode, out, **({"reveal": a.reveal} if a.mode == "sources" else {}))
    print("OK", out)


if __name__ == "__main__":
    main()
