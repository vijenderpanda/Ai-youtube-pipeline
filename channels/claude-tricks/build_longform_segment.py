#!/usr/bin/env python3
"""
build_longform_segment.py — 16:9 LONG-FORM segment renderer (VERSIONED template).

LONGFORM-PLAN.md §6: the critical build after the assemble spine. Renders ONE segment
(one tip / one news item) at native 1920x1080 with the landscape beat grammar, so N of
these feed assemble_longform.py into a full long-form. This is the horizontal counterpart
to build_ep_v2.py — a SEPARATE script (VJ 2026-08-16) that we VERSION until the template
locks; do not fold it back into the Shorts builder.

Landscape beat grammar (v1 — two modes, the tutorial-video staples):
  - host_full  : Sol fills the 16:9 frame (cover-crop the wide still), slow push, dark
                 vignette, magenta lower-third title. The setup / to-camera lines.
  - screen_pip : the real-screen proof fills the frame, Sol rides in a bottom-right rounded
                 PiP with a magenta ring (the classic "webcam over screenshare"). The demo.
Captions: karaoke (white -> magenta active word) burned from an ElevenLabs .words.json,
same word-level source the Shorts use, resized for 16:9.

v1 SCOPE: proves the LAYOUT, not the final assets. Host = the committed Sol still
(assets/character/host_library/outfit_11_sol_magenta/) held with a slow push — the same
frozen-host degrade §13 already uses when no lip-synced clip exists; a real HeyGen landscape
clip drops into the same slot later. Screen = a drawn placeholder unless --screen is given,
so the grammar can be eyeballed with zero T5 restore / zero HeyGen spend.

Usage (v1 prototype — one segment from ep11's real word-timings):
  python3 channels/claude-tricks/build_longform_segment.py \
      --words channels/claude-tricks/assets/ep11/vo_v2.words.json \
      --title "1. Switch models in one click" \
      --out channels/claude-tricks/renders/longform/seg_proto.mp4

  # with real assets once the template locks:
  #   --host-clip <landscape HeyGen mp4>  --screen <real screen recording mp4>  --audio <vo.mp3>
"""
import argparse, json, os, shutil, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "scripts"))
from ffmpeg_util import venc
# reuse the Shorts' PROVEN PIL caption system (this ffmpeg build has NO libass — same reason
# assemble_short.py renders captions as PNG overlays instead of an ass/subtitles filter)
from assemble_short import render_caption_pngs, overlay_captions

VERSION = "v3"                          # bump every iteration until the template locks
FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
FFPROBE = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"

W, H, FPS = 1920, 1080, 30
# v3 (VJ 2026-08-25): the LONG-FORM lane has its OWN identity — champagne editorial
# (webapp Obsidian & Champagne tokens), NOT the Shorts magenta. #E91E63 stays Shorts-only.
ACCENT = (228, 197, 107)                # #e4c56b — champagne (webapp --accent)
INK = (12, 15, 20)                      # deep-ink base
FONT_ANTON = os.path.join(REPO, "remotion-studio", "public", "fonts", "Anton.ttf")
SOL_DIR = os.path.join(HERE, "assets", "character", "host_library", "outfit_11_sol_magenta")

# v2: captions ride LOW (long-form band, off the host's face) instead of the mid-frame
# y=0.605 the Shorts use. PiP + lower-third are laid out to clear this band.
CAP_Y = int(H * 0.80)                    # 864 — caption top
PIP_D = 360                              # PiP diameter (square host crop), bottom-right


def run(cmd):
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)


def probe_dur(path):
    out = subprocess.check_output([FFPROBE, "-v", "error", "-show_entries",
                                   "format=duration", "-of",
                                   "default=noprint_wrappers=1:nokey=1", path])
    return float(out.strip())


def font(sz):
    return ImageFont.truetype(FONT_ANTON, sz)


# ---------------------------------------------------------------------------
# Still backdrops (drawn once with PIL, held with a slow push in ffmpeg)
# ---------------------------------------------------------------------------

