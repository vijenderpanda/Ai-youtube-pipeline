#!/usr/bin/env python3
"""
ep1_testslice.py — LONG-FORM EP1 test slice v2 (0:00–~2:00). APPROVED scope.

v2 (VJ feedback 2026-08-25): NO static frames — every beat moves; music bed added;
receipts-card caption collision fixed (captions OFF there, the card IS the text).
  a1  listing pan (pseudo-scroll)          + VO + captions
  a2  receipts COUNT-UP animation          + VO, NO captions
  a3  HeyGen Avatar IV host clip (talking) + captions       <- real motion host
  a4  real tape + eased punch-in + PiP     + VO + captions
  c1  chapter card push
  b1  real tape slow drift + PiP           + VO + captions
Bed: bed_active.mp3 looped, sidechain-ducked under VO, then two-pass loudnorm -14.

Usage:  python3 channels/claude-tricks/longform/ep1_testslice.py
Output: channels/claude-tricks/renders/longform/ep1_testslice.mp4
"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CH = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(CH))
sys.path.insert(0, CH)
sys.path.insert(0, os.path.join(REPO, "scripts"))
import build_longform_segment as lf
import ep1_storyboard as sb
from eleven_vo import load_key, synth, synth_lines
from ffmpeg_util import venc
from PIL import Image

R = os.path.join(CH, "renders", "longform")
A = os.path.join(CH, "assets", "longform_ep1")
DEMO = os.path.join(A, "mnm_demo.mov")
# v3: dedicated LONG-FORM bed (Suno "Golden Felt Drift", instrumental) — the shorts
# beds (bed_active/bed_webtour) stay shorts-only per VJ.
BED = os.path.join(CH, "assets", "music", "lf_bed_golden_felt.mp3")
HEYGEN_A3 = os.path.join(A, "a3_heygen.mp4")
VOICE, STYLE = "ZZ5OIPIzxVJswEhc0UXt", 0.4
W, H, FPS = lf.W, lf.H, lf.FPS


def run(cmd):
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)


def vo(key, name, text, tmp):
    wav = os.path.join(tmp, f"{name}.wav")
    synth(key, VOICE, text, wav, speed=1.0, style=STYLE)
    words = json.load(open(wav.rsplit(".", 1)[0] + ".words.json"))
    return wav, words, max(w["end"] for w in words)


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
         f"[1:a]{af}apad[a]", "-map", "0:v", "-map", "[a]", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-shortest", out])


def pan_still(png, dur, out, drift_px=140):
    """Motion for card-type beats: slow vertical drift on an oversized still."""
    up = round(H * 1.18)
    vf = (f"scale=-2:{up},crop={W}:{H}:x=(iw-{W})/2:y='min({drift_px}*t/{dur},ih-{H})',"
          f"fps={FPS},format=yuv420p")
    run([lf.FFMPEG, "-y", "-loop", "1", "-i", png, "-t", str(dur), "-vf", vf,
         *venc("18", "veryfast"), "-an", out])


def pip_overlay(video, out):
    pip_png = os.path.join(tempfile.gettempdir(), "lf_pip.png")
    sb.leo_pip().save(pip_png)
    pw = Image.open(pip_png).width
    run([lf.FFMPEG, "-y", "-i", video, "-i", pip_png, "-filter_complex",
         f"[0:v][1:v]overlay=x={W - pw - 48}:y={H - pw - 64}[v]", "-map", "[v]",
         *venc("18", "veryfast"), "-pix_fmt", "yuv420p", "-an", out])


def receipts_countup(dur, out, tmp):
    """Animated receipts: timestamps slide-fade in, 3H 08M counts up from 0."""
    from PIL import ImageDraw, ImageFont
    frames_dir = os.path.join(tmp, "rc_frames"); os.makedirs(frames_dir, exist_ok=True)
    f_ts = ImageFont.truetype(lf.FONT_ANTON, 76)
    f_big = ImageFont.truetype(lf.FONT_ANTON, 150)
    n = int(dur * FPS)
    total_min = 188  # 3h08m — TBD verify against session log before production
    for i in range(n):
        t = i / FPS
        im = Image.new("RGB", (W, H), lf.INK)
        d = ImageDraw.Draw(im)
        a1 = min(1.0, max(0.0, t / 0.25))
        a2 = min(1.0, max(0.0, (t - 0.35) / 0.25))
        c1 = tuple(int(210 * a1) for _ in range(3))
        c2 = tuple(int(210 * a2) for _ in range(3))
        d.text((330 - int(40 * (1 - a1)), 300), "3:04 PM  prompt sent", font=f_ts, fill=c1)
        d.text((330 - int(40 * (1 - a2)), 430), "6:12 PM  submitted to Apple", font=f_ts, fill=c2)
        k = min(1.0, max(0.0, (t - 0.7) / 0.6))
        mins = int(total_min * (1 - (1 - k) ** 3))
        txt = f"{mins // 60}H {mins % 60:02d}M"
        tw2 = d.textlength(txt, font=f_big)
        d.text(((W - tw2) / 2, 620), txt, font=f_big, fill=lf.ACCENT)
        im.save(os.path.join(frames_dir, f"f{i:04d}.png"))
    run([lf.FFMPEG, "-y", "-framerate", str(FPS), "-i",
         os.path.join(frames_dir, "f%04d.png"), *venc("18", "veryfast"),
         "-pix_fmt", "yuv420p", "-an", out])


def tape_motion(ss, dur, out, rect=None, drift=True):
    """Real tape (conformed 1920x1080) with an eased punch-in (rect) or slow drift."""
    if rect:
        seg = os.path.join(os.path.dirname(out), "t_" + os.path.basename(out))
        run([lf.FFMPEG, "-y", "-ss", str(ss), "-i", DEMO, "-t", str(dur),
             "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
                    f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={FPS}",
             *venc("18", "veryfast"), "-an", seg])
        lf.render_punch_in(seg, rect, dur, out)
    else:
        z = f"1+0.06*t/{dur}"
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
              f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,"
              f"scale=trunc(iw*({z})/2)*2:trunc(ih*({z})/2)*2:eval=frame,"
              f"crop={W}:{H},fps={FPS}")
        run([lf.FFMPEG, "-y", "-ss", str(ss), "-i", DEMO, "-t", str(dur),
             "-vf", vf, *venc("18", "veryfast"), "-an", out])


def main():
    os.makedirs(R, exist_ok=True)
    key = load_key()
    segs = []
    with tempfile.TemporaryDirectory() as tmp:
        def add(seg): segs.append(seg)

        # COLD OPEN v4 (VJ + retention laws: knee at 5-7s, no dead air, proof + energy
        # in second one). ONE continuous VO take, NEVER sliced — the VIDEO cuts to the
        # VO's line boundaries instead, so there are zero audio joins to glitch.
        cold = synth_lines(key, VOICE,
            ["This is a real app. Live on the App Store. And it took three hours.",
             "Prompt sent at three oh four. Submitted at six twelve. "
             "Zero lines of code written by me."],
            os.path.join(tmp, "cold.mp3"), brk="0.3s", style=0.55)
        TEMPO = 1.06  # energy knob — speed the whole take, keep pitch
        cold_wav = os.path.join(tmp, "cold.wav")
        run([lf.FFMPEG, "-y", "-i", cold["audio"], "-af", f"atempo={TEMPO}",
             "-ar", "48000", "-ac", "2", cold_wav])
        LEAD = 0.3
        cw = [{"w": x["w"], "start": round(x["start"] / TEMPO + LEAD, 2),
               "end": round(x["end"] / TEMPO + LEAD, 2)} for x in cold["words"]]
        b0, b1_ = cold["line_boundaries"]
        cut1 = (b0["end"] + b1_["start"]) / 2 / TEMPO + LEAD
        cold_end = b1_["end"] / TEMPO + LEAD + 0.35

        # video track: fast listing pan (0..cut1), fast receipts (cut1..end)
        png = os.path.join(tmp, "a1.png"); sb.appstore_listing_still().save(png)
        v1 = os.path.join(tmp, "a1_v.mp4"); pan_still(png, cut1, v1, drift_px=260)
        v2 = os.path.join(tmp, "a2_v.mp4")
        receipts_countup(cold_end - cut1, v2, tmp)
        cold_v = os.path.join(tmp, "cold_v.mp4")
        lstc = os.path.join(tmp, "coldcat.txt")
        open(lstc, "w").write(f"file '{v1}'\nfile '{v2}'\n")
        run([lf.FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", lstc,
             "-vf", f"fps={FPS},format=yuv420p", *venc("18", "veryfast"), "-an", cold_v])
        # captions once over the whole cold video (absolute times) — skip during the
        # receipts card (its own text IS the payload): only line-1 words get captions
        w1 = [w for w in cw if w["end"] <= cut1]
        cold_c = os.path.join(tmp, "cold_c.mp4"); captions_on(cold_v, w1, 0.0, cold_c)
        cold_seg = os.path.join(tmp, "cold.mp4"); mux(cold_c, cold_wav, cold_seg, lead=LEAD)
        add(cold_seg)

        # a3 — HeyGen talking host (VO embedded in clip) + captions
        if not os.path.exists(HEYGEN_A3):
            raise SystemExit("!! a3_heygen.mp4 missing — generate it first")
        a3w = json.load(open(os.path.join(A, "a3_promise.words.json")))
        v = os.path.join(tmp, "a3_v.mp4")
        run([lf.FFMPEG, "-y", "-i", HEYGEN_A3, "-vf",
             f"scale={W}:{H}:flags=lanczos,fps={FPS}", *venc("18", "veryfast"),
             "-c:a", "aac", "-b:a", "192k", v])
        s = os.path.join(tmp, "a3.mp4"); captions_on(v, a3w, 0.0, s)
        run([lf.FFMPEG, "-y", "-i", s, "-i", v, "-map", "0:v", "-map", "1:a",
             "-c:v", "copy", "-c:a", "copy", os.path.join(tmp, "a3f.mp4")])
        add(os.path.join(tmp, "a3f.mp4"))

        # a4 — promise over real tape, eased punch-in to the phone, PiP
        wav, words, vend = vo(key, "a4",
            "One afternoon. One tool. Zero lines of code written by me. "
            "This is the app it built.", tmp)
        lead, dur = 0.2, 0.2 + vend + 0.5
        # phone fills frame height already — punch-in degenerates; use drift
        v = os.path.join(tmp, "a4_v.mp4"); tape_motion(8.0, dur, v)
        p = os.path.join(tmp, "a4_p.mp4"); pip_overlay(v, p)
        c = os.path.join(tmp, "a4_c.mp4"); captions_on(p, words, lead, c)
        s = os.path.join(tmp, "a4.mp4"); mux(c, wav, s, lead); add(s)

        # c1 — chapter card (pan drift)
        png = os.path.join(tmp, "c1.png"); lf.chapter_card_still(1, "The Idea", png)
        v = os.path.join(tmp, "c1_v.mp4"); pan_still(png, 1.8, v, drift_px=60)
        s = os.path.join(tmp, "c1.mp4")
        run([lf.FFMPEG, "-y", "-i", v, "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
             "-shortest", "-c:v", "copy", "-c:a", "aac", s]); add(s)

        # b1 — chapter 1 open over real tape, slow drift, PiP
        wav, words, vend = vo(key, "b1",
            "MissNoMeetings started as a personal problem. My phone buries meeting "
            "invites, and I kept missing calls. Not because I was busy. Because the "
            "reminder fired on my laptop, in another room.", tmp)
        lead, dur = 0.2, 0.2 + vend + 0.5
        v = os.path.join(tmp, "b1_v.mp4"); tape_motion(0.0, min(dur, 15.5), v)
        p = os.path.join(tmp, "b1_p.mp4"); pip_overlay(v, p)
        c = os.path.join(tmp, "b1_c.mp4"); captions_on(p, words, lead, c)
        s = os.path.join(tmp, "b1.mp4"); mux(c, wav, s, lead); add(s)

        # join hard-cut, then bed duck + two-pass loudnorm
        lst = os.path.join(tmp, "concat.txt")
        with open(lst, "w") as f:
            for s in segs:
                f.write(f"file '{s}'\n")
        raw = os.path.join(tmp, "raw.mp4")
        run([lf.FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", lst,
             "-vf", f"fps={FPS},format=yuv420p", "-af", "aresample=48000",
             *venc("18", "medium"), "-c:a", "aac", "-b:a", "192k", raw])
        bedmix = os.path.join(tmp, "bedmix.mp4")
        run([lf.FFMPEG, "-y", "-i", raw, "-stream_loop", "-1", "-i", BED,
             "-filter_complex",
             "[1:a]volume=0.13[bed];"
             "[bed][0:a]sidechaincompress=threshold=0.015:ratio=20:attack=25:release=500[duck];"
             "[0:a][duck]amix=inputs=2:duration=first:weights=1 0.35[a]",
             "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
             "-shortest", bedmix])
        m = subprocess.run([lf.FFMPEG, "-hide_banner", "-i", bedmix, "-af",
                            "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                            "-f", "null", "-"], capture_output=True, text=True).stderr
        meas = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
        out = os.path.join(R, "ep1_testslice.mp4")
        run([lf.FFMPEG, "-y", "-i", bedmix, "-af",
             (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={meas['input_i']}:"
              f"measured_TP={meas['input_tp']}:measured_LRA={meas['input_lra']}:"
              f"measured_thresh={meas['input_thresh']}:offset={meas['target_offset']}:linear=true"),
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", out])
    print(">> DONE:", out)


if __name__ == "__main__":
    main()
