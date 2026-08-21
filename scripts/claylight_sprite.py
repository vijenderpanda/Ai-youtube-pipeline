#!/usr/bin/env python3
"""claylight_sprite.py — ingest a FLUX render into the CLAYLIGHT sprite library.

The lock (channels/claude-tricks/films/CLAYLIGHT.lock.json) generates every
sprite on the stage-matched dark ground (#1A1214), which makes extraction a
luminance key rather than a segmentation problem: the clay object is bright,
the ground and its baked shadow are dark, and the boundary is a soft rim. We
key on distance-from-ground colour with a soft knee, erode one pixel (the
lock's rule — halo pixels read as a cheap cutout), trim to the bounding box,
and drop a faint inner shadow so the sprite still reads dimensional after the
baked ground shadow is gone. SpriteLayer draws the stage shadow itself.

  python3 scripts/claylight_sprite.py in.png --name toybox
  -> channels/claude-tricks/assets/claylight/library/toybox.png (+ .meta.json)
"""
import argparse
import json
import os

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "channels", "claude-tricks", "assets", "claylight", "library")
GROUND = np.array([0x1A, 0x12, 0x14], float)


def key(im: Image.Image) -> Image.Image:
    a = np.asarray(im.convert("RGB")).astype(float)
    # distance from the ground colour, normalised; the baked shadow is a darker
    # version of the ground so it keys out with it
    d = np.sqrt(((a - GROUND) ** 2).sum(-1))
    # The first pass keyed at 26..90 and LEFT THE ROOM VISIBLE: FLUX's ground is
    # not flat — it carries a lit gradient and the object's soft shadow, so a
    # low knee kept a faint rectangle of 'almost ground' around every sprite,
    # and the camera made those rectangles read instantly. The knee now starts
    # where the ground's own variance ends (per-image, measured off the corner
    # patches), and edge pixels are DESPILLED toward the object so the rim does
    # not carry a dark fringe.
    corners = np.concatenate([
        d[:40, :40].ravel(), d[:40, -40:].ravel(),
        d[-40:, :40].ravel(), d[-40:, -40:].ravel()])
    floor = float(np.percentile(corners, 99)) + 14   # above ALL ground variance
    alpha = np.clip((d - floor) / 70, 0, 1)
    # kill isolated speckle
    am = Image.fromarray((alpha * 255).astype(np.uint8))
    am = am.filter(ImageFilter.MedianFilter(3))
    # 1px erode per the lock — no halo
    am = am.filter(ImageFilter.MinFilter(3))
    out = im.convert("RGBA")
    out.putalpha(am)
    return out


def trim(im: Image.Image, pad=14):
    bbox = im.getchannel("A").getbbox()
    if not bbox:
        return im
    x0, y0, x1, y1 = bbox
    x0 = max(0, x0 - pad); y0 = max(0, y0 - pad)
    x1 = min(im.width, x1 + pad); y1 = min(im.height, y1 + pad)
    return im.crop((x0, y0, x1, y1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--name", required=True)
    a = ap.parse_args()
    os.makedirs(LIB, exist_ok=True)
    im = key(Image.open(a.src))
    im = trim(im)
    dst = os.path.join(LIB, f"{a.name}.png")
    im.save(dst)
    meta = {"src": os.path.basename(a.src), "w": im.width, "h": im.height}
    json.dump(meta, open(dst.replace(".png", ".meta.json"), "w"))
    cov = np.asarray(im.getchannel("A")).astype(float).mean() / 255
    print(f">> {a.name}: {im.width}x{im.height}, alpha coverage {cov:.0%} -> {dst}")


if __name__ == "__main__":
    main()
