# Long-Form Plan — AI Unpacked

> ## ⛔ RETIRED 2026-08-20 — owner decision
>
> The channel is not going long-form. The two calendar rows for it are parked
> (the 16:9 renderer prototype and the "5 Fixes in 6 Minutes" beginner course),
> and the direction is the standalone "I Built A ___ By Typing One Line" tips
> that the data actually supports. Kept, not deleted: the competitor teardown in
> §2 and the repurpose-native format spec are the useful part, and long-form is
> a decision that gets revisited rather than one that is wrong forever.
>
> Nothing below is being worked on.

> **Status: PLAN (2026-08-16).** Format spec + build order for the channel's move into
> long-form (15–20 min), designed **repurpose-native**: one production pass yields ONE
> long-form **and** N standalone Shorts that funnel back to it.
> Competitor teardown that seeded this: **Vaibhav Sisinty** (807k) — see §2.
>
> **LOCKED (VJ directive 2026-08-16):**
> - **First topic = evergreen "AI Beginner's Playbook"** (§4 recommendation approved).
> - **Cadence = FRIDAYS.** Friday freed up after the Build Club S1 finale moved to Thu (bcs1f,
>   2026-08-20); the first long-form drops the first Friday *after* Gap 1 (§6) lands — not date-pinned
>   to a build that isn't done. Friday also suits long-form's weekend-watch behaviour (longer sessions),
>   even though Friday was a weak *Shorts* day — different audience behaviour, different format.
> - **Slot = 10:30 IST (05:00 UTC).** Grounded on Vaibhav's one confirmed recent long-form drop
>   (2026-08-14 22:05 PDT = **10:35 IST**; his account schedules on US-Pacific) + long-form platform
>   logic: publish in the India morning so watch-time accumulates through India evening prime (20:00–23:00
>   IST) the *same day* — the early-signal window long-form ranking needs and Shorts don't.
>   **Deliberately earlier than our 16:00 IST Shorts slot** (long-form needs the marinate window; a Short
>   is decided in the feed in minutes). The 3–4 derived Shorts still go out at the proven 16:00 IST.

---

## 1. Why long-form, and the one problem it must solve

The 12-day Shorts read ([docs/stats/AI-UNPACKED-READ-2026-08-14.md](../../docs/stats/AI-UNPACKED-READ-2026-08-14.md))
is unambiguous about our situation:

- **The channel is 100% Shorts-feed dependent.** 7d traffic: SHORTS 326 · YT_SEARCH 60 · rest noise.
- **1460 channel views → 5 subs.** The feed gives us *views*, not *subscribers*.
- **Every Short is decided in 24–48h and has no tail.** No video has ever climbed out of single
  digits later.

Long-form's traffic is the inverse: almost no browse impressions on a 5-sub channel, but it lives
on **search + suggested** — the one lane that *compounds* and the one we already have a trickle of
(YT_SEARCH 60/7d). Brand-bible RPM math: **$8–25 long-form vs $0.03–0.15 Shorts** ([BRAND-BIBLE.md](BRAND-BIBLE.md)).

**The problem long-form must solve on THIS channel: distribution.** A long-form uploaded cold to 5
subs gets ~no impressions. So the plan is not "make long-form instead of Shorts" — it is:

> **Shorts are the distribution engine; the long-form is the destination.** Every long-form is
> cut so that each of its segments *also* ships as a standalone Short with a CTA tail pointing back
> to the full video. The Shorts (which DO get sampled, ~130 views each) drive search/suggested and
> subscribes to the long-form. This is the ONLY structure that fits our measured traffic reality.

This is the brand bible's own doctrine — *"each short is a standalone AND a chapter of a long-form
compilation"* ([Playbook §13](../../docs/PRODUCTION-PLAYBOOK.md)) — turned into the primary
production model instead of an afterthought.

---

## 2. Competitor teardown — Vaibhav Sisinty (the structure we're matching)

Same niche, same three model names in every title, already our Shorts baseline
([memory: vaibhav-sisinty-competitor-baseline]).

