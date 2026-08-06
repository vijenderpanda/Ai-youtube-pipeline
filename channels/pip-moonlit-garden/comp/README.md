# Lulla 1-hour compilation — build state (2026-08-06)

Calendar row **C1**, planned **2026-08-10**. Spec: [`60min_calm.json`](60min_calm.json).

**Status: spec complete and validated, blocked on two account-level inputs.**
Nothing here needs more design work — it needs credits and a browser login.

---

## What is done

| | |
|---|---|
| Running order | **Locked**, measured with `scripts/song_energy.py` → [`energy.json`](energy.json) |
| Duration budget | **Locked** to 3601.04 s = **1:00:01**, every figure ffprobe-measured |
| Join / dim / loudness behaviour | **Validated** — `assemble_compilation.py` extended + tested (below) |
| Interlude scene prompts | **Written**, 21 of them, seed-locked → `scripts/gen_lulla_interlude_stills.sh` |
| Interlude beds | ⛔ **blocked** — no Suno access |
| Interlude stills | ⛔ **blocked** — Leonardo account out of API tokens |

---

## The two blockers

### 1. Leonardo is out of API tokens

```
POST /generations → {"error":"not enough api tokens userId: 3aa5736c-…"}
```

All 11 generations attempted on 6 Aug failed this way; zero images were produced,
zero credits were spent. **Top up the Leonardo account**, then:

```bash
bash scripts/gen_lulla_interlude_stills.sh          # all 21 stills
bash scripts/gen_lulla_interlude_stills.sh i5a i9b  # or just the ones you want
```

21 images at 1344×768, one prompt each, `num_images=1`, master seed `1926068932`.
Two notes baked into that script: Leonardo **rejects `num_images=3`** at this size on
this tier, and because the seed is locked, two images from *one* prompt are variations
of a single composition — crossfading between them reads as a freeze bug, so every
still gets its own clause.

**QC before building:** the arc has to actually darken. Eyeball `comp_i1a_0.jpg`
against `comp_i9b_0.jpg` — if the tail frames are not obviously near-black, the prompt
half of the dim did not land and `dim_arc`'s ±0.20 eq ramp alone will not save it.

### 2. Suno is unreachable from here

Three paths, all shut on 6 Aug:

- `http://127.0.0.1:9222/json/version` → connection refused (no CDP Chrome running)
- `~/.chrome-suno-cdp` → does not exist (nobody has ever logged in on that profile)
- claude-in-chrome extension → *"Browser extension is not connected"*

`suno_gen.py`'s own docs are explicit that the first step is a human one, and it must
stay that way — the account login is not something an agent should be doing:

```bash
# in YOUR OWN terminal, once per boot:
python3 scripts/suno_gen.py --print-chrome-recipe
# → launches real Chrome on a dedicated profile with --remote-debugging-port=9222
# FIRST TIME ONLY: sign into Suno there with the PRO seat.
```

`assert_paid_seat()` will refuse to spend credits unless `/account` reads a paid plan —
free-tier Suno output stays **non-commercial forever**, even after upgrading, and this
is a monetised MFK channel.

#### ⚠️ A tooling gap, deliberately not papered over

`suno_gen.py` **cannot currently generate these beds unattended.** It requires
`--lyrics` and has no instrumental toggle, and — more fundamentally — a reprise of a
song's *own melody* is Suno's **Cover** flow (pick the existing song, restyle it), not
the text-to-music create flow the script automates. Writing that automation blind,
against a UI nobody can currently load, would be guesswork; the §2 selector notes in
`suno_gen.py` exist precisely because that UI moves. So the nine beds are a hand-flown
Chrome session this once, and the automation is a follow-up to write **while looking at
the live page**.

#### The nine beds

Instrumental, no vocals, no percussion, same key/feel as their parent song. Target
≥3 min each (they loop to fill, so longer is only ever better — `build_interlude()`
uses `-stream_loop -1`). Save as `songs/reprises/reprise_i{1..9}.mp3`.

