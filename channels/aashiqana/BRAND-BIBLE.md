# Aashiqana — Brand Bible

> Premium AI Hindi **romantic-song** channel. Original Kumar Sanu–era melodies (Suno Pro)
> over cinematic AI mini-films starring an original AI couple per song.
> Pipeline A (music video), adult/general audience (NOT Made-for-Kids).
> Created 2026-08-02. References: *Mere Hamraaz* (AI method), *Thoda Thoda Pyaar* (visual mood).

## 1. Identity
- **Name:** Aashiqana ("romantic / lover-like") · **Key:** `aashiqana`
- **Promise:** the feeling of a 90s Bollywood love song — melody + real lyrics + cinematic romance — made fresh with AI.
- **Tone:** warm, tender, nostalgic, sincere. Never crude, never parody.
- **Palette:** monsoon/golden-hour — deep teal-blue rain tones + warm amber highlights, soft film grain. Elegant serif/Devanagari display for lyric type.

## 2. The non-negotiable rule (compliance spine)
- **NO real celebrities.** Never use a real actor/singer's name, face, or likeness; never label anything "Official Video." Every couple is an **original AI creation**.
- **Original songs only** — Kumar Sanu *style*, never his (or any label's) actual songs. No cover of copyrighted Bollywood tracks.
- **Synthetic-media disclosure ON** at upload (`status.containsSyntheticMedia=true`) — realistic AI humans require it (playbook §8).
- Honest framing in description: "Original song & visuals created with AI." Add "not affiliated with any film/music label."
- Music from **Suno Pro** (commercial tier) — regenerate anything made on free tier.

## 3. Format grammar
**Long-form (3–4 min):** full song → couple story across ~4 cinematic locations
(rain street · cafe/indoor warm · rooftop at dusk · misty hills), subtle motion only
(rain, hair, breath, slow push-ins, glances) → elegant Hindi lyric lower-thirds →
branded intro/outro sting.
**Short — couple-first, 21–28s — the retention-winning cut (LOCKED 2026-08-07).**
The song hook already stops the scroll; a Short dies from *slow visuals*, not a weak hook —
Aaja Ve measured **108% watch at 3s** but fell off a **cliff at 3.6s** because the open was one
held solo beauty shot and the couple (the romantic payoff) didn't arrive until ~6s. So the standard cut:
- **0–2s:** heroine hook shot (`G1`, slow Ken Burns push) + the **biggest lyric line on screen** + the vocal hook.
- **~2s:** cut to the **COUPLE** (`C3` almost-kiss / `C1` embrace) — the payoff lands *before* the old cliff.
- **then:** alternate heroine ↔ couple, **a new shot every ~1.5–2s, never static past 2s**, each with a subtle push.
- **last beat:** resolve back to the opening frame for a **seamless loop** (replays = watch time).
- **Lyric cards:** **bilingual — Devanagari + romanized stacked**, high-contrast, in the caption-safe band, one line per beat (widens reach + reads sound-off).
- Caption "**Use this sound 🎵**"; cover = first frame (no custom thumbnail — playbook §5).
Build with **`scripts/make_couplefirst_short.py`** (the standard Aashiqana-short assembler). The song
itself must be **hook-first** (best line first, cold-open, no intro — see Sound DNA / QUALITY-LEDGER).
**Long-form** stays the fuller couple story, but its shots are framed so any of them re-cut into this Short pattern.

## 3b. Release strategy — Shorts-first, curiosity-led (LOCKED 2026-08-07)
The channel is cold; don't spend on long-form until a song proves it earns attention.
- **Phase 1 (weeks 0–2): Shorts only.** Produce the **full** song on Suno (needed as source), but **do NOT publish the full track / long-form anywhere yet.** Ship **20–28s couple-first Short cuts** of the hook/chorus, **2–3 per week**. One song can yield **several** Shorts (different beats / lyric moments / motion) = cheap volume.
- **Build curiosity:** caption teases *"full song dropping soon 🎵"* + pin a comment. The withheld full track is the demand.
- **Measure** with `scripts/yt_retention.py`: which couple / hook / mood actually **sustains** (retention is a sustain problem, not a hook problem — playbook §13).
- **Phase 2 (analytics-gated, after 1–2 weeks):** only songs whose Shorts prove out get the **full long-form music video**. Losers stay Shorts-only. No long-form spend on unproven tracks.
- **Identity discipline:** every Short uses ONE couple, driven by the **exact start-frame ID** in `couple_library/leonardo_ids.json` — never lookalike thumbnails (see COUPLE-LIBRARY / memory). Intimate motion clips (Look/Almost/Touch) carry the couple payoff beats; the heroine open stays a Ken Burns still.

## 4. Visual system — the AI couple
- **Cast from the couple LIBRARY, by mood-tag (LOCKED 2026-08-07) — do NOT re-generate a couple per song.**
  `couple_library/` holds 5 face-locked couples, each tagged to a vibe (Monsoon / Golden Hour / Midnight /
  Café / Seaside). Read the song's mood and pick the matching couple: **`python scripts/pick_couple.py --mood
  "<one-word mood + keywords>"`** scans each `couple.meta.json` (`best_for`/`vibe`/`mood` tags) and returns the
  folder + face refs + shots. Reuse the SAME couple across a song's long-form AND its Shorts. Only generate
  2–3 song-specific extra shots on-model from that couple's refs at production (COUPLE-LIBRARY §2 two-tier policy).
  The **Midnight** couple (neon / Saiyaara / situationship) is the channel's differentiated bet — see Sound DNA.
- **Consistency:** engine is **Leonardo Nano Banana 2 Image-Ref** (photoreal + identity-consistent; replaced Kino XL charref — COUPLE-LIBRARY §1). Attach the couple's `refs/` (anchor + hero_face + heroine_face) as Image Ref on every extra shot.
- **Look target:** cinematic, candid, natural skin (avoid the AI-face uncanny valley — playbook §6). Wardrobe: modern-elegant Indian/indo-western. Real-feeling locations.
- **Motion:** SUBTLE. Image-to-video with gentle ambient motion; no exaggerated lip-sync/dance (yet). Slow dolly/push-ins for premium feel.

## 5. Pipeline (per song)
1. Lyrics (original Hindi) → `songs/NN-slug/lyrics/lyrics.md`
2. Suno Pro (Chrome) → download mp3 → `songs/NN-slug/renders/song.mp3`
3. Couple charref → 4+ scene stills → `characters/`, `scenes/`
4. Image→video subtle motion clips → `scenes/`
5. Assemble long-form + Short, Hindi lyric overlays, audio master, bookends → `renders/`
6. Upload (`--synthetic`, category Music, both formats) → verify list (playbook §9)

## 6. Locked params
| Field | Value |
|---|---|
| Pipeline | A (music video), non-MFK |
| Music | Suno Pro, Custom mode, male vocal, 90s Bollywood romantic |
| Song style prompt | see per-song `lyrics.md` |
| Couple | original AI, charref-locked per song, fresh-per-song default |
| Cadence | quality-first; ~1 premium song/week until format proves |
| Disclosure | synthetic-media = true |

## 7. Song log
| # | Title | Theme | Status |
|---|---|---|---|
| 01 | Tu Hi Hai (Baarish Aur Tum) | first love / rain | ✅ LIVE 2026-08-03 (long-form TRmiRnKEKJc + Short 1yWfA_Tg61Y, karaoke v3) · + final-chorus **hook cut** Short 2026-08-05 · + **lyric duel** Short 2026-08-06 (both derivative, see QUALITY-LEDGER §4b) |
| 02 | Aaja Ve | golden-hour yearning / "come to me" | ✅ LIVE 2026-08-03 (long-form ZQQvRrGWGLk + Short TMVJHHv7v4c) — 30/40 on the ledger, beat A1+A6 |

### Song #01 production notes (reusable)
- Song: Suno Pro V1 `d7e8b8d0-45dd-4d74-b1c0-e54dfe7a6711` (4:17). Alt V2 `6c050f89…`.
- Couple master anchor: `characters/couple_twoshot_0.jpg` (Kino XL, charref preproc 133 High).
- Motion: 3 via Leonardo **API** (Wan 2.1, API wallet drained after 3) + 3 via Leonardo **web** (Hailuo 2.3, web tokens plentiful — `Create Video` on library image, pull mp4 via read-API GET `generations/user/{uid}`, curl with browser UA). **Lesson: API tokens ≠ web tokens; use web `Create Video` for volume.**
- Assembly: `scripts/assemble_music_video.py` (motion clips + Ken Burns stills, xfade 0.7s, song + 4s fade-out). Lyrics: `scripts/lyric_overlay.py` (PIL PNG lower-thirds, romanized, Georgia Bold) — separate pass, timing in `lyrics/timing.json` (first ~90s from whisper vocal onsets; rest estimated).
