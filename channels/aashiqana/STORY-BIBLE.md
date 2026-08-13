# Unki Kahani — Story Bible (v1, 2026-08-13)

> The evergreen serialized love story of **Aarav & Meher** (the golden couple,
> `goldenhour_aajave`). Every Short = a chapter; every chapter ends on an open
> question; the question IS the subscribe reason. Companion: SHORTS-TEMPLATE-LOCKED.md
> (how a chapter is built), SERIALIZATION-PROPOSAL.md (why), couple_library/leonardo_ids.json (who).

## 1. The engine (why this never runs out)

A romance serial dies when the tension is consumed (they kiss, the end). Unki Kahani
runs on a **renewable-tension loop**:

**long → close → almost → RUPTURE → long again** (new world, higher stakes each cycle)

Intimacy climbs inside an arc; a story event (jhagda, doori, a secret, a departure)
resets it before it peaks. Nothing is ever fully consumed → evergreen. Each cycle
re-runs in a NEW register and NEW world, so it never feels templated.

## 2. The signature (never break these)

1. **The Red Thread.** Every chapter's frame-one: MEHER + one red element (dress,
   rose, dupatta, bangle, letter, umbrella). It is the series' visual watermark —
   viewers learn to spot it in the feed.
2. **Word-first open** (template rule #1) — the chapter's lyric IS its dialogue.
3. **The whispered question.** Every chapter's last ~3s: a soft female whisper asking
   the NEXT chapter's question over the music tail + end card. Formula in §5.
4. **Sensual tension always rising within an arc, capped YT-safe** — the ladder (§4).
   The camera looks away before the ladder ever tops out; a rupture resets it.

## 3. Emotional registers (rotate — never the same twice in a row)

| Register | Feel | Example beats |
|---|---|---|
| **Aches** (longing) | doori, intezaar | empty evening, two glasses, unread message |
| **Yaadein** (flashback) | nostalgia | how they met, the red-dress evening |
| **Shararat** (fun/laughter) | playful, cute | cooking chaos, rain-dance, teasing |
| **Safar** (adventure) | escape, free | road trip, seaside, mountains, running away |
| **Qurbat** (intimacy) | sensual, close | the almost-kiss, from-behind, slow dance |
| **Jhagda/Raaz** (drama) | fight, secret, doubt | raised voice, a hidden letter, a name he doesn't know |

Rules: (a) after **Qurbat** always comes **Jhagda/Raaz** or **Aches** (the reset);
(b) every 3rd–4th chapter is a drama spike (the cliff that fuels a week of comments);
(c) **Shararat/Safar** chapters keep the series warm — a serial that is only pain
churns out; joy makes the ruptures hurt.

## 4. The intimacy ladder (YT-safe cap — BRAND-BIBLE §2 + template rule #4)

L1 glance/proximity → L2 first touch (hands, rose) → L3 embrace-from-behind /
turn-within-arms → L4 forehead + almost-kiss / sink-to-sit → L5 implication only
(morning chai, her wearing his shirt-collar framing — fully clothed, tasteful).
**L5 is the ceiling, reached rarely; the cut always leaves before the kiss lands.**
Leonardo prompt wording stays tame (template rule #4); the VISUAL carries the heat.

## 5. The whispered-question CTA (the tail-retention device)

Placement: last ~3s, voice at full level with the music **ducked** under it.
Voice: soft female whisper (Lily / the song's own female-echo texture). ≤ 9 words.

Formula: **[tiny story tease] + [open question]? …Friday.**

| After a … chapter | Whisper (Hinglish) |
|---|---|
| Aches | "kya wo aayegi?… Friday ko pata chalega" |
| Yaadein | "yaadein khatam… par wo aaj bhi wahan hai. kya wo aayegi? …Friday" |
| Qurbat | "itne paas aake… ruk kyun gaye? …Friday" |
| Jhagda | "pehli baar aawaz unchi hui… kya ye alag ho jaayenge? …Friday" |
| Raaz | "wo kuch chhupa rahi hai… kya? …Friday" |
| Shararat | "itna haske bhi… ek sawaal reh gaya. …Friday" |
| Safar | "dono bhaag gaye… par kahan? …Friday" |

The **pinned comment repeats the same question in text** and invites answers
("tum kya sochte ho — comment karo") — the question does double duty as the
engagement bait yt_engage measures.

## 6. Season 1 — "Aaja Ve" (the arrival arc)

| Ch | Song bar | Register | Beat | Cliff / whisper |
|---|---|---|---|---|
| **1** ✅ live | Aaja Ve chorus | Aches | he waits, every evening incomplete | *(shipped pre-bible; pin carries the question)* kya wo aayegi? |
| **2** ✅ produced | verse 2 (red dress) | Yaadein | the evening he became hers — then back to the empty present | "yaadein khatam… kya wo aayegi? …Friday" |
| **3** | bridge → final chorus | Suspense→Qurbat | SHE ARRIVES — but stops at the gate, something unsaid in her hand (a letter? red envelope) | "wo aa gayi… par haath mein kya tha? …Friday" |
| **4** | full-song drop (long-form) | Qurbat (L4) | the reunion in full — the letter opened ON SCREEN at the end… it's not what he thinks | arc-2 hook: the letter's contents |

Season 2 — "Jhagda/Raaz" arc (Song #03, R7 slot): the letter's secret detonates;
first fight; doori again — ladder resets, registers rotate through Shararat
(the makeup begins with laughter, not apology). Season 3 — "Safar" (escape
together / Seaside world). Season 4 — festival season (Diwali timing, family
stakes). The fan-text song (calendar 58a7a94b, Aug 20 UGC loop) plugs in as a
**"pages from their diary"** interlude — fan stories become non-canon pages in
the same world.

Non-canon **pages** (mid-week posts): alt cuts, reprises (e.g. the Aug-22 Slow
Reprise), diary moments — same couple, no chapter number, no cliff. They keep
volume without burning story.

## 7. Production notes

- Chapter beats map 1:1 to the template's K1–K4 keyframes; the TURN beat is K3,
  the CLIFF is K4's final held look.
- The whisper is generated with `scripts/eleven_vo.py` (voice Lily
  `pFZP5JQG7iQjIQuC4Bku`, speed ~0.92, Devanagari text for pronunciation) and
  mixed with the music ducked ~-7dB under it (see finalize/polish flow).
- Manifest fields per chapter: `chapter`, `prev_video_id`, `story_beat`
  (feeds the pin), and the whisper line lives with the episode's renders.
- The question must be answerable ONLY by watching the next chapter — never
  answer it in the description, pin replies, or community posts.
