# FACTORY — local worker daemon

The content factory's execution layer. The dashboard writes jobs into a Supabase
queue; this worker (running on the Mac) claims them one at a time and runs each
as a real Claude Code session. The owner's Claude Code **subscription** does all
reasoning — **no Anthropic API key is used anywhere** (the worker even strips
`ANTHROPIC_API_KEY` from the child environment).

## Architecture

```
dashboard  ──insert──▶  Supabase (factory_jobs, status=queued)
                              │
                              ▼  POST /rest/v1/rpc/factory_claim_job  (atomic, SKIP LOCKED)
                    scripts/factory_worker.py  (this Mac, launchd)
                              │
                              ▼  claude -p <assembled prompt> --model … --effort …
                        Claude Code (subscription)  →  renders_out/manifest_<JOBID>.json
                              │
                              ▼  upload files → storage bucket factory-renders (public)
                                 insert factory_renders rows, job → done, factory_events
```

- **Live logs:** stdout of the `claude` run is summarized and PATCHed into
  `factory_jobs.logs` every ~4 s (capped at 200 KB) so the dashboard streams progress.
- **Timeout:** 45 min per job → process killed, job `failed`.
- **Manifest contract:** every prompt ends with an instruction to write
  `renders_out/manifest_<JOBID>.json` = `{"summary": str, "files": [{path, kind, channel_key}]}`.
  Files are uploaded to `factory-renders/<channel_key>/<job_id>/<filename>` (x-upsert).
  Local files are **never deleted**.
- **Startup seeding (idempotent):** `factory_channels` from
  `docs/PRODUCTION-PLAYBOOK.md` §14 (on-conflict **do nothing** — dashboard edits
  win forever) and `factory_generators` from the first docstring line of every
  `scripts/*.py` (on-conflict **update** description + updated_at).

## Job types → prompt assembly

| type | prompt |
|---|---|
| `produce_short` | "Produce a short for channel <key>." + channel `guidelines` + job.prompt + standing rules (playbook, premium bar) |
| `record_demo` | record_demo.py + pro-styles framing preamble + job.prompt |
| `custom` | job.prompt verbatim + repo/playbook conventions line |
| `new_channel_scaffold` | scaffold preamble + job.prompt |
| `analyze_and_suggest` | **v2/v4** — content-strategist preamble + path to a context dump the worker writes first (`renders_out/analysis_ctx_<JOBID>.json`: channels, last-30d `factory_stats`, calendar −14d…+21d, last 20 jobs, **v4:** last 10 `factory_insights` + generator catalog). **v4 prompt:** real web research first (WebSearch/WebFetch, findings cited in each `reason`), optional `kind:'factory'` self-improvement suggestions, per-channel `insights` block. Claude writes `renders_out/suggestions_<JOBID>.json`; worker ingests it (see below) |
| `analytics_sync` | **v2** — handled **natively by the worker, no claude call** (see below) |
| `suggest_brief` | **v4** — per-channel strategist. Worker first writes `renders_out/brief_ctx_<JOBID>.json` (channel guidelines + last-14d stats + last 10 job titles + next-14d calendar), claude researches the niche (WebSearch) and writes `renders_out/brief_<JOBID>.json` = `{title, brief, tags}`; the worker copies that JSON into `factory_jobs.result`. **No manifest, no renders.** Dashboard flow: `POST {action:'suggest_brief', channel_key, seed}` on factory-api creates the job (model sonnet / effort medium), client polls `?r=job&id=` until `done` and reads `result` |
| `plan_assets` | **v9 (Studio)** — breaks a calendar brief into a per-asset plan; writes `renders_out/assets_plan_<JOBID>.json`; worker ingests → `factory_assets` rows + one `generate_asset` job per asset. No media generated. See `docs/STAGED-PIPELINE.md` |
| `generate_asset` | **v9 (Studio)** — generates ONE fragment (still, clip, VO, thumb, bookend…) for a `factory_assets` row; writes `renders_out/asset_out_<JOBID>.json`; worker uploads + flips the asset row to `review`. No assembly, no posts |
| `assemble_episode` | **v9 (Studio)** — final assembly from approved assets only; worker dumps `renders_out/staged_ctx_<JOBID>.json` (approved assets w/ local paths); job ends with the standard v4 manifest → renders + draft post → calendar item `produced` |

All claude-run prompts (except `suggest_brief`) end with the manifest instruction.
**v4 manifest extension:** each `files[]` entry may also carry
`yt_title`, `yt_description`, `yt_tags` and
`contributors: [{generator: "<file>.py", role: "karaoke captions"}]`.
After upload the worker stores `factory_renders.local_path`, inserts
`factory_render_contributors` rows (generator names normalized to `<file>.py`),
and creates a **draft `factory_posts` row for every video** (see posts lifecycle).

