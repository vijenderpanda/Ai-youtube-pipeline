import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {
  BRAND, SANS, MONO, DISPLAY, rgba, clamp, Fonts, AuroraBed, SAFE,
} from "./kit";

/* =============================================================================
   CareerArc — the flat line that was never flat.

   THE ONE FRAME THIS COMPONENT EXISTS FOR. Everything here serves a single
   un-eased cut: scattered points SNAP into a rising arc and the dead baseline is
   overwritten. That cut is placed on the channel's worst measured second —
   6.00s, median -7.3pp, with 15 of 30 steepest drops falling in 4-8s — and it
   works because three things change on one frame and the eye's travel direction
   REVERSES: the answers have been drifting upward, and the arc reads left-to-
   right. A viewer cannot finish parsing before the next second starts.

   WHY A SNAP AND NOT A DRAW-ON. An eased path-draw is the obvious choice and it
   is wrong here: it spreads the payoff across ~20 frames, so no single frame is
   the event, and at 2x playback the whole reveal is over in 300ms of screen time
   having never been a moment. A hard cut survives 2x because it is instantaneous
   at any rate. Shorts default to muted, so the meaning has to arrive as SHAPE —
   scatter becoming order — not as a caption.

   HONESTY. This component draws no measured quantity. The points are the
   viewer's own typed answers and the arc asserts only "these went up", which is
   what the person said. There is deliberately NO axis, NO scale, NO numbers:
   a y-axis would give the shape measurement grammar it has not earned, which is
   the exact failure that killed three concepts on 2026-08-21.

   Geometry is authored for 1080x1920. SAFE.headerFloor (132) owns the top and
   the caption band owns from y=1380 down, so the plot lives in between.
   ========================================================================== */

const PLOT_L = 84;
const PLOT_R = 996;
const BASE_Y = 968;          // the dead line — just ABOVE the headline block
const TOP_Y = 330;           // ceiling — the arc climbs to the top-right corner
const HEAD_Y = 1022;         // headline starts below the line, same field

const EASE_OUT = Easing.bezier(0.16, 1, 0.3, 1);
const OUT_E = Easing.bezier(0.16, 1, 0.3, 1);
/** seeded jitter — Math.random breaks resumability, see LedgerFlow */
const jit = (i: number) => Math.sin(i * 12.9898 + 4.1414);

export type ArcPoint = {
  /** what the viewer answered. Kept short — this is a label, not a sentence. */
  label?: string;
  /** 0..1 height once plotted. NOT a measurement — a relative position the
   *  person's own answer implies. Never rendered with an axis. */
  lift: number;
  /** beat-local second the answer lands as a scattered dot. */
  at: number;
};

export type CareerArcProps = {
  points: ArcPoint[];
  /** THE frame. Beat-local seconds of the un-eased cut. */
  snapAt?: number;
  /** Seconds the COLD OPEN owns. A bright line draws on, climbs, then sags dead
   *  into the dotted baseline. Without it the component opens already-flat and
   *  the first beat is a still frame -- which on a Short is the swipe window
   *  spent on nothing. The flatness has to be something the viewer WATCHES
   *  happen, not a state they arrive to. Set 0 to disable. */
  openDur?: number;
  /** small mono line above the plot, e.g. "YOUR LAST 2 YEARS". */
  runLabel?: string;
  /** the reframe, burned big under the plot after the snap. */
  headline?: string;
  subhead?: string;
  /** shown BEFORE the snap — the problem, in the same slot the payoff takes. */
  preHeadline?: string;
  preSubhead?: string;
  /** beat-local second a glass prompt card DROPS IN. The line flinches from the
   *  impact — the spine has to react to events, not sit under them, or it stops
   *  reading as one object having one continuous experience. */
  pasteAt?: number;
  pasteText?: string[];
  /** beat-local second the arc shrinks and demotes to a header strip, handing
   *  off to whatever beat comes next. */
  demoteAt?: number;
  accent?: string;
  ink?: string;
  /** Sol's wide clip, shown as a small card. The upper-right of the plot is
   *  deliberately empty until the arc climbs into it, so a host card can live
   *  there on the early beats without ever covering the line. */
  host?: string;
  hostSize?: number;
  hostAnchor?: "tl" | "tr";
  transparent?: boolean;
  start?: number;
  width?: number;
  height?: number;
};

