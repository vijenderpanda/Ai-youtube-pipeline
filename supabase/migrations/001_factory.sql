-- Factory Control Room schema (all objects prefixed factory_; shared DB — touch nothing else)

create table if not exists public.factory_channels (
  key text primary key,
  name text,
  niche text,
  status text default 'active',
  accent text,
  yt_channel_id text,
  guidelines text default '',
  brand jsonb default '{}',
  created_at timestamptz default now()
);

create table if not exists public.factory_jobs (
  id uuid primary key default gen_random_uuid(),
  channel_key text,
  type text,
  title text,
  prompt text,
  model text default 'opus',
  effort text default 'high',
  status text default 'queued',
  logs text default '',
  result jsonb,
  error text,
  created_at timestamptz default now(),
  started_at timestamptz,
  finished_at timestamptz
);

create table if not exists public.factory_renders (
  id uuid primary key default gen_random_uuid(),
  channel_key text,
  job_id uuid,
  filename text,
  storage_path text,
  kind text,
  size_bytes bigint,
  duration_s numeric,
  published_url text,
  created_at timestamptz default now()
);

create table if not exists public.factory_generators (
  name text primary key,
  path text,
  description text,
  updated_at timestamptz default now()
);

create table if not exists public.factory_stats (
  id bigint generated always as identity primary key,
  channel_key text,
  date date,
  views bigint,
  subs bigint,
  raw jsonb,
  unique (channel_key, date)
);

create table if not exists public.factory_events (
  id bigint generated always as identity primary key,
  ts timestamptz default now(),
  kind text,
  message text,
  meta jsonb default '{}'
);

create table if not exists public.factory_settings (
  key text primary key,
  value text
);

-- RLS on every factory_ table, NO policies: service role + edge function only
alter table public.factory_channels enable row level security;
alter table public.factory_jobs enable row level security;
alter table public.factory_renders enable row level security;
alter table public.factory_generators enable row level security;
alter table public.factory_stats enable row level security;
alter table public.factory_events enable row level security;
alter table public.factory_settings enable row level security;

-- Job queue index
create index if not exists factory_jobs_status_created_at_idx
  on public.factory_jobs (status, created_at);

-- Atomic claim: flip ONE oldest queued job to running and return it
create or replace function public.factory_claim_job()
returns setof public.factory_jobs
language plpgsql
security definer
set search_path = public
as $$
declare
  j public.factory_jobs%rowtype;
begin
  select * into j
  from public.factory_jobs
  where status = 'queued'
  order by created_at
  limit 1
  for update skip locked;

  if not found then
    return;
  end if;

  update public.factory_jobs
     set status = 'running',
         started_at = now()
   where id = j.id
  returning * into j;

  return next j;
end;
$$;

-- Security definer function must not be callable by anon/authenticated
revoke all on function public.factory_claim_job() from public;
revoke all on function public.factory_claim_job() from anon;
revoke all on function public.factory_claim_job() from authenticated;
grant execute on function public.factory_claim_job() to service_role;

-- Seed: hashed dashboard token
insert into public.factory_settings (key, value)
values ('token_sha256', 'ec22e20dbed25f257bcff2697616b4183160c2da48f541913c02442c1f7f257e')
on conflict (key) do nothing;

-- Public bucket for rendered assets
insert into storage.buckets (id, name, public)
values ('factory-renders', 'factory-renders', true)
on conflict (id) do nothing;