| Recent long-form | Length | Views | Age | Lane |
|---|---|---|---|---|
| **China Dropped an AI 100x Cheaper (+14 AI Updates)** | 21:47 | **303k** | 6d | **news roundup** |
| Make Claude Work FREE in 17 Mins | 17:01 | 118k | 11d | tips |
| Make Money with Claude/ChatGPT/Gemini | 14:54 | 39k | 1d | money listicle |

**Finding that reframes our whole strategy:** his **news roundup is his top performer (303k)** —
8× the money listicle. Our news lane is the *worst* Shorts lane (median **14** vs tips **134**,
controlled same-day). These are not contradictory: a news *Short* is one fact fighting entertainment
in a feed; a weekly news *roundup* is a **destination people search for and subscribe to**.
**News is a bad Shorts lane and the best long-form lane in this exact niche** — and news is already
45% of our locked mix. (This directly contradicts the standing "cut the news lane" line in the
12-day read; that instruction was about *Shorts*. Flagged into the Playbook.)

**His structure (the money video, 894s, decoded) — this is the reusable skeleton:**

| Beat | Time | Function |
|---|---|---|
| Cold-open pain | 0:00–1:05 | No intro sting. "Your subscriptions have only cost you money." |
| Funnel read | 1:05–1:40 | His own free masterclass (35s) |
| Items 1–5 | 1:40–8:08 | ~65s each, no-code tier |
| **Mid-roll stakes interrupt** | **8:08–8:34** | "Why companies are cutting jobs" — dropped at the halfway mark to reset attention |
| Items 6–10 | 8:34–13:00 | ~65s each, company-scale tier |
| **Payoff gate** | 13:41 | "The master prompt that picks your idea + builds your 30-day plan" |
| Close | 14:01 | "The skill that actually matters" |

**The item template — stated once, held for all 10** (this is a schema, not a script):
*what you actually do · which tools · who pays · cost vs. what you charge.*

**His honesty clause is our doctrine verbatim:** *"Where a price is a market estimate, I say so."*
He plays the same anti-slop card the channel was built on. We match the structure; we do **not**
copy the money topic — that video sells a masterclass to 807k subs. We have 5 subs and no product;
the same video from us is a promise we can't cash (VJ directive 2026-08-16: **his structure, not his topic**).

---

## 3. The repurpose-native format — "one shoot, many cuts"

The core machine. Every long-form is assembled from **SEGMENTS**, and each segment is authored as a
**self-contained Short from the start**. One research pass + one VO session + one recording session →
one long-form + N Shorts.

```
                 ┌─ segment_01 (hook + ~50s proof + micro-CTA)  ← already a Short
   ONE           ├─ segment_02  ...                             ← already a Short
   RESEARCH  ──► ├─ ...                                          ← already a Short
   + VO + REC    └─ segment_N                                   ← already a Short
                        │
          ┌─────────────┴──────────────┐
          ▼                             ▼
   LONG-FORM (16:9)              N × SHORT (9:16, per segment)
   wrapper:                      recut:
   cold-open hook                 + channel hook card (0–2s)
   + channel/season promise       + the segment body
   + [seg1 … segN joined,         + CTA tail: "full breakdown —
      chapter markers,              9 more in the pinned video"
      transitions]                     ↓ funnels to the long-form
   + mid-roll stakes interrupt
   + payoff (master prompt / free pack)
   + outro
```

**Segment schema** (superset of the existing episode JSON — same shape our `build_ep_v2.py`
already speaks, just tagged for dual output):

```jsonc
{
  "id": "seg_03",
  "rank": 3,                       // position in the long-form
  "hook": "…",                     // 0–2s, MUST work standalone (Short frame-1 promise)
  "body": [ /* beats: host cutaway, screen-proof, mock, card — existing beat grammar */ ],
  "micro_cta": "…",                // one line, closes the segment inside the long-form
  "short": {                       // Short-only overrides
    "cover": "…",                  // 9:16 hook card
    "cta_tail": "9 more in the full breakdown — link in comments",
    "target_s": 30
  },
  "sources": [ /* attribution for any real figures (Playbook Ep28 footer rule) */ ]
}
```

