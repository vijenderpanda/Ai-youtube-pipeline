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

## Build scripts/hook_retention_audit.py — auto-map retention cliffs to episode beats
_source: analyze_and_suggest b5d40f94-15fa-47fa-9d58-56c25ca97249 · 2026-08-14_

**Why:** This job had to manually eyeball yt_retention.py's raw second-offsets against each episode's beat structure to conclude that claude-tricks' best performer ('Claude Code Forgets EVERYTHING!') has no single early cliff while five other videos share a -5 to -14pp cliff at 5.1-9.9s — that correlation is exactly the kind of finding the factory should be computing automatically every time retention data lands (48h after each upload), the same way probe_frames.py automated overlay-placement QC instead of leaving it to a human every episode.

**Interface / acceptance:**

New generator script. Input: a channel key + episode id. It runs scripts/yt_retention.py's per-video drop_points (or reads the cached retention.json it already writes) and cross-references each drop timestamp against that episode's build spec (build_ep_v2.py --ep NN --dry JSON, or the equivalent for other channels' assemblers) to name WHICH beat/segment each cliff falls inside (hook / setup / demo / payoff / chip-covered-window / stat-chart beat, etc.), not just a raw second-count. Output: a per-episode report `{video_id, drop_pct, drop_time, beat_name, beat_kind}` plus a rollup across a channel's last N episodes showing which beat KIND (hook wording, demo-cut length, chip placement) correlates with the largest average drop. This turns the current manual reading of yt_retention.py's numbers (done by hand in this job) into a repeatable diagnostic the same way scripts/probe_frames.py turned manual corner-picking into a measurement.

- [ ] open

## Create scripts/yt_retention.py --cohort — channel-wide drop-point clustering (already suggested id 84230efd, not yet built)
_source: analyze_and_suggest 7a8ccca7-dd66-4754-b675-d4dc9a40bbdc · 2026-08-14_

**Why:** This exact analysis run manually cross-referenced 6 separate yt_retention.py outputs to find the shared 5-9s cliff — a repeatable, mechanical step that should be a flag on the tool, not a manual read-and-notice each cycle.

**Interface / acceptance:**

Extend the already-shipped yt_retention.py with the --cohort flag already on the calendar as a suggestion: given a channel + days window, pull steepest-drop timestamps across every video with usable retention data, bucket them (e.g. 1s bins), and print/emit JSON of which time-buckets recur across multiple videos with what average drop magnitude. This run had to do that clustering by hand (reading 6 per-video outputs and noticing 5 of them share a 5-9s cliff) — --cohort should turn that into one command so every future analysis pass gets the cross-episode pattern automatically instead of relying on a human noticing the coincidence.

- [ ] open

## Build scripts/make_engage_cue.py — point-and-find interaction overlay for Pipeline A kids channels
_source: analyze_and_suggest 6f118f3a-8d58-4e95-ad33-afc3bd60bb10 · 2026-08-12_

**Why:** Confirmed gap by scanning the full 104-entry generator_catalog for 'cue'/'interaction'/'point'/'highlight' — none exists, and two content suggestions this cycle (lulla point-and-sing, vehicles call-and-response) both need this primitive to ship without hand-built one-off overlay code.

**Interface / acceptance:**

Create scripts/make_engage_cue.py: a reusable Remotion or PIL/ffmpeg overlay generator that draws a gentle pulsing highlight/circle cue around a named on-screen object, timed to a lyric or VO line naming it, with a --hold-min 1.5 floor (mirrors the §4 chip-hold rule) and channel-accent-colored ring (periwinkle for lulla, teal for language-abc, channel accent for vehicles). Output a `.cues.json` sidecar (time, region, label) so lulla_captions.py / lyric_karaoke.py can cross-reference timing without recomputing it. This closes a real gap: the generator catalog has caption/lyric/motion/mock tools for every Pipeline A channel but nothing that authors an interactive point-along or call-and-response visual cue, even though vehicles' 'Beep Beep, Say It With Rev' and the new lulla point-and-sing suggestion both need one.

- [ ] open

## Build scripts/make_process_reveal.py — 5th member of the in-house mock family (behind-the-AI process reveal)
_source: analyze_and_suggest 6f118f3a-8d58-4e95-ad33-afc3bd60bb10 · 2026-08-12_

**Why:** The new aashiqana 'Behind the Duet' suggestion above and any future claude-tricks 'how the factory works' follow-up both need a compliant process-reveal visual, and the mock family (§13) currently stops at four members with no process/BTS state — a real, named gap, not speculative tooling.

**Interface / acceptance:**

Create scripts/make_process_reveal.py following the exact house grammar already locked for make_chat_mock.py / make_doc_mock.py / make_report_mock.py / make_label_mock.py (§13): neutral dark canvas, channel-accent color only, no vendor name/logo/lookalike UI, generic labels ('AI SONG STUDIO', 'AI SCRIPT DESK'), safe-band-centered body per the doc-mock centering rule, ILLUSTRATIVE-or-attribution footer per the Ep28 split. States needed: `prompt` (a lyric/script line being typed), `audition` (a 2x2 grid of generated candidates), `chosen` (the picked take highlighted). This is the render path for any 'behind the scenes / how we made this' beat on claude-tricks or aashiqana without ever screenshotting a real Suno/Leonardo/ElevenLabs UI (compliance risk + brand-lookalike risk the mock family exists specifically to avoid).

- [ ] open

## Build scripts/make_engage_cue.py -- call-and-response cue-card generator for kids channels
_source: analyze_and_suggest 660a1a09-5c06-43c6-a3d1-a2e0655e5afb · 2026-08-13_

**Why:** Two independent channel insights this cycle name the same missing generator for already-queued call-and-response episodes, and the researched 2026 kids-Shorts trend favors interactive call-and-response formats -- building it once, network-wide, avoids two channels improvising incompatible one-off cue-card code.

**Interface / acceptance:**

CREATE scripts/make_engage_cue.py. This cycle's insights (last_insights for language-abc and vehicles) both flag the same gap: queued call-and-response episodes (language-abc 8/26 'Say It With Me! Colors', vehicles 8/17 'Beep Beep, Say It With Rev!') have no shared generator for the on-screen prompt-and-pause cue card that makes the format actually interactive on screen (a 'SAY IT WITH ME' / word-and-pause beat, timed to the VO's own break windows). Scope: network-wide (scope='multi' in the generator_catalog, callable by both language-abc's Pipeline A word-overlay pipeline and vehicles' Suno-based assembler). Interface: `make_engage_cue.py --channel <key> --words w1,w2,... --vo path --out cue_spec.json`, parses the eleven_vo.py/word-timestamp sidecar for pause windows >=0.6s, emits a Remotion-consumable spec (text, enable window, channel-accent color) per §4's caption-band rules (never over taught content, per the existing StepChip/probe_frames.py corner discipline). Ship a QC harness (still render at t=cue_start) same pattern as CoverDemo/StatBarsDemo.

