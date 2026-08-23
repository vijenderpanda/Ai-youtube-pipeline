import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { BRAND, SANS, SERIF, DISPLAY, rgba, clamp, Fonts, AuroraBed } from "./kit";
import { clamp01, enter, IN_E } from "./motion";

/* =============================================================================
   SerifCap — the web-tour template's SIGNATURE caption plate: a mixed-register
   line where plain sans words hand off to Playfair Display ITALIC for the
   emphasis phrase ("one command. *full autopilot.*"). The register switch IS
   the emphasis — no marker pads, no underlines; the serif italic carries it.

   Three faces per part (string enum, JSON-safe):
     sans    — 800-weight kit SANS, the plain-speech register
     serif   — Playfair Display Italic. The repo ships ONLY the italic cut
               (kit.tsx loads PlayfairDisplay-Italic.ttf, no upright), so serif
               parts always set fontStyle:"italic" — asking for upright would
               silently fall back to Georgia. Playfair's x-height is small next
               to Helvetica, so serif parts render at 1.08x to sit optically
               level with their sans neighbours.
     display — Anton faked small-caps (uppercase at 0.9x, tracked out) for the
               rare shout word.

   Timing: each line carries its own `at` (+ optional `dur`) on the component
   clock. Entry = word-cluster rise+settle (parts stagger 70ms — a cluster,
   NEVER a typewriter); exit = quick fade-UP with the line's layout slot
   collapsing smoothly so surviving lines reflow without a pop. A line with no
   `dur` holds its final state forever (time-sliced, held, never loops).

   Layout: the block's BOTTOM is anchored at `anchorY` (default 1306, clamped
   to ≤1560 — the caption band owns everything below SAFE.captionCeil) and
   lines GROW UPWARD. Every line's slot is reserved from mount, so an earlier
   line never jumps when a later line lands beneath it. Font size auto-shrinks
   until the widest line fits the 936px safe column AND the stack stays under
   the header floor — no payload can clip.

   AUTHORING RULE (not enforced in code): no burned caption shorter than 1.6s —
   Shorts run 2x playback and a sub-1.6s plate is unreadable there. Enforce at
   the episode spec, not here. Same for accent: ONE accent word per line max
   (N3) — this one IS enforced: only the first accent-flagged part tints.
   ========================================================================== */

export type SerifCapProps = {
  // caption lines (first 4 render). Each part is one line-unbreakable segment.
  lines: Array<{
    parts: Array<{ t: string; face?: "sans" | "serif" | "display"; accent?: boolean }>;
    at: number; // seconds (component clock) when the line enters
    dur?: number; // visible seconds; omit = hold final state forever
  }>;
  anchorY?: number; // block BOTTOM y in the 1920 design box (default 1306, clamped ≤1560)
  align?: "center" | "left"; // default "center"
  size?: number; // base font px — auto-shrunk to fit, never grown (default 72)
  shadow?: boolean; // legibility shadow for use over tape (default true)
  start?: number; // seconds before the component clock begins
  accent?: string; // the ONE accent word per line — magenta default, gold for crown/CTA
  ink?: string;
  width?: number;
  height?: number;
  transparent?: boolean; // skip the aurora backdrop (overlay over WebTour tape)
};

// off-white per the template's locked visual language (NOT kit paper #F2F2F8)
const PAPER = "#F5F2EC";

// per-face average glyph advance (em) for the honest width estimate; the render
// scale each face actually draws at rides along so the fit math matches pixels.
const FACE = {
  sans: { adv: 0.6, scale: 1.0 },
  serif: { adv: 0.52, scale: 1.08 },
  display: { adv: 0.58, scale: 0.9 },
} as const;

const faceStyle = (face: "sans" | "serif" | "display", fs: number): React.CSSProperties =>
  face === "serif"
    ? {
        fontFamily: SERIF,
        fontStyle: "italic", // italic-only cut — see header
        fontWeight: 500,
        fontSize: Math.round(fs * FACE.serif.scale),
      }
    : face === "display"
      ? {
          fontFamily: DISPLAY,
          fontWeight: 400,
          fontSize: Math.round(fs * FACE.display.scale),
          textTransform: "uppercase",
          letterSpacing: 2,
        }
      : { fontFamily: SANS, fontWeight: 800, fontSize: fs, letterSpacing: 0.5 };

