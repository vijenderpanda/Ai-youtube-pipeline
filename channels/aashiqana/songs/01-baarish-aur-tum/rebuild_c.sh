#!/usr/bin/env bash
set -e
cd /Users/vijenderpanda/Ai-youtube-pipeline
BASE=channels/aashiqana/songs/01-baarish-aur-tum
R=$BASE/renders
LOG=$R/rebuild_c.log; : > "$LOG"
echo "[1/4] base cut 1080p with track C" >> "$LOG"
python3 scripts/assemble_music_video.py --song "$R/song.mp3" \
  --out "$R/base_cut_c_1080.mp4" --res 1920x1080 --fps 30 --xfade 0.7 >> "$LOG" 2>&1
echo "[2/4] lyric overlay" >> "$LOG"
python3 scripts/lyric_overlay.py --base "$R/base_cut_c_1080.mp4" \
  --timing "$BASE/lyrics/timing.json" \
  --out "$R/aashiqana_tu_hi_hai_1080.mp4" >> "$LOG" 2>&1
echo "[3/4] short base (hook = cold open, start 0)" >> "$LOG"
python3 scripts/assemble_short_music.py --song "$R/song.mp3" --start 0 --dur 30 \
  --out "$R/short_base_c.mp4" >> "$LOG" 2>&1
echo "[4/4] short lyric overlay" >> "$LOG"
python3 scripts/lyric_overlay.py --base "$R/short_base_c.mp4" \
  --timing "$BASE/lyrics/timing_short.json" \
  --out "$R/aashiqana_tu_hi_hai_short_9x16.mp4" --w 1080 --h 1920 --hold 5 >> "$LOG" 2>&1
echo "REBUILD DONE" >> "$LOG"
ls -la "$R"/aashiqana_tu_hi_hai* >> "$LOG"
