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
   Odometer — a big number whose every digit is a slot-machine REEL that rolls
   to its final glyph, columns settling left→right with a sub-cell overshoot.

   Cookbook role: the invented "micro-interaction + readability workhorse". Where
   LineReveal counts a headline number by re-rendering the glyph, this earns its
   place with the *mechanism people find satisfying*: a physical wheel of stacked
   0–9 glyphs, each reel clipped to exactly one cell height (overflow:hidden) and
   translated by an animated Y offset whose held final position is exactly
   -finalDigit*cellHeight. It's the shot you cut to on "we hit 128K subscribers" —
   a metric that lands with weight instead of just appearing.

   Why the layout: a glassy display panel frames the reels so the mechanical wheel
   reads as one instrument, not floating glyphs; a small uppercase label names the
   metric above it, and a semantic delta pill (up/down + colour inferred from the
   delta's leading +/- sign) sits below. The whole stack lives in the upper-middle
   so it clears the karaoke caption band (bottom ~21%).

   The roll (per digit column c, left→right):
     • all reels start spinning together at `start`; each STOPS on its own clock —
       duration and revolutions grow with c, so the sweep settles left→right and
       the right-hand reels stay a blur the longest (real odometer behaviour).
     • the bulk travel is a hard ease-out over `landing` cells (monotonic → lands
       EXACTLY on the digit). A separate, cell-unit half-sine bump nudges it
       ~half a cell past and back — an overshoot that never scales with travel.
     • past its window a reel holds -landing*cellH, so a still near the end shows
       the finished number, crisp.

   JSON-safe: value is a number; prefix/suffix/label/delta are strings; group is a
   bool (no function props — build_ep_v2 feeds --props as JSON).
   ========================================================================== */

export type OdometerProps = {
  value: number; // the target the reels land on (rounded; abs value is rolled)
  prefix?: string; // static leading glyphs, e.g. "$"
  suffix?: string; // static trailing glyphs, e.g. "%", "K", "/mo"
  label?: string; // small uppercase caption above the number
  delta?: string; // pill text; a leading +/- infers up/down + its colour
  group?: boolean; // insert thousands separators (rendered as static commas)
  accent?: string; // backdrop glow + reel glow (brand magenta)
  accent2?: string; // prefix/suffix glyphs (brand yellow)
  ink?: string; // base fill
  start?: number; // seconds before the reels begin spinning (default 0.2)
  width?: number;
  height?: number;
  transparent?: boolean; // skip the coverBg backdrop (overlay use)
};

/* ---- roll tuning -------------------------------------------------------- */
const MAX_DIGITS = 12; // hard cap on rendered digit columns (DOM guard)
const BASE_DUR = 0.9; // seconds the leftmost reel spins
const STAGGER = 0.14; // extra spin seconds per column to the right
const BASE_SPINS = 2; // full 0–9 revolutions the leftmost reel makes
const OVERSHOOT = 0.5; // settle overshoot, in CELLS (independent of travel)
const BUFFER = 2; // spare glyphs below the landing cell to cover overshoot

/* ---- glyph metrics (base, pre-fit-scale) -------------------------------- */
const F = 210; // digit font size (Anton)
const CELL_H = Math.round(F * 1.18); // reel window / glyph box height
const DIGIT_W = Math.round(F * 0.6); // reel column width
const SEP_W = Math.round(F * 0.32); // comma column width
const STAT_W = Math.round(F * 0.62); // per-char width for prefix/suffix/sign
const PAD_X = 84; // panel horizontal padding (each side ~half)
const PAD_Y = 56; // panel vertical padding

/* soft cylinder mask: fades reel glyphs to transparent at the window edges so
   the roll reads as a physical wheel — the resting centre digit stays opaque. */
const FADE = "linear-gradient(180deg, transparent 0%, #000 8%, #000 92%, transparent 100%)";

/** hard ease-out: fast entry, decisive stop — the "already spinning" feel. */
const easeOutQuint = (u: number): number => 1 - Math.pow(1 - u, 5);

/** thousands-group an integer string: "128400" → "128,400". */
const groupInt = (s: string): string => s.replace(/\B(?=(\d{3})+(?!\d))/g, ",");

export const Odometer: React.FC<OdometerProps> = ({
  value,
  prefix = "",
  suffix = "",
  label,
  delta,
  group = false,
  accent = BRAND.mag,
  accent2 = BRAND.yellow,
  ink = BRAND.ink,
  start = 0.2,
  width = 1080,
  height = 1920,
  transparent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps; // seconds

  // semantic delta: colour + arrow inferred from the leading sign
  const UP = "#37E1A0";
  const DOWN = "#FF5D73";
  const draw = (delta ?? "").trim();
  const dir = draw.startsWith("+") ? "up" : draw.startsWith("-") ? "down" : "flat";
  const dCol = dir === "up" ? UP : dir === "down" ? DOWN : accent2;
  const dArrow = dir === "up" ? "▲" : dir === "down" ? "▼" : "•";
  const dText = ((dir === "flat" ? draw : draw.slice(1)).trim() || "").slice(0, 24);

  // build the digit string
  const safe = Number.isFinite(value) ? value : 0;
  const neg = safe < 0;
  let intStr = Math.abs(Math.round(safe)).toString();
  if (intStr.length > MAX_DIGITS) intStr = intStr.slice(0, MAX_DIGITS);
  const chars = (group ? groupInt(intStr) : intStr).split("");
  const digitCount = chars.filter((c) => c >= "0" && c <= "9").length;

  // when the LAST reel finishes (drives the pill + the settle pop)
  const lastCol = Math.max(0, digitCount - 1);
  const maxDur = BASE_DUR + Math.min(lastCol, 6) * STAGGER;

  // one reel: rolls to `digit`, stops on its own clock, holds the final cell
  const reel = (digit: number, c: number, key: number): React.ReactNode => {
    const spins = BASE_SPINS + Math.min(c, 5);
    const dur = BASE_DUR + Math.min(c, 6) * STAGGER;
    const landing = spins * 10 + digit; // cell index of the final glyph
    const local = t - start;

    const travelU = clamp(local / (dur * 0.72)); // bulk spin: 0..1 by 72% of window
    const travel = landing * easeOutQuint(travelU); // monotonic → exact landing
    const oscU = clamp((local - dur * 0.72) / (dur * 0.28)); // settle tail: 0..1
    const os = OVERSHOOT * Math.sin(oscU * Math.PI); // nudge past & back (cells)
    const offset = -Math.round((travel + os) * CELL_H);

    const glyphs: React.ReactNode[] = [];
    for (let i = 0; i <= landing + BUFFER; i++) {
      glyphs.push(
        <div
          key={i}
          style={{
            height: CELL_H,
            lineHeight: `${CELL_H}px`,
            fontFamily: DISPLAY,
            fontSize: F,
            textAlign: "center",
            color: BRAND.paper,
            textShadow: `0 4px 22px ${rgba(accent, 0.5)}, 0 2px 6px ${rgba(ink, 0.55)}`,
          }}
        >
          {i % 10}
        </div>
      );
    }

    return (
      <div
        key={key}
        style={{
          width: DIGIT_W,
          height: CELL_H,
          overflow: "hidden",
          position: "relative",
          flex: "0 0 auto",
          maskImage: FADE,
          WebkitMaskImage: FADE,
        }}
      >
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            transform: `translateY(${offset}px)`,
            willChange: "transform",
          }}
        >
          {glyphs}
        </div>
      </div>
    );
  };

  // a static glyph box (prefix / suffix / sign / comma) — same box → shared baseline
  const stat = (text: string, color: string, w: number, key: number): React.ReactNode => (
    <div
      key={key}
      style={{
        width: w,
        height: CELL_H,
        lineHeight: `${CELL_H}px`,
        fontFamily: DISPLAY,
        fontSize: F,
        textAlign: "center",
        color,
        flex: "0 0 auto",
      }}
    >
      {text}
    </div>
  );

  // assemble the row (and measure its intrinsic width for the fit-scale)
  const cells: React.ReactNode[] = [];
  let k = 0;
  let col = 0;
  let contentW = 0;
  if (prefix) {
    cells.push(stat(prefix, accent2, prefix.length * STAT_W, k++));
    contentW += prefix.length * STAT_W;
  }
  if (neg) {
    cells.push(stat("-", BRAND.paper, STAT_W, k++));
    contentW += STAT_W;
  }
  for (const ch of chars) {
    if (ch >= "0" && ch <= "9") {
      cells.push(reel(Number(ch), col, k++));
      contentW += DIGIT_W;
      col++;
    } else {
      cells.push(stat(ch, rgba(BRAND.paper, 0.55), SEP_W, k++));
      contentW += SEP_W;
    }
  }
  if (suffix) {
    cells.push(stat(suffix, accent2, suffix.length * STAT_W, k++));
    contentW += suffix.length * STAT_W;
  }

  // fit the framed panel inside the 64px safe margins, and never upscale
  const panelW = contentW + PAD_X;
  const fit = clamp((width - 128) / panelW, 0.25, 1);
  // a single settle pop once every reel has landed
  const pop = 1 + 0.035 * Math.sin(clamp((t - (start + maxDur)) / 0.4) * Math.PI);
  // pop multiplies the fit-scale, so hard-cap the combined scale to keep the
  // framed panel inside a 48px margin at ALL times — otherwise the pop (and the
  // 0.25 fit floor on pathological long prefix/suffix or 12-digit inputs) could
  // push the panel past the 1080 frame edge.
  const rowScale = Math.min(fit * pop, (width - 96) / panelW);

  // layout anchors
  const numCY = Math.round(height * 0.42);
  const labelCY = Math.round(height * 0.27);
  const pillCY = Math.round(height * 0.565);

  // label + pill entrances
  const labelP = spring({
    frame: frame - Math.round(Math.max(0, start - 0.05) * fps),
    fps,
    config: { damping: 16, mass: 0.8, stiffness: 120 },
  });
  const pillP = spring({
    frame: frame - Math.round((start + maxDur * 0.72) * fps),
    fps,
    config: { damping: 14, mass: 0.9, stiffness: 140 },
  });

  return (
    <AbsoluteFill
      style={{ background: transparent ? undefined : coverBg(accent, ink), fontFamily: SANS }}
    >
      <Fonts />

      {/* metric label */}
      {label ? (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: labelCY,
            transform: `translateY(${-50 + (1 - labelP) * -3}%)`,
            textAlign: "center",
            opacity: clamp(labelP),
          }}
        >
          <span
            style={{
              display: "inline-block",
              maxWidth: width - 160,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              fontFamily: SANS,
              fontSize: 46,
              fontWeight: 800,
              letterSpacing: 8,
              textTransform: "uppercase",
              color: rgba(BRAND.paper, 0.82),
            }}
          >
            {label}
          </span>
        </div>
      ) : null}

      {/* the reels, framed in a glassy display panel (both share the fit-scale) */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: numCY,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <div
          style={{
            transform: `scale(${rowScale})`,
            transformOrigin: "center",
            position: "relative",
            display: "flex",
            alignItems: "center",
          }}
        >
          <div
            style={{
              position: "absolute",
              left: "50%",
              top: "50%",
              width: contentW + PAD_X,
              height: CELL_H + PAD_Y,
              transform: "translate(-50%,-50%)",
              borderRadius: 46,
              background: `linear-gradient(180deg, ${rgba(BRAND.paper, 0.06)} 0%, ${rgba(
                ink,
                0.34
              )} 100%)`,
              border: `2px solid ${rgba(BRAND.paper, 0.1)}`,
              boxShadow: `0 30px 80px ${rgba(ink, 0.5)}, inset 0 2px 0 ${rgba(
                BRAND.paper,
                0.14
              )}, inset 0 0 70px ${rgba(accent, 0.1)}`,
            }}
          />
          <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
            {cells}
          </div>
        </div>
      </div>

      {/* semantic delta pill */}
      {draw ? (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: pillCY,
            textAlign: "center",
            transform: `translateY(${-50 + (1 - pillP) * 6}%)`,
            opacity: clamp(pillP),
          }}
        >
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 14,
              maxWidth: width - 180,
              padding: "18px 36px",
              borderRadius: 999,
              background: rgba(dCol, 0.13),
              border: `2px solid ${rgba(dCol, 0.42)}`,
              color: dCol,
              fontFamily: SANS,
              fontSize: 46,
              fontWeight: 800,
              letterSpacing: 0.5,
              boxShadow: `0 12px 40px ${rgba(dCol, 0.22)}`,
              transform: `scale(${interpolate(clamp(pillP), [0, 1], [0.86, 1])})`,
            }}
          >
            <span style={{ fontSize: 34, lineHeight: 1 }}>{dArrow}</span>
            <span
              style={{
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {dText}
            </span>
          </span>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

export const odometerDemo: OdometerProps = {
  value: 128400,
  group: true,
  label: "Subscribers",
  delta: "+2.4K today",
};
