import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { SAFE, BRAND, SANS, MONO, rgba, clamp, coverBg, Fonts } from "./kit";

/* =============================================================================
   Fogline — an agent's PLAN shown as a lit road it is driving down. A fixed NOW
   line sits mid-frame; the plan scrolls UP through it. Steps rise out of the fog
   at the bottom (the future), sharpen as the headlights reach them, EXECUTE at
   NOW, then recede done into the mirror above.
   Cookbook role: the invented AGENT-UI wow — the sibling to DynamicIsland. Where
   DynamicIsland is "one task, watched to completion (the PRESENT)", Fogline is
   "the whole plan, with honest foresight (the FUTURE)". It is the shape for a
   beat that says *the agent knows where it's going — and admits what it doesn't
   yet*.

   THE THESIS (why this is not just a checklist)
   - Render fidelity is BOUND TO CONFIDENCE. A step's blur, dimness and level of
     detail are a direct function of how far ahead it is: c = 1 − dist/​horizon.
     Far-future steps are a blurred verb; the next step is razor-sharp with its
     params and price. The picture literally cannot look more certain than the
     plan is. In a *render* this is exact — every frame recomputes c from `frame`,
     so there is no lagging transition faking precision.
   - Detail arrives in honest order. Deep in the fog a step is one verb. Closer,
     it gains a target line; closer still, parameters and a cost; at NOW, a live
     progress fill. That mirrors how an agent genuinely resolves arguments only
     when the prior step returns.
   - HEIGHT is time. A step is as tall as it is long, and NOW travels at constant
     pixels/second, so a long step (render, capture) genuinely dwells longer at
     the line than a short one (read, pick). You watch the schedule, not a list.
   - LIGHT is the present. Certainty falls off with distance from NOW because the
     lamp at NOW is the only light source — the fog below is simply the edge of
     what's been resolved.

   9:16 SAFE: the NOW line sits at y≈980 (51%); the sharp, detail-rich near-future
   card grows downward from it and bottoms out ≈1340, clear of the y=1517 caption
   band — only decorative deep fog (no critical text) sits that low. Done cards
   recede toward the top and fade before the header. Cards are 860px wide (110px
   margins). Verbs/targets are single-line ellipsised, params one-line, so no
   string overflows. JSON-safe throughout: steps are plain strings + numbers, no
   function props. NOW parks at the plan's end and HOLDS a finished final frame.
   ========================================================================== */

export type FoglineStep = {
  /** the action, e.g. "Draft the script" (single line — ellipsised if long). */
  verb: string;
  /** the target/detail, revealed as it nears, e.g. "180 words · grade 5". */
  detail?: string;
  /** parameters, revealed closer still, e.g. "temp 0.7 · but/therefore". */
  params?: string;
  /** the outcome, shown once DONE, e.g. "178 words". */
  result?: string;
  /** relative length 1–6 (→ how TALL the step is → how long it dwells at NOW). */
  dur?: number;
  /** optional price, e.g. "$0.09" (shown from the params tier onward). */
  cost?: string;
};

export type FoglineProps = {
  /** run label shown in the HUD, e.g. "RUN 0412 · SHORT EP16". */
  runLabel?: string;
  /** the plan, in order. ~8–12 reads best; only what fits the frame is drawn. */
  steps: FoglineStep[];
  /** seconds NOW dwells crossing an average-length step (paces the whole road). */
  perStep?: number; // default 1.0
  /** how far ahead the headlights reach, in average-steps (the confidence gate). */
  horizon?: number; // default 3
  /** fractional step index NOW starts at (>0 seeds done cards above at t=0). */
  startAt?: number; // default 1.15
  /** Raise every card off the ink. Default 0 keeps the original values, which
   *  measured only ~6 luminance steps above the background — the cards read as
   *  holes rather than surfaces, and an 8s beat at YAVG 19/255 is a dead frame
   *  in a feed. 0.5-0.7 gives the fogged cards material presence while leaving
   *  blur = confidence intact: you can see THAT a step exists, not WHAT it says. */
  lift?: number;
  /** Chrome tint for COMPLETED steps. Default keeps them cold; a distinct tone
   *  separates done from not-yet-reached, which otherwise look identical. */
  doneTone?: string;
  /** currency symbol for the SPEND readout. Defaults to "$" (API costs are
   *  dollar-denominated). Set "\u20b9" for an India-facing episode — a dollar
   *  figure in front of a 98.8%-India audience reads as someone else's video. */
  currency?: string;
  /** decimals on SPEND. 2 for cents; 0 when the real answer is a whole zero. */
  spendDecimals?: number;
  accent?: string; // brand accent (defaults to Sol magenta)
  ink?: string; // base fill
  start?: number; // seconds before the road begins moving
  width?: number;
  height?: number;
  transparent?: boolean; // skip the backdrop (overlay use inside a composition)
};

