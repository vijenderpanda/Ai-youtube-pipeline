# CHECKPOINT — 2026-08-21/22 · The Motion-Graphics Pipeline

**Purpose of this file:** a cold-start handoff. Any Claude session (or human) on any
machine should be able to read this, `git pull`, and continue exactly where this
session stopped. The session-local memory files on the Mac are NOT required —
everything decision-critical is in this doc or the repo docs it points to.

---

## 1. WHAT SHIPPED TODAY

| Thing | State | Where |
|---|---|---|
| **Ep1 "Why ChatGPT & Claude Forget Long Chats 🧠"** | **ARMED** — youtu.be/lcPa3xp0Kik, scheduled 2026-08-21T19:00:00Z (= 22 Aug 00:30 IST), 4K 2160×3840, −13.8 LUFS, all gates PASS | master `channels/claude-tricks/renders/ep_forgets_v1_outro.mp4`; calendar row `cf2cafc1` = produced |
| Ep1 manual step | **VJ must PIN the comment on publish day** | text: `films/forgets.manifest.json → packaging.pinned_comment` |
| The motion pipeline (docs) | designed + approved by VJ | `docs/MOTION-PIPELINE.md` (Parts I–III: 14 laws, stages, hit evidence, world verdict) |
| The gate suite | built, validated on reference hits | `scripts/qc_motion.py` (manifest schema in its docstring) |
| Manifest compiler + storyboard generator | built | `channels/claude-tricks/cast_scenes.py`, `storyboard.py` |
| Runtime foundation | built + committed | `remotion-studio/src/cookbook/`: `filmclock.tsx` (CRITICAL — see §4), `motion.ts`, `craft.tsx` (TravelSprite/MorphSwap/ExposureScore/FlashCut), `WorldCamera.tsx`, `ChipCaption.tsx`, `FilmLayers.tsx` |
| World 1: CLAYLIGHT (ep1) | shipped; assets in `assets/claylight/library/` (PNGs force-committed) | `Claylight.tsx`, `ForgetsClay.tsx`, `ClayOutro.tsx`, lock: `films/CLAYLIGHT.lock.json` |
| World 2: KAAGAZ paper (+ OctoPuppet character rig) | built as capability; puppet NOT used in ep2 by VJ's call | `Kaagaz.tsx` |
| Ep2 "_zerostack" draft | **AT THE STORYBOARD GATE — VJ REJECTED THE CURRENT CUT** (see §3, the open problem) | `ZeroStackPaper.tsx`, `films/zerostack.manifest.json`, storyboard artifact `6b4715c8` |

## 2. THE DOCTRINE (VJ-decided, binding)

1. **Storyboard is the approval artifact. NOTHING renders without VJ's word; no 4K by
   default; remind him for 4K after he finalizes; then arm.** (A cheap preview to
   check one mechanism still counts as a render — ask.)
2. **A world belongs to an EPISODE**, chosen at design time to fit content + VO.
   No asset reuse across worlds (no ep1 boxes/corals in ep2).
3. Zero-human canvas in this lane (Sol retired to avatar + capture lane). Hinglish:
   VO opening line only (ep2), one Devanagari chip word allowed.
4. Honesty: numbers real-sourced / declared-illustration / absent — enforced by
   `cast_scenes.py`. Mocks are re-typeset artifacts, never raw screenshots.
   Provenance strips on REAL captures only. Give the artifact (prompt in
   description above the fold + pinned comment), never promise it.
5. Existing capture/host lane is NOT retired; `channels/claude-tricks/MOTION-BUCKET.md`
   routes ideas between lanes.
6. Metadata (researched, evidence in MOTION-PIPELINE + commit 38f269a): tags are
   dead as a lever (keep minimal list for the searched-noun law), 3 hashtags in
   desc, give-in-desc above the fold, noun-specificity beats any title formula.

## 3. THE OPEN PROBLEM — VJ's LAST FEEDBACK, VERBATIM (2026-08-22 early)

> "world is different for sure but the renders and animation are still not matching
> their bar gregisenberg shorts renders and motions your version currently feels
> dull and chatgpt free claude free not working plus what is this 18/hr not able to
> relate , i watched the raw clip without vo not able to understand at all flaws in
> current motion overlapping n all but you can do far better either i am restricting
> you somewhere or i dont know what is it you are not able to fan out on creativity ,
> honestly the script also very hard to understand what we are solving what is the
> payoff"

