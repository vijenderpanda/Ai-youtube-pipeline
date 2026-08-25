#!/usr/bin/env python3
"""
ep1_build.py — LONG-FORM EP1 full episode ("I Shipped an iPhone App in 3H 48M").

Grammar locked by the approved test slice v5.1:
  - one continuous VO take per section (never sliced); the VIDEO cuts on line bounds
  - 48kHz/stereo contract on every segment
  - host = HeyGen Avatar IV clips (full-frame for hook/midroll/outro, circle-masked
    TALKING PiP over tape for chapters)
  - captions: champagne karaoke, low band; OFF on card-type visuals
  - bed: lf_bed_golden_felt at 0.07 + lowpass 5k, no ducking; loudnorm -14 pinned 48k
All numbers are the REAL receipts (git log): 10:59 first commit -> 14:47 ship = 3H48M.

Usage:  python3 channels/claude-tricks/longform/ep1_build.py
Output: channels/claude-tricks/renders/longform/ep1_master.mp4 (+ .chapters.txt, .contact.jpg)
"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CH = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(CH))
sys.path.insert(0, CH)
sys.path.insert(0, os.path.join(REPO, "scripts"))
import build_longform_segment as lf
import ep1_storyboard as sb
from ffmpeg_util import venc
from PIL import Image, ImageDraw, ImageFont

R = os.path.join(CH, "renders", "longform")
A = os.path.join(CH, "assets", "longform_ep1")
VO = os.path.join(A, "vo")
BED = os.path.join(CH, "assets", "music", "lf_bed_golden_felt.mp3")
W, H, FPS = lf.W, lf.H, lf.FPS
PIP_D = 400

REAL = {"first": "10:59 AM  first commit", "ship": "2:47 PM  ship build",
        "span_min": 228, "span_txt": "3H 48M"}

SPEC_LINES = ["1. Ask permission to read the calendar",
              "2. Ask permission to set alarms",
              "3. Find the meetings",
              "4. Set a loud system alarm before each one",
              "5. Re-sync when meetings move"]


def run(cmd):
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)


def meta():
    return json.load(open(os.path.join(VO, "sections.json")))


def vo_wav(name, tmp):
    w = os.path.join(tmp, f"vo_{name}.wav")
    run([lf.FFMPEG, "-y", "-i", os.path.join(VO, f"{name}.mp3"),
         "-ar", "48000", "-ac", "2", w])
    return w


def words_of(name):
    return json.load(open(os.path.join(VO, f"{name}.words.json")))


def captions_on(video, words, lead, out):
    caps = lf.words_to_captions([{"w": w["w"], "start": w["start"] + lead,
                                  "end": w["end"] + lead} for w in words])
    with tempfile.TemporaryDirectory() as ctmp:
        from assemble_short import render_caption_pngs
        items = render_caption_pngs(caps, accent="E4C56B", size=72, tmp=ctmp)
        lf.overlay_captions_at(video, items, lf.CAP_Y, out)


def mux(video, wav, out, lead=0.0):
    af = f"adelay={int(lead * 1000)}|{int(lead * 1000)}," if lead > 0 else ""
    run([lf.FFMPEG, "-y", "-i", video, "-i", wav, "-filter_complex",
         f"[1:a]{af}aresample=48000,apad[a]", "-map", "0:v", "-map", "[a]",
         "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
         "-shortest", out])


def conform(src, ss, dur, out, drift=True):
    """Any source -> 1920x1080 slice with slow drift zoom (real motion feel)."""
    z = f"1+0.05*t/{max(dur, 1)}"
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2")
    if drift:
        vf += (f",scale=trunc(iw*({z})/2)*2:trunc(ih*({z})/2)*2:eval=frame,"
               f"crop={W}:{H}")
    vf += f",fps={FPS},format=yuv420p"
    run([lf.FFMPEG, "-y", "-ss", str(ss), "-i", src, "-t", str(dur), "-vf", vf,
         *venc("18", "veryfast"), "-an", out])


def still_slice(png, dur, out, drift_px=120):
    up = round(H * 1.15)
    vf = (f"scale=-2:{up},crop={W}:{H}:x=(iw-{W})/2:y='min({drift_px}*t/{max(dur,1)},ih-{H})',"
          f"fps={FPS},format=yuv420p")
    run([lf.FFMPEG, "-y", "-loop", "1", "-i", png, "-t", str(dur), "-vf", vf,
         *venc("18", "veryfast"), "-an", out])


def circle_mask_pngs(tmp):
    m = Image.new("L", (PIP_D, PIP_D), 0)
    ImageDraw.Draw(m).ellipse([0, 0, PIP_D, PIP_D], fill=255)
    mp = os.path.join(tmp, "pipmask.png"); m.save(mp)
    ring = 8
    D = PIP_D + ring * 2
    r = Image.new("RGBA", (D, D), (0, 0, 0, 0))
    d = ImageDraw.Draw(r)
    d.ellipse([0, 0, D, D], outline=lf.ACCENT + (255,), width=ring)
    rp = os.path.join(tmp, "pipring.png"); r.save(rp)
    return mp, rp


# face centers measured per Avatar IV clip (camera moves + framing differ per clip);
# tighter face-centered square keeps the host inside the circle (VJ QC 2026-08-25)
PIP_FACE = {"ch1": (870, 350, 500), "ch2": (800, 340, 500),
            "ch3": (1000, 350, 500), "ch4": (900, 350, 500)}
PIP_SQ = 720


def talking_pip(base_video, host_clip, dur, out, tmp, face=(960, 400), windows=None):
    """Circle-masked TALKING host over the tape (lip-synced to the section VO)."""
    mp, rp = circle_mask_pngs(tmp)
    x = W - PIP_D - 56
    y = H - PIP_D - 72
    cx, cy, sq = (face if len(face) == 3 else (*face, PIP_SQ))
    cx0 = max(0, min(1920 - sq, cx - sq // 2))
    cy0 = max(0, min(1080 - sq, cy - sq // 2))
    run([lf.FFMPEG, "-y", "-i", base_video, "-i", host_clip, "-i", mp, "-i", rp,
         "-filter_complex",
         (f"[1:v]fps={FPS},crop={sq}:{sq}:{cx0}:{cy0},"
          f"scale={PIP_D}:{PIP_D}[pv];"
          f"[2:v]loop=-1:1,scale={PIP_D}:{PIP_D},format=gray[msk];"
          f"[pv][msk]alphamerge[pa];"
          + (f"[0:v][pa]overlay=x={x}:y={y}:eof_action=repeat"
             + (f":enable='{windows}'" if windows else "") + "[b];")
          + f"[3:v]loop=-1:1[ring];[b][ring]overlay=x={x - 8}:y={y - 8}:eof_action=repeat"
          + (f":enable='{windows}'" if windows else "") + "[v]"),
         "-map", "[v]", "-t", str(dur), *venc("18", "veryfast"),
         "-pix_fmt", "yuv420p", "-an", out])


def receipts_real(dur, out, tmp):
    frames_dir = os.path.join(tmp, "rr"); os.makedirs(frames_dir, exist_ok=True)
    f_ts = ImageFont.truetype(lf.FONT_ANTON, 76)
    f_big = ImageFont.truetype(lf.FONT_ANTON, 150)
    n = int(dur * FPS)
    for i in range(n):
        t = i / FPS
        im = Image.new("RGB", (W, H), lf.INK)
        d = ImageDraw.Draw(im)
        a1 = min(1.0, max(0.0, t / 0.25))
        a2 = min(1.0, max(0.0, (t - 0.35) / 0.25))
        d.text((330, 300), REAL["first"], font=f_ts, fill=tuple(int(210 * a1) for _ in range(3)))
        d.text((330, 430), REAL["ship"], font=f_ts, fill=tuple(int(210 * a2) for _ in range(3)))
        k = min(1.0, max(0.0, (t - 0.7) / 0.6))
        mins = int(REAL["span_min"] * (1 - (1 - k) ** 3))
        txt = f"{mins // 60}H {mins % 60:02d}M"
        d.text(((W - d.textlength(txt, font=f_big)) / 2, 620), txt, font=f_big, fill=lf.ACCENT)
        im.save(os.path.join(frames_dir, f"f{i:04d}.png"))
    run([lf.FFMPEG, "-y", "-framerate", str(FPS), "-i", os.path.join(frames_dir, "f%04d.png"),
         *venc("18", "veryfast"), "-pix_fmt", "yuv420p", "-an", out])


def spec_card_still(hot, out):
    im = Image.new("RGB", (W, H), lf.INK)
    d = ImageDraw.Draw(im)
    f_t = ImageFont.truetype(lf.FONT_ANTON, 56)
    f_l = ImageFont.truetype(lf.FONT_ANTON, 58)
    d.text((150, 120), "THE ENTIRE BRIEF (from the code, verbatim)", font=f_t, fill=lf.ACCENT)
    for i, ln in enumerate(SPEC_LINES):
        y = 280 + i * 120
        col = (245, 245, 245) if i == hot else (120, 128, 138)
        if i == hot:
            d.rounded_rectangle([120, y - 16, 1800, y + 84], radius=14,
                                fill=(lf.ACCENT + (40,))[:3], outline=lf.ACCENT, width=3)
        d.text((160, y), ln, font=f_l, fill=col)
    im.save(out)


def pop_still(text, sub, out):
    lf.pop_text_still(text, out, sub=sub)


def concat_slices(slices, out, tmp, tag):
    lst = os.path.join(tmp, f"cat_{tag}.txt")
    with open(lst, "w") as f:
        for s in slices:
            f.write(f"file '{s}'\n")
    run([lf.FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", lst,
         "-vf", f"fps={FPS},format=yuv420p", *venc("18", "veryfast"), "-an", out])


def line_times(name, lead=0.3, tail=0.6):
    m = meta()[name]
    bs = m["bounds"]
    times = []
    for i, b in enumerate(bs):
        t0 = (bs[i - 1]["end"] + b["start"]) / 2 + lead if i else 0.0
        t1 = (b["end"] + bs[i + 1]["start"]) / 2 + lead if i + 1 < len(bs) else b["end"] + lead + tail
        times.append((t0, t1))
    return times, bs[-1]["end"] + lead + tail


def static_pip_overlay(base_video, dur, out, tmp):
    """Fallback when no HeyGen clip exists (API credits): champagne circle pip, still."""
    pip_png = os.path.join(tmp, "spip.png")
    sb.leo_pip().save(pip_png)
    pw = Image.open(pip_png).width
    run([lf.FFMPEG, "-y", "-i", base_video, "-i", pip_png, "-filter_complex",
         f"[0:v][1:v]overlay=x={W - pw - 48}:y={H - pw - 64}[v]", "-map", "[v]",
         "-t", str(dur), *venc("18", "veryfast"), "-pix_fmt", "yuv420p", "-an", out])


def build_section(name, visuals, tmp, pip=None, pip_lines=None, captions=True, lead=0.3):
    """visuals: list of callables f(dur, out) aligned to VO lines."""
    times, total = line_times(name, lead=lead)
    slices = []
    for i, ((t0, t1), fn) in enumerate(zip(times, visuals)):
        p = os.path.join(tmp, f"{name}_s{i}.mp4")
        fn(t1 - t0, p)
        slices.append(p)
    base = os.path.join(tmp, f"{name}_base.mp4")
    concat_slices(slices, base, tmp, name)
    cur = base
    if pip:
        p2 = os.path.join(tmp, f"{name}_pip.mp4")
        win = None
        if pip_lines is not None:
            win = "+".join(f"between(t,{times[i][0]:.2f},{times[i][1]:.2f})" for i in pip_lines)
        if os.path.exists(pip):
            talking_pip(cur, pip, total, p2, tmp,
                        face=PIP_FACE.get(name, (960, 400, PIP_SQ)), windows=win)
        else:
            print(f"!! {name}: host clip missing (HeyGen credits) — static pip degrade")
            static_pip_overlay(cur, total, p2, tmp)
        cur = p2
    if captions:
        c = os.path.join(tmp, f"{name}_cap.mp4")
        captions_on(cur, words_of(name), lead, c)
        cur = c
    seg = os.path.join(tmp, f"{name}_seg.mp4")
    mux(cur, vo_wav(name, tmp), seg, lead=lead)
    return seg, total


def host_full_section(name, tmp, captions=True):
    clip = os.path.join(A, f"host_{name}.mp4")
    if not os.path.exists(clip):
        print(f"!! {name}: host clip missing (HeyGen credits) — pushed-still degrade")
        times, total = line_times(name)
        png = os.path.join(tmp, f"{name}_still.png")
        sb.leo_host("close").save(png)
        v = os.path.join(tmp, f"{name}_v.mp4")
        still_slice(png, total, v, drift_px=90)
        c = os.path.join(tmp, f"{name}_c.mp4")
        captions_on(v, words_of(name), 0.3, c)
        seg = os.path.join(tmp, f"{name}_seg.mp4")
        mux(c, vo_wav(name, tmp), seg, lead=0.3)
        return seg, total
    dur = float(subprocess.check_output(
        [lf.FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", clip]).strip())
    v = os.path.join(tmp, f"{name}_v.mp4")
    run([lf.FFMPEG, "-y", "-i", clip, "-vf", f"scale={W}:{H}:flags=lanczos,fps={FPS}",
         *venc("18", "veryfast"), "-c:a", "aac", "-ar", "48000", "-ac", "2",
         "-b:a", "192k", v])
    if not captions:
        return v, dur
    c = os.path.join(tmp, f"{name}_c.mp4")
    captions_on(v, words_of(name), 0.0, c)
    seg = os.path.join(tmp, f"{name}_seg.mp4")
    run([lf.FFMPEG, "-y", "-i", c, "-i", v, "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "copy", seg])
    return seg, dur


def card(tmp, idx, title, dur=1.6):
    png = os.path.join(tmp, f"card{idx}.png")
    lf.chapter_card_still(idx, title, png)
    v = os.path.join(tmp, f"card{idx}_v.mp4")
    still_slice(png, dur, v, drift_px=50)
    s0 = os.path.join(tmp, f"card{idx}_s0.mp4")
    run([lf.FFMPEG, "-y", "-i", v, "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
         "-shortest", "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-ac", "2", s0])
    s = os.path.join(tmp, f"card{idx}_s.mp4")
    sfx_mix(s0, [(0.05, "whoosh")], s)
    return s, dur



def overlay_png(video, png, out):
    run([lf.FFMPEG, "-y", "-i", video, "-i", png, "-filter_complex",
         "[0:v][1:v]overlay=0:0[v]", "-map", "[v]", *venc("18", "veryfast"),
         "-pix_fmt", "yuv420p", "-an", out])


def feature_label_png(title, sub, out):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f_t = _uifont(64, bold=True)
    f_s = _uifont(34)
    d.rectangle([96, 104, 104, 196], fill=lf.ACCENT + (255,))
    d.text((126, 104), title, font=f_t, fill=(250, 250, 250, 255),
           stroke_width=2, stroke_fill=(0, 0, 0, 140))
    d.text((128, 182), sub, font=f_s, fill=lf.ACCENT + (255,),
           stroke_width=1, stroke_fill=(0, 0, 0, 130))
    im.save(out)


def subscribe_card_still(out):
    im = Image.new("RGB", (W, H), lf.INK)
    d = ImageDraw.Draw(im)
    try:
        icon = Image.open(sb.ICON).convert("RGB").resize((300, 300), Image.LANCZOS)
        m = Image.new("L", (300, 300), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, 300, 300], radius=66, fill=255)
        im.paste(icon, ((W - 300) // 2, 220), m)
    except Exception:
        pass
    f_b = ImageFont.truetype(lf.FONT_ANTON, 130)
    f_s = ImageFont.truetype(lf.FONT_ANTON, 54)
    t = "SUBSCRIBE"
    d.text(((W - d.textlength(t, font=f_b)) / 2, 600), t, font=f_b, fill=lf.ACCENT)
    t2 = "next: the $0 creator studio"
    d.text(((W - d.textlength(t2, font=f_s)) / 2, 780), t2, font=f_s, fill=(210, 215, 222))
    im.save(out)



GLASS_FG_W, GLASS_FG_H, GLASS_R = 1614, 908, 30
SFX = os.path.join(CH, "assets", "sfx_lf")


def make_glass_assets(tmp):
    fgm = os.path.join(tmp, "glass_mask.png")
    m = Image.new("L", (GLASS_FG_W, GLASS_FG_H), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, GLASS_FG_W, GLASS_FG_H], radius=GLASS_R, fill=255)
    m.save(fgm)
    brd = os.path.join(tmp, "glass_border.png")
    b = Image.new("RGBA", (GLASS_FG_W, GLASS_FG_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(b)
    d.rounded_rectangle([1, 1, GLASS_FG_W - 2, GLASS_FG_H - 2], radius=GLASS_R,
                        outline=(255, 255, 255, 92), width=2)
    d.rounded_rectangle([3, 3, GLASS_FG_W - 4, GLASS_FG_H - 4], radius=GLASS_R - 2,
                        outline=(255, 255, 255, 30), width=1)
    b.save(brd)
    shd = os.path.join(tmp, "glass_shadow.png")
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle(
        [(W - GLASS_FG_W) // 2 + 10, (H - GLASS_FG_H) // 2 + 22,
         (W + GLASS_FG_W) // 2 + 10, (H + GLASS_FG_H) // 2 + 22],
        radius=GLASS_R, fill=(0, 0, 0, 150))
    from PIL import ImageFilter
    sh = sh.filter(ImageFilter.GaussianBlur(24))
    sh.save(shd)
    return fgm, brd, shd


def glass_conform(src, ss, dur, out, tmp):
    """Screen tape in a glass card: blurred self backdrop + rounded fg + border + shadow."""
    fgm, brd, shd = make_glass_assets(tmp)
    x = (W - GLASS_FG_W) // 2
    y = (H - GLASS_FG_H) // 2
    run([lf.FFMPEG, "-y", "-ss", str(ss), "-i", src, "-i", shd, "-i", fgm, "-i", brd,
         "-t", str(dur), "-filter_complex",
         (f"[0:v]fps={FPS},split=2[a][b];"
          f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
          f"gblur=sigma=32,eq=brightness=-0.18:saturation=0.85[bg];"
          f"[b]scale={GLASS_FG_W}:{GLASS_FG_H}:force_original_aspect_ratio=decrease,"
          f"pad={GLASS_FG_W}:{GLASS_FG_H}:(ow-iw)/2:(oh-ih)/2:color=0x0E1116[fgs];"
          f"[2:v]loop=-1:1,format=gray[mk];[fgs][mk]alphamerge[fga];"
          f"[bg][1:v]overlay=0:0[s1];[s1][fga]overlay={x}:{y}[s2];"
          f"[3:v]loop=-1:1[bo];[s2][bo]overlay={x}:{y}[v]"),
         "-map", "[v]", *venc("18", "veryfast"), "-pix_fmt", "yuv420p", "-an", out])


def cutout_overlay(video, which, out, height=760, xoff=None):
    """Modern host: transparent CUTOUT (no circle) riding bottom-right over the tape."""
    png = os.path.join(A, f"cutout_{which}.png")
    src = Image.open(png)
    w2 = round(src.width * height / src.height)
    x = (W - w2 - 8) if xoff is None else xoff
    run([lf.FFMPEG, "-y", "-i", video, "-i", png, "-filter_complex",
         f"[1:v]scale={w2}:{height}[c];[0:v][c]overlay=x={x}:y={H - height}[v]",
         "-map", "[v]", *venc("18", "veryfast"), "-pix_fmt", "yuv420p", "-an", out])


def sfx_mix(video_with_audio, events, out):
    """Mix whoosh/pop SFX at given times over a segment's existing audio.
    events: list of (time_s, 'whoosh'|'pop')."""
    if not events:
        os.replace(video_with_audio, out); return
    inputs = ["-i", video_with_audio]
    fc, mix = [], "[0:a]"
    for i, (t, kind) in enumerate(events):
        inputs += ["-i", os.path.join(SFX, f"{kind}.wav")]
        fc.append(f"[{i+1}:a]adelay={int(t*1000)}|{int(t*1000)}[sx{i}]")
        mix += f"[sx{i}]"
    fc.append(f"{mix}amix=inputs={len(events)+1}:duration=first:normalize=0[a]")
    run([lf.FFMPEG, "-y"] + inputs + ["-filter_complex", ";".join(fc),
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac",
         "-ar", "48000", "-ac", "2", "-b:a", "192k", out])



L = os.path.join(CH, "assets", "character", "host_library", "longform_champagne_v1")
PLATES = [
    {"img": os.path.join(A, "stage_plates", "using-the-reference-image-keep-the-e_1f1a0a5d_1.jpg"),
     "quad": ((92, 206), (948, 268), (956, 848), (98, 898)), "occlude": False},
    {"img": os.path.join(L, "using-the-reference-image-keep-the-e_1f1a0757_1.jpg"),
     "quad": ((62, 182), (560, 297), (555, 778), (70, 848)), "occlude": True},
]


def _plate_mask(pl, tmp, tag):
    """Quad mask; for occluding plates keep only BRIGHT pixels inside the quad so the
    mic arm crossing the screen stays in front of the composited tape."""
    mp = os.path.join(tmp, f"pmask_{tag}.png")
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon(list(pl["quad"]), fill=255)
    if pl["occlude"]:
        import numpy as np
        g = np.asarray(Image.open(pl["img"]).convert("L").resize((W, H)))
        mm = np.asarray(m)
        mm = ((mm > 0) & (g > 85)).astype("uint8") * 255
        m = Image.fromarray(mm).filter(__import__("PIL.ImageFilter", fromlist=["ImageFilter"]).GaussianBlur(1.2))
    m.save(mp)
    return mp


def monitor_stage(src, ss, dur, out, tmp, plate=0, cutout=None, ch=None):
    """Tape perspective-warped into a real Leonardo plate's angled screen."""
    pl = PLATES[plate % len(PLATES)]
    mp = _plate_mask(pl, tmp, plate)
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = pl["quad"]
    pts = f"x0={x0}:y0={y0}:x1={x1}:y1={y1}:x2={x3}:y2={y3}:x3={x2}:y3={y2}"
    seek = ["-ss", str(ss)] if ss else []
    run([lf.FFMPEG, "-y", "-loop", "1", "-i", pl["img"], *seek, "-i", src, "-i", mp,
         "-t", str(dur), "-filter_complex",
         (f"[0:v]scale={W}:{H}[bg];"
          f"[1:v]fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,"
          f"crop={W}:{H},perspective={pts}:sense=destination[warp];"
          f"[2:v]loop=-1:1,format=gray[mk];[warp][mk]alphamerge[quad];"
          f"[bg][quad]overlay=0:0,"
          f"scale=w='trunc({W}*(1.013+0.012*sin(t*0.9))/2)*2':h=-2:eval=frame,"
          f"crop={W}:{H}:(iw-{W})/2:(ih-{H})/2[v]"),
         "-map", "[v]", *venc("18", "veryfast"), "-pix_fmt", "yuv420p", "-an", out])



