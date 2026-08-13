# Calm AI — Production Blueprint (v0, PROVISIONAL)
_Written at scaffold time 2026-08-12 by adapting the locked `already-happening` recipe (the closest sibling: host-less, cinematic, Shorts-only). **Nothing here is locked until Ep01 renders and this file is rewritten as v1.** Treat every param below as a starting point with a stated reason, not as law._

## 0. Canonical builder
There is **no builder yet**. Ep01 creates it:
```
cp channels/already-happening/build_ep01_v3.py channels/calm-ai/build_ep01.py
```
then re-skin it to the Calm AI frame (§5). After Ep01 renders, `build_ep01.py` becomes the template — per episode, copy it and edit only the four marked spots (§2).

**Why fork rather than write fresh:** `build_ep01_v3.py` already solves cold-open typography, per-beat VO timing, word-level captions from the `.words.json` sidecar, the grade, the music duck and the delivery encode. The differences are cosmetic (colour, pacing, card copy) and belong in constants, not in new code.

## 1. Locked-by-inheritance format
- Shorts-only, **9:16, 1080×1920, 30fps, −14 LUFS**, target **25–40s** (ideal 32s).
- 5-beat spine (BRAND-BIBLE §3): reassurance → what happened → panic corrected → what it means for you → one calm action.
- Fact-check gate is a hard gate, not a step (BRAND-BIBLE §5).

## 2. Per-episode variables (the ONLY things that change)
1. **Topic + 5-beat script** — one defused headline. Vary the opening line's *structure*, not just its words.
2. **VO** — `renders/epN/vo/beat{1..5}.wav`.
3. **5–6 motion shots** — `assets/epN/motion/*.mp4`.
4. In `build_epN.py`: `VO` dir, `MOT` dir, `BEATS` filenames, `HOT` keyword set, and the closing card's one action line.

## 3. VO recipe (PROVISIONAL — audition at Ep01)
- `scripts/eleven_vo.py --voice <TBD> --text "<beat>" --out beatN.wav --style 0.25 --speed 0.95`
- **Style 0.25 / speed 0.95** deliberately below `already-happening`'s 0.32/1.0 — calm channel, and the Lulla lesson (playbook §15) is that caption/voice energy must match channel energy.
- **Voice: undecided.** Audition ≥3 warm low voices on the same beat and pick by listening; it must not be Brian (`already-happening`) or Hrithik (AI Unpacked). Log the winner here and in BRAND-BIBLE §8.
- One wav per beat — per-beat wavs are what drive both timing and word-level captions.
- Add **0.4s breaks between sentences** (the AI Unpacked pacing lesson: followable > fast).

## 4. Motion shot recipe (inherited)
- **Wan 2.6**, Video tab, **9:16, 5s, audio OFF, Full HD 1080×1920**, ~175 web-tokens/clip — the model the `already-happening` bake-off picked on 2026-08-12. Drive Leonardo through the claude-in-chrome extension (real logged-in session); fetch free via `scripts/leo_fetch_videos.py <dir> <n>`.
- **Calm AI look, distinct from the sibling:** daylight and domestic, not night-time and monumental. Kitchens, school runs, laptops on a sofa, hands, a phone face-down on a table. Slow single-axis camera moves only — drift, gentle push. **No whip pans, no dramatic reveals, no crowds.**
- Prompt for "soft diffuse daylight, shallow depth, coherent stable shapes" and an explicit slow camera move.
- Fire all shots back-to-back, poll from the terminal.

## 5. Build params to set at Ep01 (PROVISIONAL)
- Colours: `INDIGO=(99,102,241)`, base slate `(15,17,26)`, no pure white — soft `(232,234,246)` for type.
- **Cold-open:** slow indigo glow bloom + the fear line typing in, then a soft dissolve. Slower than `already-happening`'s hard cut — the cut IS the difference in tone.
- **Captions:** ≤4 words/line, indigo keyword colour, dark pill at y≈0.72, **never over the subject** (`step-chips-never-cover-content` rule generalises: overlays live in dead space).
- **Grade:** `eq=contrast=1.02:saturation=1.02, vignette=PI/8` — flatter and softer than the sibling's 1.05/1.08.
- **Score:** `../claude-tricks/assets/music/bed_4.mp3`, **−15dB under VO**, `loudnorm I=-14`. Chosen objectively with `scripts/song_energy.py` over all four beds: bed_4 is the lowest-BPM (50.2), lowest-LRA (3.0), near-lowest-centroid (1153) bed — as calm as bed_3 while leaving bed_3 to `already-happening` so the two channels never share a bed.
- **Brand bug:** top-left `◦ CALM AI`, body beats only.
- **Closing "calm card":** the one action, the tag "That's it. You're caught up.", one CTA — subscribe OR loop, never both.
- **Delivery encode:** `crf 21, preset slow, maxrate 12M, faststart, aac 192k, ar 48000` → `epN_web.mp4`.

## 6. Ep01 fast path
1. Pick the topic from `CONTENT-CALENDAR.csv` (row 01) or a live headline; **fact-check first, script second** — an unsourceable topic dies before the script exists.
2. Write the 5 beats. Read them out loud; if any sentence needs a second breath, cut it.
3. Audition the VO voice (§3), lock it, render `beat1..5.wav`.
4. Generate 5–6 Wan 2.6 shots (§4) → `assets/ep01/motion/`; fetch.
5. `cp channels/already-happening/build_ep01_v3.py channels/calm-ai/build_ep01.py`; re-skin per §5.
6. Render → frame-check (`scripts/probe_frames.py`) → lipsync/timing check → web encode.
7. Write `episodes/ep01.receipts.md` (every claim, dated source) and `episodes/ep01.json`.
8. Metadata from `CHANNEL-SETUP.md` → draft in `factory_posts` → VJ arms → `yt_upload.py --audience general --synthetic`.
9. **Rewrite this file as v1** with what actually got locked, and open `QUALITY-LEDGER.md` with Ep01 as the bar.

## 7. Cost discipline
Preview/animatic first, master only after approval. No paid image model where an in-house PIL card will do (cards, the calm card, the cold-open are all PIL). Motion is the only paid spend; keep it to 5–6 clips.