/* ---- geometry ------------------------------------------------------------- */
const COL_W = 860;
const COL_X = (1080 - COL_W) / 2; // 110px margins
const NOW_Y = 980; // the headlight line (51% of 1920 — near-future stays off captions)
const GAP = 22;
const H_BASE = 120; // height of a dur=1 step
const H_PER = 46; // extra px per dur unit
const MAX_BLUR = 6.4;
const OK = "#37E0B0"; // a stable success tint (semantic, not the accent)
const COLD = "#38505E"; // the color of an un-resolved (foggy) step's chrome

/** blend two #rrggbb hexes -> "#rrggbb" at t in [0,1]. Use this when the result
 *  feeds another mix(): mix() returns "rgb(...)", so nesting it silently yields
 *  NaN channels. Measured the hard way — a "lift" that darkened the frame. */
const mixHex = (a: string, b: string, t: number): string => {
  const pa = parseInt(a.replace("#", ""), 16);
  const pb = parseInt(b.replace("#", ""), 16);
  const l = (sa: number, sb: number) => Math.round(sa + (sb - sa) * clamp(t));
  const r = l((pa >> 16) & 255, (pb >> 16) & 255);
  const g = l((pa >> 8) & 255, (pb >> 8) & 255);
  const bl = l(pa & 255, pb & 255);
  return "#" + [r, g, bl].map((v) => v.toString(16).padStart(2, "0")).join("");
};

/** blend two #rrggbb hexes → "rgb(r,g,b)" at t∈[0,1]. */
const mix = (a: string, b: string, t: number): string => {
  const pa = parseInt(a.replace("#", ""), 16);
  const pb = parseInt(b.replace("#", ""), 16);
  const l = (sa: number, sb: number) => Math.round(sa + (sb - sa) * clamp(t));
  const r = l((pa >> 16) & 255, (pb >> 16) & 255);
  const g = l((pa >> 8) & 255, (pb >> 8) & 255);
  const bl = l(pa & 255, pb & 255);
  return `rgb(${r},${g},${bl})`;
};

const stepH = (dur?: number): number =>
  H_BASE + (clamp(dur ?? 1, 1, 6) - 1) * H_PER;

const fmtClock = (s: number): string => {
  const m = Math.floor(Math.max(0, s) / 60);
  const ss = Math.floor(Math.max(0, s) % 60);
  return `${m}:${ss < 10 ? "0" : ""}${ss}`;
};

