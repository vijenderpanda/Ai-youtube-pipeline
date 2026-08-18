-- 019_asset_library.sql — columns the Asset Library needs before full ingest.
-- Additive only; all objects prefixed factory_; shared DB (touch nothing else).
-- Backs the Asset Manager build spec Phase 1 (scripts/ingest_asset_library.py).
--
-- House gotcha (the 018 lesson at 018_asset_versions.sql:44-48): new tables/columns
-- in this project do NOT auto-grant. The factory-api edge fn and the worker both run
-- as service_role, so re-assert the grant explicitly at the bottom.

alter table public.factory_asset_versions add column if not exists retired_at  timestamptz;
alter table public.factory_asset_versions add column if not exists generator   text;  -- script/component that makes it
alter table public.factory_asset_versions add column if not exists job_id      uuid;  -- factory_jobs row that produced it
alter table public.factory_asset_versions add column if not exists storage_state text default 'bucket';
  -- WHERE THE BYTES ARE on disk, as written by scripts/ingest_asset_library.py:
  --   local -> repo only | t5 -> Samsung_T5 backup only | both -> same sha1 on each
  -- ('bucket' is only the legacy default carried by the 9 hand-registered backfill rows.)
  -- 883 of 1220 claude-tricks asset files live ONLY on the T5 SSD; the board must never
  -- assume a repo path resolves.

create index if not exists factory_asset_versions_retired_idx
  on public.factory_asset_versions (retired_at);

grant all on table public.factory_asset_versions to service_role;  -- re-assert, harmless
grant all on table public.factory_asset_locks    to service_role;  -- re-assert, harmless
