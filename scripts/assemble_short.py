#!/usr/bin/env python3
"""
Assemble a vertical 1080x1920 YouTube Short for "AI Unpacked" (channel key claude-tricks).

Layers (bottom -> top):
  1. B-roll base track   — images with optional Ken Burns, hard-cut to a timeline.
  2. Avatar cutaways     — host "Sol" overlaid in a corner during given time windows.
                            POC: a still rounded badge PNG.
                            Real pipeline: a green-screen HeyGen clip (set "chroma": true) that
                            gets chroma-keyed before overlay.
  3. Karaoke captions    — one word at a time, big Impact/Anton, white with heavy outline,
                            "hot" (key) words flip to the brand magenta, quick scale-pop.
                            Burned via a generated ASS file.
  4. Audio               — voiceover (drives length) + optional ducked music.

Spec JSON (see channels/claude-tricks/episodes/<ep>.short.json):
{
  "w":1080,"h":1920,"fps":30,"accent":"E0218A",
  "vo":"path/vo.wav", "music":"", "music_gain":0.12,
  "segments":[{"img":"a.png","dur":2.0,"motion":"zoom_in"}, ...],
  "avatar":{"img":"sol_badge.png","corner":"br","size":430,"margin":54,
            "windows":[[0.0,1.6],[13.0,15.0]], "chroma":false, "key":"0x00b140"},
  "captions":[{"w":"THREE","start":0.0,"end":0.30}, {"w":"CHEATING","start":0.9,"end":1.4,"hot":true}, ...]
}

Usage:
  python3 scripts/assemble_short.py --spec channels/claude-tricks/episodes/01.short.json \
      --out channels/claude-tricks/renders/ep01_poc.mp4
"""
import argparse, json, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont
from ffmpeg_util import venc  # GPU (NVENC) encode when available, else libx264

def run(cmd):
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)

def probe_dur(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path])
    return float(out.strip())

# ---------- b-roll base ----------
def ken_burns(img, dur, motion, W, H, FPS, out):
    """Render one still into a WxH clip with optional slow zoom/pan (cover-fit)."""
    frames = max(1, int(dur * FPS))
    ow, oh = int(W * 1.5), int(H * 1.5)          # oversample for zoom room
    base = f"scale={ow}:{oh}:force_original_aspect_ratio=increase,crop={ow}:{oh},setsar=1"
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    if motion == "zoom_in":
        z, x, y = "min(1.0+0.0011*on,1.18)", cx, cy
    elif motion == "zoom_out":
        z, x, y = "if(eq(on,0),1.18,max(1.18-0.0011*on,1.0))", cx, cy
    elif motion == "pan_left":
        z, x, y = "1.12", f"(iw-iw/zoom)*(1-on/{frames})", cy
    elif motion == "pan_right":
        z, x, y = "1.12", f"(iw-iw/zoom)*(on/{frames})", cy
    else:  # none — static cover
        z, x, y = "1.0", cx, cy
    zp = f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS}"
    vf = f"{base},{zp},format=yuv420p"
    run(["ffmpeg", "-y", "-loop", "1", "-i", img, "-vf", vf,
         "-t", str(dur), "-r", str(FPS),
         *venc("18", "veryfast"), "-pix_fmt", "yuv420p", out])

def video_seg(vid, dur, W, H, FPS, out, punch=False):
    """Fit a video segment to WxH and exactly dur seconds (freeze last frame if short).
    punch=True adds a Vaibhav-style punch-in: opens at 1.08x and settles to 1.0 in ~0.3s."""
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0E0E14,"
          f"tpad=stop_mode=clone:stop_duration={dur},fps={FPS}")
    if punch:
        vf += f",zoompan=z='max(1.08-0.01*on,1.0)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS}"
    vf += ",format=yuv420p"
    run(["ffmpeg", "-y", "-i", vid, "-vf", vf, "-t", str(dur), "-an",
         *venc("18", "veryfast"), "-pix_fmt", "yuv420p", out])

