#!/usr/bin/env python3
"""PIL cards for the Aaja Ve "OUT NOW" glimpse Short (9:16, 1080x1920).

Two cards, both composed on the SAME band geometry the body of the cut uses
(1080x1200 band at y=250 over a blurred, darkened copy of the frame, gold hairlines)
so the title card reads as the same film rather than a bolt-on slate -- which is what
makes the end frame a clean loop back into 0:00.

  title  : S09_THUMB (dusk ridge two-shot) in the band, "AAJA VE" + "AB LIVE" set in
           Didot gold in the 470px dead zone below the band. Frame-zero == end-frame.
  subscribe : text-only brand card, deep teal-blue -> amber vertical grade + grain,
           "Poora gaana - channel pe [rose]" / "Subscribe".

Emoji note: Apple Color Emoji is an sbix font that only accepts a handful of ppem values
-- which ones depends on the Pillow/FreeType build (137 is the usual answer and is
REJECTED here; 160 and 96 load). Asking for the display size directly raises "invalid
pixel size", so the glyph is drawn at the first ppem that loads and then downscaled.

Usage: python3 scripts/make_aaja_ve_outnow_cards.py --outdir <dir>
"""
import argparse, os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
BAND_W, BAND_H, BAND_Y = 1080, 1200, 250

GOLD = (240, 196, 92)
GOLD_SOFT = (232, 205, 150)
CREAM = (250, 243, 232)
TEAL_TOP = (14, 34, 44)
TEAL_MID = (22, 52, 62)
AMBER_BOT = (86, 52, 30)

DIDOT = "/System/Library/Fonts/Supplemental/Didot.ttc"
GEORGIA_B = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
GEORGIA = "/System/Library/Fonts/Supplemental/Georgia.ttf"
EMOJI = "/System/Library/Fonts/Apple Color Emoji.ttc"
EMOJI_PPEM = (160, 137, 96, 64)   # first one FreeType accepts wins


def font(path, size, index=0):
    try:
        return ImageFont.truetype(path, size, index=index)
    except Exception:
        return ImageFont.load_default()


def text_w(d, s, f, track=0):
    if not track:
        return d.textlength(s, font=f)
    return sum(d.textlength(c, font=f) + track for c in s) - track


def draw_tracked(d, xy, s, f, fill, track=0, shadow=None):
    """Letter-spaced text (PIL has no tracking). shadow = (dx, dy, rgba)."""
    x, y = xy
    for c in s:
        if shadow:
            dx, dy, sc = shadow
            d.text((x + dx, y + dy), c, font=f, fill=sc)
        d.text((x, y), c, font=f, fill=fill)
        x += d.textlength(c, font=f) + track


def centered_tracked(d, y, s, f, fill, track=0, shadow=None):
    w = text_w(d, s, f, track)
    draw_tracked(d, ((W - w) / 2, y), s, f, fill, track, shadow)
    return w


def emoji_tile(ch, size):
    """Colour emoji at an arbitrary display size (sbix font: draw at 137, downscale)."""
    for ppem in EMOJI_PPEM:
        try:
            f = ImageFont.truetype(EMOJI, ppem)
        except OSError:
            continue                      # this build rejects that ppem
        tile = Image.new("RGBA", (ppem * 2, ppem * 2), (0, 0, 0, 0))
        ImageDraw.Draw(tile).text((0, 0), ch, font=f, embedded_color=True)
        bb = tile.getbbox()
        if not bb:
            continue                      # font has no glyph for this codepoint
        tile = tile.crop(bb)
        r = size / tile.height
        return tile.resize((max(1, int(tile.width * r)), size), Image.LANCZOS)
    return None