### Model + effort + ultracode (v2)

- `model`: `fable` → `claude-fable-5`; `opus`/`sonnet`/`haiku` and anything else pass
  through to `claude --model` unchanged. `effort`: `low|medium|high|xhigh|max`, passed as-is.
- `ultracode` (boolean on `factory_jobs` **and** `factory_calendar`): when true the worker
  prepends the literal keyword `ultracode` as the **first line** of the claude prompt,
  opting the headless run into multi-agent orchestration.

## Calendar flow (v2)

`factory_calendar` holds dated content plans per channel
(`status: planned | suggested | queued | produced | skipped`,
`origin: manual | ai_suggestion`, plus per-item `model/effort/ultracode`).

- Dashboard creates/edits items via the `factory-api` edge function
  (`?r=calendar`, `create_calendar_item`, `update_calendar_item`).
- `queue_calendar_item` turns an item into a `factory_jobs` row (prompt = item brief,
  carries model/effort/ultracode) and sets the item `queued` + `job_id`.
- **Worker responsibility:** whenever a job finishes `done` and a calendar item has
  `job_id` = that job, the worker flips the item to `produced`.

## Staged production — "Studio" (v9)

Full contract: `docs/STAGED-PIPELINE.md`. Instead of one `produce_short` job doing
everything, a calendar item can be produced **fragment-first**:

```
stage_calendar_item ─▶ plan_assets job ─▶ factory_assets rows (one per fragment)
        ─▶ generate_asset jobs (queued, strictly one at a time)
        ─▶ dashboard /studio review: approve | revise{notes, model, effort} | skip
        ─▶ all approved → queue_assembly ─▶ assemble_episode job ─▶ renders + draft post
```

- `factory_assets` (migration 009): one row per `(calendar_id, asset_key, version)`;
  statuses `queued|generating|review|approved|skipped|superseded|failed`.
  A revision supersedes the old version and queues a fresh `generate_asset` job with
  the reviewer's notes + per-revision model/effort knobs.
- `factory_jobs.meta` (jsonb) carries `{calendar_id, asset_id, asset_key, version}`.
- `factory_calendar.production_mode`: `direct` (classic) | `staged`.
- Fragments upload to `factory-renders/<channel>/assets/<calendar_id>/<asset_key>/v<N>/`;
  `local_path` on the Mac remains the assembly source of truth.
- **Nothing is assembled until every asset's latest version is approved or skipped** —
  and the single-claim worker guarantees no two generations ever run concurrently.

## Analytics + suggestion flow (v2)

```
dashboard "Sync analytics"  ──▶  factory_jobs (type=analytics_sync, model=fable)
                                        │  claimed by worker — NATIVE, no claude call
                                        ▼
                    scripts/network_stats.py  (best effort; on failure keep existing csv)
                                        │
                                        ▼
              docs/stats/history.csv  ──aggregate──▶  factory_stats upsert
              (display name → key via DISPLAY_MAP;    (per channel per date: Σ views,
               unmatched names logged)                 max subs, raw per-video jsonb,
                                        │              on conflict channel_key,date)
                                        ▼
              auto-insert follow-up factory_jobs row (type=analyze_and_suggest,
              channel_key=_network, inherits model + ultracode, effort=high)
                                        │  claimed by worker — CLAUDE job
                                        ▼
              renders_out/analysis_ctx_<JOBID>.json  ──▶  claude (content strategist)
                                        │
                                        ▼
              renders_out/suggestions_<JOBID>.json  ──ingest──▶  factory_calendar rows
              (status='suggested', origin='ai_suggestion',       + factory_events
               suggestion_reason shown as badge tooltip)           'suggestion'
                                        │
                          user reviews on dashboard ──▶ queue_calendar_item ──▶ job
                                        │                                        │
                                        ▼                                        ▼
                                  or 'skipped'                        job done → item 'produced'
```

- `analytics_sync` result: `{rows_upserted, video_rows, video_sources, reauth_needed,
  follow_up_job_id}` (+ a human `note` naming re-auth channels when any).
- `analyze_and_suggest` result: `{summary, uploaded, posts, suggestions, analysis_summary, insights}`.
- YouTube Analytics lags ~48h; the strategist prompt says to judge small channels
  by trend, not absolutes.
- **v4:** suggestions may carry `kind:'factory'` (improvements to the factory itself —
  concrete generator create/update tasks naming `scripts/<file>`); those calendar rows
  get `kind='factory'` and `type='custom'`. The `insights` block
  (`{channel_key: {summary, details:{wins,risks,next}}}`) is inserted into
  `factory_insights` and fed back into the next analysis run.

