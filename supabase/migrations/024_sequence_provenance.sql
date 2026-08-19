-- 024_sequence_provenance.sql — the SEQUENCE twin of 021_asset_provenance.sql.
-- 021 records which asset REVISION filled each cast slot per build; this records
-- which BLOCK played at each position in the composition sequence per build, so a
-- produced Short can be diffed against its locked composition._sequence (Sprint-4
-- block reconciliation) and a silent block drop/swap is legible on screen instead
-- of vanishing. Written one row per locked _sequence block by
-- build_ep_v2._flush_sequence_provenance(); read via ?r=episode_assets as
-- `sequence`, mirroring how `provenance` carries the cast.
-- House rules (reaffirmed 018/020/021): additive only, factory_ prefix, NO foreign
-- keys, RLS on with NO policies, and — the 018 lesson — an EXPLICIT service_role
-- grant (new tables here don't auto-grant; without it the edge fn 500s).
create table if not exists public.factory_episode_blocks_used (
  id            uuid primary key default gen_random_uuid(),
  calendar_id   uuid,             -- -> factory_calendar.id; no FK, per house pattern
  channel_key   text not null,
  ep            text,
  build_tag     text,             -- the --tag stem (v2/v3/v5…)
  position      int  not null,    -- 0-based play order within the sequence
  block_type    text,             -- hook | host | broll | statbars | outro | slot | cards
  layout        text,             -- the layout id, or null for non-spatial blocks
  ref           text,             -- what filled the block (cookbook id / host label / layout) — the build_ref analog
  rendered      boolean default false,   -- did this locked block produce a segment? (false = a real divergence)
  resolved_from text default 'template', -- always the locked composition._sequence today
  created_at    timestamptz default now()
);
-- per-episode read (a piece's built blocks in play order) is served by this index;
-- the app dedups by position keeping the most-recent build (order created_at desc).
create index if not exists factory_episode_blocks_used_cal_idx on public.factory_episode_blocks_used (calendar_id);

alter table public.factory_episode_blocks_used enable row level security;
revoke all on table public.factory_episode_blocks_used from anon, authenticated;
grant all  on table public.factory_episode_blocks_used to service_role;
