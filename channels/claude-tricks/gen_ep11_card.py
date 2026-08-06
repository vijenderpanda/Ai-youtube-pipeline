#!/usr/bin/env python3
"""Ep11 opening visual: our OWN generic recreation of 'that viral infographic'
(20 secret Claude commands). No logos, no lifted artwork — genre pastiche for
the myth-bust hook. Renders card_20cmds.jpg then a slow Ken Burns mp4 for the
newsSplit top pane."""
import os, subprocess
from PIL import Image, ImageDraw, ImageFont

CH = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(CH, "assets", "ep11")
ANTON = os.path.join(CH, "..", "..", "remotion-studio", "public", "fonts", "Anton.ttf")
MONO = "/System/Library/Fonts/Menlo.ttc"

W = H = 1080
MAG, YEL, INK, WHITE = "#E0218A", "#FFD60A", "#12121A", "#F2F2F8"

img = Image.new("RGB", (W, H), INK)
d = ImageDraw.Draw(img)

# subtle card frame, viral-infographic style
d.rounded_rectangle([28, 28, W - 28, H - 28], radius=36, outline="#2A2A3A", width=4)

f_top = ImageFont.truetype(ANTON, 54)
f_big = ImageFont.truetype(ANTON, 110)
f_cmd = ImageFont.truetype(MONO, 36)
f_bot = ImageFont.truetype(ANTON, 44)

def center(txt, font, y, fill):
    w = d.textlength(txt, font=font)
    d.text(((W - w) / 2, y), txt, font=font, fill=fill)

center("99% OF PEOPLE DON'T KNOW", f_top, 70, WHITE)
center("20 SECRET", f_big, 150, YEL)
center("CLAUDE COMMANDS", f_big, 270, MAG)

cmds = ["/premortem", "/steelman", "/devil", "/brutal",
        "/scout", "/blindspots", "/eli5", "/ghost",
        "/punch", "/10x", "/roast", "/mentor",
        "/skeptic", "/vc", "/coach", "/editor",
        "/critic", "/lawyer", "/prof", "/sensei"]
x0, y0, dx, dy = 130, 455, 440, 51
for i, c in enumerate(cmds):
    x = x0 + (i % 2) * dx
    y = y0 + (i // 2) * dy
    d.text((x, y), c, font=f_cmd, fill=WHITE if i % 3 else YEL)

center("SAVE THIS BEFORE IT'S DELETED", f_bot, H - 100, MAG)

jpg = os.path.join(A, "card_20cmds.jpg")
img.save(jpg, quality=92)
print(">>", jpg)

# Ken Burns: slow push-in, 7s @30fps (only ~3s used in the cut)
mp4 = os.path.join(A, "card_20cmds.mp4")
subprocess.run([
    "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", jpg,
    "-vf", ("scale=2160:2160,zoompan=z='1+0.10*on/210':x='(iw-iw/zoom)/2':"
            "y='(ih-ih/zoom)/2':d=210:s=1080x1080:fps=30"),
    "-t", "7", "-c:v", "libx264", "-pix_fmt", "yuv420p", mp4], check=True)
print(">>", mp4)
