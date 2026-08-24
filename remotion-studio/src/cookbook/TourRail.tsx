import React from "react";
import { BRAND, MONO, rgba } from "./kit";

/* =============================================================================
   TourRail (VJ 2026-08-23) — fills the void between the global header and the
   WebTour card with a BEAT TIMELINE: a hairline, one dot per beat, and a
   glowing comet that glides along it (never static — U1) and snaps into each
   dot as the beat lands. The current beat's label rides under the comet.

   Why it earns its pixels: it is a retention device, not decoration — the
   viewer can SEE a payoff dot ahead ("the line" / "payoff"), which is the
   open-loop the web-tour grammar promises. Rationed to one rail, one comet,
   muted mono type; magenta is the only accent.
   ========================================================================== */

export type TourRailPayload = {
  labels: string[]; // one per beat, e.g. ["47K ★", "1.3B free", "what changes", "the catch", "one line", "payoff"]
  starts: number[]; // absolute seconds each beat starts (same length as labels)
  end: number; // absolute second the body ends (comet reaches the last dot)
  from?: number; // first second the rail is visible (default starts[0])
  y?: number; // rail y (default 300 — the void above the card)
};

const smooth = (x: number) => {
  const c = Math.max(0, Math.min(1, x));
  return c * c * (3 - 2 * c);
};

export const TourRail: React.FC<{ rail: TourRailPayload; t: number; width?: number }> = ({
  rail,
  t,
  width = 1080,
}) => {
  const { labels, starts, end, y = 300 } = rail;
  const from = rail.from ?? starts[0];
  if (t < from - 0.2 || labels.length === 0) return null;
  const n = labels.length;
  const left = 120;
  const right = width - 120;
  const span = right - left;
  const xs = labels.map((_, i) => left + (span * i) / Math.max(1, n - 1));

  // comet position: within beat i, ease from dot i toward dot i+1 over the
  // beat's duration — so it is ALWAYS moving, and lands exactly on the dot at
  // the beat boundary
  let active = 0;
  for (let i = 0; i < n; i++) if (t >= starts[i]) active = i;
  const b0 = starts[active];
  const b1 = active + 1 < n ? starts[active + 1] : end;
  const frac = b1 > b0 ? smooth((t - b0) / (b1 - b0)) : 1;
  const x1 = active + 1 < n ? xs[active + 1] : xs[active];
  const cx = xs[active] + (x1 - xs[active]) * frac;

  const appear = smooth((t - (from - 0.2)) / 0.5);
  const pulse = 1 + Math.sin(t * 6.5) * 0.08;
  const labelIn = smooth((t - b0) / 0.35);
  const mag = BRAND.mag;

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        top: y,
        width,
        height: 120,
        opacity: appear,
        pointerEvents: "none",
      }}
    >
      <svg width={width} height={120} style={{ position: "absolute", inset: 0, overflow: "visible" }}>
        <defs>
          <filter id="tourrail-glow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="6" />
          </filter>
        </defs>
        {/* hairline: lit up to the comet, faint beyond */}
        <line x1={left} y1={40} x2={right} y2={40} stroke={rgba("#ffffff", 0.16)} strokeWidth={2.5} />
        <line x1={left} y1={40} x2={cx} y2={40} stroke={mag} strokeWidth={3} opacity={0.9} />
        {/* beat dots */}
        {xs.map((x, i) => {
          const lit = i <= active;
          return (
            <g key={i}>
              <circle cx={x} cy={40} r={lit ? 9 : 6} fill={lit ? mag : rgba("#ffffff", 0.28)} />
              {i === n - 1 && !lit ? (
                // the payoff dot breathes faintly so the eye knows it's coming
                <circle cx={x} cy={40} r={11 + Math.sin(t * 4) * 2} fill="none" stroke={rgba("#ffffff", 0.35)} strokeWidth={1.5} />
              ) : null}
            </g>
          );
        })}
        {/* comet: trail + bloom + white-hot core */}
        <line x1={Math.max(left, cx - 70)} y1={40} x2={cx} y2={40} stroke={mag} strokeWidth={6} strokeLinecap="round" opacity={0.35} />
        <circle cx={cx} cy={40} r={20 * pulse} fill={mag} opacity={0.55} filter="url(#tourrail-glow)" />
        <circle cx={cx} cy={40} r={11 * pulse} fill={mag} />
        <circle cx={cx} cy={40} r={5} fill="#ffffff" />
      </svg>
      {/* current label under the comet */}
      <div
        style={{
          position: "absolute",
          left: Math.min(Math.max(cx - 160, 24), width - 344),
          top: 62,
          width: 320,
          textAlign: "center",
          fontFamily: MONO,
          fontSize: 30,
          letterSpacing: 5,
          textTransform: "uppercase",
          color: rgba("#ffffff", 0.82),
          opacity: labelIn,
          transform: `translateY(${(1 - labelIn) * 8}px)`,
          whiteSpace: "nowrap",
        }}
      >
        {labels[active]}
      </div>
    </div>
  );
};
