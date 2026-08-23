---
name: swipe-capture
description: Download a YouTube Short (or any yt-dlp-supported URL) as a raw learning asset and generate a labeled contact sheet from it, for studying another creator's cuts/pacing/style. Use when the user pastes a short/video URL and asks to analyze it, study its style, get its frames, or build a contact sheet — or explicitly invokes /swipe-capture.
---

# Swipe capture — reference-short contact sheets

Purpose: VJ studies other creators' Shorts (pacing, hook style, cut rhythm) by
pulling the raw file plus a frame-by-frame contact sheet. This is the repeatable
version of that one-off flow — one script call instead of re-deriving the
ffmpeg/PIL steps each time.

## When to use
- User pastes a `youtube.com/shorts/...` (or any yt-dlp URL) and asks to "check
  this", "analyze the style", "get a contact sheet", "download this short", or
  similar reference/study language.
- Not for the pipeline's OWN renders — those get QC'd via the existing
  frame-by-frame process already used in production reviews (see memory:
  contact-sheet QC on wheel-franchise renders), this skill is for **external**
  reference material.

## What it does
One entrypoint: `scripts/swipe_capture.py <url>`. It:
1. Pulls metadata via `yt-dlp -j` (title, uploader, duration, fps, dims, audio
   language) and writes `info.json`.
2. Downloads the best video+audio via `yt-dlp` into `raw.<ext>`.
3. Samples frames via `ffmpeg` (default 1 fps) and tiles them into a labeled
   grid (`t=NN.NNs` per tile) with PIL, saved as both `contact_sheet.jpg` and
   `contact_sheet.pdf`.
4. Deletes the loose `frames/` dir by default (pass `--keep-frames` to retain).

Output lands under `research/learning-assets/<video_id>_<title-slug>/` at the
repo root. That whole tree is gitignored (`research/learning-assets/` is
listed explicitly in `.gitignore`, alongside `renders_out/`/`renders_test/`)
— it's scratch reference material for studying other creators' style, not
production asset library content, and never gets committed.

## Usage
```bash
python scripts/swipe_capture.py "<url>"
python scripts/swipe_capture.py "<url>" --fps 2 --cols 8       # denser sampling
python scripts/swipe_capture.py "<url>" --keep-frames          # keep loose PNGs too
```

## Comp-DNA library mode (batch of references for style cloning)
For a set of URLs meant to become a cloning library, use `--out-dir research/comp-dna`
for each, then regenerate `research/comp-dna/LIBRARY.{json,md}` (one row per video:
id/title/creator/dur + empty theme/hook/beat-grammar/visual-DNA columns). Each video
folder has a `design/` subdir — Claude Design extractions (theme.json, tokens.css,
beat-map.md) get dropped there by VJ and the LIBRARY columns filled in. `raw.*` +
`contact_sheet.*` are gitignored; `info.json`, `design/`, `LIBRARY.*` are committed.
Claude Design chat sessions can't be read by DesignSync (it only syncs design-system
project files), so the pull is manual unless a design-system project is created.
**yt-dlp 403 → `pip install -U "yt-dlp[default]"` first** (fixed 2 of 10 on 2026-08-23).

## After running
- Report the dest folder path back to the user with a markdown link.
- Send the contact sheet (`display: render`) and the raw video
  (`display: attach`, with a one-line note if it's someone else's content —
  private reference use only, don't redistribute) via `SendUserFile`.
- If the user wants denser sampling (fast-cut shorts) or a scene-detected
  keyframe pass instead of uniform time sampling, re-run with `--fps`/`--cols`
  rather than hand-rolling ffmpeg again.
