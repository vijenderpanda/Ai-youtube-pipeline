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

## Create scripts/title_demand.py — objective title DEMAND vs INVENTED classifier
_source: analyze_and_suggest c8b69efa-0ee7-4c48-87e6-e0d69f4490c0 · 2026-08-11_

**Why:** The vehicles channel's own last-two-cycle insight passes have explicitly named this exact tool as a pending prerequisite for validating whether queued titles chase real search demand or are invented format bets, and no generator in the catalog currently does this.

**Interface / acceptance:**

CREATE scripts/title_demand.py, a network-scope CLI that closes the loop the vehicles insight pass has been flagging for 2 cycles running ('once scripts/title_demand.py lands, verify every vehicles title scores DEMAND not INVENTED') and that generalizes to every kids/education channel on the network. Interface: `python scripts/title_demand.py --channel KEY [--title 'TEXT' | --calendar-id ID | --all-queued] [--json out.json]`. Behavior: (1) pull the candidate title (from --title, or the calendar row's title/brief via Supabase factory_calendar for --calendar-id, or every 'queued'/'suggested' row for --all-queued); (2) extract the core searchable phrase (strip channel branding/emoji per the existing title-cleaning helper in yt_upload.py if present); (3) query YouTube Data API search.list for that phrase + the channel's niche keywords, and/or a lightweight WebSearch call, to check whether videos with a materially similar title/format already exist and are getting traction — this is the DEMAND signal; (4) score INVENTED when no comparable existing content is found for the phrase (i.e. the format is a bet with no external validation) vs DEMAND when comparable content already draws views; (5) emit `{title, channel_key, verdict: 'demand'|'invented'|'unclear', evidence: [...], comparable_titles: [...]}` per row, plus a summary count. Consumers: the per-channel insight-pass prompt (this job) should call it before proposing a new format episode, and `daily_check.py` can optionally flag queued rows still scored 'invented' with no owner sign-off. Acceptance: run --all-queued on vehicles and confirm colors/counting score 'demand' (established kids-vehicle format) while a genuinely novel format bet scores 'invented' or 'unclear'.

- [ ] open

## Land scripts/beat_audit.py -- pre-render gate for the 4-7s retention danger window
_source: analyze_and_suggest a42da3bb-4d5f-4144-89aa-abc8f955516a · 2026-08-12_

**Why:** yt_retention.py --summary shows the identical 5-13s structural cliff on every sample-cleared claude-tricks video for 5 straight analysis cycles, and the one fix that would enforce the proven-good structure (proof-by-4s, no boundary in 4.0-7.0s) at build time has sat open in docs/FACTORY-BACKLOG.md since 2026-08-08 with zero action.

**Interface / acceptance:**

CREATE scripts/beat_audit.py per docs/FACTORY-BACKLOG.md (open since 2026-08-08, unactioned for 5 analyze_and_suggest cycles). Interface: `python scripts/beat_audit.py --spec SPEC.json [--danger-window 4.0 7.0] [--proof-by 4.0] [--max-duration 30]`. RULE A (proof-by): assert the first segment whose kind is real proof (demo, newsSplit-with-footage, statBars) begins at or before --proof-by. RULE B (danger-window): assert NO segment boundary -- cover-dissolve end, intro-overlay hold end, host-to-footage cut, step-chip in/out pulled from the matching .timeline.json -- falls inside --danger-window. Exit non-zero on either rule failure. Wire it into build_ep_v2.py as a blocking check BEFORE any HeyGen/Leonardo generation call fires (so a failing spec never spends render budget). Acceptance: run against the spec for 'Claude Code Forgets EVERYTHING!' (must PASS -- proof by ~4s, no 4-7s boundary) and against 'The Best AI Just Got Cheaper' / 'Claude Just Got SKILLS' / 'SAME Prompt Every Day' / 'I Built an AI Factory' (must each FAIL, reproducing their measured 5-13s cliffs). Once landed, every future claude-tricks brief in this suggestions run and beyond should require a passing --assert-pacing gate before render, closing a fix that is currently re-diagnosed by hand every single cycle.

- [ ] open

