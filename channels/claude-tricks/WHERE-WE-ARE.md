# WHERE WE ARE — web-tour lane (resume doc) · updated 2026-08-23

Single source of truth to resume after a sign-out. All code is committed + pushed on branch
`claude/latest-pull-uvxc9q`.

## Cadence (LOCKED this week, per VJ's YouTube-revenue doc)
Two Shorts/day, ≥6h apart, English audio/titles (both slots):
- **00:30 IST → US/UK** (their afternoon/lunch + UK evening; higher CPM/RPM). Stage-1 seed in the West.
- **18:30 IST → India** (prime post-work). Verdict in the doc: "Excellent".
- Under the 3-notification/24h cap; no feed cannibalization. **Judge after 3–4 weeks, not 2 days.**

## Shipped / armed
| ep | title | slot | status | link |
|---|---|---|---|---|
| ep1 `fcc` | This Repo Gives You Claude Code FREE 👀 | 00:30 IST Aug 24 (2026-08-23T19:00Z) | **ARMED** | youtu.be/BEqvWkT5B5g |
| ep2 `academy` | Anthropic's Free AI Course Gives You A Badge 🎓 | 18:30 IST Aug 24 (2026-08-24T13:00Z) | **ARMED** | youtu.be/1PUZa8U-8Rw |

**Both Aug-24 slots ARMED.** Pin ep2's comment: academy.claude.com + "do the 7-min one first; sign in only to save progress" (API can't pin — manual).

## TEMPLATE LOCKED
**NIGHTWATCH** (`templates/NIGHTWATCH.LOCKED.md`) = the frozen web-tour template for the **00:30 IST slot only** — self-contained cookbook kit, no Comp-DNA/Claude-Design assets. The 18:30 IST (India) template is a SEPARATE template VJ sets up elsewhere. When VJ says "let's plan next", follow the LOCKED plan-next protocol: propose 2–3 scored ideas → capture tape + storyboard → render.

## The web-tour template (how to make the next one)
1. Pick topic (see backlog). Different searched noun each time (no cannibalising).
2. Verify every on-screen claim on the LIVE page (sweeps must be real pixels).
3. Tour: `tours/<ep>.json` → `rec_web_tour.py` (run with **miniconda python**: `/Users/vijenderpanda/miniconda3/bin/python3`). **DARK mode** (VJ standard). Reject cookie banner first.
4. Spec: copy `episodes/academy.v2.json` shape. Beats HeroDrop → WebTour×N (Sol PIP) → payoff; outro talking disc.
5. Storyboard (est. VO clock, wtdemo Sol placeholder) → VJ approval.
6. Render: `build_ep_v2.py --ep <ep>`; VO + HeyGen clips + disc cached after first run.
7. **True the knee to 6.00s** from measured VO (segment start + camera at+dur = 6.00). If G9 fails on a calm page, overlap the punch with a tape scroll's velocity peak (academy trick).
8. Gates: `scripts/qc_motion.py --video <master> --manifest <manifest>` — G1/G2/G4/G6/G8/G9/G12 must PASS. Loudness −14 ±0.5 / TP ≤ −1 (finalize auto-limits).
9. Sync 1080p review copy to app (bucket cap 50 MB → downscale; upload via curl, python requests stalls).
10. Finalize + arm at the slot; pin the comment.

## Standards LOCKED (apply to every episode)
- **HeroDrop = heavy crown-drop** (VJ 2026-08-23): deep anticipation, cubic plunge, deep squash, screen shake, gold impact flash + shockwave ring, fast dust. It's the shared component — all eps inherit it.
- **bed_active in-point 31.5s** default (skips the quiet intro); `music_fade_in` 0.25 for hot opens.
- Per-line karaoke beside Sol; `caption_from`=@beat1 (no burned caption on the cold open).
- TourRail beat-timeline in the void above the card; ≤3 EngagePing glows (like/comment/subscribe) on the VO words; talking-disc outro (avatarSize 300, HeyGen wide id — pip id dc9533 was pruned from HeyGen).
- Knee event at 6.00s; payoff ≥75%; one stop-and-slam ~85%.

## Gotchas (bit us; don't re-learn)
- **Interpreter:** rec_web_tour + yt_upload need google/playwright → use `/Users/vijenderpanda/miniconda3/bin/python3`. finalize now uses `sys.executable` (fixed).
- **Uploads:** python `requests` stalls on ~50 MB to Supabase storage; curl works. Bucket cap 50 MB → sync a 1080p review copy, keep the 2160 master local for finalize.
- **Backgrounding renders:** a foreground bash wait can hit the 10-min tool cap and SIGTERM the render — launch with nohup and poll, or use a background watcher. cwd resets to repo root between calls; cd explicitly.
- **EchoMimic:** 3060 worker (DESKTOP-DEIR7RS) was offline all day → outro disc uses HeyGen fallback. Wake it (reboot) if you want the free avatar track.

## Backlog (next eps, ranked)
1. **Option C** — "Claude Code vs Codex — 143K vs 95K Stars ⚔️" (banked for a Codex news hook; comment magnet; NEXT-POST-OPTIONS-2026-08-23.md).
2. Fresh scout picks — `research/comp-dna/scout/` (Social Blade momentum layer, 22-short scan). Pull a rising in-lane repo/tool/site.
3. `uR2JDsLZS6I` "how much water AI consumes" — local comp-dna ref without a `design/` extraction yet (pull via DesignSync from "Comp-DNA Shorts Library").
4. Port ★ Comp-DNA components into Remotion cookbook: PhoneMock, FlowTree, StatCloser (taxonomy §5 gap list).
5. Open spawned task `task_caf012df` — harden sync_preview large-file upload + auto true-peak in sfx_mix.

## Key files
- Plans: `NEXT-POST-OPTIONS-2026-08-23.md`, `EP2-PLAN-2026-08-24.md`
- Specs: `episodes/{fcc,academy,wtdemo}.v2.json` · Tours: `tours/{fcc,academy}.json`
- Components: `remotion-studio/src/cookbook/{HeroDrop,WebTour,TourRail,EngagePing,OutroGlass}.tsx`
- Build/finalize: `channels/claude-tricks/build_ep_v2.py`, `scripts/finalize_episode.py`, `scripts/qc_motion.py`
- Comp-DNA library: `research/comp-dna/` (+ Claude Design "Comp-DNA Shorts Library" `52d5d30c…` via DesignSync)
- Template law: `channels/claude-tricks/WEB-TOUR-TEMPLATE.md`; craft: `docs/PRODUCTION-PLAYBOOK.md`
