# LONG-FORM LANE — 15–20 min tutorials (claude-tricks)

**Status:** EXPLORATION. Branch point tagged `longform-branch-point` (commit d436f27, 2026-08-25).
**Rule:** contact sheets + VJ approval BEFORE any render (standing render gate). No 4K by default.

## MISSION (VJ 2026-08-25 — the compass for every episode)
Empower YOUNG ENGINEERS who use AI, want to use it, or tried it and got less than
they expected. Every episode proves: **in this era you can ship anything — it only
needs a little time.** Three jobs per episode:
1. PROOF — a real thing shipped, real receipts (timestamps, logs, tape).
2. SHOWCASE the built thing — market the app/product itself, features and all.
3. FLEX the factory — the video's own edit/mix/graphics are AI-produced, and we say so.
Host beats optional (HeyGen when funded); the format must stand WITHOUT a host.

## Future episode seeds (mission-fit)
- Ep2: "$0 Creator Studio" (locked ideation) — cancel the paid stack, rebuild free.
- "I gave AI my week — it shipped N things" (montage of small ships + receipts).
- "Your first agent in one evening" (HF agents cert angle from the shorts plan).
- "The loop that fixes AI's broken demos" (describe→test→paste→repeat, deep dive).
- Viewer-submitted idea → shipped live in one episode (community flywheel).

## Why
VJ ships real products fast (e.g. MissNoMeetings iOS app: idea → App Store in ~3h, 2026-08-25,
demo recording on VJ's Desktop; simulator screenshots available via the missnomeetings project
session). Long-form = the "force multiplier" story format: show the whole build, not a 34s tease.
Shorts lane stays as-is; long-form is a separate visual identity — must NOT look like the locked
shorts theme.

## Format thesis (proposed, not locked)
- 15–20 min, 1920x1080 horizontal, chaptered.
- Tutorial / build-along energy: calmer pacing, real screen tape as the spine,
  Remotion used for interstitials (chapter cards, diagrams, recap boards) — not wall-to-wall design.
- Host (Sol) sparse: intro + chapter pivots + outro only. HeyGen ≈ $0.025/sec → full-length host
  is ~$22-27/ep; sparse pip keeps it ~$3-5.
- outfit_12 is long-form-only and finally usable here.
- End screens EXIST in long-form (unlike Shorts) → cross-promote shorts + subscribe.
- Retention shape differs: intro must earn 30s, then chapter hooks every 2-3 min. New analytics
  baselines needed — do NOT reuse shorts retention laws (5-7s knee is a Shorts fact).

## What already exists (verified working 2026-08-25 — items 1+2 were NOT blocking)
The 16:9 path was built 2026-08-16 as a deliberately SEPARATE ffmpeg/PIL lane (not Remotion),
retired 2026-08-20, reactivated 2026-08-25:
- `scripts/assemble_longform.py` — 16:9 assemble spine (loudnorm -14 two-pass, xfade joins,
  YouTube chapters sidecar). **Selftest PASS** 2026-08-25.
- `channels/claude-tricks/build_longform_segment.py` — 1920x1080 segment renderer, two modes
  (host_full + screen_pip "webcam over screenshare"), karaoke captions from .words.json.
  **Proto rendered** → `channels/claude-tricks/renders/longform/seg_proto_v2.{mp4,contact.jpg}`.
- Full format spec + Vaibhav teardown: `channels/claude-tricks/LONGFORM-PLAN.md`;
  locked "$0 Creator Studio" ideation: `channels/claude-tricks/longform/EP01-IDEATION.md`.
Because this lane never touches Root.tsx/Short.tsx/build_ep_v2, the shorts lane is untouched
by construction. Remotion is optional later, for interstitials only.

## Prerequisite check (what must exist before ep1 render)
1. ~~Horizontal compositions~~ DONE — ffmpeg lane above; Remotion not required for v1.
2. **Caption/lower-third collision** — proto QC: in screen_pip mode the karaoke caption
   overlaps the static lower-third title. Fix y-offsets before production.
   Also: proto is magenta = shorts brand; lane needs its OWN palette (VJ directive).
