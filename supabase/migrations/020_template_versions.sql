-- 020_template_versions.sql — mix-&-match template composition.
-- House rules: additive only, factory_ prefix, shared DB, RLS on with NO policies,
-- and — the 018 lesson (018_asset_versions.sql:44-48) — an EXPLICIT service_role grant.
--
-- factory_templates names the PIPELINE (which produce/plan/finalize code runs).
-- A template VERSION names the CAST (which revision of each slot that pipeline
-- runs with). Composition is edited as join rows while `draft`, then FROZEN into
-- the `composition` jsonb at lock:
--   * the join table is the editable composition the composer writes one slot at
--     a time, and the reverse index a "who still uses this revision?" query needs;
--   * the jsonb is the frozen snapshot carrying COPIED build_refs, so a locked
--     version renders identically forever and the build resolves the whole cast
--     in ONE select (matching build_ep_v2.py's single batched lock read).
create table if not exists public.factory_template_versions (
  id                uuid primary key default gen_random_uuid(),
  template_key      text not null,   -- -> factory_templates.key; no FK, per house pattern
  channel_key       text not null,   -- denormalized: every same-channel guard is one comparison
  version           int  not null default 1,
  label             text default '', -- "olive host + quiet bed"
  notes             text default '',
  status            text not null default 'draft',   -- draft | locked | retired
  composition       jsonb not null default '{}'::jsonb,
  -- frozen at lock, keyed by asset_type (SAME vocabulary as factory_asset_versions.asset_type
  -- and build_ep_v2._LOCK_CFG_KEY):
  --   {"outro_sting": {"version_id":"…","version":3,"build_ref":"outro/x.mp4",
  --                    "label":"…","storage_path":"…","alts":[…]}}
  -- build_ref is COPIED, not joined — that is what makes the lock reproducible.
  parent_version_id uuid,
  created_at        timestamptz default now(),
  locked_at         timestamptz,
  retired_at        timestamptz,
  meta              jsonb not null default '{}'::jsonb,
  unique (template_key, version)
);
create index if not exists factory_template_versions_template_idx on public.factory_template_versions (template_key, version desc);
create index if not exists factory_template_versions_channel_idx  on public.factory_template_versions (channel_key);
create index if not exists factory_template_versions_status_idx   on public.factory_template_versions (status);
create index if not exists factory_template_versions_parent_idx   on public.factory_template_versions (parent_version_id);

-- Editable composition of a DRAFT: one row per (version, asset_type, slot position).
-- position 0 = the primary pick the build resolves; >=1 = alts (the HeyGen 1-2 face pool,
-- the b-roll bank).
create table if not exists public.factory_template_assets (
  id                  uuid primary key default gen_random_uuid(),
  template_version_id uuid not null,
  asset_type          text not null,
  asset_version_id    uuid not null,
  position            int  not null default 0,
  note                text default '',
  created_at          timestamptz default now(),
  unique (template_version_id, asset_type, position)
);
create index if not exists factory_template_assets_version_idx on public.factory_template_assets (template_version_id);
-- the reverse lookup delete_asset_version needs: "who still references this revision?"
create index if not exists factory_template_assets_asset_idx   on public.factory_template_assets (asset_version_id);

-- Which composed version this template produces with today. NULL = today's behavior exactly
-- (build falls through to factory_asset_locks).
alter table public.factory_templates add column if not exists active_version_id uuid;
-- The cast an episode was produced with — stamped at queue time so a later lock change
-- never rewrites history and a re-cut reproduces the render.
alter table public.factory_calendar  add column if not exists template_version_id uuid;

alter table public.factory_template_versions enable row level security;
alter table public.factory_template_assets   enable row level security;
revoke all on table public.factory_template_versions from anon, authenticated;
revoke all on table public.factory_template_assets   from anon, authenticated;
grant all on table public.factory_template_versions to service_role;
grant all on table public.factory_template_assets   to service_role;
