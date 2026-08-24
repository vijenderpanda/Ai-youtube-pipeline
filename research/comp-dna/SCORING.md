# SCORING — the meta-heavy tag + confidence layer

The library is not a folder of clips; it's a **scoreable** asset set. A planning agent
gives a content brief and gets back the best-fit asset pack (palette + archetype to
clone + components) with a **confidence score** and a **world-fit** check.

## Files
- `SCORING.json` — one tagged, evidence-weighted record per asset (22 references + 37 cookbook components). Built by `scripts/build_asset_scores.py` (re-run after any capture/extract).
- `scripts/pick_asset_pack.py` — the matcher. `--topic "..."` infers the brief, or pass `--brief '{...}'`.

## Tag axes (the "whole world around the content")
| axis | values | why it matters |
|---|---|---|
| **palette** | cream · paperYellow · night · midnight · cleanRed | canvas+accent family — the look must match the mood, not default to paper |
| tone | light · dark | night/midnight are dark; the rest light |
| accent | terracotta · sage · mint · yellow · red · pink · blue | **yellow wins the talking-head lane, not terracotta** |
| host | full · pip · none | avatar budget; 12/12 scout winners were host=full |
| archetype | A1–A6 (craft/Isenberg) · B1–B5 (selection/scout) | see TAXONOMY.md §2 / §2b |
| hook | logo-motion · claim-title-card · shock-stat · yes-no-question · chart-first · mid-sentence · … | first-3s mechanic |
| lane | ai-tools · design · news-hottake · framework · product-demo · tutorial | genre — the biggest fit lever (weight 3.0) |
| region | IN · US · global | India-first vs US; changes reference/voice |
| mood | calm · urgent · money · playful · authoritative · curious | emotional register |
| length | micro <25s · short 25-45 · mid 45-70 · long 70s+ | format fit |
| density | low · med · high | how much info on screen at once |

## Confidence math (honest, not just similarity)
`confidence = 0.7 × tag-fit + 0.3 × evidence`
- **tag-fit** = weighted axis match (lane 3.0, mood/host 2.0, region/palette 1.5, rest 1.0).
- **evidence** = how much real performance backs the reference (views/day percentile within the scout + like-rate). A proven short scores higher than a plausible-but-unmeasured one.
- The matcher prints the **gaps** (which axes didn't match), so a low score is a *diagnosis of a library hole*, not a silent guess. E.g. money/IN/framework currently scores ≤39% → the library is thin there; capture more India money-framework refs to fill it.

## Coverage today (2026-08-23)
palette: cream 14 · paperYellow 3 · night 3 · midnight 1 · cleanRed 1 → **paper-heavy; dark/yellow under-built** (capture target).
region: US 17 · IN 5 → **US-heavy** (capture more IN in-lane).
archetype: A1-A6 craft + B1-B5 selection, all represented.

## Use in planning
```bash
python scripts/pick_asset_pack.py --topic "Claude just shipped a scary new feature"
python scripts/pick_asset_pack.py --brief '{"lane":"news-hottake","mood":"urgent","host":"full","region":"US","length":"short"}'
```
Output = top-3 packs (clone spec + palette + component pack per beat) with confidence + world-fit. Copy the clone spec, set `theme` to the palette, swap props to your topic, render with `scripts/render_clones.py`.
