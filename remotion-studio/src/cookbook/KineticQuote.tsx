import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Easing,
} from "remotion";
import { BRAND, SANS, DISPLAY, rgba, clamp, coverBg, Fonts } from "./kit";

/* =============================================================================
   KineticQuote — a kinetic-typography punchline. A big-statement hook is split
   into parts that spring up one-by-one; the "hot" parts land in the accent color
   at a slightly larger scale with a highlight (a marker pad that wipes in behind
   them, or a thick underline that swipes across).

   Cookbook role: the TYPOGRAPHY FLEX / big-statement beat — the pure-text hook
   that carries the first ~3s of a Short when there's nothing to chart or demo
   (complements LineReveal's dataviz and CommandPalette's fake-UI). The whole
   value is taste: heavy Anton set centered, wrapping inside the safe column,
   emphasis choreographed so the eye lands on the two words that matter.

   Why the layout: one flex-wrap row of DISPLAY (Anton) parts, baseline-aligned,
   with generous row/column gaps so it reads as a real headline that breathes.
   Each part is `whiteSpace:nowrap` (a phrase never breaks mid-part) and the base
   size AUTO-SHRINKS so the widest part always fits the 936px safe column — so no
   string can ever clip horizontally regardless of the payload. Hot parts carry
   their highlight as an em-scaled child so the geometry tracks the word's own
   box no matter where it wraps to.

   JSON-safe: parts are {text, hot} objects; emphasis style is a string enum
   (`highlight:"bar"|"underline"`); timing is numeric seconds (no fn props —
   build_ep_v2 feeds --props as JSON). Time-sliced from `start`, landing on a
   held, fully-styled final state (a late still shows the finished phrase).
   ========================================================================== */

export type KineticQuoteProps = {
  // the phrase, split into reveal segments (first 9 render). Each part is one
  // line-unbreakable segment; `hot` gives it the accent + larger scale + wipe.
  parts: { text: string; hot?: boolean }[];
  kicker?: string; // small uppercase label above the quote
  footer?: string; // small uppercase line under the quote (attribution / CTA)
  highlight?: "bar" | "underline"; // hot-part emphasis style (default "bar")
  fontSize?: number; // base quote size px — auto-shrunk to fit, never grown (default 112)
  stagger?: number; // seconds between consecutive part reveals (default 0.14)
  accent?: string; // hot text + highlight (brand magenta)
  accent2?: string; // kicker tint (brand yellow)
  ink?: string; // base backdrop fill
  start?: number; // seconds before the first part reveals
  width?: number;
  height?: number;
  transparent?: boolean;
};

// A part never breaks mid-phrase, so the widest part sets the fit. Anton is a
// condensed face (~0.56em average advance); this keeps the estimate honest.
const AVG_ADVANCE = 0.56;
const HOT_SCALE = 1.06;

