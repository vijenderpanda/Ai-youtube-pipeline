#!/usr/bin/env python3
"""Self-contained vertical short generator -- zero external API spend.

Built for the V6 end-to-end pipeline test (job c1cb04d5, channel `_v6e2e`), which
arrived with a placeholder brief and no channel row, so nothing paid could be
justified. Everything here is local: Pillow for baked-text frames, macOS `say`
for the voice, ffmpeg for motion + mux.

House style per docs/PRODUCTION-PLAYBOOK.md:
  section 4 -- Anton, magenta/yellow hot words, punch-in on cuts, chips in dead space
  section 5 -- frame zero is the de-facto Shorts thumbnail, so the cover card is designed as one

Beat text is baked into the still (the Poly baked-text approach) rather than
overlaid as caption cards, so there is exactly one text layer on screen.

Usage: python3 scripts/make_v6e2e_short.py [--out DIR]
"""

import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO = Path(__file__).resolve().parent.parent
FONT = REPO / "remotion-studio" / "public" / "fonts" / "Anton.ttf"

W, H = 1080, 1920
FPS = 30
VOICE = "Samantha"
SAY_RATE = 168          # words/min -- followable, not max-speed (AI Unpacked pacing note)
GAP_S = 0.45            # breath between lines
LEAD_S = 0.20           # beat frame lands slightly before its voice
COVER_S = 2.4

MAGENTA = (224, 33, 138)
YELLOW = (255, 212, 0)
EXTRUDE = (60, 10, 40)
INK = (255, 255, 255)

# (headline lines, spoken line, hot-word index into headline lines)
BEATS = [
    (["NO BRIEF", "ON FILE"], "This one arrived with no brief.", 0),
    (["NO CHANNEL", "EITHER"], "And no channel behind it.", 0),
    (["SO WE TEST", "THE PIPE"], "So we test the pipeline instead.", 1),
    (["COVER CARD", "IS FRAME ZERO"], "The cover card is frame zero.", 1),
    (["TEXT BAKED", "INTO THE STILL"], "Text is baked into the still.", 0),
    (["PUNCH IN", "ON EVERY CUT"], "Punch in on every cut.", 0),
    (["RENDERED", "LOCAL"], "Rendered local. Zero API spend.", 1),
    (["V6", "END TO END"], "V six. End to end. Green.", 0),
]

COVER = {
    "title1": "V6 PIPELINE",
    "title2": "END TO END",
    "chip": "RENDER TEST",
    "sub": "no brief · no channel · zero spend",
    "pill": "24-SEC PROOF ▶",
}


def run(cmd, **kw):
    proc = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if proc.returncode != 0:
        sys.exit(f"FAILED: {' '.join(str(c) for c in cmd)}\n{proc.stdout}\n{proc.stderr}")
    return proc


def probe_dur(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=nw=1:nk=1", str(path)]).stdout.strip()
    return float(out)


def font(size):
    return ImageFont.truetype(str(FONT), size)


def fit_font(text, max_w, start, floor=40):
    """Largest Anton size at which `text` fits inside max_w."""
    size = start
    while size > floor:
        f = font(size)
        if f.getbbox(text)[2] - f.getbbox(text)[0] <= max_w:
            return f
        size -= 4
    return font(floor)


def backdrop(seed):
    """Dark magenta field with a drifting glow + vignette + grain."""
    base = Image.new("RGB", (W, H), (14, 4, 12))
    glow = Image.new("RGB", (W, H), (14, 4, 12))
    gd = ImageDraw.Draw(glow)
    cx = W * (0.32 + 0.36 * ((seed * 0.37) % 1.0))
    cy = H * (0.26 + 0.44 * ((seed * 0.61) % 1.0))
    for i in range(46, 0, -1):
        r = i * 30
        k = 1.0 - i / 46.0
        gd.ellipse([cx - r, cy - r * 1.15, cx + r, cy + r * 1.15],
                   fill=(int(14 + 96 * k), int(4 + 14 * k), int(12 + 62 * k)))
    glow = glow.filter(ImageFilter.GaussianBlur(90))
    base = Image.blend(base, glow, 0.92)

    # vignette
    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse([-W * 0.35, -H * 0.14, W * 1.35, H * 1.14], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(210))
    base = Image.composite(base, Image.new("RGB", (W, H), (6, 2, 6)), vig)

    # fine grain so flat gradients don't band on YouTube's encoder
    grain = Image.effect_noise((W, H), 7).convert("RGB")
    return Image.blend(base, grain, 0.045)


def draw_extruded(img, text, f, cx, cy, fill, slant=-3.0, depth=13):
    """Anton with a deep-magenta extrude, slanted -- the locked poster look."""
    bb = f.getbbox(text)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pad = depth + 60
    layer = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ox, oy = pad - bb[0], pad - bb[1]
    for d in range(depth, 0, -1):
        ld.text((ox + d, oy + d), text, font=f, fill=EXTRUDE + (255,))
    ld.text((ox, oy), text, font=f, fill=fill + (255,))
    layer = layer.rotate(slant, resample=Image.BICUBIC, expand=True)
    img.paste(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)), layer)


