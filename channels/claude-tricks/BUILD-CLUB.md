# Build Club — Friday Series Bible (LOCKED 2026-08-13, VJ)

> **Fridays on AI Unpacked belong to Build Club.** A serialized weekly build for people
> who want to make things easy and fast: one real move per chapter, homework for the
> week, next chapter next Friday. Activates the BRAND-BIBLE §5 "Built With Claude" +
> "Steal This Workflow" lanes as one serialized format.
>
> The daily template-locked flow is UNTOUCHED — Build Club replaces the Friday daily
> slot only. Everything else about the channel (host, look, captions, compliance,
> mix engine) is inherited from BRAND-BIBLE.md + PRODUCTION-PLAYBOOK.md.

---

## 0. Who it's for & the voice — NORTH STAR (VJ note 2026-08-13)
> Applies to every Build Club chapter: **title, SEO, VO script, hook, and outro.**
> Read this before writing a word of any chapter.

- **Who we're talking to:** every would-be entrepreneur, anywhere in the world, who
  has an idea or a dream but hasn't been able to *put it into action*. The person
  stuck at "someday" / "I'm not technical" / "I wouldn't know where to start."
- **What each chapter is:** a gentle push off the fence. Not a lecture, not a flex —
  a small, doable session that says *you can start this today.*
- **The feeling every line should carry:** "Starting is genuinely easy now. It's
  never been this cheap or this fast. Start the thing you dream of — and I'm right
  here to help, one little session at a time." Warm, encouraging, on-your-side.
  Never intimidating, never gatekeep-y, never assumes prior skill.
- **How it shows up in the craft:**
  - **SEO/title:** speak to the dreamer's intent ("start your idea today",
    "no coding", "build the thing you keep putting off") — not just the tech noun.
  - **VO tone:** second-person, encouraging, "you can do this", low-friction.
    Remove any word that could make a beginner feel behind.
  - **Hook:** still Vaibhav-DNA (§2), but the *promise* is emotional — the push —
    not just the mechanic.
  - **Outro:** the homework CTA is the push made concrete — "you just started,
    now ship it, I'm checking every link" (§2 homework mechanic).
- This is the emotional layer *on top of* the locked format below — it never
  overrides the STANDALONE-FIRST rule or any QC gate; it sets the words we choose
  inside those rails.

---

## 1. The promise
**"One real build move, every Friday. By Chapter 6 you've shipped a real app."**
Every chapter teaches something a beginner can genuinely replicate in a week with
free tools. Everything shown is the real stack this channel's own factory runs on
(Claude Code → Netlify → Supabase → scheduled automation) — the authenticity moat,
per BRAND-BIBLE §1.

## 2a. 🔒 TEMPLATE v1 — LOCKED (VJ 2026-08-13, after Ch.1 v4 ship)
**This beat-mix style belongs to Build Club ONLY. The daily cadence runs the
existing locked v16.4 template, untouched — none of these components ever
appear in a daily.** Locked means locked against per-episode improvisation;
system-level corrections follow the StatBars precedent (fix once in the
component, every chapter inherits).

The locked chapter flow, exactly as Ch.1 shipped:
1. **Windowed talking hook** — hook art (grid canvas + phone + chips) with an
   alpha window over the FramedHost card: Sol TALKS from frame 0; headline
   baked for the frame-zero thumbnail (`hook.baked + seeThrough + headTop`).
2. **ChapterCard** — blueprint-grid chapter-book opener, bloom + season dots.
3. **Sol thesis beat** — framed host run carrying the chapter's one idea.
4. **Pinned-comment b-roll** — where the prompt lives + COPY affordance.
5. **Real device footage in the PhoneFrame casing** (`rec:...|phone`) — the
   REAL app journey on a drawn high-end Android bezel, captions in the low
   strip; pip mix-engine beats (splitWide/recFull) carry Sol beside the
   payoff moments.
6. **RecipeCard** — ticked steps + homework panel + tease + season dots.
7. **Ch.N+1 tease outro** — next-chapter illustration card + Sol's spoken
   CTA (homework, gift when active, "next Friday we unlock…").
Persistent layer: the PROMPT→FILE→LIVE **BuildRail** across the teaching
window; GlobalHeader carries `BUILD CLUB · CH N/6`; header_scrim on.

## 2. Chapter grammar (the locked format)
- **Length:** 55–75s (vs the daily 25–40s). Pacing rules still apply — 0.4s sentence
  breaks, style 0.4, followable not frantic (playbook §7).
