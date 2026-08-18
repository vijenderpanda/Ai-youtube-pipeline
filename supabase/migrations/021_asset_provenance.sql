-- 021_asset_provenance.sql — what a shipped episode was ACTUALLY made of.
-- Without this, moving a lock rewrites history: every past episode would appear
-- to have used the new revision. build_ep_v2._flush_provenance() writes one row
-- per resolved slot per build, recording the version AND why it was chosen.
-- House rules: additive only, factory_ prefix, RLS on with no policies, and the
-- 018 lesson — an EXPLICIT service_role grant (new tables here don't auto-grant).
create table if not exists public.factory_episode_assets_used (
  id            uuid primary key default gen_random_uuid(),
  calendar_id   uuid,            -- -> factory_calendar.id; no FK, per house pattern
  channel_key   text not null,
  ep            text,
  build_tag     text,            -- the --tag stem (v2/v3/v5…)
  asset_type    text not null,
  version_id    uuid,            -- -> factory_asset_versions.id (null when a literal default won)
  build_ref     text not null,   -- the exact string substituted into the render
  resolved_from text not null,   -- cfg | template | lock | default
  created_at    timestamptz default now()
);
create index if not exists factory_episode_assets_used_cal_idx     on public.factory_episode_assets_used (calendar_id);
create index if not exists factory_episode_assets_used_version_idx on public.factory_episode_assets_used (version_id);
create index if not exists factory_episode_assets_used_ch_idx      on public.factory_episode_assets_used (channel_key, asset_type);

-- close the episode -> shipped video chain (finalize_episode.py stamps it)
alter table public.factory_posts    add column if not exists calendar_id uuid;
alter table public.factory_calendar add column if not exists template_key text;
create index if not exists factory_posts_calendar_idx on public.factory_posts (calendar_id);

alter table public.factory_episode_assets_used enable row level security;
revoke all on table public.factory_episode_assets_used from anon, authenticated;
grant all  on table public.factory_episode_assets_used to service_role;