def chip(img, text, cx, cy, bg, fg, size=44, slant=-3.0):
    f = font(size)
    bb = f.getbbox(text)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    px, py = 30, 20
    layer = Image.new("RGBA", (tw + px * 2, th + py * 2), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle([0, 0, layer.width - 1, layer.height - 1], radius=14, fill=bg + (255,))
    ld.text((px - bb[0], py - bb[1]), text, font=f, fill=fg + (255,))
    layer = layer.rotate(slant, resample=Image.BICUBIC, expand=True)
    img.paste(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)), layer)


def watermark(img):
    f = font(30)
    d = ImageDraw.Draw(img, "RGBA")
    d.text((W - 46, H - 62), "AI FACTORY", font=f, fill=(255, 255, 255, 96), anchor="rs")


def make_cover(path):
    img = backdrop(1)
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 0, W, H], fill=(30, 4, 24, 60))

    f1 = fit_font(COVER["title1"], W - 150, 168)
    f2 = fit_font(COVER["title2"], W - 150, 168)
    draw_extruded(img, COVER["title1"], f1, W / 2, H * 0.335, INK)
    draw_extruded(img, COVER["title2"], f2, W / 2, H * 0.455, INK)
    chip(img, COVER["chip"], W / 2, H * 0.565, YELLOW, (26, 6, 20), size=58)

    fs = ImageFont.truetype(str(FONT), 40)
    d.text((W / 2, H * 0.645), COVER["sub"], font=fs, fill=(255, 255, 255, 200), anchor="ms")
    chip(img, COVER["pill"], W / 2, H * 0.735, MAGENTA, INK, size=46, slant=0)

    watermark(img)
    img.save(path, quality=95)


def make_beat(path, idx, lines, hot):
    img = backdrop(idx + 2)
    # progress chip lives top-right dead space -- never over the taught line
    chip(img, f"{idx + 1}/{len(BEATS)}", W - 132, 150, MAGENTA, INK, size=42, slant=0)

    n = len(lines)
    total_h = 0
    fonts = []
    for ln in lines:
        f = fit_font(ln, W - 140, 150)
        fonts.append(f)
        bb = f.getbbox(ln)
        total_h += (bb[3] - bb[1]) + 34
    y = H / 2 - total_h / 2
    for i, (ln, f) in enumerate(zip(lines, fonts)):
        bb = f.getbbox(ln)
        h = bb[3] - bb[1]
        colour = YELLOW if i == hot else INK
        draw_extruded(img, ln, f, W / 2, y + h / 2, colour,
                      slant=-3.0 if i % 2 == 0 else -1.6)
        y += h + 34

    watermark(img)
    img.save(path, quality=95)


def say_line(text, wav):
    aiff = wav.with_suffix(".aiff")
    run(["say", "-v", VOICE, "-r", str(SAY_RATE), "-o", str(aiff), text])
    run(["ffmpeg", "-y", "-v", "error", "-i", str(aiff),
         "-ac", "1", "-ar", "48000",
         # lift + tame the system voice so it sits like a real VO bed
         "-af", "highpass=f=90,acompressor=threshold=0.12:ratio=3:attack=12:release=180,"
                "volume=3dB,alimiter=limit=0.89",
         str(wav)])
    aiff.unlink()
    return probe_dur(wav)


