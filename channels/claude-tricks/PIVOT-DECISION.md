# AI Unpacked (claude-tricks) — Pivot Decision + Flop-Proof Short Lock

> **Provenance.** Recovered from the Claude Code session transcript
> `~/.claude/projects/-Users-vijenderpanda-Ai-youtube-pipeline/31fcf55d-a434-4255-bc03-3229fe7403b6.jsonl`
> (session ran **2026-08-17 ~21:06 IST → 2026-08-18 ~09:10 IST**, 86 human turns, 430 events).
> The adversarial-workflow detail comes from that session's task-output files under
> `…/31fcf55d-…/tasks/` (`wumi186tl.output` = the 14-agent workflow result;
> `b6cx3pocx.output` = the retention pull). Cross-checked against memory note
> `build-club-friday-series.md` (🔴 PIVOT block) and `docs/stats/RETENTION-NEW.md` / `RETENTION.md`.
> **Nothing was rendered, armed, or spent in this session** — this is the locked plan for content sign-off + production.

---

## 1. TL;DR

- **Pivot (VJ, 2026-08-18, on data):** the serialized **Build Club** Shorts format is **de-prioritized**. Two chapters, two flops (**8–9 views**) across two weekdays and two packagings, while same-feed **standalone tips pull 107–228**. The constant is the *serialized-Short format*, not the day/cadence/spike/algorithm. The Shorts slot goes back to **standalone tips**; the build *story* moves to the **Friday long-form + playlist**.
- **Method:** a 14-agent adversarial workflow (Learn → Ideate → Judge → Craft → Critique) generated **12 candidate tip ideas**, scored them on 9 metrics + a skeptic, crafted 4 hook variants, wrote a script + buildable engine spec, and ran a final flaw-hunting critic.
- **Winner (77/90, beat 11):** *Ask Claude to build a tool → a real working app renders live in the side panel (Artifacts).* Type one line → a clickable **bill splitter** appears and computes **$27.33** on screen. No code, no copy-paste.
- **Hook (chosen from 4):** `D_outcome_first_reverse` — frame 1 is the *finished* calculator computing a real total, burned title **"I BUILT THIS BY TYPING ONE LINE,"** then hard-cut to the empty panel and rebuild it live. Grade-3 readability.
- **Critic verdict:** **GO WITH FIXES (medium confidence)** — 10 mechanical fixes itemized below.
- **Locked:** Artifacts short, all fixes applied, into production. Final title = **"I Built A Working App By Typing One Line 🤯."**
- **Blocked on 2 preflights:** (1) can claude.ai Artifacts be screen-recorded logged-in; (2) is HeyGen funded. Session ended before both ran.

---

## 2. The pivot — serialized Build Club → standalone tips

**Decision (VJ, 2026-08-18, on data):**
1. The **daily Shorts slot carries standalone tips** — the only lane that gets sampled. Any build-derived Short must stand 100% alone and drop all "Ch. N" framing from hook and title.
2. The **serialized build STORY lives as the Friday long-form + playlist** (long-form-native), not in the feed.

**Retention / view evidence used to justify it** (pulled live this session from the Mac):

| Lane / video | Views | Notes |
|---|---|---|
| Standalone tips (same feed) | **107–228** | the sampled lane |
| News shorts | **13–17** | flops |
| **Build Club Ch.1** `bWoa98zMWjA` (Fri Aug 14, v4) | **9** | still 9 views **4 days on** |
| **Build Club bc01 v5** `38qTA1IZg9w` (Mon Aug 17, "…4 Minutes — Your Turn") | **8 @16h** | 0 likes, **retention withheld** (sample below privacy threshold = feed not sampling it) |

Supporting analysis from the workflow's `learn:patterns` agent (grounded in the channel's own numbers):
- **Same-day, same-feed experiment (Aug 11):** a tip hit **165** vs a news short at **10** — a 13–16× gap, confound-controlled. **Tips median ≈134, news median ≈14.** The **lane, not the weekday, decides everything**, and the feed decides in **24–48h**.
- Tip winners cited: **171 / 169 / 149 / 148 / 147 / 119 / 117** (view counts of prior tip shorts).

