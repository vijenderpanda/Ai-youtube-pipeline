# QUALITY-LEDGER — Aashiqana (AI Hindi Romantic Songs)

> **Doctrine:** Every new episode must be **>= the current bar on every axis** and **strictly better on at least one weak axis**, with **zero regression on the brand spine** (original AI couple, original Suno track, Gen Z cold-open sound DNA, karaoke word-sweep, synthetic-media disclosure). This file is the single source of truth for what "better" means. Update it the same day an episode ships.
>
> Companion files: `BRAND-BIBLE.md` (spine), `BOOKENDS.md` (sting specs), `../../docs/PRODUCTION-PLAYBOOK.md` (cross-channel craft).

---

## 1. CURRENT BAR

**Song #02 — "Aaja Ve"** · shipped 2026-08-03 · long-form + Short LIVE (previous bar: song #01)

Exact params (the floor every future episode must clear):

| Component | Param |
|---|---|
| Track | Suno Pro v5.5 · Gen Z cold-open formula · locked base style + ≤3 descriptors · female-echo chorus · 3:34 · user pick from 4 candidates ranked by first-2s volumedetect |
| Couple | Original AI couple · fair late-20s glam (STANDING USER RULE: fair, unmistakably Indian, never dusky renders) · Kino XL · full-anchor charref Mid for two-shots, face-crop refs for solos, solo close-up audition BEFORE scene batch |
| Visuals | 12-shot scripted story arc + alternates, 4 locations (hilltop, wine picnic, denim lane, dusk ridge) · 5 Hailuo 2.3 hero motion clips · shots pinned to forced-aligned song sections · thumbnail-grade frame 0 · xfade 0.7s |
| Lyrics on screen | Karaoke word-sweep, white-to-gold `wiperight` · stable-ts **forced alignment** on demucs vocal stem · onset-snap · sweep-cap · = the v3 sync pipeline (user-approved) |
| Formats | Long-form 1080p + 9:16 Short (hook cold-open, 30s) |
| Compliance | Synthetic-media disclosure ON · original song · no celebrity likeness |

**Bar rule:** Song #02 must ship with at least these params. Any component below this table is a regression and blocks publish.

---

## 2. SCORECARD

Score each episode 1–5 per axis at ship time. Honest scores only — an inflated score here silently lowers the bar.

| # | Axis | What 5/5 means | Song #01 |
|---|---|---|---|
| A1 | Couple magnetism / glam | Couple looks like a late-20s fit/glam Bollywood lead pair; thumbnail-stopping faces | **2** ⚠ weak — reads older/traditional (saree, full beard) |
| A2 | Track instant-connect | Vocal hook lands in the first 3 seconds; passes the "would a Gen Z listener stay?" test | **4** — user-approved after 2 rejections |
| A3 | Motion richness | Nearly every shot has real generated motion, not Ken Burns | **3** — 6/10 shots real motion |
| A4 | Karaoke sync polish | Word-sweep hits every syllable; no drift, no early/late sweeps | **4** — v3 pipeline (forced align + onset-snap + sweep-cap) |
| A5 | Cinematic grade consistency | All shots share one color grade / mood; feels like one film | **3** — locations coherent but grade not unified |
| A6 | Story arc across shots | Shots follow a mini-narrative (meet → spark → rain → embrace), not a montage | **2** ⚠ weak — loose montage |
| A7 | Format depth | Branded intro/outro sting, custom thumbnail pushed, long-form + Short + any extra cuts | **3** — both formats live, but no bookends, no thumbnail pushed |
| A8 | Publish hygiene | Metadata, disclosure, hashtags, end-screen policy, cards all correct at upload | **4** |

**Current weak axes (score <= 2): A1 couple magnetism, A6 story arc.** Song #02 must strictly beat at least one of these.

---

## 3. DELTA QUEUE (ranked for Song #02)

Work top-down. Each delta names the axis it attacks.

| Rank | Delta | Axis | Notes |
|---|---|---|---|
| 1 | **More real-motion coverage** — animate 10+ segments incl. B-roll beats (needs API token top-up or bigger web budget) | A3 | Motion is now the weakest axis |
| 2 | **Branded intro/outro sting** — build per `BOOKENDS.md`, reuse across episodes | A7 | One-time build, permanent gain |
| 3 | **Thumbnail workflow** — push custom thumbs to both live videos once phone-verify clears | A7 | S09 frame already designed as the thumb |
| 4 | **Canonical face-reference asset** — one clean hero + heroine close-up pair saved as the permanent charref source for future songs | A1 | Kills the mustache/hair-drift rerolls |
| 5 | **Leonardo API token top-up** — decide plan (chip pending) so scene batches run scripted, not UI-driven | — | Ops, unblocks 1 |