Decomposed, the next session must fix ALL of:
- **Render/finish quality below the Isenberg bar** — his references have soft-3D
  depth, material richness, lighting; our flat vector paper reads "dull". The gap
  is probably RENDER TREATMENT (gradients, soft shadows, bevels, depth-of-field,
  texture) not layout. Study `docs/MOTION-PIPELINE.md` Part III's element-diet
  evidence + the actual reference frames (see §5 downloads).
- **Motion has overlapping flaws** — audit the current `zs_final` render for
  collisions/overlaps frame-by-frame before redesigning.
- **The SCRIPT fails the mute test at the story level**: a viewer cannot tell what
  problem is being solved or what the payoff is. "₹18/hr" landed with no referent;
  "CHATGPT FREE / CLAUDE FREE" chips meaningless without context. The story needs
  a RELATABLE problem statement in the first 2s and a payoff a muted viewer can
  name. Rewrite the script BEFORE re-choreographing.
- VJ explicitly invites more creative range: "you can do far better… fan out on
  creativity." Do not stay conservative.

Ep2 assets that survive regardless: the sourced numbers research (₹18/hr =
1.5T non-inverter ~1.9 u/hr × Mumbai ₹9.5/kWh — NoBroker/Onida 2026; ₹900/mo
derived; ₹0 = free tiers), the manifest gate discipline, the toolchain.

## 4. LANDMINES THE NEXT SESSION MUST KNOW

- **`filmclock.tsx` / `useFilmT()`**: every beat renders in its own `<Sequence>`
  (local frame 0). ANY component reading `useCurrentFrame()` raw will RESTART at
  every cut in the real build while looking perfect in studio test renders. All
  film components must read `useFilmT()`; the spine provides `FilmT` context.
- **Merged beats share one caption** in `build_ep_v2.py` — consecutive identical
  beat strings merge; use `#variant` suffixes to keep beats distinct.
- **`cfg["spine"]`** injects negative `start` offsets so a component runs one
  continuous timeline across beats; anchors resolve as `"@beatN+x"` from the
  MEASURED VO clock at build time (planned clock only for storyboards).
- **`finalize --dry` used to REAL-upload** — fixed to coerce `--skip-arm`, but never
  trust `--dry` flags in this repo without reading them.
- **The arm gate needs `renders/thumb_<ep>.jpg`**, LUFS on the spine, and the
  mirror check. `qc_motion.py --manifest` bboxes must be 0–1 normalized (px
  coords silently half-scale on 4K).
- FLUX-schnell runs via the Supabase job queue on DESKTOP-DEIR7RS
  (`scripts/img_render.py --track flux_local`), ~2 min/image, free. Pexels/Pixabay
  keys live in `.env`. Leonardo API is 402-blocked; use VJ's Chrome.
- Remotion pinned deps: all `@remotion/*` at **4.0.503** exactly; TypeScript is
  pinned 5.9.3 (7.x broke the bundler once already).

## 5. WHERE THE EVIDENCE LIVES

- Reference-film downloads + frame extractions were in the session scratchpad
  (ephemeral). Re-fetch with yt-dlp if needed; IDs + full studies are inside
  `docs/MOTION-PIPELINE.md` Part III (hit table + element diet + camera evidence).
- Ep1 phone-gate cuts, contact sheets: scratchpad (ephemeral); the shipped master
  is in `renders/` (gitignored — media lives on the Mac / T5 SSD per policy).
- Analytics ground truth: `docs/stats/history.csv`, `docs/SHORTS-METHOD-AND-APP-GATES.md`
  (note: its §"frozen frames 15–25s" rule is UNVERIFIED — see MOTION-PIPELINE).

## 6. RESUME COMMANDS

```bash
# validate + storyboard any film manifest
python3 channels/claude-tricks/cast_scenes.py films/<ep>.manifest.json
python3 channels/claude-tricks/storyboard.py films/<ep>.manifest.json

# emit episode spec after VJ approves a storyboard, then VO + preview build
python3 channels/claude-tricks/cast_scenes.py films/<ep>.manifest.json --emit
FACTORY_REMOTION_SCALE=1 python3 channels/claude-tricks/build_ep_v2.py --ep _<ep> --tag draft

# machine gates
python3 scripts/qc_motion.py --video channels/claude-tricks/renders/ep_<ep>_draft.mp4 --manifest <qc.json>
```

Ep1 analytics watch: stayed-to-watch (the title bet) + AVP (the mute-grammar bet)
+ whether any video breaks ~300 views (= second feed sample fired).
