#!/usr/bin/env python3
"""
style_blurbg.py — "blur-fill" pro framing for DESKTOP-shaped screen recordings.

Fits a non-9:16 recording into a 1080x1920 short with ZERO cropping of the
content (fixes the center-crop complaint that cut the left/right edges):

  * Background : same footage scaled-to-FILL 1080x1920, gaussian blur
                 (sigma 30) and darkened ~40% so it never distracts.
  * Foreground : the FULL recording as a rounded-corner (40px) card with a
                 soft shadow, fit to width 1080 - 2*48 = 984 (or capped by
                 height so caption-safe zones stay clear), vertically centered.
  * Motion     : slow smoothstep-eased punch-in 1.0 -> ~1.10 of the WHOLE
                 composite, biased toward the upper content area. The zoom is
                 auto-capped (numeric search) so the card NEVER leaves the
                 1080x1920 frame — the punch only crops blurred-background
                 reveal. Composite is supersampled 2x before zoompan to avoid
                 integer-pixel jitter.
  * Caption-safe: at zoom 1.0 the top 200px and bottom 300px contain only
                 blurred background (enforced by capping card height).

Choppy GIF/low-fps inputs are normalized to a 30fps frame-HOLD intermediate.
minterpolate was tested and deliberately NOT used: on discrete UI jumps it
ghosts/warps text (verified on claude_demo.gif).

Output spec: 1080x1920, H.264 crf 18, yuv420p, 30fps, no audio.

Usage: python3 scripts/style_blurbg.py INPUT OUTPUT
"""
import math
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFilter

FFMPEG = "/opt/homebrew/bin/ffmpeg"
FFPROBE = "/opt/homebrew/bin/ffprobe"

OUT_W, OUT_H = 1080, 1920
FPS = 30
SIDE_MARGIN = 48          # px each side at zoom 1.0
CORNER_RADIUS = 40        # px rounded corners on the card
TOP_SAFE, BOTTOM_SAFE = 200, 300   # caption-safe zones at zoom 1.0
BLUR_SIGMA = 30           # background gaussian blur
DARKEN = -0.15            # eq brightness (~40% perceived darkening)
ZOOM_TARGET = 1.10        # requested punch; auto-capped for zero content crop
EDGE_GUARD = 6            # min px the card keeps from frame edge at max zoom
SS = 2                    # supersample factor before zoompan (anti-jitter)
SHADOW_PAD = 60           # shadow canvas padding around card
SHADOW_BLUR = 24
SHADOW_ALPHA = 140        # 0-255
SHADOW_OFFSET_Y = 10


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"FAILED: {' '.join(cmd)}\n{r.stderr[-3000:]}")
    return r


def probe(path, entries):
    r = run([FFPROBE, "-v", "error", "-select_streams", "v:0",
             "-show_entries", entries, "-of", "csv=p=0", path])
    return r.stdout.strip().split("\n")[0].split(",")


def fg_rect_at_zoom(z, fg_x0, fg_y0, fg_w, fg_h):
    """Card rect in output coords at zoom z (matches the zoompan expressions:
    crop window centered horizontally, top-quarter biased vertically)."""
    # crop window (in un-supersampled coords): w=OUT_W/z, h=OUT_H/z
    cx = (OUT_W - OUT_W / z) * 0.5          # crop x offset
    cy = (OUT_H - OUT_H / z) * 0.25         # crop y offset (upper bias)
    x0 = (fg_x0 - cx) * z
    y0 = (fg_y0 - cy) * z
    return x0, y0, x0 + fg_w * z, y0 + fg_h * z


def max_safe_zoom(fg_x0, fg_y0, fg_w, fg_h):
    """Largest zoom <= ZOOM_TARGET that keeps the card >= EDGE_GUARD px
    inside the 1080x1920 frame at every zoom level."""
    z = ZOOM_TARGET
    while z > 1.0:
        x0, y0, x1, y1 = fg_rect_at_zoom(z, fg_x0, fg_y0, fg_w, fg_h)
        if (x0 >= EDGE_GUARD and y0 >= EDGE_GUARD
                and x1 <= OUT_W - EDGE_GUARD and y1 <= OUT_H - EDGE_GUARD):
            return round(z, 4)
        z -= 0.0025
    return 1.0


