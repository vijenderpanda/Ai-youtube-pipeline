# NIGHTWATCH — LOCKED template · web-tour Shorts · 17:30 IST slot only

> SLOT CHANGE (VJ 2026-08-25): daily slot moved 00:30 IST → **17:30 IST** (2026-xx-xxT12:00Z). Template content/gates unchanged; every other 00:30 reference below reads as 17:30 now.

**Status: LOCKED v1 (2026-08-24).** Do not change params without a new version + a VJ sign-off.
**Codename NIGHTWATCH** = the 00:30 IST upload that seeds the US/UK feed overnight (their afternoon/UK
evening). Named to stand alone: it uses ONLY this channel's own Remotion cookbook kit — **no
Comp-DNA / Claude-Design library assets** are part of this template. The 18:30 IST (India) template is
a SEPARATE template VJ maintains in another session; NIGHTWATCH does not touch it.

Proven on: ep1 `fcc` (youtu.be/BEqvWkT5B5g), ep2 `academy` (youtu.be/1PUZa8U-8Rw) — both armed 2026-08-24.

## Slot & cadence
- **17:30 IST only** (T12:00Z; VJ 2026-08-25). English audio/titles stay mandatory (Stage-2 global reach).
- One NIGHTWATCH short per day at this slot. Judge after 3–4 weeks, never off one video.

## The self-contained kit (Remotion cookbook — the ONLY components this template uses)
`remotion-studio/src/cookbook/`: **HeroDrop** (heavy crown-drop), **WebTour** (real recorded page +
scripted camera + selection sweeps + Sol PIP), **TourRail** (beat-timeline comet), **EngagePing**
(like/comment/subscribe glows), **OutroGlass** (talking-disc CTA card), plus VsTable/TermRun/SerifCap as
needed. Host = HeyGen outfit_11 Sol (wide id for the disc; pip id for beat PIPs). No external asset library.

## Locked beat grammar (~34s ±4)
1. **HeroDrop cold-open (0–~4s)** — a relevant emoji does the **heavy crown-drop** (deep anticipation →
   cubic plunge → deep squash → screen shake → gold impact flash → gold shockwave ring → fast dust)
   onto a real WebTour-frame still (`onSrc`). Claim caption parts land ON their VO words (`partAt`).
   No burned karaoke before the tour (`caption_from:"@beat1"`).
2. **WebTour tour beats (Sol PIP)** — real recorded page, scripted camera punches + browser-native
   selection sweeps on VERBATIM page text. Per-line karaoke beside Sol.
3. **VsTable / TermRun** where the content needs a compare or a command.
4. **Payoff** — the withheld sweep at ≥75% runtime → 140ms duck → SLAM.
5. **OutroGlass** — Sol in a **300px talking circle disc** (HeyGen clip cut from the outro VO,
   `avatarDelay 0.45`, card length = 0.45+cta+0.8 so retime ratio = 1) + spoken CTA + subscribe glow.

## Locked params
- 2160×3840 (2x), ~34s ±4, master **−14 LUFS ±0.5 / TP ≤ −1** (finalize auto-limits).
- **Bed:** `bed_active.mp3`, channel default in-point **31.5s** (skips the quiet intro), `music_gain_db` +2,
  `music_fade_in` 0.25, sidechain duck under VO. VO: ElevenLabs Hrithik `ZZ5OIPIzxVJswEhc0UXt`, style 0.4.
- **Knee event at absolute 6.00s** — the hardest punch + `pop` +2dB; on a calm page overlap the punch
  with the tape scroll's velocity peak so G9 clears 0.12 (academy trick).
- **Pings** ≤3 (EngagePing) fired on the VO words; **TourRail** stops = the beat labels.
- **Capture:** `rec_web_tour.py` (run with miniconda python), **DARK mode**, cookie banner rejected first,
  needles VERBATIM. Provenance strip ON. Real pages only — never retime/relabel/crop-to-mislead.

