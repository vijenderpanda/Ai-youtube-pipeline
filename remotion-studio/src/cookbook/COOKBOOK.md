# The Visual Cookbook

Graphical, animated Remotion components for the **b-roll / visual section** of a
Short — animated fake app UIs, dataviz, and invented UI/UX flexes built in
TypeScript. This is the "graphical auto-generation" path from
`docs/REMOTION-DESIGNER-VISION.md`: an on-brand, infinite, fully controllable
alternative to screen-recording a real app. The visuals themselves become a
reason to watch and a flex of taste — *without* ever papering over a weak hook.

> **The honesty bar (non-negotiable):** every component serves the beat's
> message and the 15s hold. Wow that *clarifies* is the goal; wow that only
> decorates is cut. Judge each layout against "does this hold the 15s?" —
> see the Playbook (`docs/PRODUCTION-PLAYBOOK.md`) and the pacing memory.

## The convention

Every cookbook component is one self-contained file `src/cookbook/<Name>.tsx`
that exports exactly three things:

| export | what |
|--------|------|
| `type <Name>Props` | the **props contract** — documented, **JSON-serialisable** (see below) |
| `const <Name>` | a `React.FC` that **self-animates** off `useCurrentFrame`, draws at a **1080×1920 design box**, and defaults to the **brand palette** |
| `const <name>Demo` | a canonical demo payload — the QC harness props |

Then register a preview/QC composition in `src/Root.tsx`:

```tsx
import { <Name>, <name>Demo } from "./cookbook/<Name>";
// …
<Composition id="<Name>Demo" component={<Name>} durationInFrames={N*FPS}
  fps={FPS} width={1080} height={1920} defaultProps={<name>Demo} />
```

### Rules

1. **JSON-safe props only.** `build_ep_v2.py` feeds props as `--props=<json>`.
   No function props — format numbers with `prefix`/`suffix`/`decimals`, choose
   variants with string enums (e.g. `span: "2x1"`), never a callback.
2. **Brand by default, retintable.** Import tokens from `./kit` (`BRAND.mag`
   `#E0218A`, `BRAND.yellow`, `BRAND.ink`, `BRAND.cyan`). Every component takes
   an `accent` prop so a channel can retint it; the default is the Sol identity.
3. **Self-contained.** Load fonts with `<Fonts/>` from `./kit`; body/UI text uses
   the system sans (`SANS`) so headless Chromium never blocks on a web font.
   Anton (`DISPLAY`) is the big-number/heading face.
4. **9:16 safe.** Keep content off the extreme edges; keep the bottom ~21% clear
   of critical info — that band is the karaoke caption zone (see `StatBars`
   baseline note). `transparent` prop skips the backdrop for overlay use.
5. **Time-sliced, not looped.** Animate against absolute time from `start`; a
   component should read start→finish once, landing on a held final state (the
   demo `durationInFrames` gives it a beat to breathe at the end).

`kit.tsx` is the only shared dependency: tokens, `SANS`/`DISPLAY`/`MONO`/`SERIF`
stacks, `rgba()`, `clamp()`, `coverBg()`, and the `<Fonts/>` loader.

## Catalog

