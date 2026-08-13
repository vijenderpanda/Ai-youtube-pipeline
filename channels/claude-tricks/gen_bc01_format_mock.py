#!/usr/bin/env python3
"""Build Club FORMAT mockups (1080x1920) — frames to LOCK the Friday teaching
format before any bc01 production spend (VJ ideation request, 2026-08-13).

These are NOT episode assets — they are visual proposals for the Build Club
template layer that rides on the v16.4 engine. Two directions:

DIRECTION A — "BUILD RAIL" (evolution of the locked look):
  a_hook    result-first hook: live phone + Anton stack + chapter stamp
  a_step    teaching beat: persistent top progress rail + proof pane + chip
  a_pause   the PAUSE CARD: a beat DESIGNED to be paused + copied
  a_recipe  ending: screenshot-able recipe card + homework + next-chapter tease

DIRECTION B — "NOTEBOOK / BLUEPRINT" (bigger departure):
  b_chapter chapter-book opener on a blueprint grid
  b_step    step as an annotated blueprint card

House rules kept even in mockups: channel palette only, no vendor logos/UI,
nothing meaningful above y~200 (global header zone) or under the caption band.

  gen_bc01_format_mock.py --mode a_hook|a_step|a_pause|a_recipe|b_chapter|b_step -o out.png
"""
import argparse
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from make_doc_mock import (  # noqa: E402
    S, W, MAGENTA, YELLOW, GREEN, TXT, DIM, FAINT, CARD, CARD_EDGE,
    INK_TOP, bg, font, tw, tracked, tracked_w,
)

H = 1920
WHATS_GREEN = (37, 211, 102)
HOST_DIR = (Path(__file__).resolve().parent / "assets/character/host_library"
            / "outfit_11_sol_magenta")


def host_wide(im, box):
    """Real Sol still (locked Ep11 wardrobe) fitted into a rounded wide band."""
    x0, y0, x1, y1 = [v * S for v in box]
    tile = ImageOps.fit(Image.open(HOST_DIR / "wide.jpg").convert("RGB"),
                        (x1 - x0, y1 - y0), Image.LANCZOS)
    mask = Image.new("L", tile.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, tile.width, tile.height],
                                           radius=32 * S, fill=255)
    im.paste(tile, (x0, y0), mask)
    ImageDraw.Draw(im, "RGBA").rounded_rectangle(
        [x0, y0, x1, y1], radius=32 * S, outline=CARD_EDGE, width=2 * S)


