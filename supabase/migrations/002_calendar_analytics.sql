-- Factory v2: content calendar + analytics/suggestion jobs
-- (all objects prefixed factory_; shared DB — touch nothing else)

create table if not exists public.factory_calendar (
  id uuid primary key default gen_random_uuid(),
  channel_key text not null,
  planned_date date not null,
  title text not null,
  brief text default '',
  type text default 'produce_short',
  status text default 'planned',            -- planned | suggested | queued | produced | skipped
  origin text default 'manual',             -- manual | ai_suggestion
  suggestion_reason text,                   -- why the AI suggests this
  model text default 'opus',
  effort text default 'high',
  ultracode boolean default false,
  job_id uuid,
  created_at timestamptz default now()
);

create index if not exists factory_calendar_channel_date_idx
  on public.factory_calendar (channel_key, planned_date);

create index if not exists factory_calendar_status_idx
  on public.factory_calendar (status);

-- RLS like the other factory_ tables: enabled, NO policies (service role only)
alter table public.factory_calendar enable row level security;

-- Per-job ultracode flag (worker prepends 'ultracode' keyword to the claude prompt)
alter table public.factory_jobs add column if not exists ultracode boolean default false;
