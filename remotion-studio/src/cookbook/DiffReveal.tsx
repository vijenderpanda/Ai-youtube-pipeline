import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BRAND, SANS, MONO, rgba, clamp, coverBg, Fonts } from "./kit";

/* =============================================================================
   DiffReveal — a dev-native "transformation": an AI rewriting a BEFORE into an
   AFTER, staged like a live git diff resolving itself.

   Cookbook role: the "transformation" form. Where LineReveal shows a trend and
   BentoGrid shows facts-at-once, this shows CHANGE — a messy X becoming a sharp
   Y — using the one visual every dev reads instantly: a diff panel. A rounded
   dark editor card carries a filename tab, an editor-chrome dot cluster, and a
   red/green "+N -N" stat pill that ticks up as the change lands. Each row has a
   left gutter marker (space / minus / plus) and a colored stripe, exactly like
   a real diff hunk, so the meaning is legible in the first glance.

   Why the three phases (they map to how you actually watch a rewrite happen):
     P1  the BEFORE state holds — "same" + "del" rows visible, dels tinted red.
     P2  staggered per del: a red strike-through wipes across the line, then the
         row dims and COLLAPSES to zero height (the mess melting away).
     P3  staggered per add: "add" rows slide + fade in with a green gutter and a
         soft green glow, growing from zero height (the clean version writing in).
   A single soft "AI pass" light sweeps down the panel across P2→P3, so the
   reflow reads as *something rewriting it*, not lines randomly moving. It lands
   holding the AFTER state (dels gone, adds in, a steady caret on the last line),
   so a still near the end shows a finished, clean result.

   Layout logic: rows are absolutely positioned at an ANIMATED cumulative offset
   (each row's height eases 1→0 for dels, 0→1 for adds), which produces true
   diff reflow inside a fixed, clipped card — the card never resizes, nothing can
   overflow. Body is MONO; the message above and the stat use the brand faces.
   Mono font size auto-fits the longest line, so content can't clip horizontally.

   JSON-safe: `lines` is data ({text,kind}); no function props (build_ep_v2 feeds
   --props as JSON). Everything else is strings/numbers/bools.
   ========================================================================== */

/** one diff row — module-local so the file exports exactly the three cookbook
    symbols (the Props type below inlines this shape into `lines`). */
type DiffLine = {
  text: string; // the line's content (kept to one row; auto-sized to fit)
  kind: "same" | "del" | "add"; // context / removed / inserted
};

export type DiffRevealProps = {
  lines: DiffLine[]; // the diff hunk, in document order (dels before their adds reads best)
  filename?: string; // editor-tab label, e.g. "prompt.txt"
  title?: string; // the message above the panel — the transformation in words
  kicker?: string; // tiny label over the title (brand cue), e.g. "SOL · REWRITE"
  footer?: string; // accent punchline pinned low (optional)
  addColor?: string; // insert green (default emerald)
  delColor?: string; // remove red (default rose)
  accent?: string; // brand accent (magenta) — chrome + sweep
  ink?: string;
  start?: number; // seconds before the panel springs in
  width?: number;
  height?: number;
  transparent?: boolean;
};

/* ---- easing (kept local so the only import is remotion + ./kit) ---- */
const easeOut = (x: number) => 1 - Math.pow(1 - clamp(x), 3);
const easeInOut = (x: number) => {
  const t = clamp(x);
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
};

