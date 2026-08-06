-- Factory v6: challenger suggestions — AI calendar items that propose
-- replacing/improving an EXISTING item (replaces_id), with a reason the
-- original might underperform (why_not). Accepting one supersedes the
-- original via the supersede_calendar_item API route.
-- (all objects prefixed factory_; shared DB — touch nothing else)

alter table public.factory_calendar
  add column if not exists replaces_id uuid,  -- item this suggestion proposes to replace
  add column if not exists why_not text;      -- why the original might underperform

-- factory_calendar.status values are now:
--   planned | suggested | queued | produced | skipped | superseded
-- ('superseded' = original item replaced by an accepted improvement;
--  set only by the supersede_calendar_item route)

create index if not exists factory_calendar_replaces_idx
  on public.factory_calendar (replaces_id);

-- Worker-maintained ISO timestamp of the last analytics sync
-- (surfaced by ?r=overview as last_sync_at; null until first sync)
insert into public.factory_settings (key, value)
values ('last_sync_at', null)
on conflict (key) do nothing;