- **STANDALONE-FIRST (the #1 rule).** The Shorts feed serves cold viewers Chapter 4
  who never saw Chapter 1. Every chapter must open with the current state *working on
  screen* + today's one move, and be fully satisfying alone. Series stamp + recap
  ≤ 2 seconds ("Build Club, Chapter 3. This site already answers questions.").
  "Chapter N" is a bonus layer for followers, never a dependency for strangers.
- **ONE move per chapter, 3 steps max.** The proof pane does the teaching; the exact
  copy-paste prompt lives in the pinned comment, not squeezed on screen.
- **Real deploy on screen.** The thing must actually go live / actually run during
  the recording. No mockups of the result — the live URL / fired job IS the payoff.
- **Homework outro (locked mechanic):** via the shipped `outro_cta` engine — Sol
  speaks the homework + cliffhanger over the question card:
  *"Ship yours, drop your LIVE LINK in the comments — I'm checking every one.
  Chapter N+1 next Friday — we ___."* The link IS the CTA (VJ 2026-08-13); the
  word **SHIPPED** rides along in the pinned comment/description so homework
  stays countable. ⚠️ YouTube holds many viewer comments containing URLs for
  review — approving them from Studio comment review is a DAILY human step on
  publish weekends, and the pinned comment warns viewers their link may take a
  while to appear.
- **The shared prompt is the deliverable — and it's REAL.** Each chapter's
  copy-paste prompt is an engineered, sectioned prompt (Ch.1:
  `assets/bc01/SHARE-PROMPT.txt` — SECTION 1 interview · SECTION 2 quality
  rules · SECTION 3 hand-over). The episode explains the sections, tells
  viewers "use as-is or change what you like — it comes back personalized",
  and the on-camera demo runs THAT exact prompt. Never share a prompt the
  demo didn't run, never show a simplified on-screen version that differs
  from the pinned one.
- **Hook grammar:** Vaibhav-DNA stays locked and FIRST (Stop-X / FREE / result-flash).
  The chapter suffix rides at the end of the title, applied at finalize.

## 3. Numbering & plumbing (how it coexists with Day N/30)
- **Ep keys are `bc01`–`bc06`** (non-numeric on purpose) → the daily Day/30 counter
  never sees Fridays. No skip logic, no drift; dailies keep their own sequence on
  the other six days.
- **Spec carries `"series": "build-club"`, `"chapter": N`, `"homework": "…"`.**
  `finalize_episode.py apply_series_suffix()` appends `— Build Club Ch. N` from the
  spec (chapters are content-ordered, so unlike dailies the number is NOT assigned
  at arm time). `build_description()` swaps the daily promise line for the Build
  Club promise + the week's homework.
- **Playlist:** every chapter goes into the **"Build Club — Season 1"** playlist
  — id `PLIuiep7RRSGE` (created 2026-08-13; `yt_upload --playlist PLIuiep7RRSGE`,
  or post-arm via `--video-id <id> --playlist PLIuiep7RRSGE` recovery mode).
- **Slot:** Friday 16:00 IST, same as the daily slot it replaces.

## 4. Season 1 — "Your idea → a live app" (Aug 14 – Sep 18, 2026)
| Ch | Friday | One move | Homework |
|----|--------|----------|----------|
| bc01 | Aug 14 | Idea → live website (Claude one-file page + Netlify Drop) | Ship yours, comment SHIPPED |
| bc02 | Aug 21 | Add one AI feature to the live site | Add one to yours |
| bc03 | Aug 28 | Give it memory (Supabase free tier) | Store one real thing |
| bc04 | Sep 4 | Runs while you sleep (free scheduled job) | Automate one task |
| bc05 | Sep 11 | It talks to you (notification hook) | Wire one alert |
| bc06 | Sep 18 | Launch day — domain, polish, season finale | Post your link |

- Chapters bc02–bc06 get full briefs the week they produce (calendar rows hold the
  skeleton). Each build move must be verified against the CURRENT free tier at
  production time (playbook §1.5 — verify reality).
- **After bc06:** compile all six chapters into ONE long-form video — this fulfils
  the curriculum-shorts→long-form plan already on file for the channel.
- **Season 2 candidate (VJ-approved direction):** the meta build — "I'm building a
  YouTube channel run entirely by AI" — using this channel's own factory as the
  story. Save it until Build Club has an audience.

## 5. KPIs (what "working" means)
- **Homework count:** `yt_engage.py --count-keyword SHIPPED` AND
  `--count-keyword netlify` per chapter — unique_authors union is the real
  number (people who shipped). Live links in comments are the strongest
  proof-of-homework signal a Short can produce.
- **Affiliate (verified 2026-08-13):** Netlify runs a partner/affiliate track —
  ~20% recurring rev-share (12–24 mo) via PartnerStack, manual approval
  ~3–5 days. **VJ human step: apply.** Until approved, all copy stays
  "everything free"; once live, the tracked link joins descriptions + pinned
  comments (with the FTC disclosure line per BRAND-BIBLE §8).
- **Return rate:** chapter N+1 views from subscribers vs chapter N (Analytics 2.0
  deltas) — the serialization signal.
- **Subs/100 views vs the daily baseline** — Build Club's whole thesis is that an
  unfinished build converts viewers into subscribers better than a daily tip.
- Pinned comment on every chapter = the exact copy-paste prompt
  (`yt_engage.py --pin` + the one human Studio click for the actual pin).

## 6. Production checklist (per chapter)
1. Brief finalized + free-tier reality check (day before).
2. Footage: Playwright/VHS of the REAL run — the deploy/job must genuinely happen.
3. Spec: `episodes/bcNN.v2.json` with `series`/`chapter`/`homework` fields.
4. Render via `build_ep_v2.py` (v16.4 engine, all locked QC gates apply — **enumerated in §7,
   because "all locked QC gates apply" is what both Fridays skipped**).
5. **ARM SWITCH (VJ directive 2026-08-13): NEVER arm without VJ's explicit go.**
   Production stops at the master: `finalize_episode.py --ep bcNN --skip-arm`
   (master + QC only). Present frames + the master to VJ; only after a written
   go: `finalize_episode.py --ep bcNN --schedule <iso>` + playlist add.
   (bc01 v1 was armed pre-directive and retired the same day — the rule exists
   because a produced chapter is a proposal, not a release.)
6. Post-publish: pin the prompt comment; Monday `--count-keyword SHIPPED` reading.

---

## 7. 🔒 THE AUDITION GATE — LOCKED (VJ 2026-08-14, after two unauditioned Fridays)

**Why this section exists.** Fridays have shipped outside the measured gate twice running, and
the channel's own ledger says so:

- **2026-08-07** (`xZirrXHzM4Q`, the Friday daily): ledger §4 records it verbatim as
  *"Not instrumented — this build did not run `probe_frames.py`, `lipsync_align.py`, or a LUFS
  check on the master; verification was frame-level visual spot-checks."*
- **2026-08-14** (bc01): LUFS and lipsync **were** measured (−14.20 LUFS PASS, +23 ms corr 0.99),
  but there is **no §2 A–J scorecard row, no ratchet verdict, and no chip-corner measurement** for
  a chapter whose captions sit in a low strip over real phone footage — the exact placement
  `probe_frames.py` exists to decide. And the ledger entry named the **retired** cut
  (`_ebCZEGFu74`) while `bWoa98zMWjA` is what actually went out.

That last one is the real failure mode: **an audition record that doesn't describe the shipped
file is not an audition.** A daily gets caught by the §4 ratchet table; a Friday had nothing
holding it, because Build Club is exempt from the daily ledger by design (different template).

**The gate. All five, written down, BEFORE the arm — no chapter is armed on a spot-check.**

| # | Gate | Command | Pass condition |
|---|---|---|---|
| 1 | **Audio spine** | `finalize_episode.py --ep bcNN --skip-arm` | integrated **−14.0 ±0.5 LUFS** on the delivered `*_outro` file |
| 2 | **Lip-sync** | `python scripts/lipsync_align.py` on every host clip | sharp peak **corr > 0.9**; offset applied, not eyeballed |
| 3 | **Caption/chip placement** | `python scripts/probe_frames.py corner CLIP.mp4 --window <in> <out> --label "<chip text>"` — off the **shipped** cut, over the **exact** beat window | nothing taught sits under the chip or the low caption strip. Score 0.00 is the only fully clean answer; anything above it gets written down as a trade |
| 4 | **Standalone-first** | watch the first 3s of the delivered file | series stamp ≤2s; a viewer who has never seen Ch.1 is not lost at frame 0 |
| 5 | **Homework CTA survives** | watch the last 3s | the outro CTA is readable ≥1.5s and the final frame does not contradict it |

**Then, and only then**, present frames + master to VJ for the written go (§6 step 5).

**The record (this is the part that keeps failing, so it is now mechanical):**
- Every chapter appends a **Build Club audition block** to `QUALITY-LEDGER.md` carrying all five
  gate results **as numbers**, not adjectives — a gate that was skipped is written
  `NOT RUN`, never omitted and never softened to "visually confirmed."
- The block records the video ID **after arming**, and it must be the ID of the file that
  actually shipped. A retired or superseded cut in that field makes the whole block void.
- Ch.N is auditioned against **Ch.N−1**, not against the dailies. Build Club runs its own
  ratchet — same rule as §2 of the ledger (≥ on every gate, strictly better on ≥1), because
  TEMPLATE v1 is not comparable to the daily v16.4 template.
