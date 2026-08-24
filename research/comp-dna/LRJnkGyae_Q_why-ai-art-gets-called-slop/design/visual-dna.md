## Archetype
Pure face-cam monologue ("talking-head opinion rant") — no b-roll, no screen recordings, no UI screenshots, single static shot for the entire 97s.

## Hook mechanic (first 3s)
A white rounded speech-bubble at the very top of frame states the video's exact question ("Why AI art gets called slop?") — functions as a persistent title/pinned-comment substitute, always visible. Host is already mid-gesture/mid-sentence at t=0 (no windup), immediate direct eye contact to camera.

## Caption grammar
1-3 word yellow pill/box bursts, bold uppercase, placed low over the chest, timed almost per-word (near word-by-word karaoke pacing, ~1 burst/sec). No full-sentence captions — fragments force the eye to keep reading, mimics speech rhythm. Occasional numbered marker ("#2") doubles as a listicle bookmark without breaking the monologue format.

## Information density
Low visual density, high verbal density — almost no graphic elements besides the title bubble + caption pill. All argument complexity is carried by speech + gesture, not by visual aids. This is a bet entirely on host charisma/authority and caption readability, not on any produced "wow" asset.

## Reusable asset components
- **Title/question bubble**: white rounded-rect chat-bubble pinned top-center, tail pointing down, holds the video's thesis statement in small text; stays on screen throughout (or at least through the hook).
- **Word-burst caption pill**: single-color (yellow) bold uppercase caption box, tight-fit, positioned over the chest/shoulder area, changes almost every word — themeable as color + font.
- **Numbered-point marker**: small in-line numeral tag ("#2") appearing mid-video to signal a listicle beat inside a monologue.

## Colors → content mapping notes
- Yellow caption pill = high-contrast against warm brown/olive room (curtain + plant background), reads instantly on mobile thumbnails.
- No accent-color semantic system (no red=warning, green=good, etc.) — color is purely a legibility choice, not a meaning code.
- Background is a real room (beige curtain, potted plant, brown leather chair) — organic/authentic aesthetic, not a branded set.

## Weaknesses / what NOT to copy
- Zero visual variety for 97 seconds — works only because of strong verbal hook + host charisma; a less charismatic host or synthetic voice would lose retention fast without any visual pattern-interrupts (no b-roll, no zoom punches, no cuts).
- No explicit CTA/end-card observed in the sampled frames — relies entirely on algorithm/channel-follow behavior, not a built payoff artifact.
- Caption pill can visually clash/overlap with host's chin in close moments — no dynamic reflow logic, just a fixed lower-third position.
- Not directly cloneable for our synthetic-host pipeline as-is: our hosts are shorter clips with cuts/b-roll; this format assumes a single unbroken authentic take, which a HeyGen/avatar render would expose as artificial if copied verbatim (uncanny valley risk over 90+ continuous seconds).