export const DiffReveal: React.FC<DiffRevealProps> = ({
  lines,
  filename = "file.diff",
  title,
  kicker = "SOL · REWRITE",
  footer,
  addColor = "#34D399", // emerald-400 — sleek, legible on ink
  delColor = "#F87171", // rose-400
  accent = BRAND.mag,
  ink = BRAND.ink,
  start = 0.25,
  width = 1080,
  height = 1920,
  transparent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = (frame - start * fps) / fps; // seconds since this component began

  /* ---- cap + index the hunk so card height is always bounded ---- */
  const rows = lines.slice(0, 9);
  const delOrder: number[] = []; // global-index → 0-based order among dels
  const addOrder: number[] = [];
  let dc = 0;
  let ac = 0;
  rows.forEach((l, i) => {
    if (l.kind === "del") delOrder[i] = dc++;
    else if (l.kind === "add") addOrder[i] = ac++;
  });
  const delCount = dc;
  const addCount = ac;
  const sameCount = rows.length - delCount - addCount;
  const maxVisible = Math.max(sameCount + delCount, sameCount + addCount, 1);

  /* ---- timeline (seconds) ---- */
  const stag = 0.18;
  const strikeDur = 0.34;
  const collapseDur = 0.42;
  const addDur = 0.52;
  const delT0 = 1.55;
  const lastDelStart = delT0 + Math.max(0, delCount - 1) * stag;
  // begin inserting once the last removal is ~70% collapsed (gentle overlap,
  // bounded so the peak content height can't exceed maxVisible + slack)
  const addT0 = lastDelStart + strikeDur * 0.55 + collapseDur * 0.7;

  /* ---- panel entrance ---- */
  const panelP = spring({
    frame: frame - start * fps,
    fps,
    durationInFrames: Math.round(0.55 * fps),
    config: { damping: 200, mass: 0.9 },
  });

  /* ---- per-row animation state ---- */
  type RowState = {
    heightF: number; // 0..1 fraction of a full row
    opacity: number;
    tx: number; // px horizontal offset (adds slide in)
    ty: number; // px vertical offset (dels lift as they collapse)
    strike: number; // 0..1 strike-wipe progress (dels)
  };
  const state: RowState[] = rows.map((l, i) => {
    if (l.kind === "same") {
      const appear = easeOut((t - (0.3 + i * 0.05)) / 0.4);
      return { heightF: 1, opacity: 0.35 + 0.65 * appear, tx: 0, ty: 0, strike: 0 };
    }
    if (l.kind === "del") {
      const k = delOrder[i];
      const born = easeOut((t - (0.3 + i * 0.05)) / 0.4);
      const dStart = delT0 + k * stag;
      const strike = clamp((t - dStart) / strikeDur);
      const col = easeInOut((t - (dStart + strikeDur * 0.55)) / collapseDur);
      return {
        heightF: 1 - col,
        opacity: (0.4 + 0.6 * born) * (1 - col) * (1 - 0.35 * strike),
        tx: 0,
        ty: -18 * col,
        strike,
      };
    }
    // add
    const m = addOrder[i];
    const aStart = addT0 + m * stag;
    const a = clamp((t - aStart) / addDur);
    const e = easeOut(a);
    return { heightF: e, opacity: a, tx: (1 - e) * 46, ty: 0, strike: 0 };
  });

  /* ---- geometry ---- */
  const cardX = 72;
  const cardW = width - cardX * 2; // 936
  const cardPadX = 34;
  const tabH = 92;
  const contentPadY = 26;
  const lineH = 92;
  const contentH = (maxVisible + 0.75) * lineH; // fixed; slack absorbs overlap
  const cardH = tabH + contentPadY * 2 + contentH;

  // center the card in the working band [430, 1470], never above 430
  const bandTop = 430;
  const bandBot = 1470;
  const cardY = Math.max(bandTop, bandTop + (bandBot - bandTop - cardH) / 2);

  // auto-fit mono size to the longest line so text can never clip sideways
  const gutterW = 58;
  const textPadL = 22;
  const textPadR = 26;
  const stripeW = 12; // stripe + its left margin
  const contentPx = cardW - cardPadX * 2 - stripeW - gutterW - textPadL - textPadR; // 750
  const maxChars = Math.max(1, ...rows.map((l) => l.text.length));
  const CH = 0.62; // mono advance ≈ 0.62em — used to fit + to size the strike
  const fontSize = clamp(contentPx / (maxChars * CH), 24, 42);

  /* ---- cumulative (animated) row offsets ---- */
  const tops: number[] = [];
  let acc = contentPadY;
  state.forEach((s) => {
    tops.push(acc);
    acc += lineH * s.heightF;
  });

  /* ---- stat pill counts (tick up as changes land) ---- */
  let delDone = 0;
  let addDone = 0;
  rows.forEach((l, i) => {
    if (l.kind === "del" && 1 - state[i].heightF > 0.5) delDone++;
    if (l.kind === "add" && state[i].heightF > 0.5) addDone++;
  });

  /* ---- AI "rewrite pass" light sweep across P2→P3 ---- */
  const sweepStart = delT0 - 0.1;
  const sweepEnd = addT0 + Math.max(0, addCount - 1) * stag + addDur + 0.15;
  const sweepP = clamp((t - sweepStart) / Math.max(0.6, sweepEnd - sweepStart));
  const sweepY = interpolate(sweepP, [0, 1], [-170, contentH + 40]);
  const sweepA = Math.sin(Math.PI * sweepP) * 0.9;

  // last add index → a steady caret once it lands (reads "just written")
  let lastAddIdx = -1;
  rows.forEach((l, i) => {
    if (l.kind === "add") lastAddIdx = i;
  });
  const caretA =
    lastAddIdx >= 0
      ? clamp((state[lastAddIdx].heightF - 0.9) * 10) *
        (0.55 + 0.45 * Math.sin(t * 5))
      : 0;

  const markerFor = (k: DiffLine["kind"]) => (k === "add" ? "+" : k === "del" ? "-" : " ");
  const colorFor = (k: DiffLine["kind"]) =>
    k === "add" ? addColor : k === "del" ? delColor : BRAND.mute;

  return (
    <AbsoluteFill
      style={{
        background: transparent ? undefined : coverBg(accent, ink),
        fontFamily: SANS,
      }}
    >
      <Fonts />

      {/* message above the panel — the transformation in words */}
      <div
        style={{
          position: "absolute",
          left: 80,
          right: 80,
          top: cardY - 176,
          height: 150,
          display: "flex",
          flexDirection: "column",
          justifyContent: "flex-end",
          alignItems: "center",
          textAlign: "center",
          opacity: clamp(panelP * 1.2),
        }}
      >
        {kicker ? (
          <div
            style={{
              fontSize: 30,
              letterSpacing: 6,
              textTransform: "uppercase",
              color: accent,
              fontWeight: 800,
              marginBottom: 16,
            }}
          >
            {kicker}
          </div>
        ) : null}
        {title ? (
          <div
            style={{
              fontSize: 58,
              lineHeight: 1.02,
              fontWeight: 800,
              letterSpacing: -0.5,
              color: BRAND.paper,
              maxWidth: 920,
            }}
          >
            {title}
          </div>
        ) : null}
      </div>

      {/* the diff card */}
      <div
        style={{
          position: "absolute",
          left: cardX,
          top: cardY,
          width: cardW,
          height: cardH,
          transform: `translateY(${(1 - panelP) * 26}px) scale(${0.955 + panelP * 0.045})`,
          transformOrigin: "center top",
          opacity: clamp(panelP * 1.4),
          borderRadius: 34,
          background: `linear-gradient(180deg, ${rgba("#14141c", 0.98)} 0%, ${rgba("#0b0b12", 0.98)} 100%)`,
          border: `1px solid ${rgba("#ffffff", 0.09)}`,
          boxShadow: `0 40px 120px ${rgba(ink, 0.6)}, 0 0 0 1px ${rgba(accent, 0.08)}, inset 0 1px 0 ${rgba("#ffffff", 0.06)}`,
          overflow: "hidden",
        }}
      >
        {/* editor-chrome tab: dots + filename · stat pill */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: "100%",
            height: tabH,
            display: "flex",
            alignItems: "center",
            padding: `0 ${cardPadX}px`,
            borderBottom: `1px solid ${rgba("#ffffff", 0.07)}`,
            background: rgba("#ffffff", 0.015),
          }}
        >
          <div style={{ display: "flex", gap: 12 }}>
            {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => (
              <div
                key={c}
                style={{ width: 18, height: 18, borderRadius: 9, background: rgba(c, 0.85) }}
              />
            ))}
          </div>
          <div
            style={{
              fontFamily: MONO,
              fontSize: 30,
              color: BRAND.mute,
              marginLeft: 22,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
              maxWidth: cardW * 0.42,
            }}
          >
            {filename}
          </div>
          <div style={{ flex: 1 }} />
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 16,
              fontFamily: MONO,
              fontSize: 30,
              fontWeight: 700,
              padding: "10px 22px",
              borderRadius: 999,
              background: rgba("#ffffff", 0.04),
              border: `1px solid ${rgba("#ffffff", 0.08)}`,
            }}
          >
            <span style={{ color: addColor }}>+{addDone}</span>
            <span style={{ color: delColor }}>-{delDone}</span>
          </div>
        </div>

        {/* content clip — rows reflow inside this fixed region */}
        <div
          style={{
            position: "absolute",
            left: cardPadX,
            top: tabH + contentPadY,
            width: cardW - cardPadX * 2,
            height: contentH,
            overflow: "hidden",
          }}
        >
          {rows.map((l, i) => {
            const s = state[i];
            const h = lineH * s.heightF;
            if (h < 0.5) return null; // fully collapsed → nothing to paint
            const isAdd = l.kind === "add";
            const isDel = l.kind === "del";
            const tint =
              isAdd
                ? rgba(addColor, 0.1)
                : isDel
                  ? rgba(delColor, 0.09)
                  : rgba("#ffffff", 0.015);
            return (
              <div
                key={i}
                style={{
                  position: "absolute",
                  left: 0,
                  right: 0,
                  top: tops[i],
                  height: h,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    position: "relative",
                    display: "flex",
                    alignItems: "center",
                    height: lineH,
                    borderRadius: 12,
                    background: tint,
                    opacity: s.opacity,
                    transform: `translate(${s.tx}px, ${s.ty}px)`,
                    boxShadow: isAdd
                      ? `0 0 34px ${rgba(addColor, 0.22 * s.heightF)}, inset 0 0 0 1px ${rgba(addColor, 0.16)}`
                      : "none",
                  }}
                >
                  {/* left stripe */}
                  <div
                    style={{
                      width: 6,
                      height: lineH - 22,
                      borderRadius: 4,
                      marginLeft: 6,
                      background: colorFor(l.kind),
                      opacity: l.kind === "same" ? 0 : 0.9,
                    }}
                  />
                  {/* gutter marker */}
                  <div
                    style={{
                      width: gutterW,
                      textAlign: "center",
                      fontFamily: MONO,
                      fontSize,
                      fontWeight: 800,
                      color: colorFor(l.kind),
                    }}
                  >
                    {markerFor(l.kind)}
                  </div>
                  {/* text (auto-sized, single row) */}
                  <div
                    style={{
                      position: "relative",
                      flex: 1,
                      paddingLeft: textPadL,
                      paddingRight: textPadR,
                      minWidth: 0,
                    }}
                  >
                    <span
                      style={{
                        fontFamily: MONO,
                        fontSize,
                        lineHeight: 1,
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        display: "block",
                        color: isDel
                          ? rgba(BRAND.paper, 0.55)
                          : isAdd
                            ? BRAND.paper
                            : rgba(BRAND.paper, 0.82),
                      }}
                    >
                      {l.text}
                    </span>
                    {/* red strike-through wipe (dels) */}
                    {isDel && s.strike > 0 ? (
                      <div
                        style={{
                          position: "absolute",
                          left: textPadL,
                          top: "50%",
                          height: 5,
                          width: Math.min(l.text.length * fontSize * CH, contentPx) * s.strike,
                          borderRadius: 4,
                          background: delColor,
                          boxShadow: `0 0 14px ${rgba(delColor, 0.7)}`,
                          transform: "translateY(-50%)",
                        }}
                      />
                    ) : null}
                    {/* steady caret on the freshly-written last line */}
                    {i === lastAddIdx && caretA > 0.02 ? (
                      <span
                        style={{
                          display: "inline-block",
                          width: Math.round(fontSize * 0.5),
                          height: fontSize,
                          marginLeft: 6,
                          verticalAlign: "middle",
                          background: addColor,
                          borderRadius: 3,
                          opacity: caretA,
                          boxShadow: `0 0 16px ${rgba(addColor, 0.6)}`,
                        }}
                      />
                    ) : null}
                  </div>
                </div>
              </div>
            );
          })}

          {/* the AI rewrite-pass light sweep */}
          {sweepP > 0 && sweepP < 1 ? (
            <div
              style={{
                position: "absolute",
                left: -20,
                right: -20,
                top: sweepY,
                height: 160,
                pointerEvents: "none",
                background: `linear-gradient(180deg, ${rgba(accent, 0)} 0%, ${rgba(accent, 0.16)} 45%, ${rgba(BRAND.cyan, 0.12)} 55%, ${rgba(accent, 0)} 100%)`,
                opacity: sweepA,
                mixBlendMode: "screen",
              }}
            />
          ) : null}
        </div>
      </div>

      {/* footer punchline */}
      {footer ? (
        <div
          style={{
            position: "absolute",
            left: 80,
            right: 80,
            top: Math.min(1452, cardY + cardH + 48),
            textAlign: "center",
            fontSize: 46,
            fontWeight: 800,
            letterSpacing: 1,
            textTransform: "uppercase",
            color: accent,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
            opacity: clamp((t - (addT0 + 0.3)) * 2),
          }}
        >
          {footer}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

export const diffRevealDemo: DiffRevealProps = {
  filename: "prompt.txt",
  kicker: "SOL · REWRITE",
  title: "A vague prompt becomes a sharp one.",
  lines: [
    { text: "# ask the model", kind: "same" },
    { text: "make me a logo", kind: "del" },
    { text: "something cool and modern", kind: "del" },
    { text: 'Design a wordmark logo for "Sol".', kind: "add" },
    { text: "Geometric sans, magenta on ink.", kind: "add" },
    { text: "3 variants, SVG, transparent bg.", kind: "add" },
  ],
  footer: "Specific in. Better out.",
};
