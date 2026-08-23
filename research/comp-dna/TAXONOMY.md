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

## 2b. Archetype family B — the 2026-08-23 scout cohort (what the feed actually selected in-lane)
All 12 top in-lane shorts are **host-on-camera** (host=full); none use the cream kinetic kit. Sparse proof inserts, karaoke/yellow-highlight captions, cold-open mid-sentence.
| key | label | refs | v/day range | use when |
|---|---|---|---|---|
| `B1` | talking-head + kinetic stat overlays (liquid-fill, pyramid, map) | uR2JDsLZS6I | 6.5k | one shock number carries the piece |
| `B2` | doc/essay hook card → talking-head + mixed-media b-roll (archival, comic panels, chalk) | dF9bvpTy6JA, lKs6Gl_dX8w | 4–6k | 100s+ story explainers (Varun Mayya lane) |
| `B3` | talking-head + proof-card inserts (paper/tweet/repo/doc screenshot, chart-first open) | hINGU1P9Xtw, e2W5HLrj-w4, SK8SSr7-JaY, Z1NTwYuuvvw | 1–3.4k | news/hot-take with receipts; listicle tips |
| `B4` | single-take monologue, zero cuts, captions only | SVNLC4NLXjA, TRIO7lBfgNQ, dx-0jU2Y0I4, rAWB8-qiVQo | 1–1.4k (+1 outlier) | 19–35s one-idea takes (Nate B Jones lane) — cheapest format that still gets selected |
| `B5` | walking selfie face-cam + screen-record proof | rkbacGroezI | 1.9k | "99% don't know this feature" tip (Ishan lane, India) |

**Read:** family A (Isenberg kit) is the *craft* reference; family B is the *selection* reference. The feed rewarded a face + a claim in the first second, not motion design. Our Sol host + cream kit = hybrid: B-style cold-open claim with host full-frame, A-style proof inserts (PhoneMock/AppWindow/StatCloser) instead of raw screenshots. Yellow word-highlight karaoke (B3/B4) is the caption convention across 7/12 winners.

### Family-B components to add to the cookbook (gap list)
★ proof-card insert (paper/tweet/repo/doc with red highlight box) · ★ word-highlight karaoke bar (yellow on white/black-stroke — we have KaraokeLine; add the yellow-highlight variant) · chart-first opener (timeline) · quote/question card over host · liquid-fill stat container · news-chyron card · circular avatar+chart PIP.

## 3. Hook mechanics observed (first 3s)
- Family B adds: `H-shock-stat`, `H-quote-card`, `H-claim-title-card` (title slapped over host frame 1), `H-yes-no-question`, `H-chart-first`, `H-verbal-gap`/`H-mid-sentence` (no card at all — 4/12 winners), `H-walking-selfie-claim`.
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
