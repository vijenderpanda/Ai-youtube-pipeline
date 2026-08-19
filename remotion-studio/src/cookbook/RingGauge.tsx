import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BRAND, SANS, DISPLAY, rgba, clamp, coverBg, Fonts } from "./kit";

/* =============================================================================
   RingGauge — 1–3 concentric activity-style progress rings that sweep from
   12 o'clock clockwise to their percentage, staggered, with a big counting
   headline in the hollow center and a compact synced legend below.

   Cookbook role: the RADIAL dataviz form. The cookbook splits dataviz by shape —
   StatBars is the BAR form, LineReveal is the TREND form, RingGauge is the RING
   form: a small set of "how full / how far" percentages shown at a glance. Rings
   read as completeness the instant they land, so a viewer parses "82% / 64% /
   91%" in under a second — exactly the job of a 15s-hold b-roll beat.

   Why this layout:
   - Concentric rings (not side-by-side dials) stack the whole story into one
     centered gestalt: the outer ring dominates, inners nest inside it, and the
     hollow middle becomes free real estate for the ONE number that matters
     (a custom headline like "3.5h SAVED / WK", or the primary ring's live %).
   - Each ring is a thick round-capped stroke over a faint full-circle track, so
     even a 0-progress ring reads as a ring; an accent drop-shadow glow gives the
     fill the lit "activity ring" look without any raster asset.
   - Staggered sweeps (outer first) turn a static stat block into a short performed
     reveal; the legend %s tick up in lockstep so eye can follow ring OR list.
   - Everything is centered and nested inside the outer ring's own footprint, so
     the safe margins and the karaoke caption band (bottom ~21%) are respected by
     construction — the legend sits in the gap between rings and captions.

   Time-sliced, lands held: every sweep clamps to its target and the counters
   settle, so a still near the end shows all rings full and the final numbers.
   JSON-safe: rings are {label,pct,color?}; center text is a plain string +
   label (no fn props — build_ep_v2 feeds --props as JSON).
   ========================================================================== */

export type RingGaugeProps = {
  /** 1–3 rings, drawn outer→inner in array order (extra entries are ignored).
   *  pct is 0–100; color overrides the default per-ring palette slot. */
  rings: { label: string; pct: number; color?: string }[];
  /** big center headline. If omitted, the primary (first) ring's counting %
   *  is shown instead (e.g. "82%"). Keep it short — it lives inside the hollow. */
  centerValue?: string;
  /** small uppercase caption under the center headline (e.g. "SAVED / WK"). */
  centerLabel?: string;
  /** small uppercase label pinned above the rings. */
  title?: string;
  accent?: string; // ring-1 default + brand backdrop tint (brand magenta)
  ink?: string;
  start?: number; // seconds before the first sweep begins
  stagger?: number; // seconds each inner ring lags the one outside it
  sweep?: number; // seconds a single ring takes to fill
  width?: number;
  height?: number;
  transparent?: boolean;
};

/** default per-ring color slots — on-brand, high-contrast against each other. */
const RING_PALETTE = [BRAND.mag, BRAND.cyan, BRAND.yellow];

/** ease-out cubic: fast lift, soft land — matches LineReveal's draw feel. */
const easeOut = (x: number): number => 1 - Math.pow(1 - clamp(x), 3);

/** fit the center headline to the hollow: shorter strings ride bigger. */
const centerSize = (s: string): number => {
  const n = s.length;
  if (n <= 3) return 150;
  if (n === 4) return 130;
  if (n === 5) return 112;
  if (n === 6) return 96;
  return 82;
};