**Two hard rules that make the machine honest:**

1. **The 0–15s sustain law still governs — per segment.** Our measured retention finding
   (Ep1 48% vs Ep2 71% is *entirely* the 15s sustain, not the 3s hook —
   [docs/stats/RETENTION.md]) applies to every segment's Short AND to the long-form's cold-open.
   Front-load a face/payoff; no dense dark techy beat inside the first 15s. Long-form adds a
   **per-chapter** analogue (see §6, gap 5).

2. **A segment must survive being cut BOTH ways.** If it only reads with the long-form's context
   around it, it is not a segment — it is a paragraph, and it will flop as a Short. Author the hook
   and micro-CTA to stand alone first; the long-form wrapper is what adds continuity, never the
   other way round.

---

## 4. Topic pick (trends × channel × de-risk)

VJ delegated topic choice. Two long-form franchises, and a specific de-risked **first** episode.

### First long-form — the "MAKE CLAUDE DO X FOR FREE" concept (VJ pick 2026-08-16)

**Modeled on Vaibhav's *"I Figured Out A Way To Make Claude Work For FREE In 17 Mins"* (118k).** The
"FREE / stop paying" hook is his proven differentiator, and it is the reason this is NOT the generic
"10 moves" beginner playbook (VJ rejected that): a single sharp money-saving thesis, not a listicle.

**The X (working thesis): "Claude Code Is FREE — and It Replaces $100/mo of AI Tools."** Show Claude
on its free tier doing, on real screens, exactly what people pay for elsewhere — one free tool
replacing a paid stack. Each replaced paid tool is one self-contained proof segment.

Why this fits:
- **Vaibhav-proven concept**, Claude-native, beginner, anti-hype — all on-brand.
- **The FREE hook = the differentiator** the generic playbook lacked.
- **Proof moat**: `record_demo.py` already drives Claude/ChatGPT/Gemini — every "paid tool → done
  free on camera" claim is a real tape, not an assertion.
- **Repurpose-native despite being one thesis**: each replaced-tool beat is a standalone Short
  ("Cancel ChatGPT Plus — Claude does this free", "Delete Copilot — Claude Code builds it free",
  etc.), each with a CTA tail to the full video.

Candidate segments (each = a proof beat = a Short): ChatGPT Plus (writing/analysis) → Claude free ·
a coding tool (Copilot/Cursor) → Claude Code free allocation · a PDF/doc tool → Claude reads files
free · a research/automation tool (Zapier-ish) → Claude skills/commands free · payoff: the one free
setup that runs the lot + "here's what to cancel".

Title register (measured on our own channel): **"Stop…" imperatives flopped (4–7 views); second-
person / curiosity / proof-first titles got sampled (129–223).** So lean: *"I Cancelled My AI
Subscriptions — Claude Does It All Free (2026)"* / *"Claude Is Free and Replaces $100/mo of AI Tools"*,
never *"Stop Paying For AI…"*.

⚠️ **Freshness/accuracy gate (production-time):** every "free" claim is a claim about the world on
publish day — free-tier limits and allocations change. Verify each tier live at record time
(`record_demo.py --preflight`) and voice limits honestly ("on the free tier, as of <month>"), per
the playbook's verify-reality-at-production rule. The honesty clause IS the brand (§2 BRAND-BIBLE).

### The ongoing franchise — "AI Unpacked Weekly" (NEWS ROUNDUP, the Vaibhav 303k model)

Once the pipeline is proven, this is the recurring play: the week's AI news decoded for beginners,
fed by `scripts/news_radar.py` (already running daily), repurpose-native (N stories → N Shorts + 1
long-form from ONE research pass), and a genuine **subscribe reason** — a weekly destination, which
is exactly what a browse-dead channel lacks. On-trend seed stories live now in
[NEWS-RADAR.md](NEWS-RADAR.md): models-going-rogue in safety tests, the price war (DeepSeek $0.14 /
GPT-5.6 −80% / Opus 5 lead), the Perplexity shopping-agent court ruling, EU AI Act Art.50 in force.