def host_pip(im, cx, cy, size):
    """Circular Sol pip with the magenta ring — the v16.4 trust device."""
    px = size * S
    tile = ImageOps.fit(Image.open(HOST_DIR / "cropeed_center_final.jpeg")
                        .convert("RGB"), (px, px), Image.LANCZOS)
    mask = Image.new("L", (px, px), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, px, px], fill=255)
    im.paste(tile, (cx * S - px // 2, cy * S - px // 2), mask)
    ImageDraw.Draw(im, "RGBA").ellipse(
        [cx * S - px // 2, cy * S - px // 2, cx * S + px // 2, cy * S + px // 2],
        outline=MAGENTA, width=5 * S)


def star(d, cx, cy, r, col):
    """cx/cy in UNSCALED frame px — the center must be scaled too."""
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.45
        a = math.pi / 2 + i * math.pi / 5
        pts.append((cx * S + rr * math.cos(a) * S, cy * S - rr * math.sin(a) * S))
    d.polygon(pts, fill=col)


# ---------------------------------------------------------------- primitives
def header(d, right_pill="CH 1/6"):
    """Slim global header: series identity left, chapter stamp right."""
    f = font("display", 30)
    tracked(d, (72 * S, 88 * S), "AI UNPACKED", f, FAINT, 4.0)
    tracked(d, (72 * S, 88 * S + int(f.size * 1.15)), "BUILD CLUB", f, MAGENTA, 4.0)
    fp = font("ui_sb", 30)
    t = right_pill
    wpx = int(tw(d, t, fp)) + 48 * S
    x1, y0 = 1008 * S, 92 * S
    d.rounded_rectangle([x1 - wpx, y0, x1, y0 + 62 * S], radius=31 * S,
                        fill=MAGENTA + (36,), outline=MAGENTA, width=2 * S)
    d.text((x1 - wpx + 24 * S, y0 + 11 * S), t, font=fp, fill=TXT)


def chip(d, cx, cy, text, px=54, fill=YELLOW, ink=INK_TOP, rot=-3):
    """Slanted punch chip (Cover grammar) — rendered on its own layer, rotated."""
    f = font("display", px)
    pad_x, pad_y = 34 * S, 16 * S
    wpx = int(tracked_w(d, text, f, 1.5)) + 2 * pad_x
    hpx = int(px * 1.35) * S + 2 * pad_y
    lay = Image.new("RGBA", (wpx + 40 * S, hpx + 40 * S), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    ld.rectangle([20 * S, 20 * S, 20 * S + wpx, 20 * S + hpx], fill=fill)
    tracked(ld, (20 * S + pad_x, 20 * S + pad_y - 2 * S), text, f, ink, 1.5)
    lay = lay.rotate(rot, expand=True, resample=Image.BICUBIC)
    return lay, (int(cx * S - lay.width / 2), int(cy * S - lay.height / 2))


def karaoke(d, words, active_i, y=1452):
    """Simulated caption band line — active word magenta, heavy stroke."""
    f = font("display", 62)
    gap = 22 * S
    total = sum(tw(d, w, f) for w in words) + gap * (len(words) - 1)
    x = (W * S - total) // 2
    for i, wd in enumerate(words):
        col = MAGENTA if i == active_i else TXT
        d.text((x, y * S), wd, font=f, fill=col,
               stroke_width=6 * S, stroke_fill=(8, 8, 12))
        x += tw(d, wd, f) + gap


def rail(d, y, done, active):
    """Persistent 3-node progress rail: PROMPT -> FILE -> LIVE."""
    labels = ["PROMPT", "FILE", "LIVE"]
    seg_w, gap = 288, 24
    x = (W - (seg_w * 3 + gap * 2)) // 2
    for i, lab in enumerate(labels):
        x0, x1 = x * S, (x + seg_w) * S
        if i < done:
            col, fillc, txtc = MAGENTA, MAGENTA, INK_TOP
        elif i == active:
            col, fillc, txtc = YELLOW, YELLOW, INK_TOP
        else:
            col, fillc, txtc = CARD_EDGE, CARD, FAINT
        d.rounded_rectangle([x0, y * S, x1, (y + 64) * S], radius=32 * S,
                            fill=fillc, outline=col, width=2 * S)
        f = font("ui_sb", 28)
        t = f"{i + 1}  {lab}"
        txx = x0 + (x1 - x0 - int(tw(d, t, f))) // 2
        d.text((txx, (y + 14) * S), t, font=f, fill=txtc)
        if i < done:  # drawn tick left of the label (Poppins has no ✓ glyph)
            cx2, cy2 = x0 + 36 * S, (y + 32) * S
            d.line([(cx2 - 9 * S, cy2), (cx2 - 2 * S, cy2 + 8 * S)],
                   fill=INK_TOP, width=4 * S)
            d.line([(cx2 - 2 * S, cy2 + 8 * S), (cx2 + 10 * S, cy2 - 8 * S)],
                   fill=INK_TOP, width=4 * S)
        if i < 2:  # connector
            ccol = MAGENTA if i < done else CARD_EDGE
            d.line([(x1, (y + 32) * S), (x1 + gap * S, (y + 32) * S)],
                   fill=ccol, width=4 * S)
        x += seg_w + gap


def phone(d, box, url="anitas-tiffin.netlify.app"):
    """A drawn phone running the shipped one-pager — dark-luxe premium look.

    The viewer must believe THIS quality comes out in the claimed time (VJ
    2026-08-13), so the mock site is styled like a real modern landing page:
    warm hero glow, display type, glass menu cards, gold accents.
    """
    x0, y0, x1, y1 = [v * S for v in box]
    d.rounded_rectangle([x0, y0, x1, y1], radius=56 * S,
                        fill=(13, 12, 18), outline=(84, 80, 100), width=4 * S)
    m = 20 * S
    sx0, sy0, sx1, sy1 = x0 + m, y0 + m, x1 - m, y1 - m
    d.rounded_rectangle([sx0, sy0, sx1, sy1], radius=40 * S, fill=(21, 17, 24))
    # warm hero glow — vertical fade from ember to ink
    glow_h = 330 * S
    for i in range(glow_h // (2 * S)):
        t = i / (glow_h // (2 * S))
        col = (int(52 - 31 * t), int(28 - 11 * t), int(22 + 2 * t))
        yy = sy0 + 60 * S + i * 2 * S
        d.line([(sx0 + 8 * S, yy), (sx1 - 8 * S, yy)], fill=col, width=2 * S)
    # url pill
    d.rounded_rectangle([sx0 + 36 * S, sy0 + 22 * S, sx1 - 36 * S, sy0 + 76 * S],
                        radius=27 * S, fill=(34, 30, 40))
    fu = font("ui", 25)
    d.text(((sx0 + sx1 - tw(d, url, fu)) // 2, sy0 + 35 * S), url,
           font=fu, fill=(170, 164, 180))
    # hero type
    eb = "HOME-STYLE TIFFIN · DAILY"
    fe = font("ui_sb", 22)
    tracked(d, (sx0 + 44 * S, sy0 + 118 * S), eb, fe, YELLOW, 3.0)
    d.text((sx0 + 44 * S, sy0 + 156 * S), "ANITA'S TIFFIN",
           font=font("display", 54), fill=TXT)
    d.text((sx0 + 44 * S, sy0 + 238 * S), "Ghar ka khana, delivered daily.",
           font=font("ui", 27), fill=(178, 168, 172))
    # rating row
    ry = sy0 + 300 * S
    for i in range(5):
        star(d, (sx0 // S) + 54 + i * 34, (ry // S) + 12, 13, YELLOW)
    d.text((sx0 + 220 * S, ry), "4.9 · 120+ weekly orders",
           font=font("ui", 25), fill=DIM)
    # glass menu cards
    fm, fp2 = font("ui_sb", 29), font("ui_sb", 29)
    cy0 = sy0 + 356 * S
    for dish, price in [("Rajma Chawal", "₹120"), ("Paneer Thali", "₹150")]:
        d.rounded_rectangle([sx0 + 36 * S, cy0, sx1 - 36 * S, cy0 + 84 * S],
                            radius=22 * S, fill=(33, 28, 38),
                            outline=(56, 50, 64), width=2 * S)
        d.text((sx0 + 68 * S, cy0 + 22 * S), dish, font=fp2, fill=TXT)
        d.text((sx1 - 68 * S - tw(d, price, fm), cy0 + 22 * S), price,
               font=fm, fill=YELLOW)
        cy0 += 100 * S
    # CTA
    by0 = cy0 + 18 * S
    d.rounded_rectangle([sx0 + 36 * S, by0, sx1 - 36 * S, by0 + 92 * S],
                        radius=46 * S, fill=WHATS_GREEN)
    bt = "ORDER ON WHATSAPP"
    fb = font("ui_sb", 31)
    d.text(((sx0 + sx1 - tw(d, bt, fb)) // 2, by0 + 25 * S), bt,
           font=fb, fill=(255, 255, 255))


def tick_row(d, x0, x1, y, h, title, sub, col=GREEN):
    d.rounded_rectangle([x0 * S, y * S, x1 * S, (y + h) * S], radius=26 * S,
                        fill=CARD, outline=CARD_EDGE, width=2 * S)
    cx, cy = (x0 + 58) * S, (y + h // 2) * S
    d.ellipse([cx - 26 * S, cy - 26 * S, cx + 26 * S, cy + 26 * S],
              outline=col, width=3 * S)
    d.line([(cx - 12 * S, cy), (cx - 3 * S, cy + 11 * S)], fill=col, width=4 * S)
    d.line([(cx - 3 * S, cy + 11 * S), (cx + 13 * S, cy - 11 * S)], fill=col, width=4 * S)
    d.text(((x0 + 116) * S, (y + 22) * S), title, font=font("ui_sb", 38), fill=TXT)
    d.text(((x0 + 116) * S, (y + 76) * S), sub, font=font("ui", 28), fill=DIM)


def grid(d):
    """Blueprint grid over the ink bg."""
    minor, major = (44, 44, 62), (60, 56, 84)
    for gx in range(0, W + 1, 72):
        d.line([(gx * S, 0), (gx * S, H * S)],
               fill=major if gx % 360 == 0 else minor, width=1 * S)
    for gy in range(0, H + 1, 72):
        d.line([(0, gy * S), (W * S, gy * S)],
               fill=major if gy % 360 == 0 else minor, width=1 * S)


def season_dots(d, cx, y, filled=1, n=6):
    r, gap = 14, 54
    x = cx - ((n - 1) * gap) // 2
    for i in range(n):
        box = [(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S]
        if i < filled:
            d.ellipse(box, fill=MAGENTA)
        else:
            d.ellipse(box, outline=FAINT, width=2 * S)
        x += gap


# ---------------------------------------------------------------- frames: A
def a_hook(d, im):
    header(d)
    f = font("display", 128)
    for i, line in enumerate(["STOP PAYING", "FOR WEBSITES"]):
        wpx = tracked_w(d, line, f, 2.0)
        tracked(d, ((W * S - wpx) // 2, (222 + i * 152) * S), line, f, TXT, 2.0)
    lay, pos = chip(d, W // 2, 600, "SHIP YOURS FREE", px=62)
    im.paste(lay, pos, lay)
    # Sol wide-host band (v16.4 grammar: host owns the hook), result phone below
    host_wide(im, (72, 690, 1008, 1120))
    phone(d, (300, 1160, 780, 1880))
    # floating result pill overlapping the phone top edge
    t = "LIVE IN 60 SECONDS · 3 STEPS"
    fp = font("ui_sb", 32)
    wpx = int(tw(d, t, fp)) + 60 * S
    x0, y0 = (W * S - wpx) // 2, 1122 * S
    d.rounded_rectangle([x0, y0, x0 + wpx, y0 + 74 * S], radius=37 * S, fill=MAGENTA)
    d.text((x0 + 30 * S, y0 + 16 * S), t, font=fp, fill=TXT)


def a_interview(d, im):
    """Step 1 as VJ framed it: the prompt interviews YOU — answer like a text."""
    header(d)
    rail(d, 190, done=0, active=0)
    x0, y0, x1, y1 = 72, 330, 1008, 1380
    d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], radius=32 * S,
                        fill=CARD, outline=CARD_EDGE, width=2 * S)
    d.text(((x0 + 44) * S, (y0 + 34) * S), "your ai builder",
           font=font("ui", 30), fill=FAINT)

    def bubble(y, text, user=False):
        f = font("ui_sb" if user else "ui", 30)
        wpx = int(tw(d, text, f)) + 56 * S
        if user:
            bx1 = (x1 - 44) * S
            bx0 = bx1 - wpx
            fill, col = MAGENTA, TXT
        else:
            bx0 = (x0 + 44) * S
            bx1 = bx0 + wpx
            fill, col = (34, 32, 44), TXT
        d.rounded_rectangle([bx0, y * S, bx1, (y + 78) * S], radius=32 * S, fill=fill)
        d.text((bx0 + 28 * S, (y + 18) * S), text, font=f, fill=col)

    bubble(410, "Before I build — 5 quick questions.")
    bubble(506, "1/5  What's your business called?")
    bubble(602, "Anita's Tiffin", user=True)
    bubble(698, "2/5  What do you sell, at what price?")
    bubble(794, "Rajma ₹120 · Thali ₹150 · Dal ₹90", user=True)
    bubble(890, "3/5  Your WhatsApp number?")
    bubble(986, "98765 43210", user=True)
    # builder is off writing the file
    d.text(((x0 + 44) * S, 1102 * S), "building your index.html …",
           font=font("mono", 28), fill=YELLOW)
    d.rounded_rectangle([(x0 + 44) * S, 1160 * S, (x0 + 460) * S, 1178 * S],
                        radius=9 * S, fill=(34, 32, 44))
    d.rounded_rectangle([(x0 + 44) * S, 1160 * S, (x0 + 220) * S, 1178 * S],
                        radius=9 * S, fill=MAGENTA)
    # Sol pip: bottom-left dead space (user bubbles hug the right edge)
    host_pip(im, 185, 1285, 190)
    # step chip, bottom-right
    fch = font("ui_sb", 30)
    t = "STEP 1/3 · JUST ANSWER"
    wpx = int(tw(d, t, fch)) + 52 * S
    d.rounded_rectangle([x1 * S - wpx - 24 * S, (y1 - 90) * S, (x1 - 24) * S,
                         (y1 - 24) * S],
                        radius=33 * S, fill=INK_TOP + (220,), outline=YELLOW,
                        width=2 * S)
    d.text((x1 * S - wpx + 2 * S, (y1 - 76) * S), t, font=fch, fill=YELLOW)
    karaoke(d, ["ANSWER", "LIKE", "A", "TEXT"], 3)


def a_step(d, im):
    header(d)
    rail(d, 190, done=1, active=1)
    # proof pane: neutral in-house "ai builder" surface writing the one file
    x0, y0, x1, y1 = 72, 330, 1008, 1380
    d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], radius=32 * S,
                        fill=CARD, outline=CARD_EDGE, width=2 * S)
    d.text(((x0 + 44) * S, (y0 + 34) * S), "your ai builder",
           font=font("ui", 30), fill=FAINT)
    # code card
    cx0, cy0, cx1, cy1 = x0 + 44, y0 + 100, x1 - 44, y0 + 700
    d.rounded_rectangle([cx0 * S, cy0 * S, cx1 * S, cy1 * S], radius=24 * S,
                        fill=(15, 15, 22), outline=CARD_EDGE, width=2 * S)
    fm = font("mono", 27)
    lines = [
        ("<!doctype html>", DIM),
        ("<title>Anita's Tiffin</title>", TXT),
        ("<style>  /* warm, mobile-first */", DIM),
        ("  .hero { … }  .menu { … }", DIM),
        ("</style>", DIM),
        ("<body>", TXT),
        ("  ANITA'S TIFFIN — ghar ka khana", YELLOW),
        ("  [ today's menu · prices ]", TXT),
        ("  [ ORDER ON WHATSAPP ]", GREEN),
        ("</body>   ← your WHOLE site. one file.", MAGENTA),
    ]
    for i, (t, col) in enumerate(lines):
        d.text(((cx0 + 34) * S, (cy0 + 44 + i * 54) * S), t, font=fm, fill=col)
    # download row
    fy = cy1 + 40
    fpill = font("ui_sb", 32)
    t = "index.html  ·  save it"
    wpx = int(tw(d, t, fpill)) + 60 * S
    d.rounded_rectangle([(cx0) * S, fy * S, cx0 * S + wpx, (fy + 74) * S],
                        radius=37 * S, fill=YELLOW)
    d.text((cx0 * S + 30 * S, (fy + 16) * S), t, font=fpill, fill=INK_TOP)
    d.text(((cx0) * S, (fy + 110) * S),
           "one file = nothing to configure",
           font=font("ui", 30), fill=DIM)
    # Sol pip in the dead space right of the download pill
    host_pip(im, 855, 1155, 190)
    # step chip, bottom-right dead space (pos rule)
    fch = font("ui_sb", 30)
    t = "STEP 2/3 · SAVE THE FILE"
    wpx = int(tw(d, t, fch)) + 52 * S
    d.rounded_rectangle([x1 * S - wpx - 24 * S, (y1 - 90) * S, (x1 - 24) * S, (y1 - 24) * S],
                        radius=33 * S, fill=INK_TOP + (220,), outline=YELLOW, width=2 * S)
    d.text((x1 * S - wpx + 2 * S, (y1 - 76) * S), t, font=fch, fill=YELLOW)
    karaoke(d, ["SAVE", "IT", "AS", "INDEX.HTML"], 3)


def a_pause(d, im):
    header(d)
    rail(d, 190, done=0, active=0)
    # pause affordance
    cy = 330
    d.ellipse([(W // 2 - 44) * S, cy * S, (W // 2 + 44) * S, (cy + 88) * S],
              fill=YELLOW)
    for dx in (-14, 8):
        d.rounded_rectangle([(W // 2 + dx) * S, (cy + 24) * S,
                             (W // 2 + dx + 8) * S, (cy + 64) * S],
                            radius=4 * S, fill=INK_TOP)
    f = font("display", 58)
    t = "PAUSE — COPY THIS PROMPT"
    wpx = tracked_w(d, t, f, 2.0)
    tracked(d, ((W * S - wpx) // 2, (cy + 116) * S), t, f, TXT, 2.0)
    # the prompt card — the INTERVIEW prompt (VJ 2026-08-13): it asks YOU
    x0, y0, x1, y1 = 96, 580, 984, 1268
    d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], radius=32 * S,
                        fill=CARD, outline=YELLOW, width=3 * S)
    fm = font("mono", 30)
    plines = [
        ('Build me a PREMIUM one-page', TXT),
        ('website for my business.', TXT),
        ('First, ask me 5 quick questions —', YELLOW),
        ('name, what I sell, prices, my', TXT),
        ('WhatsApp number, the vibe.', TXT),
        ('Then put ALL the code in ONE', TXT),
        ('file: index.html.', YELLOW),
        ('Make it look expensive — modern', TXT),
        ('fonts, smooth gradients, mobile-first.', TXT),
    ]
    for i, (t2, col) in enumerate(plines):
        d.text(((x0 + 52) * S, (y0 + 50 + i * 66) * S), t2, font=fm, fill=col)
    # it-interviews-you annotation
    fa = font("ui_sb", 32)
    t = "no editing — it interviews YOU"
    wpx = int(tw(d, t, fa))
    d.text(((W * S - wpx) // 2, 1300 * S), t, font=fa, fill=MAGENTA)
    t2 = "full prompt waiting in the pinned comment"
    fu = font("ui", 30)
    d.text(((W * S - int(tw(d, t2, fu))) // 2, 1354 * S), t2, font=fu, fill=DIM)


def a_recipe(d, im):
    header(d)
    f = font("display", 92)
    t = "THE RECIPE"
    wpx = tracked_w(d, t, f, 2.0)
    tracked(d, ((W * S - wpx) // 2, 210 * S), t, f, TXT, 2.0)
    rows = [("TELL CLAUDE THE IDEA", "name · vibe · one file, everything inside"),
            ("SAVE  INDEX.HTML", "that one file is your whole website"),
            ("DRAG ONTO NETLIFY DROP", "no card, no setup — live URL")]
    y = 360
    for title, sub in rows:
        tick_row(d, 72, 1008, y, 132, title, sub)
        y += 156
    # homework panel
    y += 24
    d.rounded_rectangle([72 * S, y * S, 1008 * S, (y + 250) * S], radius=32 * S,
                        fill=(53, 16, 31), outline=MAGENTA, width=3 * S)
    tracked(d, (116 * S, (y + 30) * S), "HOMEWORK", font("display", 34), MAGENTA, 4.0)
    d.text((116 * S, (y + 86) * S), "Ship yours this week.",
           font=font("ui_sb", 44), fill=TXT)
    fc = font("ui_sb", 34)
    t = "COMMENT  SHIPPED"
    wpx = int(tw(d, t, fc)) + 56 * S
    d.rounded_rectangle([116 * S, (y + 156) * S, 116 * S + wpx, (y + 226) * S],
                        radius=35 * S, fill=YELLOW)
    d.text((144 * S, (y + 171) * S), t, font=fc, fill=INK_TOP)
    # next chapter tease
    y += 290
    ft = font("ui_sb", 34)
    t = "NEXT FRIDAY · CH 2 — YOUR SITE GETS SMART"
    d.text(((W * S - int(tw(d, t, ft))) // 2, y * S), t, font=ft, fill=YELLOW)
    season_dots(d, W // 2, y + 90, filled=1)


# ---------------------------------------------------------------- frames: B
def b_chapter(d, im):
    grid(d)
    f = font("display", 34)
    t = "BUILD CLUB"
    wpx = tracked_w(d, t, f, 10.0)
    tracked(d, ((W * S - wpx) // 2, 430 * S), t, f, DIM, 10.0)
    f1 = font("display", 120)
    t = "CHAPTER"
    wpx = tracked_w(d, t, f1, 4.0)
    tracked(d, ((W * S - wpx) // 2, 520 * S), t, f1, TXT, 4.0)
    f2 = font("display", 260)
    t = "ONE"
    wpx = tracked_w(d, t, f2, 6.0)
    tracked(d, ((W * S - wpx) // 2, 680 * S), t, f2, MAGENTA, 6.0)
    lay, pos = chip(d, W // 2, 1110, "YOUR IDEA GOES LIVE", px=52)
    im.paste(lay, pos, lay)
    fu = font("ui", 34)
    t = "one move, every friday"
    d.text(((W * S - int(tw(d, t, fu))) // 2, 1220 * S), t, font=fu, fill=DIM)
    season_dots(d, W // 2, 1340, filled=1)


def b_step(d, im):
    grid(d)
    header(d)
    # tilted "taped" card holding the artifact
    cw, ch2 = 780, 860
    lay = Image.new("RGBA", ((cw + 80) * S, (ch2 + 80) * S), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    ld.rectangle([40 * S, 40 * S, (cw + 40) * S, (ch2 + 40) * S],
                 fill=(245, 242, 236), outline=(210, 204, 194), width=2 * S)
    ld.rectangle([70 * S, 70 * S, (cw + 10) * S, (ch2 - 60) * S], fill=(15, 15, 22))
    fm = font("mono", 30)
    for i, (t, col) in enumerate([("index.html", YELLOW),
                                  ("<!doctype html>", DIM),
                                  ("<title>Anita's Tiffin</title>", TXT),
                                  ("<style> .hero{…} .menu{…} </style>", DIM),
                                  ("<body>", TXT),
                                  ("  ANITA'S TIFFIN", YELLOW),
                                  ("  [ today's menu · prices ]", TXT),
                                  ("  [ ORDER ON WHATSAPP ]", GREEN),
                                  ("</body>", TXT),
                                  ("", TXT),
                                  ("everything in ONE file", MAGENTA)]):
        ld.text((100 * S, (110 + i * 58) * S), t, font=fm, fill=col)
    fc = font("ui_sb", 34)
    ld.text((70 * S, (ch2 - 30) * S), "fig. 2 — the file", font=fc, fill=(90, 84, 76))
    lay = lay.rotate(-2, expand=True, resample=Image.BICUBIC)
    px0, py0 = int((W * S - lay.width) / 2), 300 * S
    im.paste(lay, (px0, py0), lay)
    # tape strips ON the card's top corners (positions derived from the paste box)
    for tx in (px0 + int(lay.width * 0.10), px0 + int(lay.width * 0.74)):
        d.rectangle([tx, py0 + 26 * S, tx + 150 * S, py0 + 70 * S],
                    fill=(255, 255, 255, 70))
    # circled step number + annotation
    d.ellipse([120 * S, 1290 * S, 208 * S, 1378 * S], outline=MAGENTA, width=4 * S)
    d.text((146 * S, 1302 * S), "2", font=font("display", 54), fill=MAGENTA)
    fa = font("ui_sb", 38)
    d.text((240 * S, 1310 * S), "save it as  index.html", font=fa, fill=TXT)
    d.line([(164 * S, 1290 * S), (164 * S, 1230 * S), (300 * S, 1230 * S)],
           fill=MAGENTA + (140,), width=3 * S)


MODES = {"a_hook": a_hook, "a_interview": a_interview, "a_step": a_step,
         "a_pause": a_pause, "a_recipe": a_recipe,
         "b_chapter": b_chapter, "b_step": b_step}


def build(mode, out):
    canvas = bg((W * S, H * S)).convert("RGBA")
    d = ImageDraw.Draw(canvas, "RGBA")
    MODES[mode](d, canvas)
    canvas.convert("RGB").resize((W, H), Image.LANCZOS).save(out, "PNG")
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
