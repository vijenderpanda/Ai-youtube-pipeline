-- 025_plan_produce_loop.sql — Sprint 5 (Plan -> Produce loop) foundation.
-- Adds the persistence Sprint 5 needs AROUND the existing pick/produce path; the
-- PICK itself needs no new column (factory_calendar.template_version_id already
-- exists, 020). Two homes, deliberately split to keep the build's ONE-SELECT
-- resolve intact (build_ep_v2 resolves the whole locked cast+sequence from a single
-- factory_template_versions row):
--   * generation_manifest / auto_mode / manifest_version_lock ride as columns on
--     factory_calendar — a row build_ep_v2 ALREADY reads (select *), so it gains NO
--     second select. The manifest is the pre-render list of every asset the build
--     WILL make (VO/host/b-roll/statbars/hook/music/outro), each linked to its
--     scene(s), free|paid, low-confidence flagged.
--   * factory_episode_beat_review is a CHILD table for per-beat REVIEW state
--     (swap/regen/confidence/notes) that needs per-row updates. It is read only by
--     the webapp board (?r=episode_assets), NEVER by the build-read path — so it
--     can't leak into the one-select resolve.
-- House rules (reaffirmed 018/020/021/024): additive only, factory_ prefix, NO
-- foreign keys, RLS on with NO policies, and — the 018 lesson — an EXPLICIT
-- service_role grant (new tables don't auto-grant; without it the edge fn 500s).
-- Additive + degrades gracefully: a build with no manifest / classic produce with
-- no locked _sequence is byte-identical to today.

-- (a) per-piece plan/produce state on the calendar row (rides the existing select *)
alter table public.factory_calendar
  add column if not exists generation_manifest  jsonb;                          -- frozen per-piece asset manifest (null = not composed yet)
alter table public.factory_calendar
  add column if not exists auto_mode            boolean not null default false; -- run all beats with minimal review; STILL stops at the arm gate
alter table public.factory_calendar
  add column if not exists manifest_version_lock text;                          -- the template_version_id (+ lock-state) the manifest was composed against, to detect drift

-- (b) per-beat REVIEW state — child table, webapp-read only, out of the build path
create table if not exists public.factory_episode_beat_review (
  id             uuid primary key default gen_random_uuid(),
  calendar_id    uuid not null,          -- -> factory_calendar.id; no FK, per house pattern
  channel_key    text not null,
  position       int  not null,          -- 0-based scene index, aligned to composition._sequence position
  block_ref      text,                   -- what the beat resolves to (cookbook id / host label / layout) — the manifest/provenance ref
  swap_asset_key text,                   -- operator override: use this asset_key for the beat instead of the auto pick
  regen_kind     text,                   -- null | 'free' | 'paid' — a queued per-beat regeneration and its cost tier
  confidence     real,                   -- beat-level generation confidence (auto-compose score, normalized 0..1); low = flag for review
  note           text,
  updated_at     timestamptz default now(),
  unique (calendar_id, position)         -- one review row per scene (mirrors factory_template_blocks' position uniqueness)
);
-- per-episode read (a piece's beat-review rows) is served by this index.
create index if not exists factory_episode_beat_review_cal_idx on public.factory_episode_beat_review (calendar_id);

alter table public.factory_episode_beat_review enable row level security;
revoke all on table public.factory_episode_beat_review from anon, authenticated;
grant all  on table public.factory_episode_beat_review to service_role;