export const SerifCap: React.FC<SerifCapProps> = ({
  lines,
  anchorY = 1306,
  align = "center",
  size = 72,
  shadow = true,
  start = 0,
  accent = BRAND.mag,
  ink = BRAND.ink,
  width = 1080,
  height = 1920,
  transparent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tBed = frame / fps; // backdrop breathes even during the start delay
  const tt = tBed - start; // component clock, seconds

  const rows = (lines ?? []).slice(0, 4).map((l) => ({
    ...l,
    parts: (l.parts ?? []).slice(0, 8),
  }));

  const sideSafe = 72;
  const colW = width - sideSafe * 2;
  const anchorYc = Math.min(anchorY, 1560); // caption band owns y>1560

  // ---- auto-fit: widest line must fit the column, stack must clear header --
  const lineEm = (parts: (typeof rows)[number]["parts"]): number =>
    parts.reduce((sum, p) => {
      const f = FACE[p.face ?? "sans"];
      return sum + p.t.length * f.adv * f.scale;
    }, Math.max(0, parts.length - 1) * 0.3); // + columnGap between parts
  const widestEm = rows.reduce((m, l) => Math.max(m, lineEm(l.parts)), 1);
  const fitW = (colW * 0.96) / widestEm;
  const fitV = (anchorYc - 152) / (1.34 * Math.max(1, rows.length)); // stay below header floor
  const fs = clamp(Math.min(size, fitW, fitV), 34, 170);
  const lineH = Math.round(fs * 1.34); // reserved slot per line (fixed → no reflow jumps)

  const shadowBase = shadow
    ? `0 4px 14px ${rgba("#000", 0.5)}, 0 12px 40px ${rgba("#000", 0.42)}`
    : undefined;

  return (
    <AbsoluteFill style={{ background: transparent ? undefined : ink, fontFamily: SANS }}>
      <Fonts />
      {transparent ? null : <AuroraBed t={tBed} accent={accent} ink={ink} />}

      {/* the caption block: bottom anchored, lines grow UP */}
      <div
        style={{
          position: "absolute",
          left: sideSafe,
          width: colW,
          bottom: height - anchorYc,
          display: "flex",
          flexDirection: "column",
          justifyContent: "flex-end",
        }}
      >
        {rows.map((line, li) => {
          const exitAt = line.dur == null ? Infinity : line.at + line.dur;
          const e = IN_E(clamp01((tt - exitAt) / 0.26)); // quick fade-up exit
          const accentIdx = line.parts.findIndex((p) => !!p.accent); // ONE per line (N3)

          return (
            <div
              key={li}
              style={{
                height: Math.round(lineH * (1 - e)), // slot collapses with the exit
                overflow: "visible",
                opacity: 1 - e,
                transform: `translateY(${(-30 * e).toFixed(1)}px)`,
                display: "flex",
                justifyContent: align === "left" ? "flex-start" : "center",
                alignItems: "baseline",
                columnGap: Math.round(fs * 0.3),
                whiteSpace: "nowrap",
                lineHeight: 1.15,
              }}
            >
              {line.parts.map((part, i) => {
                const appear = line.at + i * 0.07; // cluster stagger, not typewriter
                const prog = enter(tt, appear, 0.44, 0.08); // rise overshoots then settles
                const op = clamp01((tt - appear) / 0.16);
                const hot = i === accentIdx;
                return (
                  <span
                    key={i}
                    style={{
                      ...faceStyle(part.face ?? "sans", Math.round(fs)),
                      display: "inline-block",
                      color: hot ? accent : PAPER,
                      opacity: op,
                      transform: `translateY(${((1 - prog) * 40).toFixed(1)}px)`,
                      textShadow: hot && shadow ? `0 6px 30px ${rgba(accent, 0.5)}, ${shadowBase}` : shadowBase,
                    }}
                  >
                    {part.t}
                  </span>
                );
              })}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const serifCapDemo: SerifCapProps = {
  lines: [
    { parts: [{ t: "one command.", face: "sans" }], at: 0.25 },
    {
      parts: [
        { t: "full", face: "serif" },
        { t: "autopilot.", face: "serif", accent: true },
      ],
      at: 0.9,
    },
  ],
  size: 84,
};
