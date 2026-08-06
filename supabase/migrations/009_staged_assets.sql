-- 009_staged_assets.sql — staged fragment production ("Studio")
-- House rules: all objects prefixed factory_, shared DB (touch nothing else),
-- RLS enabled with NO policies (service-role / edge-function access only).
-- See docs/STAGED-PIPELINE.md for the full contract.

-- Per-asset fragment rows: one row per (calendar item, asset_key, version).
create table if not exists factory_assets (
  id uuid primary key default gen_random_uuid(),
  calendar_id uuid not null,
  channel_key text not null,
  asset_key text not null,
  version int not null default 1,
  group_key text not null default 'other',   -- thumbnail|scene|clip|audio|bookend|overlay|other
  kind text not null default 'image',        -- image|video|audio|text|other
  title text default '',
  spec jsonb not null default '{}',          -- {prompt, params, revision_notes:[...]}
  status text not null default 'queued',     -- queued|generating|review|approved|skipped|superseded|failed
  job_id uuid,                               -- generate_asset job for THIS version
  filename text,
  storage_path text,
  poster_path text,
  local_path text,
  size_bytes bigint,
  duration_s numeric,
  notes text default '',                     -- reviewer feedback that requested this version
  model text,
  effort text,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique (calendar_id, asset_key, version)
);

create index if not exists factory_assets_calendar_idx on factory_assets (calendar_id);
create index if not exists factory_assets_status_idx on factory_assets (status);
create index if not exists factory_assets_job_idx on factory_assets (job_id);

alter table factory_assets enable row level security;

-- Staged jobs carry {calendar_id, asset_id?, asset_key?, version?}.
-- factory_claim_job() returns the full row, so meta flows to the worker unchanged.
alter table factory_jobs add column if not exists meta jsonb not null default '{}';

-- Calendar items opt into staged production.
alter table factory_calendar add column if not exists production_mode text not null default 'direct';
