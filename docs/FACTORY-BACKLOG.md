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

## Wire render_short.py Remotion caption_engine flag into claude-tricks default pipeline
_source: analyze_and_suggest 2097a695-a555-4f02-91db-41fdd85fac70 · 2026-08-14_

**Why:** The caption_engine flag exists in the codebase (render_short.py, a9cc42e) but is unused on the channel where the retention data most rewards punchy front-loaded text — closing this gap turns an already-shipped capability into an actual retention lever.

**Interface / acceptance:**

The Remotion kinetic-caption bridge landed in render_short.py (commit a9cc42e, opt-in via caption_engine flag) but nothing in the claude-tricks produce_short path sets it yet. Update the channel's produce_preview/finalize call sites so caption_engine defaults ON for claude-tricks (kinetic word-pop captions matching the Vaibhav-DNA pipCallout style already locked for this channel), while leaving other channels' default caption path untouched. Verify against the two videos with 'ok' retention status (Claude Code Forgets EVERYTHING, Claude Burns Your Tokens) to confirm the new caption engine doesn't regress their strong early-hold numbers before rolling to all new episodes.

- [ ] open

## Wire an automated early-cliff gate into yt_retention.py + daily_check.py
_source: analyze_and_suggest d036bc41-bb94-449d-b8af-a2752f362ca2 · 2026-08-15_

**Why:** This session hand-ran yt_retention.py --summary across 6 channels and manually eyeballed drop_points to catch the already-happening 8.4-8.8s cliff and the claude-tricks Effort Dial cliff -- both were only found because a human happened to look. Automating the same threshold check into daily_check.py (which already runs on a schedule per docs/FACTORY.md) turns this from a periodic strategist task into a standing safety net that catches the next cliff before the next 2-week cycle.

**Interface / acceptance:**

Update scripts/yt_retention.py: add a `--gate` flag that, in addition to the existing --summary output, exits non-zero if any analyzed video has a 15s hold below 30% OR any single drop_point steeper than -6pp within the first 15 seconds (the exact thresholds this session's manual review applied by hand across claude-tricks/aashiqana/already-happening). Wire `python scripts/yt_retention.py --channel <key> --days 30 --gate` into scripts/daily_check.py for every LIVE channel so an early-cliff video surfaces on the daily report automatically instead of requiring a manual --summary read every strategist cycle. Keep --summary's human-readable output unchanged; --gate only adds the exit-code + a one-line 'CLIFF: <video> -Npp at Ts' flag list to stdout.

- [ ] open

## Cap the TODAY-anchor beat duration in scripts/finalize_already_happening.py
_source: analyze_and_suggest d036bc41-bb94-449d-b8af-a2752f362ca2 · 2026-08-15_

**Why:** already-happening's first measurable retention curve shows a -23pp/-15pp double cliff at 8.4-8.8s, landing on the anchor->extrapolation handoff the blueprint's spine always produces at roughly that mark. A one-off content fix (the replaces_ref suggestion above) addresses Ep03; a finalize-time assert prevents every future episode from silently reproducing the same structural cliff without a human re-deriving the timing rule from scratch each time.

**Interface / acceptance:**

scripts/finalize_already_happening.py currently has no beat-duration assertion on the TODAY-anchor segment before the +5yr extrapolation cut. Add a hard assert (fail the finalize step, not a warning) that the anchor beat's measured VO/segment duration does not exceed ~7s, sourced from the episode's own sidecar timing JSON (same class of check as the existing §4 caption-band and §5 cover-dissolve QC gates in PRODUCTION-PLAYBOOK.md). If a beat exceeds the cap, finalize should refuse and print the offending timestamp so the human either trims the anchor script or explicitly overrides with a documented reason.

- [ ] open

## Create scripts/retention_cliff_scan.py -- network-wide early-cliff scanner
_source: analyze_and_suggest 0aba33e2-b68b-4bf2-8c18-d2493d169222 · 2026-08-15_

**Why:** Today's yt_retention.py pull independently found the SAME 4-9s early-cliff pattern on three unrelated channels in one sitting (claude-tricks 4.7-6.7s across four episodes, already-happening -19pp@8.8s, aashiqana's full-length Aaja Ve -32pp@4.3s) -- a pattern currently only caught by a human re-running yt_retention.py by hand each planning cycle, which is exactly the kind of recurring mechanical failure PRODUCTION-PLAYBOOK.md section 10 says belongs in a gate, not a reviewer's catch.

**Interface / acceptance:**

