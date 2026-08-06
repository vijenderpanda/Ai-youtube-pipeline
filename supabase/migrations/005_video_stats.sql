-- Factory v5: per-video daily analytics (YouTube Analytics API rows)
-- (all objects prefixed factory_; shared DB — touch nothing else)

create table if not exists public.factory_video_stats (
  id bigint generated always as identity primary key,
  channel_key text not null,
  video_id text not null,
  date date not null,
  title text,
  views bigint default 0,
  watch_minutes numeric,
  avg_view_duration_s numeric,
  avg_view_pct numeric,
  subs_gained bigint,
  likes bigint,
  comments bigint,
  shares bigint,
  source text default 'analytics_api',
  raw jsonb default '{}',
  unique (channel_key, video_id, date)
);

create index if not exists factory_video_stats_channel_date_idx
  on public.factory_video_stats (channel_key, date);

create index if not exists factory_video_stats_video_idx
  on public.factory_video_stats (video_id);

-- RLS like the other factory_ tables: enabled, NO policies (service role only)
alter table public.factory_video_stats enable row level security;