export const Fogline: React.FC<FoglineProps> = ({
  runLabel = "RUN 0412 · SHORT EP16",
  steps,
  perStep = 1.0,
  horizon = 3,
  startAt = 1.15,
  lift = 0,
  doneTone = "#0C1620",
  currency = "$",
  spendDecimals = 2,
  accent = BRAND.mag,
  ink = BRAND.ink,
  start = 0.3,
  width = 1080,
  height = 1920,
  transparent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const S = steps.slice(0, 14);
  const n = Math.max(S.length, 1);

  // ── lay the plan out in world-space (cumulative tops) ────────────────────
  const heights = S.map((s) => stepH(s.dur));
  const tops: number[] = [];
  let acc = 0;
  for (let i = 0; i < n; i++) {
    tops.push(acc);
    acc += heights[i] + GAP;
  }
  const meanH = acc / n; // includes the gap — the pacing unit
  const SPEED = meanH / Math.max(perStep, 0.2); // px/sec NOW travels
  const HORIZON = Math.max(1, horizon) * meanH; // headlight reach, in px

  // ── NOW's world position (parks at the plan's end, then holds) ───────────
  const t = frame / fps - start;
  const startWorld =
    tops[Math.min(Math.floor(startAt), n - 1)] +
    (startAt % 1) * heights[Math.min(Math.floor(startAt), n - 1)];
  const endWorld = tops[n - 1] + heights[n - 1] - 1;
  const nowWorld = Math.min(startWorld + SPEED * Math.max(t, 0), endWorld);

  // ── HUD readouts — computed over the WHOLE plan (not just visible cards),
  //    so spend accumulates monotonically as steps complete even after they
  //    scroll off the top, and done/lookahead stay accurate. ───────────────
  let doneCount = 0;
  let lookCount = 0;
  let spend = 0;
  const cost = (i: number): number =>
    S[i].cost ? parseFloat(S[i].cost!.replace(/[^0-9.]/g, "")) || 0 : 0;
  for (let i = 0; i < n; i++) {
    const screenTop = tops[i] - nowWorld + NOW_Y;
    if (screenTop + heights[i] <= NOW_Y + 0.5) {
      doneCount++;
      spend += cost(i); // committed: the step has fully executed
    } else if (screenTop <= NOW_Y) {
      spend += cost(i); // in-flight: its cost is already committed
    } else if (screenTop - NOW_Y < HORIZON) {
      lookCount++; // resolved enough to be inside the headlights
    }
  }

  // ── build the visible cards (culls what's off-frame) ─────────────────────
  type Card = { i: number; y: number; h: number; c: number; state: string };
  const cards: Card[] = [];
  for (let i = 0; i < n; i++) {
    const h = heights[i];
    const screenTop = tops[i] - nowWorld + NOW_Y;
    if (screenTop + h < -60 || screenTop > height + 60) continue;
    let state: string;
    let c: number;
    if (screenTop + h <= NOW_Y + 0.5) {
      state = "done";
      c = 1;
    } else if (screenTop <= NOW_Y) {
      state = "active";
      c = 1;
    } else {
      state = "future";
      c = clamp(1 - (screenTop - NOW_Y) / HORIZON);
    }
    cards.push({ i, y: screenTop, h, c, state });
  }

  const oneLine: React.CSSProperties = {
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  };

  return (
    <AbsoluteFill
      style={{
        background: transparent ? undefined : coverBg(accent, ink),
        fontFamily: SANS,
        overflow: "hidden",
      }}
    >
      <Fonts />

      {/* the lamp — the only light source, centered on NOW, falling off downward */}
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: NOW_Y,
          width: 1500,
          height: HORIZON * 2.1,
          marginLeft: -750,
          marginTop: -HORIZON * 0.62,
          background: `radial-gradient(50% 50% at 50% 42%, ${rgba(
            accent,
            0.16
          )} 0%, ${rgba(accent, 0.05)} 40%, ${rgba(ink, 0)} 72%)`,
          pointerEvents: "none",
        }}
      />

      {/* ── the road: every visible step ─────────────────────────────────── */}
      {cards.map((card) => {
        const s = S[card.i];
        const { c, state } = card;
        const isDone = state === "done";
        const isActive = state === "active";
        const blur = isDone || isActive ? 0 : (1 - c) * MAX_BLUR;

        // done cards recede into the mirror: fade fully to 0 within ~2 card-
        // heights above NOW, so only the just-finished one or two show and
        // nothing ghosts up behind the HUD.
        const doneAbove = isDone ? NOW_Y - (card.y + card.h) : 0;
        const opacity = isDone
          ? 0.62 * clamp(1 - doneAbove / 520)
          : isActive
          ? 1
          : 0.12 + 0.88 * c;

        // detail tiers (future keys off c; done shows verb + result)
        const showDetail = isActive || isDone || c > 0.34;
        const showParams = (isActive || c > 0.62) && !isDone;
        const showFoot = (isActive || c > 0.84) && !isDone;

        // LIFT: pull each card up off the ink so a fogged step still reads as a
        // surface. Blur still carries confidence; luminance carries existence.
        const bg = isActive
          ? mix(mixHex("#0F1E28", "#2C4459", lift), accent, 0.16)
          : isDone
          ? mixHex(doneTone, "#26485A", lift)
          : mix(mixHex("#0D1720", "#243B4E", lift), accent, c * 0.08);
        const border = isActive
          ? accent
          : isDone
          ? rgba("#ffffff", 0.08 + lift * 0.16)
          : mix(COLD, accent, c * 0.5);

        // live progress inside the active step
        const frac = isActive ? clamp((NOW_Y - card.y) / card.h) : 0;

        return (
          <div
            key={s.verb + card.i}
            style={{
              position: "absolute",
              left: COL_X,
              top: card.y,
              width: COL_W,
              height: card.h,
              opacity,
              borderRadius: 18,
              background: bg,
              border: `1px solid ${border}`,
              boxShadow: isActive
                ? `0 0 0 1px ${rgba(accent, 0.4)}, 0 24px 60px -18px ${rgba(
                    accent,
                    0.5
                  )}`
                : "none",
              overflow: "hidden",
              boxSizing: "border-box",
            }}
          >
            {/* per-card blur is applied to the CONTENT, so the frame recomputes it
                every tick — blur == (1−confidence), exactly, with no transition. */}
            <div
              style={{
                position: "absolute",
                inset: 0,
                padding: "20px 24px",
                display: "flex",
                flexDirection: "column",
                gap: 8,
                filter: blur > 0.05 ? `blur(${blur}px)` : undefined,
              }}
            >
              {/* the verb — always present (a plan step is at minimum an action) */}
              <div
                style={{
                  fontFamily: MONO,
                  fontSize: 30,
                  fontWeight: 600,
                  letterSpacing: 0.4,
                  lineHeight: 1.15,
                  color: isDone
                    ? rgba(BRAND.paper, 0.5)
                    : mix(COLD, BRAND.paper, c),
                  textDecoration: undefined,
                  ...oneLine,
                }}
              >
                {s.verb}
              </div>

              {/* target / detail — arrives at the mid tier */}
              {showDetail && s.detail ? (
                <div
                  style={{
                    fontSize: 26,
                    color: rgba(BRAND.paper, 0.6),
                    lineHeight: 1.25,
                    ...oneLine,
                  }}
                >
                  {s.detail}
                </div>
              ) : null}

              {/* params — arrives closer */}
              {showParams && s.params ? (
                <div
                  style={{
                    fontFamily: MONO,
                    fontSize: 21,
                    letterSpacing: 0.2,
                    color: rgba(accent, 0.7),
                    ...oneLine,
                  }}
                >
                  {s.params}
                </div>
              ) : null}

              {/* foot: cost + duration, or the DONE result line */}
              {isDone ? (
                <div
                  style={{
                    marginTop: "auto",
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    fontFamily: MONO,
                    fontSize: 22,
                    color: OK,
                  }}
                >
                  <svg width={24} height={24} viewBox="0 0 24 24">
                    <path
                      d="M5 12.5 L10 17.5 L19 6.5"
                      fill="none"
                      stroke={OK}
                      strokeWidth={2.8}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  <span style={oneLine}>{s.result || "done"}</span>
                </div>
              ) : showFoot ? (
                <div
                  style={{
                    marginTop: "auto",
                    display: "flex",
                    gap: 18,
                    fontFamily: MONO,
                    fontSize: 21,
                    letterSpacing: 0.4,
                    color: rgba(BRAND.paper, 0.42),
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  <span>{s.cost || "free"}</span>
                  <span>{Math.round((s.dur ?? 1) * 6)}s</span>
                </div>
              ) : null}
            </div>

            {/* active: top accent bar + a live fill sweeping down the card */}
            {isActive ? (
              <>
                <div
                  style={{
                    position: "absolute",
                    left: 0,
                    right: 0,
                    top: 0,
                    height: 3,
                    background: accent,
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    left: 0,
                    bottom: 0,
                    height: 4,
                    width: `${frac * 100}%`,
                    background: accent,
                    boxShadow: `0 0 14px ${rgba(accent, 0.9)}`,
                  }}
                />
              </>
            ) : null}
          </div>
        );
      })}

      {/* fog — the un-resolved future dissolving into ink at the bottom edge */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          height: 560,
          background: `linear-gradient(180deg, ${rgba(ink, 0)} 0%, ${rgba(
            ink,
            0.72
          )} 55%, ${ink} 100%)`,
          pointerEvents: "none",
        }}
      />
      {/* a soft top fade so done cards leave cleanly under the HUD */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 0,
          height: 320,
          background: `linear-gradient(180deg, ${ink} 0%, ${rgba(
            ink,
            0.55
          )} 46%, ${rgba(ink, 0)} 100%)`,
          pointerEvents: "none",
        }}
      />

      {/* ── the NOW line — a headlight beam across the road ───────────────── */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: NOW_Y,
          height: 2,
          background: `linear-gradient(90deg, ${rgba(accent, 0)} 0%, ${rgba(
            accent,
            0.9
          )} 12%, ${rgba(accent, 0.9)} 88%, ${rgba(accent, 0)} 100%)`,
          boxShadow: `0 0 22px ${rgba(accent, 0.6)}`,
        }}
      />
      {/* NOW badge — parked in the left margin so it never collides with the
          active card that straddles the line. */}
      <div
        style={{
          position: "absolute",
          left: 24,
          top: NOW_Y - 15,
          fontFamily: MONO,
          fontSize: 19,
          letterSpacing: 3,
          fontWeight: 700,
          color: accent,
          background: rgba(ink, 0.7),
          padding: "3px 8px",
          borderRadius: 6,
          textShadow: `0 0 14px ${rgba(accent, 0.6)}`,
        }}
      >
        NOW
      </div>

      {/* ── HUD: run id + live readouts ──────────────────────────────────── */}
      <div
        style={{
          position: "absolute",
          left: COL_X,
          right: COL_X,
          top: SAFE.headerFloor + 18,
          display: "flex",
          alignItems: "center",
          gap: 20,
        }}
      >
        <span
          style={{
            width: 13,
            height: 13,
            borderRadius: 999,
            background: accent,
            boxShadow: `0 0 14px ${rgba(accent, 0.9)}`,
            transform: `scale(${1 + Math.sin((frame / fps) * 6) * 0.18})`,
          }}
        />
        <span
          style={{
            fontFamily: MONO,
            fontSize: 24,
            letterSpacing: 3,
            textTransform: "uppercase",
            color: rgba(BRAND.paper, 0.72),
            ...oneLine,
            flex: 1,
          }}
        >
          {runLabel}
        </span>
      </div>
      <div
        style={{
          position: "absolute",
          left: COL_X,
          right: COL_X,
          top: SAFE.headerFloor + 64,
          display: "flex",
          gap: 40,
          fontFamily: MONO,
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {[
          ["ELAPSED", fmtClock(Math.max(0, t))],
          // a zero here reads as "failed to load", not as "free" — when nothing
          // was spent, say the word instead of the numeral.
          ["SPEND", spend <= 0 ? "FREE" : `${currency}${spend.toFixed(spendDecimals)}`],
          ["DONE", String(doneCount)],
          ["LOOKAHEAD", `${lookCount}`],
        ].map(([k, v], idx) => (
          <div key={k}>
            <div
              style={{
                fontSize: 16,
                letterSpacing: 2,
                color: rgba(BRAND.paper, 0.36),
              }}
            >
              {k}
            </div>
            <div
              style={{
                fontSize: 30,
                fontWeight: 700,
                marginTop: 3,
                color: idx === 3 ? accent : BRAND.paper,
              }}
            >
              {v}
            </div>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

/* ---- canonical demo: an AI Short being produced, end to end ---------------- */
export const foglineDemo: FoglineProps = {
  runLabel: "RUN 0412 · SHORT EP16",
  perStep: 1.0,
  horizon: 3,
  startAt: 1.15,
  steps: [
    { verb: "Read the brief", detail: "ep16 · retention notes", params: "source: QUALITY-LEDGER.md", result: "3 constraints", dur: 1, cost: "$0.01" },
    { verb: "Pick the angle", detail: "one-line-magic, again", params: "3 candidates scored", result: "angle B · 0.71", dur: 2, cost: "$0.06" },
    { verb: "Write the hook", detail: "first 2 seconds", params: "target ≤ 9 words", result: "7 words", dur: 1, cost: "$0.04" },
    { verb: "Draft the script", detail: "180 words · grade 5", params: "temp 0.7 · but/therefore", result: "178 words", dur: 3, cost: "$0.09" },
    { verb: "Render the VO", detail: "cosyvoice2 · local GPU", params: "44.1k · style 0.4", result: "33.8s", dur: 4, cost: "$0.00" },
    { verb: "Capture the app", detail: "real device · mobile UA", params: "1080×2340 · 60fps", result: "41s raw", dur: 5, cost: "$0.00" },
    { verb: "Cut to the beat", detail: "onsets from the VO", params: "hard cuts only", result: "11 cuts", dur: 2, cost: "$0.03" },
    { verb: "Caption pass", detail: "word-level timing", params: "no ghost bleed", result: "drift 12ms", dur: 2, cost: "$0.02" },
    { verb: "Normalise loudness", detail: "target −14 LUFS", params: "true peak −1.0", result: "−14.06", dur: 1, cost: "$0.00" },
    { verb: "Render the master", detail: "h264 · 1080×1920", params: "crf 18", result: "52.4 MB", dur: 5, cost: "$0.00" },
    { verb: "Arm for 16:00 IST", detail: "unlisted → scheduled", params: "needs your yes", result: "held", dur: 2, cost: "$0.00" },
  ],
};
