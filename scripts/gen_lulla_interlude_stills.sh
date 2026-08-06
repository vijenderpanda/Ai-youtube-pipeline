#!/usr/bin/env bash
# Fresh seed-locked Lulla stills for the 1-hour compilation's instrumental interludes.
#
# Sibling of gen_song06_scenes.sh: same locked identity (Lucid Origin, master seed
# 1926068932, the face-locked BASE prompt + NEG from BRAND-BIBLE §11), different job.
# These are not episode scenes — they are the connective tissue BETWEEN the six
# published songs, and they carry one requirement the episode scenes never had:
#
#   THE ARC MUST DARKEN. i1 is late dusk; i9 is nearly black with one ember.
#
# assemble_compilation.py's dim_arc adds a further eq brightness ramp on top (capped
# at -0.20), so prompt and grade compound — the prompt does the *storytelling* part of
# the dim (fewer light sources, further away, lower in frame) and the grade does the
# last few percent. All the dim from eq alone would just look like an underexposed
# daylight frame; all of it from the prompt would fight the grade.
#
# 🔴 ONE PROMPT PER STILL, num_images=1 — deliberately, twice over:
#   * Leonardo rejects num_images=3 at 1344x768 ("too many images requested"); the cap
#     on this tier is 2, which is why gen_song06_scenes.sh only ever asked for 2.
#   * More importantly, the master seed is LOCKED. Two images from one prompt at one
#     fixed seed are variations of a single composition, so using both inside the same
#     interlude buys a crossfade between near-identical frames — which reads as a
#     freeze bug, not a scene change (same failure the doc-mock notes in §13). Distinct
#     scenes come from distinct prompts, so every still gets its own clause.
#
# Still counts taper on purpose: i1-i3 get 3 (a little movement left in the hour),
# i4-i9 get 2, because "near-static" IS the back half's brief.
#
# Usage: bash scripts/gen_lulla_interlude_stills.sh [i1a i1b ...]   (default: all 21)
set -uo pipefail
cd "$(dirname "$0")/.."

MODEL="7b592283-e8a7-4c5a-9ba6-d18c31f258b9"
SEED="1926068932"
OUT="channels/pip-moonlit-garden/assets/scenes"
W=1344; H=768; N=1

BASE="3D character design of a small round chubby cute night-creature named Lulla, smooth matte soft-vinyl surface like a designer toy, absolutely no fur and no hair, pastel periwinkle-blue body, a big round glowing warm-amber heart-shaped nightlight in the middle of its round belly, two short smooth antennae each ending in a small glowing warm-yellow orb, gentle sleepy half-closed eyes, no eyelashes, tiny content smile, soft rosy cheeks, tiny stubby arms and legs, adorable kawaii, muted warm pastel palette, cozy storybook 3D, dim warm low-contrast moonlight"
NEG="fur, furry, hair, fluffy, feathers, eyelashes, big open shiny eyes, cat ears, grey body, speckled, clothes, human, girl, boy, realistic person, scary, creepy, neon, oversaturated, harsh light, extra limbs, deformed, blurry, text, watermark, logo, cluttered"

ALL="i1a i1b i1c i2a i2b i2c i3a i3b i3c i4a i4b i5a i5b i6a i6b i7a i7b i8a i8b i9a i9b"
WANT="${*:-$ALL}"

gen () { # <short-label> <clause>
  case " $WANT " in *" $1 "*) ;; *) return 0 ;; esac
  echo "=== comp_$1 ==="
  bash scripts/leo_generate.sh "$BASE, $2" "$NEG" "$MODEL" "$N" "$W" "$H" "$OUT" "comp_$1" "$SEED" \
    || echo "!! comp_$1 FAILED (continuing)"
}