**Recommended cadence: alternate.** Evergreen playbook (search tail) one week, news roundup (fresh
subscribe-driver) the next — both run on the same §3 machine, so we get the compounding asset AND
the recurring hook without doubling the pipeline.

> **The one open fork for VJ:** ship the **evergreen playbook first** (recommended — de-risks the
> build on proven assets), or open straight with a **news roundup** (more on-trend, but new material
> + new pipeline failing together). Everything else in this plan is the same either way.

---

## 5. What we already have vs. what must be built

**Transfers unchanged:** ElevenLabs VO + word timestamps · the 4-slot item template (our episode
JSON is this shape) · the four compliance mock generators (chat/doc/report/label — our legal
substitute for the vendor-pricing-page screenshots Vaibhav uses freely) · −14 LUFS master + ducked
bed · `assemble_compilation.py` (xfade/loudness-match/bookends chain, **already validated at 60-min
scale** on the Lulla build) · `record_demo.py` proof gates (`--seed-terms`, `--fail-terms`,
`--followup`, `--preflight` — our proof moat, survives the pivot) · `news_radar.py` · chapters +
keyword description (**free for us** — we have per-beat timings; Vaibhav hand-writes his).

## 6. Build order — the five gaps (honest scope)

| # | Gap | Why it's needed | Effort |
|---|---|---|---|
| **1** | **16:9 render path** — ✅ **assemble half DONE (2026-08-16)** | `scripts/assemble_longform.py` built on the proven `assemble_compilation.py` spine: **forces 1920×1080** (never inherits input dims), emits a YouTube-format `<out>.chapters.txt` from the exact join offsets, speaks the long-form beat spec (cold-open/segments/mid-roll/payoff/outro as ordered segments). Validated at full scale on synthetic mixed 9:16/16:9/720p sources (`--selftest`): output 1920×1080, predicted==actual duration, chapters correct, vertical inputs pillarboxed cleanly (edges black, content centered — verified per-pixel). **Still owed:** (a) a **blur-fill conform** — raw black pillarbox bars around a re-used 9:16 Short are not shippable quality; either author segments 16:9-native (right long-term path) or add a blurred-background fill option like `style_blurbg.py` does for Shorts; (b) the Remotion 16:9 composition set for animated cards (cold-open/lower-thirds) — not blocking the first assembly, which can use existing PIL/ffmpeg card generators at 1920×1080. | ~~Large~~ **spine done; blur-fill + cards remain** |
| **2** | **Desktop screen recording** | `record_demo.py` films a 540×960 mobile viewport; long-form proof reads better at 1920×1080 desktop. Add a `--desktop` viewport mode; all gate flags carry over. | Medium |
| **3** | **Host economics** | Sol at ~$0.025/sec = ~$22 if on-camera throughout a 15-min video. Vaibhav's own structure only needs the host for cold-open + segment intros + payoff (~4–5 min). Budget host to those beats; screen-proof + mocks carry the rest. **~$7/episode.** | Config, not build |
| **4** | **16:9 thumbnail generator** | `make_thumb_unpacked.py` is vertical. Add a 1280×720 variant (same design system). | Small |
| **5** | **Long-form retention rules** | `yt_retention.py` works; our locked "15s sustain" law is a Shorts law. Add the per-chapter analogue: read `audienceWatchRatio` at each chapter boundary, flag any chapter with a >X pp drop at its intro. | Small (analysis) |

**Segment fill — DECIDED (VJ 2026-08-16): 16:9-NATIVE.** Each tip's beats are rebuilt at true
1920×1080 (host + screen-proof laid out for landscape), NOT the reused-9:16-short blur-fill. Best
quality, reads as real long-form. Consequence: **blur-fill is dropped from the path**, and the now-
critical build is a **16:9 segment renderer** — the landscape equivalent of `build_ep_v2.py` (host
compositing, screen/proof layout, captions sized for 16:9). The tip *content* is still pre-validated
(topics/scripts proven as Shorts); only the render is new, so it de-risks the topic, not the layout.

