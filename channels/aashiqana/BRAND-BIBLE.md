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
- **MOTION path (restores the hook cliff):** pass **`--motion`** to weave the couple's identity-locked
  intimate clips (`<couple>/motion/*.mp4`, ordered Look → Almost → Touch) as the hook + payoff beats
  (`assemble_short_music.py` now has a `"clip"` beat kind). **ONE-COUPLE RULE:** the approved motion couple
  (e.g. Midnight `7a43cb0a`, see `couple_library/leonardo_ids.json`) may NOT share a face with the library
  disk stills, so with `--motion` the short is built from the **clips alone** — never mix disk stills of a
  different face. First trim the song to a ~22–28s cold-open hook cut, then:
  `make_couplefirst_short.py --couple couple_03_midnight --motion --audio hookcut.mp3 --lyrics timing.json --cut 2.2 --out short.mp4`.
**Long-form** stays the fuller couple story, but its shots are framed so any of them re-cut into this Short pattern.
- **LONG-FORM caption style (LOCKED 2026-08-13, VJ "Talab" reference): 2–3 word chunks,
  true whisper word-sync** — big Devanagari (Kohinoor, white, stroke) + romanized (Georgia, amber)
  stacked, centered lower third, each chunk on screen exactly while sung. Built by
  `songs/01-baarish-aur-tum/build_remaster_v2.py` (whisper words → chunk at >0.6s gaps / max 3
  words → PIL PNGs → batched ffmpeg overlays). **Long-forms ONLY — the Shorts templates keep
  their bilingual line-cards; do not apply chunks to Shorts.** Also: trim any instrumental
  intro so the first vocal lands ~2s in, and open on a charged couple close-up (hooky start).

## 3b. Release strategy — Shorts-first, curiosity-led (LOCKED 2026-08-07)
The channel is cold; don't spend on long-form until a song proves it earns attention.
- **Phase 1 (weeks 0–2): Shorts only.** Produce the **full** song on Suno (needed as source), but **do NOT publish the full track / long-form anywhere yet.** Ship **20–28s couple-first Short cuts** of the hook/chorus, **2–3 per week**. One song can yield **several** Shorts (different beats / lyric moments / motion) = cheap volume.
- **Build curiosity:** caption teases *"full song dropping soon 🎵"* + pin a comment. The withheld full track is the demand.
- **Measure** with `scripts/yt_retention.py`: which couple / hook / mood actually **sustains** (retention is a sustain problem, not a hook problem — playbook §13).
- **Phase 2 (analytics-gated, after 1–2 weeks):** only songs whose Shorts prove out get the **full long-form music video**. Losers stay Shorts-only. No long-form spend on unproven tracks.
- **Identity discipline:** every Short uses ONE couple, driven by the **exact start-frame ID** in `couple_library/leonardo_ids.json` — never lookalike thumbnails (see COUPLE-LIBRARY / memory). Intimate motion clips (Look/Almost/Touch) carry the couple payoff beats; the heroine open stays a Ken Burns still.

