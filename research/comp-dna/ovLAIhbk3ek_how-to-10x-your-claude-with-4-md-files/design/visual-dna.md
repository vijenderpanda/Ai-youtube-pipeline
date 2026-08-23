# Visual DNA — ovLAIhbk3ek "How to 10x your Claude with 4 .md files"

## Archetype
Talking-head + kinetic-text explainer, intercut with fake/mock Claude-chat UI screenshots. Not a real screen recording — every "app" frame is a designed motion-graphic mockup (rounded chat card, chip labels, starburst "thinking" icon) built to look like Claude's product chrome without being a literal capture.

## Hook mechanic (first 3s)
Abstract orange starburst icon on cream background morphs into a branching/tentacle graphic, paired with fragmented kinetic type ("Why / would / you") that reads as one sentence spread across cuts. No host, no product shown yet — pure curiosity gap. Host doesn't appear until ~4s, after the hook has already forced a "why" question.

## Caption grammar
- Two caption systems: (1) full-bleed kinetic word-reveal (host segments) — big serif display words, one phrase per 1s cut, italic accent on the key word (e.g. "feeding *context*"); (2) inline UI-mock text — small caption baked into the fake chat card, styled like actual product copy, not a subtitle bar.
- No caption box/pill under spoken host captions — text sits directly on the live-action frame in high-contrast serif type.
- Colored italic serif is reserved for the single "point" word of each caption line.

## Information density
Fast — 46s video, ~30+ distinct visual states (roughly 1 new element every 1-1.5s during graphic beats). Host beats are held 2-4s (breathing room), UI-mock beats cut in <1.5s bursts. Each of the 4 files gets: (a) a card reveal with 3-4 bullet contents, (b) one worked chat-UI demo. Very schema-driven — same template repeated 4x, which is what makes it fast to produce and easy for viewer to pattern-match.

## Reusable asset components
- **File chip/card**: rounded dark-green card, file icon + name (e.g. "Agents.md"), can expand to show bullet contents — themeable label/color/bullets.
- **Chat prompt-response mock**: rounded card with a "+", model name pill ("Sonnet 4.6"), user prompt line, and a dotted line down to a referenced-file chip — themeable prompt text + referenced file.
- **Starburst/node icon**: 8-12 point orange burst used as a "thinking/processing" or root-node marker; also doubles as a branching-tree hook visual.
- **Flowchart step card**: dark card with a title + sequential steps connected by dotted lines and small icons (Identify→Analyze→Breakdown→Summarize) — themeable task title + step count/labels.
- **Stacked chip list**: 3D-offset stack of pill labels (used for "reasoning styles") — themeable label set.
- **Kinetic caption overlay**: word-by-word serif reveal directly on host footage, one accent word per line in italic color.
- **Terminal/memory card**: black rounded card with cursor/quill-writing animation representing "saving to a file" — themeable filename + content lines.

## Colors → content mapping notes
- Cream/off-white (#EDE8DE-ish) = "concept/explainer" backdrop, used for hook + all standalone icon/typography beats.
- Dark green (#2F4A3C-ish) = "product/artifact" color — every file card, chat mock, and flowchart uses this same green, signaling "this is the tool," consistently, across all 4 files.
- Orange (#E8794A-ish) = single accent for energy/attention: starburst icon, italic caption keyword, node highlights. Never used for base UI chrome — purely a pointer/emphasis color.
- Black = reserved for the "memory/terminal" beat only — visually distinct to mark persistence/storage as a different kind of action from the green "reasoning" cards.

## Weaknesses / what NOT to copy
- Fake UI mockups never show a believable full Claude interface (no real message history, no scrollback) — reads as a diagram, not a screen capture; fine for speed but sacrifices some "proof" credibility vs an actual screen recording.
- Host segments are very short and interstitial (just re-anchoring beats) — almost no actual talking-head explanation carries the info; nearly all information is delivered via on-screen text/graphics. Works only if captions do 100% of the teaching work — risky if audio/attention is the sole channel.
- Card/flowchart beats blur together at 1/sec sampling (several near-duplicate frames, e.g. t=27-29, t=30-32) — the actual cut rate may be slower than it looks; don't over-copy the "cut every second" assumption without checking real frame timing.
- No explicit numbered-step/counter UI despite being a "how to" — no on-screen progress indicator (1/4, 2/4...) even though structure is a 4-item list; a lost opportunity for scannability.
