# Staged Production Pipeline ("Studio")

> Contract doc for the fragment-first production mode. The factory can now produce a
> calendar item in **stages**: plan the asset list → generate each asset as its own
> queued job (thumbnails, stills, clips, VO, bookends…) → human reviews every asset in
> the dashboard Studio page (approve / revise with an effort knob) → when everything is
> approved, one click queues the final **assembly** job. Nothing is assembled until then.
>
> House rules preserved: all objects prefixed `factory_`, RLS enabled with NO policies,
> single shared DB, worker claims ONE job at a time (fragments queue serially — never
> two CPU-heavy generations at once), dashboard talks only to the `factory-api` edge
> function, worker is the only writer of job results.

## 1. Flow

```
factory_calendar item (planned/suggested)
   │  POST stage_calendar_item {id}
   ▼
plan_assets job (claude)  ── writes renders_out/assets_plan_<JOBID>.json
   │  worker ingests: factory_assets rows (v1, status=queued)
   │  + one generate_asset job per asset (serialized by the queue)
   ▼
generate_asset jobs (claude, one at a time)
   │  each writes renders_out/asset_out_<JOBID>.json
   │  worker uploads files, patches asset row → status=review
   ▼
Dashboard /studio/:calendarId  — preview every asset
   │  approve_asset | revise_asset {notes, model, effort} | skip_asset
   │  (revise ⇒ old row status=superseded, new row version+1 status=queued + new job)
   ▼
all latest versions approved (or skipped) → POST queue_assembly {calendar_id}
   ▼
assemble_episode job (claude) ── consumes approved assets by local_path,
   writes standard manifest_<JOBID>.json (v4) → factory_renders + draft factory_posts
   → calendar item flipped to 'produced'
```

## 2. Schema — migration `009_staged_assets.sql`

- `factory_assets` (RLS enabled, no policies):
  - `id uuid PK default gen_random_uuid()`
  - `calendar_id uuid not null` — the factory_calendar item
  - `channel_key text not null`
  - `asset_key text not null` — stable slug across versions, e.g. `thumbnail`, `scene_03_still`, `vo_master`, `intro_bookend`
  - `version int not null default 1`
  - `group_key text not null default 'other'` — `thumbnail | scene | clip | audio | bookend | overlay | other`
  - `kind text not null default 'image'` — `image | video | audio | text | other`
  - `title text default ''`
  - `spec jsonb not null default '{}'` — generation spec: `{prompt, params, revision_notes:[...]}`
  - `status text not null default 'queued'` — `queued | generating | review | approved | skipped | superseded | failed`
  - `job_id uuid` — the generate_asset job for THIS version
  - `filename text`, `storage_path text`, `poster_path text`, `local_path text`
  - `size_bytes bigint`, `duration_s numeric`
  - `notes text default ''` — reviewer feedback that requested this version
  - `model text`, `effort text` — knobs used for this version
  - `created_at timestamptz default now()`, `updated_at timestamptz default now()`
  - `unique (calendar_id, asset_key, version)`; indexes on `(calendar_id)`, `(status)`, `(job_id)`
- `factory_jobs`: add `meta jsonb not null default '{}'` — staged jobs carry
  `{calendar_id, asset_id?, asset_key?, version?}`. `factory_claim_job()` already
  returns the full row, so no RPC change.
- `factory_calendar`: add `production_mode text not null default 'direct'` — `direct | staged`.

**Asset status machine** (only latest version of each asset_key matters):
`queued → generating → review → approved` | `review/failed → superseded` (via revise) |
`queued/review/failed → skipped` | job failure → `failed` (revise = retry).

## 3. Job types (worker + edge fn)