def regrade_magenta_to_champagne(im):
    """v3: the committed Sol wide still has MAGENTA bokeh (shorts brand) baked in.
    The long-form lane is champagne, so hue-rotate magenta-ish pixels (~270-345deg)
    to gold (~45deg) with a soft mask; skin/wardrobe (other hues) untouched."""
    import numpy as np
    rgb = np.asarray(im).astype(np.float32) / 255.0
    hsv = np.asarray(im.convert("HSV")).astype(np.float32)
    h, s = hsv[..., 0] * 360.0 / 255.0, hsv[..., 1] / 255.0
    mask = ((h > 270) & (h < 345)) & (s > 0.25)
    soft = Image.fromarray((mask * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(6))
    hsv[..., 0][mask] = 45 * 255.0 / 360.0
    hsv[..., 1][mask] *= 0.85
    shifted = Image.fromarray(hsv.astype("uint8"), "HSV").convert("RGB")
    return Image.composite(shifted, im, soft)


def host_full_still(out):
    """Sol wide still cover-cropped to 1920x1080 + dark vignette + magenta lower-third."""
    src = Image.open(os.path.join(SOL_DIR, "wide.jpg")).convert("RGB")
    # cover-fit 1920x1080
    scale = max(W / src.width, H / src.height)
    im = src.resize((round(src.width * scale), round(src.height * scale)), Image.LANCZOS)
    x = (im.width - W) // 2
    y = (im.height - H) // 2
    im = im.crop((x, y, x + W, y + H))
    im = regrade_magenta_to_champagne(im)
    # bottom vignette so captions + title read
    grad = Image.new("L", (1, H), 0)
    for yy in range(H):
        grad.putpixel((0, yy), int(200 * max(0, (yy - H * 0.5) / (H * 0.5)) ** 1.5))
    grad = grad.resize((W, H))
    dark = Image.new("RGB", (W, H), (0, 0, 0))
    im = Image.composite(dark, im, grad)
    im.save(out)


def screen_placeholder_still(out, label="LIVE DEMO"):
    """Dark 16:9 'screen' stand-in — a neutral terminal-ish card. Replaced by a real
    screen recording when --screen is passed. NO vendor logo/lookalike (compliance)."""
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im)
    # window chrome
    d.rounded_rectangle([80, 80, W - 80, H - 80], radius=24, outline=(60, 66, 76), width=2,
                        fill=(18, 22, 28))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([120 + i * 34, 116, 140 + i * 34, 136], fill=c)
    # fake code lines
    fy = 200
    import random
    random.seed(7)
    for _ in range(11):
        w = random.randint(300, 1300)
        col = ACCENT if random.random() < 0.18 else (90, 98, 110)
        d.rounded_rectangle([140, fy, 140 + w, fy + 20], radius=8, fill=col)
        fy += 54
    # label
    f = font(70)
    tw = d.textlength(label, font=f)
    # v3: label sits ABOVE the caption band (CAP_Y=864) — at H-210 it collided with captions
    d.text(((W - tw) / 2, H - 330), label, font=f, fill=(210, 215, 222))
    im.save(out)


