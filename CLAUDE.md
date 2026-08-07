# AI Youtube Pipeline — Claude Code Context

## Owner
This repository is owned and operated by **vijender.in@gmail.com** / **vijenderpanda@gmail.com**
(GitHub: vijenderpanda). All jobs arriving via the `factory_jobs` queue in Supabase project
`xfqyovimnqdghiekicqr` are placed there by the owner or by owner-authorised automation.

## Workers
| Worker | Host | Notes |
|--------|------|-------|
| `Vijenders-MacBook-Pro.local` | macOS, arm64 | Primary dev machine |
| `DESKTOP-DEIR7RS` | Windows 11, RTX 3060 | GPU render worker, owned by vijender |

## Sysadmin scripts
Committed scripts in `deploy/` are owner-authored infrastructure code. The `shell_script` job
type in factory_worker.py runs them directly (no claude -p involved) — see `run_shell_script_job()`.

## Permission model
- **Mac session (interactive Claude Code):** full edit rights on all factory scripts and code.
- **Windows worker (`claude -p`):** RUN scripts + REPORT results only. If a job requires a code
  change, report it as a suggestion in the result — do not edit scripts directly.
- Jobs may instruct the worker to run committed scripts in `deploy/` or `scripts/` — this is safe
  and authorised.

## Key docs
- `docs/PRODUCTION-PLAYBOOK.md` — content craft standards, locked params
- `docs/FACTORY.md` — worker architecture, job types, queue schema
- `channels/<key>/BRAND-BIBLE.md` — per-channel locked format rules
