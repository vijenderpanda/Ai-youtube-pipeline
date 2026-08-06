# Aaja Ve — `short_payoff` CUT SHEET
**The assembler follows this file. Every timestamp below is derived from `short_payoff/hook_bar.json`; nothing is hardcoded.**

| | |
|---|---|
| Cut | `short_payoff` — the payoff cut (derivative #2 for song #02) |
| Canvas | 1080×1920, **30 fps** |
| Audio in-point | **`-ss 67.61 -t 29.60`** → 67.61 → **97.21** |
| Total duration | **29.60 s = 888 frames** (target band 29.5–30.0 ✓) |
| Spine | 6 beats, 3 locations, story order **apart → memory → reunion** |
| Crossfade | 0.70 s (21 f) × 5 transitions |
| Source clips | 1376×768 @ 24 fps, 5.875 s each (landscape → vertical band) |
| Source stills | 1344×768 |

Derived from `hook_bar.json`: `chosen_start_s = 67.61`, `guard_pre_roll_s = 0.15`,
`vocal_onset_s = 68.16`, `band_downbeat_s = 67.76`. In cut-local seconds that is
**band slam 0.15 · breath 0.17 · first voiced "Aa-" 0.55**.

> Audio out is **97.21**, i.e. **0.01 s inside** `hook_bar.json`'s chosen `cut_end_s` 97.22.
> That is one 30 fps frame and it stays inside the same 20 ms −23.4 dB micro-gap, with
> 0.19 s of clearance before the next phrase attacks at 97.40. The out point is preserved.

---

## 1 · Duration arithmetic (published, per spec)

```
nominal spine   5.70 + 4.60 + 5.70 + 4.60 + 5.70 + 5.70   = 32.00 s
less overlap                              − 5 × 0.70      = −3.50 s
                                                          = 28.50 s   ← 1.00 s SHORT of the band
```

It does not add up, so the beat durations are fixed **here**, not in assembly:

```
B2 Ken Burns   4.60 → 5.10   (+0.50, at the spec cap)
B4 Ken Burns   4.60 → 5.10   (+0.50, at the spec cap)
B6 reunion     5.70 → 5.80   (+0.10)

final spine  5.70 + 5.10 + 5.70 + 5.10 + 5.70 + 5.80 = 33.10 s  (993 f)
less overlap                            − 5 × 0.70   = −3.50 s  (105 f)
TOTAL                                                = 29.60 s  (888 f)  ✓ in 29.5–30.0
```

**Judgment call — why B6 was *stretched* 0.10 s rather than B1–B5 trimmed.**
Both Ken Burns beats are already at the spec's +0.50 cap, which lands the spine at
29.50 s — legal, but 0.11 s short of the audio, which would drag the out point back to
97.10 and off the quietest frame `hook_bar.json` deliberately chose. Adding 3 frames to
B6 instead lands 888 f = 29.60 s, matching the audio to within one frame and keeping the
out point. B6's source is 5.875 s, so 5.80 s is real footage — **no freeze frame, no
black**. The spec's letter offered "trim B6"; trimming moves the wrong number.

> **30 fps rounding note:** 29.61 s is not frame-aligned (888.3 f). 888 f = 29.600 s is
> the nearest whole frame at or below it. Every duration in this sheet is a whole frame
> count — do not re-derive them from 29.61.

---

## 2 · EDL — beat map

`tl_in/tl_out` = position on the 29.60 s timeline. `solid` = the window where the beat is
the only image on screen (between transitions). `xf_offset` = the `offset=` value for
`xfade` in `assemble_short_hookcut.py` (its convention: `off = acc − XF`).

| beat | key | source | dur | f | tl_in | tl_out | solid_in | solid_out | xf_offset |
|---|---|---|---|---|---|---|---|---|---|
| **B1** | `clip_s01_hilltop_vert` | `renders/clips/s01_motion.mp4` | 5.70 | 171 | 0.00 | 5.70 | 0.00 | 5.00 | — |
| **B2** | `clip_s02_hilltop_kb` | `scenes/stills_final/S02.jpg` | 5.10 | 153 | 5.00 | 10.10 | 5.70 | 9.40 | 5.00 |
| **B3** | `clip_s07_reddress_vert` | `renders/clips/s07_motion.mp4` | 5.70 | 171 | 9.40 | 15.10 | 10.10 | 14.40 | 9.40 |
| **B4** | `clip_s08_roses_kb` | `scenes/stills_final/S08.jpg` | 5.10 | 153 | 14.40 | 19.50 | 15.10 | 18.80 | 14.40 |
| **B5** | `clip_s10_arrival_vert` | `renders/clips/s10_motion.mp4` | 5.70 | 171 | 18.80 | 24.50 | 19.50 | 23.80 | 18.80 |
| **B6** | `clip_s11_reunion_vert` | `renders/clips/s11_motion.mp4` | 5.80 | 174 | 23.80 | 29.60 | 24.50 | 29.60 | 23.80 |

Transitions (all `xfade=transition=fade:duration=0.70`): **5.00 · 9.40 · 14.40 · 18.80 · 23.80**

### Source trims (cut-local, head-anchored)

| beat | src in | src out | of | dropped |
|---|---|---|---|---|
| B1 | 0.000 | 5.700 | 5.875 | 0.175 tail |
| B3 | 0.000 | 5.700 | 5.875 | 0.175 tail |
| B5 | 0.000 | 5.700 | 5.875 | 0.175 tail |
| B6 | 0.000 | 5.800 | 5.875 | 0.075 tail |
| B2 / B4 | — | — | still | Ken Burns over 5.10 s, `zoom [1.00, 1.07]` |

**Head-anchored, tail dropped** — frame 0 of every i2v clip is the approved still, and
image-to-video drift accumulates toward the tail. Never anchor to the tail.

---

## 3 · The anti-flash proof — location holds

Three locations, two beats each, ~10–11 s per location. This is the structural difference
from every prior cut of this song.

| # | location (SHOTLIST) | beats | holds | screen time |
|---|---|---|---|---|
| 1 | **L1 sunset hilltop viewpoint** — apart | B1 + B2 | 0.00 → 10.10 | **10.10 s** |
| 2 | **L3 red-dress dusk-sky ridge** — memory | B3 + B4 | 9.40 → 19.50 | **10.10 s** |
| 3 | **L2 rustic-log wine picnic** — reunion | B5 + B6 | 18.80 → 29.60 | **10.80 s** |

Each location is entered on a motion beat and held on its partner beat before the cut
away. No location appears twice; no beat is shorter than 5.10 s.

---

## 4 · Card windows

Both cards are **overlays on the spine**, not appended segments. The spine already runs
the full 29.60 s; the cards composite on top of it. **Neither card adds a second of black
and neither changes the total duration.**

| card | window | dissolve | fully opaque | sits over |
|---|---|---|---|---|
| **frame-zero title** | 0.00 → 1.70 | **out** 1.00 → 1.70 (0.70 s) | 0.00 → 1.00 | B1 head |
| **end card** | 28.60 → 29.60 | **in** 28.60 → 28.95 (0.35 s) | 28.95 → 29.60 | B6 tail |

The frame-zero card is on screen for the band slam (0.15), the singer's breath (0.17) and
the first voiced *"Aa-"* (0.55) — you hear the hook land before you see the valley. Its
0.70 s dissolve is the card's **exit**, overlapping B1's head; B1 has been running
underneath since 0.00.

**Layer order: spine → cards → captions.**

> 🔴 **Hard requirement on the frame-zero card art.** Caption line 1 starts at **0.59**,
> i.e. 0.41 s *before* the card even begins to dissolve. The card must therefore keep
> **y 1590–1920 (the caption zone) free of type** — fill it with the same warm backdrop
> treatment as the band composition. The existing `short_outnow/cards/card_title.jpg` is a
> full-bleed 1080×1920 card belonging to a **different cut** — do not reuse it here.
> *Fallback if the card ships full-bleed:* push line 1's in-point to 1.70, which forfeits
> 1.11 s of its sweep and breaks karaoke sync on the hook word. Fix the card, not the caption.

---

## 5 · Caption windows

Re-based from `lyrics/timing_karaoke.json` by `chosen_start_s = 67.61`. These four values
are what step 4 (`karaoke_timing_short`) must reproduce; they are identical to
`hook_bar.json → cut_contents` and its `resolve_line` (`rel_s 5.79 / rel_e 9.81`).

| # | in | out | line | sits over |
|---|---|---|---|---|
| L1 | **0.59** | **5.45** | Aaja ve, aaja ve, aaja ve, aaja | **B1** (solid 0.00–5.00); ends 0.45 s into the B1→B2 dissolve. First 1.11 s is under the title card. |
| L2 | **5.79** | **9.81** | Tere bina ye shaam adhoori | **B2** (solid 5.70–9.40) — lands 0.09 s after B2 goes fully opaque, on his face. Ends 0.41 s into the B2→B3 dissolve. |
| L3 | **11.49** | **17.05** | Aaja ve, aaja ve, aaja ve, aaja | **B3 → B4** — bridges the B3→B4 dissolve at 14.40. |
| L4 | **17.21** | **21.13** | Mit jaaye bas ye thodi doori | **B4 → B5** — bridges the B4→B5 dissolve at 18.80, ends on B5. |

> **Sweep-cap note for step 4.** The L3→L4 gap is only **0.16 s**. Under the house
> `sweep-cap e = min(aligned_e, next_s − 0.20, s + 6.5)` convention, L3's end is capped to
> **17.01** (not 17.05). L1, L2 and L4 are unaffected. Use 17.01 for the sweep; the raw
> 17.05 is recorded here only for provenance.

### Where the text stops — and why

- Chant onset (first voiced *"Aa-"*): **0.55**
- Lyric block ends: **21.13**, i.e. **20.58 s after the chant onset** — the spec's "~20.6 s
  after the chant onset, after *Mit jaaye bas ye thodi doori*". ✓
- **Instrumental tail: 21.13 → 29.60 = 8.47 s, carrying NO TEXT AT ALL.**

That tail covers the last **2.67 s of B5** (she walks up the path) and **all of B6**
(the reunion). It is not dead air — `hook_bar.json` measures the vocal stem at −16.75 dB
there, wordless ad-libs over a full band at mix −12.8 dB. **The silence is deliberate: the
payoff is visual there.** Do not add a caption, a lyric echo, or a CTA over B5/B6.

**End-card clearance check:** final sweep ends **21.13**, end-card dissolve begins
**28.60** → **7.47 s of clearance**, requirement ≥ 0.40 s. ✓ (Comfortable by 7.07 s.)

---

## 6 · Withhold-inversion check ✅ PASS

The Aug-7 teaser hard-cuts **before** *"Tere bina ye shaam adhoori"*. The entire premise of
this cut is that the withheld line resolves.

| | |
|---|---|
| Line | **"Tere bina ye shaam adhoori"** |
| Cut-local | **5.79 → 9.81** (abs 73.40 → 77.42) |
| Beat | **B2** — `clip_s02_hilltop_kb`, his close-up profile, the ache |
| Placement | lands **0.09 s after B2 reaches full opacity**; completes 0.41 s into the dissolve toward the red-dress memory |
| Full gold sweep | **completes at 9.81** — 18.79 s before the end-card dissolve, 19.79 s before the end of the cut |

The withheld line plays **to completion, with its full gold sweep, on his face**, and the
image turns to the memory of her as the last word finishes. No escalation required.

---

## 7 · Vertical band — geometry and the real crop

Band **1080×1400 at y=190**, warm backdrop. Zones: 190 px above the band, band y 190–1590,
**caption zone y 1590–1920 = 330 px**.

The scale is height-driven (768 → 1400), so **only the width is sacrificed**:

| cut | band | geometric window | with `PAN=1.10` | caption zone |
|---|---|---|---|---|
| live Short (full-bleed) | 1080×1920 | 432 px = 31.4 % | 393 px = 28.5 % | 0 px |
| Baarish, Aug-5 | 1080×1200 @ y=250 | 691 px = 50.2 % | 628 px = 45.7 % | 470 px |
| **THIS cut** | **1080×1400 @ y=190** | **592 px = 43.0 %** | **539 px = 39.1 %** | **330 px** |

> 🔴 **`PAN = 1.10` is not free.** The playbook's published "~51 %" for Baarish is the
> *geometric* number; the pre-upscale that buys pan headroom spends 9 % of the width. The
> **instantaneous visible window here is 539 source px (39.1 %)**, not 592. Every framing
> number in §8 is measured at 539 px.

Also: because the scale is height-driven, **vertical latitude is only the PAN headroom**
(gh 1540 vs band 1400 = 140 px). `dy = 60` (the script default) uses 43 % of it. Fine —
but there is no room for large vertical moves.

**Caption zone is 330 px, not Baarish's 470 px.** Re-check the karaoke type size against
330 px before locking the overlay — *"Mit jaaye bas ye thodi doori"* at the Baarish point
size may not fit. This is a step-4/overlay concern, flagged here because the geometry
causes it.

---

## 8 · Per-beat framing — MEASURED, not assumed

Measured on real extracted frames against the 539 px window. **Two of these are defects at
`cx=0.50`, not preferences.**

| beat | `cx` | `dx` | verdict |
|---|---|---|---|
| B1 | 0.50 | 0 | ✅ man sits at x≈610–780 of 1376, essentially dead-centre. Clean. |
| B2 | **0.46** | 0 | ⚠️ taste. At 0.50 (window 403–941) his face holds but the back of his head is cut and there is dead space right. 0.46 balances it. Not a defect. |
| B3 | 0.50 | 0 | ✅ her face centred, well inside. Clean. |
| B4 | **0.48** | 0 | ⚠️ at 0.50 (window 403–941) her face's left edge sits **on** the window edge at x≈400. 0.48 restores margin and still holds both faces. |
| B5 | **0.54** | **+220** | 🔴 **defect at 0.50.** See below. |
| B6 | **0.525** | 0 | 🔴 **defect at 0.50.** See below. |

### 🔴 B6 — the reunion two-shot is decapitated at `cx=0.50`

Her face x≈640–830, his x≈790–980. The centred 539 px window is **419–957**, so the right
edge **cuts through the side of his head**. This is precisely the failure the playbook warns
about for tight vertical crops — on the single most important frame of the cut.

**`cx = 0.525`** → window **453–991**: both faces complete, roses held in the low centre,
only his outer shoulder clipped. Verified on frame. **Do not ship B6 at 0.50.**

### 🔴 B5 — the subject walks out of a static window

She walks *toward camera*, growing and drifting right across the beat. Measured at 539 px:

- t≈0.05 → she fits inside the centred window
- t≈4.60 → the window's right edge **slices down her face and body**

**`cx = 0.54` with `dx = +220`** (gw px) tracks her: the source window travels
**419–957 → 529–1067** across the 5.70 s, which is exactly the measured start and end
framing. If lateral drift is unavailable, static **`cx = 0.58`** protects the end of the
beat at the cost of the opening. Verified on frame at both endpoints.

Two bonuses from moving right: it excludes the **stray second blurred figure at x≈450–500**
that `REROLL-MANIFEST.md` already flagged ("crop out … distant 2nd figure"), and the
**bottom-right object** at x≥1090 stays outside for the first half of the beat.

> **`cx` means something different for stills.** For video beats `cx` positions the `crop`
> window directly. For the Ken Burns beats (B2, B4) `cx` feeds `zoompan`'s `x=` expression
> *before* a centred crop, so the effective shift is `(cx−0.5)·gw/zoom` and varies with the
> zoom ramp. Verify B2/B4 on the rendered segment, not by arithmetic.

---

## 9 · Beat labels vs what the footage actually shows

The spec's beat labels describe the **scripted** shots. Three were never rendered as
scripted — `scenes/REROLL-MANIFEST.md` already records this. The sheet must describe the
frames the assembler will actually see.

| beat | spec label | what the frame shows | verdict |
|---|---|---|---|
| B1 | "he calls into the valley" | Man alone, back to camera, **arms down at his sides**, facing layered hills at low sun. **No distant red figure** — manifest: "distant red-figure didn't render". | ✅ **reads better than the label.** "He stands facing the empty valley" is exactly the *apart* beat. Keep. |
| B2 | "his close-up profile, the ache" | Exactly that — chin lifted, eyes up into the rim light. | ✅ on spec (manifest: "✅ KEEP, on spec"). |
| B3 | "the red-dress reveal" | **Bust** over-the-shoulder glance; the red gown is only the bodice at the bottom edge. Manifest: "premium 💎 (bust, not full-length)". | ⚠️ it is a **face** beat, not a dress reveal. Works in the band; the label is wrong. |
| B4 | "the roses land in her hands" | **Behind-embrace** — he nuzzles her cheek from behind. A **single** rose low-left at x≈180–330, **outside the crop window at any usable `cx`**. Manifest: "scripted handoff never rendered in 2 tries". | 🔴 **label unsupported twice over.** See below. |
| B5 | "she walks up the path, **he rises**" | She walks toward camera in red with roses. The man is a **distant blurred figure walking away** at x≈300–420 — he does not rise. The band crop removes him. | ⚠️ **the crop fixes it.** What survives reads cleanly as the arrival. |
| B6 | "foreheads touching" | Faces close, **nose-to-nose**, eyes on each other, roses in the low centre. | ⚠️ near-spec (manifest: fix-roll for the mustache). Reads as the reunion. |

### 🔴 B4 — escalated, not silently fixed

The "roses" story beat cannot be delivered from `S08.jpg`. The bouquet handoff was never
rendered, and the one rose that exists is cropped out by this cut's band geometry. Keeping
the rose would require `cx ≈ 0.354` (window 180–772), which **cuts the man's face in half**
and destroys the two-shot — a worse trade than losing the rose.

**Recommendation:** keep `cx = 0.48` (both faces, no rose) and call B4 what it is — *the
memory-intimacy beat*, the held partner to B3's glance. It carries no lyric that mentions
roses: *"Gulaab tere haathon mein"* sits at **abs 127.70**, far outside this 67.61–97.21
window, so there is **no lyric-visual contradiction** and no §1.4 narrate-what-you-see
defect. Nothing in the cut breaks.

**But this is a story-label change, so it is the reviewer's call, not the sheet's.** If the
"roses land in her hands" beat is essential to the payoff arc, `S08` needs a third re-roll
and this cut should wait for it.

---

## 10 · Assembler warnings — `scripts/assemble_short_hookcut.py`

> 🔴 **Running the script unmodified produces the Aug-5 Baarish cut, not this one.**
> Band geometry and crossfade are **module constants with no CLI flags**. An unmodified run
> silently emits 1080×1200 @ y=250 with 0.55 s crossfades and a cold backdrop — i.e. it
> breaks differentiation items (d) and (e) *without erroring*.

Required deltas:

| line | constant | current | this cut |
|---|---|---|---|
| 27 | `BAND_H` | 1200 | **1400** |
| 27 | `BAND_Y` | 250 | **190** |
| 29 | `XF` | 0.55 | **0.70** |
| 28 | `PAN` | 1.10 | 1.10 (keep) |
| 78 | backdrop `eq` | `brightness=-0.20:saturation=0.72:contrast=1.02` — **cold** | **warm** — owned by the band-composition step, not this sheet. Starting point: `brightness=-0.16:saturation=1.06:contrast=1.02` + a gentle `colorbalance=rs=0.06:gs=0.01:bs=-0.06`. Must not read as the Aug-5 cold wash. |

Structural gaps — the script's card model does not fit this cut:

1. **No frame-zero card support at all.** `card` is appended as a trailing segment
   (`body = adur − (card_d − XF)`). The frame-zero title card here is an **overlay on B1's
   head** and must be composited, not appended.
2. **The end card dissolve is hardcoded to `XF`.** This cut needs **0.35 s** for the end
   card while the beat crossfades stay at 0.70 s → needs a separate `CARD_XF` constant.
3. **Do not let the script's `flex` duration solver touch these beats.** Pass all six
   `dur` values explicitly (§2); any beat left without `dur` gets overwritten by
   `share = (need − fixed) / len(flex)` and the published arithmetic is void.
4. Pass the audio **pre-trimmed to 29.60 s**. The script drives the timeline off `adur`,
   so a 29.61 s input reintroduces the 0.3-frame misalignment §1 removed.

Audio extract:
```
ffmpeg -ss 67.61 -t 29.60 -i channels/aashiqana/songs/02-aaja-ve/track/aaja_ve_final.mp3 \
       -c:a pcm_s24le short_payoff/hook.wav
```
Then two-pass `loudnorm` to **−14 LUFS / −1.5 dBTP** on the lossless wav before muxing
(`hook_bar.json → downstream`, gain needed −1.7 LU).

---

## 11 · Differentiation ledger

| | axis | this cut | prior | differs? |
|---|---|---|---|---|
| **(a)** | shot order | **s01, s02, s07, s08, s10, s11** | live Short: `s07, s11, s01, s10, s12` | ✅ **zero positional collisions.** Opens on s01 (live opened s07); ends on s11 (live had it 2nd); **drops s12 entirely**; **adds s02 and s08**, two stills the live Short never used. Story order apart→memory→reunion vs the live Short's non-chronological order. |
| **(b)** | beat count | **6 beats**, min 5.10 s each | Aug-7 teaser: **3 flashes** | ✅ 2× the beats, and each beat is a *hold*, not a flash. |
| **(c)** | composition | **band** — 1080×1400 panel on a blurred backdrop, 539 px of source visible (39.1 %) | live Short: **full-bleed centre crop**, 393 px (28.5 %) | ✅ 1.37× more source width; captions live below the band instead of over the couple. |
| **(d)** | band geometry | **1080×1400 @ y=190**, **warm** backdrop, 330 px caption zone | Baarish Aug-5: **1080×1200 @ y=250**, **cold** backdrop (`sat 0.72`, `bright −0.20`), 470 px caption zone | ✅ taller band, higher placement, opposite backdrop temperature. |
| **(e)** | crossfade | **0.70 s** | Baarish Aug-5 / script default: **0.55 s** | ✅ slower, consistent with the anti-flash structure. |

### Teaser EDL — **STUB, filled in step 16**

```
Aug-7 OUT-NOW teaser (short_outnow) — actual EDL:  [ TO BE FILLED IN STEP 16 ]

  cut start (abs s)      : ____
  duration               : ____
  beat / flash count     : ____  (expected 3)
  shot order             : ____
  hard-cut point         : ____  ← must land BEFORE "Tere bina ye shaam adhoori"
  band geometry          : ____
  crossfade              : ____
  cards                  : ____

  Cross-check on fill-in:
    [ ] teaser hard-cut is confirmed BEFORE the resolve line (the withhold premise)
    [ ] teaser shot order differs from this cut's s01,s02,s07,s08,s10,s11
    [ ] teaser flash count < this cut's 6 beats
```
Reference for the fill-in: `short_outnow/timing_realign_full.json` (lines are already
cut-relative; its L2 "Tere bina ye shaam adhoori" sits at 10.59–14.06 in *teaser* time).

---

## 12 · QC checklist before this cut ships

**Arithmetic**
- [ ] Rendered duration is **29.60 s / 888 frames** (not 29.50, not 29.61)
- [ ] Five crossfades land at **5.00, 9.40, 14.40, 18.80, 23.80**
- [ ] Audio out is 97.21; no chop audible before the 97.40 attack

**Framing (the two real defects)**
- [ ] **B6 rendered at `cx = 0.525`** — extract a frame and confirm **his whole head is in
      the band**. At 0.50 it is cut.
- [ ] **B5 rendered with `cx = 0.54, dx = +220`** — extract frames at t≈0.2 and t≈5.5 of
      the beat and confirm she is inside the band at **both** ends
- [ ] No stray second figure visible in B5

**Text**
- [ ] Frame-zero card leaves **y 1590–1920 free of type**; L1's sweep at 0.59 is legible
- [ ] Karaoke type fits the **330 px** caption zone on the longest line
- [ ] **B5/B6 after 21.13 carry no text of any kind** (8.47 s of deliberate silence)
- [ ] *"Tere bina ye shaam adhoori"* plays 5.79 → 9.81 with its **full gold sweep**

**Differentiation**
- [ ] Band measures **1400 px tall at y=190** in the output (not 1200 @ 250 — the script's
      default would pass every other check while failing this one)
- [ ] Backdrop reads **warm**, not the Aug-5 cold wash

---

*Generated 2026-08-06 · derived from `short_payoff/hook_bar.json` (`chosen_start_s 67.61`),
`lyrics/timing_karaoke.json`, `scenes/SHOTLIST.md`, `scenes/REROLL-MANIFEST.md`,
`docs/PRODUCTION-PLAYBOOK.md` §14 + lines 325–326. Framing verdicts measured on extracted
frames at the 539 px PAN-adjusted window.*
