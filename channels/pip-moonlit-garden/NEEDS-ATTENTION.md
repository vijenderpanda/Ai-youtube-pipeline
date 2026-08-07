# Needs attention — Pip's Moonlit Garden (Lulla) (`lulla`) — 2026-08-07 06:37

Empty guarded publish slots: **2026-08-10, 2026-08-13, 2026-08-16**

Calendar: `channels/pip-moonlit-garden/CONTENT-CALENDAR.csv` · cadence: every 3 days 16:00 IST · slot time: 16:00 IST

## 2026-08-10 — 1 HOUR of Calm — Lulla Bedtime Songs
- **ep**: C1
- **slot_time_ist**: 16:00
- **format**: compilation
- **hook_promise**: An hour of calm — the six songs, no hard cuts
- **production_note**: BLOCKED ON INPUTS (as of 6 Aug). Spec + tooling DONE and validated end-to-end: comp/60min_calm.json = 15 segments / 3601.04s / 1:00:01; assemble_compilation.py extended with xfade_ramp + dim_tempo_scope and full-scale tested. Cannot render until (a) Leonardo API tokens are topped up for the 21 interlude stills and (b) a Suno Pro Chrome session exists for the 9 instrumental reprises. Both are account actions — see comp/README.md. Slides rather than ships degraded. MFK = yes.
- **assets**: channels/pip-moonlit-garden/comp/60min_calm.json

## 2026-08-13 — Round and Round
- **ep**: 07
- **slot_time_ist**: 16:00
- **format**: song
- **hook_promise**: TBD at kickoff
- **production_note**: HARD DATE. Lyrics written (songs/07-round-and-round.md + 07_lyrics.txt); no Suno track, no shots json, no render yet. Full Pipeline A run: Suno Pro -> Leonardo Lucid Origin seed 1926068932 -> Motion 2.0 -> Whisper-synced overlay -> assemble_synced.py.
- **assets**: channels/pip-moonlit-garden/songs/07-round-and-round.md

## 2026-08-16 — Song #08 — TBD
- **ep**: 08
- **slot_time_ist**: 16:00
- **format**: song
- **hook_promise**: TBD at kickoff
- **production_note**: HARD DATE. Song not yet written — lyrics are the first blocker. Keep to the calm-bedtime lane and the locked Lucid Origin seed.
- **assets**: TBD

Produce with: open a Claude session -> 'produce the next Lulla calendar row on Pipeline A'
