-- 013: multi-worker support.
--   * factory_workers registry (one row per machine): identity, capabilities,
--     live routing config (paused + accept_types), heartbeat (last_seen).
--   * factory_jobs.assigned_worker (who ran it) + target_worker (optional pin:
--     only this worker may claim it; an explicit per-job override).
--   * factory_claim_job_v3: routing-aware atomic claim. Also (re)captures the
--     live-only factory_claim_job_v2 as a migration for reproducible setups.

-- ---- worker registry --------------------------------------------------------
create table if not exists public.factory_workers (
  worker_id     text primary key,            -- stable id (hostname or FACTORY_WORKER_ID)
  name          text,                         -- friendly display name
  hostname      text,
  os            text,                         -- 'Darwin' | 'Windows' | 'Linux'
  gpu           text,                         -- e.g. 'NVIDIA GeForce RTX 3060' or null
  max_parallel  int,
  accept_types  text[],                       -- null/empty = accept ALL job types
  paused        boolean not null default false,
  last_seen     timestamptz,
  registered_at timestamptz not null default now(),
  meta          jsonb not null default '{}'::jsonb
);

-- registry is reached only through the edge function (service_role); lock it down
alter table public.factory_workers enable row level security;
revoke all on table public.factory_workers from anon, authenticated;

-- ---- per-job assignment / pinning ------------------------------------------
alter table public.factory_jobs
  add column if not exists assigned_worker text,   -- set by the claim RPC
  add column if not exists target_worker   text;   -- optional pin (null = any worker)

-- ---- v2 (captured from live for fresh-project reproducibility) --------------
create or replace function public.factory_claim_job_v2(exclude_types text[] default '{}'::text[])
returns setof public.factory_jobs
language plpgsql security definer set search_path = public
as $$
declare j public.factory_jobs%rowtype;
begin
  if exists (select 1 from public.factory_settings where key='worker_paused' and value='1') then
    return;
  end if;
  select * into j from public.factory_jobs
   where status='queued' and not (type = any(exclude_types))
   order by created_at limit 1 for update skip locked;
  if not found then return; end if;
  update public.factory_jobs set status='running', started_at=now()
   where id=j.id returning * into j;
  return next j;
end;
$$;

-- ---- v3: routing-aware claim ------------------------------------------------
-- Claim the oldest queued job that THIS worker is allowed to run:
--   * global pause (factory_settings.worker_paused='1') and per-worker pause
--     both short-circuit to "nothing".
--   * exclude_types = this worker's heavy-serial guard (computed locally).
--   * a job pinned to this worker (target_worker = p_worker_id) is ALWAYS
--     eligible (the pin overrides the worker's type filter).
--   * otherwise the job must be unpinned AND pass the worker's accept_types
--     allow-list (null/empty = all types).
-- On claim, stamps assigned_worker = p_worker_id.
create or replace function public.factory_claim_job_v3(
  p_worker_id  text,
  exclude_types text[] default '{}'::text[],
  accept_types  text[] default null
)
returns setof public.factory_jobs
language plpgsql security definer set search_path = public
as $$
declare j public.factory_jobs%rowtype;
begin
  if exists (select 1 from public.factory_settings where key='worker_paused' and value='1') then
    return;
  end if;
  if exists (select 1 from public.factory_workers where worker_id=p_worker_id and paused) then
    return;
  end if;

  select * into j from public.factory_jobs
   where status='queued'
     and not (type = any(exclude_types))
     and (
           target_worker = p_worker_id                      -- explicit pin to me
           or (
             target_worker is null
             and (accept_types is null
                  or cardinality(accept_types)=0
                  or type = any(accept_types))
           )
         )
   order by created_at limit 1 for update skip locked;

  if not found then return; end if;

  update public.factory_jobs
     set status='running', started_at=now(), assigned_worker=p_worker_id
   where id=j.id returning * into j;
  return next j;
end;
$$;

revoke all on function public.factory_claim_job_v2(text[]) from public, anon, authenticated;
grant execute on function public.factory_claim_job_v2(text[]) to service_role;
revoke all on function public.factory_claim_job_v3(text, text[], text[]) from public, anon, authenticated;
grant execute on function public.factory_claim_job_v3(text, text[], text[]) to service_role;
