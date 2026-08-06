#!/usr/bin/env python3
"""
Lulla's soft-caption compositor — the calm, bedtime-appropriate opposite of the
punchy Shorts caption style (no heavy outline, no magenta/yellow, no pop-spring).

Two jobs, one primitive:
  1. render a line of text as a transparent full-frame PNG — cream text (#FDF6E3),
     rounded friendly font, a soft blurred shadow for legibility over the dim garden,
     auto-wrapped and auto-fit; and
  2. overlay a timed list of those PNGs onto a video, each gently fading in and out
     (alpha fade — never a hard cut), so lyrics/subtitles appear like a whisper.

Homebrew ffmpeg here has NO libass (see PRODUCTION-PLAYBOOK §3), so captions are
PNG overlays, not burned ASS. This module is that PNG path, tuned soft for Lulla.

Spec JSON (used for lyrics AND bookend text):
  {
    "lines": [
      {"text": "Little light, goodnight",
       "start": 4.0, "end": 9.0,      # seconds in the video
       "pos": "lower",                 # lower | center | upper
       "size": 64, "fade": 0.8}        # px, and fade in/out seconds
    ]
  }

CLI:
  python3 scripts/lulla_captions.py --video renders/song01.mp4 \
      --spec songs/01_lyrics.json --out renders/song01_lyrics.mp4
"""
import argparse, json, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1920, 1080

# Rounded, friendly faces — SF Rounded stands in for Nunito (not installed); the
# brand intent is "rounded, warm, legible" (BRAND-BIBLE §5), which these satisfy.
FONTS = ["/System/Library/Fonts/SFNSRounded.ttf",
         "/System/Library/Fonts/SFCompactRounded.ttf",
         "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"]

CREAM = (253, 246, 227)   # #FDF6E3 moonlight cream (BRAND-BIBLE §4)
AMBER = (255, 198, 110)   # #FFC66E belly-glow amber (accent, e.g. the heart)


def font(size):
    for p in FONTS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _wrap(draw, text, fnt, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def render_line(text, size=64, pos="lower", heart=False, out=None):
    """Full-frame transparent PNG with one soft caption. Returns the path."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fnt = font(size)
    maxw = int(W * 0.82)
    lines = _wrap(d, text, fnt, maxw)
    lh = int(size * 1.28)
    block_h = lh * len(lines)

    if pos == "upper":
        y0 = int(H * 0.16)
    elif pos == "center":
        y0 = (H - block_h) // 2
    else:  # lower third — the default, safe over the garden foreground
        y0 = int(H * 0.74) - block_h // 2

    # Soft blurred shadow layer (legibility over dim scenes without a hard outline).
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(shadow)
    for i, ln in enumerate(lines):
        tw = ds.textlength(ln, font=fnt)
        x = (W - tw) // 2
        ds.text((x, y0 + i * lh), ln, font=fnt, fill=(20, 22, 45, 200))
    shadow = shadow.filter(ImageFilter.GaussianBlur(9))
    img = Image.alpha_composite(img, shadow)

    d = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        tw = d.textlength(ln, font=fnt)
        x = (W - tw) // 2
        d.text((x, y0 + i * lh), ln, font=fnt, fill=CREAM + (255,))

    if heart:  # small amber belly-heart glow above the text (outro goodnight ritual)
        _draw_heart(img, W // 2, y0 - int(size * 0.9), int(size * 0.7))

    out = out or tempfile.mktemp(suffix=".png")
    img.save(out)
    return out


def _draw_heart(img, cx, cy, s):
    """Draw a soft glowing amber heart (Lulla's belly light) centered at (cx, cy)."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r = s // 2
    # two lobes + a triangle bottom
    d.ellipse([cx - r, cy - r // 2, cx, cy + r // 2], fill=AMBER + (255,))
    d.ellipse([cx, cy - r // 2, cx + r, cy + r // 2], fill=AMBER + (255,))
    d.polygon([(cx - r + 2, cy), (cx + r - 2, cy), (cx, cy + r)], fill=AMBER + (255,))
    glow = layer.filter(ImageFilter.GaussianBlur(14))
    img.alpha_composite(glow)
    img.alpha_composite(layer)


def overlay_timed(video, items, out, crf=19, preset="medium"):
    """items: list of (png_path, start, end, fade). Overlay each with an alpha fade."""
    inputs = ["-i", video]
    for png, *_ in items:
        inputs += ["-loop", "1", "-i", png]

    filt = []
    prev = "[0:v]"
    for idx, (png, start, end, fade) in enumerate(items, start=1):
        # Keep the looped PNG on the MAIN clock (no trim/setpts reset) so the alpha
        # fades and the overlay `enable` window share one timeline. Fade at ABSOLUTE
        # timestamps; `enable` gates visibility to [start,end].
        fo = max(start, end - fade)
        filt.append(
            f"[{idx}:v]format=yuva420p,"
            f"fade=t=in:st={start:.3f}:d={fade:.2f}:alpha=1,"
            f"fade=t=out:st={fo:.3f}:d={fade:.2f}:alpha=1[o{idx}]")
        lbl = "[vout]" if idx == len(items) else f"[m{idx}]"
        filt.append(
            f"{prev}[o{idx}]overlay=0:0:enable='between(t,{start:.3f},{end:.3f})'"
            f":eof_action=pass{lbl}")
        prev = lbl

    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", ";".join(filt), "-map", "[vout]"]
    # carry audio through untouched if present
    cmd += ["-map", "0:a?", "-c:a", "copy",
            "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    print("+ overlay", len(items), "captions →", out)
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--spec", required=True, help="lyrics/caption spec JSON")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    spec = json.load(open(a.spec))
    tmp = tempfile.mkdtemp(prefix="lulla_caps_")
    items = []
    for i, ln in enumerate(spec["lines"]):
        png = render_line(ln["text"], ln.get("size", 64), ln.get("pos", "lower"),
                          ln.get("heart", False), os.path.join(tmp, f"c{i:03d}.png"))
        items.append((png, float(ln["start"]), float(ln["end"]), float(ln.get("fade", 0.8))))
    overlay_timed(a.video, items, a.out)
    print(f">> DONE: {a.out}  ({len(items)} soft captions)")


if __name__ == "__main__":
    main()
