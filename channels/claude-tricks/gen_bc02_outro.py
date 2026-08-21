#!/usr/bin/env python3
"""BC02 outro card (1080x1920) — homework ask + Ch.3 tease.

Same grammar as gen_bc01_outro.py: Sol avatar + SHIP IT chip up top, phone on
the left, chapter tease stack right, subscribe + tagline bottom. Ch.2 payoff
phone = a SEARCH RESULT card — tomorrow (Ch.3 LAUNCH) your name goes public
where people can find you. Season dots: 1+2 filled, 3 hollow (the NEXT one).

  python3 channels/claude-tricks/gen_bc02_outro.py
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
    bg, font, tw, tracked, tracked_w)
from gen_bc01_format_mock import star  # noqa: E402
from gen_bc01_outro import grid, bubble, AVATAR  # noqa: E402

H = 1920
OUT_DIR = HERE / "assets" / "epbc02"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    canvas = bg((W * S, H * S)).convert("RGB")
    d = ImageDraw.Draw(canvas, "RGBA")
    grid(d)

    # top: Sol + homework chip
    px = 210 * S
    tile = ImageOps.fit(Image.open(AVATAR).convert("RGB"), (px, px),
                        Image.LANCZOS)
    mask = Image.new("L", (px, px), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, px, px], fill=255)
    canvas.paste(tile, (W * S // 2 - px // 2, 96 * S), mask)
    d.ellipse([W * S // 2 - px // 2, 96 * S, W * S // 2 + px // 2, 96 * S + px],
              outline=MAGENTA, width=5 * S)

    t = "SHIP IT · DROP YOUR LINK"
    fc = font("ui_sb", 38)
    wpx = int(tw(d, t, fc)) + 110 * S
    x0 = (W * S - wpx) // 2
    d.rounded_rectangle([x0, 348 * S, x0 + wpx, 430 * S], radius=41 * S,
                        fill=YELLOW)
    d.text((x0 + 32 * S, 366 * S), t, font=fc, fill=INK_TOP)
    ax = x0 + wpx - 62 * S
    d.line([(ax, 368 * S), (ax, 404 * S)], fill=INK_TOP, width=7 * S)
    d.polygon([(ax - 14 * S, 398 * S), (ax + 14 * S, 398 * S), (ax, 416 * S)],
              fill=INK_TOP)

    # middle-left phone: SEARCH RESULT — you can be FOUND (Ch.3 payoff)
    bx0, by0, bx1, by1 = 64, 560, 560, 1450
    d.rounded_rectangle([bx0 * S, by0 * S, bx1 * S, by1 * S], radius=48 * S,
                        fill=(13, 12, 18), outline=(84, 80, 100), width=4 * S)
    m = 18 * S
    sx0, sy0, sx1, sy1 = bx0 * S + m, by0 * S + m, bx1 * S - m, by1 * S - m
    d.rounded_rectangle([sx0, sy0, sx1, sy1], radius=34 * S, fill=(21, 17, 24))
    fu = font("ui", 22)
    q = "tiffin near me"
    d.rounded_rectangle([sx0 + 28 * S, sy0 + 18 * S, sx1 - 28 * S, sy0 + 66 * S],
                        radius=24 * S, fill=(34, 30, 40))
    # drawn magnifier (PIL has no emoji fallback)
    mcx, mcy, mr = sx0 + 56 * S, sy0 + 42 * S, 10 * S
    d.ellipse([mcx - mr, mcy - mr, mcx + mr, mcy + mr],
              outline=(200, 194, 205), width=3 * S)
    d.line([(mcx + mr - 2 * S, mcy + mr - 2 * S), (mcx + mr + 8 * S, mcy + mr + 8 * S)],
           fill=(200, 194, 205), width=3 * S)
    d.text((sx0 + 84 * S, sy0 + 29 * S), q, font=fu, fill=(200, 194, 205))
    # result card
    ry = sy0 + 100 * S
    d.rounded_rectangle([sx0 + 26 * S, ry, sx1 - 26 * S, ry + 300 * S],
                        radius=26 * S, fill=(30, 26, 34),
                        outline=MAGENTA, width=3 * S)
    d.text((sx0 + 48 * S, ry + 26 * S), "ANITA'S TIFFIN",
           font=font("display", 38), fill=TXT)
    d.text((sx0 + 48 * S, ry + 84 * S), "Ghar ka khana · Indiranagar",
           font=font("ui", 22), fill=(178, 168, 172))
    for i in range(5):
        star(d, (sx0 // S) + 48 + i * 34, (ry // S) + 136, 13, YELLOW)
    d.text((sx0 + 48 * S + 176 * S, ry + 124 * S), "4.9",
           font=font("ui_sb", 24), fill=YELLOW)
    d.rounded_rectangle([sx0 + 48 * S, ry + 190 * S, sx0 + 300 * S,
                         ry + 252 * S], radius=31 * S, fill=GREEN)
    d.text((sx0 + 72 * S, ry + 204 * S), "ORDER NOW", font=font("ui_sb", 26),
           fill=(255, 255, 255))
    d.text((sx0 + 36 * S, ry + 330 * S), "that's YOUR name,",
           font=font("ui", 26), fill=DIM)
    d.text((sx0 + 36 * S, ry + 372 * S), "where people search.",
           font=font("ui", 26), fill=DIM)
    # AI spark
    star(d, (sx0 // S) + 40, (by1) - 120, 16, YELLOW)
    d.text((sx0 + 66 * S, (by1 - 130) * S), "FOUND", font=font("ui_sb", 26),
           fill=YELLOW)

    # middle-right: CHAPTER THREE stack
    rx = 600
    f = font("display", 40)
    tracked(d, (rx * S, 600 * S), "TOMORROW", f, DIM, 8.0)
    d.text((rx * S, 664 * S), "CHAPTER", font=font("display", 96), fill=TXT)
    d.text((rx * S, 790 * S), "THREE", font=font("display", 170), fill=MAGENTA)
    t, t2 = "YOUR NAME", "GOES PUBLIC"
    fch = font("display", 46)
    w1 = int(tracked_w(d, t, fch, 1.5)) + 48 * S
    d.rectangle([rx * S, 1120 * S, rx * S + w1, 1196 * S], fill=YELLOW)
    tracked(d, (rx * S + 24 * S, 1132 * S), t, fch, INK_TOP, 1.5)
    w2 = int(tracked_w(d, t2, fch, 1.5)) + 48 * S
    d.rectangle([rx * S, 1210 * S, rx * S + w2, 1286 * S], fill=YELLOW)
    tracked(d, (rx * S + 24 * S, 1222 * S), t2, fch, INK_TOP, 1.5)
    dx, r, gap = rx + 22, 15, 56
    for i in range(6):
        box = [(dx - r) * S, (1360 - r) * S, (dx + r) * S, (1360 + r) * S]
        if i in (0, 1):
            d.ellipse(box, fill=MAGENTA)
        elif i == 2:
            d.ellipse(box, outline=MAGENTA, width=5 * S)
        else:
            d.ellipse(box, outline=FAINT, width=2 * S)
        dx += gap

    # bottom: subscribe + tagline
    t = "SUBSCRIBE — DON'T MISS IT"
    fs = font("ui_sb", 36)
    wpx = int(tw(d, t, fs)) + 64 * S
    x0 = (W * S - wpx) // 2
    d.rounded_rectangle([x0, 1560 * S, x0 + wpx, 1642 * S], radius=41 * S,
                        fill=MAGENTA)
    d.text((x0 + 32 * S, 1578 * S), t, font=fs, fill=TXT)
    t2 = "one practical step, all week — build club season 1"
    fu2 = font("ui", 30)
    d.text(((W * S - int(tw(d, t2, fu2))) // 2, 1682 * S), t2, font=fu2,
           fill=DIM)

    still = OUT_DIR / "outro_card.jpg"
    canvas.convert("RGB").resize((W, H), Image.LANCZOS).save(
        still, "JPEG", quality=92)
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
