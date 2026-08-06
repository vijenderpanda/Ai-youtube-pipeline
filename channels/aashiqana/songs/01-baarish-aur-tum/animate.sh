#!/usr/bin/env bash
# Animate all shots with Leonardo Motion 2.0 (subtle motion, --no-enhance preserves composition)
set -u
cd /Users/vijenderpanda/Ai-youtube-pipeline
BASE=channels/aashiqana/songs/01-baarish-aur-tum
CH=$BASE/characters
SC=$BASE/scenes
OUT=$BASE/renders/clips
LOG=$BASE/renders/animate.log
: > "$LOG"

# image | outname | motion prompt
JOBS=(
"$CH/couple_twoshot_0.jpg|c01_rain_intimate|gentle rain falling softly, subtle hair movement, soft natural breathing, very slow cinematic push in, romantic mood"
"$CH/couple_twoshot_1.jpg|c02_rain_wide|gentle rain falling, subtle body movement, slow cinematic dolly in, moody"
"$CH/couple_master_0.jpg|c03_meera_rain_a|gentle rain, hair sways softly, subtle blink and breath, slow push in, wistful"
"$CH/couple_master_1.jpg|c04_meera_rain_b|gentle rain falling, soft hair movement, subtle blink, slow zoom in, emotional"
"$SC/scene_cafe_0.jpg|c05_cafe_couple|steam rising from chai cups, subtle smiles, rain streaks sliding on the window, slow gentle push in, warm intimate"
"$SC/scene_cafe_1.jpg|c06_cafe_solo|rain sliding on the window, soft hair movement, gentle blink, slow zoom, wistful"
"$SC/scene_rooftop_0.jpg|c07_rooftop_foreheads|gentle wind moving her hair, twilight clouds drifting slowly, subtle sway, slow push in, romantic"
"$SC/scene_rooftop_1.jpg|c08_rooftop_embrace|wind blowing her hair softly, clouds drifting across the dusk sky, gentle sway, cinematic slow zoom"
"$SC/scene_hills_0.jpg|c09_hills_facing|misty rain falling, fog drifting across the green hills, gentle subtle movement, dreamy"
"$SC/scene_hills_1.jpg|c10_hills_walk|the couple walking slowly forward down the path, soft rain, fog drifting, cinematic tracking feel"
)

run_one() {
  local img="$1" name="$2" prompt="$3"
  echo "[START] $name  ($img)" >> "$LOG"
  python3 scripts/leo_motion.py --upload "$img" --no-enhance \
    --prompt "$prompt" --resolution RESOLUTION_720 \
    --out "$OUT/$name.mp4" >> "$LOG" 2>&1
  if [ -s "$OUT/$name.mp4" ]; then echo "[OK]    $name" >> "$LOG"; else echo "[FAIL]  $name" >> "$LOG"; fi
}

# launch in batches of 3 to avoid rate limits
i=0
for j in "${JOBS[@]}"; do
  IFS='|' read -r img name prompt <<< "$j"
  run_one "$img" "$name" "$prompt" &
  i=$((i+1))
  if [ $((i % 3)) -eq 0 ]; then wait; fi
  sleep 2
done
wait
echo "[ALL DONE]" >> "$LOG"
ls -la "$OUT" >> "$LOG"
