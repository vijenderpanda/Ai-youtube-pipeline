#!/usr/bin/env python3
"""Cards for a LYRIC DUEL Short (Aashiqana): versus / recap / announce / number chips.

The duel is a comment-bait derivative cut: two lines of an already-shipped song are
pitted against each other ("1 ya 2?"). Three 1080x1920 PIL cards carry the format and a
pair of small numeral chips mark which line is on screen.

  versus   frame-zero card. Both stills DUOTONED (teal-blue rain over amber dusk) and
           split by a slanted gold seam, with a VS lozenge. Frame 0 is the de-facto
           Shorts thumbnail (playbook S5), so it is designed to read at ~240px.
  recap    both romanized lines stacked with their numerals + the comment CTA, over a
           blurred/darkened blend of the same two frames.
  announce release pointer. TEXT-ONLY in the brand palette (no photo) so it can never be
           mistaken for a new song's visual.
  chip     a numeral chip, transparent PNG, overlaid on the lyric beats.

Usage:
  python3 scripts/make_duel_cards.py --kind versus  --top A.jpg --bottom B.jpg --out c.png
  python3 scripts/make_duel_cards.py --kind recap   --top A.jpg --bottom B.jpg \
      --line1 "..." --line2 "..." --out r.png
  python3 scripts/make_duel_cards.py --kind announce --title "AAJA VE" --sub "ab live" \
      --emoji "\U0001FAB7" --cta "Channel pe suno." --out a.png
  python3 scripts/make_duel_cards.py --kind chip --num 1 --out chip1.png
"""
import argparse
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
FB = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
FI = "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"
FE = "/System/Library/Fonts/Apple Color Emoji.ttc"

# --- Aashiqana palette (BRAND-BIBLE S1): monsoon teal-blue + warm amber ---
GOLD = (240, 196, 92, 255)
WHITE = (255, 246, 250, 255)
PINK = (244, 206, 220, 255)
INK = (9, 6, 16, 255)
TEAL_LO, TEAL_HI = (6, 26, 40), (168, 226, 236)      # duotone ramp, rain side
AMBER_LO, AMBER_HI = (34, 14, 2), (255, 214, 128)    # duotone ramp, dusk side


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def cover(img, w, h, cx=0.5, cy=0.5):
    iw, ih = img.size
    s = max(w / iw, h / ih)
    img = img.resize((max(w, int(iw * s)), max(h, int(ih * s))), Image.LANCZOS)
    x = int((img.width - w) * cx)
    y = int((img.height - h) * cy)
    return img.crop((x, y, x + w, y + h))


def duotone(img, lo, hi):
    """Map luminance onto a two-colour ramp. Keeps the frame legible at thumbnail size."""
    g = img.convert("L")
    chans = [g.point([int(lo[c] + (hi[c] - lo[c]) * (i / 255.0)) for i in range(256)])
             for c in range(3)]
    return Image.merge("RGB", chans)


def tracked_w(d, text, fnt, track=0):
    """Measure only -- never draw to measure (playbook S13: a measure pass leaves ink)."""
    if not track:
        bb = d.textbbox((0, 0), text, font=fnt)
        return bb[2] - bb[0]
    return sum(d.textlength(ch, font=fnt) + track for ch in text) - track


def centered(d, cx, y, text, fnt, fill, so=4, track=0):
    """Draw `text` centred on cx with a soft dark extrude. y is the TOP of the glyph box."""
    if track:
        widths = [d.textlength(ch, font=fnt) + track for ch in text]
        x = cx - (sum(widths) - track) / 2
        for ch, wch in zip(text, widths):
            for dx, dy in ((so, so), (-so, so), (so, -so), (-so, -so)):
                d.text((x + dx, y + dy), ch, font=fnt, fill=(0, 0, 0, 200))
            d.text((x, y), ch, font=fnt, fill=fill)
            x += wch
        return
    bb = d.textbbox((0, 0), text, font=fnt)
    x = cx - (bb[2] - bb[0]) / 2 - bb[0]
    for dx, dy in ((so, so), (-so, so), (so, -so), (-so, -so), (0, so), (0, -so)):
        d.text((x + dx, y + dy), text, font=fnt, fill=(0, 0, 0, 200))
    d.text((x, y), text, font=fnt, fill=fill)


def fit_font(d, text, maxw, start, floor=28, track=0):
    """Autoshrink so a glyph can never reach the frame edge (playbook S5 Cover rule)."""
    fs = start
    while fs > floor and tracked_w(d, text, font(FB, fs), track) > maxw:
        fs -= 2
    return font(FB, fs), fs


def emoji_img(ch, target_h):
    """Apple Color Emoji only has fixed bitmap strikes -- render at 160 and downscale."""
    f = font(FE, 160)
    im = Image.new("RGBA", (260, 260), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((20, 20), ch, font=f, embedded_color=True)
    bb = im.getbbox()
    if not bb:
        return None
    im = im.crop(bb)
    s = target_h / im.height
    return im.resize((max(1, int(im.width * s)), target_h), Image.LANCZOS)


def scrim(card, top_a=150, mid_a=205):
    """Monsoon-ink vertical scrim so type always clears its background."""
    sc = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sc)
    for i in range(H):
        t = abs(i - H * 0.5) / (H * 0.5)
        sd.line([(0, i), (W, i)], fill=INK[:3] + (int(mid_a - (mid_a - top_a) * t ** 1.6),))
    return Image.alpha_composite(card, sc)