**Updated build sequence:** Gap 1 assemble-spine ✅ → **16:9 segment renderer (new critical path) —
🟡 prototype v2 on disk** → lock the grammar → render the playbook's ~10 tips at 1920×1080 →
`assemble_longform.py` binds them + emits chapters → Gap 2/4 in parallel → validate retention (Gap 5)
after ~48h → then the news-roundup franchise.

**16:9 segment renderer — `channels/claude-tricks/build_longform_segment.py` (VERSIONED, prototype).**
Separate script from the Shorts builder (VJ 2026-08-16), `VERSION` bumped every iteration until the
template locks. Two-beat landscape grammar: `host_full` (Sol fills frame + lower-third title, the
setup) → `screen_pip` (screen-proof fills frame + Sol bottom-right magenta-ring PiP, the demo).
Reuses the Shorts' proven PNG karaoke caption system (no libass in this ffmpeg build). v1 proved the
grammar; **v2 fixed** the caption/lower-third collision + moved captions to the low long-form band
off the host's face. Renders zero-spend on a held Sol still + a drawn placeholder screen; the real
version drops a landscape HeyGen "Sol" clip into the host slot (~$7/ep budget) and a real screen
recording (Gap 2) into the screen slot. **Not yet locked** — pending VJ sign-off on the look.

## 7. Cost per episode (target)

| Line | Cost |
|---|---|
| Host (Sol, ~4–5 min on-camera via HeyGen) | ~$7 |
| ElevenLabs VO (full script) | ~$1–2 |
| Screen recordings / mocks / stock | ~$0 (existing free tooling) |
| **Total** | **~$8–9/episode** (well under the $22 all-host worst case) |

Shorts derived from the same pass: **$0 marginal** (re-cut of segments already produced).

## 8. First-episode concrete spec (VJ pick 2026-08-16: "Make Claude do X for FREE")

- **Concept:** modeled on Vaibhav's "Make Claude Work For FREE" (118k). Single money-saving thesis.
- **Working title:** *I Cancelled My AI Subscriptions — Claude Does It All Free (2026)* (title-test
  against *Claude Is Free and Replaces $100/mo of AI Tools*).
- **Segments (each = a real on-camera proof tape = one repurposable Short):** ChatGPT Plus →
  Claude free · a coding tool → Claude Code free · a PDF/doc tool → Claude reads files free · an
  automation tool → Claude skills/commands free. Ranked; each rendered 16:9 + kept as its 9:16 Short.
- **Wrapper:** cold-open ("You're paying ~$X/mo for AI — I stopped, and Claude does all of it free")
  → channel promise (30s) → segments 1–2 → mid-roll stakes interrupt (~30s, one on-trend news beat)
  → segments 3–4 → payoff (the one free setup that runs the lot + "here's what to cancel", → the
  free setup checklist as a newsletter lead magnet, BRAND-BIBLE §9) → outro.
- **Freshness gate:** `record_demo.py --preflight` on every vendor before the tape; voice each free
  limit honestly ("free tier, as of <month>"). No claim ships unverified (§4 gate).
- **Description:** auto-built chapters from segment timings (`assemble_longform.py`) + tool list +
  keyword tags.
- **Repurpose output:** 4–5 Shorts, each a "cancel this paid tool — Claude does it free" proof with
  a CTA tail to the pinned long-form.

---

## 9. Decisions
1. ~~§4 fork~~ — **RESOLVED: evergreen playbook first** (VJ 2026-08-16).
2. ~~Cadence~~ — **RESOLVED: Fridays, 10:30 IST** (VJ 2026-08-16). Alternate evergreen/news week-to-week
   on that Friday slot once the news franchise starts (§4).
3. **Green-light Gap 1** (the 16:9 render path) — the one large build everything else waits on. ← still owed.
