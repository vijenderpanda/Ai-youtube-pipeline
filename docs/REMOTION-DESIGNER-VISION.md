# Remotion Designer + Visual Cookbook — Vision & Plan

> Recorded 2026-08-19 at the end of a long session, to resume fresh with full context.
> **Owner (VJ) decision:** the Remotion composition is the HEART of the product. The cast/asset
> system (host id, music, outro, b-roll) is plumbing that *feeds* it. Next big focus = make the
> composition a **designable thing** + build a **visual component cookbook**. This doc is the brief.

## The core reframe (VJ's, and I agree)
"Remotion is the whole game; the rest is assets." Correct **for the look** — the composition is
where a video goes from templated-AI-slop to *made*. The template/cast editing we shipped this
session is ~20% of the value; the composition is the other 80% of the *visual* quality.

**My one correction (grounded in VJ's own retention data):** it's the whole game for LOOK, half the
game for whether the look gets *watched* — the script/hook/beat-structure is co-equal (the 15s hold,
the front-loaded cut, "changing screen by ~4.5s"). BUT those retention fixes ARE composition
decisions, so refining Remotion *is* how you execute the retention learnings — as long as every
layout is judged against **"does this hold the 15s?"**, not just "does it look good?", and a gorgeous
composition is never allowed to paper over a weak hook.

## What the composition actually is
`remotion-studio/src/Short.tsx` — a React video (1080x1920) rendered frame-by-frame via
`npx remotion render <id> --props=<beat-spec json>`. `build_ep_v2.py` writes the beat spec
(`renders_out/props_ep<ep>_<tag>.json`) and renders the `remotion_comp` the cast resolves (default
`"Short"`). Components already in there: karaoke `Caption`/`PanelCaption`, `FramedHost`, `PipCallout`,
`SplitWide`, `RecFull`, `StepChip` (#tag), `GlobalHeader`, `StatBars`, `Cover`, `OutroCard`.

## The architecture to build — composition as designable blocks
A **composition template = an ordered SEQUENCE of typed blocks + a theme + per-block config.**
- **Block vocabulary:** Host (pick the HeyGen id right here), Karaoke captions (color/fill/style),
  #tag chips, Headings, **B-roll**, Cards (pipCallout/framed), StatBars, Outro sting.
- **The designer:** redesign a layout from an existing one OR start from a fresh boilerplate; a
  composition comes with a starter sequence, and you add/reorder Sequences and configure each block.
- **Lock → produce_preview adheres.** Extends the cast/template-version system already built: a
  locked *composition template* (not just a locked *cast*) is what the build renders. Same
  honor-or-refuse contract as the cast-fidelity work (see [[cast-fidelity-and-hosts]]).
- Host block config = the HeyGen photo-avatar id (the 3-face pool at `claude-tricks/assets/heygen_pool/`,
  only outfit_11/f55806a4 is short-capable today).

## B-roll — two first-class paths (VJ's split, and it's the sharp part)
1. **Real recording** — `scripts/record_demo.py` (now `--view mobile|desktop` + `--dark`), queued via
   the `capture_demo` action → registers a `demo_clip`. Authentic but constrained (login profiles,
   real-app fragility, capture time).
2. **Graphical auto-generation (THE BIG LEVER)** — generate the "screen" as animated TypeScript/React
   components. On-brand, infinite, fully controllable, no dependency on capturing real apps. This is
   where "premium" is won.

## THE VISUAL COOKBOOK (VJ's concept — the heart of the next phase)
A curated, ever-growing library of **graphical/animated Remotion components** for the b-roll/visual
section, built in TS. The bar VJ set, verbatim in spirit:
- **Animated fake app UIs** (a believable-but-invented app screen, animated).
- **Dataviz** — reveals, charts, comparisons that teach.
- **Readability components** — anything that makes the point land faster/clearer.
- **Modern UI/UX components** — either the latest real-world modern UI patterns, OR **invented by
  Claude to create a WOW + curiosity factor** — "wait, a button/card can be made like *this*?"
- It should read as **showing off UI/UX craft** — the visuals themselves become a reason to watch and
  a flex of taste.
- **My job:** do the research, and maintain a **fine, polished, "inventable" cookbook** — a documented
  set of reusable, parameterized components (each with a demo + props contract) that drop into a
  composition sequence. Novel components welcome/encouraged, not just copies of existing UIs.
- **Constraint that keeps it honest:** every component still serves the beat's message + the 15s-hold
  retention bar. Wow that doesn't aid comprehension is decoration; wow that *clarifies* is the goal.

## Already built this session (committed, but INERT until wired)
- **Style presets** `classic|bold|minimal` — one composition, a `style` prop + `THEMES` registry;
  classic byte-identical to production (MD5-proven); registered as `ShortBold`/`ShortMinimal` in
  `Root.tsx`. NOT yet registered as `remotion_comp` asset revisions and NOT the default — so the
  composer can't pick them yet. Decision pending: register as-is (subtle tonal presets) vs push
  bold/minimal much more distinct. Samples rendered; differences are currently subtle (variations
  on a theme).
- **Caption-bleed fix** — the running-caption lookup is beat-scoped, so no stray word lingers.

## Where to begin next session (concrete first steps)
1. **Prove the cookbook pattern** — research + build 3–5 flagship graphical components (an animated
   fake app UI, a dataviz reveal, an invented "wow" card/button/interaction), each a self-contained
   parameterized Remotion component with a demo composition + a props contract. Establish the
   cookbook's file/registration/documentation convention.
2. **Formalize the composition as a typed block sequence** (the beat spec already half-is this) so a
   composition = data (sequence + theme + per-block config), editable + lockable.
3. **The designer UI** — a structured block-sequence editor (arrange typed blocks + theme + per-block
   config, lock). Pragmatic path: structured editor backed by Remotion's own live-preview Studio
   (`npx remotion studio`) for pixel work — NOT a from-scratch drag-drop Figma.
4. **Wire lock → produce_preview** so a locked composition template drives the render (extends the
   template-version resolution in `build_ep_v2._bind_template_version` / `resolve_cast`).
5. Then decide the presets question (register vs push-more-distinct) in the context of the cookbook.

## Key files
- `remotion-studio/src/Short.tsx` (composition + components + THEMES), `remotion-studio/src/Root.tsx`
  (composition registry). `channels/claude-tricks/build_ep_v2.py` (beat spec → props → render, cast
  resolution). Cast/template-version system: `webapp/src/pages/TemplateDetail.jsx`, edge
  `supabase/functions/factory-api/index.ts`. Playbook craft rules: `docs/PRODUCTION-PLAYBOOK.md`.
