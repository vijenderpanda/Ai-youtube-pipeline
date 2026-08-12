#!/usr/bin/env python3
"""build_ep01.py — assemble the host-less cinematic Short for "Already Happening" Ep01.

Pipeline (no avatar): Leonardo cinematic stills -> Ken Burns motion -> baked
kinetic text in dead space -> concat -> film grain + vignette -> VO + ducked
music bed, mastered to -14 LUFS. 1080x1920 @30fps.
"""
import json, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
AST = os.path.join(HERE, "assets", "ep01")
VO = os.path.join(HERE, "renders", "ep01", "vo")
OUT = os.path.join(HERE, "renders", "ep01")
TMP = tempfile.mkdtemp(prefix="ah_ep01_")
W, H, FPS = 1080, 1920, 30
ACCENT = (0x22, 0xD3, 0xEE)          # electric teal
MUSIC = os.path.join(HERE, "..", "claude-tricks", "assets", "music", "bed_active.mp3")

def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

def dur_of(words_json):
    w = json.load(open(words_json))
    return (w[-1]["end"] if w else 2.0)

# ---- beats: image, vo stem, text lines, accent-line index, dead-space pos, KB dir
BEATS = [
    dict(img="cinematic-pov-shot-from-inside-a-car_1f1954a6_0.jpg", vo="beat1",
         lines=["NO ONE", "IS DRIVING"], accent=[1], pos="lower", kb="in-up"),
    dict(img="ordinary-daytime-city-street-an-ever_1f1954a9_0.jpg", vo="beat2",
         lines=["NOT A DEMO.", "A TUESDAY."], accent=[1], pos="upper", kb="in-left"),
    dict(img="wide-cinematic-establishing-shot-of-_1f1954ab_0.jpg", vo="beat3",
         lines=["TODAY"], accent=[0], pos="lower", kb="in-right"),
    dict(img="near-future-city-street-at-golden-ho_1f1954ac_0.jpg", vo="beat4",
         lines=["+5 YEARS"], accent=[0], pos="upper", kb="in-up"),
    dict(img="a-former-asphalt-parking-lot-transfo_1f1954ac_0.jpg", vo="beat5",
         lines=["1/3 OF THE CITY", "WAS PARKING"], accent=[0], pos="lower", kb="in-left"),
    dict(img="cinematic-close-up-pov-of-a-human-ha_1f1954ad_0.jpg", vo="beat6",
         lines=["WOULD YOU GIVE UP", "THE WHEEL?", "yes  /  no"], accent=[2], pos="cl", kb="in-down"),
]
TAIL = 0.45   # breath after each VO line
GAP = 0.45    # silence between VO lines (matches TAIL so audio tracks video cuts)

# ---------- fonts ----------
def font(size, bold=True):
    for p in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else
              "/System/Library/Fonts/Supplemental/Arial.ttf",
              "/System/Library/Fonts/HelveticaNeue.ttc"]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: pass
    return ImageFont.load_default()

def draw_tracked(d, xy, text, fnt, fill, track, anchor_center_x):
    """Draw uppercase text with letter-spacing; xy is (center_x, top_y)."""
    widths = [d.textlength(c, font=fnt) + track for c in text]
    total = sum(widths) - track
    x = anchor_center_x - total / 2
    y = xy[1]
    for c, wch in zip(text, widths):
        d.text((x, y), c, font=fnt, fill=fill)
        x += wch

