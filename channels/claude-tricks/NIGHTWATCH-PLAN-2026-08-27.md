# NIGHTWATCH ep5 `graphify` — plan for Aug 27, 17:30 IST slot

**Status: DRAFT — awaiting VJ approval. No render until approval (standing gate).**
Swipe source: Duncan Rogoff "This Free GitHub Repo Fixes Claude Code Token Limits" (oHKt0FUbR58, 48s)
— captured + contact-sheeted at `research/learning-assets/oHKt0FUbR58_this-free-github-repo-fixes-claude-code/`.

## TITLE + IDEA (review first — standing rule)

**Lead title:** `This Free Repo Fixes Claude Code Token Burn 📉` — packaging **86/100 STRONG** (before desc pts)
**Variant:** `Claude Code Re-Reads Your Repo Every Session 🧠` — also 86 STRONG
Rejected: "111k Devs Fixed…" — 68, no hot word.

**Idea:** Claude Code silently re-reads your codebase every session — that's the token bill.
Graphify (github.com/Graphify-Labs/graphify, **110,892 stars live via API 2026-08-26**, free,
Apache-2.0, fully local) maps the repo into a knowledge graph once; Claude then queries
`graph.json` instead of re-reading files. We DON'T copy the reference's "70x fewer tokens"
slam — that number is community-reported anecdote, not on the page. We sweep only on-page
text and film the tool actually running (our differentiator: he showed marketing shots, we run it).

**Searched noun:** "claude code" (+ "token limit", "graphify" in tags) — no cannibalization with
ep1 fcc / ep2 academy / ep3 anydoc / ep4 hfagents nouns.

## VERIFIED CLAIMS (live page + API, 2026-08-26)

| Claim | Source | Sweepable verbatim? |
|---|---|---|
| 110,892 ⭐ / 10.8k forks | GitHub API + page counter | ✓ star counter focus |
| Free, Apache-2.0, local, no LLM for code | README bullets | ✓ "Code maps for free, fully local." |
| knowledge graph "query instead of grepping" | README hero line | ✓ swept |
| `uv tool install graphifyy` → `graphify install` → `/graphify .` | README install block | ✓ swept |
| graph.json "query it anytime without re-reading your files" | README file-tree block | ✓ swept (MONEY LINE) |
| Works in Claude Code, Cursor, Codex, Gemini CLI, Copilot +15 | README | ✓ swept |
| Graph build = 0 LLM credits | README benchmarks table | on page (card beat, not sweep) |
| ~71.5x fewer tokens | community-reported anecdote (graphify.com blog says so itself) | ✗ NOT used as our claim; desc-only with attribution |

## VO (9 lines = 9 beats, PURE ENGLISH, ~76 words ≈ 30s body + sting; final in episodes/graphify.v2.json)

1. HOOK: "Claude Code re-reads your repo. Every session."
2. "A hundred ten thousand devs starred the fix."
3. "It's called Graphify. Free. It maps your codebase."
4. "Claude queries the graph. Not your files."
5. "Two commands. Then slash graphify in Claude Code."
6. "I ran it. Pure parsing. Zero L L M credits."
7. "Eleven hundred nodes. Every connection. Mapped."
8. "And Claude stops re-reading your files. It asks the graph."
9. "Link's pinned. Run it on your repo tonight."
STING outro_cta: "Follow. I find one free AI win every day. What repo should I graph next?"

## MIX-CUT v1 (VJ direction 2026-08-26: reference's light/dark mix, not a dark tape wall)

Reference rhythm (48-frame sheet): no bg family holds >4s; one claim = one designed card
(giant type + small sub-caption); numbers get their own counter cards; product gets a branded run.
Ours keeps the locked NIGHTWATCH grammar (HeroDrop open / knee ~6.00 / payoff >=75% / OutroGlass)
and adds 3 LIGHT designed beats + 1 BRIGHT real-run beat between the dark tape beats.
**Template deviation for sign-off:** SplitHead/ChipRow/StatCloser (cookbook `theme` components)
join the NIGHTWATCH kit — still 100% `remotion-studio/src/cookbook/`, no comp-dna render inputs.

**Storyboard (approval artifact): `tapes/graphify_storyboard.jpg`** — real Remotion stills with the
exact ep props + real tape frames. (StatCloser tile: the "YOU GUESSED ₹2,000" row is the Demo comp's
own default — NOT in the episode spec; the ep render shows only the 110,892 counter.)