3. **VO cost/length** — ElevenLabs 15-20 min script ≈ 2.5-3k words; check credit budget, or route
   `voice_track: cosyvoice2` (free local on RTX 3060) for drafts, paid for final.
4. **Render time/weight** — 15-20 min @1080p on the GPU worker; test a 2-min slice first for
   time-per-min + temp disk. Media lives on T5 SSD — restore via rsync before rendering.
5. **Screen tape capture** — rec_*.py tooling is portrait/Shorts-shaped; need a horizontal
   desktop-capture recipe (Claude Code terminal + simulator side-by-side works well for the
   app-build story).
6. **build_ep_v2 assumptions** — episode schema, beat grammar, finalize/arm path all assume
   Shorts (duration checks, 2x-render rule, outro card). Need `template: longform` in
   factory_templates rather than hacking the shorts path.
7. **Music bed** — a 20-min bed loop with commercial rights; current beds are 30-60s.
8. **Thumbnail pipeline** — Shorts don't need one; long-form CTR is thumbnail-driven. This is a
   NEW required asset per episode (gen from a Remotion still + text pass?).
9. **Analytics** — network_stats.py handles long-form fine, but retention curves need their own
   doc; don't let shorts laws pollute judgments.

## Locked calls (VJ 2026-08-25)
- Ep1 = MissNoMeetings 3h App Store ship story; ep2 = "$0 Creator Studio" (EP01-IDEATION).
- Lane identity = **champagne editorial** (#e4c56b, webapp Obsidian & Champagne tokens);
  magenta #E91E63 stays Shorts-only. build_longform_segment.py v3 applies it
  (accent + captions + magenta-bokeh→champagne regrade of the Sol still).

## Quality reference (VJ 2026-08-25): AI Master — "FULL Claude Course for Beginners in 2026"
youtube.com/watch?v=Fys4oHlXQmQ (~105 min, 1080p). Frames + raw in
`research/learning-assets/Fys4oHlXQmQ_*/` (gitignored). The quality DNA to match:
1. **Zoomed screencasts** — never full desktop; punch-ins on the exact UI element, text
   highlighted while spoken (their highlight = warm brown; ours = champagne).
2. **Circular webcam PiP** riding over screen tape (we have this; make PiP circular).
3. **Real human host** in a moody studio w/ mic for setup beats — the ONE thing that
   isn't synthesizable to equal quality. Options: VJ on camera / HeyGen landscape Sol /
   frozen-still degrade (current proto, weakest).
   **VJ call 2026-08-25: HeyGen landscape Sol** — generate 16:9 lip-synced Sol clips for
   host beats (sparse: intro/chapter pivots/outro, ~$3-5/ep); wallet + photo-avatar cap
   per HeyGen constraints memory. Frozen-still stays the zero-cost draft degrade.
4. **Chapter title cards** (dark, one phrase) between sections — trivial for us.
5. **Meme/illustration cutaways + big pop-text** ("MORE SPECIFIC") every ~20-40s —
   cutaway density is the pacing engine of the whole video.
6. Bar-chart / comparison-card inserts for claims (our cookbook/PIL covers this).
Gap list for "same quality": zoompan punch-in + highlight choreography in the segment
builder; circular PiP; cutaway library; host decision (VJ call).

## Ep1 candidate (the killer idea already exists)
"I Built and Shipped an iPhone App in 3 Hours — full build, App Store to proof."
Real MissNoMeetings tape + simulator screenshots + App Store listing as the payoff.
Alternative angles to score at planning time: HF-agents cert walkthrough (long version of ep4 plan),
"Claude Code from zero" curriculum piece.

## Resume phrase
"let's build the long-form lane" → start with prerequisite items 1+6 (composition + template row),
produce contact sheets for ep1, get VJ approval before any render.
