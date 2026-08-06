-- 012_video_snapshots.sql — per-sync network snapshots ("Analytics 2.0")
-- House rules: all objects prefixed factory_, shared DB (touch nothing else),
-- RLS enabled with NO policies (service-role / edge-function access only).
--
-- Why: factory_video_stats holds per-video DAILY rows but the network is never
-- snapshotted as a whole, so nothing can diff "this sync vs the last one" (view
-- change, rank change, new/rising videos). Each analytics_sync now writes one row
-- per video here, stamped with a SINGLE sync_at for the whole run. Deltas =
-- the two most recent snapshots per video.
--
-- Lifetime views/likes/comments come from the Data API (video_meta), which the
-- worker fetches for EVERY channel regardless of the analytics source — so the
-- lifetime basis (and therefore the sync-to-sync delta) is clean even for
-- channels on the data_api_fallback path. window_* / avg_view_pct / subs_gained /
-- shares come from the trailing-window rows and are NULL/partial on fallback.

create table if not exists public.factory_video_snapshots (
  id           bigint generated always as identity primary key,
  sync_at      timestamptz not null,        -- ONE value per analytics_sync run
  channel_key  text not null,
  video_id     text not null,
  title        text,
  source       text not null default 'analytics_api',  -- analytics_api | data_api_fallback
  -- lifetime totals (Data API) — present for BOTH sources; basis for deltas
  views        bigint not null default 0,
  likes        bigint,
  comments     bigint,
  -- trailing-window snapshot (from the per-video daily rows; NULL/partial on fallback)
  window_views bigint,   -- analytics_api: window sum; fallback: single since-last delta
  window_days  int,      -- last_date - first_date + 1 (for honest velocity)
  avg_view_pct numeric,  -- views-weighted retention; NULL on fallback
  subs_gained  bigint,   -- window sum; NULL on fallback
  shares       bigint,   -- window sum; NULL on fallback
  rank         int,      -- within channel by window_views desc (1 = top); nulls last
  raw          jsonb default '{}',
  created_at   timestamptz default now(),
  unique (video_id, sync_at)
);

create index if not exists factory_video_snapshots_sync_idx
  on public.factory_video_snapshots (sync_at desc);
create index if not exists factory_video_snapshots_channel_sync_idx
  on public.factory_video_snapshots (channel_key, sync_at desc);
create index if not exists factory_video_snapshots_video_idx
  on public.factory_video_snapshots (video_id, sync_at desc);

-- RLS like the other factory_ tables: enabled, NO policies (service role only)
alter table public.factory_video_snapshots enable row level security;
