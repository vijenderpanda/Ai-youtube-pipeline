> LOCKED as **NIGHTWATCH** (00:30 IST slot) — see templates/NIGHTWATCH.LOCKED.md. This file is the design rationale; the LOCKED doc is the source of truth.

# Web Tour — template proposal v1 (PROPOSAL — NOT LOCKED — awaiting VJ pilot approval)

Status: **PROPOSAL** · target channel: claude-tricks (AI Unpacked) · 2026-08-23
References studied: youtube.com/shorts/DuDrHzaBQ3k ("Ruflow" — real-screen tours, camera punches,
white text-selection sweeps, serif-italic captions, SFX every 2-4s) + VJ's silent clone
"Repo King.mp4" (crown-drop hook, comparison table, terminal beat, gold CTA pill outro).
Format DNA only — never their identity, assets, or copy.

The clone's four gaps this template closes: NO audio → full measured SFX grammar (§5);
fade-to-black dead frames → banned (zoom punches / whip-drift / ≤200ms crossfade only);
static screenshots → RECORDED live pages (rec_web_tour.py tapes); no selection highlights →
browser-native selection sweeps glued to the tape pixels.

## Why this template (the distribution case)

| Audition signal | How this template plays it |
|---|---|
| Swipe-away (first ~2s) | HeroDrop asset already FALLING at frame 1 (motion at t=0, A1 cold-open plant), real page visible behind it. No intro, no branding card, no burned caption before 1.6s. |
| Watch-through | The tour is an open loop by construction — every punch/scroll promises the next reveal; payoff selection sweep withheld to ≥75% runtime (U8). |
| Mid-video bleed (our 4-8s knee; worst second = 6s) | KNEE EVENT authored at exactly 6.00s: the hardest zoom-punch of the video + broadband pop. Then a whoosh-marked transition every 2-4s — the eye never settles (U1 idle drift under every hold). |
| Loops (rewatches count) | Outro repo card echoes the hook frame's page; last beat holds motion (CTA pill pulse) so the loop restart doesn't read as a dead stop. |
| Reactions/subs (weakest layer) | Question CTA in the outro is indexed and answerable in 2s ("Which repo should I tour next?") — comment-first design, host-free. |
| Tail (search re-auditions forever) | The searched noun (repo/tool name) is in the TITLE and TAGS, not just the VO. Real-page tours are evergreen search objects; pinned comment carries the exact paste-able prompt (the GIVE). |

## Beat grammar (~34s ± 4)

Retention-verified ~34s target (PRODUCTION-PLAYBOOK.md §pacing); knee at 5-7s, so beats 1-3
carry the hold job. Every VO phrase gets an on-screen event ±0.5s (U2). Cut budget ≤0.45/s
or on the declared beat grid (U4). No fade-to-black anywhere.

1. **COLD-OPEN · 0-1.6s** — `cook:HeroDrop`: hero asset (crown/logo/emoji) already mid-fall at
   frame 1, real recorded page visible behind. Squash+overshoot landing, ≤12 gold dust
   particles. NO caption yet (2x-playback + tap-to-mute rule). SFX: `riser` from 0.1s into the
   landing hit.
2. **CLAIM · 1.6-6.0s** — `cook:SerifCap` claim line lands ("one command. *full autopilot.*"
   register: sans + serif-italic, ONE accent word). First `cook:WebTour` camera punch into the
   page hero/title. **KNEE EVENT at 6.00s = the hardest zoom-punch of the video + `pop`** (U9:
   loudest visual event in 4-8s; FAIL if the loudest second is 0-2s).
3. **TOUR · 6-14s** — WebTour beats: smooth scroll → focus punch → selection sweep, repeating.
   Selection sweeps are browser-real (translucent white fill, caret-led, ~0.35s/line) with a
   `pop` on each sweep start. `whoosh_up`/`whoosh_down` at every beat boundary, placed in VO
   gaps (reference law: a whoosh or pop every 2-4s without exception). Provenance strip visible.
4. **WHY IT MATTERS · 14-20s** — `cook:VsTable` A-vs-B row-reveal (max 5 rows, winning cell
   accent + pulse, loser column dims 60%). Bed swells here (-12 dB → -8 dB vs VO, the ~23s
   section turn in the reference). `pop` per row verdict, rationed.
