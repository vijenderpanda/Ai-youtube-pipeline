# Aashiqana — Factory Production Blueprint (v18, from-the-app)

> How Aashiqana Shorts are planned → produced → locked → armed **from the Studio Factory app**,
> aligned with the claude-tricks / already-happening wiring. The *craft* pipeline is fully
> independent per channel and lives in **`SHORTS-TEMPLATE-LOCKED.md`** (the locked recipe — read it
> first). This file only describes the app/factory control flow.

## Why human-in-the-loop (same as already-happening)
Aashiqana's creative generation **cannot run headlessly**: the Suno song AND the Leonardo
keyframes+Hailuo motion both need an interactive, logged-in **Chrome** session plus human
face/keyframe approvals. So — exactly like already-happening's Wan-2.6 motion gate — the headless
`produce_preview` session preps the deterministic parts and leaves a **`LEONARDO-TODO.md`** sentinel
for the human; `finalize_aashiqana.py` assembles + arms once the real clips are on disk.

## The app flow
1. **Plan** — ChannelDetail → "Plan content" (`plan_content`, generic idea engine) proposes song
   concepts. Or type a title + brief directly.
2. **Produce** — ChannelDetail "Produce" (`produce_channel`) → queues a `produce_preview` job.
   The worker branch (`factory_worker.py`, `produce_preview and key=="aashiqana"`) reads
   `SHORTS-TEMPLATE-LOCKED.md` and:
   - cuts the **word-first hookcut** + caption timing (if the Suno mp3 is on disk),
   - writes **`songs/<slug>/LEONARDO-TODO.md`** = the 8 locked prompts (1 anchor · 4 keyframes ·
     4 Hailuo motion), adapted to a **rotated setting** (not the previous short's location),
   - writes the manifest `episodes/ep<N>.json` + `description_short.txt`,
   - **if** the 4 motion clips + hookcut already exist, assembles + brands a preview,
   - pushes assets to Studio.
3. **Human (Chrome)** — generate the anchor + 4 keyframes (Nano Banana 2, Image-Ref) + 4 Hailuo
   motion clips per LEONARDO-TODO.md, approve the face, drop clips into `songs/<slug>/_motion/
   CLIP_{anchor,her,behind,kiss}.mp4`, delete the sentinel. (Suno song too, if not already made.)
4. **Review** — the preview lands in **StudioBoard** (`production_mode:direct`); watch it.
5. **Finalize & arm** — StudioBoard "Finalize" (`finalize_episode`) → the edge fn routes
   `channel_key=="aashiqana"` to a `shell_script` job running **`scripts/finalize_aashiqana.py`**
   (v3): assembles+brands from the human's clips **if** the branded Short isn't built yet,
   LUFS-normalises to the −14 spine, arms YouTube via `yt_upload.py --channel aashiqana
   --category 10 --audience general --synthetic --publish-at <ISO>`, writes the scheduled
   `factory_posts` row, flips the calendar item to `produced`, advances `aashiqana_last_ep`.

## Files that wire this (v18)
- `webapp/src/pages/ChannelDetail.jsx` — `PRODUCE_CFG['aashiqana']` (produce panel + copy). **[rebuild+deploy webapp]**
- `supabase/functions/factory-api/index.ts` — finalize selector routes aashiqana →
  `finalize_aashiqana.py`, tag `v3`. **[redeploy edge fn]**
- `scripts/factory_worker.py` — `produce_preview and key=="aashiqana"` branch.
- `scripts/finalize_aashiqana.py` — assemble-if-needed + LUFS + arm + DB sync + ep counter.
- `channels/aashiqana/SHORTS-TEMPLATE-LOCKED.md` — the locked craft recipe (the source of truth).
- Registry already present: worker `UPLOAD_DEFAULTS`/`DISPLAY_MAP`/`CHANNEL_SEED`,
  `channelColor.js` (#F472B6), `secrets/token_aashiqana.json`.

## Non-negotiables carried into the factory
Word-first hook · rotate the setting each song · tasteful-sensual only (YouTube-safe) ·
synthetic-media disclosure ON + AI disclosure in description · never a real celebrity likeness.
