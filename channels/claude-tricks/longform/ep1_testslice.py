#!/usr/bin/env python3
"""
ep1_testslice.py — LONG-FORM EP1 test slice (0:00–~2:00), APPROVED scope.

Per-beat ElevenLabs VO (word timings kept per beat), still/tape visuals from the v4
primitives, karaoke captions in the low band, joined by assemble_longform's spine.
1080p only. No arm, no upload. Spends: ~6 short ElevenLabs calls.

Usage:  python3 channels/claude-tricks/longform/ep1_testslice.py
Output: channels/claude-tricks/renders/longform/ep1_testslice.mp4 (+ .contact.jpg)
"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CH = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(CH))
sys.path.insert(0, CH)
sys.path.insert(0, os.path.join(REPO, "scripts"))
import build_longform_segment as lf
import ep1_storyboard as sb
from eleven_vo import load_key, synth
from ffmpeg_util import venc

R = os.path.join(CH, "renders", "longform")
A = os.path.join(CH, "assets", "longform_ep1")
VOICE, STYLE = "ZZ5OIPIzxVJswEhc0UXt", 0.4
W, H, FPS = lf.W, lf.H, lf.FPS

BEATS = [
    # (key, vo text | None, lead-in silence s, visual fn -> saves 1920x1080 PNG or MP4)
    ("a1_listing", "That's a real app. On the real App Store.", 2.0, "listing"),
    ("a2_receipts", "Now look at the timestamps. Prompt sent, three oh four in the afternoon. "
                    "Submitted to Apple, six twelve. Three hours and eight minutes.", 0.2, "receipts"),
    ("a3_promise", "By the end of this video you'll know every step. Because I'm going to show "
                   "you all of it. Including the parts that broke.", 0.2, "host_wide"),
    ("promise_app", "One afternoon. One tool. Zero lines of code written by me. "
                    "This is the app it built.", 0.2, "tape_phone"),
    ("ch1_card", None, 1.8, "card1"),
    ("ch1_open", "MissNoMeetings started as a personal problem. My phone buries meeting "
                 "invites, and I kept missing calls. Not because I was busy. Because the "
                 "reminder fired on my laptop, in another room.", 0.2, "tape_pip"),
]


def run(cmd):
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)


def still_to_video(png, dur, out, push=1.04):
    """Hold a still with a slow push (scale drift), silent."""
    vf = (f"scale={W * 2}:{H * 2},zoompan=z='1+({push}-1)*on/({dur}*{FPS})':"
          f"x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d={int(dur * FPS)}:s={W}x{H}:fps={FPS},format=yuv420p")
    run([lf.FFMPEG, "-y", "-loop", "1", "-i", png, "-t", str(dur), "-vf", vf,
         *venc("18", "veryfast"), "-an", out])


def mux(video, wav, out, lead=0.0):
    af = f"adelay={int(lead * 1000)}|{int(lead * 1000)}," if lead > 0 else ""
    run([lf.FFMPEG, "-y", "-i", video, "-i", wav, "-filter_complex",
         f"[1:a]{af}apad[a]", "-map", "0:v", "-map", "[a]", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-shortest", out])


def captions_on(video, words, lead, out):
    caps = lf.words_to_captions([{"w": w["w"], "start": w["start"] + lead,
                                  "end": w["end"] + lead} for w in words])
    with tempfile.TemporaryDirectory() as tmp:
        from assemble_short import render_caption_pngs
        items = render_caption_pngs(caps, accent="E4C56B", size=72, tmp=tmp)
        lf.overlay_captions_at(video, items, lf.CAP_Y, out)


def make_visual(kind, png):
    if kind == "listing":
        sb.appstore_listing_still().save(png)
    elif kind == "receipts":
        sb.timestamp_card().save(png)
    elif kind == "host_wide":
        sb.leo_host("wide").save(png)
    elif kind == "card1":
        lf.chapter_card_still(1, "The Idea", png)
    elif kind in ("tape_phone", "tape_pip"):
        base = sb.demo_frame(12.5 if kind == "tape_phone" else 1.0)
        if kind == "tape_phone":
            base = lf.punch_in_frame(base, (1150, 60, 400, 960), zoom=1.0)
        im = sb.with_pip(base)
        im.save(png)
    else:
        raise SystemExit(f"unknown visual {kind}")


def main():
    os.makedirs(R, exist_ok=True)
    key = load_key()
    segs = []
    with tempfile.TemporaryDirectory() as tmp:
        for name, text, lead, kind in BEATS:
            png = os.path.join(tmp, f"{name}.png")
            make_visual(kind, png)
            seg = os.path.join(tmp, f"{name}.mp4")
            if text:
                wav = os.path.join(tmp, f"{name}.wav")
                synth(key, VOICE, text, wav, speed=1.0, style=STYLE)
                words = json.load(open(wav.rsplit(".", 1)[0] + ".words.json"))
                dur = lead + max(w["end"] for w in words) + 0.5
                vid = os.path.join(tmp, f"{name}_v.mp4")
                still_to_video(png, dur, vid)
                cap = os.path.join(tmp, f"{name}_c.mp4")
                captions_on(vid, words, lead, cap)
                mux(cap, wav, seg, lead=lead)
            else:
                still_to_video(png, lead, seg)
                run([lf.FFMPEG, "-y", "-i", seg, "-f", "lavfi", "-i",
                     "anullsrc=r=48000:cl=stereo", "-shortest", "-c:v", "copy",
                     "-c:a", "aac", os.path.join(tmp, f"{name}_a.mp4")])
                seg = os.path.join(tmp, f"{name}_a.mp4")
            segs.append({"file": seg, "title": name})

        # HARD-CUT join (the reference jump-cuts; assemble_longform's 2s xfade floor is
        # a compilation rule, wrong for a cold open). Concat -> two-pass loudnorm -14.
        out = os.path.join(R, "ep1_testslice.mp4")
        lst = os.path.join(tmp, "concat.txt")
        with open(lst, "w") as f:
            for s in segs:
                f.write(f"file '{s['file']}'\n")
        raw = os.path.join(tmp, "raw.mp4")
        run([lf.FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", lst,
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", raw])
        m = subprocess.run([lf.FFMPEG, "-hide_banner", "-i", raw, "-af",
                            "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                            "-f", "null", "-"], capture_output=True, text=True).stderr
        meas = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
        run([lf.FFMPEG, "-y", "-i", raw, "-af",
             (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={meas['input_i']}:"
              f"measured_TP={meas['input_tp']}:measured_LRA={meas['input_lra']}:"
              f"measured_thresh={meas['input_thresh']}:offset={meas['target_offset']}:linear=true"),
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", out])
    print(">> DONE:", out)


if __name__ == "__main__":
    main()
