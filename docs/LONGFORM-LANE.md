# LONG-FORM LANE — 15–20 min tutorials (claude-tricks)

**Status:** EXPLORATION. Branch point tagged `longform-branch-point` (commit d436f27, 2026-08-25).
**Rule:** contact sheets + VJ approval BEFORE any render (standing render gate). No 4K by default.

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

## Prerequisite check (what must exist before ep1 render)
1. **Horizontal compositions** — Root.tsx/Short.tsx are 1080x1920 vertical. Need a `LongForm`
   composition (1920x1080) + horizontal variants/layout pass for any cookbook components reused.
   Most of the 17 cookbook components assume portrait; audit which survive rotation.
2. **Caption system** — KaraokeLine is portrait-tuned; long-form probably wants lower-third
   captions or none (YouTube CC instead). Decide, don't port blindly.
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

## Ep1 candidate (the killer idea already exists)
"I Built and Shipped an iPhone App in 3 Hours — full build, App Store to proof."
Real MissNoMeetings tape + simulator screenshots + App Store listing as the payoff.
Alternative angles to score at planning time: HF-agents cert walkthrough (long version of ep4 plan),
"Claude Code from zero" curriculum piece.

## Resume phrase
"let's build the long-form lane" → start with prerequisite items 1+6 (composition + template row),
produce contact sheets for ep1, get VJ approval before any render.
