# HOST-PLACEMENT — research-backed grammar for where/when the host appears

Filled 2026-08-24 from a per-second host-track analysis of 8 host refs (`*/design/host-track.json`),
ranked by views/day. This removes host placement from guesswork: SIGNAL auto-assigns host per beat.

## The evidence
| ref | arch | grammar | host-vis% | host-full% | hook-full s | cadence s | pip | v/day |
|---|---|---|---|---|---|---|---|---|
| FdmpR0-XvvU | B3 | **cutaway** | 7 | 7 | 2 | 2 | none | **23,200** |
| 2ZQ4jSkiqr4 | B3 | **cutaway** | 82 | 82 | 5 | 13 | none | 15,357 |
| dF9bvpTy6JA | B2 | **cutaway** | 73 | 73 | 10 | 9 | none | 5,698 |
| lKs6Gl_dX8w | B2 | **cutaway** | 17 | 17 | 3 | 8 | none | 4,311 |
| hINGU1P9Xtw | B3 | **cutaway** | 79 | 79 | 5 | 14 | none | 3,381 |
| FtyePPCE5q0 | B3 | pip (tc) | 100 | 46 | 2 | 3 | tc | 1,779 |
| GR4cCUL51wU | B3 | cutaway* | 100 | 100 | 56 | 56 | none | 1,486 |
| SK8SSr7-JaY | B3 | hybrid (tl) | 82 | 61 | 3 | 4 | tl | 0 |

*GR4c = host full 100% with graphics as small corner insets **over** the host (no cutaway).

## The rule (LOCKED for SIGNAL)
1. **Grammar = `cutaway`.** Host is **full-frame** or **absent**, never a persistent corner PIP.
   PIP (FtyePP) and hybrid (SK8) both underperformed — do not default to them.
2. **Host is FULL-frame on:** the **hook** (host holds the frame ~2–5s at open, median 4s before the
   first graphic), any **spoken turn/transition** (the "but/therefore" pivot), and the **close/CTA** if
   spoken. In practice: the **claim/quote beats** (SplitHead, KineticQuote) = host full, text as overlay.
3. **Host is ABSENT (graphic full-frame) on:** every **proof/demo/process beat** — FlowTree, AppWindow,
   TermRun, ChatApp, StatCloser, Odometer, VsTable, BentoGrid, DiffReveal. The graphic IS the shot.
4. **Cadence:** don't hold host static >~8s without a graphic, or a graphic >~8s without returning to
   host. Median cut cadence 8.4s. Host-visible% is content-driven: graphics-heavy (FdmpR0 7%, the top
   winner) is fine; talk-heavy (2ZQ4 82%) is fine — **fit to how much you're showing, not a fixed ratio.**
5. **No corner PIP by default.** (Optional `pip-tc` circle-avatar is a dev-tips variant only, and it
   scored lower — reach for it only if a beat genuinely needs host + graphic simultaneously.)

## Auto-assignment (what the pipeline does, zero manual placement)
`assign_host_track(blocks)`: for each block, host = **"full"** if the component is a spoken card
(SplitHead, KineticQuote, SerifCap) OR the beat role is hook/setup/transition/cta-spoken; host =
**"none"** if the component is a graphic proof (FlowTree/AppWindow/TermRun/ChatApp/StatCloser/Odometer/
VsTable/BentoGrid/DiffReveal) or a standalone card (BrandBumper). This reproduces the cutaway grammar
the winners use. Encoded in `scripts/assign_host.py`; CloneReel renders `host:"full"` as the dominant
talking-head shot (text overlaid) and `host:"none"` as graphic-only.
