# ep_amazon_perplexity — BEAT MAP (v1)

**Channel:** AI Unpacked (`claude-tricks`) · **Layout:** `newsSplit` · **Builder:** `channels/claude-tricks/build_ep_v2.py`
**Depends on:** `script.md` v1 (locked, 9 lines) · `research.json` v1 · `vo_master` (⚠ not yet generated — see §0) · all clip assets
**Timing source:** measured ElevenLabs word sidecars (n=12 renders, locked chain: Hrithik `ZZ5OIPIzxVJswEhc0UXt`, style 0.4, `<break time="0.4s"/>`). Evidence: `beat_map_probes/*.words.json`.

---

## 0. Read this first — what is measured and what is gated

The plan orders `beat_map` **before** `vo_master`, but this asset's contract says
timings come from a *measured* words json and never from a predicted line map. That
dependency did not exist when this ran, so rather than publish the script's syllable
model, I synthesized the locked lines through the **exact locked voice chain** and
measured them. Twelve renders in total:

| variant | n | total (s) | in band [26,30] | L5 beat start (s) | in window [14,16] |
|---|---|---|---|---|---|
| **LOCKED** (script.md as written) | 3 | 28.28 / 29.26 / 29.44 — **mean 28.99** | **3/3 ✅** | 13.39 / 12.88 / 13.39 — **mean 13.22** | **0/3 ❌** |
| RECUT-A (+`shopping` L2, +`'s assistant` L3) | 3 | 30.56 / 31.25 / 30.98 — mean 30.93 | 0/3 ❌ | 14.43 / 14.64 / 15.26 — mean 14.78 | 3/3 ✅ |
| RECUT-B (+remand on L4, −`This video too.` L8) | 3 | 31.30 / 28.23 / 29.16 — mean 29.56 | 2/3 | 16.05 / 14.15 / 14.62 — **mean 14.94** | 2/3 |
| RECUT-C (1.3s break before L5, −L8 tail) | 3 | 29.26 / 30.09 / 29.12 — mean 29.49 | 2/3 | 13.80 / 15.04 / 14.22 — mean 14.35 | 2/3 |

**These are probe renders, not the master.** The vo_master job renders its own take.
Every number below is therefore a *reference* built on a real measured take
(`beat_map_probes/vo_probe3.words.json`, total **29.440s** — the draw closest to the
locked mean), and §9 gives the deterministic re-derivation the assembler must run
against the shipped `vo_v2.words.json`. **The shipped take wins over every number in
this document.**

**Reference take — measured line clock (`vo_probe3`):**

| # | start | end | dur |
|---|-------|-----|-----|
| 1 | 0.000 | 4.950 | 4.950 |
| 2 | 4.950 | 8.290 | 3.340 |
| 3 | 8.290 | 11.590 | 3.300 |
| 4 | 11.590 | 13.390 | 1.800 |
| 5 | **13.390** | 15.750 | 2.360 |
| 6 | 15.750 | 19.340 | 3.590 |
| 7 | 19.340 | 22.630 | 3.290 |
| 8 | 22.630 | 26.370 | 3.740 |
| 9 | 26.370 | 29.440 | 3.070 |

---

## 1. FRAME 1 — how the host and the mock are both on it

**Requirement:** the host speaks from frame 1 **and** the frozen chat mock is on frame 1.

**Known limitation (Ep24, QUALITY-LEDGER):** re-verified against the source this
build, not taken on trust. `build_ep_v2.py:1301-1332` parses only
`host` / `host2` / `rec:` / `stat:`, and `Short.tsx:389-390` renders `kind:"image"`
as the **whole** `<Sequence>` body. There is no underlay or per-segment overlay
layer, so a still cannot sit *under* a host beat without spending one of the nine
VO-pinned beats on it.

**Resolution for this episode — the `newsSplit` grammar itself, not a workaround.**
`Short.tsx:408-439` renders the host as a *single* `<OffthreadVideo>` outside any
`<Sequence>`, so it is on screen from composition frame 0 whenever the active beat's
mode is not `full`. Beat 1 is:

