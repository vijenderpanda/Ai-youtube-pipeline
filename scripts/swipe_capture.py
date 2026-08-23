#!/usr/bin/env python3
"""
Download a YouTube Short (or any yt-dlp URL) as a raw learning asset and
build a labeled contact sheet from it.

Usage:
    python scripts/swipe_capture.py <url> [--out-dir research/learning-assets]
                                     [--fps 1.0] [--cols 10] [--keep-frames]

Output layout (per video, gitignored by *.mp4/*.webm/*.jpg/*.png rules):
    <out-dir>/<video_id>_<slug>/
        raw.<ext>            the downloaded video
        info.json            title/uploader/duration/fps/dims/audio-lang
        contact_sheet.jpg
        contact_sheet.pdf
        frames/              only kept with --keep-frames
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _ytdlp():
    for cand in (shutil.which("yt-dlp"),
                 Path.home() / "miniconda3/bin/yt-dlp",
                 "/opt/homebrew/bin/yt-dlp"):
        if cand and Path(cand).exists():
            return str(cand)
    return [sys.executable, "-m", "yt_dlp"]


def _ytdlp_cmd(*args):
    y = _ytdlp()
    return (y if isinstance(y, list) else [y]) + list(args)


def slugify(text, max_len=40):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return s[:max_len].rstrip("-") or "untitled"


def run(cmd):
    subprocess.run(cmd, check=True)


def fetch_info(url):
    out = subprocess.run(_ytdlp_cmd("-j", url), check=True, capture_output=True, text=True)
    return json.loads(out.stdout)


def download_video(url, dest_dir):
    run(_ytdlp_cmd("-f", "bv*+ba/b", "-o", str(dest_dir / "raw.%(ext)s"), url))
    matches = list(dest_dir.glob("raw.*"))
    if not matches:
        raise RuntimeError("yt-dlp did not produce a raw.* file")
    return matches[0]


def extract_frames(video_path, frames_dir, fps):
    frames_dir.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", f"fps={fps},scale=270:480",
        str(frames_dir / "f_%04d.png"),
        "-hide_banner", "-loglevel", "error",
    ])
    return sorted(frames_dir.glob("f_*.png"))


def build_contact_sheet(frame_files, fps, cols, out_jpg, out_pdf):
    n = len(frame_files)
    rows = (n + cols - 1) // cols
    thumb_w, thumb_h = 270, 480
    pad = 6
    label_h = 22
    cell_w = thumb_w + pad * 2
    cell_h = thumb_h + pad * 2 + label_h

    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "black")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    except Exception:
        font = ImageFont.load_default()

    for i, f in enumerate(frame_files):
        r, c = divmod(i, cols)
        im = Image.open(f)
        x = c * cell_w + pad
        y = r * cell_h + pad
        sheet.paste(im, (x, y))
        sec = i / fps
        label = f"t={sec:05.2f}s"
        draw.rectangle([x, y + thumb_h, x + thumb_w, y + thumb_h + label_h], fill=(20, 20, 20))
        draw.text((x + 4, y + thumb_h + 2), label, fill="yellow", font=font)

    sheet.save(out_jpg, quality=90)
    sheet.convert("RGB").save(out_pdf)
    return sheet.size


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--out-dir", default="research/learning-assets")
    ap.add_argument("--fps", type=float, default=1.0, help="sample rate for contact sheet frames")
    ap.add_argument("--cols", type=int, default=10)
    ap.add_argument("--keep-frames", action="store_true", help="keep the frames/ dir (deleted by default)")
    args = ap.parse_args()

    print(f"[1/4] Fetching metadata for {args.url}")
    info = fetch_info(args.url)
    video_id = info.get("id", "unknown")
    title = info.get("title", "untitled")
    dest = Path(args.out_dir) / f"{video_id}_{slugify(title)}"
    dest.mkdir(parents=True, exist_ok=True)

    (dest / "info.json").write_text(json.dumps({
        "id": video_id,
        "title": title,
        "uploader": info.get("uploader"),
        "url": info.get("webpage_url", args.url),
        "duration_s": info.get("duration"),
        "fps": info.get("fps"),
        "width": info.get("width"),
        "height": info.get("height"),
        "audio_language": info.get("language"),
    }, indent=2))

    print(f"[2/4] Downloading raw video -> {dest}")
    video_path = download_video(args.url, dest)

    print(f"[3/4] Extracting frames @ {args.fps}fps")
    frames_dir = dest / "frames"
    frame_files = extract_frames(video_path, frames_dir, args.fps)

    print(f"[4/4] Building contact sheet ({len(frame_files)} frames)")
    size = build_contact_sheet(
        frame_files, args.fps, args.cols,
        dest / "contact_sheet.jpg", dest / "contact_sheet.pdf",
    )

    if not args.keep_frames:
        shutil.rmtree(frames_dir)

    print(json.dumps({
        "dest": str(dest),
        "video": str(video_path),
        "contact_sheet_jpg": str(dest / "contact_sheet.jpg"),
        "contact_sheet_pdf": str(dest / "contact_sheet.pdf"),
        "sheet_size": size,
        "frame_count": len(frame_files),
    }, indent=2))


if __name__ == "__main__":
    main()
