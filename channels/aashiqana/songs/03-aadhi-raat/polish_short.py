#!/usr/bin/env python3
"""Add branding + retention overlays to a finished Aashiqana motion Short.
POV hook line (0-3.2s), subtle gold wordmark + @handle watermark (persistent),
'wait for it' tease (before the emotional line), and an end CTA card with the logo.
Emoji via Apple Color Emoji (rendered at 160, scaled). Text via Georgia/Kohinoor.
"""
import argparse, os, subprocess, sys, tempfile
REPO = os.path.abspath(__file__)
while REPO != "/" and not os.path.isdir(os.path.join(REPO, ".git")):
    REPO = os.path.dirname(REPO)
os.chdir(REPO)
from PIL import Image, ImageDraw, ImageFont

_ap = argparse.ArgumentParser()
_ap.add_argument("--src", default="channels/aashiqana/songs/03-aadhi-raat/renders/aadhiraat_motion_kissopen.mp4")
_ap.add_argument("--out", default="channels/aashiqana/songs/03-aadhi-raat/renders/aadhiraat_kissopen_branded.mp4")
_ap.add_argument("--pov1", default="POV: woh insaan jise tum")
_ap.add_argument("--pov2", default="chhod hi nahi paate")
_args = _ap.parse_args()
SRC = _args.src
OUT = _args.out
LOGO = "channels/aashiqana/brand/avatar_A.png"
W, H = 1080, 1920
HANDLE = "@aashiqana.diaries"
GOLD = (240, 200, 120, 255)
WHITE = (255, 255, 255, 255)

def F(paths, size):
    for p in paths:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()
GEO = lambda s: F(["/System/Library/Fonts/Supplemental/Georgia Bold.ttf"], s)
GEOI = lambda s: F(["/System/Library/Fonts/Supplemental/Georgia.ttf"], s)
DEVA = lambda s: F(["/System/Library/Fonts/Kohinoor.ttc"], s)
EMOJI = ImageFont.truetype("/System/Library/Fonts/Apple Color Emoji.ttc", 160)

def emoji_img(ch, target_h):
    im = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10, 5), ch, font=EMOJI, embedded_color=True)
    bb = im.getbbox()
    if bb: im = im.crop(bb)
    r = target_h / im.height
    return im.resize((max(1, int(im.width * r)), target_h), Image.LANCZOS)

