import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { SANS, SERIF, Fonts, themeTokens, rgba, clamp, type CookTheme } from "./kit";
import { clamp01, enter, settle, OUT_E } from "./motion";

/* =============================================================================
   SplitHead — the cream TITLE card in the split-register style: a small heavy
   SANS label ("HOW TO") over a big line where ONE punch word flips to Playfair
   italic in the accent; the rest is heavy sans in ink. Words land as clusters
   (rise + overshoot-settle), the punch word last, then an accent highlight-bar
   wipes under/behind it. Optional `kicker` above the label and `sub` below.
   Clones comp-dna: DirGcMXm4zw "split-caption headline (label + italic-serif
   punch word)", zB5mUHSYjXA "serif chapter title card", yJK5GueSHmU "editorial
   statement slide", VE2Uxb9Fz7I "word-built headline".
   Distinct from SerifCap (bottom caption plate) and KineticQuote (brand dark
   punchline): this is the structural pivot / chapter card on the cream canvas.
   HONESTY: pure typography — it states a claim, it never proves one. Never use
   it to fake a result, a number, or a product screen the viewer never saw.
   ========================================================================== */

export type SplitHeadProps = {
  label?: string; // small heavy sans label above the line, e.g. "HOW TO"
  line: string; // the headline; wraps into ≤3 rows
  punch: string; // substring of `line` drawn in serif-italic accent (first match)
  kicker?: string; // tiny mono-ish eyebrow above the label (optional)
  sub?: string; // muted sans sentence below the headline (optional)
  align?: "left" | "center"; // default "left" (editorial); "center" for statements
  size?: "md" | "lg"; // md ≈ 108px headline, lg ≈ 136px (default "lg")
  underline?: "bar" | "line" | "none"; // accent wipe under the punch word (default "bar")
  theme?: CookTheme; // default "cream"
  accent?: string;
  bg?: string;
  transparent?: boolean;
  start?: number; // seconds offset; component clock t = frame/fps - start
};

type Tok = { text: string; serif: boolean };

/* split `line` into word tokens, marking those inside the first `punch` match */
const tokenize = (line: string, punch: string): Tok[] => {
  const words = line.trim().split(/\s+/).filter(Boolean);
  const p = punch.trim();
  if (!p) return words.map((w) => ({ text: w, serif: false }));
  const idx = line.indexOf(p);
  if (idx < 0) return words.map((w) => ({ text: w, serif: false }));
  // map char ranges: a word is "serif" if its span intersects the punch span
  let cursor = 0;
  const toks: Tok[] = [];
  for (const w of words) {
    const s = line.indexOf(w, cursor);
    const e = s + w.length;
    cursor = e;
    toks.push({ text: w, serif: s < idx + p.length && e > idx });
  }
  return toks;
};

/* greedy wrap by estimated advance widths (sans 0.58em, serif 0.50em × 1.1) */
const wrap = (toks: Tok[], fs: number, colW: number): Tok[][] => {
  const wEm = (t: Tok) => t.text.length * (t.serif ? 0.5 * 1.1 : 0.58) + 0.28;
  const rows: Tok[][] = [[]];
  let cur = 0;
  for (const t of toks) {
    const w = wEm(t) * fs;
    if (cur + w > colW && rows[rows.length - 1].length > 0) {
      rows.push([]);
      cur = 0;
    }
    rows[rows.length - 1].push(t);
    cur += w;
  }
  return rows;
};

