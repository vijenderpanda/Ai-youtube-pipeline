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

### Preview

```bash
cd remotion-studio && npx remotion studio
```

Open `ChatAppDemo` / `LineRevealDemo` / `CommandPaletteDemo` / `BentoGridDemo`.
Render a still to eyeball a frame:

```bash
npx remotion still BentoGridDemo out.png --frame=110
```

## Adding a component

1. Copy the shape of an existing file; keep the three exports.
2. Prefer a **novel** idea over a copy of an existing UI — the brief wants
   "wait, a card/button can be made like *this*?" invention.
3. Add a row to the Catalog above and register a `<Name>Demo` in `Root.tsx`.
4. Render a still at a representative frame; confirm nothing clips at 1080×1920
   and the point lands inside the first 15s of a real beat.

## Next (wiring — see the vision doc)

These are **inert demos** today (previewable, not yet selectable by the builder).
The path from here: formalize the composition as a typed **block sequence** so a
cookbook component is a block type with per-block config → the designer UI →
`lock → produce_preview` adheres (extends the cast/template-version system).