Queue maintenance: when a delta ships, move it into the episode log entry and re-rank what remains. New ideas enter ranked, never appended blindly.

---

## 4. ANTI-TEMPLATING RULES

1. **<= 50% frame reuse:** no episode may reuse more than half of any prior episode's frames/stills. Reused frames must be re-graded or re-framed, not copy-pasted.
2. **6–8+ fresh on-model scenes per episode:** every episode budgets at least 6–8 newly generated, charref-locked scenes (new locations, wardrobe, or blocking).
3. **Location rotation:** no episode repeats the exact 4-location set of the previous episode; swap at least 2.
4. **Reusable-by-design assets are exempt:** branded stings/bookends and the channel logo are the *only* assets allowed to repeat verbatim.

---

## 4b. DERIVATIVE CUTS (not episodes — not scored)

A **derivative cut** re-cuts an already-shipped release into another format. It generates
nothing new, so §4's anti-templating ceiling does not apply to it and it **must not be
scored or logged as an episode** — it does not move the bar and does not satisfy the
weekly cadence. Its own gate, instead:

1. It must open on a **different bar of the song** than the Short already live for that release.
2. It must use a **different visual grammar** (framing, caption treatment, shot order) — otherwise it is a duplicate upload.
3. It must be **re-aligned from the stem**, never inherit the parent release's line times.
4. Metadata must not imply a new song.

| Date | Parent | Cut | Hook bar | Differentiation vs the live Short |
|---|---|---|---|---|
| 2026-08-05 | Song #01 *Baarish Aur Tum* | `aashiqana_baarish_hookcut_9x16.mp4` (29.6s) | **final chorus, 155.28s** — "Baarish ban ke tu, mujh mein barasta ja" (2nd-loudest 2s window, chosen over the loudest for the 23s of payoff behind it) | Live Short is the **opening** chorus (0–30s), full-bleed centre crop, 3 single-line captions at 34px. This cut is the **final** chorus, 1080×1200 lyric-band composition on a blurred backdrop, 6 split-phrase captions at 58px, story-ordered shots (together → alone → lost → found) instead of the montage order. |
| 2026-08-06 | Song #01 *Baarish Aur Tum* | `aashiqana_baarish_duel_9x16.mp4` (28.0s) — **LYRIC DUEL** | **final chorus, 155.28s** — same bar as the Aug-5 hook cut, deliberately: the duel is an A/B on two *lines*, so it needs the bar that carries both | Not a montage at all — a **format**, not a re-cut. Frame-zero VERSUS card (split teal/amber duotone, VS lozenge), then exactly TWO beats: line 1 over a **still** (`characters/couple_twoshot_1.jpg`) with a numeral chip, HARD CUT on the measured vocal attack to line 2 over `scenes/scene_rooftop_1.jpg`, then a recap card and an announce card. **Frame overlap with the Aug-5 hook cut and the live Short: 0%** — both stills are new to a Short; the hook cut shipped five motion clips + `scene_rooftop_0`. Captions are ONE unbroken line per bar at 38px full-bleed (hook cut: 6 split phrases at 58px in a letterboxed band). |

| 2026-08-07 | Song #02 *Aaja Ve* | `aashiqana_aaja_ve_outnow_9x16_final.mp4` (20.1s) — **OUT-NOW GLIMPSE** | **chorus block 2, 79.20s** — the percussive downbeat 0.38s before "Aaja ve…", found by a 20ms RMS scan on the `no_vocals` stem. Chorus 1 (4.08s) was unavailable: the live Short already opens there. | Live Short TMVJHHv7v4c is full-bleed centre crop with captions **on the couple**, chorus 1, five motion clips crossfaded at 0.6s. This cut is the 1080×1200 lyric band on a blurred backdrop (captions in the 470px dead zone, never on the couple), chorus 2, and a **glimpse grammar**: one 8.3s slow-motion hero shot, then three HARD-CUT 2.0s stills, then cards. Frame-zero card == end-frame card, so it loops. **Measured frame overlap vs the live Short: 32.5%** (13/40 frames at 0.5s sampling, dHash Hamming ≤10) — all of it inside the shared S01 hilltop cold open; the montage and cards score 14–22. |