def host_pip_png(out):
    """v4: Sol -> CIRCULAR PiP with champagne ring (AI Master grammar), transparent."""
    src = Image.open(os.path.join(SOL_DIR, "center.jpg")).convert("RGB")
    s = min(src.width, src.height)
    src = src.crop(((src.width - s) // 2, 0, (src.width - s) // 2 + s, s))  # top-square (keep face)
    src = src.resize((PIP_D, PIP_D), Image.LANCZOS)
    ring = 8
    D = PIP_D + ring * 2
    canvas = Image.new("RGBA", (D, D), (0, 0, 0, 0))
    mask = Image.new("L", (PIP_D, PIP_D), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, PIP_D, PIP_D], fill=255)
    d = ImageDraw.Draw(canvas)
    d.ellipse([0, 0, D, D], fill=ACCENT + (255,))
    canvas.paste(src, (ring, ring), mask)
    canvas.save(out)


# ---------------------------------------------------------------------------
# v4 — the three AI-Master-grammar tools (VJ 2026-08-25):
#   punch-in choreography, spoken-text highlight, cutaway library
# ---------------------------------------------------------------------------

def punch_in_frame(src_im, rect, zoom=1.0):
    """One 1920x1080 frame at `zoom` in [0..1] between full frame and `rect`
    (x, y, w, h in source px). zoom=0 full frame, zoom=1 tight on rect."""
    sw, sh = src_im.size
    # target crop that shows rect with 8% breathing room, 16:9-corrected
    rx, ry, rw, rh = rect
    rw, rh = rw * 1.16, rh * 1.16
    if rw / rh < 16 / 9: rw = rh * 16 / 9
    else: rh = rw * 9 / 16
    cx, cy = rx + rect[2] / 2, ry + rect[3] / 2
    w = sw + (rw - sw) * zoom
    h = sh + (rh - sh) * zoom
    x = min(max(cx - w / 2, 0), sw - w) if w < sw else 0
    y = min(max(cy - h / 2, 0), sh - h) if h < sh else 0
    return src_im.crop((int(x), int(y), int(x + w), int(y + h))).resize((W, H), Image.LANCZOS)


def render_punch_in(src_video, rect, dur, out, hold=0.6):
    """Production punch-in: ease from full frame into `rect` over `dur` seconds
    (first `hold` seconds full, cubic ease over the next 0.8s, then locked tight).
    Done as per-frame crop expressions in ffmpeg (zoompan jitters at 1080p)."""
    sw, sh = 1920, 1080  # conform first
    rx, ry, rw, rh = rect
    rw, rh = rw * 1.16, rh * 1.16
    if rw / rh < 16 / 9: rw = rh * 16 / 9
    else: rh = rw * 9 / 16
    # a tall rect can 16:9-correct wider than the frame — clamp or the crop is invalid
    if rw > sw: rw, rh = sw, sw * 9 / 16
    if rh > sh: rw, rh = sh * 16 / 9, sh
    cx, cy = rx + rect[2] / 2, ry + rect[3] / 2
    t0, t1 = hold, hold + 0.8
    zmax = sw / rw  # end zoom factor
    ease = f"if(lt(t,{t0}),0,if(gt(t,{t1}),1,pow((t-{t0})/{t1 - t0},3)))"
    z = f"(1+({zmax}-1)*{ease})"
    # ffmpeg crop can't animate w/h — animate SCALE instead, crop a fixed W x H
    # window whose x/y track the (scaled) rect center.
    xexp = f"min(max({cx}*{z}-{W}/2,0),iw-{W})"
    yexp = f"min(max({cy}*{z}-{H}/2,0),ih-{H})"
    vf = (f"scale={sw}:{sh}:force_original_aspect_ratio=decrease,"
          f"pad={sw}:{sh}:(ow-iw)/2:(oh-ih)/2,"
          f"scale=w='trunc({sw}*{z}/2)*2':h='trunc({sh}*{z}/2)*2':eval=frame,"
          f"crop={W}:{H}:x='{xexp}':y='{yexp}',fps={FPS}")
    run([FFMPEG, "-y", "-i", src_video, "-t", str(dur), "-vf", vf,
         *venc("18", "veryfast"), "-pix_fmt", "yuv420p", "-an", out])


def highlight_rect(im, rect, pad=10):
    """Champagne 'spoken text' highlight: translucent fill + 3px ring on rect."""
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    x, y, w, h = rect
    box = [x - pad, y - pad, x + w + pad, y + h + pad]
    d.rounded_rectangle(box, radius=12, fill=ACCENT + (56,), outline=ACCENT + (255,), width=3)
    return Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")


def pop_text_still(text, out, sub=None):
    """Cutaway: huge champagne pop-word on ink (the 'MORE SPECIFIC' beat)."""
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im)
    f = font(170 if len(text) <= 14 else 120)
    tw = d.textlength(text.upper(), font=f)
    d.text(((W - tw) / 2, H * 0.38), text.upper(), font=f, fill=ACCENT)
    if sub:
        fs = font(54)
        sw2 = d.textlength(sub, font=fs)
        d.text(((W - sw2) / 2, H * 0.62), sub, font=fs, fill=(210, 215, 222))
    im.save(out)


