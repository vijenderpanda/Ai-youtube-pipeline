#!/usr/bin/env python3
"""
One-command produce -> publish for the Lulla pipeline.

  Suno track (Chrome, done first)  ->  publish_song.py  ->  scheduled on YouTube
                                        ├─ assemble_video.py  (render + breathe)
                                        └─ youtube_upload.py  (upload + schedule + thumbnail + playlist)

Song generation is ALWAYS done by driving Suno in Chrome (see docs/WORKFLOW.md) — drop the
resulting mp3 into songs/ first, then run this.

Example:
  python3 scripts/publish_song.py \
    --audio songs/song02.mp3 --shots songs/02_shots.json \
    --title "Count the Fireflies 🌙 Calm Counting Song for Babies | Lulla's Moonlit Garden" \
    --desc-file songs/desc_02.txt \
    --tags "counting song for babies,numbers song,bedtime songs,lullaby,sleep music for kids" \
    --thumbnail assets/thumbnail/thumb02_final.jpg \
    --publish-at "2026-08-07T16:00:00+05:30"

  # render only (no upload):
  python3 scripts/publish_song.py --audio songs/song02.mp3 --shots songs/02_shots.json --title x --no-upload
"""
import argparse, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))

def run(cmd, label):
    print(f"\n=== {label} ===")
    print("›", " ".join(str(c) for c in cmd))
    if subprocess.run(cmd).returncode != 0:
        sys.exit(f"!! {label} failed")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--shots", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--desc-file", default="")
    ap.add_argument("--description", default="")
    ap.add_argument("--tags", default="")
    ap.add_argument("--thumbnail", default="")
    ap.add_argument("--publish-at", default="")
    ap.add_argument("--privacy", default="private")
    ap.add_argument("--playlist-id", default="")
    ap.add_argument("--category", default="10")   # 10=Music, 27=Education
    ap.add_argument("--breathe", default="0.05")
    ap.add_argument("--transition", default="1.2")
    ap.add_argument("--out", default="")
    ap.add_argument("--no-upload", action="store_true")
    # Ratchet upgrades (QUALITY-LEDGER §3): soft lyric overlays + branded bookends.
    ap.add_argument("--lyrics", default="", help="lyric/caption spec JSON (soft on-screen sing-along)")
    ap.add_argument("--channel", default="pip-moonlit-garden", help="slug for bookend lookup")
    ap.add_argument("--no-bookends", action="store_true",
                    help="skip the branded intro/outro stitch (default: on if they exist)")
    a = ap.parse_args()

    out = a.out or os.path.join("renders", os.path.splitext(os.path.basename(a.audio))[0] + ".mp4")

    run([sys.executable, os.path.join(HERE, "assemble_video.py"),
         "--shots", a.shots, "--audio", a.audio,
         "--breathe", a.breathe, "--transition", a.transition, "--out", out],
        "1/4 Render video")

    stage = out
    # 2/4 — soft sing-along lyric overlays (BRAND-BIBLE §7: hooks a toddler can echo).
    if a.lyrics:
        lyr = out.replace(".mp4", "_lyrics.mp4")
        run([sys.executable, os.path.join(HERE, "lulla_captions.py"),
             "--video", stage, "--spec", a.lyrics, "--out", lyr], "2/4 Lyric overlays")
        stage = lyr

    # 3/4 — stitch the branded intro + goodnight-ritual outro (auto-skips if absent).
    if not a.no_bookends:
        book = out.replace(".mp4", "_final.mp4")
        run([sys.executable, os.path.join(HERE, "add_bookends.py"),
             "--channel", a.channel, "--episode", stage, "--out", book], "3/4 Bookends")
        stage = book

    upload_file = stage
    if a.no_upload:
        print(f"\n>> Rendered (no upload): {upload_file}")
        return

    up = [sys.executable, os.path.join(HERE, "youtube_upload.py"),
          "--file", upload_file, "--title", a.title, "--tags", a.tags,
          "--category", a.category, "--privacy", a.privacy]
    if a.desc_file:
        up += ["--desc-file", a.desc_file]
    elif a.description:
        up += ["--description", a.description]
    if a.thumbnail:
        up += ["--thumbnail", a.thumbnail]
    if a.publish_at:
        up += ["--publish-at", a.publish_at]
    if a.playlist_id:
        up += ["--playlist-id", a.playlist_id]
    run(up, "4/4 Upload + schedule")

    print(f"\n>> DONE: produced + published  ({upload_file})")

if __name__ == "__main__":
    main()
