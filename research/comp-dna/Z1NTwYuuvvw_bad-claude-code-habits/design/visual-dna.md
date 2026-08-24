## Archetype
Talking-head listicle: static webcam host + word-by-word captions + lower-third "chapter card" per item, punctuated by UI-screenshot proof inserts.

## Hook mechanic (first 3s)
Title card appears over the host's face literally on frame 1 ("bad Claude Code habits" + trash emoji) — zero verbal cold open, zero b-roll intro. The card IS the hook. Viewer knows the full content contract (a habits listicle) before a single word is spoken.

## Caption grammar
- One word revealed per second, synced to speech, bold yellow-on-black-stroke, centered, positioned just above the black lower-third card.
- No multi-word phrases held on screen — pure karaoke single-word style, high info density per second but each word is trivially readable.
- Captions and the black card coexist without overlapping (card sits lower, captions sit mid-lower).

## Information density
Very high: a new "habit" (with quantified/specific detail — "12 MCP servers", "Claude.md", "fix my repo") every ~7-10s in a 33s video = 4 habits total. Each habit gets: verbal setup → visual proof/screenshot → one-word reaction ("Terrible.", "Disgusting.") → card label. No filler, no transitions wasted, no re-explaining.

## Reusable asset components
- **Trash/chapter title card**: black rounded card, small category eyebrow label (all caps, tiny), bold headline with one italic-accent word, bottom-left corner icon (emoji or small glyph) — reusable as a themeable "point card" component for any listicle format.
- **Screenshot proof insert**: real app UI screenshot (context-window meter, file tree) cut to near-full-frame width, held ~1-2s, no frame/chrome added — reusable as "evidence insert" component.
- **Literal-metaphor cutaway**: single still/photo (trash bag, laptop on desk) used as a visual pun/beat-break, held briefly — reusable as "punch cutaway" component.
- **Word-karaoke caption bar**: single centered word, high contrast fill+stroke — standard but should be kept as its own component since position is locked relative to the card.

## Colors → content mapping notes
- Neutral warm-gray office background stays constant (real environment, not graded per beat).
- Orange/gold accent used only inside the card's italicized emphasis word (e.g. "Opus", "Claude.md", "fix my repo") — consistent accent-word convention, not full-card recoloring.
- Yellow caption color is generic default, not tied to content meaning.

## Weaknesses / what NOT to copy
- Static locked-off camera + zero zoom/motion the entire video — relies entirely on host's spoken energy and screenshot cuts to avoid feeling flat; a less charismatic host or synthetic host would need added motion/zoom-punches to compensate.
- Screenshot inserts are unlabeled/uncredited and shown very briefly (~1s) — a viewer pausing to read the context-window meter gets almost no time; fine for laugh-along audience, bad if the proof itself needs to be legible.
- No explicit spoken/graphic CTA at the end — video just stops after the last habit's reaction line. Relies on YouTube's own end-of-Short loop/next mechanics rather than an authored payoff.
- Card copy has zero punctuation/branding consistency check (mixed quoting style "fix my repo" vs no quotes on others) — minor but would need normalizing in a reusable template.