```
rec:ep_amazon_perplexity/chat_mock_hold.mp4@0.0|split
```

→ top pane (0–55%) holds the frozen mock from its own frame 0; bottom pane (45%,
magenta hairline) holds the lip-synced host from composition frame 0. **Both are
literally on frame 1.** No beat is spent, nothing is faked.

**Alternative rejected:** `host` (full-frame) on line 1, cutting to the mock on line 2.
The mock would first appear at **4.950s** on the reference take — 3.3× past the 1.5s
hook gate and past the cover hold entirely. The whole point of the frame-1 mock is
that the claim and its illustration arrive together; a 4.95s delay makes it a
mid-episode cutaway instead. Rejected.

**The `Cover` composites above all of it** (`Short.tsx:455` — rendered after segments,
host, chips, emphasis and captions) and is frame zero / the de-facto Shorts thumbnail.

**⚠ Constraint this pushes onto `chat_mock_agent_cart`:** a 1080×1920 card played
`|split` is scaled to a 1080×1056 pane with `objectFit:"cover"` → **the top 432px and
bottom 432px are cropped**. Every essential element (assistant label, the cart line,
the `ILLUSTRATIVE` footer) must sit inside **y ∈ [432, 1488]**. The planned
`footer_y: 1245` is inside the band ✅. This is the one asset in the episode whose
composition is constrained by its pane mode — the glyph card avoids it by running `|full`.

---

## 2. `cover.until` — derivation, and what it costs

Derived value: hook claim head **"Amazon just lost this round"** ends at **1.46s**
measured (`ROUND`.end; n=3: 1.54 / 1.43 / 1.46, mean 1.48). Default rule *hook end
+0.6s* → **2.06s**.

**2.06s is below Playbook §13's 2.5–4.0s floor for a title beat**, and
`build_ep_v2.py:1353-1363` documents exactly this failure: a derived `until` that
small opens `Short.tsx`'s `[until−0.7, until]` fade so early the poster is gone
before it can be read, and on a short enough value the fade opens before frame 0 and
dirties the frame-zero thumbnail.

**PINNED: `until: 3.0`** — the value already locked in `script.md` §(d). The pin wins
over the derived value (that precedence is explicit in the builder). Not a flash: a
readable 3.0s title beat with the hook fully audible under it.

**What it hides.** The cover draws above captions, so caption words before 3.0s are
covered (fully to 2.30s, then under a 0.7s dissolve):

| | words | hot words |
|---|---|---|
| fully hidden (<2.30s) | AMAZON, JUST, LOST, THIS, ROUND, IT, HAD, AN, A | **AMAZON, JUST, LOST, ROUND** (4) |
| under the fade (2.30–3.0s) | I, AGENT, BANNED | **BANNED** (1) |

**4 hot words hidden, 1 partially — accepted.** The cover states the same claim in
larger type: `AMAZON LOST` / `THE CART FIGHT` / `ninth circuit · aug 4 · case continues`.
AMAZON and LOST are on screen throughout, in Anton at 225px, rather than at 78px in the
caption band — the viewer loses nothing and the audio hook plays in full underneath.

---

## 3. Beat table

Paste-ready `beats` for `EPISODES_V2` (see §8 for the episode key):

```python
    "layout": "newsSplit",
    "outro": True,
    "beats": [
      "rec:ep_amazon_perplexity/chat_mock_hold.mp4@0.0|split",      # L1
      "rec:ep_amazon_perplexity/chat_mock_hold.mp4@0.0|split",      # L2 (merges with L1)
      "rec:ep_amazon_perplexity/broll/courtroom_ruling.mp4@1.5|full",  # L3
      "host",                                                        # L4
      "rec:ep_amazon_perplexity/broll/agent_shopping.mp4@2.0|split",   # L5  SECONDARY HOOK
      "rec:ep_amazon_perplexity/glyph_delegation.mp4@0.0|full",        # L6
      "host",                                                        # L7
      "rec:ep_amazon_perplexity/broll/checkout_human.mp4@1.0|split",   # L8
      "host",                                                        # L9
    ],
```