| Component | Cookbook role | Gist |
|-----------|---------------|------|
| **ChatApp** | fake app UI | An invented AI chat screen. Messages arrive on a schedule; user bubbles slide in, AI replies show a typing indicator then spring in; thread bottom-anchors (auto-scroll). |
| **LineReveal** | dataviz reveal | A line/area chart that draws left→right while a big Anton number counts to the leading-edge value. The trend form (StatBars is the bar form). |
| **CommandPalette** | invented wow / interaction | A glassy ⌘K palette: types a query, cascades results, highlights + "launches" the chosen row. A flex of UI taste that still teaches an action. |
| **BentoGrid** | modern UI flex / readability | A staggered-spring bento tile grid, one accent tile featured. Shows 3–6 facts at once, each on its own micro-beat; `span` packs tiles gap-free. |
| **DiffReveal** | invented / transformation | A git-style before→after: red lines strike-wipe and collapse, green lines write themselves in with a glow; filename tab + a live `+N −N` diff pill. "Vague in → sharp out." |
| **RingGauge** | dataviz (radial) | 1–3 concentric activity rings sweep-fill from 12 o'clock, staggered, over a faint track, with a counting center value + a legend of ticking %s. The ring form. |
| **Odometer** | invented micro-interaction | A big number where each digit is a slot-machine reel that rolls and settles left→right with an overshoot; optional thousands grouping, label, and ▲/▼ delta pill. |
| **OrbitNodes** | invented / spatial | A glowing hub with feature nodes fanned on an orbit ring; connector lines draw outward, chips pop in, the constellation drifts. "One input, many outputs." |
| **KineticQuote** | typography flex | A punchline assembled part-by-part (each springs up); the words that matter land in the accent color with a highlight-bar wipe. For hook / big-statement beats. |
| **NotificationStack** | invented / depth | Frosted alert cards cascade onto a fanned lock-screen pile — each older card recedes with a scale/dim/blur taper behind the crisp newest, plus a live "N NEW ALERTS" count. |
| **DynamicIsland** | device-ui / live activity | An iOS Dynamic Island pill morphs wide into a live-activity card, advances an AI task through phases with a progress bar, then pops to a checkmark "done" state. |
| **VoiceOrb** | device-ui / voice | A living glass assistant orb with a radial equalizer + sound rings; a spoken prompt transcribes in word-by-word, then the orb calms and a "got it" pill confirms. |
| **SwipeDeck** | interaction / decision | A Tinder-style option deck: weak cards fling off with a "NOPE" stamp, the winner warms to accent, scales up, and a rotated "PICKED" badge slams in. The decision reads in motion. |
| **ReactionMeter** | dataviz / measurement | WAIT → a hard snap to GREEN → a number that **arrives**: the ring draws via `stroke-dashoffset`, the digits rotate up on a 26ms stagger, then an average-human marker turns the readout into a challenge the viewer can answer. The library's Plate 09 block. |
| **SpinWheel** | interaction / chance | A decision wheel that really spins: accelerates, smears at speed, eases onto the chosen wedge, then lands with a ring flare, a wedge pop and a result pill. The cookbook's **motion-hook** — continuous movement for the swipe window. |
| **Fogline** | invented agent-UI / foresight | An agent's whole PLAN as a lit road it drives down. A fixed NOW line; steps rise out of the fog (future), sharpen as the headlights reach them, EXECUTE at NOW, recede done into the mirror. **Render fidelity is bound to confidence** — blur/dimness/detail = `1 − distance/horizon`, so the picture can't look more certain than the plan is. HEIGHT is duration; LIGHT is the present. Sibling to DynamicIsland: that's one task in the present, this is the whole future. |
| **HoloCard** | hero / depth-without-3D | One subject as a floating artifact: four layers (glow, rings, emblem, type) parallax at four depths on a slow SCRIPTED camera orbit, assembling from depth on entry. Solid-3D feel, no renderer. The low-density hero spotlight (vs. BentoGrid's dense grid). |
| **GlassPanel** | material / liquid-glass | A frosted, REFRACTIVE panel over a live color bed, carrying one hero figure + supporting rows. The refraction is BAKED (the bed re-drawn, clipped, scaled + blurred) so it survives a headless render where `backdrop-filter` can't be trusted; `transparent` mode falls back to real backdrop blur for overlay use. The 2026 "style" flex. |
| **MorphField** | interaction / CTA | One object, three states: a CTA button widens into an input field, accepts a typed value, then collapses into a confirmed pill with a drawn checkmark — no hard cuts. The single-element morph for a one-field ask (signup/capture). |

### Preview

```bash
cd remotion-studio && npx remotion studio
```

Open `ChatAppDemo` / `LineRevealDemo` / `CommandPaletteDemo` / `BentoGridDemo`.
Render a still to eyeball a frame:

```bash
npx remotion still BentoGridDemo out.png --frame=110
```

## Categorization & selection (`registry.ts`)

Each component draws one **shape** of information well. `registry.ts` is the
machine-readable catalog that lets the planner pick the right component for a
beat instead of guessing. Every entry is tagged on four axes:

- **role** — visual family: `app-ui`, `device-ui`, `dataviz`, `interaction`,
  `layout`, `typography`, `transformation`.
- **beats** — where it earns its place: `hook`, `context`, `stat`, `process`,
  `comparison`, `demo`, `punchline`, `cta`, `social-proof`.
- **needs** — the data shape it requires (the planner must supply this):
  `series`, `metrics`, `single-number`, `facts`, `before-after`, `steps`,
  `options`, `dialogue`, `phrase`, `query-results`, `hub-spokes`, `alerts`,
  `utterance`.
- plus **keywords**, **wow** (1–5), **density**, and `transparentCapable`
  (can it overlay a host/b-roll).

### Picking a component from a plan

```ts
import { pickCookbook } from "./cookbook/registry";

// beat: "the channel went from 2K to 41K views over 10 weeks"
pickCookbook({ beat: "stat", needs: "series", keywords: ["views", "growth"] });
// → [LineReveal (top), Odometer, …]  each with a score + why[]
```

Scoring is additive: **+5** exact `needs` match (the strongest signal), **+3**
if the `beat` fits, **+1** per overlapping keyword, `wow/10` as a tie-breaker.
`role`, `minWow`, and `transparent` in the intent act as hard filters. So the
planner's job is to describe each beat as a `BeatIntent` (what it's saying +
what data it has), and the registry returns the best-suited components ranked.

Selection cheat-sheet by data shape:

| The beat has… | `needs` | Best component(s) |
|---------------|---------|-------------------|
| a number over time | `series` | LineReveal |
| one big number/milestone | `single-number` | Odometer |
| a few % / progress values | `metrics` | RingGauge |
| 3-6 facts to recap | `facts` | BentoGrid |
| a messy→clean rewrite | `before-after` | DiffReveal |
| a task running in phases | `steps` | DynamicIsland (one task, present) · Fogline (whole plan, future) |
| options to sift & pick | `options` | SwipeDeck |
| a choice left to chance | `options` | SpinWheel |
| a single measured number as the payoff | `ms` | ReactionMeter |
| an AI conversation | `dialogue` | ChatApp |
| a command / search | `query-results` | CommandPalette |
| one idea → many uses | `hub-spokes` | OrbitNodes |
| a punchy statement | `phrase` | KineticQuote |
| results piling up | `alerts` | NotificationStack |
| a spoken prompt | `utterance` | VoiceOrb |

## Adding a component

1. Copy the shape of an existing file; keep the three exports.
2. Prefer a **novel** idea over a copy of an existing UI — the brief wants
   "wait, a card/button can be made like *this*?" invention.
3. Add a row to the Catalog above, register a `<Name>Demo` in `Root.tsx`, **and
   add a `registry.ts` entry** (role / beats / needs / keywords) so the planner
   can select it.
4. Render a still at a representative frame; confirm nothing clips at 1080×1920
   and the point lands inside the first 15s of a real beat.

## Next (wiring — see the vision doc)

These are **inert demos** today (previewable, not yet selectable by the builder).
The path from here: formalize the composition as a typed **block sequence** so a
cookbook component is a block type with per-block config → the designer UI →
`lock → produce_preview` adheres (extends the cast/template-version system).