# ---- Mikey-style asset kit (champagne edition): floating window + webcam bubble,
# ---- cascading pills, step diagram, check row, kinetic highlighted line ----
WIN_W, WIN_H, WIN_R = 1560, 880, 26


def _soft_bg(tmp):
    pth = os.path.join(tmp, "soft_bg.png")
    if os.path.exists(pth):
        return pth
    im = Image.new("RGB", (W, H), (15, 17, 22))
    d = ImageDraw.Draw(im)
    for r in range(1100, 0, -8):
        a = int(20 * r / 1100)
        d.ellipse([W // 2 - r, H + 200 - r, W // 2 + r, H + 200 + r],
                  fill=(15 + a, 15 + int(a * 0.85), 22 + int(a * 0.3)))
    im.save(pth)
    return pth


def _webcam_bubble(tmp):
    pth = os.path.join(tmp, "bubble.png")
    if os.path.exists(pth):
        return pth
    src = Image.open(os.path.join(A, "cutout_close.png"))
    bw, bh = 300, 300
    face = src.crop((int(src.width * 0.18), 0, int(src.width * 0.18) + src.height, src.height))
    face = face.resize((bh, bh), Image.LANCZOS)
    card = Image.new("RGBA", (bw + 12, bh + 12), (0, 0, 0, 0))
    inner = Image.new("RGBA", (bw, bh), (24, 26, 32, 255))
    inner.paste(face, (0, 0), face)
    m = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, bw, bh], radius=40, fill=255)
    card.paste(inner, (6, 6), m)
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([6, 6, bw + 6, bh + 6], radius=40, outline=lf.ACCENT + (255,), width=4)
    card.save(pth)
    return pth


