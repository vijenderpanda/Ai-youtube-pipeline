# Shorts: the production method we actually practise, and the gates the factory app must enforce

**Written 2026-08-20, from one long session that took the `claude-tricks` build franchise from
tip #1 through to an armed franchise entry #4 and back around through real YouTube analytics.**

Audience: a sibling session redesigning the factory app. This is not a description of the app as
built — it is a description of **what the work actually needs**, derived from failures that really
happened, most of which the app could have caught and none of which it did.

Read with: [`docs/PRODUCTION-PLAYBOOK.md`](PRODUCTION-PLAYBOOK.md) (craft standards),
[`remotion-studio/src/cookbook/COOKBOOK.md`](../remotion-studio/src/cookbook/COOKBOOK.md)
(component contract), `channels/claude-tricks/BRAND-BIBLE.md` (locked format).

---

## 1. The loop, as it actually runs

Every short in this franchise went through the same eight stages. The app today supports stages
4 and 7 well, 6 partially, and **nothing else**.

| # | Stage | Where it lives now | What the app should do |
|---|-------|--------------------|------------------------|
| 1 | **Read fresh analytics**, pick the shape | pasted into chat by hand | surface the per-video panel + channel medians next to the calendar row being planned |
| 2 | **Capture real tape** (Playwright → claude.ai) | `channels/claude-tricks/rec_*_app.py` | register the capture script + its `PROMPT` constant as an asset of the episode |
| 3 | **Pick / invent a cookbook component** | `remotion-studio/src/cookbook/` | the composition designer already does this — see §5 |
| 4 | **Author the episode** (registry **and** mirror) | `EPISODES_V2` + `episodes/<ep>.v2.json` | **make the mirror non-optional** — see §3.1 |
| 5 | **Render → QC** | `build_ep_v2.py` + manual sheets | run the automated gates in §4 and show the results on the row |
| 6 | **Sync unarmed for review** | `scripts/sync_preview.py` | it must be impossible to review a superseded cut — see §3.6 |
| 7 | **Arm** | `scripts/finalize_episode.py` | show exactly what will be uploaded *before* upload — see §3.8 |
| 8 | **Analytics → back to 1** | `scripts/yt_retention.py`, `network_stats.py` | close the loop automatically |

The franchise, in order, so the evolution is legible:

| Ep key | Title | Outcome |
|--------|-------|---------|
| `_artifacts` | I Built A Working App By Typing One Line | produced, synced unarmed |
| `_habit` | I Built A Habit Tracker By Typing One Line 🔥 | **armed** `Ag9tBHbyrbo` — the data point everything below is calibrated on |
| `_wheel` | I Built A Dinner Decider By Typing One Line 🎰 | produced, synced unarmed; invented `SpinWheel` |
| `_style` | Stop DESCRIBING The Style — Paste 1 Example 🎯 | produced, then **killed by VJ**. Abstract "Stop X" hook, no thing appears. Do not revive |
| `_game` | I Built A Reaction Game By Typing One Line ⚡ | **armed** `73VwXn2DbbY`; invented `ReactionMeter`; took **ten** render passes |

---

## 2. What the analytics actually taught us

