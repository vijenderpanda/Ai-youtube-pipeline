#!/usr/bin/env python3
"""Build Club — Season 1 playlist cover (1280x720, YouTube playlist thumbnail).

Landscape cut of the locked series language: blueprint grid + ink, real Sol,
the premium phone, big Anton stack, season dots. Uploaded by VJ via
playlist Edit -> "Choose from library" (UI-only; no Data API for this).

  python3 channels/claude-tricks/gen_bc_playlist_cover.py
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "scripts"))

from make_doc_mock import (  # noqa: E402
    S, MAGENTA, YELLOW, TXT, DIM, FAINT, INK_TOP, font, tw, tracked,
    tracked_w,
)
from gen_bc01_format_mock import chip  # noqa: E402

W, H = 1280, 720
OUT = HERE / "assets" / "epbc01" / "playlist_cover_s1.jpg"
SOL = (HERE / "assets/character/host_library/outfit_11_sol_magenta/wide.jpg")


def main():
    import numpy as np
    top = np.array((11, 10, 16), dtype=np.float32)
    bot = np.array((26, 16, 30), dtype=np.float32)
    ramp = np.linspace(0, 1, H * S, dtype=np.float32)[:, None, None]
    arr = np.repeat(top[None, None, :] * (1 - ramp) + bot[None, None, :] * ramp,
                    W * S, axis=1).astype("uint8")
    canvas = Image.fromarray(arr, "RGB").convert("RGBA")
    d = ImageDraw.Draw(canvas, "RGBA")

    # blueprint grid
    minor, major = (44, 44, 62), (62, 58, 86)
    for gx in range(0, W + 1, 64):
        d.line([(gx * S, 0), (gx * S, H * S)],
               fill=major if gx % 320 == 0 else minor, width=1 * S)
    for gy in range(0, H + 1, 64):
        d.line([(0, gy * S), (W * S, gy * S)],
               fill=major if gy % 320 == 0 else minor, width=1 * S)

    # right: Sol (real still) in a rounded card
    tile = ImageOps.fit(Image.open(SOL).convert("RGB"), (560 * S, 560 * S),
                        Image.LANCZOS, centering=(0.5, 0.4))
    mask = Image.new("L", tile.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, tile.width, tile.height],
                                           radius=36 * S, fill=255)
    canvas.paste(tile, (672 * S, 80 * S), mask)
    d = ImageDraw.Draw(canvas, "RGBA")
    d.rounded_rectangle([672 * S, 80 * S, 1232 * S, 640 * S], radius=36 * S,
                        outline=(255, 255, 255, 40), width=2 * S)

    # left: type stack
    f = font("display", 30)
    tracked(d, (64 * S, 84 * S), "AI UNPACKED VJ PRESENTS", f, DIM, 6.0)
    f1 = font("display", 128)
    d.text((60 * S, 130 * S), "BUILD", font=f1, fill=TXT)
    d.text((60 * S, 268 * S), "CLUB", font=f1, fill=MAGENTA)
    lay, pos = chip(d, 292, 470, "SEASON 1", px=44, rot=-2)
    canvas.paste(lay, pos, lay)
    d = ImageDraw.Draw(canvas, "RGBA")
    fs = font("ui_sb", 34)
    d.text((64 * S, 528 * S), "Your idea", font=fs, fill=TXT)
    ax = 64 + int(tw(d, "Your idea", fs)) // S + 14
    ay = 528 + 22
    d.line([(ax * S, ay * S), ((ax + 34) * S, ay * S)], fill=YELLOW,
           width=5 * S)
    d.polygon([((ax + 34) * S, (ay - 8) * S), ((ax + 34) * S, (ay + 8) * S),
               ((ax + 46) * S, ay * S)], fill=YELLOW)
    d.text(((ax + 58) * S, 528 * S), "a live app.", font=fs, fill=TXT)
    d.text((64 * S, 578 * S), "One Friday at a time. Free.",
           font=font("ui", 30), fill=DIM)

    # season dots
    x, r, gap = 72, 10, 40
    for i in range(6):
        box = [(x - r) * S, (652 - r) * S, (x + r) * S, (652 + r) * S]
        if i == 0:
            d.ellipse(box, fill=MAGENTA)
        else:
            d.ellipse(box, outline=FAINT, width=2 * S)
        x += gap

    canvas.convert("RGB").resize((W, H), Image.LANCZOS).save(
        OUT, "JPEG", quality=93)
    print("OK", OUT)


if __name__ == "__main__":
    main()
