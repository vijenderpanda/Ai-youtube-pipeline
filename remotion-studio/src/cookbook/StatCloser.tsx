import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { AuroraBed, CREAM, DISPLAY, Fonts, SANS, SERIF, rgba, themeTokens } from "./kit";
import { clamp01, enter, idle, settle } from "./motion";

/* =============================================================================
   StatCloser — the calm editorial "number closer": ONE cream card, small-caps
   label above, one big Anton figure that counts up (eased, digit-locked), then
   an accent underline sweeps beneath it, a one-line sub (Playfair italic for
   the punch), optional tiny source chip, optional ghost `compare` figure.
   Clones comp-dna: dLS-6jn9xxc "stat/number closer card", cf6WEZUVbEI
   "stat/dashboard card set", IFBBmwsGpUw "stat/claim header card".
   Distinct from Odometer (reel mechanic, brand dark) and GlassPanel.
   Animates on t = frame/fps - start, reads once, then HOLDS the final state.
   HONESTY: `value`/`compare` are supplied data — never invent a figure, and
   never use the source chip to imply a citation that does not exist.
   ========================================================================== */

export type StatCloserProps = {
  value: number; // the figure — supplied data, counts up from 0
  prefix?: string; // "$", "₹", "~"
  suffix?: string; // "%", "x", " LPA"
  decimals?: number; // default 0
  label: string; // small-caps label above the figure
  sub?: string; // one line under the rule; *asterisks* mark the serif punch word(s)
  source?: string; // tiny source chip (only for a real source)
  compare?: { label: string; value: number; prefix?: string; suffix?: string; decimals?: number };
  theme?: "brand" | "cream"; // default "cream"
  accent?: string;
  bg?: string;
  transparent?: boolean; // skip the backdrop (overlay use)
  start?: number; // seconds before the component clock begins
};

const fmt = (v: number, decimals: number): string =>
  v.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });

/* count-up: fast early, slow landing — the last digit "locks" rather than blurs */
const countEase = (p: number): number => 1 - Math.pow(1 - p, 3.2);

/* split a sub line on *punch* markers into sans / serif-italic runs */
const splitSub = (s: string): Array<{ t: string; punch: boolean }> =>
  s
    .split(/(\*[^*]+\*)/g)
    .filter((x) => x.length > 0)
    .map((x) => (x.startsWith("*") && x.endsWith("*") ? { t: x.slice(1, -1), punch: true } : { t: x, punch: false }));

