# Needs attention — Pip's Moonlit Garden (Lulla) (`lulla`) — 2026-08-06 18:17

Empty guarded publish slots: **2026-08-10, 2026-08-13, 2026-08-16**

Calendar: `channels/pip-moonlit-garden/CONTENT-CALENDAR.csv` · cadence: every 3 days 16:00 IST · slot time: 16:00 IST

## 2026-08-10 — Lulla Bedtime Compilation — calm songs to sleep
- **ep**: C1
- **slot_time_ist**: 16:00
- **format**: compilation
- **hook_promise**: An hour of calm — the six songs, no hard cuts
- **production_note**: HARD DATE. Binds the six live episodes with assemble_compilation.py (>=2s xfade + acrossfade + loudness-match) then add_bookends.py. Needs a comp spec at channels/pip-moonlit-garden/comp/*.json and interlude beds. Long-form compilations are where real ad RPM lives (playbook §11/§13). MFK = yes.
- **assets**: channels/pip-moonlit-garden/renders/*.mp4 (six episodes)

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
