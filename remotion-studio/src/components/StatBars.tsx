import React from "react";
import { AbsoluteFill, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { fitFont } from "./fitText";

/* =============================================================================
   StatBars — the LOCKED premium stat/price chart for every in-episode data beat.
   (docs/PRODUCTION-PLAYBOOK.md §4 — born from AI Unpacked Ep23, 2026-08-05,
   where an improvised 1080x1080 PIL bar card got cover-cropped in the 9:16
   frame: labels amputated left/right, fat bars.)

   NEVER improvise chart layout per-episode. Feed data through props; the layout
   spec below is locked:
   - 9:16-safe side margins >= 64px (SAFE_X = 72)
   - max 6 bars (extras dropped)
   - bar width <= 42% of slot pitch, absolute cap 116px — thin, rounded caps
   - staggered spring grow-in
   - value labels with above/inside-top collision handling — they can never clip
   - channel-accent gradient fill, optional delta pills (+/- arrow inferred)
   Render it INSIDE the Remotion comp at native 1080x1920 (see StatBarsDemo in
   Root.tsx) — never pre-bake a square image and cover-fit it into a pane.
   ========================================================================== */

export type StatBar = {
  label: string;    // short axis label under the bar (autoshrinks, never clips)
  value: number;    // numeric height driver (relative to the max bar)
  display?: string; // printed value, e.g. "$30" / "80%" — defaults to String(value)
  delta?: string;   // optional pill, e.g. "-80%" / "+3x" — arrow from leading sign
  hot?: boolean;    // full-accent gradient; default bars get the muted fill
};

export type StatBarsProps = {
  title: string;
  subtitle?: string; // small grey line under the title (units / "ILLUSTRATIVE")
  footer?: string;   // accent punchline pinned above the bottom safe zone
  bars: StatBar[];
  accent?: string;   // channel accent, default AI Unpacked magenta
  accent2?: string;  // secondary accent, default yellow
  start?: number;    // seconds into the comp when the grow-in starts
  width?: number;    // design box, default 1080
  height?: number;   // design box, default 1920
  transparent?: boolean; // skip the ink background (overlay use)
};

/* ---- locked layout constants ---- */
const SAFE_X = 72;      // >= 64px 9:16-safe side margin
const MAX_BARS = 6;
const BAR_FRAC = 0.42;  // bar width <= 42% of slot pitch
const BAR_MAX_W = 116;  // absolute cap keeps 2-3 bar charts thin/premium
const LABEL_CLEAR = 96; // px below plot top where an "above" value label still fits

const INK = "#0E0E14";
const DEF_ACCENT = "#E0218A";
const DEF_ACCENT2 = "#FFD60A";
const FONT = "Anton, Arial Black, sans-serif";

const hexRgba = (hex: string, a: number): string => {
  const h = hex.replace("#", "");
  const v = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
  const n = parseInt(v, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
};

export const StatBars: React.FC<StatBarsProps> = ({
  title,
  subtitle,
  footer,
  bars,
  accent = DEF_ACCENT,
  accent2 = DEF_ACCENT2,
  start = 0,
  width = 1080,
  height = 1920,
  transparent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const startF = start * fps;

  const shown = bars.slice(0, MAX_BARS); // locked: max 6
  const n = Math.max(shown.length, 1);
  const maxVal = Math.max(...shown.map((b) => b.value), 1e-9);

  /* vertical rhythm (proportional so the same spec works in shorter boxes) */
  const titleY = Math.round(height * 0.075);
  const plotTop = Math.round(height * 0.22);
  /* 0.70, not 0.76 — the axis labels must clear the KARAOKE CAPTION BAND.
     Captions sit at bottom:21% (y ~1440-1517 at 1920). The old 0.76 baseline put
     the zero rule at y1459 and the bar labels at `baseline + 26` = y1485, i.e.
     the caption was guaranteed to land on the axis of every chart this component
     ever draws — measured on build 27, where "TOTALS" covered the Q2/Q3 labels
     and the feet of both bars. §4's rule is that the fix is never to move the
     locked caption position, and for a recording it is the camera; for a chart
     DRAWN IN-COMP the equivalent is the chart's own vertical rhythm, so it is
     fixed here at the system level rather than per-episode (the component is
     locked against improvisation, not against correction). 0.70 puts the labels
     at y1370-1406, clearing the band by ~34px. Costs ~11% of plot height. */
  const baseline = Math.round(height * 0.70);
  const plotH = baseline - plotTop;
  const footerY = Math.round(height * 0.88);

  const plotW = width - 2 * SAFE_X;
  const pitch = plotW / n;
  const barW = Math.min(pitch * BAR_FRAC, BAR_MAX_W);

  const titleSize = fitFont(title, 66, plotW);
  const subSize = subtitle ? fitFont(subtitle, 32, plotW) : 0;
  const footerSize = footer ? fitFont(footer, 52, plotW) : 0;

  return (
    <AbsoluteFill style={{ background: transparent ? undefined : INK, fontFamily: FONT }}>
      <style>{`@font-face { font-family: 'Anton'; src: url('${staticFile("fonts/Anton.ttf")}'); }`}</style>
      {/* header */}
      <div style={{ position: "absolute", top: titleY, width: "100%", textAlign: "center" }}>
        <div style={{ fontSize: titleSize, color: "#F2F2F8", letterSpacing: 1, textTransform: "uppercase" }}>
          {title}
        </div>
        {subtitle ? (
          <div style={{ marginTop: 14, fontSize: subSize, color: "#9A9AAE", letterSpacing: 2, textTransform: "uppercase" }}>
            {subtitle}
          </div>
        ) : null}
      </div>

      {/* gridlines + baseline */}
      {[0.25, 0.5, 0.75].map((g) => (
        <div
          key={g}
          style={{
            position: "absolute",
            left: SAFE_X,
            width: plotW,
            top: baseline - plotH * g,
            height: 2,
            background: "rgba(255,255,255,0.06)",
          }}
        />
      ))}
      <div
        style={{
          position: "absolute",
          left: SAFE_X,
          width: plotW,
          top: baseline,
          height: 3,
          background: "rgba(255,255,255,0.16)",
          borderRadius: 2,
        }}
      />

      {/* bars */}
      {shown.map((b, i) => {
        const cx = SAFE_X + pitch * (i + 0.5);
        const s = spring({
          frame: frame - startF - i * 5, // locked stagger: 5 frames per bar
          fps,
          config: { damping: 13, mass: 0.5 },
        });
        const finalH = Math.max(plotH * (b.value / maxVal), 8);
        const h = Math.max(finalH * s, 2);
        const top = baseline - h;
        const r = Math.min(barW / 2, h / 2);
        const fill = b.hot
          ? `linear-gradient(180deg, ${accent} 0%, ${hexRgba(accent, 0.55)} 100%)`
          : `linear-gradient(180deg, ${hexRgba(accent, 0.5)} 0%, ${hexRgba(accent, 0.24)} 100%)`;

        /* value label: above the animated cap; if the FINAL bar top leaves no
           headroom, pin it inside-top instead — either way it can never clip */
        const finalTop = baseline - finalH;
        const inside = finalTop < plotTop + LABEL_CLEAR;
        const display = b.display ?? String(b.value);
        const vSize = fitFont(display, 46, pitch * 0.92);
        const labelOpacity = interpolate(s, [0.7, 1], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        const valueTop = inside ? finalTop + 24 : Math.max(top - vSize - 18, plotTop + 6);

        /* delta pill: sits above the value label (or under it when inside) */
        const deltaSize = b.delta ? fitFont(b.delta, 32, pitch * 0.8) : 0;
        const deltaTop = b.delta
          ? inside
            ? valueTop + vSize + 18
            : Math.max(valueTop - deltaSize - 30, plotTop + 6)
          : 0;
        const down = (b.delta ?? "").trim().startsWith("-");

        const lSize = fitFont(b.label, 34, pitch * 0.94);

        return (
          <React.Fragment key={i}>
            <div
              style={{
                position: "absolute",
                left: cx - barW / 2,
                top,
                width: barW,
                height: h,
                background: fill,
                borderRadius: `${r}px ${r}px 6px 6px`,
                boxShadow: b.hot ? `0 10px 34px ${hexRgba(accent, 0.35)}` : undefined,
              }}
            />
            <div
              style={{
                position: "absolute",
                left: cx - pitch / 2,
                width: pitch,
                top: valueTop,
                textAlign: "center",
                fontSize: vSize,
                color: inside ? "#FFFFFF" : accent2,
                opacity: labelOpacity,
                textShadow: "0 2px 8px rgba(0,0,0,0.7)",
              }}
            >
              {display}
            </div>
            {b.delta ? (
              <div
                style={{
                  position: "absolute",
                  left: cx - pitch / 2,
                  width: pitch,
                  top: deltaTop,
                  display: "flex",
                  justifyContent: "center",
                  opacity: labelOpacity,
                }}
              >
                <div
                  style={{
                    background: accent2,
                    color: INK,
                    fontSize: deltaSize,
                    padding: "6px 18px 8px",
                    borderRadius: 999,
                    letterSpacing: 1,
                  }}
                >
                  {down ? "▼ " : "▲ "}
                  {b.delta}
                </div>
              </div>
            ) : null}
            <div
              style={{
                position: "absolute",
                left: cx - pitch / 2,
                width: pitch,
                top: baseline + 26,
                textAlign: "center",
                fontSize: lSize,
                color: "#E8E8F2",
                letterSpacing: 1,
                textTransform: "uppercase",
              }}
            >
              {b.label}
            </div>
          </React.Fragment>
        );
      })}

      {/* footer punchline */}
      {footer ? (
        <div
          style={{
            position: "absolute",
            top: footerY,
            width: "100%",
            textAlign: "center",
            fontSize: footerSize,
            color: accent,
            letterSpacing: 1,
            textTransform: "uppercase",
          }}
        >
          {footer}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
