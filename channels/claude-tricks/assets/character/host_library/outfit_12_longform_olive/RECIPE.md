# Outfit 12 — "Sol" long-form host: OLIVE overshirt · Vaibhav-style creator studio (LOCKED)

## 🔒 LOCKED (VJ 2026-08-16) — method + files
**Method: EDIT, don't regenerate.** Kino XL + Character Reference @ Mid *re-synthesizes* the face
and drifts (slim jaw, big quiff — rejected). The fix that holds identity is **Nano Banana 2
image-edit** (Legacy Mode OFF): attach a Sol frame as the Image Reference and prompt "keep this exact
person/face, change only …". Face stays pixel-faithful. This is the standard for all long-form host work.

**Lock chain:** outfit_11 `wide.jpg` → Nano Banana edit (olive overshirt + warm amber room) = **EDIT_0**
(`raw_edit/…_1f19955c_0.jpg`, face locked) → edit again (Vaibhav-style creator studio + hands up
mid-gesture) = **HANDS_0** (`raw_hands/…_1f199578_0.jpg`) = the locked host. Keyframes generated with
HANDS_0 as the Image Reference (same face/outfit/studio, new framing).

**Locked host files (this folder):**
- `hands_locked.jpg` / `wide.jpg` — MEDIUM, waist-up, both hands up (main talking beats)
- `keyframe_closeup.jpg` — CLOSE-UP head-and-shoulders (emphasis beats)
- `keyframe_wide.jpg` — WIDE, full podcast/creator desk (establishing / B-roll)
- `center.jpg` — tight face crop for the PiP
- raws: `raw_edit/` `raw_hands/` `raw_keyframes/` (alt picks live here)

**To add more keyframes:** Nano Banana 2, attach `hands_locked.jpg` as Image Reference, prompt
"keep this exact same person / face / olive overshirt / same creator studio — do NOT change identity
or room. [new framing/gesture]." 16:9, quantity 2. Fetch with `scripts/leo_chrome.py --fetch`.

---

## (Superseded) original olive-regenerate recipe — kept for reference only
Below is the Kino XL charref recipe first tried. It DRIFTED the face and was replaced by the edit
method above. Do not use for identity-critical host work.

# Outfit 12 — "Sol" long-form host: OLIVE overshirt · warm amber room (SAME face)

Purpose: a distinct host look for the 16:9 LONG-FORM videos (build_longform_segment.py frame
styles unchanged — only the host still swaps via `--host-dir`). Warmer, more approachable than the
magenta-studio Shorts host; moves furthest from the current look while keeping the same identity.
Face locked to the same person via the founder charref.

Generate via **claude-in-chrome** on `app.leonardo.ai` (real logged-in session — API out of
credits; see [[leonardo-via-claude-in-chrome]]). Follows the locked [[host-shoot-leonardo-recipe]]
except OUTFIT + BACKGROUND, and one deliberate negative-prompt change (below).

## SETTINGS (left rail, Legacy Mode) — unchanged from the lock
- Model: **Leonardo Kino XL**  ·  Preset Style: **Photography**  ·  Alchemy: **On (V2)**  ·  Private: **On**
- Char-Ref: Image Guidance → upload
  **`host_library/outfit_11_sol_magenta/wide.jpg`** (VJ 2026-08-16: reference the ESTABLISHED
  Sol head-and-shoulders, not the founder selfie — the outfit_11 plate locks face **and** build,
  giving better body/identity consistency; the selfie only carried the face). Type
  **Character Reference** → Strength **Mid**. (Upload path in the new UI: click slot-1 source →
  "Select Media" modal → Upload an image. Uploading via the global hidden input mis-files to a
  Style-Reference slot — use the slot-1 modal.)
  _FINAL PICK: batch `551a289d` image `_3` → wide.jpg + center.jpg. Founder-selfie batch `b80f1289`
  kept in `raw/` for reference; body-ref batch in `raw_bodyref/`._
- Fixed Seed: **On → 9422710109**  ·  Num Images: 4

## ⚠️ Negative-prompt change for THIS outfit
The locked recipe negatives include `green, teal, cyan` to stop the background drifting teal. The
outfit here IS olive (a muted green), so **drop `green` from the negatives for this outfit** and keep
only `teal, cyan` (those are the drift colours; olive/khaki is warm-earthy, not teal). Otherwise the
overshirt desaturates to grey/brown.

## SHOT A — wide (host_full backdrop). Dimensions **2376 × 1344 (16:9)**
POSITIVE:
```
facing the camera and smiling warmly with a genuine happy Duchenne smile, bright kind eyes that crinkle at the corners, relaxed raised brows. Host seated centre-frame at a modern presenter desk, upper body in shot, calm and authoritative. a South Asian man in his early thirties with short dark textured hair swept up and a neat well-groomed dark beard, wearing a muted olive-green cotton overshirt / field jacket in an earthy khaki tone over a plain cream tee. warm amber-lit editorial creator room, soft wood tones and out-of-focus warm lamp bokeh behind him, a subtle cool rim light on one shoulder for separation, clean uncluttered depth. Photography, natural realistic skin texture with visible pores, soft flattering warm key light, shallow depth of field, sharp eyes, 85mm portrait look.
```
NEGATIVE:
```
intense stare, furrowed brow, knitted eyebrows, cold eyes, dead eyes, serious blank stare, stern, airbrushed, plastic skin, waxy skin, doll skin, glossy, oversaturated, HDR, 3d render, CGI, teal, cyan, earring, extra fingers, cluttered background, text, watermark
```

## SHOT B — portrait (PiP). Dimensions **896 × 1344 (2:3)**
Same POSITIVE/NEGATIVE as Shot A, but change the framing clause
`Host seated centre-frame at a modern presenter desk, upper body in shot` →
`tight head-and-shoulders portrait, centred`.

## SAVE AS (download via `scripts/leo_chrome.py --fetch <outdir>`)
- Shot A best → `wide.jpg`   (host_full backdrop)
- Shot B best → `center.jpg` (PiP crop)
- raw 4-up → `raw/`

## THEN re-render the proto with the new host — frame styles COPIED, host SWAPPED
```
python3 channels/claude-tricks/build_longform_segment.py \
  --words channels/claude-tricks/assets/ep11/vo_v2.words.json \
  --title "1. Switch models in one click" \
  --host-dir channels/claude-tricks/assets/character/host_library/outfit_12_longform_olive \
  --out channels/claude-tricks/renders/longform/seg_proto_v3_olive.mp4
```