export const CareerArc: React.FC<CareerArcProps> = ({
  points = [],
  snapAt = 6,
  openDur = 1.5,
  runLabel,
  headline,
  subhead,
  preHeadline,
  preSubhead,
  pasteAt,
  pasteText,
  demoteAt,
  accent = BRAND.mag,
  ink = BRAND.ink,
  host,
  hostSize = 300,
  hostAnchor = "tr",
  transparent,
  start = 0,
  width = 1080,
  height = 1920,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - start;
  const P = (points || []).slice(0, 6);
  const n = Math.max(P.length, 1);

  // one un-eased boolean — this is the cut
  const snapped = t >= snapAt;
  const sinceSnap = t - snapAt;

  const xFor = (i: number) => PLOT_L + ((PLOT_R - PLOT_L) * (i + 0.6)) / (n + 0.2);
  const arcY = (p: ArcPoint) => BASE_Y - (BASE_Y - TOP_Y) * clamp(p.lift);
  /** where a point drifts BEFORE the snap: above the line, unresolved, jittered */
  // jit() is raw sin and is NEGATIVE for most low indices, so subtracting it
  // pushed the answers DOWN onto (and under) the dead line — the opposite of
  // "unresolved, hovering". Take the magnitude: every answer floats ABOVE.
  const scatterY = (p: ArcPoint, i: number) =>
    BASE_Y - 190 - Math.abs(jit(i)) * 250 - clamp(p.lift) * 40;
  /** scattered answers also drift horizontally — a tidy column reads as ordered,
   *  and "already ordered" is exactly what the snap must not look like */
  const scatterX = (i: number) => xFor(i) + jit(i + 7) * 44;

  const seatedPts = P.map((p, i) => ({ x: xFor(i), y: arcY(p) }));
  const path = seatedPts.map((s, i) => `${i ? "L" : "M"}${s.x} ${s.y}`).join(" ");
  const lastP = seatedPts[seatedPts.length - 1];
  const firstP = seatedPts[0];
  // carry the arc PAST the last node to the plot edge, so the fill closes on the
  // frame rather than on a vertical wall under the final point
  const fillPath = lastP && firstP
    ? `${path} L${PLOT_R} ${lastP.y - 26} L${PLOT_R} ${BASE_Y} L${firstP.x} ${BASE_Y} Z`
    : "";
  const linePath = lastP ? `${path} L${PLOT_R} ${lastP.y - 26}` : path;

  // after the cut the arc settles a touch — the snap is instant, the breath isn't
  const settle = snapped
    ? spring({ frame: frame - Math.round((start + snapAt) * fps), fps,
               config: { damping: 17, stiffness: 150, mass: 0.9 } })
    : 0;
  // the dead baseline is OVERWRITTEN, not hidden: it dims hard on the cut
  // ---- THE COLD OPEN -----------------------------------------------------
  // draw on, hold a beat, then collapse to the baseline and go out. `alive`
  // lerps the climb's height toward BASE_Y so the death is the SAME line
  // sagging, not a crossfade between two different graphics.
  const openOn = openDur > 0 && t < openDur * 1.35;
  const drawT = openDur > 0 ? clamp(t / (openDur * 0.40)) : 1;
  const dieT = openDur > 0 ? clamp((t - openDur * 0.52) / (openDur * 0.48)) : 1;
  const alive = 1 - OUT_E(dieT);
  const openPath = P.map((p, i) => {
    const y = BASE_Y - (BASE_Y - TOP_Y) * clamp(p.lift) * 0.62 * alive;
    return `${i ? "L" : "M"}${xFor(i)} ${y}`;
  }).join(" ");
  // the dead line arrives AS the bright one dies — one hand-off, not two events
  const baseOpacity = snapped ? 0.1 : 0.4 * (openDur > 0 ? OUT_E(dieT) : 1);
  // one-frame white flash on the cut — the "hit"
  const snapFrame = Math.round((start + snapAt) * fps);
  const hit = frame === snapFrame ? 1 : 0;

  const headIn = snapped ? 1 : 0;
  // the problem statement lands AS the line dies, not before it — the viewer
  // watches the flatline happen and THEN gets told what it means
  const preOut = snapped ? 0
    : (openDur > 0 ? OUT_E(clamp((t - openDur * 0.72) / (openDur * 0.5))) : 1);

  // ---- the spine is ALIVE, not a static rule -----------------------------
  // a line that only moves when something happens to it reads as a diagram.
  // a slow breath under everything reads as one object that is present the
  // whole time, which is the entire point of a through-line.
  const breathe = Math.sin(t * 1.15) * 3.2;

  // the card lands and the line FLINCHES — a damped ring, not a bounce
  const flinch = pasteAt == null || t < pasteAt ? 0
    : Math.exp(-(t - pasteAt) * 5.5) * Math.sin((t - pasteAt) * 26) * 22;

  // demote: the whole plot shrinks toward a header strip and hands off
  const demote = demoteAt == null ? 0 : OUT_E(clamp((t - demoteAt) / 0.75));
  const plotScale = 1 - demote * 0.42;
  const plotShiftY = -demote * 300;

  const word = (s: string, hot?: string) =>
    s.split(" ").map((w, i) => (
      <span key={i} style={{
        color: hot && w.replace(/[^A-Za-z]/g, "").toUpperCase() === hot.toUpperCase()
          ? accent : BRAND.paper,
      }}>{w}{" "}</span>
    ));

  return (
    <AbsoluteFill style={{ width, height, background: transparent ? undefined : ink }}>
      <Fonts />
      {transparent ? null : <AuroraBed t={t} accent={accent} ink={ink} opacity={0.36} />}

      {runLabel ? (
        <div style={{
          position: "absolute", left: PLOT_L, top: SAFE.headerFloor + 54,
          fontFamily: MONO, fontSize: 26, letterSpacing: 6,
          color: rgba(BRAND.paper, 0.42),
        }}>{runLabel}</div>
      ) : null}

      <svg width={width} height={height} style={{
        position: "absolute", inset: 0, zIndex: 2,
        transform: `translateY(${breathe + flinch + plotShiftY}px) scale(${plotScale})`,
        transformOrigin: "540px 470px",
      }}>
        <defs>
          <linearGradient id="ca-line" x1="0" y1="1" x2="1" y2="0">
            <stop offset="0%" stopColor={accent} />
            <stop offset="62%" stopColor="#FF5FB4" />
            <stop offset="100%" stopColor="#FFC2E4" />
          </linearGradient>
          <linearGradient id="ca-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={accent} stopOpacity={0.42} />
            <stop offset="100%" stopColor={accent} stopOpacity={0} />
          </linearGradient>
          <filter id="ca-glow" x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="14" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <filter id="ca-dot" x="-70%" y="-70%" width="240%" height="240%">
            <feGaussianBlur stdDeviation="7" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {/* the flat, dead baseline. It is never deleted — it is overwritten,
            so the viewer can still see what they thought was true. */}
        <line
          x1={PLOT_L} y1={BASE_Y} x2={PLOT_R} y2={BASE_Y}
          stroke={rgba(BRAND.paper, baseOpacity)} strokeWidth={7}
          strokeLinecap="round" strokeDasharray="1 26"
        />

        {openOn && !snapped ? (
          <path
            d={openPath} pathLength={1}
            stroke="url(#ca-line)" strokeWidth={13} fill="none"
            strokeLinecap="round" strokeLinejoin="round"
            filter="url(#ca-glow)"
            strokeDasharray={`${drawT} 1`}
            opacity={(1 - dieT * dieT) * 0.95}
          />
        ) : null}

        {snapped ? (
          <>
            <path d={fillPath} fill="url(#ca-fill)"
                  opacity={interpolate(settle, [0, 1], [0.55, 1])} />
            <path d={linePath} stroke="url(#ca-line)" strokeWidth={16} fill="none"
                  strokeLinecap="round" strokeLinejoin="round" filter="url(#ca-glow)" />
          </>
        ) : null}

        {P.map((p, i) => {
          const born = clamp((t - p.at) / 0.22);
          if (born <= 0) return null;
          const sx = snapped ? xFor(i) : scatterX(i);
          const sy = snapped ? arcY(p) : scatterY(p, i);
          const r = snapped ? 15 : 13;
          return (
            <g key={i} opacity={born}>
              <circle cx={sx} cy={sy} r={r}
                      fill={snapped ? "#FFFFFF" : accent}
                      filter="url(#ca-dot)" />
            </g>
          );
        })}

        {hit > 0 ? (
          <rect x={0} y={0} width={width} height={height}
                fill={rgba("#ffffff", hit * 0.16)} />
        ) : null}
      </svg>

      {pasteAt != null && pasteText?.length ? (() => {
        const sp = spring({
          frame: frame - Math.round((start + pasteAt - 0.22) * fps),
          fps, config: { damping: 15, stiffness: 200, mass: 0.7 },
        });
        const gone = demoteAt == null ? 0 : clamp((t - (demoteAt - 0.3)) / 0.4);
        if (sp <= 0.001 || gone >= 1) return null;
        return (
          <div style={{
            position: "absolute", left: 76, top: 236, width: 928,
            opacity: sp * (1 - gone),
            transform: `translateY(${(1 - sp) * -300 - gone * 40}px)`,
            borderRadius: 24, overflow: "hidden", padding: "34px 40px",
            background: `linear-gradient(180deg, ${rgba("#ffffff", 0.08)} 0%, ${rgba("#ffffff", 0.022)} 100%)`,
            border: `1px solid ${rgba("#ffffff", 0.18)}`,
            boxShadow: `0 30px 70px -32px ${rgba("#000", 0.9)}`,
          }}>
            <div style={{ position: "absolute", left: 0, top: 0, width: 6, height: "100%", background: accent }} />
            {pasteText.slice(0, 4).map((ln, i) => (
              <div key={i} style={{ fontFamily: MONO, fontSize: 30, lineHeight: "46px",
                                    color: rgba(BRAND.paper, 0.82) }}>{ln}</div>
            ))}
          </div>
        );
      })() : null}

      {/* THE HEADLINE SLOT. The problem and the reframe occupy the SAME space,
          so the cut replaces one claim with the other rather than adding to it. */}
      <div style={{ position: "absolute", left: PLOT_L - 4, top: HEAD_Y, right: 64, zIndex: 1,
                    opacity: 1 - demote, transform: `translateY(${demote * -60}px)` }}>
        {preHeadline && preOut > 0 ? (
          <>
            <div style={{ fontFamily: DISPLAY, fontSize: 196, lineHeight: "172px",
                          color: BRAND.paper, letterSpacing: -3 }}>{preHeadline}</div>
            {preSubhead ? (
              <div style={{ marginTop: 26, fontFamily: MONO, fontSize: 26,
                            letterSpacing: 5, color: rgba(BRAND.paper, 0.45) }}>{preSubhead}</div>
            ) : null}
          </>
        ) : null}
        {headline && headIn > 0 ? (
          <div>
            <div style={{ fontFamily: DISPLAY, fontSize: 196, lineHeight: "172px",
                          color: BRAND.paper, letterSpacing: -3 }}>{word(headline)}</div>
            {subhead ? (
              <div style={{ marginTop: 26, fontFamily: MONO, fontSize: 26,
                            letterSpacing: 5, color: accent }}>{subhead}</div>
            ) : null}
          </div>
        ) : null}
      </div>
      {host ? (
        <div style={{
          position: "absolute",
          [hostAnchor === "tl" ? "left" : "right"]: 64,
          top: SAFE.headerFloor + 26,
          width: hostSize, height: Math.round(hostSize * 0.5625),
          borderRadius: 18, overflow: "hidden",
          border: `1px solid ${rgba("#ffffff", 0.18)}`,
          boxShadow: `0 22px 54px -26px ${rgba("#000", 0.9)}`,
        } as React.CSSProperties}>
          <video src={host} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

/* ---- canonical demo ------------------------------------------------------ */
export const careerArcDemo: CareerArcProps = {
  runLabel: "YOUR LAST 2 YEARS",
  points: [
    { label: "what broke", lift: 0.24, at: 4.12 },
    { label: "what you fixed", lift: 0.46, at: 4.58 },
    { label: "who noticed", lift: 0.68, at: 5.06 },
    { label: "what you taught", lift: 0.92, at: 5.54 },
  ],
  snapAt: 5.99,
  pasteAt: 2.25,
  pasteText: ["You are my appraisal coach.", "Ask me ONE question at a time."],
  demoteAt: 9.74,
  preHeadline: "FLAT.",
  preSubhead: "AND YOU CAN'T EXPLAIN WHY",
  headline: "NOT FLAT.",
  subhead: "YOU JUST NEVER PLOTTED IT",
};
