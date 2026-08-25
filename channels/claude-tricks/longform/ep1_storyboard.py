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

# v2 (2026-08-25): Leonardo NB2 champagne host set (host_set_review.jpg picks)
LEO = os.path.join(CH, "assets", "character", "host_library", "longform_champagne_v1")
HOST = {
    "wide":    os.path.join(LEO, "using-the-reference-image-keep-the-e_1f1a0752_0.jpg"),
    "medium":  os.path.join(LEO, "using-the-reference-image-keep-the-e_1f1a0755_1.jpg"),
    "close":   os.path.join(LEO, "using-the-reference-image-keep-the-e_1f1a0756_1.jpg"),
    "profile": os.path.join(LEO, "using-the-reference-image-keep-the-e_1f1a0757_0.jpg"),
}


def leo_host(shot):
    im = Image.open(HOST[shot]).convert("RGB")
    return im.resize((W, H), Image.LANCZOS)


def leo_pip():
    """Circular PiP cropped from the champagne close-up (replaces magenta Sol crop)."""
    src = Image.open(HOST["close"]).convert("RGB")
    s = src.height
    face_cx = int(src.width * 0.42)
    box = (max(0, face_cx - s // 2), 0, min(src.width, face_cx + s // 2), s)
    sq = src.crop(box).resize((lf.PIP_D, lf.PIP_D), Image.LANCZOS)
    ring = 8
    D = lf.PIP_D + ring * 2
    canvas = Image.new("RGBA", (D, D), (0, 0, 0, 0))
    mask = Image.new("L", (lf.PIP_D, lf.PIP_D), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, lf.PIP_D, lf.PIP_D], fill=255)
    d = ImageDraw.Draw(canvas)
    d.ellipse([0, 0, D, D], fill=lf.ACCENT + (255,))
    canvas.paste(sq, (ring, ring), mask)
    return canvas
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
    pip = leo_pip()
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



ICON = "/Users/vijenderpanda/missnomeetings/artwork/icon-original-rounded.jpeg"


def appstore_listing_still():
    """Option-A cold-open frame: App-Store-style product page built from the REAL app
    icon. PLACEHOLDER CHROME — production MUST swap in a screen capture of the real
    listing (honesty rule: proof beats are real tape)."""
    im = Image.new("RGB", (W, H), (16, 16, 18))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([360, 60, W - 360, H - 60], radius=28, fill=(28, 28, 30))
    try:
        icon = Image.open(ICON).convert("RGB").resize((190, 190), Image.LANCZOS)
        m = Image.new("L", (190, 190), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, 190, 190], radius=42, fill=255)
        im.paste(icon, (420, 130), m)
    except Exception:
        d.rounded_rectangle([420, 130, 610, 320], radius=42, fill=(240, 150, 40))
    f_big = ImageFont.truetype(lf.FONT_ANTON, 64)
    f_sm = ImageFont.truetype(lf.FONT_ANTON, 34)
    d.text((650, 150), "MissNoMeetings", font=f_big, fill=(245, 245, 247))
    d.text((650, 235), "Never miss a meeting again", font=f_sm, fill=(160, 160, 166))
    d.rounded_rectangle([650, 290, 810, 344], radius=27, fill=(0, 122, 255))
    d.text((694, 300), "GET", font=f_sm, fill=(255, 255, 255))
    # real app screenshots in the three slots (VJ: nothing blank in the listing)
    shots = [os.path.join(CH, "assets", "longform_ep1", f"shot_{n}.png")
             for n in ("home", "list", "detail")]
    for i, sp in enumerate(shots):
        x = 420 + i * 350
        try:
            sc = Image.open(sp).convert("RGB")
            sc = sc.resize((320, round(320 * sc.height / sc.width)), Image.LANCZOS).crop((0, 0, 320, 580))
            m = Image.new("L", (320, 580), 0)
            ImageDraw.Draw(m).rounded_rectangle([0, 0, 320, 580], radius=24, fill=255)
            im.paste(sc, (x, 400), m)
        except Exception:
            d.rounded_rectangle([x, 400, x + 320, 980], radius=24, outline=(70, 70, 76), width=2, fill=(20, 20, 24))
        d.rounded_rectangle([x, 400, x + 320, 980], radius=24, outline=(70, 70, 76), width=2)
    d.text((430, 990), "[chrome is mock — swap for real listing capture at production]", font=f_sm, fill=(228, 197, 107))
    return im


