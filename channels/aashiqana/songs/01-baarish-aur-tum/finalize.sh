#!/usr/bin/env bash
cd /Users/vijenderpanda/Ai-youtube-pipeline
BASE=channels/aashiqana/songs/01-baarish-aur-tum
R=$BASE/renders
LOG=$R/finalize.log; : > "$LOG"
echo "waiting for base render..." >> "$LOG"
for i in $(seq 1 180); do
  pgrep -f assemble_music_video >/dev/null || break
  sleep 10
done
sleep 3
dur=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$R/base_cut_1080.mp4" 2>/dev/null)
echo "base_cut duration=$dur" >> "$LOG"
if [ -z "$dur" ]; then echo "BASE CUT INVALID" >> "$LOG"; exit 1; fi
echo "running lyric overlay..." >> "$LOG"
python3 scripts/lyric_overlay.py --base "$R/base_cut_1080.mp4" \
  --timing "$BASE/lyrics/timing.json" --out "$R/aashiqana_baarish_aur_tum_1080.mp4" >> "$LOG" 2>&1
echo "FINALIZE DONE" >> "$LOG"
ls -la "$R"/*.mp4 >> "$LOG"
