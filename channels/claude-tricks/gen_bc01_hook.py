#!/usr/bin/env python3
"""BC01 hook illustration (1080x1920) — Build Club Chapter 1 opener art.

Composition mirrors the VJ-approved a_hook mockup, MINUS the headline type:
the v16.3 HookCard overlay draws "STOP PAYING / FOR WEBSITES" + the kicker at
top (fitFont 128, ends ~y510), so the art carries visuals only below that —
real Sol wide band, the magenta 60-seconds pill, and the premium phone.
(§4/#29: never print a string the overlay also prints.)

  python3 channels/claude-tricks/gen_bc01_hook.py
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "scripts"))

from make_doc_mock import S, W, MAGENTA, TXT, bg, font, tw  # noqa: E402
from gen_bc01_format_mock import host_wide, phone, chip  # noqa: E402

H = 1920
OUT = HERE / "assets" / "epbc01" / "hook_art" / "stop_paying.png"


def main():
    """v3 (VJ 2026-08-13, dead-space pass): the series' blueprint grid + a big
    magenta bloom fill the canvas (ties the hook to the chapter card), Sol band
    is TALLER, the phone tilts over the band's bottom edge, and floating chips
    flank the phone so the lower third has no empty margins. HookCard still
    owns every headline word up top (0-460 is its zone)."""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    H = 1920
    canvas = bg((W * S, H * S)).convert("RGBA")
    d = ImageDraw.Draw(canvas, "RGBA")

    # blueprint grid (series identity)
    minor, major = (44, 44, 62), (60, 56, 84)
    for gx in range(0, W + 1, 72):
        d.line([(gx * S, 0), (gx * S, H * S)],
               fill=major if gx % 360 == 0 else minor, width=1 * S)
    for gy in range(0, H + 1, 72):
        d.line([(0, gy * S), (W * S, gy * S)],
               fill=major if gy % 360 == 0 else minor, width=1 * S)

    # v4 (VJ: "the host frame doesn't talk — fix it"): NO static Sol in the
    # art. An alpha WINDOW over the FramedHost card zone (Short.tsx: left 40,
    # top 262, 1000x562, r28, slight float) lets the REAL talking host clip
    # show through from frame 0. Window insets 8px so the floating card edge
    # never peeks past the hole.

    # magenta promise pill bridging window -> phone
    t = "FREE · NO CODE · LIVE TONIGHT"
    fp = font("ui_sb", 33)
    wpx = int(tw(d, t, fp)) + 60 * S
    x0, y0 = (W * S - wpx) // 2, 1122 * S
    d.rounded_rectangle([x0, y0, x0 + wpx, y0 + 76 * S], radius=38 * S,
                        fill=MAGENTA)
    d.text((x0 + 30 * S, y0 + 17 * S), t, font=fp, fill=TXT)

    # tilted premium phone (shorter — headline moved to 846-1110)
    lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay, "RGBA")
    phone(ld, (305, 1215, 795, 1905))
    lay = lay.rotate(-2.2, resample=Image.BICUBIC,
                     center=(550 * S, 1560 * S))
    canvas = Image.alpha_composite(canvas, lay)

    # floating flank chips — no empty margins beside the phone
    im = canvas
    lay1, pos1 = chip(ImageDraw.Draw(im), 150, 1430, "₹0", px=88, rot=-8)
    im.paste(lay1, pos1, lay1)
    lay2, pos2 = chip(ImageDraw.Draw(im), 936, 1390, "NO", px=54, rot=7)
    im.paste(lay2, pos2, lay2)
    lay3, pos3 = chip(ImageDraw.Draw(im), 928, 1520, "CODE", px=54, rot=7)
    im.paste(lay3, pos3, lay3)

    # punch the see-through window LAST so nothing drawn above fills it
    mask = Image.new("L", im.size, 255)
    ImageDraw.Draw(mask).rounded_rectangle(
        [48 * S, 270 * S, 1032 * S, 816 * S], radius=24 * S, fill=0)
    alpha = im.getchannel("A")
    from PIL import ImageChops
    im.putalpha(ImageChops.darker(alpha, mask))

    im.resize((W, H), Image.LANCZOS).save(OUT, "PNG")
    print("OK", OUT)


if __name__ == "__main__":
    main()
