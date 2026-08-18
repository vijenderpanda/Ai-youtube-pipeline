-- 022_suggestion_provenance.sql — evidence trail for auto-suggested calendar items,
-- so the Studio launcher can show WHY a suggestion exists (which file, which line,
-- which URL) instead of a bare one-liner. Additive only; factory_ prefix; shared DB.
-- House gotcha (018/019): new objects here do NOT auto-grant to service_role.
alter table public.factory_calendar
  add column if not exists evidence jsonb;
  -- {tier, source, generated_by, generated_at, source_sha,
  --  cites:[{label, path, line?, quote?, url?, date?}], peg, constraints, blockers}
  -- NEVER empty for an origin='ai_suggestion' row — scripts/suggest_next.py
  -- asserts this before insert, and the edge read filters rows without cites.

alter table public.factory_calendar
  add column if not exists suggestion_source text;
  -- pivot-decision | needs-attention | calendar-csv | brand-bible | news-radar
  -- | plan_content | analyze_and_suggest | chore

alter table public.factory_calendar
  add column if not exists suggestion_confidence text default 'scored';
  -- scored | inferred_rank | date_inferred | generated

-- factory_calendar has no uniqueness constraint, so a producer could double-insert —
-- and had: the same claude-tricks suggestion landed 2026-08-12 AND 2026-08-13 (the
-- older copy was retired to 'skipped' when this index was introduced).
create unique index if not exists factory_calendar_autosuggest_uniq
  on public.factory_calendar (channel_key, planned_date, lower(title))
  where origin = 'ai_suggestion' and status = 'suggested';

create index if not exists factory_calendar_suggested_channel_idx
  on public.factory_calendar (channel_key, status)
  where status = 'suggested';

grant all on table public.factory_calendar to service_role;