**The reasoning (why format, not day/spike/algorithm):**
- Two flops span **2 different weekdays** (Fri + Mon) → cadence exonerated; **2 different packagings** (v4, and the re-cut v5) → repackage didn't help. The only constant is the **serialized "Build Club Chapter" Short**.
- This channel **has no spike mechanism at all** (5 subs, ~100% Shorts-feed dependent). "No spike" is the expected state for *every* video — not a symptom. The real questions are only: *did it get sampled (d0 ≥ ~90)* and *what's the retention curve.*
- There is **no algorithm to "beat"** — the Shorts algorithm is an **audience-satisfaction proxy**: it shows every new Short to a few-hundred-impression test audience and only expands if scroll-through / retention / shares hold. "Align with the algorithm" decodes to "satisfy the first few hundred cold feed viewers in the 3–15s window."
- **Jenny Hoyos cold-traffic warning:** a cold stranger swiping the feed has zero context on "Chapter N of a build," and the **"— Build Club Ch. N" title actively signals "you missed the start" → swipe.**
- Going **daily Mon–Thu multiplied the flop** — one flop/week became four.

**Caveat noted in-session (rigor):** bc01 v5 was 16h in and *could* still crawl, but (a) the channel's own law — no video that started in single digits has ever climbed out — and (b) Ch.1 stuck at 9 for 4 days, made the n=2 call defensible now rather than burning 3 more chapters. Confirm at the next 07:00 IST snapshot.

---

## 3. The adversarial workflow (method)

Authored + run this session as a background "dynamic workflow" (Ultracode on). **14 agents, all `claude-opus-4-8`**, in 5 phases. Total ≈ **845K tokens, 59 tool calls**.

| Phase | Agents | Role |
|---|---|---|
| **1. Learn** | `learn:patterns` | Mine own data for what wins (accusation hooks, muted-legibility, lane>weekday, 24–48h decision). |
| | `learn:template` | Trace exact buildable `.v2.json` schema + engine invariants (`len(beats)==len(lines)`, host/host2/rec beat types). |
| | `learn:recency` | List already-shipped tip topics to **avoid duplicating** (model picker, effort dial, token saving, CLAUDE.md, custom slash commands, etc.). |
| **2. Ideate** | `ideate:power-feature` | 3 ideas — evergreen power-features beginners never turn on (Artifacts / Projects / MCP). |
| | `ideate:cost-speed` | 3 ideas — cost/speed "before-after" in the 147–149 lane. |
| | `ideate:prompt-teardown` | 3 ideas — weak→strong prompt rebuilt live. |
| | `ideate:contrarian` | 3 ideas — "you're doing the slow/wrong thing right now" corrections. |
| **3. Judge** | `judge:score` | Score all 12 on **9 metrics** (below), produce a ranked list. |
| | `judge:skeptic` | Adversarial "most-likely flop mode" kill-attempt on the top ideas. |
| **4. Craft** | `craft:hooks` | 4 hook variants (A–D), each muted/thumbnail-tested. |
| | `craft:hookjudge` | Pick the single best hook. |
| | `craft:script` | Full ~34s script in the locked Jenny-Hoyos structure. |
| | `craft:spec` | Buildable episode `.v2.json` spec matching the engine + 12 buildable checks. |
| **5. Critique** | `critique` | Final flaw-hunter → GO / GO-WITH-FIXES / NO-GO with itemized fixes + residual risks. |

**Judge scoring rubric (9 dimensions, ~10 each → max 90):**
`lane_fit · demand · hookability · sustainability_3to15s · demoability · readability_ease · evergreen · rpm_affiliate · dupe_safe`.

