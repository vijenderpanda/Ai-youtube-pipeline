# SIGNAL — LOCKED template · data-driven host hot-take · 18:30 IST slot only

**Status: LOCKED v1 (2026-08-24).** Do not change params without a new version + a VJ sign-off.
**Codename SIGNAL** = the 18:30 IST (6:30 PM India) upload. Named to stand alone from NIGHTWATCH
(the 00:30 slot). SIGNAL is the **data-driven** template: it reads the live *signal* of what is
working right now (scout views/day + SocialBlade momentum) and fires a host-first hot-take built
from our own Remotion cookbook, styled by whichever palette family the evidence says is winning.

> **Render independence (hard rule, same as NIGHTWATCH):** SIGNAL renders ONLY from this repo's
> local Remotion cookbook (`remotion-studio/src/cookbook/`). The `research/comp-dna/` library is the
> **selection brain** (scoring + reference DNA) and the **claude.ai Design project is a review mirror
> only** — neither is ever a render input. No pixel comes from Claude Design.

## Slot & cadence
- **18:30 IST only** (= 13:00 UTC). India prime-time → **India-first framing, globally-real topics**;
  Sol speaks English (audience is Indian AI-curious, English-comfortable — matches the scout's IN lane:
  Varun Mayya / Ishan Sharma / David Ondrej all English).
- One SIGNAL short per day at this slot. Judge after 3–4 weeks, never off one video.
- Complements NIGHTWATCH (00:30, US/UK, web-tour). Two different bets, two feeds, one channel.

## Why this format (the evidence, not a guess)
From the 30-short scout + SocialBlade momentum (`research/comp-dna/scout/SCOUT.md`, 2026-08-23/24):
- **12/12 top in-lane winners are host-on-camera** (host=full). Motion-design/host-free shorts
  (Isenberg/Cole/Riley) sit at 110–176 v/day. So SIGNAL = **host-first** (Sol full/pip), always.
- **The winning accent is YELLOW, not terracotta**; the winning canvases are **night (dark+yellow)**
  and **paperYellow (off-white+yellow)** — cream is the design-flex lane, not the selection lane.
- **Cold-open claim in second 1** (no logo intro), **yellow word-highlight karaoke**, sparse **proof
  inserts** (not raw screenshots). Cheapest selected format = 19–35s single-idea take (Nate B Jones).
- **Selection is title-driven** (CTR), hold is the 4–8s job — see memory `[[retention-truth-2026-08]]`.

