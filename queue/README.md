# queue/ — repo-side job intake for the factory

Drop a JSON file in `queue/pending/` and push: the `factory-queue` GitHub Action
inserts it into `factory_jobs` (Supabase) and moves the file to `queue/done/`.
A live worker claims inserted jobs within ~10s. This exists because Claude Code
cloud sessions cannot reach Supabase directly — GitHub runners can.

File shape — one job object or a list of them; allowed fields only:

```json
{
  "type": "custom",                 // required: produce_short | custom | shell_script | ...
  "prompt": "what to do",           // required
  "channel_key": "claude-tricks",
  "title": "dashboard label",
  "model": "sonnet",                // fable | opus | sonnet | haiku
  "effort": "low",                  // low | medium | high | xhigh | max
  "meta": {"script_path": "deploy/restart_worker.sh"}
}
```

Needs the `SUPABASE_SERVICE_KEY` repo secret (one-time, GitHub Settings →
Secrets and variables → Actions). Bad files stay in `pending/` and fail the run
loudly; nothing is silently dropped. On-Mac alternative: `scripts/enqueue_job.py`.
