# AI Unpacked (claude-tricks) — Quality Ledger

> **The apple-to-apple ratchet.** Every new episode on THIS channel must beat the last
> *published/best-produced* episode from THIS channel on the scored axes below. Same host,
> same world, same format → the only fair comparison. No episode ships until it clears the gate.
>
> Created 2026-08-05 (first entry — no ledger existed for this channel before). Baseline =
> internal build **16** ("Cut Your AI Bill In Half", public Ep 10, `E16`), the newest
> newsSplit-format episode before this one. Channel: **AI Unpacked** (`claude-tricks`), Pipeline B.

---

## 1. The current bar (what "last published/best-produced" means today)

**Pipeline v2 (Pipeline B):** ElevenLabs Hrithik VO (word timings, 0.4s breaks, style 0.4) →
HeyGen talking-photo host (`host_canonical.jpg`) → Remotion `Short` (newsSplit layout: host
pinned bottom pane, licensed b-roll top pane / full-frame cuts) → sidechain-ducked master
(§3 chain) → `add_bookends`-style outro sting.

| Build # | Public Ep | Title | Layout | VO dur | Notes |
|---|---|---|---|---|---|
| 16 | 10 | Cut Your AI Bill In Half (Most People Miss This) 💸 | newsSplit | 26.6s | **prior bar** — broll + app-demo mix, step chips, emphasis text |
| 11 | 11 | Those 20 "Secret" Claude Commands? FAKE 🤫 | newsSplit | 32.1s | in-house myth-bust card (no lifted artwork), real terminal proof |
| 20 | 8 | The Effort Dial Nobody Uses 🧠 | cut | 35.9s | cut-format reference, not directly comparable (no newsSplit) |
| 23 | — | The Best AI Just Got Cheaper (You're Overpaying) 💸 | newsSplit | 39.3s | see §4 |
| 24 | — | Your AI Forgets You — Fix It In One Line 🧠 | cut | 30.4s | see §4 |
| **26** | — | Everyone Knows You Used AI — One Line Fixes It ✍️ | cut | 29.9s | single-tape fail→fix→proof, see §4 |
| 08 | — | Google Just Put AI In Your Kid's Classroom 🎓 | newsSplit | 33.8s | live-peg news; real dated Google source as full-frame proof, see §4 |
| 28 | — | AI Faked IDs In Its Own Safety Test 🧪 | newsSplit | 30.5s | prior bar — peg gate returned STALE and was resolved by the rulebook; new in-house report-mock grammar, see §4 |
| 29 | — | That "AI" Label Is The Law Now — Europe Said No To The Delay 🏷️ | newsSplit | 33.2s | prior bar (news lane) — peg gate returned UNVERIFIED, resolved by WebSearch + zero-temporal-claim framing; 4th in-house mock family member, see §4 |
| **30** | — | Stop Describing Your Document To AI — Give It The File 📄 | cut | 29.7s | **current bar** — single-tape fail→fix→proof with the FIX gated positively (`--fix-seed-terms`) for the first time; the handed-over material is pasted on camera, see §4 |

---

## 2. The scorecard (rate every episode on these axes)

Legend: ✓✓ strong · ✓ ok · △ weak · ✗ missing. #16 = the standing bar.

| Axis | What "good" looks like | #16 (bar) | Notes |
|---|---|---|---|
| A. Host/brand consistency | Hrithik voice pinned, `host_canonical.jpg`, magenta/yellow Anton, ±3° tilt | ✓✓ | Locked params, unchanged |
| B. **Day-of freshness** | Claims verified via radar+WebSearch same session; no stale "just happened" framing | ✓ | Standard token-saving tip, not news-cycle-dependent |
| C. Comprehension pacing | 0.4s breaks, one idea/beat, ~30s target | ✓✓ | 26.6s, tight |
| D. News-split visual richness | Mix of full/split b-roll + host, no dead frames | ✓✓ | Pexels b-roll + real app-demo footage |
| E. Step-chip scaffold (Ep11 rule) | Chip never covers taught content | ✓✓ | tl default, no conflict (no on-screen text under it) |
| F. Audio finish | §3 ducked-music + limiter chain | ✓✓ | Standard |
| G. Cover (frame-zero thumbnail) | Poster Duotone, dissolves ~0.7–1s | ✓✓ | until:2.2s |
| H. Compliance | Synthetic disclosure, "not affiliated" line, no scraped/trademarked visuals | ✓ | Single-entity disclaimer (Anthropic only) |
| I. Bookend hygiene | Outro sting rendered + wired (not a loose candidate) | ✓✓ | `outro_sub_comment.mp4` via `--outro` flag |
| J. SEO/metadata | Title/desc/tags complete, dated claims where relevant | ✓ | No news claims to date |

**Gate rule:** a new episode must be **≥ the bar on every axis and strictly better on ≥1 weak
axis**, with **no regression on the spine** (A — host/voice/look identity).

---

## 3. The delta queue (ranked — what a news-forward build should push on)

1. **B — Day-of freshness pass, done properly.** The channel's news slots (§13 Playbook) had
   never been through a documented radar+WebSearch freshness gate before a build. Build #23
   is the first to run `news_radar.py` + WebSearch *before scripting* and log the result.
2. **H — Multi-entity compliance.** Prior episodes only ever named Anthropic. A build that
   names Anthropic **and** OpenAI **and** Google needs the disclaimer to cover all three, and
   every dated claim (price, release) sourced in the description — stricter than the #16 bar.
3. **D — In-house data visualization, not just b-roll.** #16/#11 used stock footage or a
   myth-bust card; a pricing story benefits from an actual (generic, non-scraped) bar-chart
   mock — a new visual grammar element worth reusing for future news/pricing shorts.

---

## 4. Per-episode log (append one row per new episode — record HOW it beat the bar)

| # | Title | Beat prev on | Held (no regression) | Video ID | Date |
|---|---|---|---|---|---|
| 23 | The Best AI Just Got Cheaper (You're Overpaying) 💸 | **B** (documented radar+WebSearch freshness pass, dated sources in description) + **H** (3-entity "not affiliated" disclaimer + dated claims) + **D** (in-house generic price-bars mock, illustrative label, no scraped charts/logos) | A, C (trimmed a data-dense line for pacing), E, F, G, I | *(pending upload)* | *(pending schedule)* |
| 24 | Your AI Forgets You — Fix It In One Line 🧠 | **E** (all 3 chip corners re-probed against the *shipped* clips, not proxies — caught that the planned `tr` for chip 3 sat on the "same question" prompt bubble, the literal proof of the beat; overridden to `tl`, edge score 0.00) + **F** (caught the master landing −21.1 LUFS, 2.2 LU under the channel spine, because the approved bed was a quieter track; level-matched it so the VO-present window matches #23 to 0.1 LU and the integrated lands −18.1 LUFS) | A, B (labels read off the recorded frames + dated 5 Aug 2026 freshness note), C (30.4s VO, dead-on the ~30s target), D, G, H, I, J | *(pending upload)* | *(pending schedule)* |
| 25 | I Built an AI Factory That Makes My Videos 🏭 (It Made This One) | **A** (first build whose host beat is *measured*, not assumed: HeyGen returns its driver audio offset from t=0 per render — +123 ms / +234 ms on this episode's two clips — so `@0.00` placement put the mouth behind the voice, and **#25 v2 and v3 shipped the payoff 234 ms out**. New `scripts/lipsync_align.py` measures it (corr 0.94/0.97, every silence boundary agreeing to <1 ms) and re-cuts the in-point; verified on the finished file by frame-match, 3.5 vs 8.4 mean \|Δ\|. Plus the host is on camera full-frame at 5.12s instead of 21.7s) + **D** (100% first-party product footage — live studio board, job queue, real `claude -p` worker log, HeyGen host — zero stock and zero third-party vendor UI, vs #16's Pexels mix; and a beat that is full-frame host → split on the measured word onset, so one line serves both the host and narrate-what-you-see) + **G** (title card HOLDS 3.40s over a frame-diff-proven calm frame: mean \|Δ\| 0.031 over 0.30–2.70s vs 2.456 on the busiest beat, i.e. 79× calmer — against #16's until:2.2 flash) + **I** (the episode's keyword end card now carries through the sting to the last frame, and the sting is trimmed to 1.60s *before* its own generic COMMENT chip, so the final frame no longer contradicts the CTA the teaser is measured on) + **H** (multi-entity disclaimer enumerated from the DELIVERED FOOTAGE: Anthropic + HeyGen named on screen → both in the non-affiliation line; ElevenLabs excluded there on purpose and covered by the affiliate disclosure, because a non-affiliation claim would be false) + **J** (publish package carries a runnable measurement plan: FACTORY comment count via commentThreads + avg-view% vs a live-read baseline, with pre-committed GO/NO-GO thresholds) | B (n/a — meta episode, no external dated claim), C (27.9s VO, 0.4s breaks, in the 26–30s band), E (all 3 chip holds ≥1.5s: 2.73/2.09/3.06s; corners re-scored off the shipped windows), F (−18.6 LUFS integrated, TP −4.4 dBFS, within 0.2 LU of the last **shipped** master #26). **Two trades written down, not hidden:** the ≤4s tail cap leaves the sting's SUBSCRIBE readable only 0.80s (under the ≥1.5s chip bar) — the keyword won; and chips 1 & 3 have no 0.00 corner at all on a dashboard this dense (best 0.0507 / 0.0814), so they sit on header/metadata chrome rather than on taught content | *(pending upload)* | *(pending — slot 2026-08-08T14:30:00Z)* |
| 26 | Everyone Knows You Used AI — One Line Fixes It ✍️ | **D** (the fail, the one-move fix and the proof are ONE unbroken session — no cut between "before" and "after" for a viewer to distrust — with both halves gated on the filmed text: `fail_matched` on the robotic draft, `fix_forbidden_term` null on the rewrite) + **E** (chip corner scored off the shipped clip over the *exact cut window* by the new `probe_frames.py`, and the rule extended to the caption band, which was covering the proof sentence until the punch camera was raised) + **F** (caught the bed's 30s-window level being 2.5 dB under its whole-file level, the number the locked 0.35 ratio was calibrated on) | A, B (evergreen — news peg dropped on purpose, see notes), C (29.9s VO, on the ~30s target), G, H (OpenAI + Anthropic named), I, J | BlQ-gDzw1aE | scheduled 2026-08-12 10:30 UTC |
| 08 | Google Just Put AI In Your Kid's Classroom 🎓 (Parents, Check This) | **B** (a genuine same-session-verified news build, the axis #26 deliberately punted on: WebSearch on 2026-08-06 confirmed the Google Workspace Updates post dated Aug 4 and its Aug 10 web-rollout peg; scheduled Aug 7, well inside the peg — a live-peg news short, not evergreen) + **D** (new proof grammar: the hero beat is the *real, dated official source* itself — Google's own blog post captured via Playwright, composed into a full-frame 1080×1920 card with an "OFFICIAL SOURCE · Aug 4, 2026" badge — extending #23's "in-house illustrative viz" to "the actual announcement as attributed proof"; split-pane Pexels b-roll + host fill the rest, no dead frames) + **H** (screenshot is Google's public post shown *attributed and dated*, not a scraped/relabeled chart; synthetic-media disclosure on; honest single-entity "not affiliated with Google" line; source URL + date in the description) | A (reused the pre-rendered rust-outfit host clip; magenta/Anton cover + custom 16:9 thumb + watermark unchanged), E (chip "ASK YOUR SCHOOL IF IT'S ON" placed `tr` in dead space over the full-frame host close, nothing taught under it), F (§3 ducked-music + limiter chain applied by the builder), G (Poster-Duotone cover, until:2.2), I (outro sting via `--outro`), J (title/desc/tags complete, dated source linked). **Two trades written down, not hidden:** (1) **C regression** — 33.8s VO, above the 26–30s band; a longer multi-clause news item, the one soft step back vs #26's 29.9s. (2) **Not instrumented** — unlike #24/#25/#26 this build did *not* run `probe_frames.py` (chip corner), `lipsync_align.py` (host clip reused as-is, offset not re-measured), or a LUFS check on the master; verification was frame-level visual spot-checks across every beat, so E/F/G are "visually confirmed," not measured. | xZirrXHzM4Q | scheduled 2026-08-07 10:30 UTC |

| 27 | This Free Google AI Now Does The Math On Your Files 📊 | **B** (a *plan-time* filmability gate, new: `record_demo.py --preflight` asks the account whether the capability is showable BEFORE any VO or HeyGen credit is spent — verdict LOGGED_OUT, exit 3, which killed PATH A *and* PATH B's on-camera half in one measurement instead of at record time; and the peg is capability-first, so the 3.5-week-old Jul 16 rename is one orientation line and never a 'just happened' claim) + **D** (new reusable proof grammar `scripts/make_doc_mock.py`: a 4-state in-house document-grounding surface — sources / cited answer / compute cell / rollout board — with progressive reveal, so a demo that legally could not be filmed still gets four distinct authored beats instead of one static card) + **E** (found and fixed a *systemic* caption-over-content bug: the locked `StatBars` drew its axis labels at `0.76·H + 26` = y1485, permanently inside the y1440–1517 caption band — 'TOTALS' was sitting on the Q2/Q3 labels. Fixed in the component, not the episode; every future chart beat inherits it. Also rejected a 0.00-scoring `bl` chip corner because it crowded the ILLUSTRATIVE disclosure — score ranks, it does not decide) + **F** (loudness solved by measurement against the last genuinely SHIPPED master: −19.1 → −18.0 → **−18.4 LUFS**, an exact match to #26, and the playbook's ~0.4 LU/dB sensitivity figure was measured wrong here at ~0.65 LU/dB) | A (host full-frame on the hook from frame 1 and on the payoff hard cut; lipsync **measured**, +23 ms on both clips at corr 0.997, under the ~45 ms threshold, so no shift was needed), G (Poster Duotone cover, until 3.0s), H (synthetic-media disclosure + single-entity 'not affiliated with Google' — only Google is named on screen), I (outro sting intact), J (title/desc/tags publish-ready). **Three trades written down, not hidden:** (1) **D is weaker than #26 on authenticity** — #26 shipped one unbroken real tape; this ships zero vendor footage, because the account could not show the product. Honest, compliant, and still a step down on 'real proof'; the fix is a human `--setup-profile` login, not a better mock. (2) **C regression** — 39.1s VO against the 26–30s band and #26's 29.9s; the episode carries a rename orientation, a free-vs-new split and a rollout honesty beat, and it was already cut from 41.6s. (3) the statBars beat is the one beat with **no** step chip, because an in-comp chart cannot be corner-probed before the render. | *(not uploaded — delivered as a draft post)* | *(unscheduled)* |

| 28 | AI Faked IDs In Its Own Safety Test 🧪 (Why That's Good News) | **B** (first build to run the §10 **PEG FRESHNESS GATE** as a gate rather than a habit — `news_radar.py --peg-check "AI created fake identities social engineering safety tests" --air-date 2026-08-10` returned **STALE, exit 2** (first_seen 2026-08-05, age 5d, limit 4d), logged to NEWS-RADAR.md. #23/#08 ran a freshness *pass* and passed; this is the first to be told NO and to resolve it by the gate's own rulebook. A WebSearch sweep of the whole story stream proved fix (a) had nothing to buy — every item newer than the peg is coverage of the same Aug-4 report — so fix (b): **not one line of the script makes a temporal claim**, no 'just', 'today', 'breaking'. Verification also went to the **primary source** (aisi.gov.uk's own incident report) rather than stopping at coverage, which is what caught that the '19 instances' and '10 runs' figures reported separately are one finding: 19 unsanctioned actions in 10 of 122 runs, 17 Mythos 5 / 2 GPT-5.6-Sol) + **D** (new reusable proof grammar `scripts/make_report_mock.py`, third sibling of the chat/doc mocks: finding / test-conditions / lab-vs-your-app, drawn glyphs only, no logo and no screenshot — and it establishes the **attribution footer** variant, because unlike #23/#27's invented ILLUSTRATIVE numbers these figures are real and sourced. The tie-back beat is a visual argument the channel has never made: the same switch, off in the lab and on in your app) + **H** (the hardest compliance call of the build was a **cut**: the Aug-6 secondary coverage alleging the agent 'erased evidence' / covered its tracks is absent from the primary AISI report, so per the brief's own rule it does not appear anywhere in script, graphics or description — the most dramatic available detail, dropped for being single-sourced. Multi-entity 'not affiliated' names Anthropic **and** OpenAI; every on-screen figure is dated 4 Aug 2026 on its own face, not only in the description) | A (host full-frame from frame 1 on the hook and on the payoff hard cut; lipsync **measured** at **+23 ms, corr 0.9994**, under the ~45 ms threshold so no shift — and this matters more here than on a cut-format episode: newsSplit plays ONE host clip across the whole video, so an unmeasured lead would have been out of sync for all 30s, which is exactly what #08 (the closest apple-to-apple newsSplit build) never checked), C (**30.5s** VO — 0.5s over the 26–30s band but the tightest news build on this channel: #08 33.8s, #27 39.1s), E (all 3 chips corner-probed on the SHIPPED holds over the exact cut windows: tl/tr both 0.00, bl/br 0.030–0.112; **tr** chosen on all three because tl would stack the chip under each mock's own left-aligned header, and bl/br ink IS the source attribution — the one element that may never be crowded. Holds 6.30/3.12/4.96s, all clear of the ≥1.5s bar), F (**−18.5 LUFS**, within 0.1 LU of the last genuinely shipped master #26 at −18.4; TP −2.7 dBFS. Sensitivity re-measured at ~0.56 LU/dB, a third distinct value on the same chain), G (Poster Duotone, until 3.0s), I (outro sting intact), J (title/desc/tags publish-ready). **Three trades written down, not hidden:** (1) **the peg is 5–6 days old on the air date and no amount of framing changes that** — the episode is honest because it never claims recency, but it is not a same-day news build, and the brief's day-of pass on Aug 10 is still owed and is a human step. (2) **C is still 0.5s over band.** (3) **A b-roll beat shipped wrong on the first cut and was caught at frame QC, not by any gate**: the 'Nobody told it to.' secondary hook played over a clip of a human at a keyboard — the frame arguing against the line. No probe can catch this (nothing is covered); it needed a person's eyes on an extracted frame. Promoted to the Playbook. | *(not uploaded — delivered as a draft post)* | *(unscheduled)* |

| 29 | That "AI" Label Is The Law Now — Europe Said No To The Delay 🏷️ | **B** (the peg gate returned a verdict #28 never hit — **UNVERIFIED, i.e. absent from local radar history**, which §10 says is *not* a fresh peg and must be resolved by WebSearch before proceeding, not by assuming the radar simply missed it. The sweep (EC digital-strategy's own "Commission starts enforcing … on 2 August"; Cooley 3 Aug; Lewis Silkin 24 Jul; Latham's Digital Omnibus note) found **no** newer development in the stream — no enforcement action, no platform label rollout, no new Omnibus step — so fix (b) again: zero temporal claims, and the one date spoken is an *applicability date*, which is as true on Aug 12 as on Aug 6. Where #28's verification stopped at "is this fresh", this one had to resolve a **contested** fact: the brief's whole premise is that Art. 50 was NOT deferred, and the Digital Omnibus genuinely did defer other obligations — so every beat names *which* duty moved and which did not, and the chart's unit is literally "months deferred") + **D** (new reusable proof grammar `scripts/make_label_mock.py`, **fourth** sibling of the chat/doc/report mocks and the first about *content provenance*: a labelled-media tile, the in-force date, the two label classes, the penalty ceiling. The "photo" inside the tile is drawn, not stock — a mock of a labelled picture must not put a real photographer's frame or a real person's face under the word "deepfake". Carries the report-mock's **attribution** footer, since every figure is real. And the chart is the argument rather than a decoration: three bars in ONE unit — 16 / 4 / **0** months deferred — so the punch beat is the bar that isn't there) + **E** (a defect class no probe covers, found at frame QC and then fixed *in the generator*: all four corners scored 0.00 on both mock holds, the chips were legally placed — and two of them printed the **exact same string** as the mock's own chrome header directly beside them. An overlay does not have to cover content to be a defect; duplicating it is the same §4 failure at low volume. `make_label_mock.py`'s headers are now chosen to be distinct from the chip labels an episode will put over them, so the fix outlives this episode) + **F** (−19.2 → **−18.4 LUFS**, an exact match to the last genuinely shipped master #26; sensitivity re-measured at **0.62 LU/dB** — a fourth distinct value on this chain (0.40 / 0.65 / 0.56 / 0.62), which is now enough evidence to state plainly that it is duration- and bed-dependent, not a constant) | A (host full-frame from frame 1 on the hook and on the payoff hard cut; lipsync **measured** at **+23 ms, corr 0.9993**, under the ~45 ms threshold so no shift — and as on #28 this matters because newsSplit plays ONE host clip across the whole video), E (chips also gated on hold length: 3.00 / 4.76 / 2.82s, all clear of the ≥1.5s bar; no chip on the statBars beat (cannot be corner-probed pre-render) and none on the penalty mock, whose whole frame is one number), G (Poster Duotone, until 3.0s, two-line stack, host readable under it), H (synthetic-media disclosure to be set at publish; "not affiliated" names the European Commission and the EU AI Office alongside the labs, because a public body is named on screen; every figure dated on its own face, sources dated in the description; **no EU emblem, flag or lockup anywhere** — the instrument is named in plain type and every glyph is drawn, including a deliberately generic "AI" badge that cannot be mistaken for the official Code-of-Practice icon set), I (outro sting intact), J (title/desc/tags publish-ready, sources dated). **Three trades written down, not hidden:** (1) **C regression** — 33.2s VO against the 26–30s band and #28's 30.5s; the episode has to carry an in-force date, two label classes, a deferral table and a penalty before it can spend the meta-moment, and it was already trimmed once from a 40s draft. (2) **D is weaker than #26 on authenticity for the third build running** — zero real vendor footage, because there is nothing filmable about a regulation; the b-roll is one licensed abstract clip and everything else is authored. (3) **the "deepfakes are the target" beat is the weakest narrate-what-you-see link in the cut** — an abstract particle field does not *assert* deepfakes; it was chosen because the honest alternatives (a real face under that word) assert something false about a real person, and the step chip carries the meaning instead. | *(not uploaded — delivered as a draft post)* | *(unscheduled — brief targets 2026-08-12)* |

| 30 | Stop Describing Your Document To AI — Give It The File 📄 | **D** (#26 proved the fail and the fix can share one tape when the fix REMOVES a tell; this is the first build where the fix ADDS material, which is a harder proof — the viewer has to watch the document land. New `record_demo.py --followup-paste` inserts it in one motion so the filmed order is honest (page arrives, then the question), and the payoff is no longer a claim about grounding: `--fix-seed-terms` gates the second answer on **"Reinstatement Levy" / "Schedule C"**, wording that exists nowhere but the pasted clause, measured **0.21s after the first token**. Also the first tape whose payoff was *off-screen* rather than late — a tall paste pushes the answer below a fold the page never scrolls — fixed in the recorder with a measured scroll-to-bottom + 3s still hold, not by hunting with a scroll in the edit) + **E** (all three chips re-probed on the SHIPPED styled clip over the exact cut windows; no corner scores 0.00 on a chat this dense, so each was decided by *what* the ink is: chip2 took `tr` 0.135 over `bl` 0.184 / `br` 0.159 specifically because bl/br are the pasted clause the beat exists to show, and chip3 took `br` 0.130 because it is the only corner whose ink is the answer's trailing "I'd need your monthly rent" caveat rather than the grounded finding) + **A** (host lip-sync **measured**, not assumed, per Ep25: `lipsync_align.py measure` returned **+23 ms on both clips at corr 0.997** — an order of magnitude under Ep25's 123/234 ms and under the ~45 ms audio-ahead threshold, so no in-point correction was applied and the decision is auditable) | B (n/a — evergreen, zero dated claims; the pasted agreement is our own invented text), C (29.7s VO, 0.4s breaks, dead on the ~30s target; secondary hook — the grounded answer — lands at **14.98s** against the brief's ~15s), F (−18.5 LUFS integrated vs the shipped #26 reference −18.4, TP −1.9 dBFS; one bisect step, +0.8 dB, measured sensitivity 0.50 LU/dB), G (Poster Duotone frame zero, 3.0s hold), H (multi-entity: OpenAI named because ChatGPT is the filmed surface, Anthropic because the channel's boilerplate carries it), I, J. **Three trades written down, not hidden:** (1) the caption band crosses clause 9.3.2's "(1.5) months' rent" on the paste beat — the punch is already at style_punch's clamp ceiling and the horizontal ink cap is 1.042, so there is no camera left to lift it; the *operative* sentence (9.3.3) and the whole payoff beat are clear. (2) The proof beat is deliberately camera-free — a punch on top of the recorder's scroll is two moves fighting — which means the page's own "Log in / Sign up for free" pills are uncropped there and the watermark sits over one. (3) Chip 1 spans two beats and on the second it covers the top line of the question bubble the *previous* beat already established; every alternative corner covers the hedge itself | *(pending upload)* | *(pending schedule)* |

**#30 build notes (curriculum revision; the recorder grew a positive gate and a scroll):**
**Topic move was the point of the revision.** The Aug-13 slot was a news row and the standing
draft was a third model-picker short in 12 days — the channel's weakest-retention lane. This
takes the next unproduced chapter of the Ep2 "painful problem → one-move fix" structure instead,
and stays evergreen: there is no dated claim anywhere in the script or description, and the
"rental agreement" handed over is **our own invented text** (`assets/ep30/clause_9_3.txt`), not a
real document, so the mock-family compliance rule is satisfied without a mock — the vendor UI is
real, only the paper is ours.
**The plan-time probe paid for itself, and its answer was the brief's own guess.** The brief said
to check whether *attach* exists logged-out and to fall back to paste. `--preflight` returned
LOGGED_OUT (expected — we film anonymously by choice), and the page's own copy said "Log in to …
upload files". That is a claim, not a measurement, so it was measured: all **three** logged-out
`input[type=file]` elements are image-only (`accept="image/*"`), and a `.txt` set on the only one
that takes it comes back **"Unable to upload probe_doc.txt"**. Paste is not the cheaper path here,
it is the *only* path.
**Two new recorder gates, both promoted to the playbook.** `--fix-seed-terms` is the positive twin
of `--fix-forbid-terms`: #26's fix worked by *removing* a tell, so absence was the proof; a fix
that *adds* context has to be proved by presence, and the Ep24 rule (lexical, never numeric) is
what makes it honest — the gate is `Reinstatement Levy` / `Schedule C`, invented terms that cannot
be produced by a model that did not read the paste, where any numeric gate would have been
satisfied by the hedged answer's own "1–2 months' rent" guess. `--followup-paste` lands the
material in one motion instead of human-typing a legal clause for 50 seconds.
**Roll variance is real and the gate is what caught it — three takes, no loosening.** Take 1 failed
on my *own* term list: the brief specified `it depends,typically,generally,without seeing` and the
answer hedged in different words ("That depends entirely… usually… often"). Correcting the list to
the hedge *vocabulary* is not loosening — a numeric or topic gate would have been — but it is worth
naming that I changed a gate after seeing an answer. Take 2 then drew a roll that refused to answer
at all ("Please upload your lease"), which is a different failure than hedging and was re-rolled
rather than accepted. Take 3 passed both halves and is the shipped tape.
🔴 **A payoff can fail by being off-SCREEN rather than late, and §10b's "never scroll to hunt for
it" does not cover that case.** The pasted clause renders ~1100px tall, so the grounded answer
streamed *below the fold* — and chatgpt.com's mobile web does not auto-scroll to a streaming
answer. The seed gate passed at +0.21s and the money line was never on camera. The fix is in the
recorder, not the edit: `--followup-scroll` scrolls to the *bottom of the conversation*
(deterministic — the end of the answer, not a guessed pixel offset), then holds still for 3s and
stamps `fix_proof_start/end`. Hunting for a late sentence is still banned; bringing a promptly-
generated one into the viewport is what a reader does next.
**Ink threshold is part of the measurement, not a default (new §10c note).** `probe_frames.py ink`
at the default `--thresh 34` reported a 1.042 cap on the composer beats, because the composer's own
rounded **box fill** counts as ink against a black page. At `--thresh 80` only the typed text
counts and the honest cap is **1.114** — the difference between a real camera and none. The
converse also bit: the paste beat's 1.084 was measured on the composer *alone* and sliced the first
character off every line of the answer still on screen above it ("he answer depends…"), so it was
cut back to the whole-frame cap 1.042. **Probe the region you care about, but verify against the
whole frame.**
**QC catch (cheap, free):** the compose punch was slicing the "Log in / Sign up for free" pills at
the top frame edge — the "sliced white blob" §10c warns about. Pushing the center to style_punch's
own clamp ceiling (`1 − 0.5/zoom` = 0.550 at 1.114) puts the crop top at y197 and removes them
entirely, at zero cost since the composer ink sits y844–1075.
**Not done on purpose:** not uploaded, same reasoning as #27/#28/#29 — the manifest contract turns
the delivered video into a draft post, and §9's publish preflight exists because a direct upload
plus a draft post is how this repo once produced two identical scheduled Shorts.
`containsSyntheticMedia` and `verify_uploads.py` are publish-time steps for the human who arms it.
(`verify_uploads.py --channel claude-tricks` was run read-only during this build: 0 discrepancies.)
**Coordination:** the tape is deposited in the footage bank as `session_d_document_grounding` with a
new `BANK-INDEX.md`, so the Aug-14 bank job re-records nothing.
**This is the new bar #31+ must beat.**

**#29 build notes (the revision's open question was the whole job):**
The Aug-12 brief was a REVISION whose entire point was that an earlier draft had left "was the
4-month deferral adopted?" unresolved. It is resolved here, and the resolution is *narrower* than
either the stale hook or a naive reading of the Omnibus: the deferral is real but applies to
high-risk obligations (Dec 2027) and, separately, to **machine-readable marking under Art. 50(2)**
until 2 Dec 2026 **only for generative systems already on the market before Aug 2026**. Deepfake
labelling and disclosure moved not at all. That three-way split is why the chart exists and why its
unit is months-deferred: it is the one shape that makes "not delayed, not deferred" checkable
rather than assertable.
**The peg gate returned a third verdict.** #23/#08 got fresh, #28 got STALE; this one got
**UNVERIFIED** — the story is simply not in local radar history. §10 is explicit that an unknown age
is not a fresh peg, so it was escalated to WebSearch rather than waved through. Worth noting the
radar gap itself: a regulatory-compliance story with a hard date is exactly the kind of item the
RSS hot-regex does not catch, and it will not catch the next one either.
**Craft catch that generalizes (promoted to the playbook):** a status pill sized by a hardcoded
right edge ran "UNLABELLED DEEPFAKES" through its own border. Same family as every other
measure-don't-guess lesson in this repo — if the string is a variable, the chip is a measurement.
**Not done on purpose:** not uploaded, same reasoning as #27/#28 — the manifest contract turns the
delivered video into a draft post, and §9's publish preflight exists because a direct upload plus a
draft post is how this repo once produced two identical scheduled Shorts. `containsSyntheticMedia`
and `verify_uploads.py` are publish-time steps for the human who arms it.
**Still owed:** the brief's mandatory **day-of** freshness pass on 2026-08-12. If an enforcement
action, a platform label rollout or a fresh Omnibus development has landed by then, it takes the
cold open and lines 0–2 get re-cut (`build_ep_v2.py --ep 29 --tag v3`).

**#27 build notes (capability-first revision; the preflight earned its keep on its first run):**
The brief was a REVISION of an Aug-9 Gemini Notebook short, reframed off a stale "Google just
renamed" peg onto the capability, with a **mandatory plan-time filmability check**. That check did
not exist, so it was built: `record_demo.py --preflight` loads the real recorder profile, DOM-probes
auth and asserts `--expect-terms`, films nothing, and exits **0 AVAILABLE / 3 LOGGED_OUT / 4 GATED**
so a brief can branch in code. First run returned **LOGGED_OUT**: `notebooklm.google.com` now
redirects to `notebook.google.com`, which bounces to `accounts.google.com`, and the gemini profile
holds no Google session. That is strictly worse than the brief's PATH B assumption — PATH B's
fallback beat (upload 2 PDFs, ask across them, film the cited answer) needs the *same* login as
PATH A's compute demo. Restoring it is `--setup-profile`, headed and human-only. So the demo became
100% in-house: `scripts/make_doc_mock.py` + the locked `StatBars` comp, zero vendor UI, and code
execution is voiced as "rolling out now" over an authored rollout board rather than claimed on camera.
**The preflight found its own bug first.** Its initial verdict was `logged_in: true` on a page whose
entire body was the Google sign-in form — `LOGIN_MARKERS` was written for chatgpt.com ("Log in") and
Google says "Sign in". Same family as §10b's "a check written against the wrong selector doesn't
error, it just never fires". Auth probing is now per-vendor text **plus** the auth host.
**Environment finding worth keeping:** every `channel=`-pinned Playwright launch on this machine —
`"chromium"` *and* `"chrome"` — hangs to the launch timeout, while the identical Chrome-for-Testing
binary launched with no channel comes up in 0.5s. The preflight falls back and records which build
it used; without that it would have reported a browser failure as a product verdict.
**QC catch (systemic, promoted to the playbook):** `StatBars`' axis labels were inside the caption
band by construction. Fixed at the component level (baseline 0.76 → 0.70), which retroactively
explains any chart beat that read cramped and prevents every future one.
**Not done on purpose:** not uploaded. The manifest contract turns each delivered video into a draft
YouTube post, and §9's publish preflight exists precisely because a direct upload plus a draft post
is how this repo produced two identical scheduled Shorts once already. Metadata ships publish-ready;
the arming click stays human.
**This is the new bar #28+ must beat — but #28 should beat it on D by getting a real tape back.**

**#23 build notes:** freshness pass 2026-08-05 — `news_radar.py` (0 new hits since last run)
+ WebSearch confirmed no fresher (<48h) model/pricing story beat the Jul 24 (Opus 5) / Jul 30
(GPT-5.6 Luna −80%) pair, so the price-war angle stood as the cold open per the job brief.
Generic price-bars mock: `channels/claude-tricks/gen_ep23_pricebars.py` → `card_pricebars.mp4`
(illustrative $ bars, no real leaderboard/site screenshot, no logos). *(Retired 2026-08-05:
the PIL card + Ken Burns mp4 was superseded by the native `stat:pricebars` StatBars beat in
`build_ep_v2.py` — component `remotion-studio/src/components/StatBars.tsx`; the script and both
rendered `card_pricebars.*` assets were deleted. The compliance lesson above still stands.)*
B-roll: `fetch_broll.py`
(Pexels, 6 clips, licensed/no-attribution-required — `assets/ep23/broll/manifest.json`).
**QC catch (Ep11 rule, applied to a new case):** first render had an `emphasis` text overlay
("80% cheaper — same everyday answers") sitting directly on top of the price-bars graphic's
own `$14`/`$1.40` labels — text-over-content, same failure class as the step-chip rule, just on
a different element type. Fixed by dropping that emphasis line (the graphic's own "-80%" badge
already carries the beat) and keeping emphasis only where it has clear space (over the host on
the payoff line). **Lesson for the Playbook:** the Ep11 "never cover the taught content" rule
applies to *any* overlay (chips, emphasis text, captions) over *any* content beat, not just
step chips over demo footage — QC every overlay against whatever's on screen under it, not just
chips against recordings.
**This is the new bar #24+ (news slots) must beat.**

**#24 build notes (cut-format how-to, staged/asset-first production):** assembled entirely from
pre-approved staged assets — no asset was regenerated, only cuts/in-points/mix.
**All five demo in-points were re-derived from the MEASURED `.timeline.json` sidecars of the
shipped clips**; `beat_map` v1's numerals had been fitted off *provisional* sidecars and its
`line_starts` were a regression prediction, so every number moved (e.g. beat 4 `3.20` not `4.15`,
beat 7 `10.00` not `8.25`). Real VO boundaries came from `vo_v2.words.json` break markers.
**QC catch #1 (Ep11 rule, proxy failure mode):** `step_chips` v1 picked `tr` for chip 3 from a
*proxy* clip (`demo_reask.mp4` didn't exist yet) and self-flagged it PROVISIONAL. On the real
clip `tr` is the **worst** corner (edge +11.69) — the re-ask prompt bubble lives top-right and is
the literal "same question" proof the beat is teaching. Re-probed → `tl` (edge 0.00). Chips 1/2
re-probed too and held (`tr`/`tl`), but against corrected windows (v1's were built on a superseded
recording: `seed_typing_start` 10.217, not 8.278).
**QC catch #2 (audio):** first master read **−21.1 LUFS** vs the channel's shipped −18.8/−18.9.
Cause: the approved `music_bed` asset swapped to `bed_3` (−13.7 LUFS) while the locked `volume=0.35`
ratio was calibrated on `bed_active` (−8.3 LUFS). Fixed with a per-episode `music_gain_db` pre-gain
(+5.4 dB = the programme-level delta) — chain topology untouched → −18.1 LUFS, TP −3.4 dBFS, and the
VO-present window matches #23 within 0.1 LU.
**Known limitation carried forward:** `hook_frozen_chat_still` could not be composited into frame 1.
`build_ep_v2.py`'s beat parser knows only `host`/`host2`/`rec:`/`stat:`, and `Short.tsx` supports
`kind:"image"` only as a *whole* segment — there is no underlay/per-segment overlay layer, so a still
cannot sit under a beat without surrendering one of the 9 VO-pinned beats. Shipped as a
thumbnail/frame-zero-system asset instead (`beat_map` option A).
**Secondary hook:** the 14.0–15.5s window is structurally unreachable for the *personalized-answer*
reveal (proven in `beat_map` v1 — the seed must precede the answer and lines 1–2/4 are
freshness-protected). Delivered instead: the Memory control visibly flipping at **14.42s** synced to
the spoken word "Memory", and the personalized reveal pulled forward to **18.33s** (vs `beat_map`'s
computed 20.17s) by re-cutting beats 6–7 off the measured sidecar.

**#26 build notes (evergreen curriculum short, single-tape production):**
**Freshness call — the news garnish was deliberately dropped, not forgotten.** The brief carried an
optional em-dash / "giveaway words" garnish pegged to a Dataconomy piece of Aug 4, to be
re-verified at publish. Two things killed it: (a) `news_radar.py` returned 0 new hits (and its
Anthropic feed URL now 404s — the other two feeds are fine), and (b) a WebSearch found the peg is
not just stale but **contested** — the Aug 2026 Economist analysis (55,940 sentences) concluded em
dashes are *no longer* a reliable AI tell, and only one major model still overuses them. Shipping a
week-old claim the current reporting contradicts would have failed axis B outright. Per the brief's
own escape hatch it ships as pure evergreen; its case is the Ep2 structure, not a peg. *(Note: the
brief specified `news_radar.py --peg-check`; no such flag exists — the freshness pass was the plain
radar run plus the WebSearch, which is what the flag would have done.)*
**Scheduling — Aug 11 was NOT free either.** The brief moved this off Aug 8 (double-booked with the
operator's queued factory Short) onto Aug 11. A live `verify_uploads` read showed the runway booked
solid Aug 1→11: Aug 11 10:30 UTC already holds build 11 (`YrjPbZK28Oo`). Scheduled **Aug 12** — the
first date that satisfies the brief's stated intent (extend the runway past Aug 10, no same-day
collision). ⚠️ Build **24** is still unpublished; if it is meant for Aug 12 this one moves to Aug 13.
**New tooling this build (both promoted to the Playbook):** `record_demo.py --followup` (fail→fix→
proof in one session, with `--fail-terms` / `--fix-forbid-terms` gates on the two halves) and
`scripts/probe_frames.py` (`ink` = widest safe punch zoom/center for a window; `corner` = step-chip
corner scores). The single tape ran clean on the first take — the robotic draft came back with
"I hope you're doing well" / "due to unforeseen circumstances" / "please don't hesitate to reach
out" / "Kind regards", and the rewrite matched none of the forbidden tells in 357 chars.
**QC catch #1 (probe window):** the chip probed `tl` 0.13 / best `br` over a 4s window, and `tl`
**0.00** over the 3.7s the spec actually cuts — the padding ran past the submit, where the page
scrolls. Corner decisions now come after `--dry`, off the real segment times.
**QC catch #2 (caption over proof):** the payoff beat's caption ("NOW") sat on the last line of the
human rewrite — the sentence the whole episode exists to prove. Fixed in the camera, not the
caption: `human` punch center 0.438 → 0.524 at zoom 1.05 lifted the card ~90px clear of the band.
**QC catch #3 (audio, and a wrong first diagnosis):** master landed −19.5 LUFS on the standing bed
with nothing swapped. First hypothesis — a 0.8 LU quieter ElevenLabs VO — was wrong (the fix moved
the meter 0.1 LU and was reverted, knob and all). Real cause: `bed_active` is −8.3 LUFS whole-file
but **−10.8 over its first 30s**, which is all a Short hears. `music_gain_db` +1.9 → **−18.2 LUFS**,
peak −2.7 dBFS, VO-present payoff window within 0.8 LU of #24's.
**Minor, accepted:** the cover's `emojis` was set to two glyphs but `Cover` slices to 2 UTF-16 units,
so the second (✍️, a multi-codepoint sequence) was dropped; config changed to one emoji so intent
matches output rather than re-cutting the frozen component.
**This is the new bar #27+ must beat.**

---

## 5. Global-worthy findings (candidates for `docs/PRODUCTION-PLAYBOOK.md`)

- **Multi-entity compliance disclaimer.** When a script names more than one AI lab, the
  "not affiliated with X" line must list every named lab, not just the first one ever added.
- **In-house data-mock grammar for news/pricing shorts.** A simple PIL bar-chart (`gen_ep23_pricebars.py`
  pattern: rounded bars, Anton labels, one yellow "-XX%" badge, an "ILLUSTRATIVE" footer disclaimer)
  is a reusable, zero-cost, logo-free way to visualize a pricing/benchmark story without ever
  screenshotting a real leaderboard site. *(2026-08-05: this grammar now lives in the native
  StatBars component — `remotion-studio/src/components/StatBars.tsx`, invoked as `stat:pricebars`
  beats in `build_ep_v2.py`. The one-off PIL script is retired/deleted; use StatBars for new
  episodes. The principles — generic bars, illustrative label, no scraped charts/logos — carry over
  unchanged.)*

## 6. Archived (out of active planning context — 2026-08-10)

Internal builds **Ep27 · Ep28 · Ep29 · Ep30** are archived. Local files live under
`channels/claude-tricks/_archive/` — see `_archive/README.md`. Reasons: all four shipped as
draft posts, none were armed inside their peg windows; Ep28's peg went stale (age 5d against a
4d limit) between build and would-be-arm. Their per-episode rows STAY in §4 above as build-lesson
history — the Playbook lessons they seeded (peg gate as a hard gate, in-house mock family, StatBars
axis-band fix, `probe_frames.py` shipped-clip probe, `--fix-seed-terms` payoff gate) already
propagated to `docs/PRODUCTION-PLAYBOOK.md`. Do not read these rows during current-batch planning.

The unlisted YouTube video `cv1nzSC7mMY` "Google Just Put AI In Your Kid's Classroom" is likewise
archived (11 views total, no plan to revive). Local files: none (`ep08` slot below was the internal
build that shipped it, which remains in §4). External flip: pending — will privatise via
`scripts/yt_cleanup.py` in a bundled action.

---

## Build Club bc01 — "Stop Paying For Websites" (Ch. 1) · PUBLISHED 2026-08-14 16:00 IST · youtu.be/bWoa98zMWjA

**First Build Club episode (Friday serialized builder slot; series bible BUILD-CLUB.md).** 53.7s body + 5.1s spoken-CTA outro. Delivered `epbc01_v2_outro.mp4` **−14.20 LUFS** (finalize gate −14.0±0.5 PASS, first try at `music_gain_db 1.0`). Title suffix "— Build Club Ch. 1" applied by the new series-aware `apply_series_suffix` (chapter from spec, Day/30 counter untouched — bc keys are non-numeric so dailies never see Fridays).

- **New engine surface (additive, daily template untouched):** beat tokens `chapter`/`pause`/`recipe` → in-comp ChapterCard/PauseCard/RecipeCard (`remotion-studio/src/components/BuildClub.tsx`) + `rail` spec pass-through → persistent PROMPT→FILE→LIVE progress rail at top 170. `hook.baked` added (frame-zero thumbnail rule — HookCard's slide/fade left frame 0 headline-less; same class as the Ep11 cover bake).
- **All footage REAL:** claude.ai interview tape (the pinned 3-section prompt run verbatim; Claude asked 6 questions one at a time), real 10.5KB index.html extracted from the page, Netlify Drop deploy ON CAMERA ("Voilà, your project is live"), same file permanently live at **anitas-tiffin.netlify.app** (VJ account, CLI deploy after the zip-API path served text/plain — always `netlify-cli deploy`, never raw zip POST). Phone tape re-shot after Playwright letterbox defect (viewport 540×960@dsf2 records CSS px pinned top-left in the 1080×1920 canvas — crop+lanczos upscale fixed; next time record viewport 1080×1920 dsf1).
- **Drop automation lesson:** Netlify Drop's React dropzone ignores synthetic DragEvents AND a failed CDP drag re-renders the page (killing the file inputs) — the reliable path is `set_input_files` on the `accept=".zip,.html,.htm"` input, FIRST, immediately after load. Unclaimed drop sites are password-gated (401) + expire in 1h — never film tape B against them.
- **Host:** pinned outfit_11 (wide f55806a4 / pip dc9533a1), 4 clips, lipsync +23ms corr 0.99 — no cuts needed. Sol appears: hook wide band (baked art `gen_bc01_hook.py` — art carries visuals only, HookCard owns all words), splitWide beside the live site, spoken outro CTA (+17.9dB to −14 spine).
- **KPI to watch:** `yt_engage --count-keyword SHIPPED` + `--count-keyword netlify` unique authors; Ch.2 return rate; subs/100 vs daily baseline. Pinned comment = `assets/bc01/SHARE-PROMPT.txt` verbatim (post-publish + one Studio pin click). Playlist `PLIuiep7RRSGE`.

### AUDITION BLOCK (retro-filled 2026-08-14, per the new BUILD-CLUB.md §7 gate)

Filled after the fact, so it says what was actually measured and nothing more. **This is the
record bc01 shipped without** — the gate exists from Ch.2 onward, pre-arm.

| # | Gate | Result |
|---|---|---|
| 1 | Audio spine (−14.0 ±0.5 LUFS) | **PASS** — −14.20 LUFS on `epbc01_v2_outro.mp4`, first try at `music_gain_db 1.0` |
| 2 | Lip-sync (corr > 0.9) | **PASS** — +23 ms, corr 0.99, 4 clips, no cuts needed |
| 3 | Caption/chip placement (`probe_frames.py corner`) | **NOT RUN** — the highest-risk gate on this template and the one that was skipped: TEMPLATE v1 puts captions in a low strip over real phone footage inside the PhoneFrame casing, which is exactly the "chip over taught content" class the tool exists to decide. Unmeasured on the shipped cut |
| 4 | Standalone-first (≤2s series stamp) | **NOT MEASURED** — designed for (STANDALONE-FIRST is a locked TEMPLATE v1 rule) but never verified against the delivered file |
| 5 | Homework CTA survives the tail | **NOT MEASURED** — spoken outro CTA rendered and levelled (+17.9 dB to the −14 spine); readability duration on the final frames not checked |

**Record integrity defect (the reason §7 is now mechanical):** this heading carried
`youtu.be/_ebCZEGFu74` — the **retired v1 cut** — while `bWoa98zMWjA` (the v4 Android-app cut) is
what actually published at 16:00 IST. Corrected 2026-08-14. An audition record that names a file
other than the shipped one is void by definition, and nothing in the pipeline caught it.

**Ch.2 (bc02, 2026-08-21) is auditioned against this block**, not against the dailies — gates 3, 4
and 5 are open ratchet targets, and the Ch.1 retention curve (`yt_retention.py --video bWoa98zMWjA`)
is the input for where the hook needs work. See `docs/stats/AI-UNPACKED-READ-2026-08-14.md` §4 for
the pre-committed d0 thresholds that decide whether Friday stays Build Club.
