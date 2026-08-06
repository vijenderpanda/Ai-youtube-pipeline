#!/usr/bin/env bash
set -e
cd /Users/vijenderpanda/Ai-youtube-pipeline
BASE=channels/aashiqana/songs/01-baarish-aur-tum
R=$BASE/renders
LOG=$R/karaoke_v3.log; : > "$LOG"
echo "[1/2] long-form karaoke (forced-aligned)" >> "$LOG"
python3 scripts/lyric_karaoke.py --base "$R/base_cut_c_1080.mp4" \
  --timing "$BASE/lyrics/timing_final.json" \
  --out "$R/aashiqana_tu_hi_hai_1080_v3.mp4" >> "$LOG" 2>&1
echo "[2/2] short karaoke" >> "$LOG"
python3 scripts/lyric_karaoke.py --base "$R/short_base_c.mp4" \
  --timing "$BASE/lyrics/timing_final_short.json" \
  --out "$R/aashiqana_tu_hi_hai_short_v3.mp4" --w 1080 --h 1920 >> "$LOG" 2>&1
echo "KARAOKE_V3 DONE" >> "$LOG"
ls -la "$R"/*_v3.mp4 >> "$LOG"
