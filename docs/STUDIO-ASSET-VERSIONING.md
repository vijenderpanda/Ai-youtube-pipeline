# Studio Asset Versioning & Regeneration — Design

> **Status: PHASE 1+2 SHIPPED (2026-08-18).** Migration `018_asset_versions.sql` applied to
> `artha`; 9 assets registered as v1=locked + 4 build locks (`scripts/backfill_asset_versions.py`);
> `build_ep_v2.resolve_locked()` reads the lock (per-ep > lock > default, None-safe); `?r=assets`
> GET + `lock_asset` POST on factory-api (deployed); Studio **Assets** board live (`/assets`).
> Phases 3–5 (HeyGen face pool, mix-&-match preview, regenerate-via-worker) remain. Full spec below.
>
> **Why:** the 2026-08-18 Artifacts-short production hit avoidable confusion — the build
> silently fell back to the OLD generic outro sting (the locked Ep11-style card wasn't
> wired), and "which host / which outro" was unclear. There is no single, visible source
> of truth for reusable brand assets, their LOCKED version, or their iteration history.
> This system makes the locked version obvious in Studio and makes swapping/regenerating safe.

## 1. Assets under version control
Every reusable brand/production asset gets versions + a lock:
- **Intro** sting
- **Outro** card (question-CTA, `gen_outro_card.py`)
- **Host / Sol pip frames** — the HeyGen face pool (see §4; only 3 slots exist)
- **Step chips** (STEP 1/3 … + corner placement)
- **Component library** — the "#05 card", no-types components, and other Remotion pieces (`BuildClub.tsx` etc.)
- **Music beds**
- **Sample/reference frames**

## 2. Core concepts
- Each **asset type** has ordered **versions** (v1, v2, …). Exactly one is **LOCKED** = the production default.
- **Lineage**: each version records the version it was derived from, so Studio can show "v3 (locked) ← v2 ← v1" and drill down to any older one.
- **Status** per version: `locked` · `candidate` (awaiting review) · `retired`.
- **Mix & match**: preview a sample render from a chosen combo (intro + outro + host + chips) *before* locking.
- **Regenerate**: describe a change in plain English → a worker job regenerates the asset via `claude -p` + the matching `gen_*.py` → new **candidate** appears in Studio → **keep** (lock) or **discard** (regenerate again anytime).

## 3. Data model (Supabase)
- `factory_asset_versions` — `id, channel, asset_type, version, label, storage_path, thumb_path,
  parent_version_id (lineage), status, source ('manual' | regeneration prompt), created_at, meta`.
- `factory_asset_locks` — `channel, asset_type → locked_version_id` (the current production default; one row per (channel, asset_type)).

## 4. HeyGen face pool (the 3-slot constraint)
HeyGen photo-avatars are capped at **3 slots** ([[heygen-account-constraints]]). The system tracks
those 3 as host-face versions and lets us **lock which face(s) go to production** — we can lock **1 or 2**
(note recorded here so we never assume 3 are usable). Currently Sol is pinned to `outfit_11_sol_magenta`
([[host-pinned-to-ep11]]); rotation held until `HOST_OUTFIT_POOL=on`. Locking here replaces that env flag
with a visible, per-channel choice.

## 5. Studio UI (webapp)
- **Assets board** — per asset type: the LOCKED version shown large (thumb + label + "locked since"),
  with a version rail beneath; drill down to see older versions and their lineage.
- **Lock / unlock** a version from the board (writes `factory_asset_locks`).
- **Face-pool panel** — the 3 HeyGen slots; lock 1–2 for production.
- **Mix-&-match preview** — pick intro/outro/host/chips → "render sample" → watch before locking.
- **Regenerate** — a "what to change" box on any asset → spawns a worker job → candidate returns → keep/discard.

## 6. Worker + build-pipeline integration (the actual fix)
- **New job type `asset_regenerate`** — `meta: {channel, asset_type, base_version_id, instructions}`.
  Worker runs `claude -p` (or the deterministic `gen_*.py`) → uploads the result as a **candidate**
  version → StudioBoard surfaces it. (Uses the existing `shell_script` / `claude -p` worker paths.)
- **`build_ep_v2.py` reads the LOCKED version** per asset type from `factory_asset_locks` instead of a
  hardcoded/defaulted path. **This is the root-cause fix** for the 2026-08-18 stale-outro bug: the source
  of truth becomes the lock, and it is visible in Studio — no silent fallback to an old default.

## 7. Phased plan (smallest valuable increments first)
- **Phase 1 — Foundation & visibility:** data model + a one-off backfill that registers today's assets
  (intro, outro card, Sol faces, step-chip style, key components) as versions and marks the current one
  `locked`. Studio read-only "Assets" board showing locked + history. *Delivers: "which is locked right now" is finally visible.*
- **Phase 2 — Lock + wire (kills the confusion):** lock/unlock from Studio; `build_ep_v2` resolves asset
  paths from `factory_asset_locks`. *Delivers: the build can never silently use a stale asset again.*
- **Phase 3 — Face pool:** HeyGen 3-slot management + production lock (1–2 faces).
- **Phase 4 — Mix-&-match preview:** sample render from a chosen intro/outro/host/chips combo.
- **Phase 5 — Regenerate loop:** the `asset_regenerate` worker job + claude-p regeneration + keep/discard.

**Recommendation:** build **Phase 1 + 2 first** — they are the smallest change that directly removes the
"which outro / which host" confusion, and everything else layers on top.