**Reserved for the Aug-9 payoff cut (`c1f78897`)** so the two do not converge: it should take
the **final chorus (151.88s) or chorus 1**, the verse scenes (**S02–S06, S08, S12** — none of
which this cut touches), and may go full-bleed. This glimpse cut deliberately leaves those
three levers unspent.

**Why the glimpse exists (2026-08-07):** it converts what was scoped as a pre-release
"KAL SHAAM" withhold teaser into post-release discovery — the song has been public since
Aug 3, so a countdown card would have been a false announcement. Same asset plan, same cut
structure, inverted grammar: the title card says **AB LIVE**, and the payoff beat is a
"poora gaana channel pe" card over the ducked instrumental instead of a withheld reveal.

**Why the duel exists (2026-08-06):** it does double duty — a comment-signal instrument
("1 ya 2?" is a lower-effort ask than "which song next?") *and* a funnel into an already-live
release. Its closing card points at **Aaja Ve**, live since Aug 3. It is a derivative cut, so
it is not scored and does not satisfy the weekly cadence.

**A/B read to collect:** this cut and the live Short are the same song, same couple, same
length, different bars. Retention delta between them tells us which bar of #01 actually
holds — feed that into the Gen Z track redo before locking its cold open.

---

## 5. EPISODE LOG

Newest first. Every entry answers: *how did this episode beat the last one?*

### Song #01 — "Tu Hi Hai (Baarish Aur Tum)" · 2026-08-03 · BASELINE
- **Beat previous:** n/a — founding episode; establishes the bar.
- **Scores:** A1:2 · A2:4 · A3:3 · A4:4 · A5:3 · A6:2 · A7:3 · A8:4 (total 25/40)
- **What worked:** Gen Z cold-open formula (chorus-first, vocals at 0:00) validated after 2 rejected track candidates; v3 karaoke sync pipeline (stable-ts forced alignment on demucs stem + onset-snap + sweep-cap) approved as the standard.
- **What to fix next:** couple reads older/traditional — glam upgrade is delta #1; shots are a loose montage — story arc is delta #2.
- **Frame reuse from prior episode:** n/a. Fresh scenes generated: 10.

### Song #02 — "Aaja Ve" · 2026-08-03 · SHIPPED (long-form https://youtu.be/ZQQvRrGWGLk · Short https://youtu.be/TMVJHHv7v4c)
- **Beat previous:** A1 couple glam 2→4 (fair late-20s glam pair, user-gated anchor, face-crop lock) and A6 story arc 2→4 (shots pinned to forced-aligned song sections; apart→memory→reunion with on-lyric payoffs: "wine ke do glass" on the two-glasses macro, "laal dress" on the red-dress reveal). A5 grade 3→4 (one golden-hour world). No regressions.
- **Scores:** A1:4 · A2:4 · A3:3 · A4:4 · A5:4 · A6:4 · A7:3 · A8:4 (total 30/40, was 25/40)
- **What worked:** judge-panel lyrics (4 candidates, 3 lenses, locked tie-break); volumedetect cold-open ranking before human listen; composition-first prompts + per-shot ref strategy (no-ref wides/macros, face-crop solos, couple-Mid two-shots); solo close-up audition before scene batch; thumbnail-grade frame-0 workaround while custom-thumb push is blocked; full lyrics in description for search.
- **What to fix next:** motion coverage still 6/20 segments (A3); no bookends, no pushed thumbnail (A7); hero identity needs one canonical face reference asset to stop mustache/hair drift rerolls; S07 full-length framing never rendered (charref tightens to bust).
- **Frame reuse from prior episode:** 0%. Fresh on-model scenes: 12 + 6 alternates.

---

## 6. HOW TO UPDATE THIS FILE

1. **At episode kickoff:** copy the gate checklist into the new episode's log stub; pull the top unblocked delta(s) from the queue.
2. **At ship:** fill in scores (honest), "what worked / what to fix", frame-reuse count; move shipped deltas out of the queue; re-rank the queue.
3. **If the episode raises any axis's best-ever param:** update the CURRENT BAR table — the bar is always the *best shipped* episode's params, not an aspiration.
4. **If a lesson generalizes beyond this channel:** copy it into `docs/PRODUCTION-PLAYBOOK.md`.
