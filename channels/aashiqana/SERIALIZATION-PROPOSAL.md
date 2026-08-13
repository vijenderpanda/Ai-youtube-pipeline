# Aashiqana — Couple-Story Serialization (PROPOSAL, 2026-08-13)

> STATUS: **PARTIALLY DECIDED.** SHORTS-TEMPLATE-LOCKED.md is locked;
> per worker-permissions, every change below ships only after VJ approves it.
> Decision checklist for VJ is at the bottom (§7).
>
> **DECIDED 2026-08-13 (VJ):** D1 was first Midnight, then **REVISED same day: the
> Aaja Ve golden-bedroom couple (`goldenhour_aajave`) is THE serial couple** — VJ:
> "i like this version couple, sensual tension more than the aadhi raat couple."
> **Ch.1 = youtu.be/RUm7xNDaAGQ** (publishes 2026-08-13 13:00 IST — retrofit BEFORE
> publish so it premieres labeled). Aadhi Raat stays a standalone, never numbered.
> Gen-ID capture for the couple = the one TODO before Ch.2 (leonardo_ids.json).
> Catalog hygiene applied same day: `TRmiRnKEKJc` + `n99gzIbFrpc` → **unlisted**
> (cleanup_log.json).

## 1. Why serialize

The channel converts **191 views → 4 likes → 0 subs**. A music channel earns a sub only
when the viewer expects to *miss something* by not following. Individual songs — even
premium ones — don't create that. A **story** does: one recurring couple, each song a
chapter, an open loop at the end of every Short. Music-romance serials are the proven
retention machine of this exact audience (episodic love-story Shorts routinely out-convert
one-off songs). The library already anticipates this: COUPLE-LIBRARY §5.5 — "if two songs
reuse the same couple … it becomes *their story continues* (BRAND-BIBLE §4)".

## 2. THE couple (decision 1)

The serialization needs ONE face pair, forever. Three options:

| | Option | For | Against |
|---|---|---|---|
| **A ★** | **Midnight couple, start-frame `7a43cb0a-43ab-4ee5-b737-0394c0939a0f`** (`couple_library/leonardo_ids.json`) | Only couple with a **VJ-approved on-screen identity** + durable Leonardo start-frame ID (identity is *recoverable*, unlike fresh anchors); 3 motion clips already banked (Almost / Look / Touch); BRAND-BIBLE §4 already calls Midnight "the channel's differentiated bet"; **already the face of Aadhi Raat (youtu.be/nXhtuR-dHqU)** — the live catalog seeds Chapter 1 for free | Midnight = neon/desire register; monsoon-sad songs need re-grading into their world |
| B | Monsoon `couple_01` (locked 2026-08-06, stills + 3 motion clips) | Rain/heartbreak = channel's core palette; heroine-hook stills VJ-cast | Disk stills can't re-enter Leonardo (upload sandbox-blocked) → no reliable path to NEW on-model shots; weaker Gen-Z register |
| C | Cast a fresh "THE couple" anchor (NB2, 4 candidates, VJ picks) | Clean start, faces chosen *for* the serial | Burns the Aadhi Raat head start; one more casting cycle before the next chapter |

**Recommendation: A.** It's the only option where identity is already proven on-screen,
technically durable (drive the start-frame by ID, per the IDENTITY-LOCK rule), and already
published. Caveat to accept: **Aaja Ve (RUm7xNDaAGQ, armed) and Nasha (8q5nDxvI4Bg,
scheduled Aug 14) use different couples** — see §6 for how they fit.

### Naming the couple (decision 1b)
Named leads make titles/pins/comments sticky ("Kabir waited. Naina didn't." >> "the couple").
Options — VJ picks or renames:
- **Aarav & Meher** ★ (modern, no film baggage, scans in both scripts)
- Veer & Aashi ("Aashi" echoes *Aashiqana* — nice brand rhyme, slightly cute)
- Kabir & Naina (maximum Bollywood resonance, but borrows Kabir Singh / YJHD energy — derivative risk)

## 3. Chapter grammar (decision 2)

**Story name:** "**Unki Kahani**" (their story) — used in playlist, pins, end card.