| type | runner | prompt/contract |
|---|---|---|
| `plan_assets` | claude | Brief + channel guidelines + playbook → writes `renders_out/assets_plan_<JOBID>.json` = `{summary, assets:[{asset_key, group, kind, title, spec:{prompt, params}, effort?, model?}]}`. NO media generation. 6–20 assets typical. Worker ingests → factory_assets rows (status queued, version 1, model/effort defaulting to the calendar item's) + one `generate_asset` job per asset (meta filled, title `Asset: <asset_key> — <item title>`). |
| `generate_asset` | claude | Worker builds prompt at run time from the asset row (spec.prompt, params, revision_notes, channel guidelines, kind-specific rules). MUST generate exactly one primary file (plus optional poster jpg for videos) under `renders_out/staged/<calendar_id>/<asset_key>/v<version>/` and write `renders_out/asset_out_<JOBID>.json` = `{summary, files:[{path, role:'asset'|'poster'}]}`. NO assembly, NO posts. Worker uploads to bucket `factory-renders` at `<channel_key>/assets/<calendar_id>/<asset_key>/v<version>/<filename>`, patches the asset row → `review` (+ storage_path/poster_path/local_path/size/duration). Failure/cancel → asset `failed`. |
| `assemble_episode` | claude | Worker dumps `renders_out/staged_ctx_<JOBID>.json` = `{item, channel, assets:[approved latest versions with local_path, asset_key, kind, spec]}` and prompts claude to assemble the FINAL video using existing generator scripts + playbook params, then write the standard v4 `manifest_<JOBID>.json` (yt_title/yt_description/yt_tags/contributors). Existing upload flow runs (factory_renders + draft factory_posts). Then worker patches calendar item `id = meta.calendar_id` → status `produced`. |

Worker rules:
- `mark_calendar_produced` must NOT fire for `plan_assets` / `generate_asset`
  (calendar.job_id points at the plan job — excluding by job type is required).
- On claim of `generate_asset`: patch its asset row → `generating`.
- `RECAP_SKIP_TYPES` += `plan_assets`, `generate_asset` (assemble keeps recaps).
- plan ingest guards: skip insert if assets already exist for calendar_id (idempotent re-run).
- Failed `plan_assets` → existing reset path returns the calendar item to `planned`.

## 4. factory-api additions

GET (auth as today):
- `?r=staged` → `{items:[calendar rows where production_mode='staged' and status in (queued,produced)], counts:{<calendar_id>:{total, queued, generating, review, approved, skipped, failed}}}` (counts over LATEST versions only)
- `?r=episode_assets&calendar_id=` → `{item, assets:[all versions, newest first], jobs:[{id,type,status,title,created_at} for plan/generate/assemble jobs of this item]}`

POST actions:
- `stage_calendar_item {id}` — item must be `planned|suggested`; insert `plan_assets` job (prompt=brief, model/effort/ultracode from item, `meta:{calendar_id}`); patch item `{status:'queued', production_mode:'staged', job_id}`. 409 if already staged/queued.
- `approve_asset {id}` — row must be latest version, status `review` → `approved`.
- `revise_asset {id, notes, model?, effort?}` — row must be latest version, status `review|approved|failed`; notes required. Mark row `superseded`; insert new row (version+1, status `queued`, spec = old spec with `revision_notes` appended, notes, model/effort = overrides or inherited); insert `generate_asset` job (meta with the NEW asset id). 409 if a queued/running job already exists for this asset_key.
- `skip_asset {id}` — latest version, status `queued|review|failed` → `skipped`; if its job is still `queued`, cancel it.
- `queue_assembly {calendar_id}` — validate: every distinct asset_key's latest version is `approved|skipped`, at least one `approved`, no queued/running `assemble_episode` for this item. Insert `assemble_episode` job (meta `{calendar_id}`, model/effort from item). 409 with a human message otherwise.

All actions log `factory_events` (kinds: `assets_staged`, `asset_approved`, `asset_revision`, `asset_skipped`, `assembly_queued`; worker adds `asset_ready`, `assets_planned`).

## 5. Dashboard (webapp)

- New nav entry **Studio** → `/studio`: cards for staged episodes (channel accent, title,
  planned date, progress `approved+skipped / total`, counts by status, ▶ open board).
- `/studio/:calendarId` board: assets grouped by `group_key`; each AssetCard shows
  preview (poster or media via `RENDERS_BASE + storage_path`, image→Lightbox,
  video→inline `<video controls>`, audio→`<audio>`), status chip, `vN` badge with
  version history (older versions previewable), and actions: **Approve**,
  **Revise** (panel: feedback notes required + model select + effort knob low→max),
  **Skip**. Header: progress bar + **Assemble** button (enabled only when all latest
  versions approved/skipped; confirm dialog) + a "jobs run one-at-a-time on the Mac"
  queue hint showing how many generation jobs are queued/running.
- CalendarDrawer: "Produce in stages" button beside the existing queue action for
  `planned|suggested` items → `stage_calendar_item` → link to the board.
- Poll with `usePoll` (8s board, 15s studio list). `jobMeta.js` TYPE_LABELS for the
  three new job types. Reuse existing chips/cards/drawer/toast CSS primitives.

## 5b. v10 — exception-based review + draft preview

- **Auto-approve v1**: a successful first generation lands `approved` directly (the
  factory's own QC covers it). Revisions (v2+) exist because the human flagged
  something, so those land in `review` and wait for explicit confirmation.
- **Docs rail**: `kind='text'` assets (script, beat map, research, metadata) are
  factory internals — the board tucks them into a collapsed "Factory docs" section
  instead of the filmstrip. Open on demand; same preview/inspector.
- **Frames**: video assets also emit start/mid/end stills (`role:"frame"` in
  asset_out; stored in `factory_assets.frames` jsonb) so pieces are judged from
  real frames without playing everything.
- **Overlay composites**: `group='overlay'` assets MUST render their poster as an
  honest composite over the actual target frame (Ep11 chip-over-content rule).
- **Draft preview**: POST `queue_preview {calendar_id}` (allowed while revisions
  are still in review; 409 while anything is queued/generating/failed) → worker
  `preview_episode` job → fast 540×960 DRAFT-watermarked stitch of the current
  latest assets → uploaded to `<channel>/assets/<calendar_id>/_preview/` and
  stamped on `factory_calendar.preview_path/preview_at` (migration 011). The board
  shows it as a program monitor with a Rebuild button. Never published, no post,
  no calendar flip.
- Review flow is now: watch fragments land approved → open the draft preview →
  revise only what's wrong (revision confirm = the only manual approve) → Assemble.

## 6. Ops notes

- One worker, one job: heavy fragment renders can never overlap; the queue IS the
  concurrency control. Queue order = `created_at` (oldest first).
- Local disk stays the source of truth for assembly (`local_path`); storage bucket
  copies exist for dashboard preview, same as renders today.
- 45-min per-job timeout applies per fragment (generous — fragments are small).
- Deploy checklist when this doc changes behavior: apply migration → deploy
  `factory-api` → restart `com.factory.worker` (only when no job running) → deploy webapp.
