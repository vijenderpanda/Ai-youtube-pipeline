#!/usr/bin/env python3
"""BC01 outro card — Chapter 2 curiosity tease (VJ 2026-08-13).

Replaces the generic question card for Build Club Ch.1: the SAME premium
phone from the episode, now answering a customer in chat — the Chapter 2
payoff made visible — beside a big "CHAPTER TWO / YOUR SITE GETS SMART"
stack, season dots advancing to 2, and the homework ask on top. Sol's
spoken CTA (outro_cta verbatim) plays over it; build_ep_v2 retimes the
Ken-Burns mp4 to the CTA length.

  python3 channels/claude-tricks/gen_bc01_outro.py
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "scripts"))

from make_doc_mock import (  # noqa: E402
    S, W, MAGENTA, YELLOW, GREEN, TXT, DIM, FAINT, CARD, CARD_EDGE, INK_TOP,
    bg, font, tw, tracked, tracked_w,
)
from gen_bc01_format_mock import star  # noqa: E402

H = 1920
OUT_DIR = HERE / "assets" / "epbc01"
AVATAR = (HERE / "assets/character/host_library/outfit_11_sol_magenta"
          / "cropeed_center_final.jpeg")
CYAN = (34, 211, 238)


def grid(d):
    minor, major = (44, 44, 62), (60, 56, 84)
    for gx in range(0, W + 1, 72):
        d.line([(gx * S, 0), (gx * S, H * S)],
               fill=major if gx % 360 == 0 else minor, width=1 * S)
    for gy in range(0, H + 1, 72):
        d.line([(0, gy * S), (W * S, gy * S)],
               fill=major if gy % 360 == 0 else minor, width=1 * S)


def bubble(d, x0, y0, text, fill, col, px=26, tail="l"):
    f = font("ui_sb", px)
    wpx = int(tw(d, text, f)) + 40 * S
    h = int(px * 2.2) * S
    d.rounded_rectangle([x0, y0, x0 + wpx, y0 + h], radius=h // 2, fill=fill)
    tx = x0 + (16 * S if tail == "l" else wpx - 30 * S)
    d.polygon([(tx, y0 + h - 4 * S), (tx + 22 * S, y0 + h - 4 * S),
               (tx + 4 * S, y0 + h + 16 * S)], fill=fill)
    d.text((x0 + 20 * S, y0 + int(px * 0.5) * S), text, font=f, fill=col)
    return x0 + wpx, y0 + h


def main():
    canvas = bg((W * S, H * S)).convert("RGBA")
    d = ImageDraw.Draw(canvas, "RGBA")
    grid(d)

    # ---- top: Sol + the homework ask -----------------------------------
    px = 210 * S
    tile = ImageOps.fit(Image.open(AVATAR).convert("RGB"), (px, px),
                        Image.LANCZOS)
    mask = Image.new("L", (px, px), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, px, px], fill=255)
    canvas.paste(tile, (W * S // 2 - px // 2, 96 * S), mask)
    d.ellipse([W * S // 2 - px // 2, 96 * S, W * S // 2 + px // 2,
               96 * S + px], outline=MAGENTA, width=5 * S)

    t = "SHIP IT · DROP YOUR LINK"
    fc = font("ui_sb", 38)
    wpx = int(tw(d, t, fc)) + 110 * S
    x0 = (W * S - wpx) // 2
    d.rounded_rectangle([x0, 348 * S, x0 + wpx, 430 * S], radius=41 * S,
                        fill=YELLOW)
    d.text((x0 + 32 * S, 366 * S), t, font=fc, fill=INK_TOP)
    # drawn down-arrow (PIL has no emoji fallback — 👇 renders as tofu)
    ax = x0 + wpx - 62 * S
    d.line([(ax, 368 * S), (ax, 404 * S)], fill=INK_TOP, width=7 * S)
    d.polygon([(ax - 14 * S, 398 * S), (ax + 14 * S, 398 * S),
               (ax, 416 * S)], fill=INK_TOP)

    # ---- middle-left: the phone, now TALKING (ch2 payoff) ---------------
    bx0, by0, bx1, by1 = 64, 560, 560, 1450
    d.rounded_rectangle([bx0 * S, by0 * S, bx1 * S, by1 * S], radius=48 * S,
                        fill=(13, 12, 18), outline=(84, 80, 100), width=4 * S)
    m = 18 * S
    sx0, sy0, sx1, sy1 = bx0 * S + m, by0 * S + m, bx1 * S - m, by1 * S - m
    d.rounded_rectangle([sx0, sy0, sx1, sy1], radius=34 * S, fill=(21, 17, 24))
    fu = font("ui", 22)
    url = "anitas-tiffin.netlify.app"
    d.rounded_rectangle([sx0 + 28 * S, sy0 + 18 * S, sx1 - 28 * S, sy0 + 64 * S],
                        radius=23 * S, fill=(34, 30, 40))
    d.text(((sx0 + sx1 - tw(d, url, fu)) // 2, sy0 + 28 * S), url, font=fu,
           fill=(170, 164, 180))
    d.text((sx0 + 36 * S, sy0 + 96 * S), "ANITA'S TIFFIN",
           font=font("display", 40), fill=TXT)
    d.text((sx0 + 36 * S, sy0 + 156 * S), "Ghar ka khana, delivered daily.",
           font=font("ui", 22), fill=(178, 168, 172))
    # chat: a customer asks, the SITE answers
    _, ey = bubble(d, sx0 + 36 * S, sy0 + 240 * S, "Aaj ka menu kya hai?",
                   (48, 46, 58), TXT, tail="l")
    d.text((sx0 + 36 * S, ey + 26 * S), "the site replies, on its own:",
           font=font("ui", 20), fill=FAINT)
    bubble(d, sx0 + 60 * S, ey + 66 * S, "Rajma ₹120 · Thali ₹150",
           MAGENTA, TXT, tail="r")
    bubble(d, sx0 + 60 * S, ey + 176 * S, "Order by 10 AM — bhej du?",
           MAGENTA, TXT, tail="r")
    # AI spark badge
    star(d, (sx0 // S) + 52, (ey // S) + 250, 16, YELLOW)
    d.text((sx0 + 78 * S, ey + 226 * S), "AI", font=font("ui_sb", 26),
           fill=YELLOW)
    # site CTA fills the phone's lower half (mirrors the real page)
    d.rounded_rectangle([sx0 + 36 * S, sy1 - 150 * S, sx1 - 36 * S,
                         sy1 - 62 * S], radius=44 * S, fill=GREEN)
    bt = "ORDER ON WHATSAPP"
    fb = font("ui_sb", 28)
    d.text(((sx0 + sx1 - tw(d, bt, fb)) // 2, sy1 - 126 * S), bt, font=fb,
           fill=(255, 255, 255))

    # ---- middle-right: CHAPTER TWO stack --------------------------------
    rx = 600
    f = font("display", 40)
    tracked(d, (rx * S, 600 * S), "NEXT FRIDAY", f, DIM, 8.0)
    d.text((rx * S, 664 * S), "CHAPTER", font=font("display", 96), fill=TXT)
    d.text((rx * S, 790 * S), "TWO", font=font("display", 210), fill=MAGENTA)
    # chip
    t = "YOUR SITE"
    t2 = "GETS SMART"
    fch = font("display", 46)
    w1 = int(tracked_w(d, t, fch, 1.5)) + 48 * S
    d.rectangle([rx * S, 1120 * S, rx * S + w1, 1196 * S], fill=YELLOW)
    tracked(d, (rx * S + 24 * S, 1132 * S), t, fch, INK_TOP, 1.5)
    w2 = int(tracked_w(d, t2, fch, 1.5)) + 48 * S
    d.rectangle([rx * S, 1210 * S, rx * S + w2, 1286 * S], fill=YELLOW)
    tracked(d, (rx * S + 24 * S, 1222 * S), t2, fch, INK_TOP, 1.5)
    # season dots — dot 2 highlighted hollow-magenta (the NEXT one)
    dx, r, gap = rx + 22, 15, 56
    for i in range(6):
        box = [(dx - r) * S, (1360 - r) * S, (dx + r) * S, (1360 + r) * S]
        if i == 0:
            d.ellipse(box, fill=MAGENTA)
        elif i == 1:
            d.ellipse(box, outline=MAGENTA, width=5 * S)
        else:
            d.ellipse(box, outline=FAINT, width=2 * S)
        dx += gap

    # ---- bottom: subscribe + tagline ------------------------------------
    t = "SUBSCRIBE — DON'T MISS IT"
    fs = font("ui_sb", 36)
    wpx = int(tw(d, t, fs)) + 64 * S
    x0 = (W * S - wpx) // 2
    d.rounded_rectangle([x0, 1560 * S, x0 + wpx, 1642 * S], radius=41 * S,
                        fill=MAGENTA)
    d.text((x0 + 32 * S, 1578 * S), t, font=fs, fill=TXT)
    t2 = "one practical step, every friday — build club"
    fu2 = font("ui", 30)
    d.text(((W * S - int(tw(d, t2, fu2))) // 2, 1682 * S), t2, font=fu2,
           fill=DIM)

    still = OUT_DIR / "outro_card.jpg"
    canvas.convert("RGB").resize((W, H), Image.LANCZOS).save(
        still, "JPEG", quality=92)

    # Ken-Burns mp4 (6% push, 4.2s base — build_ep_v2 retimes to the CTA)
    dur, fps = 4.2, 30
    frames = int(dur * fps)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(still),
        "-vf",
        f"scale=1296:2304,zoompan=z='1+0.06*on/{frames}':d={frames}"
        f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}",
        "-t", str(dur), "-c:v", "libx264", "-crf", "18", "-pix_fmt",
        "yuv420p", "-an", str(OUT_DIR / "outro_card.mp4")], check=True)
    print("OK", still, "+", OUT_DIR / "outro_card.mp4")


if __name__ == "__main__":
    main()
