-- 017_retention_traffic.sql — per-video traffic-source mix + retention-curve holds
-- House rules: additive only, all objects prefixed factory_, shared DB (touch
-- nothing else). These columns hang off the existing per-video daily-stats table.
--
-- Why: the Insights page had watch-through % but not the two signals the manual
-- retention analysis actually turned on —
--   1. how much of a video's reach comes from the SHORTS feed (the algorithm's
--      growth engine; ~90% on winners here), and
--   2. the audience-retention hold at the ~3s hook gate and the ~15s sustained-
--      distribution gate (so we rank by "clone the retention champ", not the
--      view champ).
--
-- These are WINDOW-level per-video values (whole trailing window), not per-day.
-- The analytics sync writes them onto the LATEST daily row per video; the
-- video_summary edge query picks the latest non-null via array_agg(order by date desc).
-- NULL on the data_api_fallback path (no Analytics scope) and NULL for videos
-- YouTube withholds below its retention privacy-sample threshold.

alter table public.factory_video_stats
  add column if not exists shorts_pct  numeric,  -- % of window views from the Shorts feed (0-100)
  add column if not exists traffic_mix jsonb,     -- {insightTrafficSourceType: views} for the window
  add column if not exists hold_3s     numeric,  -- audienceWatchRatio nearest 3s (hook gate); >1 = looping
  add column if not exists hold_15s    numeric;  -- audienceWatchRatio nearest 15s (sustained-distribution gate)