def window_stage(src, ss, dur, out, tmp, bubble=True, bar_title="localhost — MissNoMeetings"):
    """Floating rounded app window on a soft dark ground + webcam-bubble host."""
    bg = _soft_bg(tmp)
    wx, wy = (W - WIN_W) // 2, (H - WIN_H) // 2 + 10
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(frame)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([wx + 8, wy + 20, wx + WIN_W + 8, wy + WIN_H + 20],
                                         radius=WIN_R, fill=(0, 0, 0, 140))
    from PIL import ImageFilter
    sh = sh.filter(ImageFilter.GaussianBlur(20))
    d2 = ImageDraw.Draw(sh)
    d2.rounded_rectangle([wx, wy, wx + WIN_W, wy + WIN_H], radius=WIN_R, fill=(20, 22, 28, 255),
                         outline=(255, 255, 255, 60), width=2)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d2.ellipse([wx + 26 + i * 30, wy + 20, wx + 44 + i * 30, wy + 38], fill=c + (255,))
    f = ImageFont.truetype(lf.FONT_ANTON, 22)
    d2.text((wx + 130, wy + 18), bar_title, font=f, fill=(150, 156, 166, 255))
    fp = os.path.join(tmp, f"winframe_{bar_title[:8]}.png"); sh.save(fp)
    iw, ih = WIN_W - 4, WIN_H - 56
    mk = Image.new("L", (iw, ih), 0)
    ImageDraw.Draw(mk).rounded_rectangle([0, 0, iw, ih], radius=WIN_R - 6, fill=255)
    mkp = os.path.join(tmp, "winmask.png"); mk.save(mkp)
    bub = _webcam_bubble(tmp)
    seek = ["-ss", str(ss)] if ss else []
    fc = (f"[0:v]scale={W}:{H}[bg];"
          f"[2:v]loop=-1:1[fr];[bg][fr]overlay=0:0[s1];"
          f"[1:v]fps={FPS},scale={iw}:{ih}:force_original_aspect_ratio=decrease,"
          f"pad={iw}:{ih}:(ow-iw)/2:(oh-ih)/2:color=0x14161C,"
          f"eq=brightness=0.05:contrast=1.10:saturation=1.18[tv];"
          f"[3:v]loop=-1:1,format=gray[mk];[tv][mk]alphamerge[tva];"
          f"[s1][tva]overlay={wx + 2}:{wy + 52}[s2];")
    inputs = ["-loop", "1", "-i", bg, *seek, "-i", src, "-loop", "1", "-i", fp,
              "-loop", "1", "-i", mkp]
    if bubble:
        inputs += ["-loop", "1", "-i", bub]
        fc += f"[s2][4:v]overlay={W - 380}:{H - 380}[v]"
    else:
        fc += "[s2]null[v]"
    run([lf.FFMPEG, "-y"] + inputs + ["-t", str(dur), "-filter_complex", fc,
         "-map", "[v]", *venc("18", "veryfast"), "-pix_fmt", "yuv420p", "-an", out])


