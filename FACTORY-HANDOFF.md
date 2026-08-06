# Factory worker — session handoff (2026-08-06 ~13:47 UTC)

Written before quitting the Claude desktop app. To resume: open a new Claude chat in this
project and say **"check the worker queue"** — live truth is in Supabase `artha`
(`xfqyovimnqdghiekicqr`), table `factory_jobs`. This file is just a snapshot.

## Worker
- Daemon: launchd `com.factory.worker` (standalone; **NOT** a child of the desktop app — quitting
  the app does not affect it). Runs `claude -p` jobs via Keychain subscription token.
- Concurrency: **`FACTORY_MAX_PARALLEL=2`** in `secrets/factory.env` (1 heavy + 1 light).
  - History today: was 3 → caused an OOM cascade → dropped to 1 (serial) → raised to 2 after
    freeing Chrome. **Rule: 2 only while Chrome is closed / ≥60% free RAM. NEVER 3 on this 18GB Mac.**
  - Change takes effect on worker restart: `launchctl kickstart -k gui/$(id -u)/com.factory.worker`
    (restart orphans in-flight jobs, but they auto-retry once).
- Circuit breaker (no restart needed): `update factory_settings set value='1' where key='worker_paused'`
  stops new claims instantly; `'0'` resumes.

## Live state at snapshot
- Queue: **121 queued, 2 running, 106 done, 19 cancelled, 1 failed.**
- The large queue is the **"Amazon Just Lost"** plan_assets fan-out (many `generate_asset` children).
- Running: `produce_short` (claude-tricks "Stop Describing Your Problem…") + `generate_asset`
  (episode_script, Amazon Just Lost).
- `failed = 1` is **benign**: `aed54a7d` (lulla "Pip's Moonlit Garden — 1 HOUR of Calm") was
  interrupted by the parallel=2 restart and already **auto-retried as `dca72f18`**.
- `analytics_sync` "Analytics sync + AI suggestions" — **done 13:47** (was manually prioritized).

## Memory / OOM context
- 18 GB Mac. The crash came from 3× concurrent `claude -p` + Chrome (5.3 GB) + desktop app.
- Chrome was quit (75 procs → 0), freeing ~12.7 GB of swap; free pressure 33% → 70%.
- Watch memory when a `produce_short` (Remotion) peaks alongside a 2nd job; if tight, pause or set =1.

## HeyGen (claude-tricks avatar renders)
- Funded: **api credit pool ~1,591**, wallet ~$26.5, auto_reload ON. `host_payoff_clip` renders work.

## Desktop-app agent-session leak (separate from factory)
- ~24 idle "Cowork"/agent-mode sessions (plugin `cowork-plugin-management` + `anthropic-skills`),
  children of the desktop app, up to 3 days old, ~3.7 GB. **No cron causes them** (all scheduled
  tasks are disabled since July) — they're accumulated Cowork sessions the app didn't reap.
  Quit+reopen the app clears all of them (and this chat).
