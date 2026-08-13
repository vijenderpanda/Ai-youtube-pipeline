#!/usr/bin/env python3
"""BC01 pinned-comment b-roll (1080x1920 mobile-style, in-house surface).

Teaches WHERE the prompt lives: a neutral dark comments surface (house mock
grammar — no platform logo, no lookalike chrome) with the PINNED comment from
the channel holding the Build Club prompt, a thumb-tap ripple on COPY, and the
prompt text visibly selected. Ken-Burns mp4 for the `rec:` beat.

  python3 channels/claude-tricks/gen_bc01_pinned.py
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "scripts"))

from make_doc_mock import (  # noqa: E402
    S, W, MAGENTA, YELLOW, TXT, DIM, FAINT, CARD, CARD_EDGE, INK_TOP,
    bg, font, tw,
)

H = 1920
OUT_DIR = HERE / "assets" / "epbc01"
AVATAR = (HERE / "assets/character/host_library/outfit_11_sol_magenta"
          / "cropeed_center_final.jpeg")


def pin_glyph(d, cx, cy, r, col):
    """A drawn map-pin/push-pin glyph — no platform iconography."""
    d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S],
              fill=col)
    d.polygon([((cx - r * 0.55) * S, (cy + r * 0.6) * S),
               ((cx + r * 0.55) * S, (cy + r * 0.6) * S),
               (cx * S, (cy + r * 2.1) * S)], fill=col)


def main():
    canvas = bg((W * S, H * S)).convert("RGBA")
    d = ImageDraw.Draw(canvas, "RGBA")

    # comments sheet
    d.rounded_rectangle([24 * S, 140 * S, 1056 * S, 1880 * S], radius=40 * S,
                        fill=(18, 18, 26), outline=CARD_EDGE, width=2 * S)
    d.text((72 * S, 190 * S), "Comments", font=font("ui_sb", 44), fill=TXT)
    d.text((348 * S, 202 * S), "1.2K", font=font("ui", 32), fill=FAINT)
    d.line([(24 * S, 280 * S), (1056 * S, 280 * S)], fill=CARD_EDGE,
           width=2 * S)

    # THE pinned comment
    y = 330
    d.rounded_rectangle([48 * S, y * S, 1032 * S, (y + 900) * S],
                        radius=32 * S, fill=(28, 24, 36),
                        outline=MAGENTA, width=3 * S)
    pin_glyph(d, 96, y + 60, 16, MAGENTA)
    d.text((136 * S, (y + 40) * S), "Pinned by creator",
           font=font("ui_sb", 28), fill=MAGENTA)
    # avatar + handle
    px = 84 * S
    tile = ImageOps.fit(Image.open(AVATAR).convert("RGB"), (px, px),
                        Image.LANCZOS)
    mask = Image.new("L", (px, px), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, px, px], fill=255)
    canvas.paste(tile, (76 * S, (y + 100) * S), mask)
    d = ImageDraw.Draw(canvas, "RGBA")
    d.text((180 * S, (y + 116) * S), "AI Unpacked VJ",
           font=font("ui_sb", 34), fill=TXT)
    d.text((470 * S, (y + 122) * S), "· creator", font=font("ui", 28),
           fill=FAINT)

    # prompt text, visibly SELECTED (highlight wash behind the lines)
    lines = [
        "THE BUILD CLUB PROMPT — CHAPTER 1",
        "(copy everything below into Claude,",
        "then just answer its questions)",
        "",
        "You are my personal web designer.",
        "Build me a premium one-page website",
        "for my business.",
        "",
        "SECTION 1 — INTERVIEW ME FIRST",
        "Before writing any code, ask me these",
        "6 questions, one at a time...",
    ]
    ty = y + 210
    fm = font("mono", 28)
    for ln in lines:
        if ln:
            wpx = tw(d, ln, fm)
            d.rectangle([72 * S, (ty - 4) * S, 72 * S + int(wpx) + 12 * S,
                         (ty + 44) * S], fill=(224, 33, 138, 56))
            d.text((76 * S, ty * S), ln, font=fm,
                   fill=YELLOW if ln.startswith(("THE BUILD", "SECTION"))
                   else TXT)
        ty += 56

    # COPY affordance + thumb-tap ripple
    cy2 = y + 810
    d.rounded_rectangle([700 * S, cy2 * S, 1000 * S, (cy2 + 70) * S],
                        radius=35 * S, fill=YELLOW)
    d.text((760 * S, (cy2 + 14) * S), "COPY", font=font("ui_sb", 34),
           fill=INK_TOP)
    for rr, aa in ((46, 150), (66, 90), (86, 45)):
        d.ellipse([(850 - rr) * S, (cy2 + 35 - rr) * S,
                   (850 + rr) * S, (cy2 + 35 + rr) * S],
                  outline=(255, 255, 255, aa), width=3 * S)

    # a dimmed regular comment below, for realism
    y2 = y + 950
    d.ellipse([76 * S, y2 * S, 76 * S + 74 * S, (y2 + 74) * S],
              fill=(52, 50, 62))
    d.text((180 * S, (y2 + 6) * S), "priya_builds", font=font("ui_sb", 30),
           fill=DIM)
    d.text((180 * S, (y2 + 52) * S), "shipped mine in 20 minutes!",
           font=font("ui", 30), fill=FAINT)

    # step hint
    d.text((72 * S, 1790 * S), "tap COPY — then open Claude",
           font=font("ui_sb", 34), fill=DIM)

    still = OUT_DIR / "pinned_broll.jpg"
    canvas.convert("RGB").resize((W, H), Image.LANCZOS).save(
        still, "JPEG", quality=92)
    dur, fps = 5.0, 30
    frames = int(dur * fps)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(still),
        "-vf",
        f"scale=1296:2304,zoompan=z='1+0.05*on/{frames}':d={frames}"
        f":x='iw/2-(iw/zoom/2)':y='ih/4-(ih/zoom/4)':s=1080x1920:fps={fps}",
        "-t", str(dur), "-c:v", "libx264", "-crf", "18", "-pix_fmt",
        "yuv420p", "-an", str(OUT_DIR / "pinned_broll.mp4")], check=True)
    print("OK", OUT_DIR / "pinned_broll.mp4")


if __name__ == "__main__":
    main()
