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


def talking_pip(base_video, host_clip, dur, out, tmp):
    """Circle-masked TALKING host over the tape (lip-synced to the section VO)."""
    mp, rp = circle_mask_pngs(tmp)
    x = W - PIP_D - 56
    y = H - PIP_D - 72
    run([lf.FFMPEG, "-y", "-i", base_video, "-i", host_clip, "-i", mp, "-i", rp,
         "-filter_complex",
         (f"[1:v]fps={FPS},crop=w='min(iw\\,ih)':h='min(iw\\,ih)':x='(iw-min(iw\\,ih))/2+120':y=0,"
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
            talking_pip(cur, pip, total, p2, tmp)
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
    s = os.path.join(tmp, f"card{idx}_s.mp4")
    run([lf.FFMPEG, "-y", "-i", v, "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
         "-shortest", "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-ac", "2", s])
    return s, dur


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
        SIM = os.path.join(A, "sim_usage.mov")
        GITLOG = os.path.join(A, "tape_gitlog.mp4")
        CODE = os.path.join(A, "tape_code.mp4")
        TRANS = os.path.join(A, "tape_transcript.mp4")

        listing_png = os.path.join(tmp, "listing.png")
        sb.appstore_listing_still().save(listing_png)

        # ---- HOOK (host full + cutaways on lines 2-3, audio = clip's own) ----
        hv, hdur = host_full_section("hook", tmp, captions=False)
        times, _ = line_times("hook", lead=0.0, tail=0.0)
        (l2s, l2e), (l3s, _) = times[1], times[2]
        cut1 = os.path.join(tmp, "hook_cut1.mp4"); still_slice(listing_png, l2e - l2s, cut1, 200)
        rc_end = l3s + 3.2
        cut2 = os.path.join(tmp, "hook_cut2.mp4"); receipts_real(rc_end - l2e, cut2, tmp)
        base = os.path.join(tmp, "hook_over.mp4")
        run([lf.FFMPEG, "-y", "-i", hv, "-i", cut1, "-i", cut2, "-filter_complex",
             f"[1:v]setpts=PTS+{l2s}/TB[c1];[2:v]setpts=PTS+{l2e}/TB[c2];"
             f"[0:v][c1]overlay=eof_action=pass:enable='between(t,{l2s},{l2e})'[x1];"
             f"[x1][c2]overlay=eof_action=pass:enable='between(t,{l2e},{rc_end})'[v]",
             "-map", "[v]", "-map", "0:a", *venc("18", "veryfast"),
             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", base])
        hc = os.path.join(tmp, "hook_cap.mp4"); captions_on(base, words_of("hook"), 0.0, hc)
        hf = os.path.join(tmp, "hook_seg.mp4")
        run([lf.FFMPEG, "-y", "-i", hc, "-i", base, "-map", "0:v", "-map", "1:a",
             "-c:v", "copy", "-c:a", "copy", hf])
        add(hf, hdur, chapter="Hook")

        # ---- CH1 The Idea ----
        s, d = card(tmp, 1, "The Idea"); add(s, d, chapter="The Idea")
        seg, d = build_section("ch1", [
            lambda du, o: conform(DEMO, 0.0, du, o),
            lambda du, o: conform(CODE, 0.0, du, o, drift=False),
            lambda du, o: conform(SIM, 4.0, du, o),
        ], tmp, pip=os.path.join(A, "host_ch1.mp4"))
        add(seg, d)

        # ---- CH2 The Build ----
        s, d = card(tmp, 2, "The Build"); add(s, d, chapter="The Build")
        seg, d = build_section("ch2", [
            lambda du, o: conform(GITLOG, 0.0, du, o, drift=False),
            lambda du, o: conform(CODE, 4.0, du, o, drift=False),
            lambda du, o: conform(SIM, 20.0, du, o),
            lambda du, o: conform(TRANS, 0.0, du, o, drift=False),
            lambda du, o: conform(GITLOG, 8.0, du, o, drift=False),
        ], tmp, pip=os.path.join(A, "host_ch2.mp4"))
        add(seg, d)

        # ---- CH3 On My iPhone ----
        s, d = card(tmp, 3, "On My iPhone"); add(s, d, chapter="On My iPhone")
        seg, d = build_section("ch3", [
            lambda du, o: conform(SIM, 30.0, du, o),
            lambda du, o: conform(DEMO, 2.0, du, o),
            lambda du, o: conform(DEMO, 8.0, du, o),
            lambda du, o: conform(TRANS, 8.0, du, o, drift=False),
        ], tmp, pip=os.path.join(A, "host_ch3.mp4"))
        add(seg, d)

        # ---- MID-ROLL (host full) ----
        seg, d = host_full_section("midroll", tmp); add(seg, d, chapter="Why Now")

        # ---- CH4 The App Store ----
        s, d = card(tmp, 4, "The App Store"); add(s, d, chapter="The App Store")
        seg, d = build_section("ch4", [
            lambda du, o: conform(TRANS, 14.0, du, o, drift=False),
            lambda du, o: still_slice(listing_png, du, o, 150),
            lambda du, o: receipts_real(du, o, tmp),
        ], tmp, pip=os.path.join(A, "host_ch4.mp4"), captions=True)
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

        # ---- OUTRO ----
        seg, d = host_full_section("outro", tmp); add(seg, d, chapter="What's Next")

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