5. **THE HOW · 20-26s** — `cook:TermRun`: ONE command types char-by-char (`keys` click cluster
   on typeStart), response lines stream with tone colors. This is the searched noun spoken +
   on screen.
6. **PAYOFF · 26-30s** — the withheld payoff selection sweep (U8: first appearance ≥75%
   runtime) — the number/phrase the title promised, selected on the real page. **Stop-and-slam
   at ~85% runtime: 140ms mix duck (--duck) → `slam`**, the loudest hit of the video.
7. **OUTRO · 30-34s** — repo card + gold CTA pill (#FFB454 — the ONLY gold moment besides the
   hero drop) + spoken question CTA, indexed and answerable in 2s. No end screens exist on
   Shorts — the pill is the CTA. Motion holds (pill pulse, drift) to the last frame.

## Locked craft params (inherited)

- Runtime ~34s ±4 · vertical 9:16 1080x1920 · master **-14 LUFS integrated, ≤-1 dBTP, LRA ≤3 LU**
- Bed: dark tonal pad, **G2 root, no drums, minor** (`assets/music/bed_webtour.mp3`, programme
  ≈ -8.3 LUFS like bed_active) · mixed **-12 dB vs VO in the hook (0-14s), swelling to -8 dB
  for the body** at the VsTable turn · no sidechain pumping — the only dynamic device is the
  single stop-and-slam duck · no tempo grid, so SFX sync to VO gaps, never to imagined beats
- VO: ElevenLabs Hrithik `ZZ5OIPIzxVJswEhc0UXt`, style 0.4, 0.4s sentence breaks, ~1.12 speed
  (VO_SPEED knob) · sentence gaps in the master cut to ≤0.3s (reference LRA 2.6 = flat read)
- TWO caption ceilings: nothing above y=132; captions anchor ≤1560 and grow UP; YouTube paints
  ~330px of its own chrome at feed size — QC the bottom third at FEED size, not in the render
- **No burned caption before 1.6s** · SerifCap: ONE accent word per line (N3), accent =
  magenta #E0218A default, gold #FFB454 rationed to crown/CTA meaning only (U6)
- Laws gate-tested on the pilot: **U1** (nothing pixel-static >1.0s — idle drift-zoom
  1.0→1.035 between punches, sheen cycle), **U2** (visual twin ±0.5s), **U4** (cut budget),
  **U8** (payoff ≥75%), **U9** (knee event at 6.00s)
- Transitions: zoom punches, whip-drift, crossfade ≤200ms. **NO fade-to-black** (dead frames
  kill retention at the 5-7s knee)
- HONESTY (header contract in WebTour.tsx): REAL recorded pages only — camera pan/zoom INTO
  the tape is allowed (framing for readability), but NEVER retime tape (no playbackRate),
  never alter/relabel vendor pixels, never fake UI text, never crop-to-mislead. Selection
  sweeps are additive overlays exactly like a real browser selection — tape pixels untouched,
  glyphs stay legible. Real captures keep native colors, never retinted. Provenance strip
  (MONO) default ON: `REAL SCREEN RECORDING · github.com · 2026-08-23`; any staged/local
  capture is labeled `STAGED` in strip + manifest. `containsSyntheticMedia=true` on upload ·
  "Not affiliated with Anthropic" in description · never brand as "Claude [X]"

## SFX grammar (measured from the reference)

Reference cue map (ref_audio.wav, 53.0s · spectral-flux peaks ≥2.5x local median · full
analysis in scratchpad wf1_r4): integrated -21.4 LUFS on the rip → all levels below are
RELATIVE; the template re-targets -14 LUFS and keeps the deltas.

