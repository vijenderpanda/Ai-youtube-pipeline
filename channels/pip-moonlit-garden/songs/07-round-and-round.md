# Song #07 — "Round and Round, Little Light" (the **loop single**, 7 Aug 2026)

**Angle:** the channel's first purpose-built **loop** single. Every other Lulla song is a
2:30 episode with a beginning and an ending; this one is written so the last bar hands
straight back to the first, which is what a 30–60 min bedtime loop needs (BUILD-PLAN's
watch-time driver, `docs/CHANNEL-SETUP.md` Wk2). **Tempo ~60 BPM, target ~2:15.**

**What makes it loop-safe (the brief the audition is judged against):**
- No cold-start attack and **no final chord** — the outro repeats the intro line so the
  seam is a lyric hand-off, not a fade-to-fade splice.
- **Flat dynamic range throughout.** No build in the bridge — a build is the one thing
  that reads as a "restart" when the loop wraps.
- Circular lyric ("one more turn and one more turn") so a toddler hearing bar 1 again at
  minute 12 hears the same promise, not a new song.

**Audition (this is what `scripts/suno_gen.py` runs):**

```bash
python3 scripts/suno_gen.py \
  --style 'gentle children's lullaby, 60 BPM, music box and glockenspiel, soft warm piano, airy pad, tender female lead vocal, soft "ooh" backing harmonies, seamless looping, flat dynamics, no drums, warm reverb, cozy, bedtime' \
  --lyrics channels/pip-moonlit-garden/songs/07_lyrics.txt \
  --exclude-styles 'drums, percussion, brass, big finish, crescendo, orchestral swell' \
  --double --invert \
  --out-dir channels/pip-moonlit-garden/songs/candidates/07/
```

`--double` = 4 candidates from one typing session (§15 audition trick).
`--invert` ranks the **softest** cold open first — the correct polarity for a calm
channel; a loop single that opens with an attack announces its own seam.

**Human gate (§1.2):** the ranking is a listening order. Play top-down, and pick on the
one question the meter cannot answer — *does the last bar hand back to the first without
a bump?* Log the winner + why in `QUALITY-LEDGER.md`.

---

## Lyrics
Source of truth for the audition: [`07_lyrics.txt`](07_lyrics.txt) (original — safe to monetize).
Keep the `[Intro]/[Verse]/[Chorus]/[Bridge]/[Outro]` tags; Suno honours them.

## Metadata (SEO)
- **Title:** `Round and Round, Little Light 🌙 Soft Bedtime Loop for Toddlers | Lulla's Moonlit Garden`
- **Tags:** bedtime loop, sleep music for toddlers, lullaby loop, calm songs for babies,
  soothing nursery song, 1 hour lullaby, Lulla, moonlit garden
- Made-for-Kids: YES.