| # | VO line | start → end (ref) | source asset | `@t` | mode | why this visual belongs to this line |
|---|---------|-------------------|--------------|------|------|--------------------------------------|
| 1 | Amazon just lost this round. It had an A I agent banned from its site. | 0.000 → 4.950 | `chat_mock_hold.mp4` | 0.0 | `split` | The line names *an A I agent*; the mock shows an AI assistant working a shopping cart. Mock top, host bottom — both on frame 1 (§1). |
| 2 | That agent browses, compares, and fills your cart. | 4.950 → 8.290 | `chat_mock_hold.mp4` | 0.0 | `split` | Same hold continues (identical string ⇒ merged, §7.1). The mock's three exchanges *are* browse → compare → cart, arriving as the line names them. Generic shopping b-roll is **wrong** here: it shows a human browsing under a line about the agent (the Ep28 narrate-what-you-see failure). |
| 3 | The Ninth Circuit threw out the ban on Perplexity. | 8.290 → 11.590 | `broll/courtroom_ruling.mp4` | 1.5 | `full` | The line names a court; the beat shows the court. `full` gives the ruling the episode's one full-frame authority image. |
| 4 | The case is not over. | 11.590 → 13.390 | `v2_host.mp4` (host layer) | — | `host` | The scope caveat is the line most likely to be misheard as spin, so it is delivered full-frame to camera. Also gives the mandated compliance chip a clean frame (§6, W1b). |
| 5 | **The court said you are the one shopping.** | **13.390 → 15.750** | `broll/agent_shopping.mp4` | 2.0 | `split` | **SECONDARY HOOK.** The holding is that the *user* is the one accessing (C4/C5), so the frame must contain a **person** shopping — the human on screen is the "you". This is why the same clip is right here and wrong on L2. `split` keeps the host present under the money line. |
| 6 | Let agents do the legwork. You keep the pay click. | 15.750 → 19.340 | `glyph_delegation.mp4` | 0.0 | `full` | The card is the line: YOU → AGENT → CART, with the magenta PAY node under a fingertip. `full` is mandatory — it is a native 1080×1920 composition and a `split` pane would crop 432px off each end (§1). |
| 7 | Amazon can still block agents in its terms. | 19.340 → 22.630 | `v2_host.mp4` (host layer) | — | `host` | The episode's single most important honesty line (script.md judgment call 3). No stock image can illustrate "terms of service" without implying a document we have not sourced; the host saying it to camera is the honest grammar. |
| 8 | Agents do the work, humans approve. This video too. | 22.630 → 26.370 | `broll/checkout_human.mp4` | 1.0 | `split` | The line names *humans approve*; the clip's required content is a human hand completing the payment action. Literal match, and it re-states L6's payoff visually. |
| 9 | I unpack one A I story every single day. | 26.370 → 29.440 | `v2_host.mp4` (host layer) | — | `host` | CTA, to camera, full-frame — hands off cleanly to the outro sting (§7). |

**Mode rhythm:** `split split | full | host | split | full | host | split | host`.
No mode runs more than the merged L1–L2 hold, and the three `host` full-frames land on
the caveat, the counterweight and the CTA — the three lines whose credibility depends
on a face.

**Caption position moves with mode** (`Short.tsx:453`): `split` beats put captions at
`bottom:47%` (just above the pane seam); `full`/`host` beats at `bottom:21%`. Overlay
assets must use the per-beat value, not a single number.

---

## 4. SECONDARY HOOK — measured **MISS**, with the re-cut

**Gate:** the beat carrying *"the court said YOU are the one shopping"* must start in **[14.0, 16.0]s**.

**Measured on the locked script: ❌ MISS. Beat 5 starts at 13.39 / 12.88 / 13.39s
(mean 13.22s) across three renders — 0.61–1.12s below the floor, in 3 of 3. The miss
is systematic, not jitter.**

Two things make this harder than a wording tweak, both measured here:

1. **Line 1 alone jitters by up to 1.45s** across renders of byte-identical text
   (4.17s → 5.62s observed). Every downstream boundary sits on top of that. Per-line
   spread on the locked script runs 0.21–1.02s.
2. **`<break>` is not a deterministic lever.** RECUT-C raised the pre-hook break from
   0.4s to 1.3s expecting a clean +0.90s shift; the measured line-4 duration moved
   only **+0.89s of the +0.90s nominal**, but the surrounding lines re-timed enough
   that the gate still failed 1 of 3. ElevenLabs re-reads the whole utterance; silence
   does not buy a fixed offset.

Consequence: **no fixed wording lands both gates deterministically.** The correct fix
is a re-cut *plus* a take gate.

### Recommended: **RECUT-B** + a take gate

Two edits to `script.md`, one before the hook and one after it, so the total stays in band:

| line | from | to | why |
|---|---|---|---|
| 4 | "The case is not over." | "The case is not over. **It goes back to a lower court.**" | Adds ~1.6s *before* the hook. Not filler — this is **C3/C2** (remand to N.D. Cal.), high-confidence, which `script.md` cut only for line budget and flagged as restorable. |
| 8 | "Agents do the work, humans approve. **This video too.**" | "Agents do the work, humans approve." | Pays for it *after* the hook (−0.94s measured). The spoken aside is not the disclosure mechanism — `containsSyntheticMedia=true` + the description carry it, and #28 shipped with no spoken disclosure at all. |

Measured (n=3): **L5 mean 14.94s** — dead centre of the window — **total mean 29.56s**, in band.
Joint pass 2/3 per render.

**Take gate (this is the part that actually closes the gate).** `vo_master` must
render, measure, and accept only if **both** hold:

```
26.0 <= total <= 30.0            AND            14.0 <= line_starts[4] <= 16.0
```

else **re-roll the render** (≈$0.02, ~8s). At RECUT-B's measured 2/3 accept rate,
P(pass within 3 rolls) ≈ **96%**. RECUT-A must not be used: its band gate failed 3/3
(mean 30.93s), so no number of rolls can save it.

### If the script stays locked (reviewer's call)

Then record the miss honestly rather than redefining the gate. Mitigation, not a fix:
the *spoken payoff word* "YOU" lands at **14.42 / 13.84 / 14.18s** — i.e. the word
itself is at or inside the window even when the beat boundary is not. Pinning the
emphasis overlay to the word onset rather than the line start (Ep25 `cta_endcard`
precedent) puts the on-screen hook in the window while the beat stays early.
`beat_map.json.secondary_hook.locked_mitigation` carries the numbers.

---

## 5. Clip durations and in-point safety

**Rule (hard):** `in_point + beat_duration + 0.5 <= clip_duration`. A beat that runs
past its source clip freezes on the last frame; the 0.5s tail is the margin that
absorbs VO jitter between this map and the shipped take.

| clip | duration | source | in-pt | beat(s) | beat dur | required min | status |
|---|---|---|---|---|---|---|---|
| `outro/outro_sub_comment.mp4` | **3.800s** (1080×1920, 30fps, audio ✅) | **ffprobe, measured** | — | outro | — | — | ✅ exists |
| `ep28/v2_host.mp4` (reference for §6) | **30.444s** | **ffprobe, measured** | — | — | — | — | ✅ reference only |
| `chat_mock_hold.mp4` | **build to ≥ 9.0s** | this map *specifies* it | 0.0 | 1+2 (merged) | 8.290 | 8.290 + 0.5 = **8.79** | ⏳ not built |
| `glyph_delegation.mp4` | **build to ≥ 4.3s** | this map *specifies* it | 0.0 | 6 | 3.590 | 3.590 + 0.5 = **4.09** | ⏳ not built |
| `v2_host.mp4` | **= VO total** (29.440 ref) | driven by the whole VO | — | 4, 7, 9 + all `split` panes | 29.440 | full length, §6 | ⏳ not rendered |
| `broll/courtroom_ruling.mp4` | **MEASURE** | Pexels/Pixabay | 1.5 | 3 | 3.300 | **≥ 5.30s** | ⏳ not fetched |
| `broll/agent_shopping.mp4` | **MEASURE** | Pexels/Pixabay | 2.0 | 5 | 2.360 | **≥ 4.86s** | ⏳ not fetched |
| `broll/checkout_human.mp4` | **MEASURE** | Pexels/Pixabay | 1.0 | 8 | 3.740 | **≥ 5.24s** | ⏳ not fetched |

