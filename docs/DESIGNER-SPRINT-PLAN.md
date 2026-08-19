# Composition Designer — Sprint Plan

> **Status: LOCKED 2026-08-19 (VJ).** IA confirmed: Design=Templates · Plan=Calendar ·
> Produce=Studio · Arm=Publish. Archiving `/assets` + `/generators`. Building Sprint 1.
> Mockups: [Designer screen](https://claude.ai/code/artifact/00c63bab-fea8-41b6-81b0-f67512bd5acc) ·
> [Factory Flow](https://claude.ai/code/artifact/4f9405fc-3c00-49db-97b3-83fc8518fc6a).

> Scope: **option #2 — the full block designer, + layout axis + produce loop.** Design a
> composition as an ordered **sequence** of typed blocks, each with a chosen **layout**
> (spatial arrangement — host position, caption/#tag position, b-roll region) + theme +
> per-block config (host HeyGen id, caption style, cookbook b-roll). **Lock** → a named
> composition (many can exist). Then per content piece: **pick a locked composition →
> auto-generate frames** (auto-pick b-roll recorded/visual via `pickCookbook`, auto-fill
> values) → **review (same layout as the designer) or auto-mode** → swap/Preview low-res →
> **Finalize → Arm**. Plan-gated: **mockups → you lock this plan → we build.**
>
> **Two design axes (not one):** SEQUENCE (temporal order) × LAYOUT (spatial slots per scene).
> Today's beat kinds (`pipCallout`/`splitWide`/`framedHost`/`recFull`) are *already* named
> layouts — the layout library seeds from those + new ones, decoupling "which layout" from
> "what fills its slots".
>
> Grounded in the 5-subsystem architecture map (2026-08-19). Key finding: the composition
> is **already** a data-driven block sequence (`Short.props.segments[]`), and the existing
> `statBars` segment (native in-comp `<StatBars/>`) is the exact precedent — so this
> **extends** the cast/template-version system, it does **not** rewrite it.

## What one Short actually produces (the asset bundle → Remotion)
The composition assembles a bundle of generated assets. The designer chooses the ENGINES + look;
the plan stage generates the assets from a real script and shows the whole manifest.
| Asset | Engine (paid / free-local) | Drives |
|---|---|---|
| **VO** | ElevenLabs (paid) / **CosyVoice2** (free, local GPU) | **the timeline** — segment durations from `<break 0.4s>` + **karaoke word timings** |
| Captions | derived from the VO `.words.json` | on-screen karaoke (styled here, not authored) |
| **Host clips** | **HeyGen** (paid) / **EchoMimic** (free, local RTX 3060) | host beats — audio-driven talking head lip-synced to the VO |
| B-roll | recorded (`capture_demo`) / cookbook (TS) | visual beats |
| **Hook/cover image** | **Leonardo** (Chrome) / **FLUX-schnell** (free, Windows GPU) | opener illustration |
| StatBars / cards | native Remotion | data beats |
| Music bed | file + gain, ducked under VO | audio bed |
| Outro sting + Cover/hook | locked sting; baked (PIL) or illustration | outro / opener |
| Theme | preset (classic/bold/minimal) | the look |

**VO is the clock.** Change a script line → VO regenerates → durations + captions shift. So block
durations in the designer are *placeholders*; the plan stage's VO sets the real timing.

**Free-first, regen paid.** Each generated asset defaults to its free-local engine (CosyVoice2 ·
EchoMimic · FLUX) and can be **regenerated per-asset** on the paid tool (ElevenLabs · HeyGen ·
Leonardo) if the quality isn't good enough — zero cloud spend unless asked. Engines map to the
existing routers `vo_render.py` / `avatar_render.py` (shipped `007e3e8`: `echomimic_local` default
→ HeyGen auto-fallback, pinned to the Windows worker) / `img_render`. The **coordinated flip** —
pointing `build_ep_v2` at those routers instead of calling HeyGen/ElevenLabs directly — is S2 work.

## Preview vs render — the Remotion integration
- **In-app preview (low-res, instant, free):** embed **`@remotion/player`** (`<Player>`) — the same
  composition, bundled into the webapp, rendered **client-side in the browser** with play/scrub. This
  is the "Preview (low-res)" everywhere (designer audition + plan review). Requires the webapp to
  import the composition source; assets (host clips, VO) load by URL — a **structural** preview works
  before generation, a **full** preview once assets exist.
- **Full render (final MP4):** stays a **worker job** (`npx remotion render` via `build_ep_v2`) —
  in-browser can't render at final quality. The app's Finalize/Render enqueues it (existing path).
- **Remotion Studio** (`npx remotion studio`) stays the **local pixel-tuning tool** for authoring
  compositions — it's a dev server, not embeddable in the deployed Netlify app. We build on `@remotion/player`,
  not on Studio.

## Invariants (must hold every sprint)
- **Classic byte-identity.** `THEMES.classic` === pre-preset constants; a produce with no
  locked `_sequence` renders exactly as today. New block kinds are additive.
- **Draft-only edits.** Locked versions are immutable (409); the designer operates on a draft,
  then locks. Unlock rebuilds editable rows from the frozen composition.
- **One-select resolve.** build_ep_v2 must still resolve the whole locked cast+sequence from a
  single `factory_template_versions` row (the migration-020 design) — sequence rides in
  `composition._sequence` alongside `_settings`.
- **Auth.** Single shared `factory_token` gates all actions; validate cookbook ids server-side
  (registry is TS-only today) so a locked composition can never name an unrenderable component.

---

## Sprint 0 — Plan lock (this doc + mockups) — *now*
- Deliverables: this plan + the UI mockups (block-sequence editor, cookbook picker, host-id
  picker, caption-style editor, theme + lock).
- **Exit:** you approve the UX + data model. Nothing is built until then.

## Sprint 1 — Render foundation (Remotion): cookbook block + layout slots + proof
The de-risking step: prove a cookbook visual + a chosen layout render *inside* a real Short.
- `Short.tsx`: add `kind:"cookbook"` to `Seg` + fields `{ cookbook: { id, props, transparent? } }`.
- `cookbook/components.ts`: an `id → React.FC` map (registry.ts is metadata-only) + a
  `<CookbookBlock/>` dispatcher (placeholder on unknown id). Root.tsx demos read the same map.
- **Layout slots:** formalize the existing beat kinds as named **layout templates** — a layout =
  which regions exist and where (host / caption / #tag / b-roll) on the 1080×1920 frame. Add a
  `layout` id to `Seg` and a slot map so "which layout" is decoupled from "what fills each slot".
  `pipCallout`/`splitWide`/`framedHost`/`recFull` become the seed layouts; add a few new ones.
- Render branch mirroring `statBars`; overlay-gate per layout (a layout declares whether the
  global karaoke caption/step-chip draws, or the scene owns it).
- **Exit:** a locally-rendered Short frame with a cookbook b-roll beat in a chosen layout.

## Sprint 2 — Data + produce path (DB + build_ep_v2)
Make a locked composition drive the render — testable via SQL/API before any UI.
- Migration `023_composition_blocks.sql` (house rules: `factory_` prefix, additive, RLS no-policy
  + explicit `grant … to service_role`): `factory_template_blocks { id, template_version_id,
  position, block_type, config jsonb, cookbook_id, cookbook_demo_id, unique(tv_id, position) }`.
- Edge: `set_template_version_block` (copy of `set_template_version_asset`), freeze into
  `composition._sequence` at lock + rebuild on unlock, return `blocks[]` in `?r=template_versions`,
  add `?r=cookbook` (serves registry as JSON — one source for UI + validator).
- `build_ep_v2`: read `composition._sequence`; add a `cook:<id>` beat token + a segment branch
  (mirrors the `pip:` branch, ~1974-1995) emitting `{kind:'cookbook', component, props, dur}`.
  Theme stays the `remotion_comp` preset pick (classic/bold/minimal) — zero new code.
- **Exit:** a hand-seeded locked composition renders end-to-end through the worker (produce_preview).

## Sprint 3 — Designer UI (webapp `TemplateDetail`)
The full block designer — the screen you'll test.
- New **Sequence** section (draft-only), beside the cast rail: ordered, reorderable typed-block
  list; add / remove / duplicate / reorder. Reuses `usePoll` + `post()` + the cast-rail chrome.
- Per-block config (right panel):
  - **B-roll** → cookbook picker (reuses the Swap-drawer pattern, ranked by `pickCookbook()`),
    props form, still preview. *Or* keep the existing record-real path.
  - **Host** → HeyGen photo-avatar id picker (the `heygen_pool` set).
  - **Karaoke captions** → color / fill / style.
  - **#tag / heading / cards / statbars / outro** → their config.
  - **Theme** → classic / bold / minimal (the `remotion_comp` pick).
- Lock guard extended for blocks (missing config, unknown cookbook id, empty sequence).
- **Exit:** design a composition in the app → lock → produce_preview adheres. **The full flow.**

## Sprint 4 — Adherence, audition & polish
- `produce_preview` stamps the active composition version so calendar/Studio-driven produces
  honor the locked sequence (lift the `produce_channel` activeVersion lookup).
- In-designer + in-review live preview via `@remotion/player` (client-side, no API cost) — see
  "Preview vs render" above. A separate "Render" enqueues the full worker render.
- Boilerplate vs redesign-from-existing (both already in the version lifecycle: fork a fresh
  draft or edit an existing one).
- Built-vs-locked reconciliation for blocks (mirror the cast reconciliation).

## Sprint 5 — Plan → Produce loop (the switch you flip per content piece)
Turn a planned content piece into a produced Short through a chosen locked composition.
- **Pick a composition:** at plan time (per calendar row) choose which locked composition to run
  the piece through (a dropdown over the channel's locked composition library).
- **Auto-compose the first cut:** from the channel's analysis (which beats/types it needs, and
  where) the model *creates the scene sequence* and picks best-fit layouts + components + assets
  from the library — a strong first cut with no manual assembly. (Auto-pilot, one step earlier: it
  composes, not just fills.)
- **Auto-generate frames + manifest:** for each beat, `pickCookbook(beatIntent)` auto-selects the
  b-roll (recorded vs cookbook visual) and **auto-fills** values from the script/data; the produce
  shows a **generation manifest** — every asset it will make (VO, captions, host clips, hook image,
  b-roll, statbars, music, outro/cover), each **linked to its scene(s)** — with low-confidence beats
  flagged for review.
- **Review = designer-consistent WYSIWYG, previewed inline:** the board renders each beat in the
  SAME layout the designer showed; the assembled first cut **plays inline via `@remotion/player`**
  (client-side, free). Per beat: swap asset/component, **↻ Regen** (free again or paid), **Preview**.
- **Auto-mode switch:** one toggle runs all beats auto with minimal review. *Auto still stops at
  the arm gate — publishing to YouTube stays an explicit go (irreversible + public).*
- **Finalize → Arm:** on approval, finalize the render and arm/schedule it (extends the existing
  finalize/arm path). Consistency guarantee: designer layout === review layout === produced frame.

---

## Surface-by-surface change map (reference)
| Surface | File(s) | Change |
|---|---|---|
| Composition | `remotion-studio/src/Short.tsx`, new `cookbook/components.ts` | `cookbook` Seg kind + dispatcher + render branch + overlay gate |
| Produce | `channels/claude-tricks/build_ep_v2.py` | read `_sequence`; `cook:<id>` token + segment branch |
| DB | `supabase/migrations/023_composition_blocks.sql` | `factory_template_blocks` (+ maybe `factory_cookbook`) |
| Edge | `supabase/functions/factory-api/index.ts` | `set_template_version_block`, lock/unlock freeze, `blocks[]`, `?r=cookbook` |
| Webapp | `webapp/src/pages/TemplateDetail.jsx` (+ `assetCatalog.js`) | Sequence section + per-block config + cookbook picker |

## Retention guard (every layout decision)
Judge each block/layout against **"does this hold the 15s?"** — front-loaded cut, screen change
by ~4.5s, instantly-readable captions — not just "does it look good." A gorgeous composition
never rescues a weak hook.