def kenburns(still, out, dur_s, zoom_in, fade_in=0.0, fade_out=0.0):
    """Punch-in (or settle-out) Ken Burns. 2x supersample keeps zoompan smooth.

    Fades are applied PER CLIP, never across the concatenated timeline: a
    `fade=t=out` holds black for every frame past its window, so a global
    fade-out followed by a global fade-in feeds black into the fade-in and the
    rest of the video stays black. (Cost one render cycle to learn.)
    """
    frames = max(2, int(round(dur_s * FPS)))
    if zoom_in:
        z = "min(1.0+0.0009*on,1.09)"
    else:
        z = "max(1.09-0.0011*on,1.0)"
    vf = (f"scale={W*2}:{H*2},"
          f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":d={frames}:s={W*2}x{H*2}:fps={FPS},"
          f"scale={W}:{H}:flags=lanczos")
    if fade_in > 0:
        vf += f",fade=t=in:st=0:d={fade_in}"
    if fade_out > 0:
        vf += f",fade=t=out:st={max(0.0, dur_s - fade_out):.3f}:d={fade_out}"
    vf += ",format=yuv420p"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(still), "-vf", vf,
         "-frames:v", str(frames), "-c:v", "libx264", "-preset", "slow",
         "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(FPS), str(out)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "renders_out" / "v6e2e"))
    args = ap.parse_args()

    if not FONT.exists():
        sys.exit(f"missing font: {FONT}")
    for tool in ("ffmpeg", "ffprobe", "say"):
        if not shutil.which(tool):
            sys.exit(f"missing tool: {tool}")

    out = Path(args.out)
    work = out / "work"
    work.mkdir(parents=True, exist_ok=True)

    # ---- 1. voice first: line durations drive every beat length
    print("[1/4] voicing lines")
    durs = []
    wavs = []
    for i, (_, spoken, _) in enumerate(BEATS):
        wav = work / f"vo{i:02d}.wav"
        durs.append(say_line(spoken, wav))
        wavs.append(wav)
        print(f"      {i+1}. {durs[-1]:.2f}s  {spoken}")

    beat_durs = [d + GAP_S for d in durs]

    # ---- 2. frames
    print("[2/4] baking frames")
    cover_png = out / "cover.png"
    make_cover(cover_png)
    beat_pngs = []
    for i, (lines, _, hot) in enumerate(BEATS):
        p = work / f"beat{i:02d}.png"
        make_beat(p, i, lines, hot)
        beat_pngs.append(p)

    # ---- 3. motion
    print("[3/4] rendering motion")
    clips = []
    cover_mp4 = work / "clip_cover.mp4"
    kenburns(cover_png, cover_mp4, COVER_S, zoom_in=True)
    clips.append(cover_mp4)
    for i, png in enumerate(beat_pngs):
        c = work / f"clip{i:02d}.mp4"
        kenburns(png, c, beat_durs[i], zoom_in=(i % 2 == 1))
        clips.append(c)

    concat_txt = work / "concat.txt"
    concat_txt.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
    silent = work / "silent.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", str(concat_txt), "-c", "copy", str(silent)])

    # cover dissolves into beat 1 (playbook section 5)
    faded = work / "faded.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(silent),
         "-vf", f"fade=t=in:st=0:d=0.35,fade=t=out:st={COVER_S-0.30}:d=0.30,"
                f"fade=t=in:st={COVER_S}:d=0.30",
         "-c:v", "libx264", "-preset", "slow", "-crf", "17",
         "-pix_fmt", "yuv420p", "-r", str(FPS), str(faded)])

    # ---- 4. audio timeline + mux
    print("[4/4] building audio + mux")
    total = COVER_S + sum(beat_durs)
    parts = []
    lead = work / "lead.wav"
    run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
         "-i", f"anullsrc=r=48000:cl=mono", "-t", f"{COVER_S + LEAD_S:.3f}", str(lead)])
    parts.append(lead)
    for i, wav in enumerate(wavs):
        parts.append(wav)
        if i < len(wavs) - 1:
            gap = work / f"gap{i:02d}.wav"
            run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                 "-i", "anullsrc=r=48000:cl=mono", "-t", f"{GAP_S:.3f}", str(gap)])
            parts.append(gap)

    alist = work / "audio.txt"
    alist.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    vo = work / "vo.wav"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", str(alist), "-af", f"apad,atrim=0:{total:.3f}",
         "-ac", "1", "-ar", "48000", str(vo)])

    final = out / "v6e2e_short.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(faded), "-i", str(vo),
         "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-movflags", "+faststart", "-shortest", str(final)])

    meta = {
        "video": str(final),
        "cover": str(cover_png),
        "duration_s": round(probe_dur(final), 2),
        "beats": [{"lines": b[0], "vo": b[1], "vo_s": round(d, 2)}
                  for b, d in zip(BEATS, durs)],
    }
    (out / "build.json").write_text(json.dumps(meta, indent=2))
    print(f"\nwrote {final}  ({meta['duration_s']}s)")
    print(f"wrote {cover_png}")


if __name__ == "__main__":
    main()
