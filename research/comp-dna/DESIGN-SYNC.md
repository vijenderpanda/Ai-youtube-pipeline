# Claude Design ↔ comp-dna sync

Design-system project: **Comp-DNA Shorts Library**
projectId: `52d5d30c-e886-44ee-8f49-9c1294e5faf6` (created 2026-08-23 via DesignSync)

Seeded with LIBRARY.md/json + every `<folder>/info.json` (same paths as here).

## Contract for the Claude Design cloning session
Ask it to write extractions into the project at:
  <folder>/design/theme.json      colors/type/spacing tokens
  <folder>/design/beat-map.md     hook → beats → CTA with timestamps
  <folder>/design/visual-dna.md   layout/motion/caption grammar
(same `<folder>` names as LIBRARY.md). Anything under `*/design/**` is pulled back.

## Pull (Claude Code)
"pull comp-dna from claude design" → DesignSync list_files → get_file for */design/* →
write locally → fill LIBRARY.md/json columns.