From `Ag9tBHbyrbo` (tip #2), the only franchise entry with mature data:

| Metric | This video | Channel typical | Read |
|--------|-----------|-----------------|------|
| Views | 221 | 8–70 | the build franchise wins **distribution** |
| CTR | **4.6%** | ≤0.76% | **the title+thumbnail formula is the single strongest lever on this channel** |
| Stayed to watch | 24.2% | ~20% | the one-line hook works in-feed |
| Avg % viewed | 40% | ~37% | fine, but below the 50.9% *tip* median |
| Likes / comments | **0 / 0** | — | the engagement ask was never in indexed text |
| Drop-off | **0:15–0:25** | — | mapped exactly onto frozen still-holds |

**Four rules fall out of this, and they are the ones to encode in the app:**

1. **Title formula is proven; do not improvise on it.**
   `I Built A [Thing] By Typing One Line [emoji]`, **44 characters**. Both 4.6%-CTR titles are
   44 chars. The app should show character count against the channel's best-CTR titles.
2. **The searched noun must be in the title and tags, not just the voiceover.**
   `_game` shipped a first cut titled "Reaction **Test**" while the thing built was a *game* —
   `game` appeared only in the VO, i.e. nowhere the algorithm reads. Caught by VJ, not by any
   automated gate. **The app should diff title+tags against the episode's own VO and prompt for
   nouns present in one and missing from the other.**
3. **Frozen frames are the measured retention killer.** The 0:15–0:25 drop-off sat on two frozen
   still-holds. Every subsequent episode is built with live motion in that window; see §4.2.
4. **A CTA that is only in the picture earns nothing.** Zero comments on 221 views with a
   full-screen end card asking the question. The ask must ALSO be in the description
   (`desc_cta`, opt-in, added to `finalize_episode.build_description` 2026-08-20) and in a
   pinned comment. And it must be answerable in ~2 seconds — *"what's your reaction time?"*
   beats *"what should I build next?"*, which is homework.

**Statistical discipline** (learned the hard way from a 21-agent analysis): at n≈200, zero
comments is *expected* (base rates ≈0.065% → P(zero)≈0.89), and an AVP delta of ±1.3pp is ~0.65
SE. The franchise's own spread is 10× on near-identical structure. **Do not re-cut a format on
one video's noise.** The app should show confidence intervals, not bare deltas.

---

## 3. Pipeline defects found this session — each one is an app requirement

Every item below shipped, or nearly shipped, something wrong. They are ordered by how badly the
app failed to prevent them.

### 3.1 The metadata mirror was optional, so an episode shipped titled `ep_habit_v2_outro.mp4`
`EPISODES_V2[ep]` drives **rendering**; `episodes/<ep>.v2.json` drives **YouTube metadata**.
Nothing enforced that both exist or that they agree. Tip #2 went live to real subscribers with a
filename as its title and a junk description.
→ **Gate: refuse to arm unless the mirror exists AND its title/tags/lines are byte-identical to
the registry.** This is a five-line check that would have prevented a public embarrassment.

### 3.2 The VO cache keyed on file existence, so edited scripts shipped stale audio
`if not os.path.exists(vo): synth(...)`. Editing a script line and rebuilding silently reused the
old voice track: a master went out showing **269ms on screen while the voice said "two hundred and
thirty one"**.
→ **Fixed** — now content-addressed via `vo_v2.sig` (sha256 of the joined lines); a changed hash
re-synthesizes and sets `FACTORY_REBUILD_HOSTS=1`, because host clips are cut from VO slices.
→ **Corollary the app must know: regenerating the VO reshuffles EVERY beat boundary.** TTS
duration varies run to run. Any hardcoded source timestamp must be re-asserted afterwards.

### 3.3 `Short.tsx` dropped a frame at beat boundaries — latent in *every* episode ever rendered
`from` was rounded off the cumulative start, `durationInFrames` off the beat's own duration, and
`round(a)+round(b) ≠ round(a+b)`. On `_game`, beat 2 ended at frame 435 while beat 3 began at 436 —
frame 435 was covered by **no sequence** and rendered blank. The other drift direction draws two
beats at once.
→ **Fixed** — each beat's end derives from the next beat's rounded start. Invisible unless you
step frame-by-frame at a cut, which is why it survived for months.

### 3.4 `ScreenStage` sheen was one-shot, so still footage went truly dead
A flat-colour app screen does not move. Once the entry sweep finished at 1.5s the frame was
literally static — measured **0.04** motion at 0:21–0:22, inside the exact window analytics flags.
→ **Fixed** — the sweep repeats on a slow cycle (reset invisible; it is off-canvas at both ends).

### 3.5 `GenerativeUI` hardcoded 56px prompt type, so real prompts overflowed
Real typed prompts are paragraphs, not slogans. → now sizes by length.

### 3.6 Re-syncing a preview left the board serving the **previous** cut
`factory_assets` has a unique constraint on `(calendar_id, asset_key, version)` and
`sync_preview.py` hardcoded `version: 1`. Every re-sync 409'd, and the failure was silent in the
way that matters: `factory_calendar.preview_path` advanced to the new file while
`factory_assets.preview_master` still pointed at the old one. **A reviewer would have opened a cut
containing a confirmed blocker while the log said "stamped — review it on the factory app".**
→ **Fixed** — versions bump per asset key; the warning now says a *stale* preview may be served.
→ **App requirement: the board must render from ONE resolved pointer, and show which render tag
and file it is showing.** Two tables that can disagree about "the current cut" is a design bug.

### 3.7 Re-syncing did not patch the title
`sync_preview --calendar-id` updated the preview file but never the row's `title`, so a title
correction made after the first sync **never reached the board the reviewer reads**. Hit for real
on `_game` minutes after VJ asked for the title fix. → **Fixed** (title + brief now patched).

### 3.8 `finalize_episode.py --dry` performs a REAL YouTube upload
It only skips the DB sync. Confirmed at source, independently, twice. It has already created an
unwanted scheduled video once. Use `--skip-arm` for a true dry run.
→ **App requirement: a "preview what will be published" view that touches nothing** — title,
description, tags, thumbnail, schedule, rendered from the same code paths as the real arm.

### 3.9 Other traps worth encoding
- `outro_cta: "auto"` computes "tomorrow" from the **calendar row's `planned_date`**, not from
  `--schedule`. Mismatch ships a wrong day in the spoken outro.
- `finalize` **re-renders** before uploading, so the armed file is a fresh encode, not the exact
  bytes reviewed. Content is reproducible; the bytes are not.
- Thumbnail lookup is `renders/thumb_ep<ep>.jpg`. `_game` had none and would have armed with a
  YouTube auto-pick — on the channel where thumbnails drive a 6× CTR advantage.
  → **Gate: refuse to arm without a thumbnail on a channel whose CTR depends on one.**
- `"steps": []` must be present-but-empty; the key's absence raises `KeyError`.

---

## 4. The QC that actually catches things

Nine self-directed QC rounds declared the `_game` cut clean three times while real defects sat in
it. What worked was **automated measurement plus adversarial review**, not eyeballing.

### 4.1 Mechanical gates (cheap, run every build)
```
frame-by-frame contact sheet, sized to the frame count      # the only thing that catches cut-level bugs
per-second motion profile                                    # dead seconds, esp. 0:15-0:25
per-frame colour-transition scan of the source tape          # ground truth for what is on screen when
assert every ScreenStage from + duration <= tape duration    # after ANY vo change
assert beat boundary frames are not blank                    # §3.3
EBU R128 integrated loudness == -14 LUFS                     # target, verified per master
mirror == registry (title, tags, every line)                 # §3.1
every prompt surface == the capture script's PROMPT constant # §6.2
spoken numbers == numbers visible on screen at that timestamp
```

### 4.2 The motion profile is the retention gate
Per-second mean frame difference. Anything under ~0.15 is a dead second. On the shipped `_game`
the dead seconds are the outro cards (by design) and two settled beats with dense text. The
0:15–0:25 window went from a floor of **0.04 → 0.12**, and the 21–22s dead spot from **0.06/0.04
→ 0.33/0.98**. **The app should plot this next to the retention graph of the previous episode.**

### 4.3 Adversarial multi-agent QC is worth its cost
Two rounds over the `_game` master:

| Round | Raised | Survived refutation |
|-------|--------|---------------------|
| v5 | 31 | 6 |
| v8 | 30 | 4 |

~85% of findings were correctly killed. The shape that works: **N independent lenses**
(truth / frames / sync / craft / publish-readiness) → **one refuter per finding, instructed to
default to `refuted=true` when uncertain**. Both rounds found blockers that nine rounds of my own
checking had missed, including one I had personally measured and cleared.

**Two lessons about the reviewers themselves:** a refuter argued the mistitled-episode precedent
"never happened", citing the live API title — true only because the video had been patched hours
earlier. *A fixed bug erases its own evidence.* And a finder reported "a single black frame" that
was neither black nor where it said — but something **was** broken there, two layers deeper. Judge
the claim, not the description.

---

## 5. Wow-mechanics → cookbook: how components get made

Source: the "Wow Mechanics" research artifact (claude.ai `b9570dbc`), §C *"what survives the port
to Remotion"*. Ports cleanly to a frame clock:

- **Plate 01** refractive glass — *"the trick is the inset highlight, not the blur"*; bake the blur
- **Plate 03** kinetic type — per-glyph **26ms** stagger, `rotateX(-82deg)→0`, `scaleX 1.7→1`
- **Plate 05** element morph — interpolate a bounding box, do not cut
- **Plate 06** settle — `cubic-bezier(.2,.9,.25,1)`
- **Plate 07** depth without 3D — layers at 0.2/0.5/0.9, scripted camera, sheen, grain
- **Plate 08** generative UI — *"tool call → component, NOT tokens → prose"*
- **Plate 09** numbers that arrive — `stroke-dasharray → dashoffset 0`; *"the single highest-value
  block for a data-driven short"*

Does **not** port: magnetic pull (no cursor), scroll-driven CSS.

Invented this session: **`SpinWheel`** (decision surrendered to chance, `_wheel`) and
**`ReactionMeter`** (Plate 09 — WAIT → hard green snap → a number arriving on a drawn ring,
`_game`). Plus `OutroGlass` (the sting), `ScreenStage` (real tape staged), `GenerativeUI`,
`IdeaKinetic` (authored kinetic text replacing running captions), `AuroraBed` (shared ground).

**Contract**: three exports (`type <Name>Props`, self-animating `const <Name>` off
`useCurrentFrame`, `const <name>Demo`), registered in **four** places — `components.tsx` map,
`Root.tsx` composition, `registry.ts`, `COOKBOOK.md`. Props must be JSON-safe (`build_ep_v2`
feeds `--props` as JSON). Wire into an episode as a `cook:<Id>` beat with props under
`cfg["cookbook"][<Id>]`; `cook:<Id>#<variant>` for multiple instances.

**House style** (VJ rejected the first attempt as *"fat buttons, weird fonts"*): frost
`linear-gradient(160deg, rgba(#0a0b12,.34), rgba(#0a0b12,.50))`; baked refraction
`blur(26px) saturate(200%) brightness(1.08)`; 3px caustic top edge; inset hairline
`rgba(#fff,.55)`; MONO eyebrow 24/ls6; Anton display ls −1; hairlines `rgba(#fff,.12)`;
**no pills**; left-aligned, pad 60.

---

## 6. Honesty rules — non-negotiable, each from a real near-miss

### 6.1 Automated capture must not claim human performance
Colour-polling detects the green cue in **~36ms** — faster than any human (floor ~100ms, common
benchmark ~250ms). The first clean take literally recorded 36ms, which makes a *correctly working*
app look broken and would have been a false personal claim. → `--tap-delay` puts the number in the
human band, and the VO describes what the app **measures** rather than bragging a reflex.

### 6.2 Every prompt surface must equal the prompt actually typed
`_game` shipped a card quoting *"build me a reaction time game, full screen"* — **never typed**.
The real tape four seconds later showed the actual 38-word prompt, and the outro branded that one
"THE EXACT PROMPT". The cut contradicted itself, in the flattering direction. Verifying **one**
surface proves nothing about the others: diff **all** of them against the capture script's
`PROMPT` constant, character for character.

### 6.3 Designed components restate, they never replace
A cookbook component may mirror a real result exactly (same number, same winner) as a stylized
restatement of what the tape then proves. It may never be the proof itself.

### 6.4 Only the last round of a multi-round capture has a long tail
The capture re-arms ~3.2s after each tap, so every result except the final one is on screen for
only ~3s. Pointing a payoff beat at an earlier round runs it into the next round — this shipped a
beat showing **271ms under a voice saying "two hundred and thirty one"**.

---

## 7. What I would build into the app first

Ranked by damage prevented per unit of work:

1. **Arm-time gate**: mirror exists + matches registry + thumbnail present + spoken numbers match
   on-screen numbers + every prompt surface matches the capture constant. *(§3.1, §3.9, §6.2)*
2. **One resolved "current cut" pointer**, with the render tag visible on the row. *(§3.6, §3.7)*
3. **"What will publish" preview that touches nothing** — the real title, description, tags,
   thumbnail, schedule. *(§3.8)*
4. **Motion profile + frame-boundary check on every render**, shown beside the previous episode's
   retention curve. *(§4.1, §4.2)*
5. **Title/keyword assistant**: character count vs the channel's best-CTR titles, and nouns present
   in the VO or prompt but missing from title/tags. *(§2 rule 2 — the failure VJ caught by eye)*
6. **Analytics on the planning surface**, with confidence intervals rather than bare deltas. *(§2)*

The through-line: **almost every failure this session was in the path between "I produced it" and
"someone sees it"** — metadata, pointers, captions, titles. That path is the least-tested part of
the pipeline and the one where a silent failure is most expensive. Design the app around it.
