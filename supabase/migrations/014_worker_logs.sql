-- Worker log lines pushed by each machine during heartbeat.
-- Kept small: auto-prune to last ~200 per worker on insert via trigger.

create table if not exists factory_worker_logs (
  id         bigint generated always as identity primary key,
  worker_id  text not null references factory_workers(worker_id) on delete cascade,
  ts         timestamptz not null default now(),
  level      text not null default 'info',   -- info | warn | error
  message    text not null,
  meta       jsonb
);

create index if not exists idx_worker_logs_worker_ts
  on factory_worker_logs(worker_id, ts desc);

-- Auto-prune: keep only the newest 200 rows per worker after each batch insert.
create or replace function prune_worker_logs() returns trigger as $$
begin
  delete from factory_worker_logs
  where worker_id = NEW.worker_id
    and id not in (
      select id from factory_worker_logs
      where worker_id = NEW.worker_id
      order by ts desc
      limit 200
    );
  return null;
end;
$$ language plpgsql;

drop trigger if exists trg_prune_worker_logs on factory_worker_logs;
create trigger trg_prune_worker_logs
  after insert on factory_worker_logs
  for each row execute function prune_worker_logs();