def _frames_to_mp4(frames_dir, out):
    run([lf.FFMPEG, "-y", "-framerate", str(FPS), "-i",
         os.path.join(frames_dir, "f%04d.png"), *venc("18", "veryfast"),
         "-pix_fmt", "yuv420p", "-an", out])


def _ease(t):
    return 1 - (1 - max(0.0, min(1.0, t))) ** 3


UIFONT = "/System/Library/Fonts/HelveticaNeue.ttc"


def _uifont(sz, bold=False):
    try:
        return ImageFont.truetype(UIFONT, sz, index=1 if bold else 0)
    except Exception:
        return ImageFont.truetype(lf.FONT_ANTON, sz)


def pills_anim(labels, dur, out, tmp, title=None):
    """Slim cascading chips — modern, quiet, champagne tick (v2 after VJ 'fat ugly')."""
    fd = os.path.join(tmp, f"pl_{abs(hash(tuple(labels))) % 99999}")
    os.makedirs(fd, exist_ok=True)
    f = _uifont(34)
    ft = _uifont(26, bold=True)
    n = int(dur * FPS)
    for i in range(n):
        t = i / FPS
        im = Image.open(_soft_bg(tmp)).convert("RGB")
        d = ImageDraw.Draw(im)
        if title:
            d.text((360, 170), title.upper(), font=ft, fill=(140, 146, 156))
        for j, lab in enumerate(labels):
            k = _ease((t - 0.22 * j) / 0.4)
            if k <= 0:
                continue
            y = 260 + j * 104 - int(18 * (1 - k))
            x = 360
            tw = d.textlength(lab, font=f)
            fill = (26, 28, 35)
            d.rounded_rectangle([x, y, x + tw + 112, y + 64], radius=32, fill=fill,
                                outline=(64, 68, 78), width=1)
            cx, cy = x + 34, y + 32
            d.ellipse([cx - 13, cy - 13, cx + 13, cy + 13], outline=lf.ACCENT, width=2)
            if k > 0.7:
                d.line([(cx - 6, cy), (cx - 1, cy + 5), (cx + 7, cy - 5)], fill=lf.ACCENT, width=3)
            d.text((x + 64, y + 14), lab, font=f, fill=(int(238 * k),) * 3)
        im.save(os.path.join(fd, f"f{i:04d}.png"))
    _frames_to_mp4(fd, out)