**Recovery limitation:** the per-agent full outputs are truncated to ~401-char previews in the saved task file. The **full `judge:score` ranked list of all 12 numeric scores did NOT survive** — only the winner's complete row (below) is recoverable. The other 11 candidates' individual scores are **not found in transcript**.

---

## 4. The full candidate slate (all 12)

Grouped by the 4 ideation clusters (3 ideas each). **Only the winner's score survived** (see limitation above); the "why it lost" column is reconstructed from each cluster's stated angle + the winner's judge verdict + `learn:recency`'s dupe list. Where a specific reason isn't in the transcript it's marked *(inferred)*.

| # | Title | Cluster | Score | Why it lost (recoverable / inferred) |
|---|---|---|---|---|
| **1** | **Ask Claude For A Tool — It BUILDS It On Screen 🤯** *(Artifacts)* | power-feature | **77 — WINNER** | Won: most muted-legible payoff in the slate. |
| 2 | You Re-Explain Your Job To AI Every Chat. Do This ONCE *(Projects / persistent memory)* | power-feature | not found | *(inferred)* weaker muted proof — persistent memory has no single sharp on-screen "it appeared" moment; adjacency to shipped "CLAUDE.md memory" tip. |
| 3 | Claude Can Reach Your REAL Apps — Not Just Chat *(MCP)* | power-feature | not found | Cluster flagged MCP **honestly as carrying real beginner-comprehension risk**; included "for breadth." |
| 4 | Claude Writes You An ESSAY — You Pay Per Word 💸 | cost-speed | not found | *(inferred)* strong lane but crowded vs shipped token/cost titles; less muted-legible than an app appearing. |
| 5 | One Long Chat Is DOUBLING Your AI Bill 💸 | cost-speed | not found | *(inferred)* same — cost lane already worked (147–149) but heavily shipped; dupe pressure. |
| 6 | You Send 5 Prompts. Send 1 (Half The Time) ⚡ | cost-speed | not found | *(inferred)* speed before/after, weaker single-frame payoff than Artifacts. |
| 7 | Your Prompt Forgot WHO You Are 🫥 (Add 1 Line) | prompt-teardown | not found | *(inferred)* before/after output diff is legible but subtler than a whole app materializing. |
| 8 | Stop DESCRIBING The Style — Paste 1 Example 🎯 | prompt-teardown | not found | *(inferred)* good muted before/after, but text-output change < app-appears for cold muted swipe. |
| 9 | Make AI Grade Its OWN Answer 📉 (Then Fix It) | prompt-teardown | not found | *(inferred)* payoff is a text re-grade — low visual arrest; overlaps #12. |
| 10 | STOP Explaining Your Bug To Claude — Paste The Red Error | contrarian | not found | *(inferred)* dev-lane audience narrowing; cluster explicitly avoided abstract "Stop X" flops. |
| 11 | STOP Pasting Code Into Claude — Drag The Whole Folder In | contrarian | not found | *(inferred)* dev-lane; drag action is muted-legible but narrower demand than a universal tool. |
| 12 | STOP Trusting Claude's First Answer — Make It Grade Itself | contrarian | not found | *(inferred)* overlaps #9; self-grade payoff is text, low visual arrest. |

Cluster angle notes worth keeping: the **contrarian** agent deliberately avoided abstract "Stop X" hooks because they flopped in-feed — **"Stop Describing Your Document" = 8 views, "Stop Copy-Pasting Between AIs" = 5 views** — and required a real on-screen BEFORE state landing by ~6s. The **cost-speed** agent deliberately dodged every shipped token/model title (Burns Your Tokens, Prompt Caching, Best AI Got Cheaper, Fast vs Deep, Effort Dial, WRONG Model, Ask For a Table).

---

## 5. The winner — "Artifacts" short (full spec)

**Idea:** In Claude.ai, ask for a small tool ("build me a bill splitter") and Claude renders a real, working, clickable app **live in the side panel (Artifacts)** — you use it right there, no coding, no copy-paste into another site.

