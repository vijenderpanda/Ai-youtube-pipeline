import React from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BRAND, SANS, DISPLAY, rgba, clamp, coverBg, Fonts } from "./kit";

/* =============================================================================
   LineReveal — an animated line/area chart that draws left→right while a big
   headline number counts to the leading-edge value.
   Cookbook role: the "dataviz reveal" (complements StatBars' bar chart — this is
   the TREND form: growth, decay, a curve over time). A dot rides the drawing
   edge, the area fills under it, and the value pill lands on the final point.
   JSON-safe: values are numbers; formatting via prefix/suffix/decimals (no fn
   props — build_ep_v2 feeds --props as JSON).
   ========================================================================== */

export type LineRevealProps = {
  points: number[]; // y-values, evenly spaced along x (>= 2)
  title?: string; // small header label over the number
  labels?: string[]; // optional x labels; first + last are drawn under the axis
  prefix?: string; // number prefix, e.g. "$"
  suffix?: string; // number suffix, e.g. "%", "K"
  decimals?: number; // counter decimal places (default 0)
  footer?: string; // accent punchline pinned low
  accent?: string; // line + dot (brand magenta)
  accent2?: string; // headline number + pill text (brand yellow)
  ink?: string;
  draw?: number; // seconds the line takes to draw (default 1.7)
  start?: number; // seconds before the draw begins
  width?: number;
  height?: number;
  transparent?: boolean;
};

/** y-value along the polyline at fractional x-progress p (0..1). */
const valueAt = (pts: number[], p: number): number => {
  if (pts.length < 2) return pts[0] ?? 0;
  const span = (pts.length - 1) * clamp(p);
  const i = Math.min(Math.floor(span), pts.length - 2);
  return pts[i] + (pts[i + 1] - pts[i]) * (span - i);
};

export const LineReveal: React.FC<LineRevealProps> = ({
  points,
  title,
  labels,
  prefix = "",
  suffix = "",
  decimals = 0,
  footer,
  accent = BRAND.mag,
  accent2 = BRAND.yellow,
  ink = BRAND.ink,
  draw = 1.7,
  start = 0.3,
  width = 1080,
  height = 1920,
  transparent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const p = clamp((frame - start * fps) / (draw * fps));
  const eased = interpolate(p, [0, 1], [0, 1], { easing: (x) => 1 - Math.pow(1 - x, 3) });

  // plot box — top clears the title+number stack, bottom clears the caption band
  const L = 96;
  const R = width - 96;
  const top = Math.round(height * 0.36);
  const bot = Math.round(height * 0.72);
  const plotW = R - L;
  const plotH = bot - top;

  const n = points.length;
  const maxV = Math.max(...points);
  const minV = Math.min(...points);
  const range = Math.max(maxV - minV, 1e-9);
  // 8% headroom top & bottom so peaks/troughs never touch the plot edges
  const yOf = (v: number) => bot - ((v - minV) / range) * plotH * 0.84 - plotH * 0.08;
  const xOf = (i: number) => L + (plotW * i) / (n - 1);

  const linePts = points.map((v, i) => `${xOf(i)},${yOf(v)}`).join(" ");
  const areaPts = `${L},${bot} ${linePts} ${R},${bot}`;

  // leading edge
  const edgeX = L + plotW * eased;
  const edgeV = valueAt(points, eased);
  const edgeY = yOf(edgeV);
  const counter = valueAt(points, eased);

  const clipW = plotW * eased;
  const gid = "lr_area";

  return (
    <AbsoluteFill
      style={{
        background: transparent ? undefined : coverBg(accent, ink),
        fontFamily: SANS,
      }}
    >
      <Fonts />

      {/* headline number + title */}
      <div style={{ position: "absolute", top: Math.round(height * 0.11), width: "100%", textAlign: "center" }}>
        {title ? (
          <div style={{ fontSize: 40, letterSpacing: 4, textTransform: "uppercase", color: BRAND.mute, marginBottom: 10 }}>
            {title}
          </div>
        ) : null}
        <div style={{ fontFamily: DISPLAY, fontSize: 210, lineHeight: 0.9, color: accent2, textShadow: `0 10px 40px ${rgba(accent2, 0.28)}` }}>
          {prefix}
          {counter.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}
          {suffix}
        </div>
      </div>

      <svg width={width} height={height} style={{ position: "absolute", inset: 0 }}>
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={rgba(accent, 0.42)} />
            <stop offset="100%" stopColor={rgba(accent, 0)} />
          </linearGradient>
          <clipPath id="lr_clip">
            <rect x={L} y={top - 40} width={clipW} height={plotH + 120} />
          </clipPath>
        </defs>

        {/* gridlines */}
        {[0, 0.25, 0.5, 0.75, 1].map((g) => (
          <line key={g} x1={L} x2={R} y1={bot - plotH * g} y2={bot - plotH * g} stroke={rgba("#ffffff", g === 0 ? 0.16 : 0.05)} strokeWidth={g === 0 ? 3 : 2} />
        ))}

        {/* area + line, revealed by the growing clip */}
        <g clipPath="url(#lr_clip)">
          <polygon points={areaPts} fill={`url(#${gid})`} />
          <polyline points={linePts} fill="none" stroke={accent} strokeWidth={9} strokeLinejoin="round" strokeLinecap="round" style={{ filter: `drop-shadow(0 6px 20px ${rgba(accent, 0.5)})` }} />
        </g>

        {/* leading dot + pulse */}
        {p > 0 && p < 1 ? (
          <>
            <circle cx={edgeX} cy={edgeY} r={26} fill={rgba(accent, 0.22)} />
            <circle cx={edgeX} cy={edgeY} r={13} fill="#fff" stroke={accent} strokeWidth={6} />
          </>
        ) : null}

        {/* final point marker */}
        {p >= 1 ? <circle cx={xOf(n - 1)} cy={yOf(points[n - 1])} r={15} fill={accent2} stroke={ink} strokeWidth={5} /> : null}
      </svg>

      {/* x labels (first + last) */}
      {labels && labels.length >= 2 ? (
        <div style={{ position: "absolute", top: bot + 22, left: L, width: plotW, display: "flex", justifyContent: "space-between", fontSize: 30, letterSpacing: 2, textTransform: "uppercase", color: BRAND.mute }}>
          <span>{labels[0]}</span>
          <span>{labels[labels.length - 1]}</span>
        </div>
      ) : null}

      {/* footer punchline */}
      {footer ? (
        <div style={{ position: "absolute", top: Math.round(height * 0.86), width: "100%", textAlign: "center", fontSize: 52, letterSpacing: 1, textTransform: "uppercase", color: accent, opacity: clamp((p - 0.75) * 4) }}>
          {footer}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

export const lineRevealDemo: LineRevealProps = {
  title: "Weekly views",
  points: [2, 3, 2.6, 5, 8, 7.4, 12, 18, 24, 41],
  labels: ["WK 1", "", "", "", "", "", "", "", "", "WK 10"],
  suffix: "K",
  decimals: 0,
  footer: "Post daily. Compound.",
};
