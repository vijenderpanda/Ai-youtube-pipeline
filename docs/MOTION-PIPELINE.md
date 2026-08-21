# THE MOTION PIPELINE — pure-motion Shorts for AI Unpacked

Status: **DESIGNED 2026-08-21, awaiting VJ approval. Nothing built, nothing rendered.**
Origin: VJ supplied 11 reference Shorts as the quality bar with the brief: a new pipeline for
motion-graphics Shorts matched to our niche's idea bucket, every graphic automated or pulled
from AI generators. His diagnosis of the current work, verbatim: "i am not able to understand
anything if muted so we need to level up here."

Method: 11 agents studied one reference each, frame-by-frame off real extracted frames +
scene-cut detection; one distilled the grammar into checkable laws; three designed competing
pipelines (asset-first / template-first / story-first); one synthesized. 16 agents, all evidence
grounded in frames on disk, not memory of the videos.

## The 11 references (studied frame-by-frame, 2026-08-21)

Craft bar — Ravie & Co. (pure motion design):
| video | views | what it proves |
|---|---|---|
| [Anthem](https://youtube.com/shorts/bdG0jy2ogxg) | 394K | causal morph chain, carry-ball through 8 scenes, brand withheld to 85% |
| [Are We Still Friends?](https://youtube.com/shorts/cOsFhMeL0J4) | 17K | exposure-as-music, physics acting, loop-as-payoff |
| ["What You Know" Rhythm Game](https://youtube.com/shorts/Cmm6WZE9WFc) | 8.7K | ZERO cuts in 13.9s — one continuous camera through morphing light geometry |
| [Is Fusion Energy The Future?](https://youtube.com/shorts/u1G655x53Yc) | 5.4K | explainer in pure motion: odometer numbers-as-props, 4-word caption locus, world inversion at 5.0s |
| [Coolest Water Ad](https://youtube.com/shorts/GsmIXc1eGLI) | 4.3K | 3 colors across 10 environments, element-morph transitions, beat grid |

Niche bar — AI-tips content told with motion:
| video | views | what it proves |
|---|---|---|
| [Claude Code Clearly Explained](https://youtube.com/shorts/5G9PAIUs5Pk) (Isenberg) | 442K | cream editorial system, typed prompts as script, re-typeset UIs |
| [10x your Claude with 4 .md files](https://youtube.com/shorts/ovLAIhbk3ek) (Isenberg) | 806K | chapter flips landing defocused->sharp, carry flower, greeked body text |
| [Hermes Agent Explained](https://youtube.com/shorts/ecm2ZUOQSTg) (Isenberg) | 99K | draining $100->$10 gauge, terminal mega-scene, icon illustrations |
| [Weavy AI](https://youtube.com/shorts/cUG0TGwE9-4) (Isenberg) | 55K | missing-checkbox planted at 12s paid at 92%, zoom-through-whiteout |
| [Why Pay For Claude Code](https://youtube.com/shorts/9n827BGeDVc) (100x Engineers) | 55K | 1-3 word chips at 0.4-0.7s cadence, every phrase has a visual twin |
| [Claude Code free 6 months](https://youtube.com/shorts/Npr7ibKFNek) (CodeHype) | 238K | real-desk plate + composited 3D type + word-by-word caption |


---

# PART I — THE MOTION GRAMMAR

# THE MOTION GRAMMAR — Checkable Laws from 11 Reference Studies

Test infrastructure assumed: the ink-delta frame auditor (per-band content change per second), ffmpeg `scdet`, an OCR pass (tesseract) over sampled frames, and basic luma/edge stats. Every law below is stated so a gate can PASS/FAIL a rendered MP4, with the manifest as the only extra input where noted.

---

## UNIVERSAL LAWS (exhibited by all 11)

**U1. NO-DEAD-FRAME.** No region of the frame that carries content may be pixel-static for longer than 1.0s; every "hold" must idle (cursor blink, slosh, drift, ticking).
- Evidence: Fusion (every hold has liquid slosh/odometer/flicker, only the final wordmark rests ~1.5s); 100x (longest true hold ~0.8s); Weavy (payoff held 4.4s *with idle UI motion*); CodeHype (longest zero-motion hold ≈ 0 frames — perpetual handheld drift); Anthem (nothing static >0.4s except the drifting title).
- TEST: ink-delta per band per 1.0s sliding window. FAIL if any window has delta == 0 in every band containing rendered content. Also FAIL the inverse: delta == 0 across the full frame for ≥0.5s.

**U2. VISUAL-TWIN.** Every unit of meaning (VO phrase, claim, number) must have a visible event on screen within ±0.5s — the picture demonstrates, never decorates.
- Evidence: Fusion (caption noun = literal picture, all 23.9s); DeepSeek (every phrase → chip, highlight, or display stack — "if a phrase has no visual twin, the beat isn't done"); CodeHype (PROMISE→RECEIPT→PRODUCT→METHOD, every claim a screenshot-grade artifact); Ravie films have no VO — the event stream IS the meaning.
- TEST (manifest-assisted): for each VO phrase boundary in the timing manifest, require an ink-delta event (band delta above the video's 60th percentile) within ±0.5s. FAIL any phrase with no aligned visual event. This directly detects "wallpaper behind narration."

**U3. CARRY-ELEMENT.** One declared visual element must survive every scene boundary — the muted eye must never re-acquire from zero.
- Evidence: Anthem (white ball through all 8 scenes); Water Ad (bubble→plane→ball→heart in every shot, exit direction = entry direction); Fusion (atom glyph in 4 scenes, glass bracketing the film); smartwater (blue droplet through 4 beats); 100x (prompt bar survives ~8 scenes, asterisk x4); Greg .md (coral flower in every chapter); DeepSeek (whale glyph at 2.3/9.5/32/38.5s); CodeHype (caption word "Anthropic." literally bridges the 10.6s cut; sticker parked at frame edge across shots).
- TEST: manifest declares the carry element + its bbox track. At each detected cut, template-match the element in the last pre-cut frame and first 12 post-cut frames. FAIL any boundary where no declared element appears on both sides.

**U4. CUT-BUDGET.** Hard cuts ≤0.45/s, OR every cut locked to a declared beat grid; scene changes are earned by morph/camera/carry, not free.
- Evidence: Friends 0 cuts/13.8s; Anthem 0.28/s (all flash-frames inside one action); Fusion 2 true cuts/23.9s; 100x 0.12/s; Greg .md 0.17/s; Hermes 0.15/s; CodeHype 0.21/s; DeepSeek 0.41/s; the outlier smartwater runs 1.2/s but on a strict 0.54s (~111 BPM) grid with scenes of exactly 1/2/3 beats.
- TEST: ffmpeg scdet count / duration ≤0.45, else check cut timestamps against the manifest's beat grid (tolerance ±1 frame). FAIL otherwise.

**U5. PREPARED-BOUNDARY.** No scene may simply stop: the outgoing scene accelerates/deforms into the boundary, and the incoming scene lands with a settle (defocus→sharp, overshoot→rest, already-zoomed→pull-back).
- Evidence: smartwater (type stretches + motion-blurs in the last 2–3 frames of every scene); Greg .md (every cut lands defocused, racks sharp in ~0.2s); Weavy (zoom-through whiteout at 12.9s — the bloom IS the next background); Hermes (cut-on-zoom at 29.33s); Anthem (smear-slab at 1.8s IS the next scene's bar).
- TEST: ink-delta in the 4 frames before each cut must exceed the shot's mean delta (exit velocity); Laplacian sharpness in the 6 frames after each cut must be rising (settle-in). FAIL any boundary flat on both sides.

**U6. LOCKED-PALETTE.** At most 5 hue families for the whole film, held without exception; accent colors are rationed to one meaning (red = villain/limit, exactly once or twice).
- Evidence: Water Ad (3 colors, 10 environments); smartwater (3); Friends (5); Fusion (1 brand hue + black + white-as-light); 100x (5 swatches, red reserved for wrong/limit); Weavy (5, "never broken"); Hermes/Greg (5-color paper worlds).
- TEST: k-means on sampled frames' hues (exclude near-black/near-white); FAIL if >6 clusters exceed 2% pixel share across the video, or if the declared accent color appears in >15% of frames.

**U7. WORD-BUDGET + FIXED LOCUS.** Never more than ~6 readable narrator words on screen at once, always at one fixed anchor (≈65–72% frame height, above Shorts chrome); body copy is never real paragraphs.
- Evidence: Fusion (max 4 words, baseline locked at 72% for 23.9s, cap-height 2.5%); CodeHype (1–3 word cards at 68%, ~44 cards); DeepSeek (1–3 word chips at 68–75%); Hermes (2–6 word cards); Anthem (1 word total); Friends (0 words). Greg .md greeks all body text into skeleton bars.
- TEST: OCR per sampled frame — FAIL any frame with >8 narrator-register words (outside declared UI-evidence beats), or if the caption bbox y-center variance across the video exceeds 3% of frame height, or if story text intrudes into the bottom 25% band.

**U8. WITHHELD-PAYOFF.** The opening plants an explicit question/incomplete object; the resolving element first appears at ≥75% of runtime.
- Evidence: Anthem (brand at 85%); smartwater ("got..?" answered at 7.1s/77%); Fusion (brand card at 86%; glass returns at 80%); Weavy (missing third checkbox at 12s paid at 47.5s/92%); CodeHype ($1,000 at 80%); Friends (never resolved at all — the loop is the payoff).
- TEST (manifest-assisted): declared payoff element's first appearance timestamp ≥0.75 × duration. FAIL if it appears earlier or never.

**U9. KNEE-EVENT.** The single loudest visual event of the film must land inside 4–8s — exactly where our measured retention knee is (worst second: 6s).
- Evidence: Fusion (full black→magenta→white world inversion at 5.0s); smartwater (single-frame flicker cluster at 5.5s); Anthem (collapse-to-glyph reset at 3.3s + slice setup by 6.4s); Water Ad (beam→road signature move 3.6–4.2s); Weavy (chapter flip + prompt dive 5.7–8.8s).
- TEST: max full-frame ink-delta within the 4.0–8.0s window must be ≥90th percentile of all per-second deltas in the video. FAIL if the video's loudest second lies at 0–2s (our current habit) with nothing comparable in the knee.

**U10. NUMBER-AS-PROP.** Any number spoken in the VO must exist on screen as a physical object — a gauge, odometer, giant display numeral — not only inside caption text.
- Evidence: Fusion (odometer 800→860→865); Hermes ($100→$10 draining Token-usage bar; "$0" callback; "53" at 40% frame width); DeepSeek (28k stars ring + "0 to 28,000 in a day"); CodeHype ($1,000, "20x" badge shown on the real UI twice).
- TEST: OCR — every numeral token in the VO script must be found on-screen with glyph height ≥4% of frame height within ±1s of being spoken. FAIL per missing number.

---

## CRAFT-TIER LAWS (Ravie only — the aspirational bar)

**C1. EXPOSURE-SCORE.** Luminance is composed like music: frames are allowed to go nearly black between hits; brightness peaks are placed, not ambient.
- Evidence: Friends (mean luma oscillates 29↔92; ~70% of every frame under 10% brightness; brightest moment placed at the 70% mark); Anthem (near-black breath at 6.5–7.2s before the finale); Water Ad (1–2-frame full palette inversions as punctuation).
- TEST: per-second mean-luma series must have σ ≥ 15 (0–255 scale) and at least one 1s window under 25% of peak luma in the middle third. Cheap flat-lit videos FAIL instantly.

**C2. CAUSAL MORPH CHAIN (zero-cut storytelling).** Every scene is physically caused by the previous one — the transition object is disguised as the next scene's first object; cuts effectively don't exist.
- Evidence: Anthem (stick smear IS the metronome bar; 2D squares fall into a 3D ziggurat); Water Ad (bubble folds into plane mid-flight; beam straightens into road); Friends (13.8s, zero cuts, pads passing camera function as wipes).
- TEST: true hard cuts ≤1 per 5s AND every scdet hit is a ≤2-frame flash (next frame resembles previous scene family by histogram distance). This is stricter than U4 and mostly aspirational for us.

**C3. PHYSICS ACTING.** Motion has mass: squash-and-stretch on contact, anticipation before big moves, drawn smear frames, gravity landings — never symmetric tweens.
- Evidence: Anthem (ball pill-squash at 3.1s, apex hang at 4.7s, 3-frame smear slab); Friends (arc-tangent tilt, squash on landing, onion-skin echo plates); smartwater (stamp-then-settle, never spring-bouncy).
- TEST (weak but runnable): track declared hero element; its position trace must show overshoot (≥3% past target then return) on ≥50% of arrivals, and ≥1 deliberate 2–4-frame smear/stretch (aspect-ratio spike) per 10s.

**C4. ONE-SUBJECT-ONE-VERB.** One hero object per frame (35–70% of frame area), one repeated action, one color axis carrying the story; nothing else may move meaningfully.
- Evidence: Friends (single capsule, single verb "leap", white/yellow-vs-red axis carries the entire title); Fusion (one centered hero per scene, scale contrast as storytelling).
- TEST: ink-delta concentration — ≥70% of per-frame delta must fall inside one connected region ≤70% of frame area. FAIL frames where motion is smeared evenly everywhere (our particle/trace habit).

---

## NICHE-TIER LAWS (what the AI-tips channels actually do — cheaper, and sufficient)

**N1. CAPTION-IS-THE-SCRIPT.** The full VO transcript appears as 1–3 word chips advancing every 0.4–0.7s at one anchor — a karaoke *transcript*, not a summary or decoration.
- Evidence: DeepSeek (0.4–0.7s cadence, pill chips); CodeHype (~44 cards over 15s, 2.5 words/s, one card at a time); Hermes (2–6 word two-tone cards synced to VO stress).
- TEST: OCR change-rate in the caption band: text content must change every 0.4–1.0s while VO is active; ≤3 words per chip. FAIL windows >1.5s with unchanged caption during speech.

**N2. DIEGETIC PROOF.** Claims are shown as real, legible artifacts — typed prompts, emails, forms, terminal output, UIs — rebuilt/re-typeset so text is ≥3% frame height, never raw tiny screenshots.
- Evidence: 100x (the copy-pasteable prompt on screen at 13s; re-typeset Claude Code UIs); CodeHype (email, filled form, model picker — "every claim is a legible real screenshot"); Hermes (terminal mega-scene = 40% of screen time, list rows ≈40px); Weavy (5 typed prompts ARE the script).
- TEST: OCR — during declared proof beats, minimum median glyph height ≥3% frame height; at least one typed-on text event (character count monotonically rising over ≥1s) per tip/chapter.

**N3. TWO-REGISTER TEXT.** Exactly two text voices, never mixed: small diegetic UI text (mono/sans, inside windows) and large narrator text (serif/display) with ONE emphasis word per line flagged by color/italic that rhymes with an object in frame.
- Evidence: 100x (serif captions, one green/red italic phrase; red italic ↔ red circle); Hermes (mint noun highlighting on every card); DeepSeek (serif connectives + giant sans payload: "FRACTION"/"COST"/"53").
- TEST: OCR box-height histogram must be bimodal (two clusters separated ≥2x); color-sample emphasis words — FAIL if >1 accent-colored word per caption line.

**N4. PERSISTENT-CANVAS CAMERA.** The video is one world (paper table, dark canvas, desk, vertical scroll) explored by a camera; elements enter/exit while the canvas persists; hard cuts are reserved for palette flips and host punch-ins.
- Evidence: Hermes (8.1s and 6.7s zero-cut canvas glides; conveyor transition over a fixed background); Greg .md (one vertical canvas, camera dollies between chapters); Weavy (one cream table, 12s no-cut node-canvas drive); DeepSeek (20.6–28.7s single glide).
- TEST: during transitions, dense optical flow must be globally coherent (one dominant translation/scale vector, ≥60% of vectors within 20° of it) rather than a full-frame decorrelation. Plus: require ≥1 continuous ≥6s stretch with zero scdet hits.

**N5. MOTION BLUR + DRIFT ON EVERYTHING FAST.** Fast entries arrive as smears; screen recordings never sit frozen — they get slow pull-back/scroll with velocity-proportional blur and micro-wobble.
- Evidence: Weavy ("baked motion blur on every fast move… without it the same choreography reads cheap"); CodeHype (6s pull-backs, focus breathing, shutter ghosting on scrolls — the explicit cure for our frozen-frame retention killer); Greg .md (whip-pans with true directional blur, f035 fully smeared); 100x (nothing teleports).
- TEST: correlate per-frame delta with Laplacian sharpness: frames in the top delta decile must be measurably blurrier than hold frames (ratio ≤0.7). FAIL "crisp teleport" videos where fast frames are as sharp as holds. Separately: any screen-capture segment must show nonzero global-motion (scale or translate ≥0.5px/frame).

---

# THE DELTA — our 26s SVG-component Short vs. this grammar

What we make: themed SVG motion components (traces, glass cards, karaoke captions) sequenced on a VO clock. What all 11 references make: **a demonstration the eye can follow with the sound off**. The five gaps, by impact:

**GAP 1 — Our visuals decorate the VO; theirs ARE the script. (U2, N2)**
This is the mute failure. A trace animating over a glass card communicates "tech vibes," not the claim being spoken. In every niche reference, the meaning-bearing object is on screen: the prompt typed live (Weavy 5.7–8.8s, 100x 10–13.5s), the email with the button and the hand-drawn arrow (CodeHype 1.2–4.3s), the terminal selection with the price highlighted (Hermes 9.2–24s). **Closing technique: kill the mood-component beat class. Every beat must be a diegetic artifact — a TypeOn prompt composer, a re-typeset UI doing the thing, or a number-prop (Fusion odometer / Hermes draining gauge). QC gate = U2's phrase-to-event alignment; a beat with no visual twin is an unfinished beat.**

**GAP 2 — Our captions are karaoke of full sentences; theirs are the transcript in 1–3 word chips at a fixed anchor. (N1, N3, U7)**
KaraokeLine paints a full sentence and highlights through it — the muted viewer must read a paragraph while graphics move elsewhere. References hard-swap ONE chip (1–3 words) every 0.4–0.7s at a locked 68% anchor, with one color-flagged noun that rhymes with an object in frame (DeepSeek, CodeHype, Hermes). Reading burden ≈ zero; the words land on VO stress like drum hits. **Closing technique: restyle KaraokeLine into single-chip cards — hard swap ≤2 frames, micro scale-pop, fixed anchor, two-tone emphasis, global layer that does NOT reset at cuts (CodeHype's word bridging a hard cut).**

**GAP 3 — Our beats are islands; theirs are one world with a carry element. (U3, N4)**
We stitch independent compositions: each beat resets background, palette position, and attention. All 11 references thread a protagonist through every boundary (Anthem's ball, Greg's flower, 100x's prompt bar) and/or persist one canvas explored by a camera (Hermes conveyor, Weavy's cream table). A muted viewer of ours must re-orient every 3 seconds — which reads as noise. **Closing technique: one persistent canvas per Short + one declared carry element (channel mascot/prompt bar/brand glyph) present in every scene; build the conveyor transition (fixed background, outgoing card slides off with 3–5° momentum rotation, incoming enters as one group) and the container-morph (same rounded rect, contents crossfade, then scale-to-fullbleed — 100x/Hermes).**

**GAP 4 — Our transitions are unprepared pops on the VO clock; theirs are earned boundaries. (U4, U5)**
Components mount/unmount when the VO says so — no exit velocity, no landing settle, no morph. References either morph (bubble→plane, beam→road, moodboard→logo pixel-dissolve) or, when they do cut, deform into it and settle out of it (smartwater's stretch-blur exit; Greg's defocus→sharp landing; Weavy's zoom-through whiteout). **Closing technique: build a `<CutPrep>` wrapper (last 3 frames: scaleY stretch + directional blur) and one signature morph transition (zoom-through-whiteout is the cheapest: scale 1→8 into a target element + white bloom = next scene's background). Gate = U5's exit-velocity/settle-sharpness test.**

**GAP 5 — Uniform, crisp, flat motion: no drift, no blur, no luma rhythm, dead holds. (U1, N5, C1, U9)**
Our SVG springs are crisp teleports; our holds freeze (the retention data already convicted frozen frames); our lighting is flat and constant; our loudest moment is at 0s, not in the 5–7s knee. References keep a camera perpetually drifting (CodeHype's 6s pull-backs with focus breathing), bake blur into every fast move (Weavy), idle every hold (Fusion's slosh/flicker/odometer), and place their maximal event at 4–8s (Fusion's world inversion at 5.0s). **Closing technique: a global camera layer (Perlin-noise drift + slow scale on every scene, mandatory on screen captures), velocity-keyed blur on all entrances, an idle-motion requirement per component (cursor/shimmer/tick), and schedule the single biggest ink-delta event of the film into 4–8s. Gates = U1, U9, N5.**

Ruthless summary: the gap is not asset quality and not tooling — every reference is ~70–100% buildable in Remotion today. The gap is that we compose *decoration synced to audio* while they compose *silent demonstrations that audio happens to narrate*. Fix order: Gap 1 makes it comprehensible, Gap 2 makes it readable, Gap 3 makes it followable, Gaps 4–5 make it expensive.

---

# PART II — THE PIPELINE

# THE MOTION PIPELINE — "AI Unpacked VJ" Pure-Motion Shorts (SYNTHESIS v1)

**THE PIPELINE IN ONE PARAGRAPH**

One artifact runs the whole factory: the **FILM MANIFEST** — a single JSON that is simultaneously the storyboard you approve, the build input, and the ground truth every QC gate tests against (story-first's core decision; it makes "passed QC but wasn't the approved story" impossible). An idea enters by **verb, not topic**: it must be stateable as "OBJECT goes from STATE A to STATE B" or it routes to the existing host/capture lane. An approved idea becomes a chain of 4–6 **scene archetypes** — typed Remotion scenes with continuity ports (template-first's contract), so carry element, canvas persistence, and prepared boundaries are compile errors, not taste. Assets are **code-first**: meaning-bearing objects are Claude-authored SVG/TSX on kit.tsx tokens ($0, can't drift off-palette); FLUX-schnell on the 3060 supplies texture plates; Leonardo-via-Chrome is rationed to ≤1 hero still; **no host, no HeyGen** — marginal cost ≈ $1/episode. Two human gates only: you approve the storyboard contact sheet (nothing renders or spends before yes), and you watch the draft **sound-off, at feed size, on your phone** — because that viewing is the format's definition of done. Everything else is machine gates derived from the 11-reference grammar, run by one suite on the rendered MP4 with the manifest as spec.

---

**STAGES**

1. **CAPTURE** — In: news radar, sparks, comments, curriculum. Out: bucket row in `channels/claude-tricks/MOTION-BUCKET.md` (schema below). Tool: Claude + existing news poller. Who: auto + VJ. Time: ~5 min/idea, continuous.
2. **SHAPE** — In: bucket row passing the admission gate. Out: story spine — mute logline, payoff object, carry element, knee-event candidate, number-provenance plan, 44-char title with the searched noun. Tool: Claude drafts 3 spines, VJ picks 1. Time: 20–30 min.
3. **SCRIPT + MUTE TABLE** — In: spine. Out: VO lines (~34s, last line written first) where **every line carries a stage direction `{subject, from, to}`** — a noun and two states, no adjectives. A line whose direction is "graphics animate" fails here and the *script* gets fixed. Numbers get provenance tags. Tool: Claude; honesty audit is a hard sub-gate. Time: 1–2 h.
4. **ARCHETYPE CAST** — In: mute table. Out: FILM MANIFEST v1 — archetype chain with slot fills + ports + asset list; the **continuity compiler** validates the chain (carryOut matches next carryIn, ≤2 palette flips, A1's plant reaches A8) and the **honesty type-check** rejects any number without a source. Tool: new `cast_scenes.py`. Who: Claude. Time: 15 min.
5. **STORYBOARD — THE OWNER GATE** — In: manifest. Out: one contact-sheet page: real Remotion stills (3/scene), the knee frame and payoff frame marked at their seconds, carry element circled in every frame, per-beat one-liner "what the muted viewer sees," asset list with generator route and cost. Delivered via `sync_preview.py`. **NOTHING renders and no paid/slow generation runs before your yes — approval also authorizes the asset batch, so you see cost before it's spent.** Tool: new `storyboard.py`. Time: 30 min build, 5 min review.
6. **VO** — In: approved lines. Out: cached ElevenLabs takes + measured clock (0.4s breaks, style 0.4). VO deliberately sits *after* approval so line edits at review are free. Existing build_ep_v2 path. Time: 10 min, ~$0.5–1.
7. **ASSETS** — In: manifest asset list. Out: everything on disk. SVG already authored at stage 4; FLUX plate batch fires as a `shell_script` job on DESKTOP-DEIR7RS; Leonardo via `leo_chrome.py` only if flagged; every raster passes `ingest_plate.py` before it may enter a comp. Who: auto (Leonardo semi). Time: 0.5–1 h wall, parallel with nothing blocked.
8. **BUILD** — In: manifest + clock + assets. Out: draft 1080x1920 master at -14 LUFS. Tool: build_ep_v2 "film" episode type — reuses `@beatN+x` resolution, `cook:` beats, and the spine mechanism verbatim; global Canvas + ChipCaption + CameraDrift layers mount in Short.tsx. Time: ~1 h incl. render.
9. **MACHINE QC** — In: draft MP4 + manifest. Out: PASS/FAIL per gate (table below), failing law named, returns to stage 4 or 7. Tool: new `qc_motion.py` extending `probe_frames.py`. Time: 5 min.
10. **PHONE GATE → FINALIZE → ARM** — You watch the draft muted, feed-size, on your phone. Then existing flow: sync_preview approval, finalize (never `--dry`; use `--skip-arm`), **4K reminder**, arm; pinned comment carries the exact prompt (give, don't promise). Time: 15 min.

Steady state: under 1 day wall clock, ~45 min of your attention, ~$1 marginal cost.

---

**THE IDEA BUCKET**

File: `channels/claude-tricks/MOTION-BUCKET.md`. The bucket is the **router** between the two coexisting lanes: the capture lane asks "can we film it?", this lane asks "**what single object, mutating, IS the argument?**"

**Taxonomy (7 classes — every mute-tellable AI story is one of these):**
- **QUANTITY** — a real number moves as a physical prop (honest only with owner-measured/sourced figures, locked_numbers.json pattern)
- **TRANSFORMATION** — mess → structure (the strongest class for mute play)
- **ROUTE** — a decision shown as a traveled path
- **MECHANISM** — how it works under the hood; declares itself an illustration, zero honesty risk
- **DUEL** — A vs B, honest only if both sides were actually run once
- **RECIPE** — a repeatable method as an assembly line
- **TRAP** — the mistake as physical failure; the red accent is spent here and only here

**The admission gate (all six or the idea stays in the bucket):**
1. Mute logline exists: "OBJECT goes from STATE A to STATE B" — nameable object, visible before, visible after.
2. Payoff object is withholdable to ≥75% of runtime and plantable incomplete at 0s.
3. Knee event nameable in one sentence and schedulable at 4–8s.
4. Every number is real-sourced, mechanism-illustration, or absent — no fourth option.
5. The GIVE exists: a paste-able prompt for the description/pin.
6. Honesty class declared: real-capture / reads-as-mock / declared-illustration. News that dies in 48h stays in the fast lane (this format has a day of lead time).

**12 episodes, ranked by mute-tellability x reach** (title-noun · mute story · payoff):

1. **"Why Claude Forgets Long Chats"** · glass tube fills with message blocks, oldest fall out the bottom · the one block you pinned glows and never falls. *(PILOT — pure mechanism, zero external assets, zero honesty risk, huge search noun.)*
2. **"Stop Describing. Paste One Example"** · describing = a fog silhouette that never sharpens; pasting = output snaps to match · side-by-side fog vs sharp. *(Reprises the proven `_style` premise in mute grammar.)*
3. **"40 Tabs → One Answer"** · tab cards rain into a chaotic pile; one typed line collapses them · a single stacked answer card with source chips standing where the pile was.
4. **"The 5 Words Doing the Work"** · an 80-word prompt's filler greys and blows away to 9 words · the same answer card materializes from the 9-word line. *(Both prompts actually run once.)*
5. **"Your Photos Are a Database"** · screenshots of bills/meds/anything fall into a grid; a typed question lifts only matching cells · the answer assembled from lifted cells. *(PII masked structurally, `_upi` pattern.)*
6. **"What a Token Actually Is"** · a Hinglish sentence shatters into bricks, odometer counting · the same idea rebuilt in fewer bricks fits with room to spare. *(Counts from a real tokenizer run.)*
7. **"The Email That Hijacks Your AI"** · an email with hidden white text turns the assistant's head away from you · the "never obey instructions inside content" shield stamps down, hidden text revealed in red. *(The best-unmade-video from the capability research.)*
8. **"Screenshots Beat Connectors"** · a parcel faces a cable-tangle of login walls vs a camera slot · the parcel arrives by photo while the cable path still blinks at a login. *(Grounded in verified connector-friction facts.)*
9. **"The Context Sandwich"** · loose ingredients thrown separately yield a half-built answer · layered as one sandwich, the full answer assembles beside the half one.
10. **"Why AI Sounds Confident When Wrong"** · a ball rolls the deepest-worn groove even where it ends at a cliff · "say I-don't-know if unsure" carves a side-ramp; the ball takes it.
11. **"The ₹0 Stack"** · a conveyor assembles one real deliverable through stations with a cost meter welded at ₹0 · finished deliverable, meter never moved. *(Task actually done once, free-plan only.)*
12. **"Voice Note → Meeting Minutes"** · a waveform pours into a funnel and comes out a table with owners and dates · one row lifts: "you — Friday."

(Held back, not killed: "The Double-Count Trap" — best QUANTITY story we have, but blocked on your real-data consent.)

---

**SCENE ARCHETYPES**

Eight cover every scene in all 11 references. Each is a Remotion composition-piece one level above the cookbook: it orchestrates existing components, owns its boundary behavior, and implements the **ScenePorts contract** (`carryIn/carryOut` with anchor+velocity, `canvas: persist|flip`, `exit: morph|cutprep|whiteout`; `RealNumber` carries a mandatory `source` field — the honesty bar in the type system). The continuity compiler walks the chain at build time.

- **A1 COLD-OPEN PLANT** — motion already running at frame 1; plants the incomplete payoff object and the question; no static hook card ever. *Refs: Anthem opening, smartwater "got..?", Weavy's missing checkbox.* Slots: 1 chip line, incomplete-object spec, optional 1 FLUX plate.
- **A2 TYPE-ON COMPOSER** — a prompt typed live, cursor idling, glyphs ≥3% frame; the prompt bar is itself a CarryId that can shrink to a header and survive the film. *Refs: Weavy's 5 typed prompts, 100x prompt bar, CodeHype email.* Slots: literal text, send-moment anchor. Uses: ScreenStage, ChatApp, CommandPalette.
- **A3 OBJECT-JOURNEY** — the hero passes through 2–4 states on one continuous clock via the existing `spine` mechanism (the `_appraisal` episode already proves this archetype). *Refs: Anthem's ball, Water Ad bubble→plane→ball.* Slots: state list with `@beat` anchors, labels. Uses: ProofTrace, CareerArc.
- **A4 NUMBER-PROP** — a spoken number as a physical object ≥4% frame height arriving by count/drain/roll; forbidden without a sourced number. *Refs: Fusion odometer, Hermes draining gauge, DeepSeek stars ring.* Slots: RealNumber+source, unit, motion verb. Uses: Odometer, RingGauge, LedgerFlow.
- **A5 EXPLODED-DIAGRAM** — one persistent canvas, the object explodes into 3–5 labeled parts, camera dollies between them, ≥6s no-cut. *Refs: Greg .md chapters, Hermes terminal mega-scene, Weavy node canvas.* Slots: parts, camera path, canvas plate (FLUX). Uses: BentoGrid, OrbitNodes, Fogline.
- **A6 BEFORE/AFTER DIFF** — two states of one container; the wipe is carried BY the carry element crossing frame, never a free cut. *Refs: 100x red/green axis, CodeHype PROMISE→RECEIPT.* Slots: stateA/B fills, the one accent-colored contrast word. Uses: DiffReveal.
- **A7 RHYTHM MONTAGE** — 3–5 micro-scenes of exactly 1/2/3 beats on a declared BPM grid; the only legal way past the cut budget; max once per episode. *Ref: smartwater's 0.54s grid.* Slots: BPM, items, 1-chip captions. Uses: SwipeDeck, TapStack.
- **A8 PAYOFF / GIVE** — A1's planted object completes (type-checked: payoff ref must === A1's plant), biggest settle of the film, then the prompt-on-glass GIVE. *Refs: Anthem brand at 85%, Weavy checkbox at 92%.* Slots: payoff ref, OutroGlass props, desc_prompt. Uses: OutroGlass via gen_outro_glass.py.

Above all archetypes, three global layers (nothing opts out): **ChipCaption** (single 1–3-word chip, hard swap ≤2 frames, locked 68% anchor, one accent word, does not reset at cuts), **CameraDrift** (Perlin drift + slow scale + velocity-keyed blur + exposure ramps), **Canvas** (persistent world plate + grain + grade).

---

**ASSET AUTOMATION MAP**

Doctrine: **SVG-first, raster-as-texture.** Meaning-bearing objects are code because they must hit palette tokens exactly, animate on the frame clock, and pass OCR gates. Rasters supply atmosphere, never meaning.

| Asset class | Generator | Fallback | Cost/ep |
|---|---|---|---|
| Props, mock UIs, number props, diagrams, chips, carry mascot, morph pairs | Claude-authored TSX/SVG (cookbook, kit.tsx tokens; brandmarks.ts for real marks — never redrawn) | — (never generated raster) | $0 |
| Canvas plates, paper/grain/gradient worlds | FLUX-schnell on DESKTOP-DEIR7RS (`shell_script` batch, 1–2/ep) | procedural SVG noise | $0 |
| Hero illustration (the 1–2 money frames) | FLUX-schnell | Leonardo via owner's Chrome (`leo_chrome.py`, Kino recipe; API is 402-blocked) — budget ≤1/ep | $0 |
| Photographic texture inserts (rare) | Pexels/Pixabay via `fetch_broll.py` — **one-time task: free API keys into .env** | FLUX stylized substitute | $0 |
| VO | ElevenLabs (cached) | CosyVoice2 local (voice-tracks contract) | ~$0.5–1 |
| Music bed | Suno via Chrome, once per series, reused | existing bed_ files | ~$0 amortized |
| Host | **none — this format is host-free** | Sol PIP only if a beat truly needs a human ask | $0 (saves $3–5/ep) |

**Style consistency — three enforced layers:**
1. **STYLE.lock** per series: 5 palette hexes + accent meaning, font pair, grain PNG, LUT, drift params, FLUX prompt suffix + seed family, Leonardo recipe. Never changes mid-episode. Plus 3–5 **season anchor images** generated in one Leonardo sitting for image-guidance.
2. **`ingest_plate.py`** — no raster touches a frame directly: resize to slot geometry, quantize/retint toward the locked palette, grain + LUT, then emit. A plate that survives retint but still reads off-style gets one anchor regeneration, then is **cut** — a missing plate is recoverable, an off-style one is not.
3. **Palette gate** (below) convicts drift on the rendered file mechanically.

---

**QUALITY GATES**

One suite, `qc_motion.py`, manifest as spec. Fail names the beat + law.

| Gate | Measures | Passes when | Sits at |
|---|---|---|---|
| Mute-table completeness | every VO line has `{subject,from,to}`; every numeral has provenance; illustration numbers carry no measurement grammar | 100% | blocks stage 4 |
| Continuity compile (U3/U5/U8) | port chain, ≤2 canvas flips, plant reaches payoff | type-check clean | blocks stage 5 |
| **OWNER STORYBOARD** | the grammar, the cost, the muted story | your yes | blocks stages 6–8 |
| G1 dead-frame (U1) | per-band ink-delta, 1.0s window | no content band at delta 0 ≥1.0s; no full freeze ≥0.5s | stage 9 |
| G2 visual-twin (U2) | VO phrase boundaries x ink events | every phrase has a ≥p60 band event within ±0.5s | stage 9 |
| G3 carry (U3) | template-match carry element at every cut | present both sides, every boundary | stage 9 |
| G4 cut budget (U4) | ffmpeg scdet | ≤0.45 cuts/s OR all on declared grid ±1 frame | stage 9 |
| G5 prepared boundary (U5) | pre-cut exit velocity + post-cut sharpening | every boundary | stage 9 |
| G6 palette (U6) | k-means hues | ≤6 clusters >2% share; accent ≤15% of frames | stage 9 |
| G7 chips (U7/N1) | OCR caption band | ≤3 words/chip; changes every 0.4–1.0s in speech; y-variance ≤3%; nothing in bottom 25% + the ~330px chrome band at FEED size | stage 9 |
| G8 payoff (U8) | payoff first-seen timestamp | ≥0.75 x duration | stage 9 |
| G9 knee (U9) | max full-frame delta in 4.0–8.0s | ≥p90 of all seconds; FAIL if loudest second is 0–2s | stage 9 |
| G10 number-prop (U10) | VO numerals x OCR | on-screen ≥4% glyph height within ±1s | stage 9 |
| G11 blur-on-fast (N5) | top-decile-delta sharpness vs holds | ratio ≤0.7; captures show ≥0.5px/frame motion | stage 9 |
| G12 loop | last 12 frames vs first 12 | histogram + carry position compatible (reported; warning first month, then blocker) | stage 9 |
| G13 masters | LUFS, caption ceilings, contact sheet | -14 LUFS + existing thresholds | stage 10 |
| **PHONE GATE** | the draft, muted, feed-size, on your phone | it works with the sound off | blocks stage 10 |

C3 overshoot (arrivals ≥3% past target on ≥50%) runs as a **warning** trending toward a gate. No "looks fine" overrides except your explicit word.

---

**BUILD ORDER** (to Short #1 at reference quality — ~8 working days; pilot is all-SVG, so the raster chain slides to episode 2)

1. **ChipCaption** — restyle KaraokeLine to single-chip cards, fixed anchor, survives cuts. Highest leverage per line of code. *1 day.*
2. **Canvas + CameraDrift + CutPrep + zoom-through-whiteout morph** — the three global layers and the one signature transition, mounted in Short.tsx. *2 days.*
3. **withIdle() + kit motion primitives** (`enter()/settle()/smear()` with overshoot and velocity blur baked in; archetypes may only move things through these) — U1/G5/G11 pass by construction. *1 day.*
4. **ScenePorts + `cast_scenes.py` continuity compiler**; retrofit ProofTrace/CareerArc/OutroGlass so A1/A3/A8 exist formally. *1.5 days.*
5. **`qc_motion.py`** — G2/G3/G5/G9/G11 new; G1/G4/G6/G7/G8/G10 assemble probe_frames + scdet + tesseract. *2 days.*
6. **`storyboard.py` + FILM MANIFEST "film" type in build_ep_v2** — stills batch, carry map, cost line, sync_preview delivery. *1 day.*
7. **PILOT: "Why Claude Forgets Long Chats"** — A1→A3→A5→A6→A8 chain, no external assets, no captures, no host. Full stages 1–10; expect 2–3 gate-fail loops — the fails are the point, each hardens a law into a component. *1.5 days.*

Episode 2+ adds `ingest_plate.py` + STYLE.lock + the FLUX batch template + Pexels keys (*~1.5 days*, parallel). A2/A4/A5/A7 formalize one per episode, each inside a real Short — the SpinWheel/ReactionMeter pattern, never built cold.

---

**WHAT WE ARE NOT DOING**

- **Asset-first as the organizing principle** (generate a raster batch, then assemble) — SVG-first makes most "assets" code; the manifest keeps asset-first's routing table, not its center of gravity.
- **VO before storyboard approval** — line edits at your review must be free; nothing paid runs before yes.
- **Three QC scripts** (`frame_laws.py`/`mute_gate.py`/`qc_motion.py`) — one suite, one report, one name.
- **Two bucket files** — one `MOTION-BUCKET.md`; the calendar row's `format:` field is the router.
- **The low-res animatic with scratch VO** — the annotated contact sheet approves in one minute; an animatic adds a build cycle for no decision it changes.
- **Craft-tier C1/C2 as gates** (exposure scoring, zero-cut causal morph chains) — aspirational; revisit after 5 shipped episodes.
- **C3 physics as a hard gate now** — warning that trends to a gate once the primitives exist, or it blocks episode 1 forever.
- **Auto-hue-rotating arbitrary rasters into compliance** as the main defense — retint lives inside ingest_plate; the real defense is that rasters are plates behind SVG, and off-style plates get cut.
- **Rasters as protagonists** — a FLUX image may never be the meaning-bearing object; meaning is authored code.
- **The UPI double-count episode as pilot** — best QUANTITY story we have, but blocked on your real-data consent; the mechanism pilot has zero dependencies.
- **News reactions and "top 5 tools" lists in this lane** — no object, no state change; they stay in the fast host/capture format.
- **Per-episode Suno, HeyGen host, 4K by default** — one bed per series, host-free format, 4K only on your say after finalize (standing rules).


---

# PART III — THE FRESH START (2026-08-21, same day, evening)

VJ's verdict on the first pilot build, verbatim: *"only see svg cant we use elements like in
the references, and camera motions, i feel we are restricted with our own current style
systems, lets have a fresh start."* He was right, and the wider evidence then proved it
quantitatively: **no hit is majority-SVG** — coded graphics cap at ~30% in every winner and
serve as connective tissue, never as the proof.

Method: 3 web-search agents found the top-performing Claude/AI Shorts; the top 6 by verified
views (10.0M / 8.78M / 5.53M / 1.78M / 1.66M / 1.57M) were downloaded and studied
frame-by-frame like the original references; a pattern synthesis, then three competing
fresh style worlds (KAAGAZ paper-editorial / LATE SHIFT desk-world / CLAYLIGHT soft-3D toy),
judged and merged. What survives from Parts I–II: the 14 laws, the gates, the manifest, the
capture rigs, the pinned-prompt rule. What died: the obsidian/aurora/glass/magenta system on
canvas, SVG-as-the-diet, and HeyGen-on-canvas.

The frozen result: **channels/claude-tricks/films/CLAYLIGHT.lock.json**.

## III.1 The hit pattern (evidence)

# THE HIT PATTERN — AI/Claude Shorts (synthesis of 6 hits, 10.0M–1.57M views)

Videos cited: FRACTAL (AI Code Clash, 10.0M, 6.1s) · FLOAT (Fireship, 8.78M, 54s) · VIBE (Alberta Tech, 5.53M, 51.6s) · PDF (100x Engineers, 1.78M, 58.5s) · ANTI (Wanderloots, 1.66M, 25s) · HACK (NetworkChuck, 1.57M, 58s).

---

## 1. ELEMENT MIX OF A HIT

Measured element diet across the six (share of runtime; overlays counted separately):

| Element class | FRACTAL | FLOAT | VIBE | PDF | ANTI | HACK | Verdict |
|---|---|---|---|---|---|---|---|
| Real captured artifact (UI, console, live code output, GitHub/PyPI, test runner) | 100% (live canvases, ~47% of pixels) | ~22% | ~20% (editor/test overlays) | ~22% | ~39% | ~35% | **20–40% in every hit. Never zero.** |
| Human face (real host) | 0% | 0% | 100% (base) | ~26% | ~54% | ~45% | Optional — the two BIGGEST hits have no human |
| Big type layer (captions/cards) | 100% static | ~65% (primary content) | ~90% | ~90% | ~85% | ~90% | **~85–100% overlay presence in all six** |
| Coded/vector graphics (diagrams, icons, motion cards — our "branded SVG" class) | 0% | ~12% | 0% | ~29% | ~35% overlay (logos/cards) | ~12% | **Ceiling ≈30%. No hit is majority-SVG** |
| Stock / generated imagery | 0% | ~13% (retro stock) | 0% | ~13% | 0% | 0% | 0–13%, optional, always ironic/cheap-on-purpose |
| Characters/memes | 0% | ~41% | 0% | 0% | 0% | ~5% icon | Fireship-only specialty |

**The correction to our 100%-branded-SVG instinct:** the evidence says the load-bearing pixels are *verifiable reality* — real syntax highlighting (VIBE 0.0s), 125k GitHub stars (PDF 29s), a real rate-limit toast (ANTI 0.5s), real `docker ps` (HACK 50s), live generative output (FRACTAL, all 6.1s). Coded graphics never exceed ~30% and serve as *connective tissue* (counters, diagrams, icon montages, transitions), never as the proof. The working formula: **base layer = real face OR real artifact; 20–40% real captured proof; type overlay ~90% of runtime; coded vector 10–30%; stock ≤13% optional.** Credibility is the aesthetic — audiences in this niche verify the pixels (VIBE's "8 Issues" DevTools chip, FLOAT's real REPLs).

## 2. CAMERA LANGUAGE OF A HIT

Full catalogue of camera moves observed, with frequency:

| Move | Where seen | Frequency |
|---|---|---|
| **Nothing — locked frame, zero moves** | FRACTAL (entire), FLOAT (frame-diff-verified static, e.g. telescope 26.0s vs 27.5s), VIBE (all 3 setups, all 52s) | **3/6 — and they are the top 3 by views** |
| Slow constant push-in on host | PDF, ANTI (per block), HACK (emphasis beats "boom" 36s) | 3/6 |
| Punch-in/out alternation between consecutive host cuts | PDF (tighter/wider alternation), ANTI (scale jumps at caption swaps ~2–4s) | 2/6 |
| Crop + slow pan/drift-zoom over real UI captures (post-move Ken Burns) | ANTI (captures never shown static-fullscreen), PDF (GitHub slow scroll) | 2/6 |
| Insert panel slides/punches in from top over persistent host | HACK (top-half captures), PDF (split hook) | 2/6 |
| Signature stylized transition (logo wipe / RGB glitch) | ANTI (Claude asterisk spin 8.5s, 19.5s), HACK (glitch-shatter on nearly every change) | 2/6 |
| Shake, whip pan, handheld, dramatic dolly | — | **0/6. Absent from the entire corpus.** |

**Minimum vocabulary separating a hit from a static explainer: zero camera, but never a static frame.** The substitution is explicit in every study: element motion replaces camera motion — swaying canvases (FRACTAL), a red decimal square jumping positions (FLOAT 36–43s), captions swapping every 0.4–0.7s (HACK), progress bars filling (PDF 1.6–3.8s), cursor motion inside captures (PDF 0–1.5s drag). If a host exists, add exactly two moves: slow push-in + punch alternation at caption swaps. If captures exist, add crop+pan. One signature transition maximum. That is the complete kit.

## 3. STYLE WORLDS

Both modes exist, but the split is not what it looks like:

- **One-world:** FRACTAL (single composite), VIBE (zero graphics that aren't editor-real; 100% one aesthetic), ANTI (host + yellow type + product UI), HACK (magenta/purple grade + chromatic aberration applied to *everything* including the mug — the grade IS the world).
- **Collage:** FLOAT (memes + retro stock + 3D + consoles + diagrams), PDF (celebrity keynote + stock b-roll + flat vector + real UI + host).

But the two collagers each carry a **binder** that makes the collage read as one video: FLOAT binds with black-bg one-accent-color-per-card typography (65% of runtime) and recurring binary-digit motifs (4 appearances); PDF binds with a disciplined 3-palette rule (dark Claude UI / pale blue-grey graphic cards / warm host) and a reused progress-bar motif (3 appearances over different footage).

**Implication for a style system:** lock the *chrome*, free the *panels*. The system should hard-lock (a) the caption/type layer, (b) a 3-zone palette, (c) one transition signature, (d) 1–2 recurring motif components reused 3+ times per video — and then allow content panels to come from any source class (capture, vector, stock, character) without breaking identity. Our instinct to lock one illustration style for all pixels was solving the wrong layer.

## 4. HOOKS THAT WIN (first-2s patterns, ranked by frequency)

1. **No intro, ever — frame 1 is already the content** (6/6). FRACTAL's frame is complete at 0.00s; PDF opens already split-screen mid-drag; VIBE's first caption + broken code are at 0.0s. Zero logos, zero build-ins, zero throat-clearing in the corpus.
2. **Motion inside the frame at t=0** (6/6): swaying trees, cursor dragging PDFs, glitch tear, text popping within second one (FLOAT "0.1" at ~1.0s).
3. **A recognizable AI brand legible before 1s** (5/6): four model names (FRACTAL f1), Claude UI (PDF f1), "claude" caption box over glitch (HACK 0.0–0.6s), Claude+Antigravity logos (ANTI 0–0.5s), code-fix prompt to an AI (VIBE). FLOAT is the exception (concept-first). Brand = instant audience self-selection.
4. **Full title promise delivered — spoken/captioned — inside 2s** (4/6): HACK ("accidentally turned Claude into a hacker" complete by 2.0s), VIBE title card 0–7.5s, PDF thesis "Everyone… PDFs", ANTI "Hitting Rate Limits?".
5. **The viewer's own pain/habit mirrored verbatim** (3/6): ANTI's actual "5-hour limit reached" toast, PDF's "Everyone [uploads] PDFs" accusation, VIBE's "please fix this method". Strongest form: the *literal error message the viewer saw today*.
6. **Direct question converting viewer to judge** (3/6): "who won??" (FRACTAL), "Hitting Rate Limits?" (ANTI), title question (FLOAT).
7. **First complete joke/gag lands by 2.0s** (2/6, both sketch/comedy): VIBE's request→"I have deleted the method" visual gag at 2.0s; FLOAT's absurdly trivial equation.

Winning stack = 1+2+3 always, plus one of 4/5/6 depending on shape.

## 5. VARIETY — the shapes in the winner set

Six hits, six distinct shapes. An idea bucket must span all of them:

| Shape | Exemplar | Skeleton | Length |
|---|---|---|---|
| **Comparison poll / judge-bait** | FRACTAL | same prompt → N models → legible-at-feed-size quality differences → verdict withheld forever → invisible loop | 6s |
| **Concept-explainer comedy** | FLOAT | question title → joke → proof → name the culprit (20s) → mechanism (28–49s) → title-callback joke | 54s |
| **Relatable sketch** | VIBE | costume-coded characters → escalating dialogue → false resolution (38s) → third-party punchline (46.6s) → mid-word loop cut | 52s |
| **Habit-callout tool tutorial** | PDF | "everyone does X wrong" → quantify the cost (tokens counter) → tool name at exact midpoint via social-proofed real page → escalate (MCP) → indexed CTA | 58s |
| **Optimization trailer** | ANTI | your error message → stack reveal → green-test proof frame → recipe deliberately withheld → long-form end card | 25s |
| **Experiment/confession** | HACK | "I accidentally…" → build montage over persistent host → "boom" turn (36s) → one plain-English command produces dramatic real output (44s) → "and it's clean" reframe (50s) | 58s |

Note the length bimodality: 6s loop-machine or 25–58s narrative — nothing between.

## 6. WHAT THE 11 REFERENCES MISSED

Deltas only — patterns present in this hit set that the reference-derived laws did not encode:

1. **Payoff withheld to 100% is a legal move** — our 75% law has an exception class. FRACTAL never answers "who won??"; the verdict is outsourced to comments via an **engineered controversy gradient** (one obvious sacrificial loser — dim DeepSeek — plus a genuinely ambiguous top tier so every partisan has ammunition). 10M views on a video with no payoff at all.
2. **A hit can have no audio stream** (FRACTAL — file literally contains none). Mute-proof isn't the ceiling; audio-optional is.
3. **Loop engineering as a designed feature, not luck** (3/6): frame 1 ≡ frame 183 (FRACTAL), mid-swear cut "mother—" that re-motivates the first line (VIBE 50.6s), title-callback rebus ending (FLOAT 52s). At 6s, one involuntary loop = >100% retention by construction.
4. **The false resolution** — plant a fake ending before the real one. VIBE's "Executed 61 of 61 SUCCESS / it works" at 38–43s exists to be demolished at 46.6s. None of our references did this.
5. **Fresh face + fresh room at the ~90% mark as a retention respike** (VIBE's coworker, 46.6s) — a new visual context precisely where curves die.
6. **Cuts are nearly irrelevant; the corpus runs 0–0.56 cuts/s.** The real metronome is the caption/event cadence: one keyword per 0.4–0.7s (HACK), one visual event per ~1.7–1.9s (ANTI, PDF). FLOAT held 8.8M viewers through a 12-second cut-free stretch because in-frame events never stopped. Our "no dead frames" law undersold how far this goes: 10–12s holds are fine if two layers are acting.
7. **The persistent two-panel stage** — a base layer that never leaves (FLOAT's meme guy 0–20s, HACK's host under sliding top-inserts, PDF's split hook) makes long holds feel busy and lets "cuts" be panel-swaps. Corollary: **layout re-architecture is the act break** (FLOAT's half-screen→full-screen shift at exactly 20s = culprit named).
8. **Social-proof numbers do the persuasion on screen**: 125k stars shown twice (PDF 29–32s), 564k installs (ANTI 8s), "Executed 61 of 61" (VIBE). We encoded numbers-as-props for *content* numbers, not *credibility* numbers.
9. **Quantify the problem before the reveal so the payoff has a number to beat** — PDF spends 26s establishing 1,500–3,000/page and 70,000/doc so "millions saved" lands (44s).
10. **Zero-human beats face-first at the top end**: the two 8M+ hits have no host. A face is a mid-tier retention tool, not a requirement — relevant given our HeyGen dependency.
11. **Brand logos as transition devices** (ANTI: Claude asterisk spin-wipe 8.5s/19.5s) — the brand IS the edit grammar, and it doubles the brand-recognition hook mid-video.
12. **Silence as pattern interrupt** (VIBE 22–23.8s typing, 27.3–30.8s smug wordless face — the biggest muted laugh has zero text). Our chip-cadence laws would have prohibited it.
13. **The trailer shape violates our "give, don't promise" rule and still hit 1.66M** (ANTI withholds the full recipe to sell the long-form). Divergence to test, not adopt blindly — but the evidence exists.
14. **One performer, N characters via costume+angle+background coding** (VIBE) — an entire cast for the price of a wardrobe change; every character switch reads as a camera move for free.

## III.2 The world verdict

# THE VERDICT

## Scoring (5 criteria, per world)

| Criterion | KAAGAZ | LATE SHIFT | CLAYLIGHT |
|---|---|---|---|
| Hit-evidence match | **High** — diet closest to hit table (captures 30–40%, FLUX only 8–13%) | **High** — "credibility is the aesthetic" thesis most literal; but stock plates posing as "my desk" is a quiet honesty tension the other two don't have | Med-High — sprites at 35–45% exceed the corpus generated-share (only precedent: FLOAT's 41% stylized layer, 8.78M) |
| Pipeline producibility | High — flat FLUX illustration is easy consistency; all-deterministic materials | **Lowest** — ScreenMap homography + photoreal prop compositing + plate-library curation; hardest QC gate ("reads pasted → doesn't ship"), 4–6d build | **Highest** — stylized clay is FLUX-schnell's most repeatable register; camera designed *backwards* from what flat sprites can't do; library compounds; 2–3d build |
| Distinct / recognizably ours | **Highest** (nobody does Indian-newspaper AI) — but it is still a flat authored-graphics world, the exact thing the owner just rejected ("only see svg") | Lowest — well-crafted version of what the niche already looks like | High — dark clay diorama + embedded real screens exists nowhere in the niche; feed-recognizable at thumbnail size |
| Variety across shapes | 6/6 mapped | 6/6 mapped | 6/6 mapped (incl. prompt-injection, the best unmade video on the backlog) |
| Cost/episode | ~$0, low time | ~$0 cash, highest time (1.5–2h) + fragile QC | ~$0, **lowest** (3–5 min GPU, sprite library amortizes) |

## RECOMMENDED WORLD

**CLAYLIGHT, primary and only, hardened with two transplants: KAAGAZ's provenance strip and LATE SHIFT's screen-embedding craft (spill + soften + light-wrap) applied to the SlabScreen.** Rationale: the owner's verbatim complaint is against flat authored vector — KAAGAZ, despite the best cultural identity of the three, is still a 2D graphics world with better texture, and recommending it risks "this is still cards." LATE SHIFT matches the references most literally but scores lowest on distinctiveness, highest on build/QC fragility, and its core fiction (stock plates as "my desk") sits uneasily against our honesty bar. CLAYLIGHT is the only spec that simultaneously delivers what the owner actually asked for (dimensional elements, true parallax camera motion), is engineered honestly around its own limits (hard orbit caps, no turntables), compounds in cost, and stays dark-ground feed-legible. Its one evidence gap — generated-sprite share above the corpus norm — is patched by clamping the diet (below) and by stealing the two mechanisms that made the other specs' credibility cases: every capture carries a KAAGAZ provenance strip, and the slab is embedded with LATE SHIFT's optical craft so the real pixels read *witnessed*, not pasted. One world, one builder, no second build at launch. A bonus the specs missed: Baloo 2 is an Ek Type family with harmonized Devanagari — KAAGAZ's Hinglish-chip rule ports into CLAYLIGHT natively, zero extra fonts.

## STYLE.lock — CLAYLIGHT v1

**Palette (frozen):**
- `#1A1214` Espresso ground (radial vignette to `#241A1C` lamplight pool center)
- `#EFE3D3` Clay cream — object bodies + primary type ink
- `#FF6B5E` Toy coral — **carry element ONLY; one coral object per episode; two coral = broken grammar**
- `#FFB454` Lamp amber — heat/cost/limit; counters, warning glow
- `#6FD5A8` Proof mint — **capture-adjacent only; mint on a toy alone is illegal**
- Zone rule: toys live in ground+cream+coral+amber; **real captures keep native colors, never retinted**; type layer = cream + coral pills only.

**Type (frozen):**
- Display/chips: Baloo 2 ExtraBold, uppercase, tracked +2%, 1–3 words; punch chip = cream-on-coral pill. Chips ≥64px.
- Devanagari (transplant): max ONE Devanagari word per episode, chips only, Baloo 2 Devanagari — only when it's the word an Indian viewer would actually think. (Owner call #3 to enable.)
- Counters: IBM Plex Mono Medium, amber, tabular — **renders ONLY measured numbers**. Mono on an invented number is a QC fail.
- Whisper line: Baloo 2 SemiBold, 60% size, cream @70%.
- ALL type on a flat 2D layer above the 3D world. Type never enters perspective.

**Materials (frozen):**
- Baked warm rim light from upper-left in every sprite prompt; shadow ellipse (radial, 25% black, 4:1 squash) auto-drawn by `SpriteLayer` — non-optional.
- Global bind: 2% amber overlay + soft vignette over everything EXCEPT full-frame proof captures; frame-indexed grain ~3%.
- SlabScreen embed stack (LATE SHIFT transplant): 0.5px soften on the inset capture · 4–8% sheen · blurred 103% light-wrap behind at ~15% screen-blend · dominant-hue radial spill onto adjacent clay at 10–15% screen-blend, crossfading 6f on capture cuts.
- Provenance strip (KAAGAZ transplant): Plex Mono strip under every capture — `REAL CAPTURE · claude.ai · <date>` (mint tick) / `STAGED` (cream 60%) for any mock. The honesty bar is now a visible brand asset.
- Brand lockup: clay badge, top zone, static. Nothing load-bearing below y≈1590.

**FLUX-schnell recipe (frozen):**
- Suffix, immutable: `", cute soft 3D clay render, matte plastic toy, smooth handmade clay texture, single warm rim light from upper left, soft studio shadow, centered, isolated on plain dark background #1A1214, viewed from 35 degrees three-quarter angle, 15 degrees above, 50mm lens, no text, no face, no logo"`
- steps 4 · 1536×1536 · seed family base `331100`, object *i* = `331100+i` · 3 candidates (seed / +1000 / +2000), elect 1, commit forever to `assets/claylight/library/` · rembg + 1px alpha erode + faint inner shadow · generate on stage-matched bg.
- ONE canonical angle per object. Carry element gets 3 lighting *states* (neutral/amber/mint), never angles. Mirror only symmetric props. No faces/googly eyes ever — props, not characters.

## CAMERA SYSTEM SPEC

Rig: `<div style={{perspective: 1200}}>` → WORLD group; all motion = frame-interpolated `camZ/camX/rotY/scale` tracks on the group. Layer depths fixed: FAR −600 · MID −300 · HERO 0 · FORE +150. Parallax is free.

1. **SHELF DOLLY** (default): camZ 0→220 over the full beat (8–14s), strictly linear. Frame never static.
2. **COUNTERWEIGHT PAN**: world translateX −60→+60px per beat; toys shelf-arranged; chip fires as each crosses center.
3. **KNEE SNAP**: 6f ease-out, scale 1.0→1.18 + rotateX 0→2°. Reserved for the knee event + ≤2 emphasis beats.
4. **ZOOM-THROUGH** (signature, ≤2/ep): ease-in dolly into a foreground sprite's dark center (sprite →~8×, scene A opacity dies at 60%), radial mask reveals scene B. Through-object = the coral carry element when possible — the brand IS the edit.
5. **ORBIT NOD**: world rotateY sine ±6°, ~5s period, for holds. **Hard cap ±8°, compiled into the rig.**
6. **DROP-IN**: sprite from camera, scale 3→1, 8f overshoot, blur 12px→0 (per-frame deterministic), shadow fades in 4f AFTER contact. One drop-in per VO sentence in setup beats.

Banned (compiled, not advisory): shake, whip pan, handheld noise, non-constant-rate dolly, per-sprite Y rotation (=0 always), effective sprite scale >1.4× native, turntable of any single object, dynamic sprite lighting, cross-Z physical contact, camera-tracked cast shadows.

## ELEMENT DIET TARGET (QC eye, per episode)

- **Real captures: 30–35%** (clamped UP from the spec's 25% floor to close the evidence gap). Proof beats: slab flat 0°, ≥85% frame width. Never zero. Provenance strip mandatory.
- **Clay sprites: 35–40%** (clamped DOWN from 45%).
- **Type overlay presence: ~90%**; event cadence one per 0.4–0.7s hot, ≤1.9s in holds; ≥2 layers acting every frame.
- **Code SVG/TSX: 15–25%** — shadows, dotted lines, counters, glow, masks. Connective tissue only, never the proof.
- **Pexels stock: 0–10%**, retinted warm, ironic only. Skippable.
- **Human face: 0%.**

## PILOT RE-SKIN PLAN — "Why Claude Forgets Long Chats" (~34s)

Toy box = context window · clay bricks = messages · amber overflow glow = the limit · **coral brick = your first message** (carry element).

| Beat | Time | Action | Camera |
|---|---|---|---|
| HOOK | 0–1.6s | Frame 1 complete: slab tilted 6° playing a REAL long claude.ai chat auto-scrolling (brand <1s, motion at t=0, provenance strip on); toy box beside it, bricks dropping; coral brick faint at bottom. Chip: **"IT FORGOT."** No burned caption before 1.6s. | Drift only |
| SETUP | 1.6–6.0s | One DROP-IN brick per VO sentence; amber mono counter ticks REAL token figures from an actual chat export. At **exactly 6.00s**: threshold digit roll + micro KNEE SNAP (the 6s worst-second fix). | Shelf dolly |
| MECHANISM | 6–14s | Box fills, bricks compress, amber glow rises; counter + settling bricks = two layers always acting through the 4–8s kill zone. Chips ~1.8s: `128K` → `FULL` → `NO ROOM`. | Orbit nod |
| KNEE | ~14s | KNEE SNAP → coral brick (chip: **"YOUR FIRST MESSAGE"**) tips over the back rim, falls out of the lamplight, blurs below FAR. Then **0.8s total silence** — no VO, no chip. | Snap + element motion |
| PROOF | 14–22s | ZOOM-THROUGH the box's dark mouth → full-frame REAL capture: "what was the first thing I said?" — Claude visibly missing it. Slab flat, ≥85% width, provenance strip, spill on. | Zoom-through |
| PAYOFF (~75%) | 22–30s | Only backwards dolly of the episode: pull back reveals clay JAR, chip **"NOTES."** Real capture of the summarize-before-overflow prompt working; **mint** chip `IT REMEMBERS` beside the real screen — mint earned. | Reverse dolly |
| LOOP + CTA | 30–34s | Coral brick rolls back to frame-1 position; final composition ≡ opening (engineered loop). Indexed CTA chip answerable in 2s; exact prompt in pinned comment (standing rule). | — |

**Asset list:**
- FLUX (RTX 3060 queue, seed family, 3 candidates each): toy box ×1 · clay brick ×1 (instanced; neutral/amber/mint-coral states via lighting-clause swaps) · slab frame ×1 · notes jar ×1 → ~12–15 generations ≈ 3–5 min GPU + one rembg batch.
- Captures (existing rigs, dark mode, 2x): ① long chat auto-scroll ② first-message miss ③ summary prompt working → 3 sessions.
- Code/TSX: counter, chips, shadow ellipses, GlowPulse, zoom-through mask, provenance strip.
- Leonardo: 0 (optional 1 cover still). Pexels: 0. Cash: $0 + optional VO.

**Build-once (2–3 days):** `ToyStage` · `SpriteLayer` · `SlabScreen` (with embed stack + provenance) · `ZoomThrough` · `ChipLayer` · `GlowPulse` · `scripts/claylight_sprite.py`. All registered via the existing cookbook pattern (`cook:<Id>` beats).

## WHAT DIES

- **Obsidian/aurora bed, glass grammar, magenta-on-canvas** — retired from this channel's motion shorts. (#E91E63's survival in off-canvas branding = owner call #4.)
- **Branded-SVG-as-the-diet** — demoted permanently to ≤25% connective tissue; never the proof.
- **HeyGen/Sol on canvas** — zero-human world; the HeyGen line item goes to $0 for this format (owner call #2).
- **KaraokeLine caption layer** — replaced by the chip system.
- **KAAGAZ and LATE SHIFT as worlds** — parked, but harvested: provenance strip + Devanagari-chip restraint (KAAGAZ), spill/soften/light-wrap embed stack + proof-color discipline (LATE SHIFT).

**What survives:** the 14 grammar laws, capture rigs, cookbook registry, ~34s target, 6.00s digit break, contact-sheet + feed-size QC, pinned-prompt rule, both caption ceilings, honesty bar — now upgraded from a disclaimer to a visible branded device.

## OPEN CALLS FOR THE OWNER

1. **VO or silent-first?** The corpus proves audio-optional; ElevenLabs is the only remaining per-episode cash cost. Ship the pilot silent+bed, or voiced?
2. **Retire Sol on-canvas entirely?** Zero-human is the top of the hit table, but Sol is the channel's current face — full retirement vs. reserve for occasional formats is identity, not craft.
3. **Enable the Hinglish chip rule?** One Devanagari word per episode (India-first asset, IN 1270/US 15) vs. all-English for global reach.
4. **Magenta's fate off-canvas** — keep #E91E63 in avatar/thumbnails or full rebrand to coral/espresso?
5. **KAAGAZ reserve clause** — park permanently, or hold as the designated skin for the `_upi`/ledger confession episode later (accepting a second build)?
6. **Debut episode** — pilot re-skin (mechanism story, full kit test) vs. the 6–8s "4 AIs pack the same box" judge-bait loop (cheapest live test of the world's feed performance)?
