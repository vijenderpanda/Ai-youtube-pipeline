#!/usr/bin/env bash
set -e
cd /Users/vijenderpanda/Ai-youtube-pipeline
BASE=channels/aashiqana/songs/01-baarish-aur-tum
R=$BASE/renders
LOG=$R/karaoke_final.log; : > "$LOG"
echo "[1/2] long-form karaoke" >> "$LOG"
python3 scripts/lyric_karaoke.py --base "$R/base_cut_c_1080.mp4" \
  --timing "$BASE/lyrics/timing_karaoke.json" \
  --out "$R/aashiqana_tu_hi_hai_1080_v2.mp4" >> "$LOG" 2>&1
echo "[2/2] short karaoke" >> "$LOG"
python3 scripts/lyric_karaoke.py --base "$R/short_base_c.mp4" \
  --timing "$BASE/lyrics/timing_karaoke_short.json" \
  --out "$R/aashiqana_tu_hi_hai_short_v2.mp4" --w 1080 --h 1920 >> "$LOG" 2>&1
echo "KARAOKE DONE" >> "$LOG"
