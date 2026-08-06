#!/usr/bin/env python3
"""
style_device.py — "device-in-frame" pro framing renderer.

Presents a screen recording inside a phone-style mockup on a branded dark
background (big-tech app-demo look):

  * 1080x1920 PIL-generated background: near-black #0E0E12 top -> deep tone
    bottom with a subtle accent glow bottom-right + gentle vignette (dithered
    to avoid banding).
  * Recording scaled down, corners rounded, thin #2A2A30 bezel ring, soft
    drop shadow, placed slightly above vertical center.
  * Whole composition gets a slow cinematic push: zoom 1.00 -> 1.05 over the
    full duration. The composite is built at 2x (2160x3840) and zoompan
    samples it down to 1080x1920, so the push is sub-pixel smooth.
  * Caption-safe: the device (incl. bezel) stays out of the top ~200px and
    bottom ~300px for the ENTIRE zoom range — those zones belong to step
    chips / captions and must never cover taught content. This caps the
    device width at ~70% for 9:16 input (the naive 78% would break the safe
    zones), which is the deliberate trade-off.

Usage:
  python3 scripts/style_device.py INPUT OUTPUT [--accent HEX]

Output: 1080x1920, H.264 crf 18, yuv420p, 30 fps, no audio.
"""

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

FFMPEG = "/opt/homebrew/bin/ffmpeg"
FFPROBE = "/opt/homebrew/bin/ffprobe"

OUT_W, OUT_H = 1080, 1920
SS = 2                      # supersample factor for the composite canvas
FPS = 30
ZOOM_MAX = 1.05             # slow push 1.00 -> 1.05 over full duration
TOP_SAFE = 200              # caption-safe zones (1x px) — hard pipeline rule
BOTTOM_SAFE = 300
TARGET_W_FRAC = 0.78        # desired device width (soft; safe zones win)

BG_TOP = (0x0E, 0x0E, 0x12)     # near-black
BG_BOTTOM = (0x13, 0x10, 0x18)  # deep tone with a hint of purple
BEZEL_RGB = (0x2A, 0x2A, 0x30)
BEZEL_PX = 3                    # bezel ring thickness (1x px)


def hex_to_rgb(s: str):
    s = s.lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        raise argparse.ArgumentTypeError(f"bad hex color: {s!r}")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def probe(path: str):
    out = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height:format=duration",
         "-of", "json", path],
        capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    st = data["streams"][0]
    dur = float(data["format"]["duration"])
    return int(st["width"]), int(st["height"]), dur


def even(v: float) -> int:
    return int(round(v / 2.0)) * 2


def rounded_mask(w: int, h: int, r: int, ss: int = 4) -> Image.Image:
    """Anti-aliased rounded-rectangle mask (mode L), drawn supersampled."""
    big = Image.new("L", (w * ss, h * ss), 0)
    d = ImageDraw.Draw(big)
    d.rounded_rectangle([0, 0, w * ss - 1, h * ss - 1], radius=r * ss, fill=255)
    return big.resize((w, h), Image.LANCZOS)


def compute_layout(in_w: int, in_h: int):
    """Device rect at 1x such that safe zones hold even at ZOOM_MAX."""
    cy = OUT_H / 2.0
    # y_static maps to cy + (y - cy) * ZOOM_MAX at full push (centered zoom)
    top_limit = cy - (cy - TOP_SAFE) / ZOOM_MAX            # ~236
    bottom_limit = cy + (OUT_H - BOTTOM_SAFE - cy) / ZOOM_MAX  # ~1588
    band_h = bottom_limit - top_limit - 2 * BEZEL_PX       # bezel stays safe too

    aspect = in_w / in_h
    dev_w = min(TARGET_W_FRAC * OUT_W, band_h * aspect)
    dev_w = even(dev_w)
    dev_h = even(dev_w / aspect)

    x = even((OUT_W - dev_w) / 2.0)
    # pin to the top of the allowed band => "slightly above vertical center"
    y = even(top_limit + BEZEL_PX)
    if y + dev_h + BEZEL_PX > bottom_limit:
        y = even(bottom_limit - BEZEL_PX - dev_h)
    radius = max(24, int(round(56 * dev_w / 843.0)))       # scale spec radius
    return x, y, dev_w, dev_h, radius


