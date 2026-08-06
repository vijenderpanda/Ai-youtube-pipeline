#!/usr/bin/env python3
"""
Animated outro sting (reusable across episodes): ~3.8s, 1080x1920 @30fps.
"FOR MORE → SUBSCRIBE" pill pops + pulses, "GOT FEEDBACK? COMMENT 💬" slides in,
Sol avatar ring, magenta glow breathing. PIL frames -> ffmpeg (leonardo-free
fallback; swap bg for a Leonardo motion clip later if credits are topped up).
Output: assets/outro/outro_sub_comment.mp4 (+ with music: outro_master.mp4)
"""
import math, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFilter, ImageFont

CH = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(CH, "assets", "outro"); os.makedirs(OUT, exist_ok=True)
W, H, FPS, DUR = 1080, 1920, 30, 3.8
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
    """Letter-spaced text (PIL has no tracking). Anchors on vertical middle;
    center=True centers on x, else x is the left edge. Returns the end x."""
    if center:
        x -= tracked_width(d, text, fnt, tr) / 2
    for c in text:
        d.text((x, y), c, font=fnt, fill=fill, anchor="lm")
        x += d.textlength(c, font=fnt) + tr
    return x

# avatar disc (current host — square head+shoulders crop from the rust outfit)
AV = Image.open(os.path.join(CH, "assets", "channel", "avatar_host_v3.jpg")).convert("RGB")

def ease(t): return 1 - (1 - max(0.0, min(1.0, t)))**3

def frame(t):
    base = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(base)
    for y in range(0, H, 6):
        d.line([(0, y), (W, y)], fill=(18, 18, 26))
    # breathing magenta glow
    breath = 0.5 + 0.5 * math.sin(t * 2.2)
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gr = int(560 + 70 * breath)
    ImageDraw.Draw(glow).ellipse([W//2-gr, H//2-gr-100, W//2+gr, H//2+gr-100],
                                 fill=(int(44+20*breath), 12, int(30+13*breath)))
    glow = glow.filter(ImageFilter.GaussianBlur(200))
    base = Image.blend(base, glow, 0.55)
    d = ImageDraw.Draw(base)

    # avatar disc pops first — thin magenta ring, no chunky frame
    s_av = ease(t / 0.5)
    if s_av > 0.02:
        size = int(336 * s_av)
        av = AV.resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, size, size], fill=255)
        cy = 330
        base.paste(av, (W//2 - size//2, cy - size//2), mask)
        d.ellipse([W//2-size//2-4, cy-size//2-4, W//2+size//2+4, cy+size//2+4],
                  outline=MAG, width=3)

    # ---- SUBSCRIBE: primary CTA, sleek solid pill (soft glow + top sheen) ----
    s_sub = ease((t - 0.6) / 0.45)
    if s_sub > 0.02:
        draw_tracked(d, W//2, 636, "FOR MORE", font(34, "reg"), DIM, 10)
        pulse = 1 + 0.03 * math.sin((t - 1.05) * 5.0) * (1 if t > 1.05 else 0)
        sc = s_sub * pulse
        label, fpill, tr = "SUBSCRIBE", font(52, "bold"), 6
        tw = tracked_width(d, label, fpill, tr)
        ph = int(112 * sc); pw = int((tw + 128) * sc)
        cx, cyp = W//2, 792
        box = [cx-pw//2, cyp-ph//2, cx+pw//2, cyp+ph//2]
        # soft outer glow (replaces the hard 6px ring flash)
        gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(gl).rounded_rectangle([box[0]-8, box[1]-8, box[2]+8, box[3]+8],
                                             radius=ph//2+8, fill=(224, 33, 138, 135))
        gl = gl.filter(ImageFilter.GaussianBlur(28))
        base = Image.alpha_composite(base.convert("RGBA"), gl).convert("RGB")
        d = ImageDraw.Draw(base)
        d.rounded_rectangle(box, radius=ph//2, fill=MAG)
        # top sheen for a soft glossy read
        sheen = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sheen).rounded_rectangle([box[0]+4, box[1]+4, box[2]-4, cyp-2],
                                                radius=ph//2-6, fill=(255, 255, 255, 30))
        base = Image.alpha_composite(base.convert("RGBA"), sheen).convert("RGB")
        d = ImageDraw.Draw(base)
        if s_sub > 0.5:
            draw_tracked(d, cx, cyp, label, fpill, WHITE, tr)

    # ---- COMMENT: secondary CTA, ghost pill (translucent fill + hairline) ----
    s_c = ease((t - 1.6) / 0.5)
    if s_c > 0.02:
        y0 = 1052 + int((1 - s_c) * 36)
        draw_tracked(d, W//2, y0, "GOT FEEDBACK?", font(34, "reg"), DIM, 10)
        label, fc, tr = "COMMENT", font(46, "bold"), 4
        tw = tracked_width(d, label, fc, tr)
        gl_w, gap, ph, padx = 46, 20, 96, 52
        group = tw + gap + gl_w
        pw = int(group + 2 * padx)
        cx, cyc = W//2, y0 + 118
        box = [cx-pw//2, cyc-ph//2, cx+pw//2, cyc+ph//2]
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(ov).rounded_rectangle(box, radius=ph//2,
                                             fill=(255, 214, 10, 20),
                                             outline=(255, 214, 10, 230), width=2)
        base = Image.alpha_composite(base.convert("RGBA"), ov).convert("RGB")
        d = ImageDraw.Draw(base)
        left = cx - group / 2
        endx = draw_tracked(d, left, cyc, label, fc, YELLOW, tr, center=False)
        # slim speech-bubble glyph
        gx, top = endx + gap, cyc - 20
        d.rounded_rectangle([gx, top, gx+gl_w, top+34], radius=9, outline=YELLOW, width=2)
        d.polygon([(gx+11, top+33), (gx+27, top+33), (gx+11, top+47)], fill=YELLOW)
        for k in range(3):
            dx = gx + 12 + k * 10
            d.ellipse([dx, top+15, dx+4, top+19], fill=INK)

    # tagline
    s_t = ease((t - 2.3) / 0.5)
    if s_t > 0.02:
        c = int(120 * s_t + 14)
        draw_tracked(d, W//2, 1470, "one AI skill, every single day",
                     font(40, "reg"), (c, c+6, c+18), 3)
    return base

tmp = tempfile.mkdtemp(prefix="outro_")
n = int(DUR * FPS)
for i in range(n):
    frame(i / FPS).save(os.path.join(tmp, f"f_{i:05d}.png"))

raw = os.path.join(OUT, "outro_sub_comment.mp4")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                "-i", os.path.join(tmp, "f_%05d.png"),
                "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
                "-pix_fmt", "yuv420p", raw], check=True)
print(">>", raw, f"({n} frames, {DUR}s)")
