-- 011_draft_preview.sql — exception-based review + draft preview
-- frames: per-video start/mid/end still storage paths (jsonb array) so the board
-- can show real frames without playing every clip. preview_path/preview_at: the
-- episode-level low-res DRAFT stitch (preview_episode job) — watch what would go
-- out on YouTube BEFORE committing to full assembly.

alter table factory_assets add column if not exists frames jsonb not null default '[]';
alter table factory_calendar add column if not exists preview_path text;
alter table factory_calendar add column if not exists preview_at timestamptz;
