#!/usr/bin/env python3
"""
Animated brand INTRO sting (reusable across episodes) — the bookend twin of
gen_outro.py, in the SAME visual language so intro and outro read as one system:
dark ink + scanlines, breathing magenta glow, the circular Sol avatar disc with a
thin magenta ring, HelveticaNeue/Arial tracked type. NOT a new look — it mirrors
the outro (gen_outro.py), only the copy changes (channel name instead of the CTAs).

Kept SHORT on purpose (~1.5s): the retention curves (scripts/yt_retention.py) show
the 0-15s window is the whole ballgame, so a brand sting must not delay the hook —
the episode's hook VO starts underneath it. Output: assets/... -> bookends/intro.mp4
"""
import math, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFilter, ImageFont

CH = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(CH, "bookends"); os.makedirs(OUT, exist_ok=True)
W, H, FPS, DUR = 1080, 1920, 30, 1.5
INK = (14, 14, 20); MAG = (224, 33, 138); WHITE = (238, 240, 245)
DIM = (150, 156, 170); YELLOW = (255, 214, 10)


def font(size, weight="reg"):
    paths = {
        "reg":  ["/System/Library/Fonts/HelveticaNeue.ttc",
                 "/System/Library/Fonts/Supplemental/Arial.ttf"],
        "bold": ["/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                 "/System/Library/Fonts/HelveticaNeue.ttc"],
    }[weight]
    for p in paths:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: pass
    return ImageFont.load_default()


def tracked_width(d, text, fnt, tr):
    return sum(d.textlength(c, font=fnt) for c in text) + tr * (len(text) - 1)


def draw_tracked(d, x, y, text, fnt, fill, tr, center=True):
    if center:
        x -= tracked_width(d, text, fnt, tr) / 2
    for c in text:
        d.text((x, y), c, font=fnt, fill=fill, anchor="lm")
        x += d.textlength(c, font=fnt) + tr
    return x


# same brand disc as the outro, so the two bookends match exactly
AV = Image.open(os.path.join(CH, "assets", "channel", "avatar_host_v3.jpg")).convert("RGB")


def ease(t): return 1 - (1 - max(0.0, min(1.0, t)))**3


def frame(t):
    base = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(base)
    for y in range(0, H, 6):
        d.line([(0, y), (W, y)], fill=(18, 18, 26))
    # breathing magenta glow (same as outro)
    breath = 0.5 + 0.5 * math.sin(t * 2.2)
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gr = int(560 + 70 * breath)
    ImageDraw.Draw(glow).ellipse([W//2-gr, H//2-gr-40, W//2+gr, H//2+gr-40],
                                 fill=(int(44+20*breath), 12, int(30+13*breath)))
    glow = glow.filter(ImageFilter.GaussianBlur(200))
    base = Image.blend(base, glow, 0.55)
    d = ImageDraw.Draw(base)

    # avatar disc pops first — identical treatment to the outro
    s_av = ease(t / 0.45)
    cy = 640
    if s_av > 0.02:
        size = int(300 * s_av)
        av = AV.resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, size, size], fill=255)
        base.paste(av, (W//2 - size//2, cy - size//2), mask)
        d.ellipse([W//2-size//2-4, cy-size//2-4, W//2+size//2+4, cy+size//2+4],
                  outline=MAG, width=3)

    # channel name — tracked bold white with a growing magenta underline
    s_ttl = ease((t - 0.35) / 0.42)
    if s_ttl > 0.02:
        ty = 900 + int((1 - s_ttl) * 22)
        c = int(238 * s_ttl)
        draw_tracked(d, W//2, ty, "AI UNPACKED", font(72, "bold"), (c, c, c), 10)
        bw = int(300 * s_ttl)
        d.rounded_rectangle([W//2-bw//2, ty+52, W//2+bw//2, ty+60], radius=4, fill=MAG)

    # tagline — identical copy + style to the outro's closer
    s_t = ease((t - 0.72) / 0.42)
    if s_t > 0.02:
        c = int(120 * s_t + 14)
        draw_tracked(d, W//2, 1010, "one AI skill, every single day",
                     font(40, "reg"), (c, c+6, c+18), 3)
    return base


if __name__ == "__main__":
    tmp = tempfile.mkdtemp(prefix="intro_")
    n = int(DUR * FPS)
    for i in range(n):
        frame(i / FPS).save(os.path.join(tmp, f"f_{i:05d}.png"))
    raw = os.path.join(OUT, "intro.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                    "-i", os.path.join(tmp, "f_%05d.png"),
                    "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
                    "-pix_fmt", "yuv420p", raw], check=True)
    print(">>", raw, f"({n} frames, {DUR}s)")