| t (s) | strength | character | template cue |
|---|---|---|---|
| 0.1 | 5.9 | high-freq opening riser | `riser` under the cold-open |
| 2.8 | 12.0 | hard whoosh — hook transition | `whoosh_up` into the claim |
| 3.9 | 8.5 | broadband thud (hook payoff) | `pop` on HeroDrop landing / claim land |
| 6.6 | 9.6 | whoosh | knee-adjacent transition |
| 9.9→10.5 | 4.4/4.6 | whoosh → low thud pair | scroll-end + focus punch pair |
| 12.3 | 6.2 | high shimmer/whoosh | transition |
| 13.6 / 14.8 / 15.2 | 5.1-8.5 | broadband pops | highlight hits (selection/verdict) |
| 15.9 / 18.5 / 19.5 / 20.5 | 3.5-5.6 | whooshes | beat boundaries, all in VO gaps |
| **23.1** | 12.3 | **MUSIC BED SWELL** (spectral change, no level jump) | bed -12→-8 dB at the body turn — NOT a one-shot sample |
| 25.3-26.9 | 5.9-12.0 | 5-hit click/typing cluster + capping pop | `keys` on TermRun typeStart |
| 27.6 | 4.6 | whoosh | transition |
| **31.0→31.5** | **17.4**/9.4 | sharpest transient (bright snap) → whoosh pair | snap→whoosh pair on a hard reveal |
| 33.0-42.2 | 3.5-6.8 | pops + whooshes alternating | tour cadence continues |
| **45.5→45.8** | 3.3/8.5 | whoosh → **140ms DEAD-STOP (mix -29 dB)** → biggest broadband SLAM | `whoosh_down` → `--duck "45.65,45.79"` → `slam` at ~85% runtime |
| 46.8 | 5.2 | whoosh | post-slam release |
| **50.5** | 18.1 | MUSIC STING / outro section change | outro sting — music event, not a sample |

Derived grammar (the authoring rules, worked example in `films/webtour.sfx.example.json`):

| Rule | Cue | Placement |
|---|---|---|
| Every beat boundary | `whoosh_up` / `whoosh_down` | IN a VO gap (≥120ms pause), every 2-4s without exception; whooshes never land on speech |
| Every selection sweep | `pop` | ON the sweep start (`selections[].at`) — pops land on content, not in gaps |
| Terminal typing | `keys` | ON TermRun `typeStart` (5-hit high-freq cluster ~1.2s) |
| Hook payoff | `riser` | 1.2s riser resolving into the HeroDrop landing / knee punch |
| ONE per video | `slam` + `--duck` | ~85% runtime: 140ms full-mix duck (video audio ×~0.06) then the hardest hit. Never twice. |
| Levels | `gain_db` | default -9 dB vs the VO spine (kit level); per-event override allowed; SFX peaks may punch to ~VO level, nothing above it |
| Bed events | (none) | the 23.1s-style swell and outro sting are BED section changes — author them in the bed mix, never as one-shot samples |

## Capture recipe (rec_web_tour.py)

```
python3 channels/claude-tricks/rec_web_tour.py \
    --tour tours/claude_code.tour-in.json \
    --out remotion-studio/public/tapes/webtour_demo   # → .mp4 + .tour.json beside it
```

Input tour script (`--tour`):

```json
{ "url": "https://github.com/anthropics/claude-code",
  "view": "desktop",            // desktop 1280x720@2 → 1920x1080 tape; mobile 540x960@2 → 1080x1920
  "steps": [
    {"do":"wait","s":1.2},
    {"do":"scroll","to_selector":"#readme","smooth":true,"dur":1.6},
    {"do":"scroll","by":600,"smooth":true,"dur":1.0},
    {"do":"focus","selector":".about","label":"agents","hold":2.0},
    {"do":"select","selector":"#readme","text":"60+ Specialized Agents","hold":1.5},
    {"do":"click","selector":"a.file-row"} ] }
```

Output manifest (`<out>.tour.json`) — the ground truth the WebTour props are trued-up from:

```json
{ "view":{"w":1280,"h":720,"dsf":2}, "fps":30, "url":"...", "captured_at":"ISO",
  "events":[ {"t":3.2,"kind":"scroll_start","scroll_top":0},
             {"t":4.8,"kind":"scroll_end","scroll_top":612} ],
  "focus":[ {"t":5.0,"hold":2.0,"label":"agents","box":[x0,y0,x1,y1],
             "center":[cx,cy],"zoom":2.1} ],
  "selections":[ {"t":7.2,"label":"60+ Specialized Agents","scroll_top":612,
                  "rects":[[x0,y0,x1,y1]]} ] }
```

- Boxes/rects/centers normalized 0-1 to the tape frame; selection rects are per-LINE
  (Range.getClientRects), viewport-relative + the scroll_top they were captured at.
- Dark mode (color_scheme dark) is the reference look for GitHub; anonymous browsing default;
  `--redact` blurs logged-in chrome if a session is ever needed.
