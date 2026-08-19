-- 023_composition_blocks.sql — LOCKED composition SEQUENCE (block order) per template version.
-- House rules: additive only, factory_ prefix, shared DB, RLS on with NO policies, NO foreign
-- keys, and — the 018 lesson (018_asset_versions.sql:44-48, reaffirmed in 020_template_versions.sql:2-3)
-- — an EXPLICIT service_role grant (without it the edge fn 500s).
--
-- 020 gave a version its CAST (which revision fills each asset_type slot). This gives a version
-- its SEQUENCE (which blocks play, in what order, with what layout + config). Edited as draft
-- rows here, then FROZEN into factory_template_versions.composition._sequence at lock:
--   * the join table is the editable sequence the composer writes one block at a time;
--   * the jsonb snapshot rides ALONGSIDE composition._settings so a locked version resolves the
--     whole cast+sequence in ONE select (the migration-020 single-batched-lock-read invariant
--     build_ep_v2.py depends on).
-- config is OPEN jsonb (cookbook props / host lines / slot layout+host+broll), so new cookbook
-- comps and layouts need no schema change.
create table if not exists public.factory_template_blocks (
  id                  uuid primary key default gen_random_uuid(),
  template_version_id uuid not null,   -- -> factory_template_versions.id; no FK, per house pattern
  position            int  not null,   -- play order; 0-based, dense within a version
  block_type          text not null,   -- hook | host | broll | statbars | outro | slot | cards
  layout              text,            -- a layout id (full-broll|host-top|host-bottom|split|host-pip|framed) or NULL for non-spatial blocks
  config              jsonb not null default '{}'::jsonb,  -- OPEN: {"cookbook":{...},"dur":5} | {"host":{...},"dur":5} | {"layout":"host-top","host":{...},"broll":{...},"dur":5}
  created_at          timestamptz default now(),
  unique (template_version_id, position)
);
create index if not exists factory_template_blocks_version_idx on public.factory_template_blocks (template_version_id);
-- ordered read (a version's blocks in play order) is served by the implicit btree that
-- UNIQUE(template_version_id, position) creates — no separate (version, position) index needed.

alter table public.factory_template_blocks enable row level security;
revoke all on table public.factory_template_blocks from anon, authenticated;
grant all on table public.factory_template_blocks to service_role;