export const KineticQuote: React.FC<KineticQuoteProps> = ({
  parts,
  kicker,
  footer,
  highlight = "bar",
  fontSize = 112,
  stagger = 0.14,
  accent = BRAND.mag,
  accent2 = BRAND.yellow,
  ink = BRAND.ink,
  start = 0.25,
  width = 1080,
  height = 1920,
  transparent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const sec = (s: number) => s * fps;

  // cap the phrase so it can never overrun the frame
  const items = parts.slice(0, 9);
  const n = items.length;

  // side-safe content column (>= 64px off each edge)
  const sideSafe = 72;
  const colW = width - sideSafe * 2;

  // AUTO-FIT the base size so nothing can clip — on BOTH axes.
  // Horizontal: the widest single part (incl. its hot decorations — the marker
  // bar's ~0.15em overhang each side + the 0.04em inner padding each side) must
  // fit the safe column.
  const widestEm = items.reduce((m, p) => {
    const scale = p.hot ? HOT_SCALE : 1;
    const deco = 0.08 + (p.hot ? 0.3 : 0); // inner padding + bar overhang (em)
    return Math.max(m, scale * (p.text.length * AVG_ADVANCE + deco));
  }, 1);
  const fitW = (colW * 0.96) / widestEm;

  // Vertical: even if EVERY part wraps onto its own line, the phrase (plus a
  // kicker/footer when present) must stay above the caption band (y>1517) and
  // below the top-safe line — the block is vertically centered in the column.
  const band = height * 0.79; // caption band top (1517 @ 1080x1920)
  const blockCy = Math.round(height * 0.12) + Math.round(height * 0.64) / 2;
  const vBudget = 2 * Math.min(band - 40 - blockCy, blockCy - 96);
  const chrome = (kicker ? 78 : 0) + (footer ? 88 : 0); // kicker + footer reserves
  const perLine = HOT_SCALE + 0.18; // worst-case line advance (line height + rowGap), em
  const nLines = Math.max(1, n);
  const fitH = Math.max(0, vBudget - chrome) / (perLine * nLines);

  const fs = clamp(Math.min(fontSize, fitW, fitH), 40, 240);

  // ---- timeline (seconds → frames) --------------------------------------
  const kickLead = kicker ? 0.34 : 0; // let the kicker land before the phrase
  const partsBegin = start + kickLead;
  const partSettle = 0.5; // spring settle per part
  const wipeDelay = 0.1; // highlight starts just after the word lifts
  const wipeDur = 0.42;
  const lastLandT = partsBegin + (n - 1) * stagger + partSettle;

  const kProg = kicker
    ? clamp(
        spring({
          frame: Math.max(0, frame - sec(start)),
          fps,
          config: { damping: 18, stiffness: 120 },
        })
      )
    : 0;

  const fProg = footer
    ? clamp(
        spring({
          frame: Math.max(0, frame - sec(lastLandT)),
          fps,
          config: { damping: 20, stiffness: 110 },
        })
      )
    : 0;

  return (
    <AbsoluteFill
      style={{
        background: transparent ? undefined : coverBg(accent, ink),
        fontFamily: SANS,
      }}
    >
      <Fonts />

      {/* centered content column, held clear of the caption band (bottom ~21%) */}
      <div
        style={{
          position: "absolute",
          left: sideSafe,
          top: Math.round(height * 0.12),
          width: colW,
          height: Math.round(height * 0.64),
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
        }}
      >
        {/* kicker — small uppercase label between two accent ticks */}
        {kicker ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 18,
              marginBottom: 44,
              opacity: kProg,
              transform: `translateY(${interpolate(kProg, [0, 1], [18, 0])}px)`,
            }}
          >
            <span style={{ width: 46, height: 5, background: accent2, borderRadius: 3 }} />
            <span
              style={{
                fontSize: 34,
                fontWeight: 800,
                letterSpacing: 8,
                textTransform: "uppercase",
                color: accent2,
              }}
            >
              {kicker}
            </span>
            <span style={{ width: 46, height: 5, background: accent2, borderRadius: 3 }} />
          </div>
        ) : null}

        {/* the phrase — flex-wrap of Anton parts, baseline-aligned */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "center",
            alignItems: "baseline",
            rowGap: Math.round(fs * 0.18),
            columnGap: Math.round(fs * 0.26),
            fontFamily: DISPLAY,
            lineHeight: 1,
          }}
        >
          {items.map((part, i) => {
            const appear = sec(partsBegin + i * stagger);
            const prog = clamp(
              spring({
                frame: Math.max(0, frame - appear),
                fps,
                config: { damping: 15, stiffness: 130 },
              })
            );
            const rise = interpolate(prog, [0, 1], [52, 0]);
            const sc = interpolate(prog, [0, 1], [0.92, 1]);

            const isHot = !!part.hot;
            const pFs = Math.round(fs * (isHot ? HOT_SCALE : 1));

            // highlight wipe — starts after the word has begun to lift
            const wipe = clamp((frame - (appear + sec(wipeDelay))) / sec(wipeDur));
            const wipeE = interpolate(wipe, [0, 1], [0, 1], {
              easing: Easing.out(Easing.cubic),
            });

            return (
              <span
                key={i}
                style={{
                  position: "relative",
                  display: "inline-block",
                  whiteSpace: "nowrap",
                  fontSize: pFs,
                  opacity: prog,
                  transform: `translateY(${rise}px) scale(${sc})`,
                }}
              >
                {/* marker pad behind hot words (default) */}
                {isHot && highlight === "bar" ? (
                  <span
                    aria-hidden
                    style={{
                      position: "absolute",
                      left: "-0.15em",
                      right: "-0.15em",
                      top: "0.02em",
                      bottom: "0.1em",
                      background: rgba(accent, 0.22),
                      border: `2px solid ${rgba(accent, 0.5)}`,
                      borderRadius: "0.12em",
                      boxShadow: `0 14px 44px ${rgba(accent, 0.4)}`,
                      transform: `scaleX(${wipeE}) rotate(-1.3deg)`,
                      transformOrigin: "0% 50%",
                      zIndex: 0,
                    }}
                  />
                ) : null}

                {/* underline that swipes across hot words (alt) */}
                {isHot && highlight === "underline" ? (
                  <span
                    aria-hidden
                    style={{
                      position: "absolute",
                      left: "-0.04em",
                      right: "-0.04em",
                      bottom: "-0.01em",
                      height: "0.16em",
                      background: accent,
                      borderRadius: "0.08em",
                      boxShadow: `0 8px 26px ${rgba(accent, 0.55)}`,
                      transform: `scaleX(${wipeE})`,
                      transformOrigin: "0% 50%",
                      zIndex: 0,
                    }}
                  />
                ) : null}

                <span
                  style={{
                    position: "relative",
                    zIndex: 1,
                    padding: "0 0.04em",
                    color: isHot ? accent : BRAND.paper,
                    textShadow: isHot
                      ? `0 8px 34px ${rgba(accent, 0.45)}`
                      : `0 6px 26px ${rgba("#000000", 0.35)}`,
                  }}
                >
                  {part.text}
                </span>
              </span>
            );
          })}
        </div>

        {/* footer — attribution / CTA line under the phrase */}
        {footer ? (
          <div
            style={{
              marginTop: 48,
              fontSize: 40,
              letterSpacing: 2,
              textTransform: "uppercase",
              color: BRAND.mute,
              opacity: fProg,
              transform: `translateY(${interpolate(fProg, [0, 1], [16, 0])}px)`,
            }}
          >
            {footer}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

export const kineticQuoteDemo: KineticQuoteProps = {
  kicker: "The real unlock",
  parts: [
    { text: "You don't" },
    { text: "need" },
    { text: "MORE TIME.", hot: true },
    { text: "You need a" },
    { text: "SYSTEM.", hot: true },
  ],
  footer: "Systems beat willpower.",
  highlight: "bar",
};
