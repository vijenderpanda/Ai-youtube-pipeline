#!/usr/bin/env python3
"""
Ep9 b-roll: stylized animated recreation of the Claude DESKTOP app
(hotkey quick-entry bar, folder drag-in, streaming reply).
Same approach as scripts/term_anim.py — PIL frames -> ffmpeg. Deliberately
stylized in channel ink+magenta (channel ships containsSyntheticMedia=true).

Outputs (1080x1920 @30fps) into assets/ep09b/:
  app_hotkey.mp4   (~5.5s)  desktop -> floating bar pops -> typed prompt
  app_drag.mp4     (~5.5s)  folder glides into app window -> attachment chip
  app_reply.mp4    (~6s)    user bubble -> streaming assistant reply
"""
import math, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFilter, ImageFont

CH = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(CH, "assets", "ep09b"); os.makedirs(OUT, exist_ok=True)
W, H, FPS = 1080, 1920, 30
INK = (14, 14, 20); PANEL = (24, 24, 33); PANEL2 = (32, 32, 44)
WHITE = (238, 240, 245); DIM = (140, 146, 160); MAG = (224, 33, 138)
GREEN = (80, 220, 140); BLUE = (150, 200, 255)

def font(size, mono=False):
    cands = (["/System/Library/Fonts/Menlo.ttc"] if mono else
             ["/System/Library/Fonts/HelveticaNeue.ttc", "/System/Library/Fonts/Helvetica.ttc"])
    for p in cands:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: pass
    return ImageFont.load_default()

F_UI = font(40); F_UI_S = font(34); F_BIG = font(52); F_MONO = font(34, mono=True)