## The self-contained kit (Remotion cookbook — the ONLY components SIGNAL uses)
Host = **outfit_12_sol_vaibhav** (LOCKED default 2026-08-24 — Sol restyled to the Vaibhav presentation: black tee, hands gesturing, warm dark studio; keep-face NB2 edit). `wide.jpg` = hands full-frame for "host full" beats; `center.jpg` = HeyGen/EchoMimic talking-photo + PIP. outfit_11 magenta = fallback.
Palette from `kit.tsx` `PALETTES` — chosen per episode by the scoring layer (default **night**;
**paperYellow** for lighter/how-to; **cleanRed** only for a hard urgency/number claim).
Beat components, all `theme`-aware (accent = the palette's yellow unless a red/pink claim):
- **SplitHead** — cold-open claim title (label + serif-italic punch word) over/beside Sol.
- **KineticQuote** — the punch line / contrarian turn.
- **AppWindow / TermRun** — invented app/editor/terminal proof (never a real product screenshot).
- **FlowTree** — a plan/decision/harness breakdown.
- **ChipRow** — platforms/models/objections as pop-in chips (yellow `hot`, struck for dismissed).
- **StatCloser / Odometer** — the number payoff.
- **VsTable** — A-vs-B when the take is comparative.
- **BrandBumper** (`mode:"close"`) — "AI Unpacked · follow for more" CTA sting.
- Captions: yellow word-highlight karaoke (the family-B convention), bottom-third, off the low 25%.

## Host placement — LOCKED to the cutaway grammar (research-backed, auto-assigned)
From the 8-ref host-track analysis (`research/comp-dna/HOST-PLACEMENT.md`), **cutaway won** — it holds
the entire top-5 by views/day; PIP and hybrid underperformed. So SIGNAL never uses a persistent corner
PIP. **`scripts/assign_host.py` sets host per beat automatically** — no manual placement:
- **Host FULL-frame** on spoken-card beats (SplitHead claim, KineticQuote turn) + hook/close → the
  talking-head IS the shot, the caption/claim overlays on top (yellow karaoke in real render).
- **Host ABSENT** (graphic full-frame, hard cutaway) on every proof beat (FlowTree/AppWindow/TermRun/
  StatCloser/VsTable/…). The graphic is the shot.
- Cadence: don't hold host static >~8s without a graphic or a graphic >~8s without returning to host.
- Host-visible % is content-driven, not fixed (graphics-heavy 7% and talk-heavy 82% both win). Run
  `python scripts/assign_host.py <spec>.json --in-place` after building the block spec.

## Locked beat grammar (~30–40s, knee trued to 6.00s)
1. **Cold-open claim (0–~2s)** — Sol full/pip + SplitHead states the whole hot-take as a caption on
   frame 1. NO logo-motion intro. Digit/pattern break lands at **exactly 6.00s** (retention law).
2. **Setup (2–8s)** — the "but/therefore": why the obvious answer is wrong. KineticQuote or ChipRow.
3. **Proof beats (8–24s)** — 2–3 invented inserts (AppWindow/FlowTree/StatCloser) carrying the argument;
   Sol pip beside them; per-line yellow karaoke on VO stress.
4. **Payoff (≥75% runtime)** — the withheld number/answer: StatCloser or the FlowTree "active" node;
   140ms audio duck → land.
5. **BrandBumper close** — Sol CTA + follow pill.

## Gates — ALL must pass before arm
- **Packaging** ≥ **62** floor (`scripts/score_packaging.py`, wired into `finalize` arm_gate):
  44-char title formula · searched noun in title+tags+desc (not just VO) · desc line-1 ≠ title +
  GIVE-don't-promise + affiliate/AI disclosure · hook carries a trigger word. Below floor blocks arm.
- **Retention**: knee/pattern-break trued to **6.00s**; no frozen frame >0.8s uncovered; hook ≤1.6s
  (2x playback + tap-to-mute means no burned caption survives under 1.6s).
- **Honesty**: every insert serves the beat + the 4–8s hold; invented UI only; **no real third-party
  logos** (BrandBumper glyph enum only; brandmarks.ts for licensed marks); the claim/number must be
  real and India-defensible; automated-tap/superhuman timing disclosed if shown.
- **Visual lipsync** (`scripts/lipsync_visual.py`, ±80ms) on the Sol PIP.
- **Caption zone**: nothing critical below y=1500; yellow-highlight legible on the chosen canvas.

## The locked workflow (what "let's plan next" runs)
Trigger phrase: **"let's plan next"** (or "plan signal"). It runs steps 1–3 and STOPS for review.
1. **Refresh the signal** — `python scripts/comp_scout.py` (+ note SocialBlade momentum if >7 days old).
   Pull the freshest in-lane, high-views/day topics + what's cooling.
2. **Score ideas** — for each candidate brief run `python scripts/pick_asset_pack.py --topic "..."`;
   take the palette + archetype + component pack + confidence + evidence it returns.
3. **Produce 2–3 idea packages** → write `channels/claude-tricks/SIGNAL-PLAN-<date>.md`, each with:
   final **title** (+2 alts, score_packaging pre-check), **hook line**, **beat-by-beat content**,
   **description** (line-1≠title, GIVE + disclosure), **tags**, chosen **palette/archetype/components**,
   the **evidence** (which scout ref + its v/day) and **confidence**, and a **gate pre-check** table.
   **← VJ reviews these docs and approves one. No render before approval.**
4. **On approval** → build the **contact sheet**: seed a CloneReel/episode spec from the chosen pack,
   render stills (`scripts/render_clones.py` or the ep still pass) → `tapes/<ep>_contact.jpg` for a
   second look at the actual frames.
5. **On contact-sheet OK** → **render** the full episode via `build_ep_v2.py --ep <ep>` (VO + Sol PIP +
   render + master + outro + SFX). Run all gates.
6. **On VJ final OK** → `finalize_episode.py` → **arm for the 18:30 IST slot**; pin the exact-prompt/
   answer comment. Sync the master to the factory app (`scripts/sync_preview.py`).

## Naming / independence recap
SIGNAL (18:30, India, data-driven, host hot-take) ⟂ NIGHTWATCH (00:30, US/UK, web-tour, fixed format).
Both render from the local cookbook only. SIGNAL's edge = the **scoring brain** picks palette+archetype+
components+hook from *live evidence* each day, so the look tracks what's actually going viral, not a
frozen style. Update the evidence by re-running the scout; the template params here stay locked.
