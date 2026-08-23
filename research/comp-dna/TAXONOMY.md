# Comp-DNA taxonomy — how an agent picks a look for planned content

Source: 10 reference Shorts (9× Greg Isenberg house style, 1× be10X ad). Per-video detail in
`<folder>/design/{theme.json,beat-map.md,visual-dna.md}`. Pick by **archetype → host → accent**.

## 1. The shared canvas (the "Isenberg kit")
| token | value | repaint? |
|---|---|---|
| `bg` | warm cream `#EAE7E0` (range #DEDAD1–#EDE9E3) | rarely — it IS the look; dark variant `#1C1C1A` only for "glass countdown / terminal" cards |
| `fg` | near-black `#1F1F1D` | no |
| `accent` | ONE of: terracotta `#E8623D` · sage `#3E8C74` · teal-mint `#5FBFA0` | **YES — this is the content dial** |
| `accent2` | muted version of accent or charcoal | follows accent |
| caption | heavy sans, sentence-case, 2–4 words on screen; italic-serif for the punch word | weight fixed, color = accent |

**Repaint rule:** content mood → accent. Money/urgency/warning → terracotta family. Calm/system/tooling → sage/teal family. Never two accents in one short. Brand/affiliate colour only on the product's own logo/UI screenshot, never on the canvas.

## 2. Archetypes (choose ONE per episode)
| key | label | host | refs | use when |
|---|---|---|---|---|
| `A1` | talking-head + UI-mockup demo | full | DirGcMXm4zw, ovLAIhbk3ek, zB5mUHSYjXA | a person's credibility sells a tool/tip; Sol pip/full works |
| `A2` | talking-head pip + kinetic case-study reel | pip | cf6WEZUVbEI | step-by-step "I did X in Y minutes" proof reels |
| `A3` | host-free kinetic-text + app-metaphor | none | VE2Uxb9Fz7I, dLS-6jn9xxc, yJK5GueSHmU | product/concept explainer, no avatar cost |
| `A4` | host-free kinetic-icon (silhouettes + geometry) | none | VSC5E0okvD4 | frameworks / mindset / decision content |
| `A5` | screen-record walkthrough + kinetic titles | none | cUG0TGwE9-4 | tool tutorials where the real UI is the star |
| `A6` | static infographic + stylus annotation | none | IFBBmwsGpUw | ad/poster-style; NOT our lane (low craft, high CTR bait) |

## 3. Hook mechanics observed (first 3s)
- `H-logo-motion` — icon/starburst → product logo → hard cut (VE2, DirG)
- `H-wordless-icon` — 3s vector motion before any text (VSC5, dLS)
- `H-object-3d` — relatable 3D object + incomplete 2nd-person line (yJK5)
- `H-crt-boot` — retro monitor boot text + countdown (cf6W)
- `H-curiosity-type` — abstract kinetic type "Why would you…" (ovLA)
- `H-dense-montage-relief` — rapid dark screenshots → clean simple card (cUG0)
- `H-poster-claim` — payoff stat already rendered, hand mid-underline (IFBB)
- `H-mid-sentence` — no card, series continuity (zB5m) — weakest

## 4. Reusable asset components (build once, themeable by `accent`)
Grouped by role. ★ = appears in ≥3 refs → build first.
**Frames/mocks:** ★ phone mockup (iMessage/app) · ★ fake app window / chat-UI mock · terminal/command card · code-editor screenshot frame · mini app-window · vault/note-list mock · social-post / ad mock
**Diagrams:** ★ node tree / flowchart step card · ★ hub-and-spoke radial · branching decision path · icon-branch flowchart · assembly-line row · funnel/filter · icon-to-icon connector loop · 5-column ladder
**Cards:** ★ stat/number closer card · quadrant value-matrix · 3-tier pricing table · citation card · 2-option comparison · before/after (approve/deny) · checkbox decision-test row · objection pill list · design-brief spec card
**Type:** ★ kinetic word-build title card · split headline (sans label + italic-serif punch) · editorial statement slide · serif chapter title
**Chrome:** ★ pill/chip (label, model-pill, platform badge, prompt-chip bar) · persistent CTA banner · dark glass countdown card · brand bumper card · progress/settings pill bar
**Characters:** mascot icon loop (teal robot) · silhouette actor · 3D floating object · stylus/hand annotation layer
**Motion:** starburst/node particle reveal · 3D tumbling icon cluster · icon-orbit constellation · vertical smear/funnel transition · squiggly connector line

## 5. Mapping to our pipeline
Already have (Remotion cookbook, 17 comps): KaraokeLine, DiffReveal, KineticQuote, SpinWheel, LedgerFlow, ReactionMeter, Fogline… → covers Type + some Cards.
**Gap to build (priority):** phone mockup frame · chat-UI mock · node-tree/flowchart card · hub-spoke radial · stat closer card · pill/chip system · brand bumper. All take `accent` + `bg` props from `theme.json`.

## 6. Selection recipe for an agent
1. Content type → archetype (§2). 2. Host budget? (full/pip → A1/A2; none → A3–A5). 3. Mood → accent (§1 repaint rule). 4. Pick hook mechanic (§3) that matches the first line of VO. 5. Pull components (§4) by beat role from the matching ref's `beat-map.md`. 6. Avoid §6 weaknesses listed per ref in `visual-dna.md`.