def build_background(path: str, dev, accent):
    """2160x3840 background: gradient + glow + vignette + shadow + bezel."""
    W, H = OUT_W * SS, OUT_H * SS
    dx, dy, dw, dh, r = [v * SS for v in dev[:4]] + [dev[4] * SS]

    yy = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None]
    xx = np.linspace(0.0, 1.0, W, dtype=np.float32)[None, :]

    top = np.array(BG_TOP, dtype=np.float32)
    bot = np.array(BG_BOTTOM, dtype=np.float32)
    t = (yy ** 1.15)[..., None]
    img = np.broadcast_to(top * (1.0 - t) + bot * t, (H, W, 3)).astype(np.float32)

    # subtle accent glow, bottom-right (Apple-keynote quiet, not loud)
    gx, gy = 0.84, 0.90
    ar = W / H
    d2 = ((xx - gx) * ar) ** 2 + (yy - gy) ** 2
    glow = np.exp(-d2 / (0.34 ** 2)) * 0.14                # peak 14% blend
    img += glow[..., None] * (np.array(accent, np.float32) - img)

    # very subtle vignette
    vd2 = ((xx - 0.5) * ar) ** 2 + (yy - 0.5) ** 2
    vign = 1.0 - 0.11 * np.clip((np.sqrt(vd2) - 0.45) / 0.55, 0.0, 1.0) ** 2
    img *= vign[..., None]

    # anti-banding: LOW-frequency dither only. Full-res white noise here turns
    # into temporal grain once zoompan sub-pixel-shifts it (x264 at crf 18
    # then balloons to 40+ Mbps). Low-freq noise wiggles the band contours,
    # is invisible as texture, and compresses to almost nothing.
    rng = np.random.default_rng(7)
    small = rng.uniform(-2.2, 2.2, (H // 8, W // 8)).astype(np.float32)
    noise = np.asarray(Image.fromarray(small, mode="F").resize((W, H), Image.BILINEAR))
    img += noise[..., None]
    bg = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")

    # soft drop shadow: blurred dark rounded rect, offset down
    grow, offset, blur = 8 * SS, 26 * SS, 34 * SS
    sh = Image.new("L", (W, H), 0)
    sh.paste(rounded_mask(dw + 2 * grow, dh + 2 * grow, r + grow),
             (dx - grow, dy - grow + offset))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    sh = sh.point(lambda v: int(v * 0.62))                 # soft, not black hole
    bg = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), bg, sh)

    # bezel plate: sits under the video, ring + corner fill show through
    bpx = BEZEL_PX * SS
    plate = rounded_mask(dw + 2 * bpx, dh + 2 * bpx, r + bpx)
    bg.paste(Image.new("RGB", plate.size, BEZEL_RGB), (dx - bpx, dy - bpx), plate)

    bg.save(path)


def main():
    ap = argparse.ArgumentParser(description="Device-in-frame pro framing renderer")
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--accent", type=hex_to_rgb, default="#E91E63",
                    help="accent hex for the background glow (default #E91E63)")
    args = ap.parse_args()

    in_w, in_h, dur = probe(args.input)
    n_frames = max(2, int(round(dur * FPS)))

    dev = compute_layout(in_w, in_h)
    dx, dy, dw, dh, r = dev
    print(f"[style_device] input {in_w}x{in_h} {dur:.2f}s -> device "
          f"{dw}x{dh} at ({dx},{dy}) r={r} | safe zones {TOP_SAFE}/{BOTTOM_SAFE} "
          f"held through zoom {ZOOM_MAX}")

    tmp = tempfile.mkdtemp(prefix="style_device_")
    bg_png = os.path.join(tmp, "bg.png")
    mask_png = os.path.join(tmp, "mask.png")

    build_background(bg_png, dev, args.accent)
    rounded_mask(dw * SS, dh * SS, r * SS).save(mask_png)

    vw, vh = dw * SS, dh * SS
    vx, vy = dx * SS, dy * SS
    dz = ZOOM_MAX - 1.0
    fc = (
        f"[0:v]fps={FPS},scale={vw}:{vh}:flags=lanczos,format=rgba[v];"
        f"[2:v]format=gray[m];"
        f"[v][m]alphamerge[vm];"
        f"[1:v][vm]overlay={vx}:{vy}:format=auto:shortest=1[comp];"
        f"[comp]format=rgb24,"
        f"zoompan=z='min(1+{dz}*on/{n_frames - 1},{ZOOM_MAX})'"
        f":x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2'"
        f":d=1:s={OUT_W}x{OUT_H}:fps={FPS},format=yuv420p[out]"
    )
    cmd = [
        FFMPEG, "-y",
        "-i", args.input,
        "-loop", "1", "-framerate", str(FPS), "-i", bg_png,
        "-loop", "1", "-framerate", str(FPS), "-i", mask_png,
        "-filter_complex", fc,
        "-map", "[out]",
        # hard frame cap: with -loop 1 image inputs, overlay shortest=1 alone
        # does NOT terminate the graph on ffmpeg 8.x -> endless encode
        "-frames:v", str(n_frames),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", str(FPS), "-an",
        "-movflags", "+faststart",
        args.output,
    ]
    print("[style_device] rendering...")
    subprocess.run(cmd, check=True)
    print(f"[style_device] done -> {args.output}")


if __name__ == "__main__":
    main()
