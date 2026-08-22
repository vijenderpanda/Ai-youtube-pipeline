#!/usr/bin/env python3
"""cutout_lpa.py — key the plain-cream background off the ep3 cake sequence
renders, producing alpha sprites the film composites directly onto its own
canvas (VJ: "renders with no background works more, but we definitely need
an environment setup in canvas"). Method = the ep1 sprite pipeline: measure
the background from the corner patches per image, key by color distance with
a soft feather, keep the soft contact shadow by treating near-background
darkness as partial alpha.
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

SRC = Path("assets/lpa")
OUT = SRC / "sprites"
OUT.mkdir(exist_ok=True)

NAMES = ["seq_full", "seq_cut1", "seq_cut3", "seq_half", "seq_wedge"]

for name in NAMES:
    p = SRC / f"{name}.png"
    if not p.exists():
        print(f"!! missing {p}"); continue
    im = Image.open(p).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    h, w, _ = a.shape
    # ROW-WISE background estimate: the object is centered, so each row's
    # left/right margins are pure background — this follows the vignette
    # instead of assuming one flat color.
    edges = np.concatenate([a[:, :30, :], a[:, -30:, :]], axis=1)
    bgrow = np.median(edges, axis=1)
    bg = bgrow.mean(axis=0)
    dist = np.sqrt(((a - bgrow[:, None, :]) ** 2).sum(axis=2))
    # soft key: fully bg under lo, fully object over hi
    lo, hi = 14.0, 48.0
    alpha = np.clip((dist - lo) / (hi - lo), 0, 1)
    # no shadow retention: the film draws its own contact shadow, and a
    # kept bg-tinted shadow would haze over the darker desk plate
    am = Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
    rgba = im.convert("RGBA"); rgba.putalpha(am)
    # trim to content bbox with margin
    bbox = am.point(lambda v: 255 if v > 12 else 0).getbbox()
    if bbox:
        m = 14
        bbox = (max(0, bbox[0]-m), max(0, bbox[1]-m), min(w, bbox[2]+m), min(h, bbox[3]+m))
        rgba = rgba.crop(bbox)
    rgba.save(OUT / f"{name}.png")
    print(f">> {name}: {rgba.size}, bg={bg.astype(int).tolist()}")
print("done")
