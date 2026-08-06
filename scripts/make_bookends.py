#!/usr/bin/env python3
"""
Render Lulla's branded bookends → channels/pip-moonlit-garden/bookends/{intro,outro}.mp4
from the already-made sting mp3s (bookends/candidates/) + on-model scenes.

  intro  = establishing wide (slow zoom) + "Lulla's Moonlit Garden" title fading in,
           over the intro sting.
  outro  = the belly-hug / sleep scene, gently DIMMING to near-dark at the end
           (the signature "belly light softly dims, whispered Goodnight" ritual —
           BRAND-BIBLE §6), with a soft amber heart + "Goodnight" + a subscribe line,
           over the outro sting.

Once rendered, add_bookends.py picks them up automatically (channels/<slug>/bookends/
intro.mp4 + outro.mp4) and publish_song.py stitches them onto every episode.

Usage:
  python3 scripts/make_bookends.py           # renders both with defaults
  python3 scripts/make_bookends.py --intro-dur 8 --outro-dur 10
"""
import argparse, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from assemble_video import ken_burns                      # noqa: E402
from lulla_captions import render_line, overlay_timed     # noqa: E402

CH = "channels/pip-moonlit-garden"
SCENES = f"{CH}/assets/scenes"
BOOK = f"{CH}/bookends"


def run(cmd):
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)


def mux_sting(video, audio, out, fade_out_at, dim=False):
    """Mux a sting under the clip: audio fades in/out; optional video fade-to-dark end."""
    afade = f"[1:a]afade=t=in:st=0:d=1.2,afade=t=out:st={fade_out_at:.2f}:d=1.2[a]"
    if dim:
        # video dims to near-black over the last 2s (belly light going out)
        vfade = f"[0:v]fade=t=out:st={fade_out_at:.2f}:d=2.0:color=0x0A0A1A[v]"
        fc = f"{vfade};{afade}"
        vmap = "[v]"
    else:
        fc = afade
        vmap = "0:v"
    run(["ffmpeg", "-y", "-i", video, "-i", audio, "-filter_complex", fc,
         "-map", vmap, "-map", "[a]", "-c:v", "libx264", "-crf", "19",
         "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
         "-shortest", "-movflags", "+faststart", out])


def build(kind, scene, motion, sting, dur, lines, out, dim=False):
    tmp = tempfile.mkdtemp(prefix=f"lulla_{kind}_")
    bg = os.path.join(tmp, "bg.mp4")
    ken_burns(scene, dur, motion, bg)                      # silent Ken-Burns bg

    items = []
    for ln in lines:
        png = render_line(ln["text"], ln.get("size", 64), ln.get("pos", "center"),
                          ln.get("heart", False))
        # title/goodnight holds for the whole clip, gentle 1.4s fade in and out
        items.append((png, ln.get("start", 0.6), ln.get("end", dur - 0.4),
                      ln.get("fade", 1.4)))
    titled = os.path.join(tmp, "titled.mp4")
    overlay_timed(bg, items, titled)

    os.makedirs(BOOK, exist_ok=True)
    mux_sting(titled, sting, out, fade_out_at=max(0.1, dur - 1.4), dim=dim)
    print(f">> {kind} → {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--intro-dur", type=float, default=8.0)
    ap.add_argument("--outro-dur", type=float, default=10.0)
    ap.add_argument("--intro-sting", default=f"{BOOK}/candidates/lulla_intro_A_0-19.mp3")
    ap.add_argument("--outro-sting", default=f"{BOOK}/candidates/lulla_outro_A_0-17.mp3")
    a = ap.parse_args()

    build("intro", f"{SCENES}/lib13_wide_0.jpg", "zoom_in", a.intro_sting, a.intro_dur,
          [{"text": "Lulla's Moonlit Garden", "size": 76, "pos": "upper"},
           {"text": "a soft song for sleepy little ones", "size": 40, "pos": "lower",
            "start": 1.4}],
          f"{BOOK}/intro.mp4")

    build("outro", f"{SCENES}/s04_sleep_0.jpg", "zoom_in", a.outro_sting, a.outro_dur,
          [{"text": "Goodnight", "size": 84, "pos": "center", "heart": True},
           {"text": "New calm songs every week  ·  Subscribe", "size": 38, "pos": "lower",
            "start": 1.4}],
          f"{BOOK}/outro.mp4", dim=True)

    print("\n>> Bookends ready. add_bookends.py will now find them automatically.")


if __name__ == "__main__":
    main()
