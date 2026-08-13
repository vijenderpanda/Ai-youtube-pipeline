#!/usr/bin/env python3
"""gen_brand.py — channel icon + banner for "Calm AI".

Mark = "Settled Signal": one sharp panic spike on the left that decays into a
slow breathing wave and comes to rest on a still dot. It IS the channel's thesis
(the scary version -> the calm one) in a shape that survives 32px, and it sits
apart from the siblings' hard teal chevron (Already Happening) and magenta
wordmark (AI Unpacked).

Two rejected passes, kept here so nobody re-walks them:
  1. Concentric arcs around a dot — at icon size it read as a generic
     wifi/broadcast glyph, i.e. a signal blasting outward: the opposite of the
     brand.
  2. Spike -> dead-flat line -> dot — clean, but a flatlining trace reads as
     death. Hence the decaying wave rather than a flat tail.

Run: python3 channels/calm-ai/gen_brand.py
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

INDIGO = (99, 102, 241)      # #6366F1 — locked channel accent
HI = (165, 180, 252)         # soft highlight
INK = (232, 234, 246)        # off-white type (no pure white on this channel)
MUTED = (148, 152, 178)
BG = (13, 14, 22)

OUT = "channels/calm-ai/assets/brand"
os.makedirs(OUT, exist_ok=True)


def font(sz, bold=True):
    cands = (["/System/Library/Fonts/Supplemental/Avenir Next.ttc",
              "/System/Library/Fonts/Supplemental/Arial Bold.ttf"] if bold else
             ["/System/Library/Fonts/Supplemental/Arial.ttf"])
    for p in cands:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def radial(w, h, cx, cy, inner, outer, r):
    yy, xx = np.mgrid[0:h, 0:w]
    dist = np.sqrt(((xx - cx) / w) ** 2 + ((yy - cy) / h) ** 2) / r
    t = np.clip(dist, 0, 1)[..., None]
    return (np.array(inner) * (1 - t) + np.array(outer) * t).astype("uint8")


def settled_signal(d, cx, cy, span, amp, w, col, dot=True):
    """Panic spike -> settles into a slow breathing wave -> still dot.

    The tail is deliberately a low wave, NOT a flat line: a flatlining trace
    reads as death, which is exactly the wrong feeling for this channel.
    """
    x0 = cx - span / 2
    x1 = cx + span / 2
    spike = [
        (x0, cy),                      # flat lead-in
        (x0 + span * 0.14, cy),
        (x0 + span * 0.22, cy - amp),  # the panic
        (x0 + span * 0.30, cy + amp * 0.52),
        (x0 + span * 0.38, cy),        # settled from here on
    ]
    # two slow, decaying breaths
    tail = []
    n = 60
    tx0, tx1 = x0 + span * 0.38, x1 - w * 1.9
    for i in range(n + 1):
        t = i / n
        x = tx0 + (tx1 - tx0) * t
        y = cy - amp * 0.17 * (1 - 0.5 * t) * np.sin(2 * np.pi * 1.0 * t)
        tail.append((x, y))
    pts = spike + tail
    # Stamp a round brush along the path instead of ImageDraw.line(width=…):
    # a wide polyline over densely-sampled curve points leaves visible mitre
    # nicks on every segment join, which shows up as hatching on the wave.
    r = w / 2
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        seg = max(1, int(np.hypot(bx - ax, by - ay) / max(1.0, r * 0.25)))
        for i in range(seg + 1):
            t = i / seg
            px, py = ax + (bx - ax) * t, ay + (by - ay) * t
            d.ellipse([px - r, py - r, px + r, py + r], fill=col)
    if dot:
        rr = w * 1.15
        ex, ey = tail[-1]
        d.ellipse([ex - rr, ey - rr, ex + rr, ey + rr], fill=col)


def icon():
    S = 800
    base = Image.fromarray(radial(S, S, S * 0.5, S * 0.44, (24, 26, 44), BG, 1.15), "RGB").convert("RGBA")
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    mark = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gd, md = ImageDraw.Draw(glow), ImageDraw.Draw(mark)
    for dd in (gd, md):
        settled_signal(dd, 400, 448, span=660, amp=205, w=50, col=INDIGO + (255,))
    # highlight the settled end — the eye should land on the calm, not the spike
    ex, ey = 400 + 660 / 2 - 50 * 1.9, 448
    md.ellipse([ex - 22, ey - 24, ex + 18, ey + 16], fill=HI + (255,))
    glow = glow.filter(ImageFilter.GaussianBlur(24))
    out = Image.alpha_composite(Image.alpha_composite(base, glow), mark)
    out.convert("RGB").save(f"{OUT}/icon.png", quality=95)

    prev = out.resize((160, 160), Image.LANCZOS)
    m = Image.new("L", (160, 160), 0)
    ImageDraw.Draw(m).ellipse([0, 0, 160, 160], fill=255)
    circ = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    circ.paste(prev, (0, 0), m)
    circ.convert("RGB").save(f"{OUT}/icon_circle160.png")
    # 32px legibility proof — if the mark muddies here, the mark is wrong
    circ.resize((32, 32), Image.LANCZOS).resize((160, 160), Image.NEAREST) \
        .convert("RGB").save(f"{OUT}/icon_32px_proof.png")
    print("icon.png + circle160 + 32px proof")


def draw_tracked(d, cx, y, text, f, fill, track):
    widths = [d.textlength(c, font=f) + track for c in text]
    total = sum(widths) - track
    x = cx - total / 2
    for c, w in zip(text, widths):
        d.text((x, y), c, font=f, fill=fill)
        x += w


def banner():
    W, H = 2560, 1440
    base = Image.fromarray(radial(W, H, W * 0.5, H * 0.5, (26, 28, 50), (9, 10, 16), 1.3), "RGB").convert("RGBA")
    # oversized, very faint mark behind the wordmark — texture, not decoration
    motif = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    mo = ImageDraw.Draw(motif)
    settled_signal(mo, W // 2, int(H * 0.50), span=1900, amp=430, w=30, col=INDIGO + (34,))
    motif = motif.filter(ImageFilter.GaussianBlur(5))
    im = Image.alpha_composite(base, motif)

    vig = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vig).ellipse([-W * 0.2, -H * 0.35, W * 1.2, H * 1.35], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(240))
    im = Image.composite(im, Image.alpha_composite(im, Image.new("RGBA", (W, H), (6, 7, 12, 140))), vig)

    d = ImageDraw.Draw(im)
    cx = W // 2
    # small mark above the wordmark. Layout is pinned inside YouTube's mobile-safe
    # band (middle 1546x423, i.e. y 509..931 on a 2560x1440 banner) — the first
    # pass floated the whole block ~100px above it and would have been cropped.
    sm = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    smd = ImageDraw.Draw(sm)
    settled_signal(smd, cx, int(H * 0.393), span=150, amp=50, w=11, col=INDIGO + (255,))
    im = Image.alpha_composite(im, sm)
    d = ImageDraw.Draw(im)

    draw_tracked(d, cx, int(H * 0.425), "CALM AI", font(132), INK + (255,), 26)
    draw_tracked(d, cx, int(H * 0.545), "AI NEWS, MINUS THE PANIC.", font(46, bold=False), MUTED + (255,), 8)

    sch = "NEW SHORTS   ·   MON / WED / FRI"
    f2 = font(38)
    tw = sum(d.textlength(c, font=f2) + 4 for c in sch) - 4
    y = int(H * 0.600)
    d.rounded_rectangle([cx - tw / 2 - 34, y - 10, cx + tw / 2 + 34, y + 62], radius=36,
                        outline=INDIGO + (210,), width=3)
    draw_tracked(d, cx, y, sch, f2, INDIGO + (255,), 4)
    im.convert("RGB").save(f"{OUT}/banner.png", quality=92)
    print("banner.png")


if __name__ == "__main__":
    icon()
    banner()
