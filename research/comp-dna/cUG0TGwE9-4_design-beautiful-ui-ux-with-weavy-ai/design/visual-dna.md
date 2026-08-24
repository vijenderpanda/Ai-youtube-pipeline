## Archetype
Screen-record walkthrough of an AI design tool ("prompt-chip UI tutorial") — no host, no face-cam. Entirely phone-mock screen captures + kinetic-text interstitials + generated reference imagery. Closest existing label: "tool-demo screen-record + kinetic text."

## Hook mechanic (first 3s)
Rapid montage of dense, credible-looking dark-mode screenshots (code editor, multiple phone mocks) at ~1/sec, then hard-cuts to a clean app icon card. No spoken/burned hook text captured in frames — hook is visual density + implied complexity ("this looks like a real technical tool"), then immediate simplification relief.

## Caption grammar
No traditional bottom-third burned captions. Text is delivered two ways: (1) verbatim prompt text inside a UI "prompt bar" chip (teaches by literally showing what was typed), (2) short kinetic serif/italic word reveals as standalone title cards (2-5 words, centered, sometimes built letter-by-letter with a soft blur transition in). This keeps text feeling diegetic (part of the tool) rather than editorial overlay.

## Information density
High. New visual state roughly every 1s. Nearly every beat shows a distinct UI screen, prompt, or generated asset — very little static hold time. Only the kinetic-word beats (13-19s) and the design-brief read (19-20s) slow down for comprehension. This is closer to "watch someone work" pacing than a slowed-down tutorial.

## Reusable asset components
- **Prompt-chip bar**: rounded dark pill containing typed instruction text + a small model-badge ("Sonnet 4.6") + send icon — reusable as a themeable "AI prompt input" component.
- **Phone-mock frame**: consistent bezel-less phone silhouette used for every app-state screenshot — themeable container for any UI content.
- **Flow/pipeline diagram**: small labeled nodes connected by dotted lines (Prototype→References→Personality→Anchor→Refine) — reusable "process map" component.
- **Design-brief card**: dark card with headers (Overall Character / Color / Typography) and body copy — reusable "spec sheet" component.
- **Moodboard collage**: scattered photo tiles (cassette tapes) assembling into a grid — reusable "reference collage" component.
- **Model-picker list**: small dropdown/list of AI model name chips (Ideogram v3, Opt 4o, Nano banana) — reusable "model select" component.
- **Constraint list card**: prompt card with a bold "No X / No Y / No Z" bullet list — reusable "negative-prompt rule card."
- **App icon grid**: 2-3 candidate icon options shown side by side for comparison — reusable "options comparison" component.
- **Kinetic word-reveal title card**: single word/phrase, serif italic, center screen, ink/blur transition — reusable "beat title" component.

## Colors → content mapping notes
- Dark forest green (#1F2E22-ish) = "process/tool" screens (prompts, flow diagrams, spec cards) — signals "behind the scenes."
- Warm off-white/cream (#EDE9E3) = "output/result" screens (final UI, moodboards, kinetic text) — signals "the deliverable."
- Terracotta/orange accent (#D97B52) = brand mark (butterfly icon) + starburst "personality" asset + record-dot — used sparingly as the single hot accent throughout.
- Soft teal/mint (#5FC9A8) = secondary UI accent color inside the generated app itself (mic icon, waveform) — distinguishes "the product being designed" from "the tool designing it."
This bg-swap (dark=process, light=output) is a strong, cheap, reusable rule: any clip of "typing a prompt" goes dark, any clip of "seeing a result" goes light.

## Weaknesses / what NOT to copy
- No spoken-hook text was visible burned into frames — if audio hook is weak, this format has nothing visual to fall back on in the first 1s (relies entirely on density/credibility, not curiosity-gap copy).
- Very screen-recording-native; would look flat/cheap without a genuinely polished third-party tool UI to record — hard to fake with mockups.
- Almost no on-screen numbers/stakes/proof-of-outcome (views, cost, time saved) — pure aesthetic/process demo, weaker for a "value/results" angle.
- Pacing is extremely dense (~1 cut/sec); if ported to a lower-energy channel voice it may feel frantic rather than confident.
- Zero captions accessible without sound except the kinetic word cards — bad for silent-autoplay retention outside the prompt-chip beats.
