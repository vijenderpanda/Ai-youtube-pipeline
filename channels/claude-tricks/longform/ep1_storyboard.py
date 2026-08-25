#!/usr/bin/env python3
"""
ep1_storyboard.py — LONG-FORM EP1 storyboard ("I Shipped an iPhone App in 3 Hours").

Render-gate artifact (VJ standing rule): one labeled still per beat, tiled into a
storyboard sheet for approval BEFORE any production render. Uses the v4 primitives
from build_longform_segment.py + the real MissNoMeetings demo tape.

Usage:  python3 channels/claude-tricks/longform/ep1_storyboard.py
Output: channels/claude-tricks/renders/longform/ep1_storyboard.jpg
"""
import os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
CH = os.path.dirname(HERE)
sys.path.insert(0, CH)
sys.path.insert(0, os.path.join(os.path.dirname(CH), "..", "scripts"))
import build_longform_segment as lf

DEMO = os.path.join(CH, "assets", "longform_ep1", "mnm_demo.mov")
OUT_DIR = os.path.join(CH, "renders", "longform")
W, H = lf.W, lf.H


def demo_frame(t):
    """Grab one frame from the real tape at t seconds, conformed to 1920x1080."""
    tmp = tempfile.mktemp(suffix=".png")
    subprocess.run([lf.FFMPEG, "-y", "-loglevel", "error", "-ss", str(t), "-i", DEMO,
                    "-frames:v", "1", tmp], check=True)
    im = Image.open(tmp).convert("RGB")
    scale = min(W / im.width, H / im.height)
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H), lf.INK)
    canvas.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
    os.unlink(tmp)
    return canvas


def with_pip(im):
    tmp = tempfile.mktemp(suffix=".png")
    lf.host_pip_png(tmp)
    pip = Image.open(tmp)
    os.unlink(tmp)
    base = im.convert("RGBA")
    base.paste(pip, (W - pip.width - 48, H - pip.height - 64), pip)
    return base.convert("RGB")


def host_still():
    tmp = tempfile.mktemp(suffix=".png")
    lf.host_full_still(tmp)
    im = Image.open(tmp).convert("RGB")
    os.unlink(tmp)
    return im


def still_of(fn, *a):
    tmp = tempfile.mktemp(suffix=".png")
    fn(*a, tmp) if fn is not lf.pop_text_still else None
    im = Image.open(tmp).convert("RGB")
    os.unlink(tmp)
    return im


def pop(text, sub=None):
    tmp = tempfile.mktemp(suffix=".png")
    lf.pop_text_still(text, tmp, sub=sub)
    im = Image.open(tmp).convert("RGB"); os.unlink(tmp); return im


def chapter(idx, title):
    tmp = tempfile.mktemp(suffix=".png")
    lf.chapter_card_still(idx, title, tmp)
    im = Image.open(tmp).convert("RGB"); os.unlink(tmp); return im


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    # sim phone sits right-of-frame in the tape (1920x1200 conformed -> ~same x band)
    PHONE = (1150, 60, 400, 960)
    CLAUDE_PANE = (60, 80, 900, 900)

    beats = [
        # (timecode, mode label, VO line, image)
        ("0:00", "COLD-OPEN — App Store proof",
         "This app is live on the App Store right now. Built in three hours. I didn't write the code.",
         with_pip(lf.punch_in_frame(demo_frame(12.5), PHONE, zoom=1.0))),
        ("0:45", "PROMISE — host",
         "Idea to shipped iPhone app, one afternoon, one tool. I'll show you every step — including the parts that broke.",
         host_still()),
        ("1:20", "CHAPTER CARD", "—", chapter(1, "The Idea")),
        ("1:30", "SCREEN+PIP — the one-prompt spec",
         "MissNoMeetings: my phone buries meeting invites, I miss calls. So I typed the whole app as one prompt.",
         with_pip(demo_frame(1.0))),
        ("3:00", "CHAPTER CARD", "—", chapter(2, "The Build")),
        ("3:10", "PUNCH-IN — Claude Code writes the app",
         "Watch what it does with that prompt — project, Swift files, the timer logic — while I get coffee.",
         with_pip(lf.highlight_rect(lf.punch_in_frame(demo_frame(4.0), CLAUDE_PANE, zoom=0.85), (120, 300, 700, 60)))),
        ("5:30", "CUTAWAY — pop text", "—", pop("3 HOURS", "total. Including the App Store review prep.")),
        ("6:00", "CHAPTER CARD", "—", chapter(3, "On My iPhone")),
        ("6:10", "PUNCH-IN — simulator running",
         "First run in the simulator. The meeting timer, the alerts — working. Then the real test: my actual iPhone.",
         with_pip(lf.punch_in_frame(demo_frame(13.5), PHONE, zoom=0.9))),
        ("8:30", "MID-ROLL — host stakes",
         "Why is this suddenly possible? Agentic coding. The model doesn't suggest code — it builds, runs, and fixes.",
         host_still()),
        ("9:00", "CHAPTER CARD", "—", chapter(4, "The App Store")),
        ("9:10", "SCREEN+PIP — archive & submit",
         "Signing, archive, App Store Connect, the review questions — the parts every tutorial skips. Here's each one.",
         with_pip(demo_frame(8.0))),
        ("12:30", "CUTAWAY — pop text", "—", pop("APPROVED", "review time: under a day")),
        ("13:00", "PAYOFF — the exact prompt",
         "Here is the exact prompt I started from — pause and copy it. Change one line and it's YOUR app.",
         with_pip(lf.highlight_rect(demo_frame(0.5), (120, 180, 820, 320)))),
        ("14:30", "OUTRO — host + tease",
         "Next episode: I replace my entire paid creator stack with free AI. Subscribe so you don't miss the ship.",
         host_still()),
    ]

    # tile: 3 cols, labeled
    cols = 3
    tw = 620
    th = round(tw * 9 / 16)
    label_h = 96
    rows = (len(beats) + cols - 1) // cols
    try:
        f_big = ImageFont.truetype(lf.FONT_ANTON, 26)
        f_sm = ImageFont.truetype(lf.FONT_ANTON, 19)
    except Exception:
        f_big = f_sm = None
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * 16, rows * (th + label_h + 16) + 96), (10, 12, 16))
    d = ImageDraw.Draw(sheet)
    d.text((20, 20), "LONG-FORM EP1 STORYBOARD — 'I Shipped an iPhone App in 3 Hours' (~15 min, champagne v4)",
           font=f_big, fill=(228, 197, 107))
    for i, (tc, mode, vo, im) in enumerate(beats):
        r, c = divmod(i, cols)
        x = 16 + c * (tw + 16)
        y = 72 + r * (th + label_h + 16)
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x, y + th + 8), f"{tc}  {mode}", font=f_big, fill=(228, 197, 107))
        vo_show = vo if len(vo) <= 92 else vo[:89] + "..."
        d.text((x, y + th + 44), vo_show, font=f_sm, fill=(200, 205, 212))
    out = os.path.join(OUT_DIR, "ep1_storyboard.jpg")
    sheet.save(out, quality=88)
    print(">> storyboard:", out, sheet.size)


if __name__ == "__main__":
    main()
