#!/usr/bin/env bash
# Generate the 8 fresh scenes for Song #06 "Time for Bed, Little Light".
# Face-locked hero base (BRAND-BIBLE §11 + the #4/#5 face-lock fix) + per-scene clause.
# Model Lucid Origin, master seed 1926068932, 1344x768, 2 images each.
set -uo pipefail
cd "$(dirname "$0")/.."

MODEL="7b592283-e8a7-4c5a-9ba6-d18c31f258b9"
SEED="1926068932"
OUT="channels/pip-moonlit-garden/assets/scenes"
W=1344; H=768; N=2

BASE="3D character design of a small round chubby cute night-creature named Lulla, smooth matte soft-vinyl surface like a designer toy, absolutely no fur and no hair, pastel periwinkle-blue body, a big round glowing warm-amber heart-shaped nightlight in the middle of its round belly, two short smooth antennae each ending in a small glowing warm-yellow orb, gentle sleepy half-closed eyes, no eyelashes, tiny content smile, soft rosy cheeks, tiny stubby arms and legs, adorable kawaii, muted warm pastel palette, cozy storybook 3D, dim warm low-contrast moonlight"
NEG="fur, furry, hair, fluffy, feathers, eyelashes, big open shiny eyes, cat ears, grey body, speckled, clothes, human, girl, boy, realistic person, scary, creepy, neon, oversaturated, harsh light, extra limbs, deformed, blurry, text, watermark, logo, cluttered"

gen () { # <label> <clause>
  echo "=== $1 ==="
  bash scripts/leo_generate.sh "$BASE, $2" "$NEG" "$MODEL" "$N" "$W" "$H" "$OUT" "$1" "$SEED" \
    || echo "!! $1 FAILED (continuing)"
}

gen s06_dusk        "wide shot of the whole moonlit garden at last light, warm amber sunset fading into deep indigo sky, Lulla standing small on a grassy hill looking up, first few soft stars appearing, crescent moon rising"
gen s06_foldflowers "Lulla gently touching a glowing garden flower as its petals softly fold closed for the night, beds of soft glow-flowers dimming, deep indigo night garden"
gen s06_wash        "Lulla at the edge of a still Moon Pond softly splashing cool water with tiny hands, a crescent moon reflected on the calm water, gentle ripples, night"
gen s06_mosspillow  "Lulla plumping a soft round moss pillow on the grass under a big friendly oak tree with a warm hanging lantern, getting a cozy bed ready, night garden"
gen s06_tuck        "Lulla lying cozy on soft moss pulling a big soft leaf blanket up to its chin, sleepy content smile, crescent moon and soft stars above"
gen s06_yawn        "extreme close-up of Lulla mid-yawn, tiny round mouth open, eyes squeezed happy and closed, soft belly glow, cozy deep indigo background"
gen s06_stars       "Lulla lying back on the grass watching soft stars appear one by one in a deep indigo sky, warm belly glow, peaceful, crescent moon"
gen s06_ember       "Lulla curled up fast asleep on the moss, belly heart-light dimmed to a soft warm ember, the garden dark and still, moon high, a few dim fireflies"

echo ">> ALL SONG06 SCENES ATTEMPTED"