def timestamp_card():
    """Beat 2: the unbelievable number, as receipts."""
    im = Image.new("RGB", (W, H), lf.INK)
    d = ImageDraw.Draw(im)
    f_ts = ImageFont.truetype(lf.FONT_ANTON, 76)
    f_big = ImageFont.truetype(lf.FONT_ANTON, 150)
    f_sm = ImageFont.truetype(lf.FONT_ANTON, 40)
    d.text((330, 300), "3:04 PM  prompt sent", font=f_ts, fill=(210, 215, 222))
    d.text((330, 430), "6:12 PM  submitted to Apple", font=f_ts, fill=(210, 215, 222))
    t = "3H 08M"
    tw2 = d.textlength(t, font=f_big)
    d.text(((W - tw2) / 2, 620), t, font=f_big, fill=lf.ACCENT)
    d.text((330, 850), "[timestamps TBD — pull the REAL ones from the session log before render]",
           font=f_sm, fill=(228, 197, 107))
    return im


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    # sim phone sits right-of-frame in the tape (1920x1200 conformed -> ~same x band)
    PHONE = (1150, 60, 400, 960)
    CLAUDE_PANE = (60, 80, 900, 900)

    beats = [
        # (timecode, mode label, VO line, image)
        ("0:00", "COLD-OPEN A1 — the listing, silent",
         "(no VO for 2s — just the listing scrolling) ...That's a real app, on the real App Store.",
         appstore_listing_still()),
        ("0:08", "COLD-OPEN A2 — the receipts",
         "Now look at the timestamps. Prompt sent 3:04. Submitted to Apple 6:12. Three hours, eight minutes.",
         timestamp_card()),
        ("0:20", "COLD-OPEN A3 — the promise (LEO wide)",
         "By the end of this video you'll know every step — because I'm going to show you all of it, including what broke.",
         leo_host("wide")),
        ("0:45", "PROMISE — the app itself (punch-in)",
         "One afternoon, one tool, zero lines of code written by me. Here's the app it built.",
         with_pip(lf.punch_in_frame(demo_frame(12.5), PHONE, zoom=1.0))),
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
        ("8:30", "MID-ROLL — host stakes (LEO medium)",
         "Why is this suddenly possible? Agentic coding. The model doesn't suggest code — it builds, runs, and fixes.",
         leo_host("medium")),
        ("9:00", "CHAPTER CARD", "—", chapter(4, "The App Store")),
        ("9:05", "B-ROLL — host at monitor (LEO profile)",
         "(music swell, no VO — breathing room before the submit sequence)",
         leo_host("profile")),
        ("9:10", "SCREEN+PIP — archive & submit",
         "Signing, archive, App Store Connect, the review questions — the parts every tutorial skips. Here's each one.",
         with_pip(demo_frame(8.0))),
        ("12:30", "CUTAWAY — pop text", "—", pop("APPROVED", "review time: under a day")),
        ("13:00", "PAYOFF — the exact prompt",
         "Here is the exact prompt I started from — pause and copy it. Change one line and it's YOUR app.",
         with_pip(lf.highlight_rect(demo_frame(0.5), (120, 180, 820, 320)))),
        ("14:30", "OUTRO — host + tease (LEO close)",
         "Next episode: I replace my entire paid creator stack with free AI. Subscribe so you don't miss the ship.",
         leo_host("close")),
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