## Gates — ALL must pass before arm
- **Motion** (`scripts/qc_motion.py`): G1 dead-frame · G2 visual-twin · G4 cut-budget · G6 palette (≤6) ·
  G8 payoff ≥75% · G9 knee@6.00s · G12 loop.
- **Loudness:** −14 ±0.5 LUFS, TP ≤ −1 dBTP.
- **Packaging** (`scripts/score_packaging.py`, wired into `finalize` arm_gate): score ≥ **62** floor
  (title 40–50 chars · 1 emoji · hot word · number/named-thing · searched noun in title AND tags · 8–15
  tags · desc line-1 ≠ title + GIVE + disclosure · short hook w/ trigger). Below floor blocks (−−force-arm
  to override). Targets: STRONG ≥80. (fcc 88, academy 94.)
- **Arm integrity:** mirror↔registry match, title ≠ filename, VO matches script lines, thumbnail exists,
  "Not affiliated" disclosure.

## The pipeline (repeatable, in order)
1. Pick topic → verify every claim on the LIVE page.
2. `tours/<ep>.json` → `rec_web_tour.py --tour … --pre-wait 3` (miniconda py, dark). Contact-sheet the tape.
3. Hero still: render one WebTour frame → `tapes/<ep>_hero.jpg`.
4. `episodes/<ep>.v2.json` (copy `academy.v2.json` shape): beats, cookbook props from the `.tour.json`
   geometry, sfx (@beat clock), pings, tour_rail, outro_cta, desc_cta, desc_prompt.
5. Outro: synth CTA VO → HeyGen wide disc → `gen_outro_glass.py … --avatar <disc> --avatar-size 300
   --avatar-delay 0.45 --pings '[subscribe]' --dur <0.45+cta+0.8>`.
6. `build_ep_v2.py --ep <ep>` (VO + PIP clips + render + master + outro + SFX). True the knee to 6.00s
   from the measured VO; re-render.
7. Limiter pass if TP > −1; `qc_motion` + `score_packaging` must pass; cut a 1080p review copy.
8. `sync_preview` the 1080p copy (curl upload; python requests stalls on ~50 MB; bucket cap 50 MB).
9. `finalize_episode.py --ep <ep> --tag <v> --schedule <T19:00Z> --calendar-id <id>` (thumb first).
10. Pin the comment (GIVE — URL/prompt + any caveat). API can't pin — manual.

## "plan next" protocol (LOCKED behaviour; v2 — VJ 2026-08-25)
When VJ says **"let's plan next"** (for NIGHTWATCH), the flow is:
0. **PULL ANALYTICS FIRST** (ep4+ rule): current views/likes/AVP/stayed for every prior NIGHTWATCH ep
   (yt API + whatever VJ shares from Studio). Name the winner pattern in one line and derive the ideas
   from it. Known reads so far: ep2 (free + BADGE/credential + mega-brand + beginner) 5–6x ep1
   (free + dev-tool); AVP strong (47.3%) but "stayed" slightly below typical → the FIRST SECOND needs
   visual PROOF of the promise (show the result/credential immediately — YouTube's own tip).
1. **Propose 2–3 topic ideas**, each with: title (+1–2 variants), the searched noun, the real page to tour,
   why it fits the 00:30/US-UK slot, and a **`score_packaging` score** for the lead title.
2. VJ picks one (A/B allowed).
3. **Capture the tape + build the storyboard/contact sheet** (est. VO clock, placeholder PIP) for approval.
4. On approval → **render** through the pipeline above, gates, review copy.
5. On VJ OK → finalize + arm for the 00:30 slot; pin the comment.

## Interpreter / infra notes (bit us once)
- rec_web_tour + yt_upload need google/playwright → `/Users/vijenderpanda/miniconda3/bin/python3`.
  finalize uses `sys.executable` (fixed).
- Renders: launch detached (nohup) + poll; a foreground wait can hit the 10-min cap and SIGTERM the render.
- EchoMimic (free avatar) needs the 3060 worker awake; else HeyGen fallback for the disc.