def numeral_badge(d, cx, cy, num, r=64, fs=76):
    """Amber disc + dark numeral -- the duel's one repeated mark."""
    d.ellipse([cx - r - 5, cy - r - 5, cx + r + 5, cy + r + 5], fill=(0, 0, 0, 130))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GOLD, outline=(255, 232, 186, 255), width=3)
    f = font(FB, fs)
    bb = d.textbbox((0, 0), num, font=f)
    d.text((cx - (bb[2] - bb[0]) / 2 - bb[0], cy - (bb[3] - bb[1]) / 2 - bb[1]),
           num, font=f, fill=(28, 16, 6, 255))


# ---------------------------------------------------------------- versus

def build_versus(a):
    seam_l, seam_r = 900, 1010          # slanted seam, left edge -> right edge
    top = duotone(cover(Image.open(a.top).convert("RGB"), W, 1060, cy=0.35), TEAL_LO, TEAL_HI)
    bot = duotone(cover(Image.open(a.bottom).convert("RGB"), W, 1060, cy=0.30), AMBER_LO, AMBER_HI)

    card = Image.new("RGBA", (W, H), INK)
    card.paste(top.convert("RGBA"), (0, 0))
    # bottom panel masked to the slant so the seam is a designed edge, not a paste line
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon([(0, seam_l), (W, seam_r), (W, H), (0, H)], fill=255)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer.paste(bot.convert("RGBA"), (0, H - 1060))
    card = Image.composite(layer, card, mask)
    # type-only scrims: the panels stay bright (frame 0 competes at ~240px in-feed,
    # playbook S5), and only the two type bands are darkened enough to carry gold.
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    for i in range(320):                                   # wordmark band, top
        bd.line([(0, i), (W, i)], fill=INK[:3] + (int(185 * (1 - i / 320.0) ** 1.1),))
    for i in range(1400, H):                               # headline band, bottom
        t = (i - 1400) / (H - 1400)
        bd.line([(0, i), (W, i)], fill=INK[:3] + (int(200 * min(1.0, t * 1.7) ** 0.9),))
    card = Image.alpha_composite(card, band)

    d = ImageDraw.Draw(card)
    d.line([(0, seam_l), (W, seam_r)], fill=GOLD[:3] + (215,), width=7)
    d.line([(0, seam_l + 14), (W, seam_r + 14)], fill=GOLD[:3] + (70,), width=2)

    centered(d, W // 2, 118, "AASHIQANA", font(FB, 44), PINK, so=3, track=16)
    centered(d, W // 2, 196, "LYRIC DUEL", font(FB, 34), GOLD, so=3, track=13)

    # the two contenders, one per panel, in the panel's own dead corner
    centered(d, 250, 560, "1", font(FB, 240), WHITE, so=7)
    centered(d, 890, 1105, "2", font(FB, 240), WHITE, so=7)

    # VS lozenge sits ON the seam -- the one element that belongs to both halves
    cy = (seam_l + seam_r) // 2
    d.ellipse([W // 2 - 108, cy - 108, W // 2 + 108, cy + 108], fill=(0, 0, 0, 165))
    d.ellipse([W // 2 - 100, cy - 100, W // 2 + 100, cy + 100], outline=GOLD, width=6)
    centered(d, W // 2, cy - 62, "VS", font(FB, 108), GOLD, so=5, track=6)

    f, _ = fit_font(d, a.headline, W - 150, 108, track=8)
    centered(d, W // 2, 1600, a.headline, f, GOLD, so=5, track=8)
    centered(d, W // 2, 1745, a.sub, font(FI, 52), PINK, so=3)
    card.convert("RGB").save(a.out)


# ---------------------------------------------------------------- recap

def build_recap(a):
    top = cover(Image.open(a.top).convert("RGB"), W, H // 2, cy=0.35)
    bot = cover(Image.open(a.bottom).convert("RGB"), W, H // 2, cy=0.30)
    bg = Image.new("RGB", (W, H))
    bg.paste(duotone(top, TEAL_LO, TEAL_HI), (0, 0))
    bg.paste(duotone(bot, AMBER_LO, AMBER_HI), (0, H // 2))
    # blurred enough to be a field, light enough that the two worlds still read
    card = scrim(bg.filter(ImageFilter.GaussianBlur(38)).convert("RGBA"), top_a=132, mid_a=178)
    d = ImageDraw.Draw(card)

    centered(d, W // 2, 250, "KAUNSI LINE?", font(FB, 54), GOLD, so=4, track=14)
    d.line([(W // 2 - 150, 340), (W // 2 + 150, 340)], fill=GOLD[:3] + (140,), width=2)

    for num, lines, y0 in (("1", a.line1.split("|"), 430), ("2", a.line2.split("|"), 900)):
        numeral_badge(d, W // 2, y0 + 60, num)
        y = y0 + 165
        for ln in lines:
            f, fs = fit_font(d, ln.strip(), W - 130, 66)
            centered(d, W // 2, y, ln.strip(), f, WHITE, so=4)
            y += int(fs * 1.32)

    d.line([(W // 2 - 90, 810), (W // 2 + 90, 810)], fill=GOLD[:3] + (110,), width=2)

    centered(d, W // 2, 1380, "1 ya 2?", font(FB, 116), GOLD, so=6, track=6)
    sub, fs = "Comment mein batao", 56
    em = emoji_img("\U0001F447", 58)
    f = font(FB, fs)
    tw = tracked_w(d, sub, f) + (em.width + 18 if em else 0)
    x = W // 2 - tw / 2
    bb = d.textbbox((0, 0), sub, font=f)
    for dx, dy in ((3, 3), (-3, 3), (3, -3), (-3, -3)):
        d.text((x + dx - bb[0], 1580 + dy - bb[1]), sub, font=f, fill=(0, 0, 0, 200))
    d.text((x - bb[0], 1580 - bb[1]), sub, font=f, fill=PINK)
    if em:
        card.alpha_composite(em, (int(x + tracked_w(d, sub, f) + 18), 1574))
    card.convert("RGB").save(a.out)


# ---------------------------------------------------------------- announce

def build_announce(a):
    """TEXT-ONLY, brand palette. No photo: the card points at a release, it does not
    depict one -- a still here would read as this Short being that song's video."""
    card = Image.new("RGBA", (W, H), INK)
    d = ImageDraw.Draw(card)
    for i in range(H):                      # monsoon teal-blue ink -> warm amber ink
        t = i / H
        d.line([(0, i), (W, i)],
               fill=(int(8 + 62 * t ** 1.4), int(40 - 4 * t), int(56 - 42 * t ** 0.8), 255))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([W // 2 - 660, 520, W // 2 + 660, 1560], fill=(240, 178, 78, 78))
    card = Image.alpha_composite(card, glow.filter(ImageFilter.GaussianBlur(190)))
    d = ImageDraw.Draw(card)

    y = 560
    centered(d, W // 2, y, "AASHIQANA", font(FB, 44), PINK, so=3, track=16)
    y += 108
    d.line([(W // 2 - 170, y), (W // 2 + 170, y)], fill=GOLD[:3] + (150,), width=2)
    y += 62

    f, fs = fit_font(d, a.title, W - 150, 148, track=12)
    centered(d, W // 2, y, a.title, f, GOLD, so=6, track=12)
    y += int(fs * 1.30)

    em = emoji_img(a.emoji, 74) if a.emoji else None
    sf = font(FB, 72)
    tw = tracked_w(d, a.sub, sf) + (em.width + 22 if em else 0)
    x = W // 2 - tw / 2
    bb = d.textbbox((0, 0), a.sub, font=sf)
    for dx, dy in ((4, 4), (-4, 4), (4, -4), (-4, -4)):
        d.text((x + dx - bb[0], y + dy - bb[1]), a.sub, font=sf, fill=(0, 0, 0, 200))
    d.text((x - bb[0], y - bb[1]), a.sub, font=sf, fill=WHITE)
    if em:
        card.alpha_composite(em, (int(x + tracked_w(d, a.sub, sf) + 22), y + 4))
    y += 152

    d.line([(W // 2 - 110, y), (W // 2 + 110, y)], fill=GOLD[:3] + (120,), width=2)
    y += 54
    centered(d, W // 2, y, a.cta, font(FI, 58), PINK, so=3)
    y += 130

    # subscribe pill -- sized from ink, never a hardcoded right edge (playbook S13)
    pf = font(FB, 56)
    pw = tracked_w(d, "SUBSCRIBE", pf, 12) + 96
    d.rounded_rectangle([W // 2 - pw / 2, y, W // 2 + pw / 2, y + 112], radius=56,
                        fill=(0, 0, 0, 120), outline=GOLD, width=4)
    centered(d, W // 2, y + 24, "SUBSCRIBE", pf, GOLD, so=3, track=12)
    card.convert("RGB").save(a.out)


# ---------------------------------------------------------------- chip

def build_chip(a):
    S = 168
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    numeral_badge(d, S // 2, S // 2, str(a.num), r=72, fs=88)
    im.save(a.out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True,
                    choices=["versus", "recap", "announce", "chip"])
    ap.add_argument("--top"); ap.add_argument("--bottom")
    ap.add_argument("--line1"); ap.add_argument("--line2")
    ap.add_argument("--headline", default="KAUNSI LINE?")
    ap.add_argument("--title"); ap.add_argument("--emoji", default="")
    ap.add_argument("--sub", default=""); ap.add_argument("--cta", default="")
    ap.add_argument("--num", type=int, default=1)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    {"versus": build_versus, "recap": build_recap,
     "announce": build_announce, "chip": build_chip}[a.kind](a)
    print(">> wrote", a.out)


if __name__ == "__main__":
    main()