- [ ] open

## Build scripts/calendar_dedupe_check.py -- planning-time near-duplicate title/premise checker
_source: analyze_and_suggest 660a1a09-5c06-43c6-a3d1-a2e0655e5afb · 2026-08-13_

**Why:** This cycle's 'Shapes on Wheels' collision was found only by manually reading the full calendar dump; moving the existing publish-time duplicate check earlier, to planning time, would have caught it automatically and will scale better as more channels queue further ahead.

**Interface / acceptance:**

CREATE scripts/calendar_dedupe_check.py. The existing duplicate-title guard (verify_uploads.py / publish preflight, normalized similarity >=0.90) only fires at upload time, AFTER a video is fully produced -- this cycle's challenge pass caught a live example (vehicles' 43963ae0 'Shapes on Wheels! Circles, Squares & Triangles' 8/21 vs f7ec338c 'Shapes on Wheels! Rev Finds a Triangle Truck' 8/26, near-identical title+premise 5 days apart) purely by manual read of the calendar dump, which doesn't scale as the runway grows. Scope: network, read-only against factory_calendar/factory_posts. Interface: `calendar_dedupe_check.py --channel <key>|--all --window-days 14` -- runs the same normalized-similarity function verify_uploads.py already has (import, don't reimplement) pairwise over all planned/suggested/queued rows in the window, plus a cheap premise-overlap heuristic (shared capitalized noun phrases in the title) to catch same-concept-different-wording collisions verify_uploads.py's title-only check misses. Exit non-zero + print colliding id pairs; wire into the planning-agent's own preflight so a challenge-pass run like this one gets the check for free instead of relying on manual read-through.

- [ ] open

## Build a retention-cliff gate into the episode builder
_source: analyze_and_suggest fbfc465d-a8bc-4078-8b07-124a46260ae9 · 2026-08-14_

**Why:** The channel's own briefs have been manually re-deriving and re-stating the 'PROOF-AT-4s' rule episode by episode (b7d4f6fb, def03e8e both restate it) because nothing in scripts/ enforces it at build time — automating the check turns a recurring human QC catch into a one-time systemic fix, per playbook §4's own precedent of fixing layout bugs 'once at the system level' rather than per-episode.

**Interface / acceptance:**

Create scripts/retention_cliff_gate.py: reads the per-episode timing sidecar (VO word timestamps / beat map, same source build_ep_v2.py --dry already emits) for claude-tricks episodes and asserts the first on-screen PROOF beat (demo/table/answer reveal) lands at or before 4.0s, hard-failing the build with the offending beat's actual timestamp if not. Wire it as a `--assert-pacing` flag into channels/claude-tricks/build_ep_v2.py (already referenced by name in calendar brief b7d4f6fb but not yet implemented per current scripts/ contents) so every future episode is checked automatically instead of relying on a per-brief reminder. Feed it real numbers: 6 of 7 videos with usable retention samples this cycle show a 10-15pp drop precisely in the 4.7-6.7s band whenever the payoff isn't visible by ~4s (yt_retention.py run, 2026-08-13) — use that band, not a guess, as the gate's threshold.

- [ ] open