def desktop_bg():
    """dark gradient desktop with subtle glow — generic, no real OS chrome"""
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im)
    for y in range(0, H, 4):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(14+18*t), int(14+10*t), int(20+30*t)))
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(glow).ellipse([W//2-420, H//2-520, W//2+420, H//2+320], fill=(60, 12, 40))
    glow = glow.filter(ImageFilter.GaussianBlur(180))
    return Image.blend(im, glow, 0.5)

def rr(d, box, r, **kw):
    d.rounded_rectangle(box, radius=r, **kw)

def spark(d, cx, cy, s, color=MAG):
    for a in range(8):
        ang = a * math.pi / 4
        d.line([(cx, cy), (cx + s*math.cos(ang), cy + s*math.sin(ang))],
               fill=color, width=6)

def folder_icon(d, x, y, s, label=None):
    rr(d, [x, y+s*0.18, x+s, y+s*0.82], int(s*0.10), fill=(80, 140, 230))
    rr(d, [x, y+s*0.10, x+s*0.45, y+s*0.30], int(s*0.08), fill=(100, 160, 245))
    if label:
        d.text((x+s/2, y+s*0.95), label, font=F_UI_S, fill=WHITE, anchor="ma")

def quick_bar(im, scale=1.0, text="", cursor=True):
    """floating quick-entry bar, centered, pop-scale"""
    bw, bh = int(920*scale), int(150*scale)
    if bw < 10: return im
    bar = Image.new("RGB", (bw, bh), PANEL)
    d = ImageDraw.Draw(bar)
    rr(d, [0, 0, bw-1, bh-1], int(28*scale), fill=PANEL, outline=MAG, width=max(2, int(4*scale)))
    spark(d, int(70*scale), bh//2, int(26*scale))
    tx = int(130*scale)
    if text:
        d.text((tx, bh//2), text, font=F_UI, fill=WHITE, anchor="lm")
        if cursor:
            cw = d.textlength(text, font=F_UI)
            d.rectangle([tx+cw+10, bh//2-26, tx+cw+22, bh//2+26], fill=MAG)
    else:
        d.text((tx, bh//2), "Ask Claude anything…", font=F_UI, fill=DIM, anchor="lm")
    sh = bar.filter(ImageFilter.GaussianBlur(0))
    im.paste(sh, ((W-bw)//2, (H//2 - bh//2 - 200)))
    return im

def hotkey_chip(im, alpha):
    """'⌥ space' key chip bottom center"""
    if alpha <= 0: return im
    chip = Image.new("RGBA", (W, 130), (0, 0, 0, 0))
    d = ImageDraw.Draw(chip)
    label = "opt + space"
    fw = d.textlength(label, font=F_BIG)
    x0 = (W - fw)//2 - 40
    rr(d, [x0, 10, x0+fw+80, 120], 24, fill=(*PANEL2, int(255*alpha)), outline=(*MAG, int(255*alpha)), width=4)
    d.text((W//2, 65), label, font=F_BIG, fill=(*WHITE, int(255*alpha)), anchor="mm")
    im.paste(chip, (0, H-560), chip)
    return im

def app_window(files_chip=False, msgs=None, typing=""):
    """main app window mock (no sidebar), rounded, header dots"""
    im = desktop_bg()
    x0, y0, x1, y1 = 40, 240, W-40, H-240
    d = ImageDraw.Draw(im)
    rr(d, [x0, y0, x1, y1], 36, fill=PANEL)
    for i, c in enumerate([(255, 105, 97), (255, 190, 90), (90, 200, 120)]):
        d.ellipse([x0+36+i*46, y0+34, x0+64+i*46, y0+62], fill=c)
    spark(d, x0+520, y0+48, 18)
    d.text((x0+560, y0+48), "New chat", font=F_UI_S, fill=DIM, anchor="lm")
    d.line([(x0, y0+96), (x1, y0+96)], fill=PANEL2, width=3)
    # input box bottom
    iy0 = y1-190
    rr(d, [x0+30, iy0, x1-30, y1-40], 28, fill=PANEL2)
    if typing:
        d.text((x0+70, iy0+52), typing, font=F_UI, fill=WHITE, anchor="lm")
        cw = d.textlength(typing, font=F_UI)
        d.rectangle([x0+70+cw+10, iy0+28, x0+70+cw+22, iy0+76], fill=MAG)
    elif not files_chip:
        d.text((x0+70, iy0+52), "Ask Claude anything…", font=F_UI, fill=DIM, anchor="lm")
    if files_chip:
        rr(d, [x0+60, iy0-100, x0+660, iy0-16], 22, fill=(40, 40, 56), outline=MAG, width=3)
        folder_icon(d, x0+84, iy0-96, 64)
        d.text((x0+170, iy0-58), "Q3 Reports · 3 files", font=F_UI_S, fill=WHITE, anchor="lm")
    # messages
    yy = y0 + 150
    for who, lines in (msgs or []):
        if who == "u":
            tw = max(d.textlength(t, font=F_UI_S) for t in lines) + 70
            rr(d, [x1-60-tw, yy, x1-60, yy+40+len(lines)*48], 24, fill=(46, 24, 40), outline=MAG, width=2)
            for i, t in enumerate(lines):
                d.text((x1-60-tw+34, yy+22+i*48), t, font=F_UI_S, fill=WHITE, anchor="lm")
            yy += 70 + len(lines)*48
        else:
            for t in lines:
                col = MAG if t.startswith("**") else WHITE
                d.text((x0+70, yy), t.replace("**", ""), font=F_UI_S, fill=col, anchor="lm")
                yy += 54
            yy += 30
    return im

class Clip:
    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix="ep09b_"); self.n = 0
    def emit(self, im, copies=1):
        p = os.path.join(self.tmp, f"f_{self.n:05d}.png"); im.save(p); self.n += 1
        for _ in range(copies-1):
            q = os.path.join(self.tmp, f"f_{self.n:05d}.png"); os.link(p, q); self.n += 1
    def save(self, name):
        out = os.path.join(OUT, name)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                        "-i", os.path.join(self.tmp, "f_%05d.png"),
                        "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
                        "-pix_fmt", "yuv420p", out], check=True)
        print(f">> {out} ({self.n} frames, {self.n/FPS:.1f}s)")

def ease(t):  # ease-out cubic
    return 1 - (1 - t)**3

# ---- clip 1: hotkey summon + typed prompt
def clip_hotkey():
    c = Clip()
    base = desktop_bg()
    c.emit(base, int(0.6*FPS))
    for i in range(int(0.5*FPS)):                       # hotkey chip fades in
        c.emit(hotkey_chip(base.copy(), ease(i/(0.5*FPS))))
    held = hotkey_chip(base.copy(), 1.0)
    c.emit(held, int(0.4*FPS))
    for i in range(int(0.4*FPS)):                       # bar pops
        c.emit(quick_bar(held.copy(), scale=0.2+0.8*ease(i/(0.4*FPS))))
    bar_bg = held
    text = "summarize the Q3 reports"
    per = max(1, round(FPS/16))
    for i in range(1, len(text)+1):                     # typing
        c.emit(quick_bar(bar_bg.copy(), 1.0, text[:i]), per)
    c.emit(quick_bar(bar_bg.copy(), 1.0, text), int(0.8*FPS))
    c.save("app_hotkey.mp4")

# ---- clip 2: folder drag into window
def clip_drag():
    c = Clip()
    win = app_window()
    c.emit(win, int(0.5*FPS))
    sx, sy, tx, ty = 130, H-420, W//2-60, H-560   # path: desktop corner -> input area
    dur = int(1.6*FPS)
    for i in range(dur):
        t = ease(i/dur)
        x = sx + (tx-sx)*t
        y = sy + (ty-sy)*t - 220*math.sin(math.pi*t)   # arc
        fr = win.copy(); d = ImageDraw.Draw(fr)
        folder_icon(d, int(x), int(y), 130, "Q3 Reports")
        c.emit(fr)
    chip = app_window(files_chip=True)
    for i in range(int(0.3*FPS)):                       # drop flash
        fr = chip.copy(); d = ImageDraw.Draw(fr)
        a = 1 - i/(0.3*FPS)
        rr(d, [70, H-430-100, 700, H-430-16], 22, outline=(int(224+(255-224)*a), 33, 138), width=6)
        c.emit(fr)
    c.emit(chip, int(1.6*FPS))
    typ = "what changed vs Q2?"
    per = max(1, round(FPS/16))
    for i in range(1, len(typ)+1):
        c.emit(app_window(files_chip=True, typing=typ[:i]), per)
    c.emit(app_window(files_chip=True, typing=typ), int(0.5*FPS))
    c.save("app_drag.mp4")

# ---- clip 3: streaming reply
def clip_reply():
    c = Clip()
    user = [("u", ["what changed vs Q2?"])]
    c.emit(app_window(msgs=user), int(0.6*FPS))
    reply = ["**Reading 3 files…", "Revenue up 12% — Sales beat target,", "Support renewals steady.",
             "**The big change:", "launch spend moved to Q4,", "so margins look better than they are."]
    shown = []
    for line in reply:
        shown.append(line)
        c.emit(app_window(msgs=user + [("a", list(shown))]), int(0.55*FPS))
    c.emit(app_window(msgs=user + [("a", reply)]), int(1.4*FPS))
    c.save("app_reply.mp4")

clip_hotkey(); clip_drag(); clip_reply()