export const RingGauge: React.FC<RingGaugeProps> = ({
  rings,
  centerValue,
  centerLabel,
  title,
  accent = BRAND.mag,
  ink = BRAND.ink,
  start = 0.35,
  stagger = 0.22,
  sweep = 1.5,
  width = 1080,
  height = 1920,
  transparent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  // cap at 3 and default-color each slot so a bare {label,pct} still looks brand
  const items = (rings ?? []).slice(0, 3).map((r, i) => ({
    label: r.label,
    pct: clamp(r.pct, 0, 100),
    color: r.color ?? (i === 0 ? accent : RING_PALETTE[i] ?? accent),
  }));

  // ring geometry — nested inside the outer ring's footprint, centered on cy.
  const cx = width / 2;
  const cy = Math.round(height * 0.4);
  const maxR = 330; // outer ring centerline radius
  const step = 84; // radius drop per inner ring
  const stroke = 56; // ring thickness
  const innerR = maxR - (items.length - 1) * step - stroke / 2; // hollow radius

  // per-ring eased progress (outer sweeps first, inners lag by `stagger`)
  const sweepDur = Math.max(sweep, 0.001); // guard: sweep=0 would divide-by-zero → NaN
  const prog = items.map((_, i) =>
    easeOut((t - (start + i * stagger)) / sweepDur)
  );
  const primaryProg = prog[0] ?? 0;

  // center headline: custom string, or the primary ring's live count-up %
  const bigText = centerValue ?? `${Math.round((items[0]?.pct ?? 0) * primaryProg)}%`;
  const bigSize = centerSize(bigText);

  // center entrance: a gentle spring pop so the number "lands" on the ring
  const enter = spring({
    frame: frame - start * fps,
    fps,
    config: { damping: 15, stiffness: 130, mass: 0.8 },
  });
  const centerScale = 0.72 + 0.28 * enter;

  return (
    <AbsoluteFill
      style={{
        background: transparent ? undefined : coverBg(accent, ink),
        fontFamily: SANS,
      }}
    >
      <Fonts />

      {/* title — pinned above the rings, well clear of them */}
      {title ? (
        <div
          style={{
            position: "absolute",
            top: Math.round(height * 0.115),
            left: 64,
            width: width - 128,
            textAlign: "center",
            fontSize: 40,
            letterSpacing: 5,
            textTransform: "uppercase",
            color: BRAND.mute,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {title}
        </div>
      ) : null}

      <svg
        width={width}
        height={height}
        style={{ position: "absolute", inset: 0 }}
      >
        {/* soft glow pooled in the hollow, brightening as the primary ring fills */}
        <defs>
          <radialGradient id="rg_core" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={rgba(accent, 0.22 * primaryProg)} />
            <stop offset="70%" stopColor={rgba(accent, 0)} />
          </radialGradient>
        </defs>
        <circle cx={cx} cy={cy} r={innerR + stroke} fill="url(#rg_core)" />

        {items.map((r, i) => {
          const radius = maxR - i * step;
          const C = 2 * Math.PI * radius;
          const p = clamp(prog[i]);
          const arc = C * (r.pct / 100) * p;
          const glow = interpolate(p, [0, 1], [10, 26]); // tightens as it lands
          return (
            <g key={i} transform={`rotate(-90 ${cx} ${cy})`}>
              {/* faint full track behind the fill */}
              <circle
                cx={cx}
                cy={cy}
                r={radius}
                fill="none"
                stroke={rgba("#ffffff", 0.07)}
                strokeWidth={stroke}
              />
              {/* the sweeping fill — thick, round-capped, glowing */}
              <circle
                cx={cx}
                cy={cy}
                r={radius}
                fill="none"
                stroke={r.color}
                strokeWidth={stroke}
                strokeLinecap="round"
                strokeDasharray={`${arc} ${C}`}
                style={{
                  // hide before the sweep begins so the round cap can't leave a dot at 12 o'clock
                  opacity: arc > 0.5 ? 1 : 0,
                  filter: `drop-shadow(0 0 ${glow}px ${rgba(r.color, 0.55)})`,
                }}
              />
            </g>
          );
        })}
      </svg>

      {/* center headline + label, springing in over the hollow */}
      <div
        style={{
          position: "absolute",
          left: 0,
          width: "100%",
          top: cy,
          transform: `translateY(-50%) scale(${centerScale})`,
          textAlign: "center",
          opacity: clamp(enter * 1.5),
        }}
      >
        <div
          style={{
            fontFamily: DISPLAY,
            fontSize: bigSize,
            lineHeight: 0.9,
            color: BRAND.paper,
            whiteSpace: "nowrap",
            textShadow: `0 8px 34px ${rgba(accent, 0.35)}`,
          }}
        >
          {bigText}
        </div>
        {centerLabel ? (
          <div
            style={{
              marginTop: 12,
              fontSize: 30,
              letterSpacing: 4,
              textTransform: "uppercase",
              color: BRAND.mute,
            }}
          >
            {centerLabel}
          </div>
        ) : null}
      </div>

      {/* legend — one row per ring, dot + label + counting %, synced to the sweep.
          Sits in the gap between the rings and the caption band. */}
      <div
        style={{
          position: "absolute",
          top: cy + maxR + stroke / 2 + 46,
          left: (width - 660) / 2,
          width: 660,
          display: "flex",
          flexDirection: "column",
          gap: 22,
        }}
      >
        {items.map((r, i) => {
          const shown = Math.round(r.pct * clamp(prog[i]));
          return (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 22,
                opacity: clamp(prog[i] * 3), // fades in with its ring
              }}
            >
              <span
                style={{
                  width: 22,
                  height: 22,
                  borderRadius: "50%",
                  background: r.color,
                  boxShadow: `0 0 16px ${rgba(r.color, 0.6)}`,
                  flex: "0 0 auto",
                }}
              />
              <span
                style={{
                  flex: 1,
                  fontSize: 42,
                  color: BRAND.paper,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {r.label}
              </span>
              <span
                style={{
                  fontFamily: DISPLAY,
                  fontSize: 52,
                  lineHeight: 1,
                  color: r.color,
                  flex: "0 0 auto",
                }}
              >
                {shown}%
              </span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const ringGaugeDemo: RingGaugeProps = {
  title: "Hours AI gave back",
  rings: [
    { label: "Research", pct: 82 },
    { label: "Drafting", pct: 64 },
    { label: "Editing", pct: 91 },
  ],
  centerValue: "3.5h",
  centerLabel: "Saved / wk",
};
