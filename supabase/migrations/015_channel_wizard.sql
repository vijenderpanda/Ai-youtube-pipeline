-- Channel-creation wizard (Phase B): conversational drafts + channel lifecycle.

create table if not exists public.factory_channel_drafts (
  id uuid primary key default gen_random_uuid(),
  seed text,
  status text not null default 'intake',        -- intake | ready | created | abandoned
  step int not null default 0,
  answers jsonb not null default '{}'::jsonb,    -- captured brand.* map
  transcript jsonb not null default '[]'::jsonb, -- AI/user back-and-forth history
  created_channel_key text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.factory_channel_drafts enable row level security;

-- lifecycle: 'incubating' during the Ep01 TEMP loop, 'active' once locked.
-- Existing channels default to 'active' so nothing regresses.
alter table public.factory_channels add column if not exists lifecycle text not null default 'active';
alter table public.factory_channels add column if not exists baseline_ref text;
