-- 007: job control — cooperative stop + worker liveness heartbeat.
-- control: nullable text; 'stop' = user requested termination (worker polls
--          it ~every 4s while a claude child runs and terminates the child).
-- heartbeat_at: worker updates ~every 4s while running; a running job whose
--          heartbeat is >3min old (and isn't the worker's current job) is
--          considered orphaned and reaped.
alter table public.factory_jobs
  add column if not exists control text,
  add column if not exists heartbeat_at timestamptz;
