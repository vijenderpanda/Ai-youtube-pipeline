import React from "react";
import { rgba } from "./kit";
import { clamp01, OUT_E, settle } from "./motion";
import { useFilmT } from "./filmclock";

/* =============================================================================
   EngagePing v2 — VJ's engagement-glow, SHAPE-MATCHED (his note: "match the
   icon shapes please, not generic glows, and color is dull").

   Each ping draws the ACTUAL icon silhouette at the exact spot YouTube
   paints its button — heart (like), speech bubble (comment), share arrow,
   subscribe pill — as a white-hot core stroke inside a vivid red bloom
   (SVG gaussian glow), with two expanding shape-echoes. The real YT icon
   sits on top of our pixels, so the shape reads as the button itself
   lighting up.

   Fired ON script beats, one at a time, ~2s, tooltip a few words.
   ========================================================================== */

const DISP = "'Archivo Black', 'Arial Black', sans-serif";
const HOT = "#FF2D2D";          // vivid red bloom — visible on any ground
const CORE = "#FFFFFF";         // white-hot core stroke

const POS: Record<string, { x: number; y: number; side: "left" | "top" }> = {
  like: { x: 1002, y: 1218, side: "left" },
  comment: { x: 1002, y: 1372, side: "left" },
  share: { x: 1002, y: 1516, side: "left" },
  subscribe: { x: 566, y: 1618, side: "top" },
};

/* icon silhouettes, 100-unit viewBox space */
const SHAPES: Record<string, { d: string; vb: string; w: number; h: number }> = {
  like: {
    d: "M50 88 C 20 63 6 43 12 26 C 18 12 36 10 50 26 C 64 10 82 12 88 26 C 94 43 80 63 50 88 Z",
    vb: "0 0 100 100", w: 76, h: 76,
  },
  comment: {
    d: "M14 8 h72 a10 10 0 0 1 10 10 v38 a10 10 0 0 1 -10 10 h-38 l-18 16 v-16 h-16 a10 10 0 0 1 -10 -10 v-38 a10 10 0 0 1 10 -10 z",
    vb: "0 0 100 88", w: 76, h: 70,
  },
  share: {
    d: "M60 10 L92 38 L60 66 V51 C 32 51 18 62 8 80 C 11 52 27 30 60 27 Z",
    vb: "0 0 100 88", w: 78, h: 70,
  },
  subscribe: {
    d: "M10 8 h150 a22 22 0 0 1 22 22 v0 a22 22 0 0 1 -22 22 h-150 a22 22 0 0 1 -22 -22 v0 a22 22 0 0 1 22 -22 z",
    vb: "-14 0 200 62", w: 205, h: 66,
  },
};

export type Ping = {
  at: number; kind: "like" | "comment" | "share" | "subscribe";
  tip: string; dur?: number;
};

export const EngagePing: React.FC<{ t?: number; ping: Ping }> = ({ t: tProp, ping }) => {
  const filmT = useFilmT();
  const t = tProp ?? filmT;
  const { at, dur = 2.2 } = ping;
  if (t < at || t > at + dur) return null;
  const local = t - at;
  const on = OUT_E(clamp01(local / 0.35));
  const off = clamp01((local - (dur - 0.4)) / 0.4);
  const o = on * (1 - off);
  const p = POS[ping.kind];
  const sh = SHAPES[ping.kind];
  /* grow animation: the outline pops from 55% up to the icon's real size
     with a spring overshoot, then breathes gently */
  const grow = 0.55 + OUT_E(clamp01(local / 0.28)) * 0.45 + settle(t, at + 0.28, 0.35) * 0.08;
  const pulse = grow * (1 + Math.sin(local * 7) * 0.04);
  const fid = `ep-glow-${ping.kind}`;

  /* the shape, drawn 3 ways: wide red bloom, red mid, white-hot core —
     plus two expanding echoes of the same silhouette */
  const echo = (phase: number) => {
    const rp = (local * 0.8 + phase) % 1;
    const sc = 1 + rp * 1.15;
    return (
      <g key={phase} transform={`translate(${sh.w / 2} ${sh.h / 2}) scale(${sc}) translate(${-sh.w / 2} ${-sh.h / 2})`}
        opacity={(1 - rp) * 0.55}>
        <path d={sh.d} fill="none" stroke={HOT} strokeWidth={3.5} vectorEffect="non-scaling-stroke" />
      </g>
    );
  };

  const tipW = 34 + ping.tip.length * 16;
  const tipX = p.side === "left" ? p.x - tipW - sh.w * 0.6 - 30 : p.x - tipW / 2;
  const tipY = p.side === "top" ? p.y - sh.h / 2 - 80 : p.y - 24;

  return (
    <div style={{ position: "absolute", inset: 0, zIndex: 44, opacity: o, pointerEvents: "none" }}>
      <svg width={sh.w} height={sh.h} viewBox={sh.vb}
        style={{ position: "absolute", left: p.x - sh.w / 2, top: p.y - sh.h / 2,
          transform: `scale(${pulse})`, overflow: "visible" }}>
        <defs>
          <filter id={fid} x="-80%" y="-80%" width="260%" height="260%">
            <feGaussianBlur stdDeviation="5" />
          </filter>
        </defs>
        {/* red bloom */}
        <path d={sh.d} fill="none" stroke={HOT} strokeWidth={8} filter={`url(#${fid})`} opacity={0.95}
          strokeLinejoin="round" />
        {/* red mid */}
        <path d={sh.d} fill="none" stroke={HOT} strokeWidth={4.5} opacity={0.95} strokeLinejoin="round" />
        {/* white-hot core */}
        <path d={sh.d} fill="none" stroke={CORE} strokeWidth={2} opacity={0.98} strokeLinejoin="round" />
        {echo(0)}
        {echo(0.5)}
      </svg>
      {/* tooltip */}
      <div style={{
        position: "absolute", left: tipX, top: tipY,
        transform: `scale(${0.9 + on * 0.1 + settle(t, at, 0.4) * 0.06})`,
        transformOrigin: p.side === "left" ? "right center" : "center bottom",
        background: rgba("#16100A", 0.96), borderRadius: 12,
        padding: "8px 16px", boxShadow: `0 5px 16px ${rgba("#000", 0.5)}`,
        border: `2px solid ${HOT}`,
      }}>
        <span style={{ fontFamily: DISP, fontSize: 28, color: "#FFFFFF", whiteSpace: "nowrap" as const }}>
          {ping.tip}
        </span>
        <div style={{
          position: "absolute",
          ...(p.side === "left"
            ? { right: -8, top: "50%", transform: "translateY(-50%) rotate(45deg)",
                borderRight: `2px solid ${HOT}`, borderTop: `2px solid ${HOT}` }
            : { left: "50%", bottom: -8, transform: "translateX(-50%) rotate(45deg)",
                borderRight: `2px solid ${HOT}`, borderBottom: `2px solid ${HOT}` }),
          width: 14, height: 14, background: rgba("#16100A", 0.96),
        }} />
      </div>
    </div>
  );
};