# ---- i1 · after "Sleepy Little Colors" — dusk drains out of the garden -------
gen i1a "wide establishing shot of the moonlit garden as the last colour drains from the sky, soft violet and dusty rose clouds going blue-grey, Lulla very small at the bottom of frame among tall soft grasses, warm belly glow the only warm point, first stars"
gen i1b "the same garden a little later from a low angle through the grass stems, the violet gone from the sky, Lulla standing small looking up at the first handful of stars, blue-grey dusk"
gen i1c "close-up of a single tall night flower still half-open at dusk, its pale petals catching the last light, Lulla's warm belly glow soft and out of focus behind it, blue-grey evening"

# ---- i2 · after "Count the Fireflies" — the fireflies disperse ---------------
gen i2a "a slow drift of soft fireflies spreading apart over a still dark pond, their glow dim and scattered, Lulla sitting small on the mossy bank watching them go, deep indigo water, crescent moon reflection breaking into ripples"
gen i2b "overhead view of black still water with five or six dim fireflies far apart across the whole frame, tiny warm points on a vast dark surface, Lulla a small shape at the very edge"
gen i2c "the last two fireflies drifting low and almost out of frame, Lulla alone on the dark mossy bank with its belly glow, deep indigo night, very quiet, empty space"

# ---- i3 · after "Little Light, Goodnight" — the lantern path -----------------
gen i3a "a winding garden path lit by a few low warm lanterns half-buried in moss, Lulla walking away from camera into the dark, small and calm, tall closed night flowers on both sides, deep blue-violet night"
gen i3b "close-up of one low moss lantern burning very low, warm amber light pooling on wet moss, the path beyond it disappearing into darkness"
gen i3c "the far end of the lantern path where the last lantern has almost gone out, Lulla a small dim silhouette beside it, deep blue-violet dark, most of the frame empty night"

# ---- i4 · after "Goodnight, Little Garden" — everything closes ---------------
gen i4a "beds of glow-flowers fully closed for the night, their light reduced to faint seams in the petals, soft round moss pillows under a great dark oak, Lulla curled at the edge of frame, very dim warm light"
gen i4b "wide low shot of the closed flower beds under a huge dark tree, the garden reading almost entirely in silhouette, one faint warm glow low in the frame where Lulla rests"

# ---- i5 · after "Breathe with Lulla" — mist settles --------------------------
gen i5a "low ground mist settling over completely still black water, the garden reduced to soft silhouettes, Lulla a small dim shape half-hidden in the mist, only the belly ember visible, deep desaturated indigo, almost monochrome"
gen i5b "thick soft mist filling most of the frame, the shapes of night flowers barely readable through it, a single faint warm ember glow deep in the haze, extremely low contrast"

# ---- i6..i9 · the coda — near-static, progressively almost dark --------------
gen i6a "Lulla curled up fast asleep on soft moss under a big leaf, belly heart-light dimmed to a low warm ember, the garden around it very dark and completely still, moon high and small, one or two faint distant fireflies"
gen i6b "very close on the sleeping Lulla's dimmed belly ember, the rest of the frame soft dark moss and shadow, warm amber light falling off fast into black"

gen i7a "extremely wide distant view of the whole sleeping garden at deep night, the entire frame dark blue-black, one single tiny warm amber dot far away where Lulla sleeps, faint stars, vast quiet"
gen i7b "the sleeping garden seen from even further away across dark water, its one warm dot reflected as a second smaller dot, everything else deep blue-black, still"

gen i8a "a deep night sky filling almost the whole frame, dense soft stars, the garden only a low dark silhouette along the very bottom edge, one barely-visible warm ember, near-black, extremely low contrast"
gen i8b "slow soft clouds drifting across a dense field of dim stars, the garden a thin dark band at the bottom of frame, the warm ember almost lost, near-black"

gen i9a "almost total darkness, the faintest possible warm ember glow at the very centre of the frame, the suggestion of a sleeping round shape around it, a low crescent moon setting at the edge, deep black-blue, minimal detail"
gen i9b "the last frame before sleep, near-black, only a dying warm ember and one dim star, everything else soft empty darkness, no detail, deeply restful"

echo ">> ALL COMPILATION INTERLUDE STILLS ATTEMPTED"
