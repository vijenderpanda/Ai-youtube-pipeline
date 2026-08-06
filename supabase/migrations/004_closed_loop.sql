-- Factory v4: closed loop — posts pipeline, insights, render contributors,
-- generator scope/tags, calendar kind, auto-sync settings.
-- (all objects prefixed factory_; shared DB — touch nothing else)

-- Upload/publish pipeline rows
create table if not exists public.factory_posts (
  id uuid primary key default gen_random_uuid(),
  channel_key text,
  render_id uuid,
  job_id uuid,
  local_path text,
  yt_title text,
  yt_description text default '',
  tags jsonb default '[]',
  publish_at timestamptz,
  audience text,
  synthetic boolean default false,
  status text default 'draft',  -- draft | armed | uploading | scheduled | published | failed
  video_id text,
  error text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists factory_posts_status_idx
  on public.factory_posts (status);
create index if not exists factory_posts_channel_created_idx
  on public.factory_posts (channel_key, created_at desc);

-- Analytics/AI insights feed
create table if not exists public.factory_insights (
  id bigint generated always as identity primary key,
  channel_key text,
  ts timestamptz default now(),
  summary text,
  details jsonb default '{}'
);

create index if not exists factory_insights_channel_ts_idx
  on public.factory_insights (channel_key, ts desc);

-- Which generators contributed to a render, in what role
create table if not exists public.factory_render_contributors (
  id bigint generated always as identity primary key,
  render_id uuid,
  generator text,
  role text  -- human phrase: "intro/outro bookends", "karaoke captions", "voice-over", ...
);

create index if not exists factory_render_contributors_render_idx
  on public.factory_render_contributors (render_id);
create index if not exists factory_render_contributors_generator_idx
  on public.factory_render_contributors (generator);

-- Generator scope + tags
alter table public.factory_generators
  add column if not exists tags jsonb default '[]',
  add column if not exists scope text default 'unknown';
  -- scope: network | multi | single:<channel_key>

-- Calendar kind: content items vs factory-improvement items
alter table public.factory_calendar
  add column if not exists kind text default 'content';  -- content | factory

-- Local path of rendered file on the production machine
alter table public.factory_renders
  add column if not exists local_path text;

-- RLS like the other factory_ tables: enabled, NO policies (service role only)
alter table public.factory_posts enable row level security;
alter table public.factory_insights enable row level security;
alter table public.factory_render_contributors enable row level security;

-- Auto-sync schedule settings
insert into public.factory_settings (key, value) values
  ('auto_sync_hour', '07:30'),
  ('auto_sync_tz', 'Asia/Kolkata')
on conflict (key) do nothing;
