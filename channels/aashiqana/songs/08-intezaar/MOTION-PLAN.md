# Intezaar — Motion Plan (long-form, track = 3:04.6)

**Status:** extra keyframes generated — MOTION SPEND AWAITS VJ COST APPROVAL
**Engine:** Hailuo 2.3 in Leonardo web (Video tab), image start-frame, 6s @ 768p 16:9, ~98 tok/clip.
Kling start+end-frame where a connected A→B move is needed (check availability in Video model list at drive time).

## 3060 / FLUX verdict (2026-08-22)
- Cast keyframes: NO — FLUX-schnell has no identity lock; NB2 image-edit is the only face-safe path (and 80 tok/frame is trivial).
- Motion: NO — start/end-frame local video (Wan FLF2V 14B) doesn't fit 12GB usably; hours/clip, sub-Hailuo quality.
- YES for optional cast-free atmospherics (landscape POV blur, steam, lamp macros) as free FLUX stills if we ever want to save tokens.

## Frame library (after this batch)
- kf01 her at window alone · kf02 chai two-shot · kf03 hands almost-touch · kf04 corridor walk
- kf05 platform goodbye · kf06 empty seat + dupatta
- kf07 her reflection in glass · kf08 chai tumblers macro (trembling) · kf09 tunnel silhouettes
- kf10 viaduct establishing wide · kf11 him alone w/ empty seat · kf12 side-by-side at window
- kf13 station clock in steam · kf14 her waiting on platform · kf15 reunion in steam (ALT ending)
- 4 Pexels keeper plates (window blur, tunnel, rain glass, corridor) as cutaway texture

## Timed map (3:04 ≈ 184.6s — refine to actual section stamps after audio analysis)
| Section (est.) | Time | Shots (6s clips, some reused) |
|---|---|---|
| Chorus 1 (cold open) | 0:00–0:22 | kf01 window+palm · kf07 reflection · kf10 viaduct wide |
| Verse 1 | 0:22–0:48 | kf02 chai two-shot · kf08 chai macro · plate window-blur POV |
| Chorus 2 | 0:48–1:10 | kf12 side-by-side · kf03 hands almost-touch |
| Verse 2 (dupatta) | 1:10–1:36 | kf11 him alone · kf06 empty seat+dupatta · kf13 clock |
| Bridge (suranga) | 1:36–2:00 | tunnel plate → kf09 tunnel silhouettes · kf04 corridor walk |
| Final chorus | 2:00–2:40 | kf05 goodbye · kf14 her waiting · kf15 reunion (OR hold ache: kf06 again) |
| Outro | 2:40–3:04 | kf10 viaduct receding · steam/clock texture |

## Motion spend (for approval)
- ~16 Hailuo clips × 98 tok ≈ **1,570 tokens** (balance after keyframes ≈ 16.5k → ends ≈ 15k). No cash cost beyond the existing web subscription.
- Motion prompts will use the locked grammar: "cinematic subtle motion… keep both faces exactly the same, no morphing, no warping, smooth realistic movement" + per-shot camera move.
- Connected-motion rule honored: window→reflection, hands→touch, goodbye→waiting→reunion are start/end pairs, not chopped repeats.

## Ending decision for VJ
kf15 gives a REUNION ending ("ek hi raat" resolved); kf06-reprise keeps the ACHE ending. Pick one before motion.