export const SplitHead: React.FC<SplitHeadProps> = ({
  label,
  line,
  punch,
  kicker,
  sub,
  align = "left",
  size = "lg",
  underline = "bar",
  theme = "cream",
  accent,
  bg,
  transparent,
  start = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - start;
  const tk = themeTokens(theme, accent, bg);

  const colX = 80;
  const colW = 920;

  // ---- fit: pick a font size, wrap, shrink until ≤3 rows fit the column ----
  const toks = tokenize(line ?? "", punch ?? "");
  let fs = size === "lg" ? 136 : 108;
  let rows = wrap(toks, fs, colW);
  while (rows.length > 3 && fs > 64) {
    fs -= 6;
    rows = wrap(toks, fs, colW);
  }
  const lineH = Math.round(fs * 1.08);

  // ---- timeline (component clock) ----
  const T_KICK = 0.0;
  const T_LABEL = 0.18;
  const T_WORDS = 0.42; // first non-punch word
  const stagger = 0.09;
  const nonPunch = toks.filter((x) => !x.serif).length;
  const T_PUNCH = T_WORDS + nonPunch * stagger + 0.18; // punch lands last
  const T_BAR = T_PUNCH + 0.34;
  const T_SUB = T_BAR + 0.22;

  // assign each token its appearance time: non-punch in order, punch after
  let ni = 0;
  let pi = 0;
  const atFor = toks.map((x) => {
    if (x.serif) return T_PUNCH + pi++ * 0.07;
    return T_WORDS + ni++ * stagger;
  });

  // vertical block placement: stack = kicker + label + rows + sub, centred ~y 860
  const blockH =
    (kicker ? 44 : 0) + (label ? 70 : 0) + rows.length * lineH + (sub ? 110 : 0);
  const top = clamp(Math.round(900 - blockH / 2), 260, 1500 - blockH);
  const justify = align === "center" ? "center" : "flex-start";
  const textAlign = align === "center" ? "center" : "left";

  const rise = (at: number) => {
    const p = enter(t, at, 0.46, 0.07);
    const op = clamp01((t - at) / 0.18);
    return { op, y: (1 - p) * 46 };
  };

  const kickR = rise(T_KICK);
  const labelR = rise(T_LABEL);
  const subR = rise(T_SUB);
  const barP = OUT_E(clamp01((t - T_BAR) / 0.42));
  const punchSettle = settle(t, T_PUNCH + 0.3, 0.5);

  let tokIdx = -1;

  return (
    <AbsoluteFill style={{ background: transparent ? undefined : tk.bg, fontFamily: SANS }}>
      <Fonts />
      {/* faint paper vignette so the cream reads as material, not flat */}
      {transparent ? null : (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: `radial-gradient(120% 90% at 50% 30%, ${rgba("#FFFFFF", 0.25)} 0%, ${rgba(
              tk.ink,
              0,
            )} 55%, ${rgba(tk.ink, 0.06)} 100%)`,
          }}
        />
      )}

      <div
        style={{
          position: "absolute",
          left: colX,
          width: colW,
          top,
          display: "flex",
          flexDirection: "column",
          alignItems: justify,
          textAlign,
        }}
      >
        {kicker ? (
          <div
            style={{
              fontFamily: SANS,
              fontWeight: 700,
              fontSize: 26,
              letterSpacing: 4,
              textTransform: "uppercase",
              color: tk.accent,
              height: 44,
              opacity: kickR.op,
              transform: `translateY(${kickR.y.toFixed(1)}px)`,
            }}
          >
            {kicker}
          </div>
        ) : null}

        {label ? (
          <div
            style={{
              fontFamily: SANS,
              fontWeight: 900,
              fontSize: 40,
              letterSpacing: 6,
              textTransform: "uppercase",
              color: tk.ink,
              height: 70,
              opacity: labelR.op,
              transform: `translateY(${labelR.y.toFixed(1)}px)`,
            }}
          >
            {label}
          </div>
        ) : null}

        {rows.map((row, ri) => (
          <div
            key={ri}
            style={{
              display: "flex",
              justifyContent: justify,
              alignItems: "baseline",
              columnGap: Math.round(fs * 0.24),
              height: lineH,
              lineHeight: 1,
              whiteSpace: "nowrap",
            }}
          >
            {row.map((tok, wi) => {
              tokIdx += 1;
              const at = atFor[tokIdx];
              const r = rise(at);
              const isP = tok.serif;
              return (
                <span
                  key={wi}
                  style={{
                    position: "relative",
                    display: "inline-block",
                    opacity: r.op,
                    transform: `translateY(${r.y.toFixed(1)}px) scale(${
                      isP ? (1 + punchSettle * 0.025).toFixed(4) : 1
                    })`,
                    transformOrigin: "left bottom",
                    fontFamily: isP ? SERIF : SANS,
                    fontStyle: isP ? "italic" : "normal",
                    fontWeight: isP ? 500 : 900,
                    fontSize: isP ? Math.round(fs * 1.1) : fs,
                    letterSpacing: isP ? 0 : -fs * 0.02,
                    color: isP ? tk.accent : tk.ink,
                  }}
                >
                  {isP && underline !== "none" ? (
                    <span
                      aria-hidden
                      style={{
                        position: "absolute",
                        left: -fs * 0.04,
                        right: -fs * 0.04,
                        bottom: underline === "bar" ? -fs * 0.02 : -fs * 0.06,
                        height: underline === "bar" ? fs * 0.34 : fs * 0.06,
                        background: underline === "bar" ? rgba(tk.accent, 0.18) : tk.accent,
                        transform: `scaleX(${barP.toFixed(4)})`,
                        transformOrigin: "left center",
                        borderRadius: 4,
                        zIndex: -1,
                      }}
                    />
                  ) : null}
                  {tok.text}
                </span>
              );
            })}
          </div>
        ))}

        {sub ? (
          <div
            style={{
              marginTop: 28,
              maxWidth: 820,
              fontFamily: SANS,
              fontWeight: 500,
              fontSize: 36,
              lineHeight: 1.25,
              color: tk.mute,
              opacity: subR.op,
              transform: `translateY(${subR.y.toFixed(1)}px)`,
            }}
          >
            {sub}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

export const splitHeadDemo: SplitHeadProps = {
  kicker: "Chapter 2",
  label: "How to",
  line: "Build the whole workforce",
  punch: "workforce",
  sub: "Three agents, one brief — and nobody waits on anybody.",
  align: "left",
  size: "lg",
  underline: "bar",
  theme: "cream",
};