Per-Short framing, layered so no single surface carries the whole load:

1. **Title** — keep the locked lyric-hook grammar, add a compact chapter chip at the END:
   `Woh insaan jise tum chhod hi nahi paate 🥺 | Aadhi Raat | Unki Kahani Ch.1 #shorts`
   - Alternative (title-purist): NO chapter in title; chapter lives only in
     description/pin/end-card. Safer for search ("New Hindi Love Song" keeps its slot) but
     the browse-feed viewer never sees the serial. **Recommend the chip** — serialization IS
     the differentiator; "New Hindi Love Song" can move to the tags/description.
2. **Description, first two lines** (above the fold):
   `Chapter N of Unki Kahani — Aarav & Meher's story.`
   `Missed Chapter N-1? → <link> · Next chapter Friday. Follow @aashiqana.diaries`
3. **Playlist** — `Unki Kahani — The Story So Far` (chapters in order). Wiring already
   exists: `yt_upload.py --playlist <id>`.
4. **Pinned comment** (the ask, in Hinglish):
   `Chapter N: <one-line story beat>. Agla chapter Friday — miss mat karna 🥀 Follow karo.`
   Post via `yt_engage.py --pin` (prereq: one-time `--auth` re-consent for force-ssl scope —
   playbook §9b — do it before the next publish day).
5. **End-card CTA (text, not spoken)** — replace the static tagline
   `a new love song every week` (polish_short.py:187) with:
   `follow their story — agla chapter Friday`.
   **Spoken CTA: recommend NO.** The Shorts are the song — a voice-over stinger would break
   "USE THIS SOUND" reuse and the music-first brand. Text end-card + pin carries it.
6. **Story beat in the POV hook** — the existing `--pov1/--pov2` lines become *serial*
   copy where it fits: "Ch.3 — woh laut aaya" instead of generic POV. No pipeline change,
   just prompt discipline at produce time.

## 4. Chapter day + cadence (decision 3)

End card says "every week"; the calendar is currently arming near-daily (Aug 12/13/14).
Pick one:
- **A ★ Friday = chapter day.** Canonical story beats ship Fridays ("next chapter Friday"
  is literally true). Mid-week Shorts become "**diary pages**" — same couple, non-canonical
  moments (B-side bars, alt cuts), titled `… | Unki Kahani — page` without a chapter number.
  Keeps volume AND makes Friday appointment viewing.
- B: Every Short is a numbered chapter, CTA says "new chapter every week" loosely. Simpler,
  but daily numbered chapters burn story faster than songs can be written, and a missed day
  breaks a visible promise.

## 5. Template/script wiring (the exact changes, all gated on VJ)

**None of this is applied. Diffs staged only after §7 sign-off.**

1. **Manifest** (`channels/aashiqana/episodes/ep<N>.json`) gains:
   `"chapter": N, "couple_id": "midnight-7a43cb0a", "prev_video_id": "…", "story_beat": "one-liner"`.