Create scripts/retention_cliff_scan.py: a thin network CLI that loops channels/*/channel.json (same iteration pattern as scripts/daily_check.py), calls scripts/yt_retention.py --channel <key> --days 30 --summary --json for each, and flags any video whose steepest measured drop_point exceeds 10pp and falls inside a 4-10s window (the recurring 'sustain, not hook' failure documented in PRODUCTION-PLAYBOOK.md section 13). Output: a single ranked docs/RETENTION-CLIFFS.md (video, channel, drop pp, timestamp, 15s-hold) refreshed on each run, plus a non-zero exit when a NEW video crosses the threshold (so it can hook into the existing com.aiunpacked.dailycheck launchd cadence without adding a second plist, per the §10 'one plist' rule). Read-and-report only, matching daily_check.py's doctrine -- no upload/retitle/reschedule. This is distinct from the already-suggested scripts/yt_retention.py --cohort (84230efd, per-channel drop-point clustering, not yet built): this scan is cross-channel and threshold-gated for the automation loop, --cohort is an interactive per-channel clustering view for a human session; build both, this one first since it plugs into the automation channels/daily_check already runs.

- [ ] open

## Add --rank-by-hold to scripts/yt_retention.py
_source: analyze_and_suggest d1680ad6-9b34-4928-b22c-ecfa31c9e64f · 2026-08-16_

**Why:** e35312bc had to manually rank four episodes by 15s/end-hold instead of avg_view_pct to fix a real segment-selection bug this cycle -- codifying that ranking into the script removes the need to re-derive it by hand on every future long-form/compilation decision.

**Interface / acceptance:**

scripts/yt_retention.py --summary currently prints per-video 15s-hold/end-hold/drop-points but leaves ranking to the human. This cycle's e35312bc suggestion had to hand-derive a '(15s hold, end hold) not avg_view_pct' ranking to select and order segments for a long-form compilation, explicitly because avg_view_pct hides the early cliff that matters. Add a `--rank-by-hold` flag to scripts/yt_retention.py that outputs videos sorted by (15s_hold desc, end_hold desc) instead of publish order, with a one-line flag on any video whose worst single-second drop exceeds 6pp inside the first 8s (the exact threshold this playbook's §edits already use). This turns a repeated manual analysis step into a reusable one for every future compilation/season-recap decision.

- [ ] open

## Add --lint-brief to scripts/host_outfit.py
_source: analyze_and_suggest d1680ad6-9b34-4928-b22c-ecfa31c9e64f · 2026-08-16_

**Why:** This exact bug (a brief instructing host_canonical.jpg instead of the pinned wardrobe) had to be found by manual audit this cycle (ab39705f) despite being documented as fixed on 2026-08-06 -- a mechanical lint on brief text closes the gap between 'fixed in the pipeline' and 'still possible in a hand-written or AI-drafted brief'.

**Interface / acceptance:**

PLAYBOOK §6 documents host_canonical.jpg as a fixed, found-and-fixed wardrobe bug (2026-08-06) -- yet this cycle's own audit (ab39705f replacing 6d0b019e) found a fresh brief in the same 08-16..30 queue still instructing 'host_canonical.jpg' for a hook clip, contradicting every sibling brief. Add a `--lint-brief <path-or-stdin>` mode to scripts/host_outfit.py that greps a draft brief/suggestion text for literal 'host_canonical' and exits non-zero with the PLAYBOOK §6 citation if found, so this class of regression is caught mechanically instead of by a manual audit pass every few days.

- [ ] open

## Build scripts/hook_qc.py -- flag any produced Short whose first 3s doesn't state the core claim
_source: analyze_and_suggest 60c7a3ec-ca7a-4676-a1f4-ce2004a6b195 · 2026-08-18_

**Why:** yt_retention.py --channel claude-tricks --days 30 shows a recurring 8-15pp drop clustered at 4.5-6s across most videos with a slow-build hook, while the channel's best-retention video states its problem in <3s. This is a repeatable, checkable pattern (not a one-off), so it belongs in a script gate rather than relying on manual QC every episode.

**Interface / acceptance:**

Create scripts/hook_qc.py: given a finished master mp4 + its line-timing sidecar (from eleven_vo.py's *.alignment.json), check whether the FIRST spoken line lands entirely within the first 3.0s and contains no scene-setting words (a small stoplist: 'so', 'today', 'in this video', 'let me show you'). Exit non-zero with a printed offending line if the hook line starts late or reads as preamble. Wire as an optional pre-flight check callable from build_ep_v2.py --dry (report-only, non-blocking) before it becomes a hard gate. This directly operationalizes the retention finding below so future episodes get checked automatically instead of caught after upload.

- [ ] open

## Build scripts/hook_qc.py -- automated proof-by-4s retention gate
_source: analyze_and_suggest 38964421-fc50-4355-a801-cb3b58c6cb34 · 2026-08-18_

**Why:** The latest claude-tricks insight explicitly proposes 'consider the hook_qc.py factory gate' after finding the same fast-hook-vs-slow-setup pattern by hand across multiple episodes -- this converts that recurring manual check into an automated one.

**Interface / acceptance:**

Create scripts/hook_qc.py: a pre-render QC gate for claude-tricks (and reusable by already-happening) that reads a built episode's spec JSON (from build_ep_v2.py --dry) plus its eleven_vo.py alignment sidecar, and asserts the FIRST on-screen payoff/proof beat (the segment kind that shows the fix/finding, not the cold-open hook card) starts at or before 4.0s of spoken audio. Exit non-zero with the measured timestamp if the proof beat starts later, mirroring the pattern of scripts/probe_frames.py (measure the real artifact, don't trust the brief's prose) and scripts/verify_uploads.py (non-zero exit, mandatory last-mile gate). This automates a lesson the insights cycle currently re-derives by hand every run: every recent brief manually cites 'proof by 4.0s' or 'cliff window 5.3-5.8s' against yt_retention.py pulls; a script makes it a build-time assertion instead of a copy-pasted paragraph.

- [ ] open

## Update daily_check.py -- flag double-challenged calendar slots
_source: analyze_and_suggest 38964421-fc50-4355-a801-cb3b58c6cb34 · 2026-08-18_

**Why:** This audit's own claude-tricks insight risk list names exactly this failure mode ('two live suggested rows both pointing replaces_id at each other... worth a human pass') as an unresolved risk with no current tooling catching it.

**Interface / acceptance:**

Extend scripts/daily_check.py (the existing network-wide daily publish-slot guard) with a new check: query factory calendar rows with status='suggested' and non-null replaces_id, build the reverse-lookup graph, and flag any pair where two 'suggested' rows point replaces_id at EACH OTHER (a mutual/circular challenge) with no third row resolving it. Print the pair's ids + titles + planned_date to the existing daily_check output/log so it surfaces on the next automated run, exactly like its existing slot-collision and duplicate-title checks -- read-only, no auto-resolution (a human picks the winner, per the channel's own suggestion_reason convention).

- [ ] open

## UPDATE scripts/build_ep_v2.py -- add a hook-cold-open preflight check
_source: analyze_and_suggest 41c7ba4a-7da6-4f3c-8b91-a2f58158adcb · 2026-08-20_

**Why:** The 4-10s cliff pattern repeats across at least 6 of the channel's 9 analytics-eligible episodes this month regardless of topic, which is a structural/timing defect the two best-performing episodes don't share -- a build-time check turns 'remember to front-load the hook' into an enforced gate instead of a per-writer judgment call.

**Interface / acceptance:**

UPDATE scripts/build_ep_v2.py (claude-tricks Shorts assembler) to add a preflight validation step that fails the build (non-zero exit, printed diagnostic) if the first spoken word or word-card timestamp lands later than 1.5s into the cut. Retention data across the last 30 days shows a recurring attention cliff clustered at 4-10s in nearly every claude-tricks episode regardless of topic (Ask AI For a Table -8pp@4.8s; Effort Dial -14pp@4.7s and -10pp@2.2s; I Built an AI Factory -14pp@6.7s and -10pp@6.4s; The Best AI Just Got Cheaper -11pp@9.2s; Claude Just Got Skills -10pp@5.8s; You Type The Same Prompt -11pp@5.3s), while the two episodes with the best 15s-hold ('Claude Code Forgets Everything' 74%, '6 Claude Commands' 68%) both land their payoff inside 2s. Implementation: read the existing captions/timing JSON build_ep_v2.py already produces, compute the first non-silence word timestamp, compare against a --max-hook-delay 1.5 (default) CLI flag, and print the offending timestamp plus the script segment responsible so the writer can move the cold-open line earlier rather than discovering the problem 48h later in analytics. Do not auto-edit the script; just gate the build with a clear failure so it becomes a repeatable check every episode passes through instead of a one-off note.

- [ ] open

## UPDATE scripts/assemble_music_video.py -- add a chant-first cold-open mode
_source: analyze_and_suggest 41c7ba4a-7da6-4f3c-8b91-a2f58158adcb · 2026-08-20_

**Why:** The flagship long-form cut loses 27pp at the 4.3s instrumental open while the channel's single best-holding video skips that delay entirely (60% 15s-hold), and three upcoming calendar briefs already request the 'chant-first' pattern by name with no generator that implements it yet.

**Interface / acceptance:**

UPDATE scripts/assemble_music_video.py (Aashiqana Pipeline A long-form assembler) to add a --cold-open-mode chant flag that cuts straight to the chorus/hook line (no instrumental intro, no establishing shot) for the first 3-4s before falling back to the full arrangement. The flagship long-form cut 'Aaja Ve' loses 27pp of viewers at 4.3s during its instrumental-led open, while the direct-address Short 'Woh insaan jise tum chhod hi nahi paate' (no instrumental delay, hero line in frame immediately) holds 60% at 15s -- the highest 15s-hold of any Aashiqana video with sufficient sample. The upcoming Unki Kahani Ch.3-5 briefs already call for 'chant-first' and 'chorus in 8s' cuts by name (calendar items 9af56f0d, 29112758) but no generator currently implements the cut pattern, so each editor re-derives it by hand per song. Implementation: accept the existing song's beat-map/lyric-timing JSON, detect the first vocal-chorus window, and render that window as the opening 3-4s before cutting to the verse/instrumental build, reusing the existing crossfade/motion-clip pipeline assemble_music_video.py already has.

- [ ] open

## Create scripts/beat_audit.py — pre-render early-structure gate (proof-by-4s, no boundary idle)
_source: analyze_and_suggest 2667b2d6-9408-4f00-ac95-347d74975b7f · 2026-08-21_

**Why:** This item is already 'suggested' in the calendar since Aug-8 and this cycle's retention pull independently reproduces the exact failure it targets (a >4s setup run before the first proof beat correlates with sub-30% 15s-holds on claude-tricks) — it should move from suggested to built now that the data confirms the rule generalizes.

**Interface / acceptance:**

CREATE scripts/beat_audit.py, a pre-render QC gate that reads a built episode spec JSON (the `build_ep_v2.py --dry` output or the `assemble_*` segment list) and flags exactly the failure mode this analysis found repeatedly: a beat sequence that spends >4-5s on setup/problem-statement before the first demo/proof/payoff beat. Usage: `python scripts/beat_audit.py --spec path/to/spec.json [--channel claude-tricks] [--max-setup-s 4.5]`. Behavior: (1) walk the beats list, classify each beat kind (`hook`, `problem`, `demo`, `cook`, `stat`, `payoff`) via its existing `kind`/tag field; (2) sum the duration of any leading run of `problem`/`hook`-only beats before the first `demo`/`cook`/`payoff` beat; (3) fail (non-zero exit, printed reason) if that run exceeds `--max-setup-s`; (4) also flag any single beat >6s with zero caption/overlay change (a 'dead air' beat, the other half of the 15s-battle). Write findings to stdout and optionally `--json report.json`. This turns the pattern this cycle found by hand (Effort Dial 10% 15s-hold / Ask-AI-Table 26% vs Forgets-Everything 74% / SKILLS 57%, all explained by setup-before-proof timing) into an automatic pre-render check instead of a retrospective retention read.

- [ ] open

## Update scripts/yt_retention.py — add --attribute, joining measured drop_points to the episode's beat map
_source: analyze_and_suggest 2667b2d6-9408-4f00-ac95-347d74975b7f · 2026-08-21_

**Why:** Already flagged 'suggested' in the calendar (Aug-7) and this cycle needed exactly this join done by hand across 8 measurable videos to reach its conclusions — building it removes that manual step from every future analysis cycle.

**Interface / acceptance:**

UPDATE scripts/yt_retention.py to add `--attribute` mode: `python scripts/yt_retention.py --channel claude-tricks --video-id <id> --attribute --spec channels/claude-tricks/episodes/<ep>.v2.json`. It should map each returned `drop_points` timestamp onto the nearest beat boundary in the episode's built spec (reusing the same beat/segment timing `beat_audit.py` reads) and print which named beat owns each cliff, e.g. 'drop at 4.8s -> beat 2 (problem-statement, 3.2s-9.1s)'. Currently this analysis had to eyeball drop_points against beat names by hand for every video (Effort Dial's 2.2s/4.7s/5.4s drops vs Ask-AI-Table's 4.8s) — automating the join turns 'where does it bleed' from a manual cross-reference into one command's output, and lets a daily/weekly retention pass name the offending beat directly instead of just the timestamp.

- [ ] open

