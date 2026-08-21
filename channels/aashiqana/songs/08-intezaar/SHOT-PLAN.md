# Intezaar 🚂 — Shot Plan (candidate #4, vintage train journey)

**Status:** PLATES PULLED (free) · Leonardo cast NOT generated — awaiting VJ approval (render gate)
**Sources:** Pexels = real environment plates (free, license-safe) · Leonardo web UI via `leo_chrome.py` = photoreal couple cast (17,438 paid web tokens available; API blocked, do not use API)
**Pipeline:** locked Aashiqana v1 — fresh anchor → NB2 image-edit keyframes → Hailuo/Kling connected motion → stitch → brand → arm

## Look
- NOT literal sepia (brand drift). Warm tungsten + window light, deep mahogany shadows, film grain.
- Rotate-setting rule satisfied: train cabin is new vs café/seaside/golden-hour.
- Connected motion: blurring landscape out the window + rhythmic sway = free Kling start/end-frame moves.

## Environment plates (Pexels, downloaded → `plates/`)
12 portrait plates pulled; **VJ-approved keepers → `keepers/`** (2026-08-21): window motion-blur 17408946, tunnel 19268923, rain-streaked window 27948075, warm corridor 33300959 (distant walker — crop/blur in edit; the other corridor plate dropped: children in frame).

## Cast (Leonardo — HOLD until approved)
Fresh anchor couple (do NOT reuse Kino charref — face drift; consistency comes from NB2 EDIT afterward):

**Anchor prompt (Leonardo web, photoreal):**
> Cinematic photoreal portrait, young Indian couple early 20s inside a vintage 1940s Indian Railways first-class wooden cabin at dusk, warm tungsten lamp glow, mahogany paneling, he in cream kurta gazing at her, she in deep maroon saree by the rain-streaked window, soft film grain, shallow depth of field, longing expression, 9:16

**NB2 edit keyframes from anchor (~80 tok/img):**
1. Her alone at window, landscape blur, hand on glass (hook shot — word-first)
2. Two-shot across the cabin, tea glasses trembling with track rhythm
3. Close-up his hand almost touching hers on the seat
4. Corridor walk toward camera, lamps flickering past
5. Platform goodbye through the closing door, steam
6. Final: empty seat, her dupatta left behind (intezaar payoff)

## Sound DNA
Cold-open vocal hook over track-clack foley; no intro; exclude-styles trick; audition multiple candidates.

**Lyric rule (VJ 2026-08-21): NO cliché stock lines** — nothing like "2 wine ke glass" / "tu laal dress me thi" / daaru-party-dress-color tropes. Every image in the lyrics must come from THIS song's world: the train's rhythm (intezaar ki taal), rain crawling down the glass, the platform clock, steam, the dupatta left behind. Test: if the line fits any generic Punjabi-pop track, cut it.

## Gate
- [x] VJ approves plates (contact sheet) — 2026-08-21
- [x] Anchor generated (Leonardo web UI via claude-in-chrome, NB2 848×1264, 80 tok) → `cast/cinematic-photoreal-portrait-young-i_1f19d536_0.jpg`
- [x] VJ approved anchor → 6 NB2 keyframes generated **16:9 1376×768 (LONG-FORM per VJ 2026-08-21)**, 480 tok, in `keyframes/` (kf01–kf06 + `_kf_contact_sheet.jpg`); anchor stays the identity ref
- [x] VJ approved keyframes (2026-08-21) → motion spend UNLOCKED (Kling/Hailuo connected motion, start+end frames) — awaiting lyric/track lock first
- [x] Lyrics LOCKED: A + B's dupatta verse → `lyrics/final_v1.md`
- [x] Suno: 2 pairs generated (v5.5, male vocal); **VJ picked track #2 (3:04)** → `track/intezaar_v1_picked.mp3` (184.6s)
- [ ] Motion pass sized to 3:04 track — plan + cost to VJ before motion spend
- Only if TEST 1 verdict = GO (≥50 related by d14) does this arm.
