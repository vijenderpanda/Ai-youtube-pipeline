#!/usr/bin/env python3
"""BC02 hook illustration (1080x1920) — Chapter 2 opener art.

Same composition grammar as bc01 v4 hook (gen_bc01_hook.py): blueprint grid,
see-through window for the REAL talking host clip (HookCard owns all headline
words up top), magenta promise pill, and a phone in the lower third — but the
phone now shows the CHAT: a customer asks, the site answers by itself (the
chapter's proof). §4/#29: art never prints a string the HookCard overlay prints.

  python3 channels/claude-tricks/gen_bc02_hook.py
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageChops

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "scripts"))

from make_doc_mock import S, W, MAGENTA, TXT, bg, font, tw  # noqa: E402
from gen_bc01_format_mock import chip  # noqa: E402
from gen_bc01_outro import bubble, FAINT  # noqa: E402

H = 1920
OUT = HERE / "assets" / "epbc02" / "hook_art" / "smart_site.png"


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas = bg((W * S, H * S)).convert("RGBA")
    d = ImageDraw.Draw(canvas, "RGBA")

    minor, major = (44, 44, 62), (60, 56, 84)
    for gx in range(0, W + 1, 72):
        d.line([(gx * S, 0), (gx * S, H * S)],
               fill=major if gx % 360 == 0 else minor, width=1 * S)
    for gy in range(0, H + 1, 72):
        d.line([(0, gy * S), (W * S, gy * S)],
               fill=major if gy % 360 == 0 else minor, width=1 * S)

    # magenta promise pill
    t = "ONE PROMPT · NO CODE · STILL FREE"
    fp = font("ui_sb", 33)
    wpx = int(tw(d, t, fp)) + 60 * S
    x0, y0 = (W * S - wpx) // 2, 1122 * S
    d.rounded_rectangle([x0, y0, x0 + wpx, y0 + 76 * S], radius=38 * S,
                        fill=MAGENTA)
    d.text((x0 + 30 * S, y0 + 17 * S), t, font=fp, fill=TXT)

    # chat phone — customer asks, site answers (drawn, premium dark)
    lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay, "RGBA")
    bx0, by0, bx1, by1 = 285, 1215, 800, 1905
    ld.rounded_rectangle([bx0 * S, by0 * S, bx1 * S, by1 * S], radius=52 * S,
                         fill=(13, 12, 18), outline=(84, 80, 100), width=4 * S)
    m = 18 * S
    sx0, sy0, sx1, sy1 = bx0 * S + m, by0 * S + m, bx1 * S - m, by1 * S - m
    ld.rounded_rectangle([sx0, sy0, sx1, sy1], radius=38 * S, fill=(21, 17, 24))
    url = "anitas-tiffin.netlify.app"
    fu = font("ui", 22)
    ld.rounded_rectangle([sx0 + 26 * S, sy0 + 18 * S, sx1 - 26 * S, sy0 + 62 * S],
                         radius=22 * S, fill=(34, 30, 40))
    ld.text(((sx0 + sx1 - tw(ld, url, fu)) // 2, sy0 + 27 * S), url, font=fu,
            fill=(170, 164, 180))
    ld.text((sx0 + 34 * S, sy0 + 92 * S), "ASK US ANYTHING",
            font=font("display", 34), fill=TXT)
    _, ey = bubble(ld, sx0 + 34 * S, sy0 + 168 * S, "aaj ka menu kya hai?",
                   (48, 46, 58), TXT, tail="l")
    ld.text((sx0 + 34 * S, ey + 22 * S), "the site replies, on its own:",
            font=font("ui", 20), fill=FAINT)
    bubble(ld, sx0 + 56 * S, ey + 60 * S, "Rajma ₹120 · Thali ₹150",
           MAGENTA, TXT, tail="r")
    bubble(ld, sx0 + 56 * S, ey + 168 * S, "Order by 10 AM — bhej du?",
           MAGENTA, TXT, tail="r")
    lay = lay.rotate(-2.2, resample=Image.BICUBIC, center=(542 * S, 1560 * S))
    canvas = Image.alpha_composite(canvas, lay)

    im = canvas
    lay1, pos1 = chip(ImageDraw.Draw(im), 148, 1430, "AI", px=88, rot=-8)
    im.paste(lay1, pos1, lay1)
    lay2, pos2 = chip(ImageDraw.Draw(im), 950, 1390, "24", px=54, rot=7)
    im.paste(lay2, pos2, lay2)
    lay3, pos3 = chip(ImageDraw.Draw(im), 942, 1520, "/7", px=54, rot=7)
    im.paste(lay3, pos3, lay3)

    # see-through window for the live talking host (FramedHost zone)
    mask = Image.new("L", im.size, 255)
    ImageDraw.Draw(mask).rounded_rectangle(
        [48 * S, 270 * S, 1032 * S, 816 * S], radius=24 * S, fill=0)
    im.putalpha(ImageChops.darker(im.getchannel("A"), mask))

    im.resize((W, H), Image.LANCZOS).save(OUT, "PNG")
    print("OK", OUT)


if __name__ == "__main__":
    main()
