# Calm AI — Brand Bible
_Created 2026-08-12 from the channel-wizard brief. Locked rules live here; the build recipe lives in `PRODUCTION-BLUEPRINT.md`. Status: **incubating** — nothing is battle-tested until Ep01 ships._

## 1. The one-line thesis
**AI news, minus the panic.** Every Short takes one real, dated thing that happened in AI this week and answers the only question a busy adult actually has: *do I need to do anything about this?* Usually the honest answer is "no, and here's why" — and saying that out loud is the brand.

- **Vision:** make a fast-moving, intimidating topic feel calm and understandable.
- **Purpose:** build authority in the niche (authority first, monetisation later).
- **Audience:** general adults, beginner-friendly — written for a busy parent who has 40 seconds, no jargon tolerance, and a low-grade dread about AI.
- **Quality bar:** premium. Host-less cinematic.

## 2. The wedge (and the honest risk)
The AI-explainer Shorts lane is crowded, and **this channel is the third AI channel in our own network**. It only earns its slot if the difference is loud:

| | AI Unpacked (`claude-tricks`) | Already Happening (`already-happening`) | **Calm AI (`calm-ai`)** |
|---|---|---|---|
| Job | teach a tool trick | provoke about the near future | **lower the reader's heart rate** |
| Host | synthetic host "Sol" | none | **none** |
| Energy | punchy, fast cuts | cinematic, ominous | **slow, warm, unhurried** |
| Accent | magenta `#E0218A` | teal `#22D3EE` | **indigo `#6366F1`** |
| Bed | `bed_active` | `bed_3` | **`bed_4`** |
| Days | daily | Tue/Wed/Thu | **Mon/Wed/Fri** |
| Ending | "try it today" | binary provocation | **"you can ignore this" / one small action** |

⚠️ **If an episode could be re-badged as AI Unpacked without anyone noticing, it is the wrong episode.** The tell: are we teaching a tool (wrong channel) or de-escalating a headline (right channel)?

## 3. Locked format
- **Shorts only. 9:16, 1080×1920, 30fps, −14 LUFS.** Target **25–40s**, ideal 32s.
- **Spine (5 beats):**
  1. **Cold-open reassurance** (0–3s) — name the fear in the viewer's own words, then defuse it. e.g. "No, AI is not reading your kid's homework. Here's what actually happened."
  2. **What happened** — one dated, sourced fact.
  3. **Why the panic version is wrong** — the specific overstatement, corrected. Conservative numbers only.
  4. **What it means for you** — concretely, in the viewer's week.
  5. **One calm action** — a single thing to do, or explicit permission to do nothing.
- **Narration:** licensed AI VO (ElevenLabs), warm and slow, no hype cadence. Music bed under, never over.
- **Captions:** always on, short lines, indigo keyword highlight, placed in dead space — **never over the subject**.
- **Signature brand frame (identical every ep):** slow-fade indigo cold-open card, `◦ CALM AI` bug top-left on body beats only, keyword captions, closing "calm card" with the one action.

## 4. Voice rules
- **Never** open with "BREAKING", "INSANE", "you won't believe", or a countdown timer.
- **Never** manufacture urgency the story doesn't have. If the honest read is "this changes nothing for you", that IS the episode.
- Second person, present tense, short sentences. One idea per sentence.
- No jargon without an immediate plain-English gloss in the same breath.
- No prescriptive parenting advice, no medical/legal/financial advice. We explain; we don't instruct.
- Close on the verbal tag **"That's it. You're caught up."**

## 5. Fact-check gate (MANDATORY)
Same discipline as `already-happening` — the whole brand is "you can trust this one":
- Every on-screen claim, number and date needs a **dated primary source** logged in `episodes/epN.receipts.md`.
- **Understate.** If a source says "up to 40%", we say "roughly a third".
- If a fact cannot be sourced by production time, **the episode changes topic** — it does not ship hedged.
- Never imply a company said something it didn't. Quote or paraphrase conservatively, with the date on screen.

## 6. Anti-throttle discipline (July-2025 inauthentic-content rule)
We are exactly the profile that rule targets: faceless, AI-assisted, templated. Mitigation is non-negotiable:
- The brand frame stays constant; **everything inside it varies every episode** — topic, all visuals, shot types, beat rhythm, caption keyword set, opening line structure.
- ≥6 fresh generated shots per episode; **no reusing a prior episode's motion clips.**
- Real editorial judgement per episode (which panic to defuse, what to leave out) — that judgement is the human contribution and should be visible in the script.

## 7. Compliance
- **Not made for kids** (`made_for_kids: false`) — the audience is parents, not children. Never label as MFK, never cross-link to the kids cluster (Lulla / Poly / Rumble Trucks).
- **AI-content disclosure ON** for every upload (`--synthetic`): footage and voice are AI-generated.
- Topics touching children and AI are in-scope as *news*, but the address is always to the adult.

## 8. Open decisions (resolve at Ep01, then lock here)
1. **ElevenLabs voice** — needs an audition; must be warm/low/unhurried and NOT Brian (that's `already-happening`'s) nor Hrithik (AI Unpacked's).
2. **Motion model** — inherit the `already-happening` finding (Wan 2.6, 9:16, 5s, ~175 tokens) unless a calmer look wants otherwise.
3. **Handle** — see `CHANNEL-SETUP.md`; must be locked across platforms before Ep01 publishes.
4. **Loop vs CTA ending** — pick one per episode, never both.
