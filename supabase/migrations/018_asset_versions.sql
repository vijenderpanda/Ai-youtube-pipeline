-- 018_asset_versions.sql — Studio asset version history + per-(channel,asset_type) live lock
-- House rules: additive only, all objects prefixed factory_, shared DB (touch nothing
-- else), RLS enabled with NO policies (service-role / edge-function only).
-- Backs docs/STUDIO-ASSET-VERSIONING.md Phase 1+2. Root-cause fix for the 2026-08-18
-- stale-outro bug: build_ep_v2 resolves the LOCKED version instead of a silent fallback.

create table if not exists public.factory_asset_versions (
  id                uuid primary key default gen_random_uuid(),
  channel_key       text not null,
  asset_type        text not null,                   -- MUST match build_ep_v2 _LOCK_CFG_KEY keys:
                                                      -- outro_sting|host_outfit|music_bed|hook_image|remotion_comp
  version           int  not null default 1,
  label             text default '',
  storage_path      text,                            -- bucket path <channel>/assets/... (webapp preview)
  thumb_path        text,                            -- poster/thumb bucket path
  parent_version_id uuid,                            -- lineage; no FK, per house pattern
  status            text not null default 'candidate', -- locked|candidate|retired|failed
  source            text default 'import',            -- import|manual|regeneration|produce
  created_at        timestamptz default now(),
  meta              jsonb not null default '{}'::jsonb, -- meta.build_ref = exact string build_ep_v2 substitutes
  unique (channel_key, asset_type, version)
);

create index if not exists factory_asset_versions_channel_type_idx
  on public.factory_asset_versions (channel_key, asset_type);
create index if not exists factory_asset_versions_status_idx
  on public.factory_asset_versions (status);
create index if not exists factory_asset_versions_parent_idx
  on public.factory_asset_versions (parent_version_id);

-- one lock row per (channel, asset_type): which version is currently live
create table if not exists public.factory_asset_locks (
  channel_key       text not null,
  asset_type        text not null,
  locked_version_id uuid,                            -- -> factory_asset_versions.id; no FK, per house pattern
  locked_at         timestamptz default now(),
  updated_at        timestamptz default now(),
  primary key (channel_key, asset_type)
);

alter table public.factory_asset_versions enable row level security;
alter table public.factory_asset_locks    enable row level security;
revoke all on table public.factory_asset_versions from anon, authenticated;
revoke all on table public.factory_asset_locks    from anon, authenticated;
