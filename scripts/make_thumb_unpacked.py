#!/usr/bin/env python3
"""
AI Unpacked (claude-tricks) 16:9 custom thumbnail — 1280x720.

Same visual system as the FROZEN "Poster Duotone" cover card (frame zero) so the
watch page / channel search / cross-post art reads as one design language:
magenta-duotone host photo, extruded Anton stack in deep magenta #3C0A28,
punch line in a slanted yellow chip, magenta pill anchor, watermark.

Layout differs only because the canvas is landscape: the duotone host is a
full-bleed left-third panel, the type lives on the dark-ink field to its right.

Usage:
  python3 scripts/make_thumb_unpacked.py \
    --photo channels/claude-tricks/assets/character/host_canonical.jpg \
    --pill MEMORY --line1 "YOUR AI" --line2 "FORGETS YOU" \
    --out renders_out/.../thumb_ep24.jpg
"""
import argparse
import os
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

W, H = 1280, 720
SAFE = 0.05
SAFE_X, SAFE_Y = int(W * SAFE), int(H * SAFE)          # 64, 36

INK = (11, 7, 16)              # dark-ink base
MAGENTA = (224, 33, 138)       # #E0218A brand
YELLOW = (255, 209, 10)
EXTRUDE = (60, 10, 40)         # #3C0A28 — frozen cover extrude
WHITE = (250, 248, 252)
DUO_SHADOW = (10, 6, 16)
DUO_HIGH = (168, 62, 120)      # cover ramp lifted so the face reads at 320px

FONT = "remotion-studio/public/fonts/Anton.ttf"
PANEL_W = 470                  # left third
RULE_W = 5


def duotone_lut(shadow, highlight):
    lut = []
    for ch in range(3):
        lut += [round(shadow[ch] + (highlight[ch] - shadow[ch]) * (i / 255)) for i in range(256)]
    return lut


def font_at(size):
    return ImageFont.truetype(FONT, size)


def fit_font(text, max_w, start, floor=28):
    """Autoshrink so type can never clip the frame (mirrors components/fitText.ts)."""
    size = start
    while size > floor:
        f = font_at(size)
        if f.getbbox(text)[2] - f.getbbox(text)[0] <= max_w:
            return f
        size -= 2
    return font_at(floor)


def host_panel(photo_path, w, h):
    """Magenta-duotone crop of the host, framed on the face, filling w x h."""
    im = Image.open(photo_path).convert("RGB")
    # face-centred source window (host_canonical is a 832x1216 studio portrait)
    fx, fy = 0.53, 0.44
    win_h = int(im.height * 0.70)
    win_w = int(win_h * w / h)
    cx, cy = im.width * fx, im.height * fy
    x0 = max(0, min(im.width - win_w, int(cx - win_w / 2)))
    y0 = max(0, min(im.height - win_h, int(cy - win_h * 0.42)))
    im = im.crop((x0, y0, x0 + win_w, y0 + win_h)).resize((w, h), Image.LANCZOS)

    g = ImageEnhance.Contrast(im.convert("L")).enhance(1.16)
    out = Image.merge("RGB", (g, g, g)).point(duotone_lut(DUO_SHADOW, DUO_HIGH))

    # bottom + top vignette so the panel sinks into the ink field
    mask = Image.new("L", (w, h), 0)
    px = mask.load()
    for y in range(h):
        bot = max(0.0, (y - h * 0.66) / (h * 0.34)) * 0.82
        top = max(0.0, (h * 0.16 - y) / (h * 0.16)) * 0.55
        a = int(min(1.0, bot + top) * 255)
        for x in range(w):
            px[x, y] = a
    dark = Image.new("RGB", (w, h), INK)
    out = Image.composite(dark, out, mask)

    # soft key light on the face so the eyes still read at 320x180
    spot = Image.new("L", (w, h), 0)
    ImageDraw.Draw(spot).ellipse([w * 0.10, h * 0.20, w * 0.86, h * 0.70], fill=118)
    spot = spot.filter(ImageFilter.GaussianBlur(70))
    return Image.composite(ImageEnhance.Brightness(out).enhance(1.42), out, spot)


