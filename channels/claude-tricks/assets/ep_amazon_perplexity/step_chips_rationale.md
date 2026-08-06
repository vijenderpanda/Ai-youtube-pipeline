# Step chips — ep_amazon_perplexity (claude-tricks) · v1

Three step chips, each corner **measured** against the shipped clip over the exact
cut window, plus the mandatory compliance chip probed alongside because it shares
`cfg['steps']`.

| # | label | beat | window (s) | hold | pos | why |
|---|-------|------|-----------|------|-----|-----|
| S1 | `STEP 1/3 — AGENTS BROWSE + COMPARE` | 1 · chat mock `\|split` | 4.95 → 8.29 | 3.34s | **bl** | tl scores lower but sits on the reply line |
| S2 | `STEP 2/3 — COURT: THE USER ACCESSES` | 4 · agent_shopping `\|split` | 13.39 → 15.75 | 2.36s | **bl** | no corner is 0.00; chrome beats content |
| S3 | `STEP 3/3 — YOU CONFIRM THE PURCHASE` | 5 · glyph card `\|full` | 15.75 → 19.34 | 3.59s | **bl** | 0.0000 on all four; bl for scaffold consistency |
| C0 | `PRELIMINARY INJUNCTION VACATED — CASE CONTINUES` | 2–3 · courtroom `\|full` → host | 8.29 → 13.39 | 5.10s | **tl** | only tl keeps off the statue |

All holds clear the 1.5s minimum. **No beat-map hold defects.**

---

## The measurement that changed the answer

`scripts/probe_frames.py corner` scores a chip rect in **frame** coordinates. On a
`|full` beat the shipped clip *is* the frame, so the raw command is exact. On a
`|split` beat it is not: `Short.tsx` cover-fits the clip into a 1080×1056 top pane,
so source rows 432–1488 land at frame rows 0–1056 (1:1) and **frame rows 1056–1920
are the host layer, not the clip at all**.

Running the prescribed command straight at a `|split` source therefore scores pixels
the episode never shows — the same failure mode as probing a padded window. So for
S1 and S2 the deciding numbers come from a rebuilt composite (real top-pane crop +
host pane, magenta divider, Short.tsx geometry). Both numbers are recorded in
`step_chips.json` so the divergence is auditable:

| chip | corner | raw source | composite | verdict |
|------|--------|-----------|-----------|---------|
| S1 | tl | 0.0000 | **0.0648** | raw says clean; the frame says it's on the reply line |
| S1 | bl | 0.0002 | **0.3128** | raw is measuring rows that get cropped away |
| S2 | bl | 0.0427 | **0.3074** | raw bl/br are phantoms — those rows don't exist in frame |
| S3 | all | 0.0000 | 0.0000 | `\|full`, so raw == composite. Nothing is a stand-in. |

## F1 — the chat mock's chip-clear zone is real, but the split crop moves it

The brief said a non-zero score on a graphic authored chip-clear means *something
moved* — investigate, don't accept. Investigated:

- Raw probe of the shipped `chat_mock_hold.mp4` over the exact cut window:
  **tl 0.0000 / tr 0.0000 / bl 0.0002 / br 0.0002.** The card honours the convention.
- Same window on the composite: **tl 0.0648 / tr 0.0739.**

What moved is the pane, not the art. The 432px top crop maps the frame's tl/tr rect
onto source y602–678, which is the assistant's reply bubble. The control confirms it:
`glyph_delegation.mp4` plays `|full` and scores **0.0000 on all four corners**.

Fix options are in `step_chips.json` findings. This cut takes the host-pane placement;
re-authoring the card's clear bands at source y602–678 / y1716–1792 is the alternative
and belongs to that asset, not this one.

## Score ranks, ink decides (Ep11)

**S1** — tl (0.0648) is numerically five times cleaner than bl (0.3128), and it is the
wrong answer. tl slices the top half off *"Compared 6 sellers on ONLINE STORE."* — the
exact "compares" evidence the chip is labelling. bl's 0.3128 is a flat grey wall and
the top-left corner of a bookshelf: chrome. The host's head begins ~390px below the
chip's lower edge.

**S2** — nothing scores 0.00 on a photographic beat, so the whole decision is ink type.
tl (0.2241) is the laptop screen showing the store grid — the on-screen shopping the
beat teaches, and a bright ground for a light chip. bl (0.3074) is wall and bookshelf
edge. Chrome over content.

**S3** — 0.0000 everywhere. bl over the equally clean tl so the three-step scaffold
holds one screen position, and so the chip reads as a caption to the PAY button
directly above it.

**C0** — tl (0.0759) is blurred window mullions behind the statue; bl (0.3795) cuts
across the statue of Justice's skirt. Score and ink agree here.

Posters use the **worst** frame of each window (max ink under the chosen rect), not a
flattering one.

## Wording — what changed from the sample text and why

- **S2** was going to be `STEP 2/3 — YOU ARE THE ONE SHOPPING`. That duplicates
  emphasis window **E1** (`"the court said YOU are the one shopping"`, recommendation
  *keep*) word for word on the same beat. Reworded to a compression of **C4** verbatim:
  *"It is the user who accesses Amazon's computers…"*. The chip now adds the legal
  precision the VO simplifies instead of echoing the emphasis text. No spatial clash
  either — chip at y1284–1360, E1 at y≈730.
- **S3** was going to be `YOU KEEP THE PAY CLICK`. That rests on **C17**, which
  research.json marks *medium* confidence and **HEDGE ON AIR**. Replaced with the
  sanctioned phrasing from `banned_phrasings.use_instead`: *"…and you confirm the
  purchase."* The glyph card also already says "THIS ONE STAYS YOURS".
- **S1** kept as drafted. Backed by C13/C14/C17; it describes agent mechanics and
  asserts no legal outcome.

No chip asserts anything research.json does not carry. Nothing touches the banned
phrasings list.

## F3 — what is still blocked

S1, S2 and the compliance chip's W1b half all resolve against **`v2_host.mp4`, which
has not been rendered** (beat_map `open_items`). The host-pane numbers here come from
`host_hook.mp4` and `host_payoff.mp4` — two real renders from the same shoot, which
agree to within 0.0003 on bl. That is corroboration, not the deciding measurement.

**Re-probe S1 (4.95–8.29), S2 (13.39–15.75) and W1b (11.59–13.39) once `v2_host.mp4`
exists.** Risk is low: Short.tsx anchors the host pane `objectPosition: "center top"`
specifically to keep head-and-shoulders in frame, which puts the chip band well above
the head in both stand-ins. If the framing does change and the band lands on the face,
S1/S2 move to `tl` and F1's re-author option becomes mandatory.