**⚠ Honest scope note.** The contract says *"probe each file with ffprobe and write the
durations in."* Only two of the eight clips exist at the time this asset ran — the
episode's media is queued behind it. Everything measurable **is** measured; the rest
carries a computed minimum and a hard assert instead of a guess. Two of the three
unbuilt clips (`chat_mock_hold`, `glyph_delegation`) are not really blocked: their
plan specs read their duration *from this map*, so the numbers above are the
authoritative spec, not a placeholder. Only the three Pexels durations are genuinely
unknown, and `fetch_broll.py` already reports `duration_s` per candidate — the
assembler asserts against the table above and rejects any candidate under the minimum.

Assembler assert (run before `--dry`):

```bash
python3 - <<'PY'
import json, subprocess
BM = json.load(open("channels/claude-tricks/assets/ep_amazon_perplexity/beat_map.json"))
A  = "channels/claude-tricks/assets/"
for b in BM["beats"]:
    if not b["src"]: continue
    d = float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=nw=1:nk=1", A+b["src"]], capture_output=True, text=True).stdout)
    need = b["in_point"] + b["dur"] + 0.5
    print(("OK  " if d >= need else "FAIL"), b["src"], f"dur={d:.2f} need>={need:.2f}")
    assert d >= need, f"{b['src']}: {d:.2f}s < {need:.2f}s (in {b['in_point']} + beat {b['dur']} + 0.5)"
PY
```

---

## 6. HOST CLIP OFFSETS — measured lag and the shifted-copy path

**⚠ Structural finding: `newsSplit` takes ONE full-length host clip, not two.**
`build_ep_v2.py:1284-1288` calls `host_clip("v2_host", 0, total)` — a single HeyGen
render driven by the **entire** VO — and `Short.tsx:408-439` plays it as one
continuous element with **no `startFrom`**. The plan's `host_hook_clip` (lines 1–2) and
`host_payoff_clip` (final lines) cannot satisfy this: the host pane is on screen during
every `split` beat, so a clip covering only the head and tail leaves the bottom pane
wrong from 8.29s to 26.37s, and a concatenation of two slices would not be
timeline-aligned. **Render one clip driven by the whole VO** → `v2_host.mp4`
(~29.4s ≈ 44 HeyGen credits ≈ $1.10 at the ~1.5 cr/s rate in the account notes).

**Measured lag on this exact code path.** Both shipped `newsSplit` episodes were
measured with `lipsync_align.py measure ... --at 0.0`:

| episode | clip | lag | corr |
|---|---|---|---|
| #28 | `ep28/v2_host.mp4` (30.444s) | **+23.0 ms** | 0.9994 |
| #29 | `ep29/v2_host.mp4` (33.240s) | **+23.0 ms** | 0.9993 |

Identical to the millisecond across two independent renders, with a near-perfect
correlation peak. That is not a HeyGen creative lead — **+23ms ≈ 1024 samples at
44.1kHz, i.e. AAC encoder priming delay** on the returned mp4. It is also *below* the
~45ms audio-ahead perceptual threshold quoted in `lipsync_align.py`, which is why #28
and #29 shipped clean without a shift. The 123ms/234ms leads recorded on Ep25 were on
**short sliced** renders (`rec:` beats), a different path.

**Procedure — mandatory, because the lead is per-render:**

