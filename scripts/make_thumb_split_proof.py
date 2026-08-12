#!/usr/bin/env python3
"""
make_thumb_split_proof.py — a BEFORE/AFTER split thumbnail cut from two real
frames of the episode's own tape.

Why this exists: the channel's other thumb makers (make_thumb_unpacked.py et al)
build a host-photo + headline card. A fail->fix episode sells on the CONTRAST
itself — the unusable answer beside the usable one — and that contrast only reads
if both halves are the actual filmed frames, not a mock. So this takes the two
in-points straight off the tape, desaturates the "before" so the eye lands on the
"after", and drops one accent chip on the seam.

  python3 scripts/make_thumb_split_proof.py \
      --clip channels/claude-tricks/assets/ep32/table_demo.mp4 \
      --left-t 16.0 --right-t 44.0 --chip TABLE \
      --out channels/claude-tricks/renders/thumb_ep32.jpg

Ships 1280x720 (the channel's banked-thumb size, cf. thumb_ep31.jpg).
"""
import argparse, os, subprocess, sys, tempfile

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANTON = os.path.join(REPO, "remotion-studio", "public", "fonts", "Anton.ttf")
MAG, INK, PAPER = "#E0218A", "#100C16", "#F7F8FC"


def grab(clip, t):
    fd, png = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", clip,
                    "-frames:v", "1", "-y", png], check=True)
    im = Image.open(png).convert("RGB")
    os.unlink(png)
    return im


def pane(im, w, h, top_frac=0.0):
    """Cover-fit `im` into w x h, anchored `top_frac` down its height.

    The tape is a 9:16 phone-shaped chat column, so a centred crop into a
    landscape half throws away the answer and keeps whitespace. Anchoring lets
    each side show the part that carries its argument.
    """
    s = max(w / im.width, h / im.height)
    nw, nh = int(im.width * s + 0.5), int(im.height * s + 0.5)
    im = im.resize((nw, nh), Image.LANCZOS)
    y = int((nh - h) * top_frac)
    return im.crop((max(0, (nw - w) // 2), max(0, min(y, nh - h)),
                    max(0, (nw - w) // 2) + w, max(0, min(y, nh - h)) + h))


def fit(text, box_w, start=96, lo=30):
    size = start
    while size > lo:
        f = ImageFont.truetype(ANTON, size)
        if f.getbbox(text)[2] - f.getbbox(text)[0] <= box_w:
            return f
        size -= 2
    return ImageFont.truetype(ANTON, lo)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clip", required=True)
    ap.add_argument("--left-t", type=float, required=True, help="before frame (s)")
    ap.add_argument("--right-t", type=float, required=True, help="after frame (s)")
    ap.add_argument("--left-top", type=float, default=0.30)
    ap.add_argument("--right-top", type=float, default=0.30)
    ap.add_argument("--chip", default="TABLE")
    ap.add_argument("--left-label", default="WALL OF TEXT")
    ap.add_argument("--right-label", default="ONE TABLE")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    W, H = 1280, 720
    HALF = W // 2
    card = Image.new("RGB", (W, H), INK)

    left = pane(grab(a.clip, a.left_t), HALF, H, a.left_top)
    # the "before" is drained of colour and darkened: it is the thing the viewer
    # is being told NOT to accept, so it must lose the contrast fight on purpose.
    left = ImageEnhance.Color(left).enhance(0.0)
    left = ImageEnhance.Brightness(left).enhance(0.62)
    card.paste(left, (0, 0))

    right = pane(grab(a.clip, a.right_t), HALF, H, a.right_top)
    right = ImageEnhance.Contrast(right).enhance(1.12)
    card.paste(right, (HALF, 0))

    d = ImageDraw.Draw(card, "RGBA")
    # legibility scrims behind each label band
    d.rectangle([0, H - 132, W, H], fill=(10, 8, 16, 205))
    # the seam
    d.rectangle([HALF - 4, 0, HALF + 3, H], fill=MAG)

    lf = fit(a.left_label, HALF - 60, 62)
    rf = fit(a.right_label, HALF - 60, 62)
    d.text((30, H - 100), a.left_label, font=lf, fill="#9AA0AC")
    d.text((HALF + 30, H - 100), a.right_label, font=rf, fill=PAPER)

    # accent chip, centred on the seam so it reads as the hinge between the two
    cf = fit(a.chip, 420, 104)
    tb = d.textbbox((0, 0), a.chip, font=cf)
    cw, ch = tb[2] - tb[0], tb[3] - tb[1]
    px, py = 34, 20
    bx0, by0 = (W - (cw + px * 2)) // 2, 54
    d.rounded_rectangle([bx0, by0, bx0 + cw + px * 2, by0 + ch + py * 2],
                        radius=20, fill=MAG)
    d.text((bx0 + px - tb[0], by0 + py - tb[1]), a.chip, font=cf, fill=PAPER)

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    card.save(a.out, quality=92)
    print(f">> thumb {a.out} {card.size}")


if __name__ == "__main__":
    sys.exit(main())
