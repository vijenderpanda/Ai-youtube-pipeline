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
**Short (30–45s):** the mukhda hook, best 1–2 scenes, one big lyric moment →
"Full song on Aashiqana." (Cover = first frame; Shorts show no custom thumbnail — playbook §5.)

## 4. Visual system — the AI couple
- **Fresh couple per song** by default; a couple that performs well gets **reused** in a follow-up ("their story continues").
- **Consistency:** character-reference (Leonardo **Kino XL / charref**, NOT Lucid — playbook §2) or Fable/Higgsfield charref; lock a face per lead, reuse across all scenes of that song.
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