def make_assets(fg_w, fg_h, tmp):
    mask_p = os.path.join(tmp, "mask.png")
    shadow_p = os.path.join(tmp, "shadow.png")
    # rounded-rect alpha mask (white=opaque), rendered 4x for clean AA edges
    s = 4
    m = Image.new("L", (fg_w * s, fg_h * s), 0)
    ImageDraw.Draw(m).rounded_rectangle(
        [0, 0, fg_w * s - 1, fg_h * s - 1], radius=CORNER_RADIUS * s, fill=255)
    m.resize((fg_w, fg_h), Image.LANCZOS).save(mask_p)
    # soft shadow: blurred black rounded rect on transparent canvas
    sw, sh = fg_w + 2 * SHADOW_PAD, fg_h + 2 * SHADOW_PAD
    sh_img = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    ImageDraw.Draw(sh_img).rounded_rectangle(
        [SHADOW_PAD, SHADOW_PAD, SHADOW_PAD + fg_w - 1, SHADOW_PAD + fg_h - 1],
        radius=CORNER_RADIUS, fill=(0, 0, 0, SHADOW_ALPHA))
    sh_img = sh_img.filter(ImageFilter.GaussianBlur(SHADOW_BLUR))
    sh_img.save(shadow_p)
    return mask_p, shadow_p


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: python3 scripts/style_blurbg.py INPUT OUTPUT")
    src, out = sys.argv[1], os.path.abspath(sys.argv[2])
    if not os.path.isfile(src):
        sys.exit(f"input not found: {src}")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        # ---- 1. normalize to clean 30fps frame-hold intermediate (even dims)
        norm = os.path.join(tmp, "norm30.mp4")
        run([FFMPEG, "-y", "-v", "error", "-i", src,
             "-vf", f"fps={FPS},scale=trunc(iw/2)*2:trunc(ih/2)*2:flags=lanczos",
             "-an", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", norm])

        w, h = (int(v) for v in probe(norm, "stream=width,height"))
        nframes = int(probe(norm, "stream=nb_frames")[0])

        # ---- 2. card geometry (full content, no crop)
        fg_w = OUT_W - 2 * SIDE_MARGIN
        fg_h = int(round(h * fg_w / w))
        max_h = OUT_H - 2 * max(TOP_SAFE, BOTTOM_SAFE)  # keeps safe zones clear
        if fg_h > max_h:                                # very tall input: fit by height
            fg_h = max_h
            fg_w = int(round(w * fg_h / h))
        fg_w -= fg_w % 2
        fg_h -= fg_h % 2
        fg_x0 = (OUT_W - fg_w) // 2
        fg_y0 = (OUT_H - fg_h) // 2                     # vertically centered

        zmax = max_safe_zoom(fg_x0, fg_y0, fg_w, fg_h)
        mask_p, shadow_p = make_assets(fg_w, fg_h, tmp)

        # ---- 3. composite + eased punch (supersampled zoompan)
        za = zmax - 1.0
        nf = max(nframes - 1, 1)
        ease = f"pow(min(on/{nf}\\,1)\\,2)*(3-2*min(on/{nf}\\,1))"
        zexpr = f"1+{za:.4f}*{ease}"
        fc = (
            f"[0:v]format=rgba,split=2[bgsrc][fgsrc];"
            f"[bgsrc]scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase:"
            f"flags=lanczos,crop={OUT_W}:{OUT_H},gblur=sigma={BLUR_SIGMA},"
            f"eq=brightness={DARKEN}[bg];"
            f"[fgsrc]scale={fg_w}:{fg_h}:flags=lanczos[fgs];"
            f"[fgs][1:v]alphamerge[card];"
            f"[bg][2:v]overlay={fg_x0 - SHADOW_PAD}:"
            f"{fg_y0 - SHADOW_PAD + SHADOW_OFFSET_Y}[bgsh];"
            f"[bgsh][card]overlay={fg_x0}:{fg_y0}[comp];"
            f"[comp]scale={OUT_W * SS}:{OUT_H * SS}:flags=lanczos,"
            f"zoompan=z='{zexpr}':x='(iw-iw/zoom)*0.5':y='(ih-ih/zoom)*0.25':"
            f"d=1:fps={FPS}:s={OUT_W}x{OUT_H},format=yuv420p[out]"
        )
        run([FFMPEG, "-y", "-v", "error",
             "-i", norm, "-loop", "1", "-i", mask_p, "-loop", "1", "-i", shadow_p,
             "-filter_complex", fc, "-map", "[out]",
             "-frames:v", str(nframes), "-r", str(FPS),
             "-an", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", out])

    print(f"OK {out}  card {fg_w}x{fg_h} at ({fg_x0},{fg_y0})  zoom 1.0->{zmax}")


if __name__ == "__main__":
    main()