| bed | reprise of | intent |
|---|---|---|
| i1 | #2 Count the Fireflies | the counting figure, slowed, no vocal |
| i2 | #5 Sleepy Little Colors | the colour motif dissolving |
| i3 | #1 Little Light, Goodnight | the goodnight cadence, music-box |
| i4 | #3 Goodnight, Little Garden | sparse, wide, celeste |
| i5 | #4 Breathe with Lulla | the breathing pulse only |
| i6 | #6 Time for Bed | the tuck-in theme, very low |
| i7 | motifs from #1 + #3 | coda — almost no melody, drifting pads |
| i8 | motifs from #4 + #6 | coda — a few notes, long gaps |
| i9 | one held motif | coda — near-silence with a single warm figure |

Style prompt (all nine), with the *parent song's* descriptors appended:

```
gentle instrumental lullaby, music box and soft celeste, warm analog pad,
very slow, sparse, no drums, no percussion, no vocals, low dynamic range,
soothing bedtime, fades to near silence
```
Exclude styles: `drums, percussion, brass, vocals, choir, bright synth, build-up`

Rank the audition pool softest-attack-first (`--invert`, the calm-channel setting) —
but the ranking is a listening ORDER, not a verdict (§1.2). Pick by ear.

```bash
python3 scripts/suno_gen.py --rank-only channels/pip-moonlit-garden/songs/reprises/ --invert
```

---

## Then build

```bash
python3 scripts/assemble_compilation.py \
  --channel pip-moonlit-garden \
  --spec   channels/pip-moonlit-garden/comp/60min_calm.json \
  --out    channels/pip-moonlit-garden/renders/comp_60min_calm.mp4
```

Expect `>> DONE: … (3601.04s = 60m01.0s, 15 segments, xfade=2.50→5.00s, dim_arc=True,
bookends=applied)`. The script now prints **predicted vs actual** duration and warns if
they disagree by more than 1 s — if that warning fires, do not ship, the offset math and
ffmpeg have diverged.

**Gate before upload** (§3 — the loudness reference is the last shipped master, measured,
never this doc's prose):

```bash
ffmpeg -i channels/pip-moonlit-garden/renders/comp_60min_calm.mp4 -af ebur128=peak=true -f null -
ffmpeg -i channels/pip-moonlit-garden/renders/song06_final.mp4      -af ebur128=peak=true -f null -
```

Every segment is individually two-pass `loudnorm`-ed to −14 LUFS before joining, so the
hour should land close to the singles — but the interludes are deliberately quieter
material and will pull the integrated figure down. Compare, and if the gap is more than
~0.5 LU, fix it with a pre-gain on the *beds*, not by touching the songs.

---

## What was validated on 6 Aug (so you don't re-litigate it)

`assemble_compilation.py` got two changes, both tested:

1. **`xfade_ramp: [2.5, 5.0]`** — per-join crossfades instead of one flat value, because
   the brief wants the back half to dissolve more slowly than the front. The offset math
   had to change with it: a join's offset is `sum(durs[:i]) - sum(xfades[:i])`, the
   running timeline length, **not** `i * xfade`. Verified on a 3-segment build (offsets
   17.500 / 28.500, predicted 48.50 s = actual 48.50 s) and at full 15-segment scale.

2. 🔴 **`dim_tempo_scope`, defaulting to `interlude`** — this one was a real defect.
   `dim_arc` applied `atempo` to *every* segment, and because the graph then trims each
   segment's audio back to its **video** duration, `atempo` silently **cuts the end off**
   whatever it touches. Measured on a synthetic tail-beep: at the 14th segment
   (`atempo=0.916`) roughly **9% of the audio never plays** — about **15 seconds** off the
   end of a 160 s song, i.e. its entire closing cadence. On a looped ambient bed that is
   inaudible; on a published song it is an edit, and it would have broken the one rule
   this whole compilation is built on. Songs now get the brightness ramp only. The
   filtergraph was checked directly: `[1:a]` (interlude) carries `atempo=0.9940`,
   `[0:a]` and `[2:a]` (songs) carry none.
