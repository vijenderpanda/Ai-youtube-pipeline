-- Factory v8: auto publish-slot defaults + published-content backfill support.
-- (all objects prefixed factory_; shared DB — touch nothing else)
--
-- 1) Draft posts are prefilled with a publish_at slot: the linked calendar
--    item's planned_date at default_publish_time (local auto_sync_tz),
--    clamped to the future. Logic lives in scripts/factory_worker.py
--    (default_publish_at); this just seeds the tunable slot time.
--
-- 2) Shipped-before-the-factory content is backfilled by
--    scripts/backfill_calendar_published.py as factory_calendar rows with
--    origin 'backfill' + factory_posts rows with status 'published', linked
--    by a shared synthetic job_id (no factory_jobs row). No schema change
--    needed — origin is already free-text.

insert into public.factory_settings (key, value) values
  ('default_publish_time', '16:00')
on conflict (key) do nothing;