### Per-video daily stats (v5)

`analytics_sync` ALSO pulls **per-video daily metrics** into `factory_video_stats`
(unique on `channel_key, video_id, date`), for every channel in `UPLOAD_DEFAULTS`
using its own OAuth token (`yt_creds` refreshes non-interactively from an absolute
`secrets/` path — the worker **never** starts an OAuth flow):

- **Preferred source `analytics_api`:** YouTube Analytics API v2
  `reports.query(ids=channel==MINE, dimensions=video,day, metrics=views,
  estimatedMinutesWatched, averageViewDuration, averageViewPercentage,
  subscribersGained, likes, comments, shares)` over the last 30 days. A bare
  `video,day` query 400s — the worker chunks the channel's upload ids into
  multi-value `filters=video==id1,id2,…` groups of 5 (≤155 potential rows/query;
  `startIndex` paging silently drops rows on this report, so chunking is the only
  reliable way). The existing tokens' `youtube` scope is accepted by the
  Analytics API — verified live on all 5 channels.
- **Fallback `data_api_fallback`:** if the Analytics call 403s (token lacks an
  analytics-capable scope), the channel falls back to Data API `videos.list`
  lifetime totals turned into **daily deltas vs the previous stored day**
  (baseline: latest prior fallback row's `raw.lifetime`, else the last pre-today
  `history.csv` snapshot; first sighting seeds the lifetime total with
  `raw.baseline=true`). Only views/likes/comments populate; watch/retention/
  subs/shares stay null. The job result's `reauth_needed` + `note` name the
  channels needing a **one-time manual re-auth** with `yt-analytics.readonly`.
- Titles come from Data API `videos.list` snippets (fallback: `history.csv`).
- One channel failing never kills the sync (`video_sources[key]='error'`, logged).
- The `analyze_and_suggest` context dump gains a **`video_summary`** section —
  top/bottom 3 videos per channel by 30d views + views-weighted `avg_view_pct` —
  and the prompt tells the strategist to cite specific videos as evidence.

Dashboard reads (factory-api, keeps v1–v4 routes):
`GET ?r=video_stats&channel=K&days=N` (default 30, max 90 — raw rows, date desc /
views desc) and `GET ?r=video_summary&channel=K&days=N` — per-video aggregates
over the window computed **in SQL** via the edge function's direct Postgres pool:
`{videos:[{video_id, title, total_views, watch_minutes, avg_view_pct (weighted),
subs_gained, likes, comments, first_date, last_date, trend:[daily views]}]}`.

## Posts lifecycle (v4)