```bash
# 1. render RAW (never straight to v2_host.mp4)
#    -> channels/claude-tricks/assets/ep_amazon_perplexity/v2_host_raw.mp4
# 2. measure against the shipped master VO
python3 scripts/lipsync_align.py measure \
    channels/claude-tricks/assets/ep_amazon_perplexity/v2_host_raw.mp4 \
    channels/claude-tricks/assets/ep_amazon_perplexity/vo_v2.wav --at 0.0
# 3a. |lag| <= 0.045 and corr >= 0.95  -> copy raw to v2_host.mp4, record the number
# 3b. |lag| >  0.045                   -> cut a SHIFTED COPY and write it to v2_host.mp4
python3 scripts/lipsync_align.py cut \
    channels/claude-tricks/assets/ep_amazon_perplexity/v2_host_raw.mp4 \
    --lag <MEASURED> --dur <VO_TOTAL> \
    --out channels/claude-tricks/assets/ep_amazon_perplexity/v2_host.mp4
# 3c. corr < 0.85 -> the render is not a pure time-shift. Re-render; do NOT in-point it.
```

**Why the shifted copy must overwrite `v2_host.mp4` rather than be pointed at:**
`build_ep_v2.py:1368` sets `spec["host"]` from `full_host` directly and `Short.tsx`
gives the host layer no `startFrom`. **There is no in-point on the host layer at all**
— the only place a correction can live is the file itself. (This is also why the ban on
`@0.00` against a raw HeyGen file is not expressible here as an in-point: the file
*is* the in-point. Recorded lag goes in `beat_map.json.host.measured_lag_s`, and
`v2_host.mp4` must be the shifted or verified-clean copy, never the untouched render.)

`build()` only synthesizes when the file is absent, so dropping a verified
`v2_host.mp4` into the episode directory makes the builder reuse it.

---

## 7. Outro

`outro: True`. Sting = `assets/outro/outro_sub_comment.mp4`, **measured 3.800s**,
1080×1920, 30fps, audio present. Reused as-is — never re-rendered (Playbook §15
bookends hygiene). Appended after the master pass, music bed continuing with its
fade-out re-derived at `2.6s` (the untrimmed default).

**Nothing needs to survive it.** `endcard_planned: false` in the plan, so there is no
`endcard` block, no `over_outro` composite, and no `outro_dur` trim — the sting plays
its full 3.800s and its own SUBSCRIBE/COMMENT chips are the last thing on screen, which
is the intended ending for a non-keyword episode. (`outro_dur` exists only to cut the
sting before its generic COMMENT chip when an episode carries its own comment-keyword
card — not this one.)

**Final runtime:** VO total + 3.800s ≈ **33.2s** on the reference take.

### 7.1 Merged-beat gotcha

`build_ep_v2.py:1305` merges *consecutive byte-identical* beat strings into one
segment. Beats 1 and 2 are identical, so the spec emits **8 segments for 9 lines** —
one 8.290s `chat_mock_hold` segment. This is intended (a continuous hold reads better
than a cut to itself), and it is why `chat_mock_hold.mp4` is specced at ≥9.0s rather
than the ~5–6s its plan entry guessed. Chips and emphasis are unaffected: both are
computed from per-line `line_starts`, not from segments.

### 7.2 Why there is no overlay beat

Restating the §1 limitation for the assembler: a transparent PNG that must sit *over*
a beat cannot be expressed in the spec. If one becomes necessary it is an ffmpeg
composite in `build()` (the `endcard` block at `build_ep_v2.py:1418-1439`), never a
beat.

---

## 8. Hard constraints for the assembler

1. **Episode key.** `build()` resolves assets to `assets/ep{ep}`. Register this episode
   as **`EPISODES_V2["_amazon_perplexity"]`** so `A` resolves to
   `assets/ep_amazon_perplexity` (renders → `ep_amazon_perplexity_v2.mp4`, spec →
   `episodes/_amazon_perplexity.v2.json`). Any other key silently builds against an
   empty directory and re-synthesizes the VO and the host clip from scratch.
2. **VO filenames.** `build()` reads `assets/ep_amazon_perplexity/vo_v2.wav` and the
   sidecar `vo_v2.words.json`. The `vo_master` asset is planned as `vo.mp3` +
   `vo.words.json` — it **must** land (or be copied) as `vo_v2.wav` / `vo_v2.words.json`,
   or the builder will bill a second ElevenLabs render and every timing here goes stale.
