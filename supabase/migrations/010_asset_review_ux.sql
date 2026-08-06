-- 010_asset_review_ux.sql — Studio review UX: step ordering + reviewer cheat-sheets
-- position: production-step order from the asset plan (0-based; versions of one
-- asset_key share the step). review_note: short "what to check" note written by
-- the generate job so huge docs (scripts, research) can be reviewed at a glance.

alter table factory_assets add column if not exists position int not null default 0;
alter table factory_assets add column if not exists review_note text default '';

-- backfill: rank each calendar item's asset_keys by first appearance
with keys as (
  select calendar_id, asset_key, min(created_at) as first_at
  from factory_assets
  group by calendar_id, asset_key
), ranked as (
  select calendar_id, asset_key,
         row_number() over (partition by calendar_id order by first_at asc) - 1 as rn
  from keys
)
update factory_assets a
set position = r.rn
from ranked r
where a.calendar_id = r.calendar_id and a.asset_key = r.asset_key;