Every VIDEO uploaded from a job manifest becomes a **draft** `factory_posts` row
(`yt_title` from the manifest or the job title, `audience`/`synthetic` prefilled from
the worker's per-channel `UPLOAD_DEFAULTS`). The user edits and arms it on the
dashboard; the worker is the only thing that ever uploads.

**v8 — the draft's `publish_at` is prefilled too** (`default_publish_at`): the
linked calendar item's `planned_date` (join via `job_id`) at
`factory_settings.default_publish_time` (default `16:00` local `auto_sync_tz`
= the network's standard 10:30Z slot); no calendar item → the next upcoming
slot. Always clamped to the future (YouTube rejects a past `publishAt`). The
date stays fully editable before arming — this only kills the "waiting for a
manual date pick" dead-end in the plan→generate→post flow.

**v8 — shipped-before-the-factory content**: `scripts/backfill_calendar_published.py`
pulls real `snippet.publishedAt` per channel from the YouTube Data API and
writes `factory_calendar` (`origin='backfill'`, status `produced`) +
`factory_posts` (`status='published'`, real `video_id`/`publish_at`) pairs
linked by a **synthetic shared `job_id`** (no `factory_jobs` row; the drawer
hides "View job" for `origin='backfill'`). Idempotent by `video_id` + loose
title match; safe to run while the worker is live.

```
                    dashboard edits (update_post: title/desc/tags/publish_at…)
                                   │
   job done ──▶  draft  ──arm_post─▶  armed  ──worker poll──▶  uploading
   (event          ▲                    │ (needs yt_title +        │ scripts/yt_upload.py
   'post_draft')   └──disarm_post───────┘  future publish_at)      │ --channel <token> --video …
                                                                   │ --publish-at <RFC3339 UTC>
                                             ┌─────────────────────┴───────────┐
                                             ▼ success                         ▼ failure
                                         scheduled  (+video_id,            failed (+error,
                                          event 'post_scheduled')           event 'post_failed')
                                             │
                                             ▼  publish_at passes (lazy flip on poll)
                                         published  (event 'post_published')
```

- The publisher runs **every poll cycle**: it fetches `status='armed'` only — drafts
  are never touched — claims each with a conditional `armed→uploading` PATCH (no
  double upload), then runs `scripts/yt_upload.py` with the channel's token file
  (`UPLOAD_DEFAULTS[channel].token_file` → `--channel` arg), `--publish-at` (RFC3339
  UTC from `publish_at`), `--audience kids|general`, `--synthetic` when set,
  `--tags`, `--desc-file` (description written to `renders_out/post_desc_<ID>.txt`)
  and an optional `--thumbnail` when the same job produced an image render with
  "thumb" in its filename that is still on disk.
- Per-channel upload defaults: lulla + language-abc + vehicles → `kids`, no
  synthetic flag; claude-tricks + aashiqana → `general` audience + `--synthetic`
  (AI-content disclosure). Token files: `token.json` (lulla), `token_poly.json`
  (language-abc), `token_vehicles.json`, `token_claude-tricks.json`,
  `token_aashiqana.json`.
- `scheduled` rows flip to `published` lazily once `publish_at` passes (no YT poll).

## Daily auto-sync (v4)

`factory_settings`: `auto_sync_hour` (default `07:30`) + `auto_sync_tz`
(default `Asia/Kolkata`), seeded idempotently on worker start. Every ≤5 min the
poll loop checks the clock in that timezone; once past the hour it queues one
`analytics_sync` job (model `fable`) — guarded twice (no `analytics_sync` job
created today AND no `auto_sync` event today) so it fires **at most once per day**,
which then drives the whole stats → suggestions → insights chain above.

## The ONE manual step

`secrets/factory.env` needs the Supabase **service-role** key (it can't be
committed or fetched automatically):

1. Supabase dashboard → project `xfqyovimnqdghiekicqr` → **Settings → API keys**
2. Copy the `service_role` secret
3. Add to `/Users/vijenderpanda/Ai-youtube-pipeline/secrets/factory.env`:
   ```
   SUPABASE_SERVICE_KEY=<paste here>
   ```

Until then the worker exits immediately with instructions (by design).

## Testing

```bash
# print the exact claude commands for fake jobs (produce_short, fable+ultracode,
# suggest_brief) AND the exact yt_upload.py command for a fake armed post
# (constructed, never executed):
python3 scripts/factory_worker.py --dry-run

# single claim attempt (seeds channels/generators/settings, claims ≤1 job,
# runs one publisher/auto-sync cycle, exits):
python3 scripts/factory_worker.py --once
```

## Install as launchd daemon

```bash
mkdir -p ~/Library/LaunchAgents /Users/vijenderpanda/Ai-youtube-pipeline/logs
cp /Users/vijenderpanda/Ai-youtube-pipeline/scripts/com.factory.worker.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.factory.worker.plist

# status / logs
launchctl print gui/$(id -u)/com.factory.worker | head
tail -f /Users/vijenderpanda/Ai-youtube-pipeline/logs/factory_worker.log

# stop / restart
launchctl bootout gui/$(id -u)/com.factory.worker
launchctl kickstart -k gui/$(id -u)/com.factory.worker
```

## DB objects (created separately)

Tables `factory_channels/jobs/renders/generators/stats/events/settings/calendar`
(all RLS-enabled, no policies — service role + edge function only),
RPC `factory_claim_job()` (security definer, `FOR UPDATE SKIP LOCKED` — returns the
full row, so new columns like `ultracode` flow through automatically),
public storage bucket `factory-renders`.

v2 schema: `factory_jobs.ultracode boolean default false`; `factory_calendar`
(id, channel_key, planned_date, title, brief, type, status, origin,
suggestion_reason, model, effort, ultracode, job_id, created_at) with indexes on
(channel_key, planned_date) and (status); `factory_stats` has a unique index on
(channel_key, date) for the analytics upsert.

v4 schema: `factory_posts` (draft→armed→uploading→scheduled→published|failed, see
posts lifecycle), `factory_insights` (per-channel strategist takeaways),
`factory_render_contributors` (render_id, generator, role — which script did what
on each render), `factory_generators.tags jsonb` + `.scope`
(network | multi | single:<channel_key>), `factory_calendar.kind`
(content | factory), `factory_renders.local_path`, and `factory_settings` rows
`auto_sync_hour` / `auto_sync_tz`.

v5 schema: `factory_video_stats` (id identity pk, channel_key, video_id, date,
title, views, watch_minutes, avg_view_duration_s, avg_view_pct, subs_gained,
likes, comments, shares, `source` 'analytics_api'|'data_api_fallback', raw jsonb,
**unique(channel_key, video_id, date)** — the analytics_sync per-video upsert
target; indexes on (channel_key, date) and (video_id)). RLS-enabled, no policies,
like every other factory table.