## 3c. Serial mode — "Unki Kahani" chapter Shorts (LOCKED 2026-08-13)
The channel's serial format: **ONE couple = one ongoing story, told in weekly chapter Shorts**
built on the locked template (SHORTS-TEMPLATE-LOCKED.md §Serial mode).
- **TWO parallel couple-serials run under the Unki Kahani umbrella (VJ 2026-08-13):**
  · **Aadhi Raat couple** (neon midnight-city world, Song #03) — **every THURSDAY 17:00 IST**.
    Ch.1 kiss-open youtu.be/nXhtuR-dHqU · Ch.2 verse-1 youtu.be/whB9e_p5-zE.
  · **Aaja Ve golden-bedroom couple — "Aarav & Meher"** (golden-hour world, Song #02) —
    **every FRIDAY 13:00 IST**. Ch.1 youtu.be/RUm7xNDaAGQ · Ch.2 youtu.be/8o2OKu0C6eg (Fri 2026-08-14).
- **Disambiguation rule:** the SONG NAME sits in every chapter title ("… | Aadhi Raat | Unki Kahani
  Ch. N" / "… | Aaja Ve | Unki Kahani Ch. N") — two Ch. Ns may coexist in the same week, the song
  tag + couple keeps them distinct. Never cross the couples or their worlds.
- **Identity:** every chapter drives NB2 Image-Ref off the SAME registered identity frames
  (`couple_library/leonardo_ids.json` → `aadhiraat_serial`) — the previous chapter's approved
  keyframes are the canonical face source, never lookalikes.
- **Setting rotation applies WITHIN the couple's world:** a NEW location each chapter
  (rooftop → 2am apartment → taxi → stairwell…), but always the same world/mood/wardrobe DNA.
  The template's "never repeat last Short's location" rule is satisfied chapter-to-chapter.
- **Continuity furniture in every chapter:** description header "Chapter N of Unki Kahani —
  <lead names>' story" + link to the previous chapter + "next chapter Thursday" tease; POV hook
  line advances the story; each chapter still works standalone (word-first hook, loopable).
- **Bar rule:** each chapter opens on a DIFFERENT bar of the song (Ch.1 = hook/chorus,
  Ch.2 = verse 1 …), whisper-verified word-first.
- **Outro stack — REQUIRED on every chapter (VJ 2026-08-13):** whispered story-question CTA
  (Lily voice via `scripts/eleven_vo.py`, ~5s, music ducked to 0.35 under it) + "<DAY> dekhna…
  miss na ho, subscribe kar lena" + **red SUBSCRIBE pill popping ON the spoken word**
  (branch polish `--sub-at <abs word ts>`; words.json from eleven_vo gives the offset).
  Re-check integrated loudness after the mix (ducking drops it ~1 dB — compensate to −14 LUFS).
- **Nasha lane (Song #04) is NOT a serial:** standalone mood Shorts, **every Wednesday**,
  fresh couple per song allowed, no chapter furniture.

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
| 02 | Aaja Ve | golden-hour yearning / "come to me" | ✅ LIVE 2026-08-03 (long-form ZQQvRrGWGLk + Short TMVJHHv7v4c) — 30/40 on the ledger, beat A1+A6 · golden-bedroom Short armed 2026-08-13 (RUm7xNDaAGQ) · **series FROZEN — Ch.2 built + HELD (§3c)** |
| 03 | Aadhi Raat | situationship / midnight city | ✅ armed 2026-08-12 (kiss-open Short nXhtuR-dHqU) · **ACTIVE SERIAL — "Unki Kahani" Ch.1, chapters every Thursday 17:00 IST (§3c)** |
| 04 | Nasha | rain / intoxication | standalone Wednesday lane, NOT a serial (§3c) — ep4 manifest ready (`episodes/ep4.json`) |

### Song #01 production notes (reusable)
- Song: Suno Pro V1 `d7e8b8d0-45dd-4d74-b1c0-e54dfe7a6711` (4:17). Alt V2 `6c050f89…`.
- Couple master anchor: `characters/couple_twoshot_0.jpg` (Kino XL, charref preproc 133 High).
- Motion: 3 via Leonardo **API** (Wan 2.1, API wallet drained after 3) + 3 via Leonardo **web** (Hailuo 2.3, web tokens plentiful — `Create Video` on library image, pull mp4 via read-API GET `generations/user/{uid}`, curl with browser UA). **Lesson: API tokens ≠ web tokens; use web `Create Video` for volume.**
- Assembly: `scripts/assemble_music_video.py` (motion clips + Ken Burns stills, xfade 0.7s, song + 4s fade-out). Lyrics: `scripts/lyric_overlay.py` (PIL PNG lower-thirds, romanized, Georgia Bold) — separate pass, timing in `lyrics/timing.json` (first ~90s from whisper vocal onsets; rest estimated).