def layer_extruded(text, font, depth=9):
    """White Anton with the deep-magenta cover extrude, on its own RGBA layer."""
    b = font.getbbox(text)
    pad = 40 + depth
    lay = Image.new("RGBA", (b[2] - b[0] + pad * 2, b[3] - b[1] + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    ox, oy = pad - b[0], pad - b[1]
    for i in range(depth, 0, -1):
        d.text((ox + i, oy + i), text, font=font, fill=EXTRUDE + (255,))
    d.text((ox, oy), text, font=font, fill=WHITE + (255,),
           stroke_width=2, stroke_fill=(24, 8, 20, 255))
    return lay


def layer_chip(text, font, pad_x=30, pad_y=18):
    """Punch line in a yellow chip (black type), on its own RGBA layer."""
    b = font.getbbox(text)
    tw, th = b[2] - b[0], b[3] - b[1]
    w, h = tw + pad_x * 2, th + pad_y * 2
    m = 26
    lay = Image.new("RGBA", (w + m * 2, h + m * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([m + 6, m + 7, m + w + 5, m + h + 6], radius=16, fill=(30, 6, 22, 210))
    d.rounded_rectangle([m, m, m + w, m + h], radius=16, fill=YELLOW + (255,))
    d.text((m + pad_x - b[0], m + pad_y - b[1]), text, font=font, fill=(12, 8, 14, 255))
    return lay


def layer_pill(text, font, pad_x=22, pad_y=11):
    b = font.getbbox(text)
    tw, th = b[2] - b[0], b[3] - b[1]
    w, h = tw + pad_x * 2, th + pad_y * 2
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=MAGENTA + (255,))
    d.text((pad_x - b[0], pad_y - b[1]), text, font=font, fill=WHITE + (255,))
    return lay


def paste_left(canvas, lay, left, cy, deg):
    """Rotate, then place so the *ink* (not the transparent pad) starts at `left`."""
    lay = lay.rotate(deg, resample=Image.BICUBIC, expand=True)
    bb = lay.getbbox()
    x = int(left - bb[0])
    y = int(cy - (bb[1] + bb[3]) / 2)
    canvas.alpha_composite(lay, (x, y))
    return (x + bb[0], y + bb[1], x + bb[2], y + bb[3])


def watermark(canvas, right, bottom):
    f = font_at(30)
    parts = [("AI ", WHITE), ("UNPACKED ", MAGENTA), ("VJ", YELLOW)]
    widths = [f.getbbox(t)[2] - f.getbbox(t)[0] for t, _ in parts]
    total = sum(widths)
    b = f.getbbox("AI UNPACKED VJ")
    h = b[3] - b[1]
    lay = Image.new("RGBA", (total + 36, h + 22), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([0, 0, lay.width - 1, lay.height - 1], radius=10, fill=(18, 8, 24, 165))
    x = 18
    for (t, col), w in zip(parts, widths):
        d.text((x - f.getbbox(t)[0], 11 - b[1]), t, font=f, fill=col + (255,))
        x += w
    pos = (right - lay.width, bottom - lay.height)
    canvas.alpha_composite(lay, pos)
    return (pos[0] + 18, pos[1] + 11, pos[0] + 18 + total, pos[1] + 11 + h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--photo", required=True)
    ap.add_argument("--pill", default="MEMORY")
    ap.add_argument("--line1", default="YOUR AI")
    ap.add_argument("--line2", default="FORGETS YOU")
    ap.add_argument("--out", required=True)
    ap.add_argument("--proof", default=None, help="also write a downscaled readability proof")
    ap.add_argument("--proof-width", type=int, default=320,
                    help="width of the readability proof (default 320)")
    ap.add_argument("--safe-pct", type=float, default=SAFE * 100,
                    help="safe-margin percent used for placement + the check (default 5)")
    ap.add_argument("--quality", type=int, default=90)
    a = ap.parse_args()

    global SAFE_X, SAFE_Y
    SAFE_X, SAFE_Y = int(W * a.safe_pct / 100), int(H * a.safe_pct / 100)

    canvas = Image.new("RGBA", (W, H), INK + (255,))
    canvas.alpha_composite(host_panel(a.photo, PANEL_W, H).convert("RGBA"), (0, 0))

    ImageDraw.Draw(canvas).rectangle([PANEL_W, 0, PANEL_W + RULE_W - 1, H],
                                     fill=MAGENTA + (255,))
    # faint magenta bloom off the rule into the ink field (own layer: alpha blends)
    bloom = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bloom)
    for i in range(64):
        bd.line([(PANEL_W + RULE_W + i, 0), (PANEL_W + RULE_W + i, H)],
                fill=MAGENTA + (int(40 * (1 - i / 64)),))
    canvas.alpha_composite(bloom)

    col_x = PANEL_W + RULE_W + 46                 # 521 — left rail for the type stack
    col_w = (W - SAFE_X) - col_x                  # to the 5% right margin

    f_pill = font_at(36)
    f1 = fit_font(a.line1, col_w - 16, 208)
    f2 = fit_font(a.line2, col_w - 130, 130)      # chip padding + tilt eat width

    boxes = {}
    boxes["pill"] = paste_left(canvas, layer_pill(a.pill, f_pill), col_x + 6, 140, 0)
    boxes["line1"] = paste_left(canvas, layer_extruded(a.line1, f1, depth=11), col_x, 330, 2)
    boxes["chip"] = paste_left(canvas, layer_chip(a.line2, f2), col_x, 522, 3)
    boxes["watermark"] = watermark(canvas, W - SAFE_X, H - SAFE_Y)

    ok = True
    for k, b in boxes.items():
        inside = b[0] >= SAFE_X and b[1] >= SAFE_Y and b[2] <= W - SAFE_X and b[3] <= H - SAFE_Y
        ok &= inside
        print(f"   {k:10s} {b}  {'ok' if inside else 'OUTSIDE SAFE MARGIN'}")

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    rgb = canvas.convert("RGB")
    rgb.save(a.out, "JPEG", quality=a.quality, subsampling=0, optimize=True)
    print(f">> {a.out} {rgb.size} {os.path.getsize(a.out)} bytes  safe={ok}")

    if a.proof:
        pw = a.proof_width
        ph = round(pw * H / W)
        rgb.resize((pw, ph), Image.LANCZOS).save(a.proof, "JPEG", quality=92, subsampling=0)
        print(f">> {a.proof} {pw}x{ph} readability proof")


if __name__ == "__main__":
    main()