def kinetic_line(text, hot, dur, out, tmp):
    """Single centered sentence, key word in champagne, soft scale-in."""
    fd = os.path.join(tmp, f"kl_{abs(hash(text)) % 99999}")
    os.makedirs(fd, exist_ok=True)
    n = int(dur * FPS)
    words = text.split()
    for i in range(n):
        t = i / FPS
        k = _ease(t / 0.5)
        base = 56 + int(5 * k)
        f = _uifont(base, bold=True)
        im = Image.open(_soft_bg(tmp)).convert("RGB")
        d = ImageDraw.Draw(im)
        widths = [d.textlength(w + " ", font=f) for w in words]
        total = sum(widths)
        x = (W - total) / 2
        for w, ww in zip(words, widths):
            hots = {h.lower() for h in (hot if isinstance(hot, (set, list, tuple)) else [hot])}
            col = lf.ACCENT if w.strip(".,!?").lower() in hots else (int(235 * k),) * 3
            d.text((x, H // 2 - base), w, font=f, fill=col)
            x += ww
        im.save(os.path.join(fd, f"f{i:04d}.png"))
    _frames_to_mp4(fd, out)


def main():
    os.makedirs(R, exist_ok=True)
    segs, chapters, t_cursor = [], [], 0.0

    def add(seg, dur, chapter=None):
        nonlocal t_cursor
        if chapter:
            chapters.append((t_cursor, chapter))
        segs.append(seg)
        t_cursor += dur

    with tempfile.TemporaryDirectory() as tmp:
        DEMO = os.path.join(A, "mnm_demo.mov")
        SIM = os.path.join(A, "sim_usage.mp4")
        LIVE = os.path.join(A, "sim_live.mp4")
        BR1 = os.path.join(A, "broll_br1.mp4")
        BR2 = os.path.join(A, "broll_br2.mp4")
        BR3 = os.path.join(A, "broll_br3.mp4")
        GITLOG = os.path.join(A, "tape_gitlog.mp4")
        CODE = os.path.join(A, "tape_code.mp4")
        TRANS = os.path.join(A, "tape_transcript.mp4")

        listing_png = os.path.join(tmp, "listing.png")
        sb.appstore_listing_still().save(listing_png)

        # ---- HOOK (v5 approved: HOST ON CAMERA + cutaways; audio = clip's own) ----
        HOOKC = os.path.join(A, "host_hook.mp4")
        hw = json.load(open(os.path.join(A, "hook.words.json")))
        T1, T2, T3 = 2.06, 4.00, 6.35
        hook_dur = 10.5
        c1v = os.path.join(tmp, "hkc1.mp4"); still_slice(listing_png, T2 - T1, c1v, 200)
        c2v = os.path.join(tmp, "hkc2.mp4"); conform(LIVE, 2.0, T3 - T2, c2v)
        hb = os.path.join(tmp, "hook_base.mp4")
        run([lf.FFMPEG, "-y", "-i", HOOKC, "-i", c1v, "-i", c2v, "-filter_complex",
             f"[0:v]fps={FPS},scale={W}:{H}:flags=lanczos[h];"
             f"[1:v]setpts=PTS+{T1}/TB[c1];[2:v]setpts=PTS+{T2}/TB[c2];"
             f"[h][c1]overlay=eof_action=pass:enable='between(t,{T1},{T2})'[x1];"
             f"[x1][c2]overlay=eof_action=pass:enable='between(t,{T2},{T3})'[v]",
             "-map", "[v]", "-map", "0:a", *venc("18", "veryfast"),
             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", hb])
        hc = os.path.join(tmp, "hook_cap.mp4"); captions_on(hb, hw, 0.0, hc)
        hf = os.path.join(tmp, "hook_seg.mp4")
        run([lf.FFMPEG, "-y", "-i", hc, "-i", hb, "-map", "0:v", "-map", "1:a",
             "-c:v", "copy", "-c:a", "copy", hf])
        add(hf, hook_dur, chapter="Hook")

        # ---- RELATE (curiosity b-roll — "have you tried AI...", VJ positioning) ----
        times, total = line_times("relate")
        POPQ = [("TRIED AGENTS?", "workflows - side hustles - gen AI"),
                ("GAVE UP?", "the back-and-forth loop"),
                (None, None), (None, None)]
        rv = []
        for i, ((t0, t1), src) in enumerate(zip(times, [BR1, None, GITLOG, LIVE])):
            base_v = os.path.join(tmp, f"rl{i}.mp4")
            if i == 1:
                kinetic_line("Somewhere in that loop... you give up.",
                             ("give", "up"), t1 - t0, base_v, tmp)
            else:
                monitor_stage(src, 0.0 if i != 3 else 1.0, t1 - t0, base_v, tmp, plate=i % 2)
            if POPQ[i][0]:
                lab = os.path.join(tmp, f"rlq{i}.png")
                feature_label_png(POPQ[i][0], POPQ[i][1], lab)
                ov = os.path.join(tmp, f"rlo{i}.mp4"); overlay_png(base_v, lab, ov)
                base_v = ov
            rv.append(base_v)
        rb = os.path.join(tmp, "rel_base.mp4"); concat_slices(rv, rb, tmp, "rel")
        rcut = rb
        rc = os.path.join(tmp, "rel_cap.mp4"); captions_on(rcut, words_of("relate"), 0.3, rc)
        rs0 = os.path.join(tmp, "rel_seg0.mp4"); mux(rc, vo_wav("relate", tmp), rs0, lead=0.3)
        rs = os.path.join(tmp, "rel_seg.mp4")
        sfx_mix(rs0, [(t0, "pop") for (t0, _), q in zip(times, POPQ) if q[0]], rs)
        add(rs, total, chapter="Sound Familiar?")

        # ---- CH1 The Idea ----
        s, d = card(tmp, 1, "The Idea"); add(s, d, chapter="The Idea")
        seg, d = build_section("ch1", [
            lambda du, o: monitor_stage(DEMO, 0.0, du, o, tmp, plate=0),
            lambda du, o: window_stage(CODE, 0.0, du, o, tmp, bubble=False,
                                       bar_title="MeetingStore.swift"),
            lambda du, o: window_stage(LIVE, 2.0, du, o, tmp, bubble=False),
        ], tmp, pip=os.path.join(A, "host_ch1.mp4"), pip_lines=[1, 2])
        add(seg, d)

        # ---- CH2 The Build ----
        s, d = card(tmp, 2, "The Build"); add(s, d, chapter="The Build")
        seg, d = build_section("ch2", [
            lambda du, o: pills_anim(["Read the calendar", "Set alarms", "Find meetings",
                                      "Ring loud, locked", "Re-sync on change"],
                                     du, o, tmp, title="THE FIVE LINES"),
            lambda du, o: window_stage(CODE, 4.0, du, o, tmp, bubble=False,
                                       bar_title="MeetingStore.swift"),
            lambda du, o: window_stage(SIM, 20.0, du, o, tmp, bubble=False),
            lambda du, o: window_stage(TRANS, 0.0, du, o, tmp, bubble=False,
                                       bar_title="Claude Code — session log"),
            lambda du, o: window_stage(GITLOG, 8.0, du, o, tmp, bubble=False,
                                       bar_title="git log"),
        ], tmp, pip=os.path.join(A, "host_ch2.mp4"), pip_lines=[1, 2, 3, 4])
        add(seg, d)

        # ---- CH3 On My iPhone ----
        s, d = card(tmp, 3, "On My iPhone"); add(s, d, chapter="On My iPhone")
        seg, d = build_section("ch3", [
            lambda du, o: monitor_stage(LIVE, 30.0, du, o, tmp, plate=1),
            lambda du, o: window_stage(DEMO, 2.0, du, o, tmp, bubble=False),
            lambda du, o: window_stage(DEMO, 8.0, du, o, tmp, bubble=False),
            lambda du, o: window_stage(TRANS, 8.0, du, o, tmp, bubble=False,
                                       bar_title="Claude Code — session log"),
        ], tmp, pip=os.path.join(A, "host_ch3.mp4"), pip_lines=[1, 2, 3])
        add(seg, d)

        # ---- THE APP (feature showcase / marketing beat — vision job #2) ----
        sc, d = card(tmp, 4, "The App"); add(sc, d, chapter="The App")
        FEATURES = [("IMPORTANT ONLY", "alarm just the meetings that matter", 52.0),
                    ("RING BEFORE", "you pick the runway: 2m - 30m", 12.0),
                    ("TWO ALARM SOUNDS", "Standard rings. Gentle chimes.", 22.0),
                    ("RINGS WHEN LOCKED", "the feature I missed calls for", 1.0)]
        times, total = line_times("appfeat")
        fs = []
        for i, ((t0, t1), (ttl, sub, ss)) in enumerate(zip(times, FEATURES)):
            base_v = os.path.join(tmp, f"ft{i}.mp4")
            window_stage(LIVE, ss, t1 - t0, base_v, tmp, bubble=False, bar_title="MissNoMeetings")
            lab = os.path.join(tmp, f"ftl{i}.png"); feature_label_png(ttl, sub, lab)
            ov = os.path.join(tmp, f"fto{i}.mp4"); overlay_png(base_v, lab, ov)
            fs.append(ov)
        ab0 = os.path.join(tmp, "app_base0.mp4"); concat_slices(fs, ab0, tmp, "app")
        ab = os.path.join(tmp, "app_base.mp4")
        cutout_overlay(ab0, "close", ab, height=640)  # app BEHIND the host (VJ)
        ac = os.path.join(tmp, "app_cap.mp4"); captions_on(ab, words_of("appfeat"), 0.3, ac)
        aseg0 = os.path.join(tmp, "app_seg0.mp4"); mux(ac, vo_wav("appfeat", tmp), aseg0, lead=0.3)
        aseg = os.path.join(tmp, "app_seg.mp4")
        sfx_mix(aseg0, [(t0, "pop") for t0, _ in times], aseg)
        add(aseg, total)

        # ---- MID-ROLL (HeyGen talking host + kinetic-line cutaway) ----
        mv, mdur = host_full_section("midroll", tmp, captions=True)
        times, _ = line_times("midroll", lead=0.0, tail=0.0)
        klv = os.path.join(tmp, "mid_kl.mp4")
        kinetic_line("It builds. It runs. It repairs itself.", "repairs",
                     times[1][1] - times[1][0], klv, tmp)
        mo = os.path.join(tmp, "mid_over.mp4")
        run([lf.FFMPEG, "-y", "-i", mv, "-i", klv, "-filter_complex",
             f"[1:v]setpts=PTS+{times[1][0]}/TB[k];"
             f"[0:v][k]overlay=eof_action=pass:enable='between(t,{times[1][0]},{times[1][1]})'[v]",
             "-map", "[v]", "-map", "0:a", *venc("18", "veryfast"),
             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", mo])
        mseg = os.path.join(tmp, "mid_seg.mp4")
        sfx_mix(mo, [(times[1][0], "whoosh")], mseg)
        add(mseg, mdur, chapter="Why Now")

        # ---- CH4 The App Store ----
        s, d = card(tmp, 5, "The App Store"); add(s, d, chapter="The App Store")
        seg, d = build_section("ch4", [
            lambda du, o: pills_anim(["Step 1 — Signing", "Step 2 — Archive",
                                      "Step 3 — App Store Connect", "Step 4 — Submit"],
                                     du, o, tmp, title="THE BORING WALL"),
            lambda du, o: still_slice(listing_png, du, o, 150),
            lambda du, o: receipts_real(du, o, tmp),
        ], tmp, pip=None, captions=True)
        add(seg, d)

        # ---- PAYOFF (spec card, line-by-line highlight on VO bounds) ----
        times, total = line_times("payoff")
        stills = []
        for i in range(3):
            p = os.path.join(tmp, f"spec{i}.png")
            spec_card_still({0: -1, 1: 2, 2: 2}[i], p)
            stills.append(p)
        pv = []
        for i, ((t0, t1), p) in enumerate(zip(times, stills)):
            o = os.path.join(tmp, f"pay_s{i}.mp4")
            still_slice(p, t1 - t0, o, drift_px=40)
            pv.append(o)
        pb = os.path.join(tmp, "pay_base.mp4"); concat_slices(pv, pb, tmp, "pay")
        pc = os.path.join(tmp, "pay_cap.mp4"); captions_on(pb, words_of("payoff"), 0.3, pc)
        ps = os.path.join(tmp, "pay_seg.mp4"); mux(pc, vo_wav("payoff", tmp), ps, lead=0.3)
        add(ps, total, chapter="Copy The Brief")

        # ---- OUTRO (host-free: receipts -> factory flex -> subscribe) ----
        times, total = line_times("outro2")
        o1 = os.path.join(tmp, "ot1.mp4"); receipts_real(times[0][1] - times[0][0], o1, tmp)
        flex_src = os.path.join(R, "ep1_storyboard.jpg")
        o2 = os.path.join(tmp, "ot2.mp4")
        if os.path.exists(flex_src):
            fd = times[1][1] - times[1][0]
            run([lf.FFMPEG, "-y", "-loop", "1", "-i", flex_src, "-t", str(fd),
                 "-vf", (f"scale={W}:-2,crop={W}:{H}:0:y='min((ih-{H})*t/{fd},ih-{H})',"
                         f"fps={FPS},format=yuv420p"),
                 *venc("18", "veryfast"), "-an", o2])
        else:
            conform(GITLOG, 4.0, times[1][1] - times[1][0], o2, drift=False)
        sub_png = os.path.join(tmp, "subcard.png"); subscribe_card_still(sub_png)
        o3 = os.path.join(tmp, "ot3.mp4"); still_slice(sub_png, times[2][1] - times[2][0], o3, drift_px=40)
        ob = os.path.join(tmp, "out_base.mp4"); concat_slices([o1, o2, o3], ob, tmp, "outro")
        oc = os.path.join(tmp, "out_cap.mp4"); captions_on(ob, words_of("outro2"), 0.3, oc)
        oseg = os.path.join(tmp, "out_seg.mp4"); mux(oc, vo_wav("outro2", tmp), oseg, lead=0.3)
        add(oseg, total, chapter="What's Next")

        # ---- JOIN + BED + LOUDNORM ----
        lst = os.path.join(tmp, "master.txt")
        with open(lst, "w") as f:
            for s in segs:
                f.write(f"file '{s}'\n")
        raw = os.path.join(tmp, "raw.mp4")
        run([lf.FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", lst,
             "-vf", f"fps={FPS},format=yuv420p", "-af", "aresample=48000",
             *venc("18", "medium"), "-c:a", "aac", "-ar", "48000", "-ac", "2",
             "-b:a", "192k", raw])
        bedmix = os.path.join(tmp, "bedmix.mp4")
        run([lf.FFMPEG, "-y", "-i", raw, "-stream_loop", "-1", "-i", BED,
             "-filter_complex",
             "[1:a]volume=0.07,lowpass=f=5000[bed];"
             "[0:a][bed]amix=inputs=2:duration=first:weights=1 0.25[a]",
             "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac",
             "-ar", "48000", "-ac", "2", "-b:a", "192k", "-shortest", bedmix])
        m = subprocess.run([lf.FFMPEG, "-hide_banner", "-i", bedmix, "-af",
                            "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                            "-f", "null", "-"], capture_output=True, text=True).stderr
        meas = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
        out = os.path.join(R, "ep1_master.mp4")
        run([lf.FFMPEG, "-y", "-i", bedmix, "-af",
             (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={meas['input_i']}:"
              f"measured_TP={meas['input_tp']}:measured_LRA={meas['input_lra']}:"
              f"measured_thresh={meas['input_thresh']}:offset={meas['target_offset']}:"
              f"linear=true,aresample=48000"),
             "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-b:a", "192k", out])

    with open(os.path.join(R, "ep1_master.chapters.txt"), "w") as f:
        f.write("# Paste into the YouTube description:\n")
        for t, name in chapters:
            f.write(f"{int(t // 60)}:{int(t % 60):02d} {name}\n")
    print(">> MASTER:", os.path.join(R, "ep1_master.mp4"))
    print(">> chapters:", chapters)


if __name__ == "__main__":
    main()
