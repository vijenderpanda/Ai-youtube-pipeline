# design-sync notes — AI Unpacked Motion Cookbook

Project: https://claude.ai/design/p/8a24b4d5-f061-44df-90bb-e913dd9ae2d0
Shape: `package`. Source: `remotion-studio/`, entry `src/designsystem.tsx` → `dist/`.

## This is not an ordinary design system — read this first
Every component in `src/cookbook` is a **Remotion** component: it reads
`useCurrentFrame()` / `useVideoConfig()`, which only resolve inside a Remotion
timeline. Imported into plain React they THROW. `src/designsystem.tsx` therefore
exports **`MotionStage`**, which mounts any of them inside `@remotion/player` so
they render AND animate on a web page. That is not an export hack — it is
genuinely how you embed one of these, so it is the honest thing for the design
agent to build with.

## Gotchas that cost real time
- **`autoPlay` alone screenshots frame 0.** Most components animate IN, so frame
  0 is deliberately empty and the card reads as broken. ALWAYS pass
  `initialFrame` as well — `autoPlay` + `initialFrame` gives a live card AND a
  representative still. Every authored preview follows this.
- **The repo ships its own canonical props.** All 25 components export a
  `<name>Demo` object that production beats were authored against; these are
  re-exported from `designsystem.tsx`. Use them — never invent props.
- **`remotion-studio/package.json` had no `main`/`module`/`types`**, so
  `exportedNames()` looked for a root `index.d.ts` that does not exist and found
  ZERO components. Those fields are now set and must stay set.
- **There was no build.** `tsconfig.build.json` + `npm run build` (tsc) now emit
  `dist/` with declarations. Re-run it before any re-sync (`cfg.buildCmd`).
- **No CSS anywhere** — components are inline-styled, so `[CSS_RUNTIME]` is
  expected and non-blocking. Fonts are the exception: `public/fonts/fonts.css`
  supplies real `@font-face` for Anton and Playfair, wired via `cfg.extraFonts`.
  Without it every card silently falls back to a system font.

## Known render warns (triaged, not new)
- `MotionStage` floor card renders blank — correct: it is a wrapper with no
  component until a preview supplies one. Needs its own authored preview.
- KineticQuote's three cells look similar at a glance; they are at frames
  70/70/110 and genuinely differ. Do not chase `variantsIdentical` there.

## Re-sync risks
- `dist/` is gitignored-adjacent build output; a fresh clone MUST run
  `npm i && npm run build` in `remotion-studio/` before the converter.
- `@remotion/player` is now a direct dep of remotion-studio. React is 19.2.8
  there and 18.3.1 in `webapp/` — if a preview ever throws a hooks/dedupe error,
  that mismatch is the first suspect (the factory Composition Designer hit it).
- 22 components are still on the floor card. They are authorable incrementally
  on any re-sync; verified ones carry forward via the uploaded `_ds_sync.json`.