def chapter_card_still(idx, title, out):
    """Cutaway: dark chapter card — number tick + one phrase (AI Master grammar)."""
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im)
    d.rectangle([W // 2 - 260, H * 0.30, W // 2 - 246, H * 0.30 + 96], fill=ACCENT)
    d.text((W // 2 - 210, H * 0.30), f"{idx:02d}", font=font(88), fill=ACCENT)
    f = font(110 if len(title) <= 16 else 84)
    tw = d.textlength(title.upper(), font=f)
    d.text(((W - tw) / 2, H * 0.47), title.upper(), font=f, fill=(245, 245, 245))
    im.save(out)


def lower_third_png(out, title):
    """Magenta lower-third title strip, transparent PNG at 1920x1080."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font(64)
    tw = d.textlength(title.upper(), font=f)
    bar_y = 596                                                         # above the low caption band
    d.rectangle([90, bar_y, 90 + 14, bar_y + 92], fill=ACCENT)          # accent tick
    d.text((128, bar_y + 8), title.upper(), font=f, fill=(255, 255, 255))
    im.save(out)


# ---------------------------------------------------------------------------
# Captions — reuse the Shorts' word-by-word PNG karaoke (assemble_short), sized for 16:9
# ---------------------------------------------------------------------------

def overlay_captions_at(video, items, y, out):
    """assemble_short.overlay_captions pins y=0.605*H (mid-frame, right for a Short). Long-form
    wants the low band, so this is the same overlay chain with a caller-set y."""
    if not items:
        os.replace(video, out); return
    inputs = ["-i", video]
    for p, _, _ in items:
        inputs += ["-i", p]
    fc = []; prev = "[0:v]"
    for i, (p, s, e) in enumerate(items):
        lbl = "[v]" if i == len(items) - 1 else f"[t{i}]"
        fc.append(f"{prev}[{i+1}:v]overlay=x=(W-w)/2:y={y}-h/2:enable='between(t,{s},{e})'{lbl}")
        prev = lbl
    run([FFMPEG, "-y"] + inputs + ["-filter_complex", ";".join(fc), "-map", "[v]",
         "-t", str(probe_dur(video)), *venc("18", "veryfast"), "-pix_fmt", "yuv420p", out])


def words_to_captions(words):
    """ElevenLabs {w,start,end} -> assemble_short caption dicts. Hot words (accent colour)
    every 3rd word + any word >=6 chars, the same 'colour is the pop' rhythm the Shorts use."""
    caps = []
    for i, wd in enumerate(words):
        hot = (i % 3 == 2) or len(wd["w"]) >= 6
        caps.append({"w": wd["w"], "start": wd["start"], "end": wd["end"], "hot": hot})
    return caps


# ---------------------------------------------------------------------------
# Beat renders
# ---------------------------------------------------------------------------

def render_beat_host_full(still, dur, out):
    n = int(dur * FPS)
    vf = (f"scale={W*2}:{H*2}:flags=lanczos,"
          f"zoompan=z='min(1.0+0.04*on/{max(n-1,1)},1.04)':d=1:"
          f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},setsar=1,format=yuv420p")
    run([FFMPEG, "-y", "-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", still,
         "-vf", vf, "-frames:v", str(n), *venc("18", "medium"), out])


def render_beat_screen_pip(screen_still, pip_png, dur, out):
    n = int(dur * FPS)
    px = W - PIP_D - 16 - 60          # bottom-right, 60px margin
    py = CAP_Y - (PIP_D + 16) - 24    # sit clearly ABOVE the low caption band
    fc = (f"[0:v]scale={W}:{H},setsar=1,format=yuv420p,"
          f"zoompan=z='min(1.0+0.03*on/{max(n-1,1)},1.03)':d=1:"
          f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS}[bg];"
          f"[bg][1:v]overlay={px}:{py}[out]")
    run([FFMPEG, "-y", "-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", screen_still,
         "-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", pip_png,
         "-filter_complex", fc, "-map", "[out]", "-frames:v", str(n), *venc("18", "medium"), out])


def main():
    ap = argparse.ArgumentParser(description=f"16:9 long-form segment renderer ({VERSION})")
    ap.add_argument("--words", required=True, help="ElevenLabs .words.json (list of {w,start,end})")
    ap.add_argument("--title", default="1. The move", help="lower-third title")
    ap.add_argument("--audio", help="VO mp3/wav; if given it's muxed and drives duration")
    ap.add_argument("--screen", help="real screen-recording mp4 (else a drawn placeholder)")
    ap.add_argument("--host-dir", default=None,
                    help="host still library dir (wide.jpg + center.jpg); default outfit_11_sol_magenta")
    ap.add_argument("--out", required=True)
    ap.add_argument("--crf", default="18")
    args = ap.parse_args()

    if args.host_dir:
        global SOL_DIR
        SOL_DIR = args.host_dir if os.path.isabs(args.host_dir) else os.path.join(REPO, args.host_dir)
        if not os.path.isdir(SOL_DIR):
            sys.exit(f"!! --host-dir not found: {SOL_DIR}")

    words = json.load(open(args.words))
    if not words:
        sys.exit("!! no words")
    total = (probe_dur(args.audio) if args.audio else words[-1]["end"] + 0.6)
    split = total * 0.42               # first ~42% to-camera, rest is the demo
    beatA_words = [w for w in words if w["start"] < split]
    beatB_words = [w for w in words if w["start"] >= split]
    if not beatA_words or not beatB_words:
        beatA_words, beatB_words = words[:len(words)//2], words[len(words)//2:]
        split = beatB_words[0]["start"]

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    tmp = tempfile.mkdtemp(prefix=f"lfseg_{VERSION}_")
    try:
        print(f".. {VERSION}: segment {total:.1f}s  (host_full 0-{split:.1f}s, screen_pip {split:.1f}-{total:.1f}s)")
        # backdrops
        hf = os.path.join(tmp, "host_full.png");     host_full_still(hf)
        sp = os.path.join(tmp, "screen.png");        screen_placeholder_still(sp, args.title.split(".")[-1].strip().upper()[:22] or "LIVE DEMO")
        pip = os.path.join(tmp, "pip.png");          host_pip_png(pip)
        lt = os.path.join(tmp, "lower_third.png");   lower_third_png(lt, args.title)

        # beat clips
        a = os.path.join(tmp, "beatA.mp4"); render_beat_host_full(hf, split, a)
        b = os.path.join(tmp, "beatB.mp4"); render_beat_screen_pip(sp, pip, total - split, b)

        # concat beats (hard cut inside a segment is fine; joins between SEGMENTS get the xfade)
        cat = os.path.join(tmp, "cat.mp4")
        lst = os.path.join(tmp, "list.txt"); open(lst, "w").write(f"file '{a}'\nfile '{b}'\n")
        run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", cat])

        # lower-third TITLE only during the title-in window (first 5s of beat A) so it never
        # shares the frame-bottom with the captions — the v1 collision fix.
        lt_hold = min(5.0, split)
        staged = os.path.join(tmp, "staged.mp4")
        vf = f"[0:v][1:v]overlay=0:0:enable='lt(t,{lt_hold:.3f})'[v]"
        cmd = [FFMPEG, "-y", "-i", cat, "-loop", "1", "-t", f"{lt_hold:.3f}", "-i", lt]
        if args.audio:
            cmd += ["-i", args.audio]
        cmd += ["-filter_complex", vf, "-map", "[v]"]
        if args.audio:
            cmd += ["-map", "2:a", "-c:a", "aac", "-b:a", "192k", "-shortest"]
        cmd += [*venc(args.crf, "medium"), "-pix_fmt", "yuv420p", "-r", str(FPS),
                "-movflags", "+faststart", staged]
        run(cmd)

        # captions: word-by-word PNG karaoke (reused Shorts system), sized for 16:9, low band
        caps = words_to_captions(words)
        items = render_caption_pngs(caps, accent="E4C56B", size=72, tmp=tmp)
        overlay_captions_at(staged, items, CAP_Y, args.out)
        print(f">> DONE ({VERSION}): {args.out}  ({probe_dur(args.out):.2f}s, {W}x{H})")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
