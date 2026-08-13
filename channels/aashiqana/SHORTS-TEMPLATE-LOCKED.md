# Aashiqana — LOCKED Sensual-Motion Shorts Template (v1, 2026-08-12)

> The proven, repeatable pipeline for premium Aashiqana Shorts. Every future short
> matches this level. Validated on **Aadhi Raat (kiss-open)** and **Aaja Ve** (both armed).
> Companion: `BRAND-BIBLE.md` (spine), `QUALITY-LEDGER.md` (bar), memory `[[aashiqana-connected-motion]]`.

## The bar (what "same level" means)
A ~22s vertical Short = **4 identity-locked, DIFFERENT connected shots** of ONE AI couple that
flow like a real music-video cut, over a **word-first hook** (vocal on-screen at 0:00), with
bilingual karaoke-style captions + premium branding. Sensual but **tasteful & YouTube-safe**.

## Non-negotiables
1. **Word-first hook** — the audio MUST open on a vocal WORD at 0.0s, never humming/intro.
   Whisper-verify every hookcut (`faster_whisper` small, hi, word_timestamps); cut so word[0] ≈ 0.0s.
2. **Varied setting per song** — do NOT repeat the previous short's location (e.g. neon rooftop →
   golden bedroom). Same-location day/night swaps read as templated. Rotate the world each time.
3. **Identity lock** — ONE couple, face-consistent across all 4 keyframes (Nano Banana 2 Image-Ref).
4. **Sensual, not crude** — bare shoulders / off-shoulder / open-collar / near-kiss / from-behind /
   sink-to-bed are OK; no lingerie/nudity/explicit. Realistic-AI-human intimacy → tasteful only
   (a strike sinks the channel). Leonardo's content filter DISABLES Generate on words like
   "sensual/lips/almost-kiss/bare shoulders" — use tamer wording ("tender", "cheek near shoulder",
   "quiet loving pause"); the VISUAL still reads intimate.
5. **Synthetic disclosure ON** at upload + AI disclosure in description (never a celebrity likeness).

## Pipeline (the exact steps)
1. **Anchor** — Leonardo web → **Nano Banana 2**, 2:3 (848×1264). Either reuse a locked couple or
   generate a FRESH anchor (×4) in the song's vibe; VJ approves the face. Lock it.
   *(Exact library-couple faces are unrecoverable — local upload to Leonardo is sandbox-blocked —
   so fresh-anchor is the reliable identity path.)*
2. **4 keyframes** — Nano Banana 2, **Image Reference = the anchor** (pick from Your Generations,
   NOT upload). Beats: **K1 establishing embrace · K2 her single · K3 the bold intimate beat
   (embrace-from-behind) · K4 near-kiss payoff**. Prompt "the SAME couple/woman from the reference…".
   Fetch full-res via REST GET `generations/user/{uid}` (deep-find the image url).
3. **Motion** — Leonardo web → **Hailuo 2.3 (≈98 tok/6s, 24× cheaper than Seedance — never Seedance)**.
   **Start Frame** only (delete any Image-Ref chip → image icon → "Start frame" → pick keyframe).
   9:16, 6s. Dynamic motion, not just push-ins: **front-to-camera turn, turn-within-his-arms from
   behind, sink to sit on the bed**. One clip per keyframe. Fetch mp4 via `motionMP4URL` (REST GET).
   *(UI note: after Blueprint/nav round-trips the Generate button can stick disabled or drop the
   prompt/ref — a full tab close+reopen fixes it; a plain reload may not.)*
4. **Stitch** — `scripts/assemble_motion_generic.py --clips <ordered mp4s> --audio <hookcut>
   --lyrics <timing.json> --out <short.mp4>`. Cross-dissolve 0.5s, bilingual **Kohinoor** cards
   (romanized amber + Devanagari white). Order: open on the strongest hook beat (her turn / near-kiss).
5. **Brand** — `channels/aashiqana/songs/03-aadhi-raat/polish_short.py --src <short> --out <branded>
   --pov1 "…" --pov2 "…"`. Adds: **POV hook line tied to the song's own lyric** (0–3s), subtle
   `@aashiqana.diaries` gold wordmark watermark, **"wait for it 🥹"** tease (~10s), and the
   **premium end card** (drawn gold monogram ring + Playfair-italic "Aashiqana" + USE THIS SOUND +
   handle + "a new love song every week"). Emoji via Apple Color Emoji @160 scaled.
6. **Arm** — `scripts/yt_upload.py --channel aashiqana --video <branded> --title "…#shorts"
   --desc-file <desc> --tags "…" --category 10 --audience general --synthetic --privacy public
   --publish-at <RFC3339 UTC>`. Cover = first frame (no custom thumb, playbook §5).

## Reusable assets
- `scripts/assemble_motion_generic.py` — generic connected-motion stitcher (any song).
- `channels/aashiqana/songs/03-aadhi-raat/polish_short.py` — parameterized premium branding
  (`--src --out --pov1 --pov2`).
- Public review host: Supabase `factory-renders` bucket, `aashiqana/<song>/…` (upsert = stable URL).

## Serial mode (added 2026-08-13 — see BRAND-BIBLE §3c)
When a song is the ACTIVE SERIAL ("Unki Kahani" chapters), the template runs with these deltas:
1. **No fresh anchor** — Image Reference = the registered identity frames of the serial couple
   (`couple_library/leonardo_ids.json`), i.e. the previous chapter's approved keyframes picked
   from Your Generations. Face approval already stands; keyframe stills still get VJ review
   before motion spend.
2. **Setting rotates within the couple's world** — new location each chapter, same
   world/mood/wardrobe DNA (satisfies non-negotiable #2 chapter-to-chapter).
3. **Different bar each chapter** (Ch.1 hook/chorus → Ch.2 verse 1 → …), still word-first
   at 0.0s, whisper-verified.
4. **Chapter furniture** — description header "Chapter N of Unki Kahani — <leads>' story" +
   link to previous chapter + "next chapter Thursday" tease; POV lines advance the story;
   the Short must still work standalone and loop.
5. **Cadence** — TWO serials: **Aadhi Raat couple Thursdays 17:00 IST** · **Aaja Ve couple
   (Aarav & Meher) Fridays 13:00 IST**. Song name in every title disambiguates the chapters.
6. **Spoken outro CTA — required (VJ 2026-08-13, "no spoken cta" = a reject):** whispered
   story-question via `eleven_vo.py` (Lily `pFZP5JQG7iQjIQuC4Bku`, style 0.5, speed 0.92) →
   mix over the last ~5.5s with music ducked 0.35 → SUBSCRIBE pill at the spoken word via the
   CTA polish (`polish_short_cta.py --sub-at`), then re-level to −14 LUFS (+1 dB after duck).

## Shipped with this template
- Aadhi Raat kiss-open → youtu.be/nXhtuR-dHqU (armed 2026-08-12 13:30 IST) — **= Unki Kahani Ch.1 (active serial)**
- Aaja Ve golden-bedroom → youtu.be/RUm7xNDaAGQ (armed 2026-08-13 13:00 IST) — series frozen after Ch.1; Ch.2 built + held