def text_png(beat, idx):
    """Full-frame transparent PNG with the kinetic text baked in dead space."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lines = beat["lines"]; accent_idx = set(beat["accent"])
    big = font(96); small = font(58)
    track = 6
    # vertical anchor by dead-space position
    pos = beat["pos"]
    line_h = 118
    block_h = line_h * len(lines)
    if pos == "upper":   top = int(H * 0.16)
    elif pos == "cl":    top = int(H * 0.60)
    else:                top = int(H * 0.66)   # lower
    # subtle gradient scrim behind text for legibility (soft, not a box)
    scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scrim)
    pad = 60
    sd.rectangle([0, top - pad, W, top + block_h + pad], fill=(6, 8, 12, 96))
    scrim = scrim.filter_blur() if hasattr(scrim, "filter_blur") else scrim
    im = Image.alpha_composite(im, scrim)
    d = ImageDraw.Draw(im)
    y = top
    for i, ln in enumerate(lines):
        is_last_small = (beat["pos"] == "cl" and i == len(lines) - 1)
        fnt = small if is_last_small else big
        fill = (ACCENT + (255,)) if i in accent_idx else (245, 248, 250, 255)
        # drop shadow
        draw_tracked(d, (W // 2, y + 4), ln, fnt, (0, 0, 0, 170), track, W // 2 + 3)
        draw_tracked(d, (W // 2, y), ln, fnt, fill, track, W // 2)
        y += (72 if is_last_small else line_h)
    # small teal ticker bar under the block for brand signature
    d.rectangle([W // 2 - 46, y + 14, W // 2 + 46, y + 20], fill=ACCENT + (255,))
    p = os.path.join(TMP, f"txt_{idx}.png"); im.save(p)
    return p

def prep_image(src, idx):
    """Cover-crop to 1.5x final for Ken Burns headroom."""
    tw, th = int(W * 1.5), int(H * 1.5)
    im = Image.open(src).convert("RGB")
    sw, sh = im.size
    scale = max(tw / sw, th / sh)
    im = im.resize((int(sw * scale), int(sh * scale)), Image.LANCZOS)
    x = (im.size[0] - tw) // 2; y = (im.size[1] - th) // 2
    im = im.crop((x, y, x + tw, y + th))
    p = os.path.join(TMP, f"prep_{idx}.png"); im.save(p)
    return p

def ken_burns(img, dur, kb, out):
    frames = max(1, int(round(dur * FPS)))
    z = "min(1.0+0.0006*on,1.12)"
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    if "up" in kb:    cy = "ih/2-(ih/zoom/2)-0.35*on"
    if "down" in kb:  cy = "ih/2-(ih/zoom/2)+0.35*on"
    if "left" in kb:  cx = "iw/2-(iw/zoom/2)-0.35*on"
    if "right" in kb: cx = "iw/2-(iw/zoom/2)+0.35*on"
    zp = f"zoompan=z='{z}':x='{cx}':y='{cy}':d={frames}:s={W}x{H}:fps={FPS}"
    run(["ffmpeg", "-y", "-loop", "1", "-i", img, "-vf", zp, "-t", str(dur),
         "-r", str(FPS), "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-pix_fmt", "yuv420p", out])

def overlay_text(bg, png, dur, out):
    # text fades in over 0.4s starting at 0.25s, holds
    fc = ("[1:v]format=rgba,fade=t=in:st=0.25:d=0.45:alpha=1[t];"
          "[0:v][t]overlay=0:0[v]")
    run(["ffmpeg", "-y", "-i", bg, "-loop", "1", "-i", png,
         "-filter_complex", fc, "-map", "[v]", "-t", str(dur),
         "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-pix_fmt", "yuv420p", out])

def main():
    os.makedirs(OUT, exist_ok=True)
    seg_files, vo_parts, durs = [], [], []
    for i, b in enumerate(BEATS):
        wj = os.path.join(VO, b["vo"] + ".words.json")
        d = dur_of(wj) + TAIL
        durs.append(d)
        prepped = prep_image(os.path.join(AST, b["img"]), i)
        bg = os.path.join(TMP, f"bg_{i}.mp4"); ken_burns(prepped, d, b["kb"], bg)
        tpng = text_png(b, i)
        seg = os.path.join(TMP, f"seg_{i}.mp4"); overlay_text(bg, tpng, d, seg)
        seg_files.append(seg)
        vo_parts.append(os.path.join(VO, b["vo"] + ".wav"))
    # concat video segments (hard cuts)
    listf = os.path.join(TMP, "segs.txt")
    open(listf, "w").write("".join(f"file '{s}'\n" for s in seg_files))
    concat = os.path.join(TMP, "concat.mp4")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listf,
         "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", concat])
    # global cinematic grade: subtle film grain + vignette
    graded = os.path.join(TMP, "graded.mp4")
    run(["ffmpeg", "-y", "-i", concat, "-vf",
         "noise=alls=7:allf=t,vignette=PI/5",
         "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", graded])
    # build VO track: voN + GAP silence, concatenated to track segment cuts
    sil = os.path.join(TMP, "sil.wav")
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
         "-t", str(GAP), "-c:a", "pcm_s16le", sil])
    aparts = []
    for p in vo_parts:
        aparts.append(p); aparts.append(sil)
    alist = os.path.join(TMP, "vo.txt")
    open(alist, "w").write("".join(f"file '{p}'\n" for p in aparts))
    vofull = os.path.join(TMP, "vo_full.wav")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", alist,
         "-c:a", "pcm_s16le", vofull])
    # mux VO + ducked music, master to -14 LUFS
    out = os.path.join(OUT, "ep01_v1.mp4")
    fc = ("[1:a]volume=6dB[v0];"
          "[2:a]volume=-20dB[m];"
          "[v0][m]amix=inputs=2:duration=first:normalize=0,"
          "loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    run(["ffmpeg", "-y", "-i", graded, "-i", vofull, "-stream_loop", "-1", "-i", MUSIC,
         "-filter_complex", fc, "-map", "0:v", "-map", "[a]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out])
    total = sum(durs) + GAP * len(durs)
    print(f"OK -> {out}  (~{total:.1f}s)")

if __name__ == "__main__":
    main()