def grain(img, amount=7):
    import random
    random.seed(20260807)
    n = Image.new("L", (W // 2, H // 2))
    n.putdata([random.gauss(128, amount) for _ in range(n.width * n.height)])
    n = n.resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(0.4))
    return Image.blend(img, Image.merge("RGB", (n, n, n)), 0.055)


def band_plate(still_path):
    """Blurred cover backdrop + sharp 0.9-aspect band + gold hairlines -- the body's look."""
    src = Image.open(still_path).convert("RGB")
    sw, sh = src.size

    s = max(W / sw, H / sh)
    bg = src.resize((int(sw * s), int(sh * s)), Image.LANCZOS)
    bx, by = (bg.width - W) // 2, (bg.height - H) // 2
    bg = bg.crop((bx, by, bx + W, by + H)).filter(ImageFilter.GaussianBlur(34))
    bg = Image.eval(bg, lambda v: int(v * 0.80))

    s2 = max(BAND_W / sw, BAND_H / sh)
    bd = src.resize((int(sw * s2), int(sh * s2)), Image.LANCZOS)
    cx, cy = (bd.width - BAND_W) // 2, (bd.height - BAND_H) // 2
    bd = bd.crop((cx, cy, cx + BAND_W, cy + BAND_H))

    bg.paste(bd, (0, BAND_Y))
    d = ImageDraw.Draw(bg, "RGBA")
    d.rectangle([0, BAND_Y, W, BAND_Y + 2], fill=GOLD + (77,))
    d.rectangle([0, BAND_Y + BAND_H - 2, W, BAND_Y + BAND_H], fill=GOLD + (77,))
    return bg


def card_title(still_path, out):
    img = band_plate(still_path)
    d = ImageDraw.Draw(img, "RGBA")

    # scrim under the type zone so gold on dusk sky stays legible
    zone = Image.new("RGBA", (W, H - (BAND_Y + BAND_H)), (0, 0, 0, 0))
    zd = ImageDraw.Draw(zone)
    for i in range(zone.height):
        zd.line([(0, i), (W, i)], fill=(6, 14, 20, int(150 * min(1, i / 90))))
    img.paste(zone, (0, BAND_Y + BAND_H), zone)

    # wordmark above the band
    f_mark = font(GEORGIA, 34)
    centered_tracked(d, 150, "A A S H I Q A N A", f_mark, GOLD_SOFT + (215,), track=6,
                     shadow=(0, 2, (0, 0, 0, 170)))

    # title in the dead zone below the band
    f_title = font(DIDOT, 132, index=1)          # Didot Bold
    centered_tracked(d, BAND_Y + BAND_H + 78, "AAJA VE", f_title, GOLD, track=10,
                     shadow=(0, 5, (0, 0, 0, 190)))

    # "AB LIVE" in a hairline gold pill
    f_sub = font(GEORGIA_B, 46)
    label, track = "AB LIVE", 12
    tw = text_w(d, label, f_sub, track)
    pw, ph = tw + 92, 86
    px, py = (W - pw) / 2, BAND_Y + BAND_H + 268
    d.rounded_rectangle([px, py, px + pw, py + ph], radius=ph / 2,
                        fill=(10, 26, 34, 165), outline=GOLD + (225,), width=3)
    draw_tracked(d, (px + 46, py + 18), label, f_sub, GOLD, track,
                 shadow=(0, 2, (0, 0, 0, 160)))

    img = grain(img)
    img.save(out, quality=96)
    print(">> title card", out)


def card_subscribe(out):
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        if t < 0.62:
            u = t / 0.62
            c = tuple(int(TEAL_TOP[i] + (TEAL_MID[i] - TEAL_TOP[i]) * u) for i in range(3))
        else:
            u = (t - 0.62) / 0.38
            c = tuple(int(TEAL_MID[i] + (AMBER_BOT[i] - TEAL_MID[i]) * (u ** 1.6))
                      for i in range(3))
        d.line([(0, y), (W, y)], fill=c)

    # warm bloom low-right, like the golden-hour sun in the film
    bloom = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(bloom).ellipse([620, 1330, 1320, 2030], fill=(150, 96, 44))
    img = Image.blend(img, bloom.filter(ImageFilter.GaussianBlur(150)), 0.42)
    d = ImageDraw.Draw(img, "RGBA")

    # the band's gold hairlines, kept so the card belongs to the same cut
    d.rectangle([0, BAND_Y, W, BAND_Y + 2], fill=GOLD + (60,))
    d.rectangle([0, BAND_Y + BAND_H - 2, W, BAND_Y + BAND_H], fill=GOLD + (60,))

    f_mark = font(GEORGIA, 34)
    centered_tracked(d, 150, "A A S H I Q A N A", f_mark, GOLD_SOFT + (215,), track=6)

    # everything lives between y=500 and y=1400 -- above that the band hairline reads as
    # header, below it the Shorts UI (title, handle, action rail) eats the frame
    f_eyebrow = font(GEORGIA_B, 40)
    centered_tracked(d, 520, "A A J A   V E", f_eyebrow, GOLD + (230,), track=8)

    f_line = font(DIDOT, 66, index=1)
    # "Poora gaana - channel pe  [rose]"  (rose set as a colour tile on the baseline)
    part_a, part_b = "Poora gaana ", "channel pe"
    rose = emoji_tile("\U0001F940", 64)   # U+1F940 WILTED FLOWER (not U+1FAB7 lotus)
    wa = d.textlength(part_a, font=f_line)
    wdash = d.textlength("— ", font=f_line)
    wb = d.textlength(part_b, font=f_line)
    gap = 26
    total = wa + wdash + wb + (gap + rose.width if rose else 0)
    x = (W - total) / 2
    y = 630
    d.text((x, y), part_a, font=f_line, fill=CREAM + (240,)); x += wa
    d.text((x, y), "— ", font=f_line, fill=GOLD_SOFT + (200,)); x += wdash
    d.text((x, y), part_b, font=f_line, fill=GOLD); x += wb
    if rose:
        img.paste(rose, (int(x + gap), int(y + 14)), rose)

    # hairline rule + the ask
    d.rectangle([(W - 300) / 2, 790, (W + 300) / 2, 792], fill=GOLD + (120,))

    f_sub = font(GEORGIA_B, 92)
    label, track = "SUBSCRIBE", 14
    tw = text_w(d, label, f_sub, track)
    pw, ph = tw + 120, 156
    px, py = (W - pw) / 2, 880
    d.rounded_rectangle([px, py, px + pw, py + ph], radius=ph / 2,
                        fill=(240, 196, 92, 236))
    draw_tracked(d, (px + 60, py + 26), label, f_sub, (18, 32, 40), track)

    f_note = font(GEORGIA, 38)
    centered_tracked(d, 1110, "Poora gaana + video — description mein link", f_note,
                     CREAM + (205,), track=1)
    centered_tracked(d, 1180, "Original song & visuals created with AI", f_note,
                     CREAM + (150,), track=1)

    img = grain(img)
    img.save(out, quality=96)
    print(">> subscribe card", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--still",
                    default="channels/aashiqana/songs/02-aaja-ve/scenes/stills_final/S09_THUMB.jpg")
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    card_title(a.still, os.path.join(a.outdir, "card_title.jpg"))
    card_subscribe(os.path.join(a.outdir, "card_subscribe.jpg"))


if __name__ == "__main__":
    main()