2. **`scripts/finalize_aashiqana.py`:**
   - if `chapter` present: append title chip ` | Unki Kahani Ch.N` (guard the 100-char cap);
     prepend the §3.2 block to the description; pass `--playlist <UNKI_KAHANI_ID>` to
     yt_upload; after arm, print the ready-to-run `yt_engage.py --pin` command with the
     §3.4 copy (pin itself stays the 1-click human step — API can't pin).
   - chapter number source: manifest first, fallback `factory_settings['aashiqana_last_ep']+1`
     (the counter finalize already advances).
3. **`channels/aashiqana/songs/03-aadhi-raat/polish_short.py`:** new `--cta "<line>"` arg,
   default = current tagline (zero behavior change until finalize passes the serial line).
4. **`SHORTS-TEMPLATE-LOCKED.md` → v2:** step 1 (Anchor) changes from *"reuse a locked
   couple or generate a FRESH anchor"* to *"THE serial couple via start-frame ID /
   Image-Ref from Your Generations (leonardo_ids.json); fresh anchors only for
   non-canon one-offs"*. This is the biggest lock change — it trades per-song casting
   freedom for the serial's identity spine.
5. **`leonardo_ids.json`:** becomes the single registry for the serial couple's every
   approved keyframe/motion gen_id (it already half-is).

## 6. Retro-fit of the live catalog (REVISED 2026-08-13 — golden couple)

- **Aaja Ve `RUm7xNDaAGQ` (golden-bedroom couple) → Chapter 1** by title chip + description
  block + playlist add + pin. Retrofit lands while still scheduled → premieres pre-labeled.
- **Aadhi Raat `nXhtuR-dHqU` (Midnight) + Nasha `8q5nDxvI4Bg` (other face):** leave OUT of
  the numbered story — standalone songs. Do not fake continuity across faces; VJ caught
  exactly this class of mix-up before (IDENTITY-LOCK memory).
- Chapter 2 = the **next produced Short** with the golden couple, answering Aaja Ve's beat
  ("jiske bina har shaam adhoori" → she comes / the evening that finally wasn't empty).
  Prereq: capture the couple's gen IDs from Your Generations into leonardo_ids.json.

## 7. VJ decision checklist

All decided 2026-08-13 — VJ: "go with all the starred defaults."

- [x] **D1 — couple:** ✅ REVISED: **golden-bedroom Aaja Ve couple** (`goldenhour_aajave`;
      gen IDs pending capture from Your Generations ~Aug 12). Midnight demoted to standalone.
- [x] **D1b — names:** ✅ **Aarav & Meher**.
- [x] **D2 — title chip:** ✅ chapter in title (` | Unki Kahani Ch.N`, 100-char guard).
- [x] **D3 — chapter day:** ✅ Friday-canon + weekday "diary pages" (pages get NO number —
      finalize only decorates when the manifest carries `chapter`).
- [x] **D4 — wiring:** ✅ STAGED on branch `claude/vigilant-goldstine-f8eaaa`:
      `finalize_aashiqana.py` (chip + desc block + playlist + pin cmd), `polish_short.py --cta`,
      `channel.json serial` block, `SHORTS-TEMPLATE-LOCKED.md` v2, `leonardo_ids.json` serial flag,
      new `scripts/yt_serialize.py`.
- [x] **D5 — retro-fit** Ch.1: ✅ REVISED to **Aaja Ve `RUm7xNDaAGQ`** — executes via
      `yt_serialize.py --retrofit RUm7xNDaAGQ 1` (run pending, see §8; ideally before
      13:00 IST publish). Aadhi Raat is NOT retrofitted.
- [x] **D6 — prereqs:** ✅ approved — playlist via `yt_serialize.py --init-playlist`;
      force-ssl re-consent via `yt_engage.py --channel aashiqana --auth` (browser click = VJ).

## 8. Execution status (2026-08-13)

Staged code = done. Channel-mutating runs (playlist create, Ch.1 retrofit, pin) are
**pending a human-triggered run** — the Claude session's permission layer declined to fire
them autonomously, so VJ runs the three commands in the session (Run buttons provided in chat).

## Appendix — catalog hygiene (feeds the serialization)

Live scan 2026-08-13 (yt_cleanup dry run, read-only): 11 uploads.
The two 🗑️ DELETE marks (`4EgwUVBN7Ng`, `_HNZAhV2a_c`) are **already private**
(cleanup_log.json, 2026-08-06) — invisible to search/channel page. Hard-delete stays a
manual Studio action (playbook §9: never hard-delete via automation); they cluster under
🗑️ in Studio for a 2-click bulk delete whenever convenient.

Unlist candidates (recommend, not applied — split Tu Hi Hai's search traffic 4 ways):
- `TRmiRnKEKJc` — Tu Hi Hai **long-form**, 3 views. §3b release strategy says withhold the
  full track in Phase 1; unlisting it also restores the "full song dropping soon" tease.
- `n99gzIbFrpc` — Devanagari-title lyric-duel Short, 8 views. Third Short on the same song;
  keep the A/B pair (`1yWfA_Tg61Y` 38v, `aT5c5fJ38WM` 17v) and fold this one.

Keep untouched: `ZQQvRrGWGLk` (103v — channel's best), `TMVJHHv7v4c` (66v).