3. **No pre-baked chart images in a 9:16 pane.** Any numeric / price / comparison visual
   is a native `stat:` StatBars beat with sourced numbers (Playbook §4).
   **This episode plans NO stat beat**, deliberately: `research.json` contains no
   sourced number worth charting — the story is a holding, not a metric. The available
   numerals (case filed Nov 2025, injunction Mar 2026, ruling Aug 4 2026, slip op. pp.
   15/21) are dates and citations, which belong in the cover `sub` and the description,
   not in bars. If a later research pass surfaces a real comparable pair, add it here as
   `stat:<name>|full` with `subtitle` carrying the source and date — never as an image.
4. **No `@0.00` on a raw HeyGen file.** See §6: on `newsSplit` the host layer has no
   in-point, so compliance means `v2_host.mp4` is itself the measured-clean or
   shifted copy, with the lag recorded.
5. **No Amazon or Perplexity screenshots, logos, lookalike colours or product UI**
   anywhere in any beat (plan-level hard rule). Every non-host beat here is either
   in-house type or licence-clean stock.
6. **`steps` is not optional.** `build_ep_v2.py:1342` iterates `cfg["steps"]` without a
   default — the `step_chips` asset must deliver at least an empty list.

---

## 9. Re-derivation (run this, do not trust the numbers above)

Every timing in this document is a reference take. Before `--dry`, regenerate
`beat_map.json`'s clock from the shipped sidecar using the builder's own boundary
logic (`build_ep_v2.py:1223-1255`):

```bash
python3 - <<'PY'
import json
A   = "channels/claude-tricks/assets/ep_amazon_perplexity/"
W   = json.load(open(A + "vo_v2.words.json"))
BM  = json.load(open(A + "beat_map.json"))
def is_break(w):
    r = w["w"].lower().strip()
    return (r.startswith("<break") or r.startswith("time=") or r in ("/>", "/")) \
        and abs(w["end"] - w["start"]) < 1e-3
bounds = sorted({round(w["start"], 3) for w in W if is_break(w)})
caps   = [w for w in W if not is_break(w)]
assert len(bounds) == 8, f"{len(bounds)} break markers != 8 — builder would fall back to word-count timing"
total  = caps[-1]["end"]
durs, p = [], 0.0
for b in bounds: durs.append(round(b - p, 3)); p = b
durs.append(round(total - p, 3))
starts, a = [], 0.0
for d in durs: starts.append(round(a, 3)); a += d

hook = [c for c in caps if c["w"] == "ROUND"][0]["end"]
print(f"total          {total:.3f}   gate 26-30      {'OK' if 26 <= total <= 30 else 'FAIL'}")
print(f"hook head ends {hook:.3f}    gate <=1.5      {'OK' if hook <= 1.5 else 'MARGINAL'}")
print(f"L5 (2nd hook)  {starts[4]:.3f}   gate 14.0-16.0  {'OK' if 14 <= starts[4] <= 16 else 'FAIL -> re-roll the VO take (beat_map §4)'}")
print(f"derived cover.until (hook+0.6) {hook + 0.6:.2f}  -> PINNED 3.0 (Playbook §13 floor)")
for i, (s, d) in enumerate(zip(starts, durs)): print(f"  L{i+1}: {s:7.3f} -> {s + d:7.3f}  ({d:.3f})")

BM["line_starts"], BM["seg_durs"], BM["vo_total_s"] = starts, durs, total
BM["secondary_hook_s"] = starts[4]
BM["timing_state"] = "MEASURED_SHIPPED"
for i, b in enumerate(BM["beats"]):
    b["start"], b["dur"] = starts[i], durs[i]
# merged beats + chip/emphasis windows follow line_starts, so recompute those too
for w in BM["chip_windows"] + BM["emphasis_windows"]:
    w["t0"] = starts[w["line_a"]]
    w["t1"] = round(starts[w["line_b"]] + durs[w["line_b"]], 3)
    if w.get("src_follows_timeline"): w["src_t0"], w["src_t1"] = w["t0"], w["t1"]
    elif w.get("src_in_point") is not None:
        w["src_t0"] = round(w["src_in_point"] + w["t0"] - starts[w["seg_line"]], 3)
        w["src_t1"] = round(w["src_in_point"] + w["t1"] - starts[w["seg_line"]], 3)
json.dump(BM, open(A + "beat_map.json", "w"), indent=1)
print("\n>> beat_map.json re-derived from the shipped take")
PY
```

