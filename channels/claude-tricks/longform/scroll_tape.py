#!/usr/bin/env python3
"""
scroll_tape.py — terminal-styled scrolling tape from REAL text (git log, source files,
session transcripts). Honesty: the pixels are styled, the WORDS are verbatim from the
artifact — this is the ep1 stand-in where no live screen recording of the build exists.

Usage: scroll_tape.py --text <file> --out <mp4> --dur 20 [--title "git log"] [--px 30]
"""
import argparse, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "..", "scripts"))
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 30
INK = (14, 17, 22)
ACCENT = (228, 197, 107)
MONO_CANDIDATES = ["/System/Library/Fonts/SFNSMono.ttf", "/System/Library/Fonts/Menlo.ttc",
                   "/Library/Fonts/SF-Mono-Regular.otf"]


def mono(sz):
    for p in MONO_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                continue
    return ImageFont.load_default()


def build(text_path, out, dur, title, px):
    lines = open(text_path, errors="replace").read().splitlines()
    f = mono(px)
    lh = px + 12
    pad_x, pad_top = 120, 150
    total_h = pad_top + len(lines) * lh + H
    canvas = Image.new("RGB", (W, total_h), INK)
    d = ImageDraw.Draw(canvas)
    # window chrome
    d.rounded_rectangle([60, 50, W - 60, total_h - 30], radius=22, outline=(60, 66, 76),
                        width=2)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([100 + i * 34, 86, 120 + i * 34, 106], fill=c)
    if title:
        d.text((200, 84), title, font=mono(26), fill=(160, 166, 176))
    for i, ln in enumerate(lines):
        st = ln.strip()
        if st.startswith(("commit", "##")):
            col = ACCENT
        elif st.startswith("//"):
            col = (126, 200, 148)
        elif any(k in ln for k in ("+", "insertions", "changed")):
            col = (222, 226, 233)
        elif any(k in ln for k in ("enum", "case", "import", "final", "struct", "func", "var", "let")):
            col = (137, 187, 255)
        else:
            col = (186, 192, 202)
        d.text((pad_x, pad_top + i * lh), ln[:150], font=f, fill=col)
    scroll = max(1, total_h - H)
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "tall.png")
        canvas.save(src)
        vf = (f"crop={W}:{H}:0:y='min({scroll}*t/{dur},{scroll})',fps={FPS},format=yuv420p")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", src,
                        "-t", str(dur), "-vf", vf, "-c:v", "libx264", "-crf", "18",
                        "-preset", "veryfast", "-an", out], check=True)
    print(">>", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dur", type=float, default=20)
    ap.add_argument("--title", default="")
    ap.add_argument("--px", type=int, default=30)
    a = ap.parse_args()
    build(a.text, a.out, a.dur, a.title, a.px)