| # | est t | beat | bg | visual | VO line |
|---|---|---|---|---|---|
| B0 | 0-3.0 | HeroDrop#hook | DARK | 🧠 crown-drop on stars-punch still | Claude Code re-reads your repo. Every session. |
| B1 | 3.0-6.4 | SplitHead#stars | **LIGHT cleanRed** | "110,892 stars. and it's *free*." | A hundred ten thousand devs starred the fix. |
| B2 | 6.4-9.8 | WebTour#tour | DARK tape | camera punch on star counter (Sol PIP); KNEE = light->dark cut + pop abs 6.0 | It's called Graphify. Free. It maps your codebase. |
| B3 | 9.8-12.8 | WebTour#graphline | DARK tape | sweep "query instead of grepping" (verbatim) | Claude queries the graph. Not your files. |
| B4 | 12.8-16.2 | ChipRow#install | **LIGHT paperYellow** | 3 chips: uv tool install graphifyy / graphify install / `/graphify .` | Two commands. Then slash graphify in Claude Code. |
| B5 | 16.2-20.3 | TermRun#run | DARK term | REAL output: "Rebuilt: 1179 nodes, 2363 edges, 98 communities" | I ran it. Pure parsing. Zero L-L-M credits. |
| B6 | 20.3-22.9 | WebTour#graphviz | **BRIGHT viz** | OUR real graph.html (psf/requests), baked cinematic push-in | Eleven hundred nodes. Every connection. Mapped. |
| B7 | 22.9-27.0 | WebTour#money | DARK tape | MONEY sweep "query it anytime without re-reading your files" + SLAM ~25.5 (>=75%) | And Claude stops re-reading your files. It asks the graph. |
| B8 | 27.0-30.4 | StatCloser#closer | **LIGHT cream** | 110,892 counter + repo chip | Link's pinned. Run it on your repo tonight. |
| OUT | 30.4-34 | sting | glass | OutroGlass Sol disc + subscribe glow | (outro_cta) |

Gate math: 9 hard cuts + sting << G4 cap 15 detected @34s. Light beats carry component motion
(no static-card freeze). G6 risk = B6 multicolor node hues -> duotone-regrade fallback at build.
G2: cuts land on line boundaries by construction (1 line : 1 beat).

## TOOLING (VJ ask 2026-08-26)

Contact sheets: installed **vcsi** (pip, free) = the premium option — proper thumbs, header
metadata, timestamps (`tapes/graphify_contact_vcsi.jpg`). PIL stays as the scripted fallback
(brew ffmpeg build here lacks drawtext; ImageMagick not installed). Standing recipe updated.

## REAL-RUN ARTIFACTS (our differentiator — he showed marketing shots, we ran it)

- `uv tool install graphifyy` on this Mac; `graphify update .` on a shallow **psf/requests** clone
  -> VERBATIM output "[graphify watch] Rebuilt: 1179 nodes, 2363 edges, 98 communities" (TermRun beat).
- `graphify_graph_tape.mp4` (18.1s, --staged): graph_show.html = our graph.html copy with brighter
  edges + baked slow push-in to the densest cluster (presentation only, same data).
- FastAPI run also done (25,684 nodes) — kept as backup; requests run is the one on screen.

## TAPE (cut 2026-08-26, no warnings)

`tapes/graphify_tape.mp4` 39.2s dark desktop; manifest `tapes/graphify_tape.tour.json`.
Focus: repo-title 4.57 / stars 7.50 (zoom 2.3) / install 24.25. Sweeps: grepping 12.25 /
free-local 15.36 / install-cmd 26.47 / money-line 30.81 / works-in 34.02. Hero still
`tapes/graphify_hero.jpg` (stars zoom). Contact sheets: `graphify_contact.jpg` (PIL),
`graphify_contact_vcsi.jpg` (vcsi — new standard tool). Second tape CUT: `graphify_graph_tape.mp4` (18.1s show camera, psf/requests run).

## PACKAGING DRAFT

Tags: `claude code, claude code tokens, token limit, graphify, knowledge graph, ai coding,
claude code tips, cursor, free ai tools, ai tips` (10)
Desc line 1 (≠title, GIVE): "The repo: github.com/Graphify-Labs/graphify — free, Apache-2.0, runs on-device."
Desc body: install commands + "Community reports like '71.5x fewer tokens' are user-reported,
not our benchmark." + "Not affiliated."
Pinned comment (GIVE): repo URL + the 3 commands + same caveat. (API can't pin — manual.)

## GATES PRE-CHECK

- score_packaging ≥62: **100/100 STRONG** (--ep graphify; channel record — fcc 88, academy 94) ✓
- knee@6.00: B1 scroll velocity peak (tape 10.3→11.6 scroll 0→1500) aligned via `from` offset ✓ plan
- payoff ≥75%: money sweep lands ~23.2–26.6 of ~34s ≈ 68–78% — SLAM at 25.8s = 76% ✓ plan
- honesty: all sweeps verbatim on-page; no unattributed benchmark claims ✓
- loudness/−14, G-gates, lipsync: at build
