#!/usr/bin/env python3
"""
Animated terminal renderer for AI Unpacked b-roll.

Renders a scripted terminal session (typing + output reveal) as an MP4:
dark editorial window, mono font, syntax-ish colors, blinking cursor.
Reusable across episodes: feed it a "cast" = list of steps.

Cast step types:
  {"type":"type",  "text":"> refactor auth", "color":"white", "cps":18}   typed char-by-char
  {"type":"out",   "lines":[["Here's my plan:","white"],...], "lps":8}    lines revealed one per 1/lps s
  {"type":"pause", "dur":1.0}                                             hold frame
  {"type":"badge", "text":"⏸ plan mode on", "color":"green"}              instant status line

Usage:
  python3 scripts/term_anim.py --cast ep01_cast.json --out clip.mp4 \
      [--w 1080 --h 1920 --fps 30 --title "claude-code — ~/project"]
Cast JSON: {"title": "...", "steps": [...]}
"""
import argparse, json, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

INK = (14, 14, 20); PANEL = (22, 22, 30); HEAD = (30, 30, 42)
COLORS = {"white": (238, 240, 245), "dim": (140, 146, 160), "green": (80, 220, 140),
          "magenta": (224, 33, 138), "red": (255, 120, 120), "blue": (150, 200, 255),
          "yellow": (240, 200, 100)}

def mono(size):
    for p in ["/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Monaco.ttf"]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: pass
    return ImageFont.load_default()

class Term:
    """Terminal state -> frame renderer."""
    def __init__(self, W, H, title, fsize=34, lh=52):
        self.W, self.H, self.title = W, H, title
        self.f = mono(fsize); self.lh = lh
        self.mx, self.my = 60, 320                  # window position
        self.mw, self.mh = W - 120, H - 640
        self.tx, self.ty = self.mx + 40, self.my + 120
        self.max_lines = (self.mh - 160) // lh
        self.lines = []                              # [(text, colorname)]

    def frame(self, cursor=True):
        im = Image.new("RGB", (self.W, self.H), INK)
        d = ImageDraw.Draw(im)
        for i in range(0, self.H, 4):
            d.line([(0, i), (self.W, i)], fill=(18, 18, 26), width=1)
        x, y, w, h = self.mx, self.my, self.mw, self.mh
        d.rounded_rectangle([x, y, x+w, y+h], radius=28, fill=PANEL, outline=(44, 46, 60), width=2)
        d.rounded_rectangle([x, y, x+w, y+74], radius=28, fill=HEAD)
        d.rectangle([x, y+46, x+w, y+74], fill=HEAD)
        for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            d.ellipse([x+30+i*34, y+30, x+48+i*34, y+48], fill=c)
        d.text((x+150, y+26), self.title, font=mono(26), fill=COLORS["dim"])
        vis = self.lines[-self.max_lines:]
        for i, (t, c) in enumerate(vis):
            d.text((self.tx, self.ty + i*self.lh), t, font=self.f, fill=COLORS.get(c, COLORS["white"]))
        if cursor and vis:
            t, c = vis[-1]
            cw = d.textlength(t, font=self.f)
            cy = self.ty + (len(vis)-1)*self.lh
            d.rectangle([self.tx+cw+8, cy+6, self.tx+cw+26, cy+self.lh-10], fill=COLORS["magenta"])
        return im

def render(cast, W, H, fps, out):
    term = Term(W, H, cast.get("title", "claude-code — ~/project"))
    tmp = tempfile.mkdtemp(prefix="term_"); n = 0
    def emit(im, copies=1):
        nonlocal n
        p = os.path.join(tmp, f"f_{n:05d}.png"); im.save(p); n += 1
        for _ in range(copies-1):
            q = os.path.join(tmp, f"f_{n:05d}.png")
            os.link(p, q); n += 1
    for step in cast["steps"]:
        k = step["type"]
        if k == "type":
            cps = step.get("cps", 18); col = step.get("color", "white")
            term.lines.append(("", col))
            per = max(1, round(fps / cps))
            for i in range(1, len(step["text"]) + 1):
                term.lines[-1] = (step["text"][:i], col)
                emit(term.frame(), per)
        elif k == "out":
            lps = step.get("lps", 8); per = max(1, round(fps / lps))
            for t, c in step["lines"]:
                term.lines.append((t, c)); emit(term.frame(cursor=False), per)
        elif k == "badge":
            term.lines.append((step["text"], step.get("color", "green")))
            emit(term.frame(cursor=False), 2)
        elif k == "pause":
            emit(term.frame(), int(step.get("dur", 1.0) * fps))
    run = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps),
           "-i", os.path.join(tmp, "f_%05d.png"),
           "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", out]
    subprocess.run(run, check=True)
    print(f">> {out}  ({n} frames, {n/fps:.1f}s)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cast", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--w", type=int, default=1080); ap.add_argument("--h", type=int, default=1920)
    ap.add_argument("--fps", type=int, default=30)
    a = ap.parse_args()
    render(json.load(open(a.cast)), a.w, a.h, a.fps, a.out)