def build_base(segments, W, H, FPS, tmp, out):
    clips = []
    for i, s in enumerate(segments):
        c = os.path.join(tmp, f"seg_{i:02d}.mp4")
        if s.get("vid"):
            video_seg(s["vid"], s["dur"], W, H, FPS, c, punch=s.get("punch", False))
        else:
            ken_burns(s["img"], s["dur"], s.get("motion", "none"), W, H, FPS, c)
        clips.append(c)
    if len(clips) == 1:
        run(["ffmpeg", "-y", "-i", clips[0], "-c", "copy", out]); return
    listf = os.path.join(tmp, "concat.txt")
    with open(listf, "w") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listf,
         *venc("18", "veryfast"), "-pix_fmt", "yuv420p", out])

# ---------- avatar overlay ----------
def _circle_masks(size, ring_px, accent, tmp):
    """Solid-circle alpha mask + magenta ring PNG (both size x size)."""
    r = int(accent[0:2], 16); g = int(accent[2:4], 16); b = int(accent[4:6], 16)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([ring_px, ring_px, size - ring_px, size - ring_px], fill=255)
    mp = os.path.join(tmp, f"av_mask_{size}.png"); mask.save(mp)
    ring = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse([ring_px // 2, ring_px // 2, size - ring_px // 2, size - ring_px // 2],
                                 outline=(r, g, b, 255), width=ring_px)
    rp = os.path.join(tmp, f"av_ring_{size}.png"); ring.save(rp)
    return mp, rp

def overlay_video_avatar(base, av, accent, tmp, out):
    """Loop a (square-cropped) idle video in the corner, circle-masked + magenta ring.
    A gentle vertical bob (default on) keeps the host feeling alive."""
    size = av.get("size", 430); m = av.get("margin", 54); corner = av.get("corner", "br")
    xexpr = f"W-w-{m}" if corner in ("br", "tr") else f"{m}"
    ybase = f"H-h-{m}" if corner in ("br", "bl") else f"{m}"
    yexpr = f"{ybase}+9*sin(2*PI*t/2.2)" if av.get("bob", True) else ybase
    windows = av.get("windows", [])
    enable = "+".join(f"between(t,{a},{b})" for a, b in windows) if windows else "1"
    mask, ring = _circle_masks(size, 14, accent, tmp)
    fc = (f"[1:v]crop='min(iw,ih)':'min(iw,ih)',scale={size}:{size},format=rgba[sq];"
          f"[2:v]format=gray[mk];[sq][mk]alphamerge[cir];"
          f"[cir][3:v]overlay=0:0:format=auto[av];"
          f"[0:v][av]overlay=x={xexpr}:y='{yexpr}':enable='{enable}'[v]")
    run(["ffmpeg", "-y", "-i", base, "-stream_loop", "-1", "-i", av["video"],
         "-loop", "1", "-i", mask, "-loop", "1", "-i", ring,
         "-filter_complex", fc, "-map", "[v]", "-t", str(probe_dur(base)),
         *venc("18", "veryfast"), "-pix_fmt", "yuv420p", out])

def overlay_avatar(base, av, W, H, out):
    corner = av.get("corner", "br"); m = av.get("margin", 54); size = av.get("size", 430)
    xexpr = f"W-w-{m}" if corner in ("br", "tr") else f"{m}"
    yexpr = f"H-h-{m}" if corner in ("br", "bl") else f"{m}"
    windows = av.get("windows", [])
    enable = "+".join(f"between(t,{a},{b})" for a, b in windows) if windows else "1"
    if av.get("chroma"):
        key = av.get("key", "0x00b140")
        fc = (f"[1:v]chromakey={key}:0.12:0.06,scale={size}:-1[av];"
              f"[0:v][av]overlay=x={xexpr}:y={yexpr}:enable='{enable}'[v]")
        run(["ffmpeg", "-y", "-i", base, "-i", av["img"], "-filter_complex", fc,
             "-map", "[v]", *venc("18", "veryfast"),
             "-pix_fmt", "yuv420p", out])
    else:
        fc = (f"[1:v]scale={size}:-1[av];"
              f"[0:v][av]overlay=x={xexpr}:y={yexpr}:enable='{enable}'[v]")
        run(["ffmpeg", "-y", "-i", base, "-loop", "1", "-i", av["img"],
             "-filter_complex", fc, "-map", "[v]", "-t", str(probe_dur(base)),
             *venc("18", "veryfast"), "-pix_fmt", "yuv420p", out])

# ---------- captions (Pillow PNG overlays; no libass needed) ----------
_CAP_FONTS = ["/System/Library/Fonts/Supplemental/Impact.ttf",
              "/System/Library/Fonts/Supplemental/Arial Black.ttf",
              "/System/Library/Fonts/HelveticaNeue.ttc"]

def _cap_font(size):
    for p in _CAP_FONTS:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: pass
    return ImageFont.load_default()

def render_caption_pngs(captions, accent, size, tmp):
    """One transparent PNG per word: big, uppercase, heavy outline, slight tilt.
    Hot words alternate accent-magenta / electric-yellow (Vaibhav-style color pops)."""
    r = int(accent[0:2], 16); g = int(accent[2:4], 16); b = int(accent[4:6], 16)
    mag = (r, g, b, 255); yel = (255, 214, 10, 255)
    white = (245, 247, 250, 255); black = (0, 0, 0, 255)
    f = _cap_font(size); sw = max(8, size // 12)
    probe = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    items = []; hot_n = 0
    for i, c in enumerate(captions):
        word = c["w"].upper()
        if c.get("hot"):
            col = mag if hot_n % 2 == 0 else yel; hot_n += 1
        else:
            col = white
        bb = probe.textbbox((0, 0), word, font=f, stroke_width=sw)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]; pad = sw + 46
        Wi, Hi = tw + pad * 2, th + pad * 2
        im = Image.new("RGBA", (Wi, Hi), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([6, 6, Wi - 6, Hi - 6], radius=int(Hi * 0.30), fill=(10, 10, 16, 180))
        d.text((pad - bb[0], pad - bb[1]), word, font=f, fill=col,
               stroke_width=sw, stroke_fill=black)
        if c.get("hot"):  # hot words get a slight tilt for punch
            im = im.rotate(-3 if hot_n % 2 else 3, expand=True, resample=Image.BICUBIC)
        p = os.path.join(tmp, f"cap_{i:03d}.png"); im.save(p)
        items.append((p, float(c["start"]), float(c["end"])))
    return items

def overlay_captions(video, items, H, out):
    if not items:
        os.replace(video, out); return
    y = int(H * 0.605)
    inputs = ["-i", video]
    for p, _, _ in items:
        inputs += ["-i", p]
    fc = []; prev = "[0:v]"
    for i, (p, s, e) in enumerate(items):
        lbl = "[v]" if i == len(items) - 1 else f"[t{i}]"
        fc.append(f"{prev}[{i+1}:v]overlay=x=(W-w)/2:y={y}:enable='between(t,{s},{e})'{lbl}")
        prev = lbl
    run(["ffmpeg", "-y"] + inputs + ["-filter_complex", ";".join(fc), "-map", "[v]",
         "-t", str(probe_dur(video)), *venc("18", "veryfast"),
         "-pix_fmt", "yuv420p", out])

def render_captions_remotion(stage_video, spec, fps, out):
    """Kinetic karaoke captions via the Remotion render layer (repo-root render/),
    behind the spec flag caption_engine="remotion". Maps the PNG-caption spec to
    the word-timestamp contract and leaves every other layer untouched. Keeps the
    FULL source duration so a trailing no-caption tail is never truncated."""
    import sys
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    from render_short import render_short
    words = [{"text": c["w"], "startMs": int(float(c["start"]) * 1000),
              "endMs": int(float(c["end"]) * 1000)} for c in spec["captions"]]
    # Default "tier1" = captions only. This channel carries its own watermark /
    # logo / banner branding, so the tier2 story-bar + Follow chrome stays OFF
    # unless a spec explicitly opts in via "caption_style": "tier2".
    render_short(stage_video, words, out,
                 style=spec.get("caption_style", "tier1"),
                 handle=spec.get("handle", "@aiunpacked"),
                 fps=fps, duration_s=probe_dur(stage_video))

# ---------- audio ----------
def mux_audio(video, vo, music, gain, out):
    if music and os.path.exists(music):
        # normalize=0 keeps the VO at full level (amix halves inputs by default);
        # loudnorm masters the final mix to Shorts-standard -14 LUFS.
        fc = (f"[1:a]afade=t=in:st=0:d=0.15,volume=11dB[v0];"
              f"[2:a]volume={gain}[m];"
              f"[v0][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
              f"alimiter=limit=0.89[a]")
        run(["ffmpeg", "-y", "-i", video, "-i", vo, "-stream_loop", "-1", "-i", music,
             "-filter_complex", fc, "-map", "0:v", "-map", "[a]",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out])
    else:
        run(["ffmpeg", "-y", "-i", video, "-i", vo, "-map", "0:v", "-map", "1:a",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    spec = json.load(open(args.spec))
    W = spec.get("w", 1080); H = spec.get("h", 1920); FPS = spec.get("fps", 30)
    accent = spec.get("accent", "E0218A")
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="aiunpacked_")

    base = os.path.join(tmp, "base.mp4")
    build_base(spec["segments"], W, H, FPS, tmp, base)

    stage = base
    if spec.get("avatar"):
        avs = spec["avatar"] if isinstance(spec["avatar"], list) else [spec["avatar"]]
        for k, av in enumerate(avs):
            av_out = os.path.join(tmp, f"avatar{k}.mp4")
            if av.get("video"):
                overlay_video_avatar(stage, av, accent, tmp, av_out)
            else:
                overlay_avatar(stage, av, W, H, av_out)
            stage = av_out

    if spec.get("captions"):
        cap_out = os.path.join(tmp, "capped.mp4")
        # caption_engine: "png" (default, PIL word overlays) | "remotion" (kinetic
        # karaoke via render/). Default preserves current renders exactly.
        if spec.get("caption_engine") == "remotion":
            render_captions_remotion(stage, spec, FPS, cap_out)
        else:
            items = render_caption_pngs(spec["captions"], accent, spec.get("caption_size", 150), tmp)
            overlay_captions(stage, items, H, cap_out)
        stage = cap_out

    # timed banners (e.g. thumbnail-style topic cover over the hook, fading out)
    for bi, b in enumerate(spec.get("banners", [])):
        if not os.path.exists(b["img"]):
            continue
        fade = b.get("fade_out", 0.0)   # seconds of alpha fade before `end`
        chain = f"[1:v]scale={int(W * b.get('scale', 0.92))}:-1,format=rgba"
        if fade > 0:
            chain += f",fade=t=out:st={b['end'] - fade:.2f}:d={fade}:alpha=1"
        chain += (f"[bn];[0:v][bn]overlay=x=(W-w)/2:y={b.get('y', int(H*0.09))}:"
                  f"enable='between(t,{b['start']},{b['end']})'[v]")
        b_out = os.path.join(tmp, f"banner{bi}.mp4")
        run(["ffmpeg", "-y", "-i", stage, "-loop", "1", "-i", b["img"], "-filter_complex",
             chain, "-map", "[v]", "-t", str(probe_dur(stage)),
             *venc("18", "veryfast"), "-pix_fmt", "yuv420p", b_out])
        stage = b_out

    # branding: persistent corner watermark + logo pop over the last ~1.2s
    wm = spec.get("watermark"); lp = spec.get("logo_pop")
    if wm or lp:
        total = probe_dur(stage)
        inputs = ["-i", stage]; fc = []; prev = "[0:v]"; idx = 1
        if wm and os.path.exists(wm):
            inputs += ["-loop", "1", "-i", wm]
            fc.append(f"[{idx}:v]scale=300:-1,format=rgba,colorchannelmixer=aa=0.75[wm];"
                      f"{prev}[wm]overlay=x=W-w-28:y=30[b{idx}]")
            prev = f"[b{idx}]"; idx += 1
        if lp and os.path.exists(lp):
            inputs += ["-loop", "1", "-i", lp]
            fc.append(f"[{idx}:v]scale=760:-1[lp];"
                      f"{prev}[lp]overlay=x=(W-w)/2:y=H*0.13:enable='gte(t,{total-1.2:.2f})'[b{idx}]")
            prev = f"[b{idx}]"; idx += 1
        brand_out = os.path.join(tmp, "branded.mp4")
        run(["ffmpeg", "-y"] + inputs + ["-filter_complex", ";".join(fc), "-map", prev,
             "-t", str(total), *venc("18", "veryfast"),
             "-pix_fmt", "yuv420p", brand_out])
        stage = brand_out

    if spec.get("vo"):
        mux_audio(stage, spec["vo"], spec.get("music", ""), spec.get("music_gain", 0.12), args.out)
    else:
        os.replace(stage, args.out)
    print(f">> DONE: {args.out}")

if __name__ == "__main__":
    main()
