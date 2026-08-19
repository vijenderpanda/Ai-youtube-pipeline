import React from "react";
import {
  AbsoluteFill,
  spring,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BRAND, SANS, DISPLAY, rgba, clamp, coverBg, Fonts } from "./kit";

/* =============================================================================
   BentoGrid — a modern "bento" tile layout that pops in with a staggered
   spring, one accent tile featured.
   Cookbook role: the "modern UI/UX flex + readability" component — a bento grid
   is the current SaaS/landing-page idiom, and it lets one beat show 3-6 facts at
   once, each landing on its own micro-beat. Tiles span the grid via `span`
   (CSS grid auto-flow dense does the packing), so any tile mix stays gap-free.
   ========================================================================== */

export type BentoTile = {
  title: string; // small label at top
  value?: string; // big Anton value/number (optional)
  note?: string; // small footnote under the value
  icon?: string; // glyph top-right
  span?: "1x1" | "2x1" | "1x2" | "2x2"; // grid footprint (cols x rows)
  accent?: boolean; // magenta-filled feature tile
};

export type BentoGridProps = {
  tiles: BentoTile[];
  heading?: string; // section heading above the grid
  cols?: number; // grid columns (default 2)
  rowH?: number; // base row height px (default 340)
  accent?: string; // brand magenta
  ink?: string;
  start?: number; // seconds before the first tile pops
  stagger?: number; // seconds between tiles (default 0.12)
  width?: number;
  height?: number;
  transparent?: boolean;
};

const SPAN: Record<NonNullable<BentoTile["span"]>, { c: number; r: number }> = {
  "1x1": { c: 1, r: 1 },
  "2x1": { c: 2, r: 1 },
  "1x2": { c: 1, r: 2 },
  "2x2": { c: 2, r: 2 },
};

export const BentoGrid: React.FC<BentoGridProps> = ({
  tiles,
  heading,
  cols = 2,
  rowH = 340,
  accent = BRAND.mag,
  ink = BRAND.ink,
  start = 0.25,
  stagger = 0.12,
  width = 1080,
  height = 1920,
  transparent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const M = 80; // side margin
  const gap = 28;

  return (
    <AbsoluteFill
      style={{
        background: transparent ? undefined : coverBg(accent, ink),
        fontFamily: SANS
      }}
    >
      <Fonts />
      {heading ? (
        <div style={{ position: "absolute", top: Math.round(height * 0.09), left: M, right: M, fontFamily: DISPLAY, fontSize: 96, lineHeight: 0.98, color: BRAND.paper, textTransform: "uppercase", letterSpacing: 1 }}>
          {heading}
        </div>
      ) : null}
      <div
        style={{
          position: "absolute",
          left: M,
          right: M,
          top: heading ? Math.round(height * 0.2) : Math.round(height * 0.14),
          display: "grid",
          gridTemplateColumns: `repeat(${cols}, 1fr)`,
          gridAutoRows: `${rowH}px`,
          gridAutoFlow: "dense",
          gap,
        }}
      >
        {tiles.map((tile, i) => {
          const sp = SPAN[tile.span ?? "1x1"];
          const s = spring({ frame: frame - (start + i * stagger) * fps, fps, config: { damping: 15, mass: 0.7 } });
          const isA = tile.accent;
          return (
            <div
              key={i}
              style={{
                gridColumn: `span ${Math.min(sp.c, cols)}`,
                gridRow: `span ${sp.r}`,
                opacity: clamp(s * 1.5),
                transform: `translateY(${interpolate(s, [0, 1], [40, 0])}px) scale(${interpolate(s, [0, 1], [0.9, 1])})`,
                borderRadius: 36,
                padding: 44,
                boxSizing: "border-box",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                background: isA
                  ? `linear-gradient(150deg, ${accent}, ${rgba(accent, 0.72)})`
                  : rgba("#15151d", 0.9),
                border: `1.5px solid ${isA ? rgba("#ffffff", 0.18) : rgba("#ffffff", 0.08)}`,
                boxShadow: isA
                  ? `0 24px 60px ${rgba(accent, 0.4)}`
                  : `0 20px 50px ${rgba("#000000", 0.4)}`,
                color: isA ? ink : BRAND.paper,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div style={{ fontSize: 34, fontWeight: 700, letterSpacing: 0.5, color: isA ? rgba(ink, 0.75) : BRAND.mute, textTransform: "uppercase" }}>
                  {tile.title}
                </div>
                {tile.icon ? (
                  <div style={{ fontSize: 46, opacity: 0.9 }}>{tile.icon}</div>
                ) : null}
              </div>
              {tile.value ? (
                <div style={{ fontFamily: DISPLAY, fontSize: sp.c >= 2 || sp.r >= 2 ? 150 : 108, lineHeight: 0.9, color: isA ? ink : BRAND.paper }}>
                  {tile.value}
                </div>
              ) : null}
              {tile.note ? (
                <div style={{ fontSize: 30, color: isA ? rgba(ink, 0.72) : BRAND.mute, lineHeight: 1.3 }}>
                  {tile.note}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const bentoGridDemo: BentoGridProps = {
  heading: "One day of posting",
  tiles: [
    { title: "Views", value: "41K", note: "+180% vs last week", span: "2x1", accent: true, icon: "↗" },
    { title: "Watch time", value: "92%", note: "avg. retention", icon: "▶" },
    { title: "New subs", value: "1.2K", icon: "✦" },
    { title: "Comments", value: "340", note: "replies drive reach", span: "2x1", icon: "💬" },
  ],
};
