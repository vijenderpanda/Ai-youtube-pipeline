# Factory Backlog

Code / factory-internal suggestions written by `analyze_and_suggest` runs. Reviewed from a Claude Code session (not the calendar). Content-facing suggestions still land in `factory_calendar` and drive the calendar UI. See `scripts/factory_worker.py::ingest_suggestions`.

Sections are dedup'd by title. Flip `- [ ] open` to `- [x] done` once actioned; move actioned items into an `# Actioned` section at the bottom if you want history.

**One-time cleanup owed:** delete existing `kind='factory'` rows from `factory_calendar` so the calendar UI clears immediately (their reasoning JSON already sits in `renders_out/suggestions_*.json` for history; this file is the ongoing sink). SQL:

```sql
delete from public.factory_calendar
where kind = 'factory' and status = 'suggested';
```

Manually copy any still-relevant items into sections below before running that.

---

## Update scripts/yt_retention.py — add --attribute, joining measured drop_points to the episode's named beats
_source: analyze_and_suggest 6ebc3319 · 2026-08-07_

**Why:** yt_retention.py reports timestamps with no idea what is on screen at them. Every retention-driven fix this cycle had to be reconstructed by hand from briefs → episode beats. Attributing drop_points to the named beat unlocks retention-driven revisions as a routine step, not a special investigation.

**Interface / acceptance:**

`python scripts/yt_retention.py --channel KEY --attribute [--video ID] [--spec path/to/spec.json] [--timeline path/to/*.timeline.json] [--json attributed.json] [--md]`

Output: per-video table of (elapsed %, drop pp, beat name, on-screen artefact reference). Acceptance: running on claude-tricks independently reproduces this cycle's hand analysis.

- [ ] open

## Create scripts/beat_audit.py — pre-render early-structure gate (proof-by-4s, no boundary in the 4-7s danger window)
_source: analyze_and_suggest 6ebc3319 · 2026-08-08_

**Why:** The 5-6s retention cliff is entirely a build-time property of the spec. So the fix belongs in a pre-render gate, not a post-mortem five days after publish. `analyze_and_suggest` cited this as the highest-leverage factory improvement of the cycle.

**Interface / acceptance:**

`python scripts/beat_audit.py --spec SPEC.json [--danger-window 4.0 7.0] [--proof-by 4.0] [--max-duration 30]`

RULE A (proof-by): assert that a segment whose kind is real proof (`demo`, `newsSplit` with footage, `statBars`) begins at or before `--proof-by`.

RULE B (danger window): assert that NO segment boundary — cover-dissolve end, intro-overlay hold end, host→footage cut, step-chip in/out from `.timeline.json` — falls inside `--danger-window`.

Exit non-zero on either rule failure. Wire into `build_ep_v2.py` before HeyGen/Leonardo generations fire.

- [ ] open
