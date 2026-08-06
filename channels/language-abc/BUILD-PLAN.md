# Build Plan — Poly the Parrot (Language / ABC)

> Pipeline **A** (kids music video). Inherits the network doctrine in `channels/README.md` and Pip's QC discipline. This doc spells out only the **deltas** for a multilingual learning channel.
> Goal: a premium, un-templated second channel that reuses ~90% of the existing factory and adds our biggest scale lever (multi-language fan-out) as *content*.

---

## 1. What's reused vs. new
**Reused as-is (zero new spend):** `leo_generate.sh` (Leonardo, fixed-seed consistency), `assemble_video.py` (gentle Ken Burns + crossfade — perfect for "bouncy but not frantic"), `make_thumbnail.py`, Suno Pro, the QC-gate habit.
**New for this channel:** Poly character + world (Brand Bible), an **ElevenLabs multilingual TTS step** for verified spoken foreign words (free tier), and the multilingual on-screen text spec.
> No render-engine changes needed here (that's a Vehicles problem, not ours). This is why Language/ABC is the cheapest, fastest second channel.

## 2. Content pillars
1. **Foundations (English anchor — the search-volume engine):** ABC song, phonics (letter sounds), counting 1–10 / 1–20, colors, shapes, animal sounds. Huge evergreen demand; establishes the channel.
2. **First Words in… (the differentiator):** greetings, numbers, colors, animals, "please/thank you" in ES / FR / DE / HI — 1–3 target words per video.

## 3. The fan-out engine (our scale lever) — 3 tiers
- **Tier 1 — Bilingual-in-one-video:** English anchor + a few target words (e.g. "Count to 5 in Spanish!"). This *is* the differentiator content and it's broadly shareable.
- **Tier 2 — Full dub to sister channels (the multiplier):** every **Foundations** song (pure, language-neutral visuals) gets fully re-voiced/re-sung into **Poly en Español / Poly en Français / …** channels. Same render, new audio + text = ~5× the view pool at near-zero marginal cost. Set up after 6–10 Foundations songs exist.
- **Tier 3 — Compilations + playlists:** 30–60 min learning compilations (watch-time/RPM driver) and autoplay playlists per pillar.

## 4. SEO playbook (kids-education specifics)
Parents scan + the algorithm autoplays. Optimize thumbnails + watch-time loops, not clever titles.
- **Title format (keyword-front-loaded, consistent suffix):**
  `ABC Song 🎵 Learn the Alphabet | Poly the Parrot` ·
  `Say Hello in 5 Languages 👋 Spanish, French, German, Hindi for Kids | Poly the Parrot`
- **Foundations = the discovery net** ("abc song", "phonics song", "counting song", "learn colors"); **First-Words = the differentiation + shares** ("spanish for kids", "hello in different languages").
- Chapters in every description (more watch time), consistent tags, parent-friendly pinned comment, rich description with learning outcomes.
- **Cadence:** 2–3 songs/week + 1 compilation/week. Consistency > volume.

## 5. Pronunciation QC
The one hard gate — see Brand Bible §7. Foreign words are **spoken TTS (verified)**, not gambled on Suno. Never publish an unverified pronunciation.

## 6. Money math
Made-for-Kids RPM ≈ **$0.30–1.00** (same COPPA reality as Pip). Levers specific to this channel:
- **Multilingual fan-out = up to 5× the view pool** on Foundations content — the single biggest accelerator.
- Education skews toward **strong evergreen watch-time** (parents replay learning songs), which helps the compilation/live formats that actually drive revenue.
- To $200/mo from ads ≈ ~570K views/mo — reachable faster here than a single-language channel *because* of the 5-language multiplier.

## 7. First 30 days (lean, concrete)
**Week 1 — Lock the brand core**
- Confirm working name **Poly the Parrot** (YouTube handle + light trademark check).
- Generate Poly (below), pick the best, **lock the seed** into Brand Bible §10.
- Create channel + banner + logo (reuse `make_channel_art.py`).

**Week 2 — Prove one hero video** → build Episode 1, **"Hello Around the World"** (`songs/01-hello-around-the-world.md`): the whole channel promise in one shareable video. Run the QC gate. This is the quality bar.

**Week 3 — Build the Foundations line** → batch ABC + Counting 1–10 + Colors (pure visuals = future Tier-2 dub masters). Set up the ElevenLabs voice + Google Sheet calendar.

**Week 4 — Publish + compile + iterate** → publish on a fixed schedule, drop a "First Words" compilation, start playlists. Read retention; double down on the winning format.

## 8. Concrete commands (run from repo root)
**Generate Poly (portrait, 4 options):**
```bash
scripts/leo_generate.sh \
  "Poly the Parrot: a small round cheerful cartoon parrot, teal body, sunny yellow belly, coral cheeks, three rainbow feathers as a head crest, big friendly eyes, short curved beak, storybook 2D children's book illustration, soft shading, thick clean outlines, warm cream background, wholesome" \
  "3d render, pixar, photoreal, realistic, neon, oversaturated, scary, deformed beak, extra limbs, blurry, text, watermark" \
  7b592283-e8a7-4c5a-9ba6-d18c31f258b9 4 1024 1024 \
  channels/language-abc/assets/character poly_v1
```
Pick the best → note its seed (from the Leonardo generation) → **lock it** → regenerate the chosen one + all scenes with that seed as the **9th arg** for consistency.

**Assemble Episode 1** (after Suno song + TTS inserts are muxed into `song01.mp3` and shots JSON is written):
```bash
python3 scripts/assemble_video.py \
  --shots channels/language-abc/songs/01_shots.json \
  --audio channels/language-abc/songs/song01.mp3 \
  --out   channels/language-abc/renders/ep01.mp4
```

## 9. Tool table (lean)
| Stage | Tool | Cost |
|---|---|---|
| Character + scenes | Leonardo Lucid Origin (`leo_generate.sh`) | 🟢 (existing key) |
| Song (English bed) | Suno Pro | 🔴 already paying |
| Foreign spoken words | ElevenLabs multilingual | 🟢 free tier |
| Assembly | FFmpeg `assemble_video.py` | 🟢 |
| Thumbnails / channel art | `make_thumbnail.py` / `make_channel_art.py` | 🟢 |
| Dub fan-out (later) | ElevenLabs / Synthesia / Kapwing | 🟡 |

*Living document — update as Poly finds his winners.*