def rich_line(segments, canvas_w, y_pad=0):
    """segments: list of (kind,val,font/size). kind in {'t','e'}. Returns centered RGBA strip."""
    # measure
    tmp = Image.new("RGBA", (10, 10)); d = ImageDraw.Draw(tmp)
    parts, total_w, max_h = [], 0, 0
    for kind, val, meta in segments:
        if kind == "t":
            font = meta
            bb = d.textbbox((0, 0), val, font=font, stroke_width=6)
            w, h = bb[2] - bb[0], bb[3] - bb[1]
            parts.append(("t", val, font, w, h, bb[1]))
        else:
            im = emoji_img(val, meta)
            w, h = im.width, im.height
            parts.append(("e", im, None, w, h, 0))
        total_w += w + 12; max_h = max(max_h, h)
    total_w -= 12
    strip = Image.new("RGBA", (canvas_w, max_h + 20 + y_pad), (0, 0, 0, 0))
    sd = ImageDraw.Draw(strip)
    x = (canvas_w - total_w) // 2; base = 10
    for p in parts:
        if p[0] == "t":
            _, val, font, w, h, oy = p
            sd.text((x, base - oy), val, font=font, fill=WHITE if font is not GOLD else GOLD,
                    stroke_width=6, stroke_fill=(0, 0, 0, 235))
            x += w + 12
        else:
            _, im, _, w, h, _ = p
            strip.alpha_composite(im, (x, base + (max_h - h) // 2))
            x += w + 12
    return strip

def colored_line(segments, canvas_w, fill):
    tmp = Image.new("RGBA", (10, 10)); d = ImageDraw.Draw(tmp)
    parts, total_w, max_h = [], 0, 0
    for kind, val, meta in segments:
        if kind == "t":
            bb = d.textbbox((0, 0), val, font=meta, stroke_width=5)
            parts.append(("t", val, meta, bb[2] - bb[0], bb[3] - bb[1], bb[1])); total_w += bb[2] - bb[0] + 10; max_h = max(max_h, bb[3] - bb[1])
        else:
            im = emoji_img(val, meta); parts.append(("e", im, None, im.width, im.height, 0)); total_w += im.width + 10; max_h = max(max_h, im.height)
    total_w -= 10
    strip = Image.new("RGBA", (canvas_w, max_h + 20), (0, 0, 0, 0)); sd = ImageDraw.Draw(strip)
    x = (canvas_w - total_w) // 2; base = 10
    for p in parts:
        if p[0] == "t":
            _, val, font, w, h, oy = p
            sd.text((x, base - oy), val, font=font, fill=fill, stroke_width=5, stroke_fill=(0, 0, 0, 230)); x += w + 10
        else:
            _, im, _, w, h, _ = p; strip.alpha_composite(im, (x, base + (max_h - h) // 2)); x += w + 10
    return strip

work = tempfile.mkdtemp(prefix="polish_")

# ---- 1. POV hook (two centered lines near top) ----
pov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
# soft scrim behind
scrim = Image.new("RGBA", (W, 300), (0, 0, 0, 0))
ImageDraw.Draw(scrim).rounded_rectangle([120, 0, W - 120, 250], radius=40, fill=(0, 0, 0, 120))
pov.alpha_composite(scrim, (0, 150))
l1 = colored_line([("t", _args.pov1, GEO(58))], W, WHITE)
l2 = colored_line([("t", _args.pov2, GEO(58)), ("e", "🥺", 70)], W, WHITE)
pov.alpha_composite(l1, (0, 185)); pov.alpha_composite(l2, (0, 262))
pov.save(f"{work}/pov.png")

# ---- 2. persistent watermark: gold wordmark + handle, top-left, subtle ----
wm = Image.new("RGBA", (W, H), (0, 0, 0, 0)); wd = ImageDraw.Draw(wm)
wd.text((48, 60), "Aashiqana", font=GEO(46), fill=(240, 200, 120, 210), stroke_width=3, stroke_fill=(0, 0, 0, 140))
wd.text((50, 118), HANDLE, font=GEOI(32), fill=(255, 255, 255, 180), stroke_width=2, stroke_fill=(0, 0, 0, 140))
wm.save(f"{work}/wm.png")

# ---- 3. wait-for-it tease (pill, upper-mid dead zone) ----
wfi = Image.new("RGBA", (W, H), (0, 0, 0, 0))
pill = colored_line([("t", "wait for it ", GEO(52)), ("e", "🥹", 60)], W, (255, 235, 190, 255))
# small dark pill behind
pb = Image.new("RGBA", (W, 130), (0, 0, 0, 0))
ImageDraw.Draw(pb).rounded_rectangle([330, 0, W - 330, 110], radius=55, fill=(0, 0, 0, 110))
wfi.alpha_composite(pb, (0, 1120)); wfi.alpha_composite(pill, (0, 1138))
wfi.save(f"{work}/wfi.png")

# ---- 4. PREMIUM end card (last ~2.6s): cinematic scrim + drawn gold monogram
#         + Playfair wordmark + hairline + small-caps CTA + handle ----
import math
PLAYFAIR = F(["remotion-studio/public/fonts/PlayfairDisplay-Italic.ttf"], 1) and \
           "remotion-studio/public/fonts/PlayfairDisplay-Italic.ttf"
DIDOT = "/System/Library/Fonts/Supplemental/Didot.ttc"
GOLD2 = (231, 195, 126, 255)
GOLD_SOFT = (206, 176, 128, 235)
cx = W // 2

def spaced(text, tracking):
    return (" " * tracking).join(list(text))

end = Image.new("RGBA", (W, H), (0, 0, 0, 0))
# radial cinematic scrim: darkest at card center, feathered to edges (couple stays faintly visible)
scr = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sp = scr.load()
ccx, ccy, rmax = W / 2, 1020, 1150
for yy in range(0, H, 2):
    for xx in range(0, W, 2):
        dist = math.hypot(xx - ccx, yy - ccy) / rmax
        a = int(max(0, 232 - dist * 210))            # 232 center -> ~22 edge
        if a > 0:
            sp[xx, yy] = (6, 8, 14, a)
            if xx + 1 < W: sp[xx + 1, yy] = (6, 8, 14, a)
            if yy + 1 < H: sp[xx, yy + 1] = (6, 8, 14, a)
            if xx + 1 < W and yy + 1 < H: sp[xx + 1, yy + 1] = (6, 8, 14, a)
end.alpha_composite(scr)

ed = ImageDraw.Draw(end)
# monogram: thin gold ring + serif A
ring_y = 560; r = 118
for w in range(3):                                    # crisp thin double ring
    ed.ellipse([cx - r + w, ring_y - r + w, cx + r - w, ring_y + r - w], outline=(231, 195, 126, 255 - w * 40))
ed.ellipse([cx - r - 10, ring_y - r - 10, cx + r + 10, ring_y + r + 10], outline=(231, 195, 126, 90))
aA = F([DIDOT], 150)
bb = ed.textbbox((0, 0), "A", font=aA); ed.text((cx - (bb[2] - bb[0]) / 2 - bb[0], ring_y - (bb[3] - bb[1]) / 2 - bb[1]), "A", font=aA, fill=GOLD2)

# wordmark (Playfair italic), letter-spaced
wm_f = F([PLAYFAIR, DIDOT], 96)
word = "Aashiqana"
bb = ed.textbbox((0, 0), word, font=wm_f); wx = cx - (bb[2] - bb[0]) / 2 - bb[0]
ed.text((wx, 730), word, font=wm_f, fill=GOLD2, stroke_width=2, stroke_fill=(0, 0, 0, 120))

# hairline divider
ed.line([(cx - 150, 858), (cx + 150, 858)], fill=(231, 195, 126, 210), width=2)
ed.ellipse([cx - 4, 854, cx + 4, 862], fill=(231, 195, 126, 230))

# small-caps tagline
tag_f = F([DIDOT], 30)
tg = spaced("ORIGINAL AI LOVE SONGS", 1)
bb = ed.textbbox((0, 0), tg, font=tag_f); ed.text((cx - (bb[2] - bb[0]) / 2 - bb[0], 888), tg, font=tag_f, fill=GOLD_SOFT)

# CTA: music note + USE THIS SOUND (small caps)
cta = colored_line([("t", spaced("USE THIS SOUND", 1), GEO(44))], W, GOLD2)
end.alpha_composite(cta, (0, 968))
# handle
hf = GEOI(38)
bb = ed.textbbox((0, 0), HANDLE, font=hf); ed.text((cx - (bb[2] - bb[0]) / 2 - bb[0], 1044), HANDLE, font=hf, fill=(255, 255, 255, 220), stroke_width=1, stroke_fill=(0, 0, 0, 140))
# weekly tagline (italic)
wk_f = F([PLAYFAIR, "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"], 40)
wk = "a new love song every week"
bb = ed.textbbox((0, 0), wk, font=wk_f); ed.text((cx - (bb[2] - bb[0]) / 2 - bb[0], 1112), wk, font=wk_f, fill=(235, 225, 210, 220))
end.save(f"{work}/end.png")

# ---- ffmpeg overlay chain ----
# timings (video ~22s)
fc = (
    "[0:v][1:v]overlay=0:0:enable='between(t,0,3.2)'[a];"
    "[a][2:v]overlay=0:0[b];"                                   # watermark persistent
    "[b][3:v]overlay=0:0:enable='between(t,9.3,12.4)'[c];"
    "[4:v]format=rgba,fade=t=in:st=19.2:d=0.7:alpha=1[end];"    # premium end card fades in
    "[c][end]overlay=0:0:enable='gte(t,19.2)'[v]"
)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", SRC,
    "-i", f"{work}/pov.png", "-i", f"{work}/wm.png", "-i", f"{work}/wfi.png",
    "-loop", "1", "-t", "23", "-i", f"{work}/end.png",
    "-filter_complex", fc, "-map", "[v]", "-map", "0:a",
    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy",
    "-movflags", "+faststart", OUT], check=True)
d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", OUT],
                   capture_output=True, text=True).stdout.strip()
print(">> DONE", OUT, d, "s")