export const StatCloser: React.FC<StatCloserProps> = ({
  value,
  prefix = "",
  suffix = "",
  decimals = 0,
  label,
  sub,
  source,
  compare,
  theme = "cream",
  accent,
  bg,
  transparent,
  start = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tBed = frame / fps;
  const t = tBed - start;
  const tk = themeTokens(theme, accent, bg);
  const cream = theme === "cream";

  // ---- timeline (seconds on the component clock) ---------------------------
  const T_CARD = 0.0; // card rises
  const T_LABEL = 0.28; // label fades in
  const T_COUNT = 0.45; // count-up begins
  const D_COUNT = 1.35; // count-up duration
  const T_RULE = T_COUNT + D_COUNT + 0.05; // underline sweep
  const T_SUB = T_RULE + 0.3;
  const T_CHIP = T_SUB + 0.3;
  const T_CMP = T_SUB + 0.15;

  const cardP = enter(t, T_CARD, 0.5, 0.05);
  const cardOp = clamp01((t - T_CARD) / 0.25);
  const labelOp = clamp01((t - T_LABEL) / 0.3);
  const countP = countEase(clamp01((t - T_COUNT) / D_COUNT));
  const shown = value * countP;
  const landed = t >= T_COUNT + D_COUNT;
  const landKick = settle(t, T_COUNT + D_COUNT, 0.45); // stamp-then-settle on the lock
  const ruleP = clamp01((t - T_RULE) / 0.42);
  const ruleEased = 1 - Math.pow(1 - ruleP, 3);
  const subP = enter(t, T_SUB, 0.4, 0.06);
  const subOp = clamp01((t - T_SUB) / 0.25);
  const chipOp = clamp01((t - T_CHIP) / 0.3);
  const cmpP = enter(t, T_CMP, 0.4, 0.06);
  const cmpOp = clamp01((t - T_CMP) / 0.3);
  const drift = idle(t, 3, 1.6); // the hold breathes, never freezes

  // ---- layout: card centred in the safe box, nothing below y=1500 -----------
  const cardX = 80;
  const cardW = 920;
  const cardY = 560;
  const cardH = compare ? 820 : 700; // bottom ≤ 1380 — clear of the caption zone
  const figStr = `${prefix}${fmt(shown, decimals)}${suffix}`;
  const figChars = `${prefix}${fmt(value, decimals)}${suffix}`.length;
  const figSize = Math.round(Math.min(240, (cardW - 160) / (figChars * 0.52)));
  const ruleW = Math.min(cardW - 160, Math.max(240, figChars * figSize * 0.5));

  const paper = cream ? CREAM.card : tk.card;
  const subRuns = sub ? splitSub(sub) : [];

  return (
    <AbsoluteFill style={{ background: transparent ? undefined : tk.bg, fontFamily: SANS }}>
      <Fonts />
      {transparent ? null : cream ? (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: `radial-gradient(110% 70% at 50% 8%, ${CREAM.bgDeep} 0%, ${tk.bg} 60%)`,
          }}
        />
      ) : (
        <AuroraBed t={tBed} accent={tk.accent} ink={tk.bg} />
      )}

      {/* the card */}
      <div
        style={{
          position: "absolute",
          left: cardX,
          top: cardY,
          width: cardW,
          height: cardH,
          borderRadius: 40,
          background: paper,
          border: `1px solid ${tk.line}`,
          boxShadow: cream
            ? `0 30px 80px -40px ${rgba("#000", 0.35)}, 0 2px 0 ${rgba("#fff", 0.6)} inset`
            : `0 40px 100px -40px ${rgba("#000", 0.7)}, 0 1px 0 ${rgba("#fff", 0.12)} inset`,
          opacity: cardOp,
          transform: `translate(${drift.x.toFixed(2)}px, ${(drift.y + (1 - cardP) * 70).toFixed(2)}px) scale(${(0.96 + 0.04 * cardP).toFixed(4)})`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "0 80px",
          boxSizing: "border-box",
        }}
      >
        {/* accent corner tick — the only decoration */}
        <div
          style={{
            position: "absolute",
            top: 44,
            left: 56,
            width: 28,
            height: 8,
            borderRadius: 4,
            background: tk.accent,
            opacity: labelOp,
          }}
        />

        {/* small-caps label */}
        <div
          style={{
            fontFamily: SANS,
            fontWeight: 700,
            fontSize: 30,
            letterSpacing: 6,
            textTransform: "uppercase",
            color: tk.mute,
            opacity: labelOp,
            transform: `translateY(${((1 - labelOp) * 14).toFixed(1)}px)`,
            marginBottom: 18,
            textAlign: "center",
          }}
        >
          {label}
        </div>

        {/* the figure */}
        <div
          style={{
            fontFamily: DISPLAY,
            fontSize: figSize,
            lineHeight: 1.05,
            color: tk.ink,
            letterSpacing: 1,
            fontVariantNumeric: "tabular-nums",
            whiteSpace: "nowrap",
            opacity: clamp01((t - T_COUNT + 0.1) / 0.2),
            transform: `scale(${(1 + landKick * 0.05).toFixed(4)})`,
            transformOrigin: "50% 80%",
          }}
        >
          {figStr}
        </div>

        {/* accent underline sweep — draws left→right once the count lands */}
        <div style={{ width: ruleW, height: 12, marginTop: 14, position: "relative" }}>
          <div
            style={{
              position: "absolute",
              left: 0,
              top: 0,
              height: 12,
              width: `${(ruleEased * 100).toFixed(2)}%`,
              borderRadius: 6,
              background: tk.accent,
              boxShadow: `0 6px 18px ${rgba(tk.accent, 0.35)}`,
            }}
          />
        </div>

        {/* sub line — sans with the serif-italic punch */}
        {sub ? (
          <div
            style={{
              marginTop: 34,
              fontSize: 40,
              lineHeight: 1.25,
              color: tk.ink,
              textAlign: "center",
              opacity: subOp,
              transform: `translateY(${((1 - subP) * 26).toFixed(1)}px)`,
              maxWidth: cardW - 140,
            }}
          >
            {subRuns.map((r, i) =>
              r.punch ? (
                <span key={i} style={{ fontFamily: SERIF, fontStyle: "italic", fontWeight: 600, fontSize: 46, color: tk.accent }}>
                  {r.t}
                </span>
              ) : (
                <span key={i} style={{ fontFamily: SANS, fontWeight: 600 }}>
                  {r.t}
                </span>
              ),
            )}
          </div>
        ) : null}

        {/* ghost compare figure */}
        {compare ? (
          <div
            style={{
              marginTop: 40,
              display: "flex",
              alignItems: "baseline",
              gap: 18,
              opacity: cmpOp * 0.8,
              transform: `translateY(${((1 - cmpP) * 20).toFixed(1)}px)`,
            }}
          >
            <span style={{ fontFamily: SANS, fontWeight: 700, fontSize: 24, letterSpacing: 4, textTransform: "uppercase", color: tk.mute }}>
              {compare.label}
            </span>
            <span
              style={{
                fontFamily: DISPLAY,
                fontSize: 64,
                lineHeight: 1,
                color: tk.mute,
                textDecoration: "line-through",
                textDecorationColor: rgba(tk.accent, 0.7),
                textDecorationThickness: 5,
              }}
            >
              {`${compare.prefix ?? ""}${fmt(compare.value, compare.decimals ?? 0)}${compare.suffix ?? ""}`}
            </span>
          </div>
        ) : null}

        {/* source chip */}
        {source ? (
          <div
            style={{
              position: "absolute",
              bottom: 36,
              right: 48,
              fontFamily: SANS,
              fontWeight: 600,
              fontSize: 22,
              letterSpacing: 1,
              color: tk.mute,
              border: `1px solid ${tk.line}`,
              borderRadius: 999,
              padding: "8px 18px",
              opacity: chipOp,
              background: cream ? rgba("#fff", 0.5) : rgba("#fff", 0.04),
            }}
          >
            {source}
          </div>
        ) : null}
      </div>

      {/* landed tick — a single quiet dot under the card once the number locks */}
      <div
        style={{
          position: "absolute",
          left: 540 - 6,
          top: cardY + cardH + 40,
          width: 12,
          height: 12,
          borderRadius: 6,
          background: tk.accent,
          opacity: landed ? clamp01((t - T_RULE) / 0.3) : 0,
        }}
      />
    </AbsoluteFill>
  );
};

export const statCloserDemo: StatCloserProps = {
  value: 6069,
  prefix: "₹",
  label: "Spent on Blinkit",
  sub: "in 6 orders — *₹1,012 a tap*",
  source: "from your own screenshots",
  compare: { label: "you guessed", value: 2000, prefix: "₹" },
  theme: "cream",
};
