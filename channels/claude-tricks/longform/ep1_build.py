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
PIP_FACE = {"ch1": (870, 400), "ch2": (780, 380), "ch3": (1000, 400), "ch4": (900, 400)}
PIP_SQ = 720


def talking_pip(base_video, host_clip, dur, out, tmp, face=(960, 400)):
    """Circle-masked TALKING host over the tape (lip-synced to the section VO)."""
    mp, rp = circle_mask_pngs(tmp)
    x = W - PIP_D - 56
    y = H - PIP_D - 72
    cx, cy = face
    cx0 = max(0, min(1920 - PIP_SQ, cx - PIP_SQ // 2))
    cy0 = max(0, min(1080 - PIP_SQ, cy - PIP_SQ // 2))
    run([lf.FFMPEG, "-y", "-i", base_video, "-i", host_clip, "-i", mp, "-i", rp,
         "-filter_complex",
         (f"[1:v]fps={FPS},crop={PIP_SQ}:{PIP_SQ}:{cx0}:{cy0},"
          f"scale={PIP_D}:{PIP_D}[pv];"
          f"[2:v]loop=-1:1,scale={PIP_D}:{PIP_D},format=gray[msk];"
          f"[pv][msk]alphamerge[pa];"
          f"[0:v][pa]overlay=x={x}:y={y}:eof_action=repeat[b];"
          f"[3:v]loop=-1:1[ring];[b][ring]overlay=x={x - 8}:y={y - 8}:eof_action=repeat[v]"),
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


def build_section(name, visuals, tmp, pip=None, captions=True, lead=0.3):
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
        if os.path.exists(pip):
            talking_pip(cur, pip, total, p2, tmp,
                        face=PIP_FACE.get(name, (960, 400)))
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
    f_t = ImageFont.truetype(lf.FONT_ANTON, 92)
    f_s = ImageFont.truetype(lf.FONT_ANTON, 44)
    d.rectangle([90, 96, 104, 210], fill=lf.ACCENT + (255,))
    d.text((128, 100), title, font=f_t, fill=(255, 255, 255, 255),
           stroke_width=3, stroke_fill=(0, 0, 0, 160))
    d.text((130, 214), sub, font=f_s, fill=lf.ACCENT + (255,),
           stroke_width=2, stroke_fill=(0, 0, 0, 160))
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



MON_SCR = (150, 120, 1330, 800)   # x, y, w, h of the monitor screen hole


def make_monitor_assets(tmp):
    """Studio backdrop + monitor bezel (transparent screen hole) for the explain stage."""
    bgp = os.path.join(tmp, "stage_bg.png")
    bg = Image.new("RGB", (W, H), (13, 15, 20))
    d = ImageDraw.Draw(bg)
    for r in range(900, 0, -6):
        a = int(26 * (r / 900))
        d.ellipse([180 - r, H - 160 - r, 180 + r, H - 160 + r],
                  fill=(13 + a, 13 + int(a * 0.86), 20 + int(a * 0.35)))
    bg.save(bgp)
    bzp = os.path.join(tmp, "monitor_bezel.png")
    x, y, w2, h2 = MON_SCR
    bz = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(bz)
    d.rounded_rectangle([x - 34, y - 34, x + w2 + 34, y + h2 + 34], radius=30,
                        fill=(24, 27, 34, 255), outline=(70, 76, 88, 255), width=3)
    d.rounded_rectangle([x - 4, y - 4, x + w2 + 4, y + h2 + 4], radius=8,
                        fill=(0, 0, 0, 255))
    d.rectangle([x, y, x + w2, y + h2], fill=(0, 0, 0, 0))
    cx = x + w2 // 2
    d.polygon([(cx - 90, y + h2 + 34), (cx + 90, y + h2 + 34),
               (cx + 130, y + h2 + 110), (cx - 130, y + h2 + 110)], fill=(30, 33, 40, 255))
    d.rounded_rectangle([cx - 240, y + h2 + 104, cx + 240, y + h2 + 128], radius=12,
                        fill=(38, 42, 50, 255))
    bz.save(bzp)
    return bgp, bzp


def monitor_stage(src, ss, dur, out, tmp, cutout="medium", ch=None):
    """VJ 2026-08-25: explaining-pose host needs something to explain AT — a monitor
    in front of him. bg -> tape in monitor -> bezel -> host cutout (gaze at screen)."""
    bgp, bzp = make_monitor_assets(tmp)
    if ch is None:
        ch = 600 if cutout == "wide" else 760  # wide cutout carries its own desk
    png = os.path.join(A, f"cutout_{cutout}.png")
    cw = round(Image.open(png).width * ch / Image.open(png).height)
    x, y, w2, h2 = MON_SCR
    run([lf.FFMPEG, "-y", "-loop", "1", "-i", bgp, "-ss", str(ss), "-i", src,
         "-i", bzp, "-i", png, "-t", str(dur), "-filter_complex",
         (f"[1:v]fps={FPS},scale={w2}:{h2}:force_original_aspect_ratio=decrease,"
          f"pad={w2}:{h2}:(ow-iw)/2:(oh-ih)/2:color=black[tv];"
          f"[0:v][tv]overlay={x}:{y}[s1];[s1][2:v]overlay=0:0[s2];"
          f"[3:v]scale={cw}:{ch}[hc];[s2][hc]overlay=x={W - cw + 60}:y={H - ch}[v]"),
         "-map", "[v]", *venc("18", "veryfast"), "-pix_fmt", "yuv420p", "-an", out])


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

        # ---- HOOK v6 (host-free, vision cut): listing -> receipts -> sim punch ----
        times, total = line_times("hook2")
        v1 = os.path.join(tmp, "hk1.mp4"); still_slice(listing_png, times[0][1] - times[0][0], v1, 220)
        v2 = os.path.join(tmp, "hk2.mp4"); receipts_real(times[1][1] - times[1][0], v2, tmp)
        v3 = os.path.join(tmp, "hk3.mp4"); conform(SIM, 8.0, times[2][1] - times[2][0], v3)
        hb = os.path.join(tmp, "hook_base.mp4"); concat_slices([v1, v2, v3], hb, tmp, "hook")
        hw = [w for w in words_of("hook2")]
        hc = os.path.join(tmp, "hook_cap.mp4")
        capw = [w for w in hw if not (times[1][0] - 0.3 <= w["start"] <= times[1][1] - 0.3)]
        captions_on(hb, capw, 0.3, hc)
        hf = os.path.join(tmp, "hook_seg.mp4"); mux(hc, vo_wav("hook2", tmp), hf, lead=0.3)
        add(hf, total, chapter="Hook")

        # ---- RELATE (curiosity b-roll — "have you tried AI...", VJ positioning) ----
        times, total = line_times("relate")
        POPQ = [("TRIED AGENTS?", "workflows - side hustles - gen AI"),
                ("GAVE UP?", "the back-and-forth loop"),
                (None, None), (None, None)]
        rv = []
        for i, ((t0, t1), src) in enumerate(zip(times, [BR1, BR2, GITLOG, LIVE])):
            base_v = os.path.join(tmp, f"rl{i}.mp4")
            monitor_stage(src, 0.0 if i != 3 else 1.0, t1 - t0, base_v, tmp,
                          cutout="medium" if i % 2 == 0 else "wide")
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
            lambda du, o: monitor_stage(DEMO, 0.0, du, o, tmp, cutout="medium"),
            lambda du, o: monitor_stage(CODE, 0.0, du, o, tmp, cutout="wide"),
            lambda du, o: monitor_stage(LIVE, 2.0, du, o, tmp, cutout="medium"),
        ], tmp, pip=None)
        add(seg, d)

        # ---- CH2 The Build ----
        s, d = card(tmp, 2, "The Build"); add(s, d, chapter="The Build")
        seg, d = build_section("ch2", [
            lambda du, o: glass_conform(GITLOG, 0.0, du, o, tmp),
            lambda du, o: glass_conform(CODE, 4.0, du, o, tmp),
            lambda du, o: glass_conform(SIM, 20.0, du, o, tmp),
            lambda du, o: glass_conform(TRANS, 0.0, du, o, tmp),
            lambda du, o: glass_conform(GITLOG, 8.0, du, o, tmp),
        ], tmp, pip=None)
        add(seg, d)

        # ---- CH3 On My iPhone ----
        s, d = card(tmp, 3, "On My iPhone"); add(s, d, chapter="On My iPhone")
        seg, d = build_section("ch3", [
            lambda du, o: monitor_stage(LIVE, 30.0, du, o, tmp, cutout="wide"),
            lambda du, o: monitor_stage(DEMO, 2.0, du, o, tmp, cutout="medium"),
            lambda du, o: monitor_stage(DEMO, 8.0, du, o, tmp, cutout="wide"),
            lambda du, o: monitor_stage(TRANS, 8.0, du, o, tmp, cutout="medium"),
        ], tmp, pip=None)
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
            base_v = os.path.join(tmp, f"ft{i}.mp4"); glass_conform(LIVE, ss, t1 - t0, base_v, tmp)
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

        # ---- MID-ROLL (host-free: pop-text kinetics) ----
        times, total = line_times("midroll")
        POPS = [("AGENTS", "the one-word answer"),
                ("BUILDS. RUNS. REPAIRS.", "it reads its own errors"),
                ("DESCRIBE. TEST.", "your whole job now")]
        ms = []
        for i, ((t0, t1), (t_, sub)) in enumerate(zip(times, POPS)):
            png = os.path.join(tmp, f"mp{i}.png"); lf.pop_text_still(t_, png, sub=sub)
            v = os.path.join(tmp, f"mpv{i}.mp4"); still_slice(png, t1 - t0, v, drift_px=60)
            ms.append(v)
        mb = os.path.join(tmp, "mid_base.mp4"); concat_slices(ms, mb, tmp, "mid")
        mseg0 = os.path.join(tmp, "mid_seg0.mp4"); mux(mb, vo_wav("midroll", tmp), mseg0, lead=0.3)
        mseg = os.path.join(tmp, "mid_seg.mp4")
        sfx_mix(mseg0, [(t0, "whoosh") for t0, _ in times], mseg)
        add(mseg, total, chapter="Why Now")

        # ---- CH4 The App Store ----
        s, d = card(tmp, 5, "The App Store"); add(s, d, chapter="The App Store")
        seg, d = build_section("ch4", [
            lambda du, o: glass_conform(TRANS, 14.0, du, o, tmp),
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
