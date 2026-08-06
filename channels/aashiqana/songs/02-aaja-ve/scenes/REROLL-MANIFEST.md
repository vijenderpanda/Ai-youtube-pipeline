# Song #02 re-roll manifest (v2 scene pass — Leonardo WEB UI, API tokens exhausted)

## QC verdict on API batch v1 (2026-08-03)
| Shot | Verdict | Problem |
|---|---|---|
| S01 | ❌ re-roll | portrait of woman instead of extreme wide w/ man + distant red figure |
| S02 | ✅ KEEP `s02_1` | his profile ache — on spec, identity holds |
| S03 | ❌ re-roll | woman appeared instead of man-alone (driver used couple ref) |
| S04 | ❌ re-roll | portrait instead of macro wine-glass detail |
| S05 | ❌ re-roll | woman alone; no couple walking |
| S06 | ⚠️ B-roll keep `s06_1` | behind-hug cute but faces drifted; re-roll for joined-hands spec |
| S07 | ❌ re-roll | bust portrait, dress went mauve; need full-length RED gown mid-turn |
| S08 | ⚠️ B-roll keep `s08_1` | her+roses solo is gorgeous; man missing from handoff — re-roll |
| S09 | ❌ re-roll | woman-only close-up; need couple right-third + sky negative space (THUMB) |
| S10 | ⚠️ B-roll keep `s10_1` | back-to-back two-shot pretty; not the arrival payoff — re-roll |
| S11 | ⚠️ keep `s11_0` as fallback | wine-glass nuzzle near-spec; re-roll for foreheads-touch |
| S12 | ❌ generate | never ran (API tokens ran out) |

## Fix rules for v2 (bake into every prompt)
1. **Composition tokens FIRST** — prompt starts "Cinematic extreme wide shot…" etc.; couple-DNA appended at the END (charref carries identity).
2. **Ref strategy per shot type:** extreme wide / macro (S01, S04, S12) → **NO character reference**, faces tiny or absent; man-alone (S03) → `hero_face_crop.jpg` charref; woman-solo full-length (S07) → `heroine_face_crop.jpg` charref **Mid** (High forces bust framing); two-shots (S05, S08, S09, S10, S11) → full anchor charref **Mid** + phrase "BOTH the man and the woman clearly together in frame".
3. **Woman makeup guard:** append "soft natural feathered eyebrows, light natural makeup, soft nude-rose lips"; negatives += "thick painted eyebrows, heavy dark lipstick".
4. **Wardrobe color lock:** name the color twice ("deep crimson red chiffon gown, vivid red fabric").
5. Keep Kino XL + 16:9 (closest web preset to 1344×768) for grade consistency with kept shots.

## v2 QC + FINAL PICKS (2026-08-03, web-UI batch)
Composition-first + per-shot refs fixed the batch: 10/12 usable on first v2 roll.

| Shot | Final pick | Notes |
|---|---|---|
| S01 | `stills_v2/s01_0.jpg` | true extreme wide ✓; distant red-figure didn't render — narrative carried by cutting to S07 |
| S02 | `stills/s02_1.jpg` (v1) | his profile ache, kept from API batch |
| S03 | fix-roll (mustache) | v2 had the man ✓ but visible mustache + missing props |
| S04 | `stills_v2/s04_1.jpg` | TWO glasses + roses + bottle — exact lyric beat 💎 |
| S05 | `stills_v2/s05_1.jpg` | couple walking, denim ✓ (medium not full-wide — fine) |
| S06 | `stills_v2/s06_0.jpg` | facing each other laughing, denim continuity |
| S07 | `stills_v2/s07_1.jpg` | red-dress over-shoulder glance — premium 💎 (bust, not full-length) |
| S08 | `stills_v2/s08_0.jpg` | rose-in-hand behind-embrace (scripted handoff never rendered in 2 tries) |
| S09 | `stills_v2/s09_0.jpg` 📌THUMB | her radiant smile over his shoulder at sunset — thumbnail-stopping |
| S10 | `stills_v2/s10_0.jpg` | she walks the path in red w/ roses, man behind; crop out bottom-right object + distant 2nd figure |
| S11 | fix-roll (mustache) | v2 s11_1 wine-toast good but mustache |
| S12 | `stills_v2/s12_0.jpg` | silhouette embrace, violet-amber sky, clean end-card space 💎 |

**New lesson:** charref-Mid revives Kino XL's mustache prior on the hero in ~half of rolls — "no mustache" in the negative isn't enough; needs "completely clean-shaven upper lip" as a POSITIVE phrase + fix-rolls. Watch every male render for it.
