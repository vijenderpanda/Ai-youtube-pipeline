#!/usr/bin/env python3
"""EP14 in-house AUTONOMOUS-SCREENING mock (1080x1920), 2 states.

Fourth sibling of the in-house-mock family (data -> StatBars, chat ->
make_chat_mock, documents -> make_doc_mock, evaluation -> make_report_mock).
This one mocks a **clinical screening result surface** for the "an AI can
legally diagnose you" episode.

COMPLIANCE (playbook §13, and the brief's own hard constraints):
  - The numbers ON THIS GRAPHIC ARE INVENTED (a generic patient, a generic
    lesion score) => it wears the ILLUSTRATIVE footer, NOT an attribution line.
    The episode's REAL, SOURCED figures live on the StatBars beat instead,
    which carries its own attribution. Getting that split backwards in either
    direction is the compliance failure (see make_report_mock's docstring).
  - NO FDA seal, NO vendor name, NO device logo, NO screenshot. The regulator
    and the device class are described in plain type or not at all.
  - "NOT MEDICAL ADVICE" is drawn on the `limits` state, which is the beat that
    sets up the payoff rule.
  - Nothing meaningful above y=200 or below the y1420 caption band (asserted by
    make_doc_mock.build's safe-band checks, which we reuse wholesale).

Chrome headers are chosen to be DISTINCT from the chip/pip labels this episode
puts over them (playbook #29: printing the same string twice is a §4 defect
even when nothing is occluded).

  gen_ep14_mock.py --mode scan|limits -o out.png
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
FOOTER = "ILLUSTRATIVE MOCK · NOT A REAL PATIENT RESULT · NOT MEDICAL ADVICE"


def footer(d, y):
    """ILLUSTRATIVE disclosure — asserted inside the caption-safe band."""
    f = font("display", 25)
    w = tracked_w(d, FOOTER, f, 3.2)
    tracked(d, ((W * S - w) // 2, y * S), FOOTER, f, FAINT, 3.2)
    assert y + 28 <= SAFE_BOT, f"footer at {y} breaks the caption-safe band"


def retina_glyph(d, box, accent):
    """A DRAWN fundus image — never a stock photo, never a device capture."""
    x0, y0, x1, y1 = [v * S for v in box]
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    r = min(x1 - x0, y1 - y0) // 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(46, 22, 14),
              outline=(78, 40, 26), width=3 * S)
    # optic disc
    d.ellipse([cx + r // 3, cy - r // 5, cx + r // 3 + r // 4, cy + r // 20 + r // 5],
              fill=(150, 104, 58))
    # vessel tree, drawn not traced — arcs stay strictly inside the globe
    import math
    for base_deg in (150, 210, 30, 330):
        px, py = cx + int(0.30 * r * math.cos(math.radians(base_deg % 360))), cy
        ang = base_deg
        for i in range(5):
            ang += 14 if base_deg in (150, 30) else -14
            step = 0.11 * r
            nx = px + int(step * math.cos(math.radians(ang)))
            ny = py + int(step * math.sin(math.radians(ang)))
            # clamp to 0.82r so a vessel can never leave the fundus
            dx, dy = nx - cx, ny - cy
            dist = math.hypot(dx, dy)
            if dist > 0.82 * r:
                k = (0.82 * r) / dist
                nx, ny = cx + int(dx * k), cy + int(dy * k)
            d.line([(px, py), (nx, ny)], fill=(126, 44, 40), width=max(2, (5 - i)) * S)
            px, py = nx, ny
    # the flagged micro-lesions the screen is about
    for lx, ly in ((-0.35, -0.28), (-0.12, 0.34), (0.18, -0.42), (-0.48, 0.12)):
        ex, ey = cx + int(lx * r), cy + int(ly * r)
        d.ellipse([ex - 7 * S, ey - 7 * S, ex + 7 * S, ey + 7 * S], fill=accent)
        d.ellipse([ex - 17 * S, ey - 17 * S, ex + 17 * S, ey + 17 * S],
                  outline=accent + (150,), width=2 * S)


def pill(d, box, text, col, filled=False, px=28, right=None):
    """Pill sized to its TEXT — a fixed box silently clips a longer label.

    `right` right-aligns the pill to that x instead of growing from x0.
    """
    x0, y0, _, y1 = [v * S for v in box]
    f = font("ui_sb", px)
    w = int(tw(d, text, f)) + 44 * S
    if right is not None:
        x0 = right * S - w
    x1 = x0 + w
    d.rounded_rectangle([x0, y0, x1, y1], radius=(y1 - y0) // 2,
                        fill=col if filled else col + (34,), outline=col, width=2 * S)
    d.text((x0 + 22 * S, y0 + ((y1 - y0) - int(px * 1.22) * S) // 2),
           text, font=f, fill=INK_TOP if filled else col)
    return x1 // S


def m_scan(d, **_):
    """The result surface: a machine read a scan and issued a referral itself."""
    y = 286
    d.text((72 * S, y * S), "retinal image · left eye", font=font("ui", 32), fill=DIM)
    y += 66

    d.rounded_rectangle([72 * S, y * S, 1008 * S, (y + 470) * S], radius=32 * S,
                        fill=CARD, outline=CARD_EDGE, width=2 * S)
    retina_glyph(d, (128, y + 46, 508, y + 424), YELLOW)

    tx = 556
    d.text((tx * S, (y + 62) * S), "RESULT", font=font("display", 26), fill=FAINT)
    d.text((tx * S, (y + 106) * S), "MORE THAN", font=font("ui_sb", 44), fill=YELLOW)
    d.text((tx * S, (y + 158) * S), "MILD DISEASE", font=font("ui_sb", 44), fill=YELLOW)
    pill(d, (tx, y + 226, tx + 250, y + 284), "REFER TO A DOCTOR", YELLOW)

    d.text((tx * S, (y + 322) * S), "4 lesions flagged", font=font("ui", 30), fill=DIM)
    d.text((tx * S, (y + 366) * S), "result in 60 seconds", font=font("ui", 30), fill=DIM)
    y += 470 + 20

    # Disclosure sits DIRECTLY under the result card, not floating at the block
    # bottom. This beat plays in the newsSplit pane, which crops the bottom of
    # the mock — a block-bottom footer got sliced in half on the ep14 preview
    # (host pane below it). A disclosure that is only half legible is not a
    # disclosure, so it is anchored to the content it disclaims.
    footer(d, y)
    y += 54

    # the whole point of the beat: no human in the loop
    d.rounded_rectangle([72 * S, y * S, 1008 * S, (y + 132) * S], radius=26 * S,
                        fill=(53, 16, 31), outline=MAGENTA + (140,), width=2 * S)
    d.text((116 * S, (y + 26) * S), "READ BY", font=font("display", 25), fill=FAINT)
    d.text((116 * S, (y + 62) * S), "software, on its own", font=font("ui_sb", 40), fill=TXT)
    pill(d, (0, y + 40, 0, y + 96), "NO CLINICIAN", MAGENTA, right=964)


def m_limits(d, **_):
    """What the clearance actually covers — the setup for the payoff rule."""
    y = 320
    d.text((72 * S, y * S), "what the clearance covers", font=font("ui", 34), fill=DIM)
    y += 86

    rows = [("SCREEN YOU", "CLEARED", GREEN, True),
            ("FLAG A RISK", "CLEARED", GREEN, True),
            ("DIAGNOSE THE REST OF YOU", "NOT CLEARED", RED, False),
            ("TREAT YOU", "NOT CLEARED", RED, False)]
    for label, state, col, ok in rows:
        d.rounded_rectangle([72 * S, y * S, 1008 * S, (y + 128) * S], radius=26 * S,
                            fill=CARD, outline=CARD_EDGE, width=2 * S)
        # tick / cross, drawn
        cx, cy = 132 * S, (y + 64) * S
        d.ellipse([cx - 26 * S, cy - 26 * S, cx + 26 * S, cy + 26 * S],
                  outline=col, width=3 * S)
        if ok:
            d.line([(cx - 12 * S, cy), (cx - 3 * S, cy + 11 * S)], fill=col, width=4 * S)
            d.line([(cx - 3 * S, cy + 11 * S), (cx + 13 * S, cy - 11 * S)], fill=col, width=4 * S)
        else:
            d.line([(cx - 11 * S, cy - 11 * S), (cx + 11 * S, cy + 11 * S)], fill=col, width=4 * S)
            d.line([(cx + 11 * S, cy - 11 * S), (cx - 11 * S, cy + 11 * S)], fill=col, width=4 * S)

        d.text((190 * S, (y + 44) * S), label, font=font("ui_sb", 36),
               fill=TXT if ok else DIM)
        f_s = font("ui_sb", 26)
        sw = tw(d, state, f_s) + 44 * S
        d.rounded_rectangle([1008 * S - 44 * S - sw, (y + 40) * S,
                             1008 * S - 44 * S, (y + 88) * S],
                            radius=24 * S, fill=col + (36,), outline=col, width=2 * S)
        d.text((1008 * S - 44 * S - sw + 22 * S, (y + 47) * S), state, font=f_s, fill=col)
        y += 150

    y += 26
    d.text((72 * S, y * S), "A screen is a question.", font=font("ui", 40), fill=TXT)
    d.text((72 * S, (y + 56) * S), "A diagnosis is an answer.", font=font("ui", 40), fill=TXT)
    footer(d, y + 168)


HEADERS = {"scan": "SCREENING RESULT", "limits": "SCOPE OF CLEARANCE"}
MODES = {"scan": m_scan, "limits": m_limits}


def build(mode, out):
    """Body on a transparent layer, then centred in the safe band (see make_doc_mock)."""
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