**Winner judge row (the only full score recovered):**
`lane_fit 9 · demand 9 · hookability 9 · sustainability_3to15s 8 · demoability 10 · readability_ease 8 · evergreen 9 · rpm_affiliate 6 · dupe_safe 9` → **total 77.**
Judge verdict: *"TOP PICK. A working app literally materializing on screen is the single most muted-legible payoff in the whole slate — the empty-then-full side panel IS the story… rides the vibe-coding wave, zero dupe overlap. Only real risk: the hook mis-reading as crowded 'AI writes code' — mitigate by making the render the whole visual and picking an instantly-useful tool (tip splitter), not an abstract widget. Cut the render to seconds so it doesn't drag past 15s like Table did."* Skeptic did **not** kill it.

**Why it won:** most muted-legible payoff in the slate (understandable sound-off and to a non-English viewer — Jenny's test), standalone, evergreen, one clean tape, zero title-dupe (no shipped title touches Artifacts), and it matches the proven **"painful habit → one move → visible payoff by ~5s"** shape of the 169/171-view winners.

### The 4 hook variants + why the reverse won
Craft produced 4 variants; **3 of 4 IDs survived** recovery (the 4th, presumably "C," is *not found in transcript*):
- **`A_empty_panel_accusation`** — real Claude.ai screen, chat box with "build me a tip calculator" typed, a fat magenta arrow to a **visibly EMPTY** grey side panel. *Rejected:* its frame-1 is a blank panel that reads muted as "nothing here."
- **`B_watch_it_build_itself`** *(runner-up)* — opens mid-build. *Rejected:* a frozen half-drawn calculator risks reading as a **broken/loading UI** (a flop-mode, not a hook).
- **(4th variant — id not recovered)**
- **`D_outcome_first_reverse` — CHOSEN.** Frame 1 = a **finished** bill splitter with a cursor tapping a button and the total ticking to **$27.33** (bill split 3 ways); faint origin line "build me a tip splitter" pinned at the left edge; burned title **"I BUILT THIS WORKING APP BY TYPING ONE LINE."** Then the body hard-cuts back to the empty panel and rebuilds live.

**Why D:** it is the **only hook whose first frame is unambiguously a working, useful thing** — strongest on the two filters this cold, 100%-feed channel is decided by: (1) the **muted first-second swipe** (a functioning app + a real number reads instantly sound-off / non-English), and (2) **thumbnail-grade** (works as a static title+thumbnail, which A and B cannot). Outcome-first doesn't "spend the reveal" because the frame shows only that an app *exists* while withholding *how* → clean curiosity loop; the empty→full rebuild is still the mid-video payoff (preserves the "Forgets EVERYTHING" one-sharp-visual-resolved-fast shape); most loop/rewatch-friendly. Readability grade 3.

### Locked script (7 lines / 7 beats after fixes) — from `craft:spec` spec_json
Final title: **"I Built A Working App By Typing One Line 🤯"** · epTag `ARTIFACTS · BUILD IT LIVE` · target 34s.

1. *This calculator works — and I wrote zero code. I just asked for it in one sentence.* — `host` (HOOK)
2. *Watch me build it from an empty box. By the end: one line, no code. Watch.* — `host` (SPOKEN FORESHADOW)
3. *In Claude, I type one thing — build me a tip splitter.* — `rec:epNEW/hold_type.mp4`
4. *A real app builds itself in the side panel. No copy-paste, no other website.* — `rec:epNEW/hold_build.mp4`
5. *Split the bill three ways — tap — twenty-seven thirty-three. It just works.* — `rec:epNEW/hold_total.mp4` (PAYOFF)
6. *That's Artifacts. Ask for a tool, and Claude builds the working thing right there.* — `host2` (WHY IT WORKS)
7. *Follow. I unpack one AI skill every single day.* — `host2` (CTA + loopback to hook)

Beats: `host, host, rec:hold_type@0, rec:hold_build@0, rec:hold_total@0, host2, host2` (shape = proven host-bookended demo that produced Table 169 / Effort 171). Host panels: `["I WROTE","ZERO CODE — I","JUST ASKED"]` / `["EMPTY BOX","TO A WORKING","APP — WATCH"]`. Step chips `STEP 1/3 TYPE ONE LINE (tr)`, `2/3 IT BUILDS LIVE (tl)`, `3/3 TAP THE TOTAL (tl)`. Hook still `epNEW/hook_art/calc_working.jpg`, `until 1.6`. Music `music/bed_active.mp3`. `outro:true`, `outro_dur:0`, `outro_cta:"auto"` (Sol speaks CTA). Endcard `endcard_comment.png` (e.g. "Comment BUILD — I'll send you the exact prompt"), `over_outro:true`. Caption hotwords: WORKS, ZERO, ONE, SENTENCE, TAP, LIVE, LINE, FOLLOW.

**Assets to capture** (`craft:spec`): `hook_art/calc_working.jpg` (finished calc still), `hold_type.mp4` (empty panel + one line typed, pre-submit — redact recents/account name per §10b), `hold_build.mp4` (app building, keep <2s), `hold_total.mp4` (tap → $27.33), `outro_card.mp4` (gen_outro_card.py), `endcard_comment.png`, `music/bed_active.mp3` (already in repo).

---

## 6. Critic's verdict — GO WITH FIXES (medium confidence)

Scorecard: **LANE PASS · HOOK weak-mixed · 3–15s SUSTAIN FAIL (as speced) · READABILITY PASS · DEMO/PROOF pass-conditional · LOOPBACK PASS · MUTED-LEGIBILITY mixed · DUPE-SAFETY pass-but-adjacent-risk · COMPLIANCE pass-with-checks · RPM PASS.**

**All 10 required fixes (verbatim intent):**
1. **Kill the front-load (highest flop-impact).** As speced the first changing screen appears ~7.6s and the $27.33 payoff resolves ~18s after ~6s of Sol talking-head — the exact shape that bled the **Table short to 0.256@15s** (`ret_ct.json ueTa4OnVNk8`, drops 4.8/5.2/7.4s). Merge L1+L2 into one host beat; get a real changing screen on by **~4.5s**, payoff by **~13–14s** (or keep Sol as a corner PIP over the live screen through the death zone).
2. **Reconcile `beats==lines`.** Script had **8 lines** but the engine invariant + rationale want **7 beats**. Ship the proven ep12 **7/7** shape (merge L1+L2 and L7+L8). Do not feed 8 lines into a 7-beat skeleton.
3. **Fix "tip splitter" vs "bill splitter" incoherence + the math.** Demo computes **$82 / 3 = $27.33** with no gratuity, but it's labeled a "tip splitter" (a muted viewer catches that a tip splitter produced a tip-free number). Rename to **"bill splitter"** throughout (cleanest). Also **27.33 × 3 = 81.99 ≠ 82.00** — have the app resolve the penny so it sums.
4. **Unify title = thumbnail** on the winning proof-first pattern. Thumbnail "I BUILT THIS BY TYPING ONE LINE" is the channel's best frame (proof-first "I Built" = 223 lifetime); make the YouTube title match (**"I Built A Working App By Typing One Line"**) instead of the weaker capability-reveal "Ask Claude For A Tool — It BUILDS It."
5. **Resolve hook-motion vs static conflict.** The engine `hook` block renders a **static image** — it cannot do the "finger taps, total ticks to $27.33 in second one" motion. Either drop the motion claim (ship a bright static still) or make beat-0 a `rec:` clip with L1 VO over it. Don't spec motion the opener can't deliver.
6. **Cut the "building live" dead-air.** The Artifacts spinner is low-info motion landing ~12–15s (the collapse point). Timelapse / hard-cut empty→built to **<2s**; never show slow streaming code in the death zone.
7. **Trim the tail to match the "abrupt end."** Beats put two host2 recaps + a spoken outro CTA *after* the payoff (~7s draggy tail). Fuse why-it-works + CTA + loopback into **one host2 (~3–4s)** rhyming back to the hook; `outro_dur:0`; avoid double-CTA (L8 "Follow" + outro_cta both speaking a CTA).
8. **Frame for 9:16.** Desktop claude.ai is a wide chat-left/panel-right layout that shrinks illegibly in portrait — use §10c pro-framing (never center-crop); QC that the typed line + app buttons are legible at **240px** feed size; QC frame-0 fully opaque and bright.
9. **Production preflight before shooting.** Verify current claude.ai still renders an interactive Artifact from a one-line prompt in a **logged-in recorder profile** (`record_demo.py --preflight`). A logged-out / changed-UI return kills the tape (same trap that killed the Ep27/Ep20 demos). Confirm "wrote zero code / runs right where you asked" is accurate in the shipped build.
10. **Re-probe step-chip corners on the SHIPPED clip, not the plan** (§4 Ep24 lesson). The app builds in the RIGHT panel, so a chip safe on the composer beat can cover the app on the build/payoff beats. Re-score each chip corner against the actual capture + its measured VO window.

**Compliance checks flagged:** nominative fair use covers recording claude.ai, but set `containsSyntheticMedia=true`, add a "Not affiliated with Anthropic" line, and put **no Anthropic logo** on our own cards/overlays.

---

## 7. Residual risk + realistic ceiling

The critic's 5 residual risks (judgment calls that survive the fixes):
1. **Concept adjacency to a just-killed lane (biggest un-fixable risk):** "AI builds you a real working thing, no code" is the exact emotional promise of Build Club bc01 ("Four minutes ago this didn't exist… no code, no card," 8–9 views). Standalone single-tape framing helps, but the feed may pattern-match it as the same build-a-thing lane that just flopped.
2. A calculator is a **generic, low-arrest muted still** — the wow lives in the *invisible* cause (one line typed), so the opening frame leans entirely on burned copy; weaker than the top winners' visible accusation / before-after (169/171).
3. Even fully fixed, this is a **capability-reveal** ("look what it can do"), which historically sits **MID** on this channel (Skills 119, Best AI Got Cheaper 107) below top accusation/before-after tips. **Realistic ceiling ~100–140, not a 170 breakout** — set expectations accordingly.
4. The reverse hook (finished app → hard-cut to empty → rebuild) can read as a **continuity glitch** sound-off, costing a slice of cold swipers before the rebuild pays off.
5. **Artifacts UX churns** — a shipped tape can go stale fast if Anthropic changes the side panel (evergreen premise but fragile capture).

**VJ/assistant counter (why GO anyway):** what killed Build Club was **serialization** ("Chapter N," needs prior context, 4-min build), not the concept. A standalone tape with the payoff by ~5s is a genuinely different animal. Risk isn't zero (cold feed pattern-matches on surface — "person building an app on a Claude screen"), but the realistic ceiling ~100–140 sits solidly in the sampled tips lane.

---

## 8. LOCKED decision

**LOCKED (VJ, 2026-08-18):** the **Artifacts standalone tip Short, all 10 fixes applied**, into production. Final packaging = title **"I Built A Working App By Typing One Line 🤯,"** thumbnail = burned proof-first line, clean **bill-splitter** demo with numbers that sum, front-loaded so a changing screen is on by ~4.5s and the payoff lands by ~13–14s, 7/7 beats, ~34s. Editing decisions are the assistant's; content is signed off.

---

## 9. Production pipeline + gating preflights + current status

**Pipeline (learned in-session):**
- `channels/claude-tricks/build_ep_v2.py --ep <key>` builds the episode from `episodes/<key>.v2.json` and **auto-generates the VO (ElevenLabs) + the Sol host (HeyGen)**.
- The **real screen recordings** (`rec:` clips — `hold_type.mp4`, `hold_build.mp4`, `hold_total.mp4`) must be **captured first** via `scripts/record_demo.py`.
- Then render to master with **`--skip-arm`**; run QC gates (visual lipsync `scripts/lipsync_visual.py`, caption/dead-space, narrate-what-you-see); present the finished cut — **unarmed until VJ's explicit go** (ARM SWITCH).

**Two gating preflights (must clear before spending):**
1. **Can claude.ai Artifacts be screen-recorded logged-in?** (`record_demo.py --preflight` in a logged-in recorder profile — a logged-out / changed-UI return kills the tape.)
2. **Is HeyGen funded?** (wallet balance for the Sol render.)

> **Status at session end:** both preflights were **about to run — not found completed in transcript** (last event 2026-08-18 ~03:39 UTC / ~09:09 IST, right after the pipeline was understood). Render *readiness* was confirmed earlier: **T5 SSD mounted** (9.2G media + host library), ElevenLabs + HeyGen keys in `.env`, `token_claude-tricks.json` present, Remotion `node_modules` + Anton font local. The only open unknowns were the two spend/login-gated preflights above.
>
> **Preflight update (2026-08-18, recovery session — both now CLEARED):**
> 1. **Artifacts recordable — ✅ AVAILABLE.** `python3 scripts/record_demo.py --site claude --preflight` (headless, read-only, no prompt sent) returned `state: AVAILABLE`, `logged_in: true`, exit 0; the claude.ai left-nav body includes the **Artifacts** entry, so the feature is reachable in the recorder profile. ⚠️ The probe body + screenshot exposed real chat titles and account context → **redact recents / account name on the actual tape** (critic fix #9 / Playbook §10b).
> 2. **HeyGen funded — ✅.** `/v2/user/remaining_quota` = **811 api credits** + free-tier credits; per `heygen-account-constraints` memory auto_reload was ON (Aug 5) — eyeball the dashboard before the Sol render so a failed reload can't kill it mid-run.
>
> → **Clear to capture the three `rec:` clips.** The next step (`record_demo.py --site claude --prompt …`) SENDS the one-line prompt to the live logged-in account and starts the production/spend chain → awaiting VJ go (ARM SWITCH still applies).

**Serialized Build Club hold state (executed this session):**
- **bc02** "…CHEAPEST Model — Build Club Ch. 2" (`sM6I7bsKHu8`) was **silently auto-scheduled to publish Aug 18 16:00 IST** (`publishAt 2026-08-18T10:30:00Z`). **HELD private** via the new **`scripts/yt_unschedule.py`** (reversible; publishAt cleared; verified with a fresh read after a read-after-write cache scare). It will **not** auto-publish.
- **bc06 (Wed) + finale bcs1f (Thu):** not yet uploaded → nothing to unschedule; **on hold**, do not produce/arm as serialized Shorts.
- **Daily Shorts slots Aug 18 / 19 / 20 are now empty** → fill with **standalone tips** (produce-to-master + present; ARM SWITCH still applies). The Artifacts short is the first fill.
- Optional salvage noted: the already-shot bc02 build footage could be re-cut as a *standalone* Short (drop "Ch. 2," lead with the result) so the work isn't wasted.

**New/changed files from this session (in working tree):** `scripts/yt_unschedule.py`, `docs/stats/RETENTION-NEW.md`, `docs/stats/retention_new.json`, `scripts/retention_recheck.sh`; committed `721b5aa` = Playbook Jenny-Hoyos learnings + **34s length verdict** (killed the stale 22–28s target) + weekly retention cron.

---

### Recovery gaps (be honest)
- **Full `judge:score` ranked scores for the 11 losing candidates: not found in transcript** (per-agent outputs truncated to ~401 chars; only the winner's 77-row survived).
- **4th hook variant ("C") id/detail: not found in transcript** (only A / B / D survived; assistant text confirms there were 4).
- Full `judge:skeptic` kill list and full `ideate` per-idea detail beyond title+angle: **only partially recoverable** (previews truncated).