Then re-probe chip corners **against the refreshed windows** — Ep26's rule: a chip
scored on a padded window is scored on frames the episode never shows.

---

## 10. Windows for the overlay assets (probe these, not padded ones)

`chip_windows` and `emphasis_windows` in `beat_map.json` carry, for each candidate:
the **timeline** window `[t0,t1]`, the **source clip** and its **`[src_t0, src_t1]`** —
the exact seconds `probe_frames.py corner` must score.

Useful property of `newsSplit`: the host layer is timeline-aligned (no `startFrom`), so
for any `host` beat **`src_t0 == t0`**. For a `rec:` beat the source window is offset by
the in-point: `src_t0 = in_point + (t0 − beat_start)`.

| id | label | lines | timeline | probe target | notes |
|---|---|---|---|---|---|
| W1a | PRELIMINARY INJUNCTION VACATED — CASE CONTINUES | 3 | 8.290–11.590 | `broll/courtroom_ruling.mp4` 1.50–4.80 | **Mandated** by `research.json compliance.required_chip`. Must sit in dead space, never over the quoted holding. |
| W1b | (same chip continuing) | 4 | 11.590–13.390 | `v2_host.mp4` 11.590–13.390 | Chip spans two segments ⇒ **probe both**; a corner that is clean over the b-roll may sit on the host's face. |
| W2 | AMAZON'S TERMS STILL APPLY | 7 | 19.340–22.630 | `v2_host.mp4` 19.340–22.630 | Reinforces the counterweight line. 3.29s ≥ the 1.5s minimum hold. |
| W3 | *(optional)* AN AGENT, BANNED | 1–2 | **3.000**–8.290 | `chat_mock_hold.mp4` **3.00**–8.29 | ⚠ Window **starts at 3.0, not 0.0**: the cover holds until 3.0s, so scoring 0.0–3.0 scores frames behind the poster. Likely dropped — the mock carries its own header label. |

No chip on beats 5, 6, 8 or 9: 6 is an authored card that states its own point (the
#28 precedent), 5 is the secondary hook and must stay uncluttered, 9 is the CTA.

| emphasis | text | line | timeline | live underneath | recommendation |
|---|---|---|---|---|---|
| E1 | *the court said YOU are the one shopping* | 5 | 13.390–15.750 | `agent_shopping` `split` — renders at `top:38%`, inside the top pane | **Keep.** The one line worth a second text system. Consider pinning `start` to the measured onset of the word "YOU" (§4) rather than the line start. |
| E2 | *agents do the legwork — you keep the pay click* | 6 | 15.750–19.340 | `glyph_delegation` `full` — the card's own node labels | **Drop.** The card already says it in type; a serif line over it is the crowding the emphasis spec warns against. |

Caption collision to check: on `split` beats the caption sits at `bottom:47%` and
emphasis at `top:38%` — roughly 15% of frame height apart. Verify on a real frame.

---

## 11. Open items for review

1. **The secondary-hook gate fails on the locked script (§4).** Needs a decision:
   apply RECUT-B + the take gate, or accept the miss with the word-onset mitigation.
   This is the one thing that cannot be resolved inside the beat map.
2. **`host_hook_clip` / `host_payoff_clip` are the wrong shape for `newsSplit` (§6).**
   They should be superseded by one full-length `v2_host.mp4`.
3. **`vo_master` must land as `vo_v2.wav` / `vo_v2.words.json`** (§8.2), not `vo.mp3`.
4. Three b-roll durations are still unmeasured (§5) — asserted, not assumed.