- Focus punches respect min gaps (PUNCH_IN .55 / PUNCH_OUT .65 / MIN_GAP 1.4) — same floors
  as record_demo's build_punches.
- Copy the manifest to `channels/claude-tricks/assets/_recordings/` for provenance.

## Episode spec recipe

An episode of this template is a normal `episodes/<ep>.v2.json` film-type spec:

```json
{ "title": "...", "tags": "...", "lines": ["..."],
  "beats": [ "cook:HeroDrop#hook", "cook:SerifCap#claim", "cook:WebTour#tour1",
             "cook:VsTable#why", "cook:TermRun#how", "cook:WebTour#payoff" ],
  "cookbook": { "tour1": { "src": "tapes/<ep>_tape.mp4", "camera": [...], "selections": [...] } },
  "music": "music/bed_webtour.mp3",
  "film": { "sfx": [ {"at":"@beat1+0.1","name":"riser"},
                     {"at":6.0,"name":"pop","_note":"knee punch"},
                     {"at":"@beat5+0.2","name":"keys"},
                     {"at":"@beat6+1.4","name":"slam","gain_db":-3} ] } }
```

- Camera/selection prop values come FROM the capture's `.tour.json` (focus boxes → `camera`
  punches via punch_from_box math; selection rects + scroll_top → `selections`). Never invent
  rects — they must map to real tape pixels.
- `"music": "music/bed_webtour.mp3"` — per-episode bed override, relative to assets/ (same
  mechanism as ep24/ep25).
- `film.sfx` events use `@beatN+x` anchors resolved on the MEASURED clock (props segment
  durations), or absolute seconds. Worked reference: `films/webtour.sfx.example.json`.
- AUTO-SFX HOOK: when `cfg["film"]["sfx"]` is present, build_ep_v2 runs sfx_mix.py on the
  built master right after the outro concat, producing `<stem>_sfx.mp4` and shipping THAT. A
  failed SFX pass prints a loud warning and ships the un-sfx master — it never kills a build.
  Manual invocation stays available:
  `python3 sfx_mix.py --manifest <film manifest> --props <props.json> --video <master>.mp4
   --out <master>_sfx.mp4 [--gain_db -9] [--duck "t0,t1"]`

## Packaging (the tail design)

- **Title:** 44-char formula (CTR 4.6% law) + 1 emoji max. The **searched noun (repo/tool
  name) must be IN the title and tags**, not just the VO. Grammar: claim-on-the-noun, e.g.
  "This GitHub Repo Runs 60+ AI Agents Free 👑" (43 chars).
- **Description line 1:** the emotional line the title doesn't carry; line 2: series promise.
  "Not affiliated with Anthropic" line. `containsSyntheticMedia=true` at upload.
- **The GIVE:** the exact paste-able command/prompt from the TermRun beat goes in the
  description AND the pinned comment (give, don't promise; API can't pin — pin manually on
  publish day, force-ssl auth done beforehand).
- **Question CTA** (outro + description): indexed, answerable in 2s — "Which repo should I
  tour next?" — comment-first, host-free.

## Cost model

VO ≈ $0.30 (ElevenLabs) · capture $0 (Playwright, anonymous, local) · render $0 (local
Remotion) · bed $0 (one-time asset) · HeyGen $0 (host-free format). **≈ $0.30/episode** —
cheapest template in the stable alongside the motion lane; built for daily-cadence economics.

## Pilot plan

Produce ONE pilot on the already-captured tape (`tapes/webtour_demo.mp4` —
github.com/anthropics/claude-code) or a stronger repo pick if VJ names one. Flow:

1. Author tour + episode spec → storyboard → **VJ approves the storyboard before ANY render**
   (standing render gate; no 4K by default — remind VJ about 4K only at finalize).
2. QC gates before arm: U1/U2/U4/U8/U9 pass on the contact sheet; knee punch verified at
   6.00s; -14 LUFS / LRA ≤3 on the master; provenance strip visible; bottom-third QC at FEED
   size; no burned caption <1.6s.
3. **Pre-committed lock criterion:** lock the template only if the pilot's 48h audition beats
   the channel median (views vs the current band AND relativeRetentionPerformance at 3s above
   the channel's recent median, with no 4-8s hold regression). Below median → one revision
   pass on the 4-8s window only; still below → park the template, keep the components (they
   register in the cookbook regardless).
