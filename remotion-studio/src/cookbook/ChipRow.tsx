import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { CookTheme, DISPLAY, Fonts, SANS, SERIF, rgba, themeTokens } from "./kit";
import { enter, settle } from "./motion";

/* =============================================================================
   ChipRow — a pill/chip system: one row (or wrapped rows) of rounded chips that
   pop in staggered, each able to go HOT (accent fill) or get STRUCK (objection
   dismissed with a drawn strike-through). Variants: label / model / platform /
   objection / toggle.
   Clones comp-dna refs: cf6WEZUVbEI "pill toggle/settings bar", "objection pill
   list", "platform badge chip"; ovLAIhbk3ek "model pill", "stacked chip list";
   cUG0TGwE9-4 "prompt-chip bar".
   NOT the transcript — that is ChipCaption. This is for facts/labels/options.
   HONESTY: chip text is a label, never a benchmark; a `hot` chip marks emphasis
   not a measured winner; `struck` must only dismiss a claim the VO actually
   refutes. Never fake a model/platform as "supported" by chipping its name.
   ========================================================================== */

export type ChipKind = "label" | "model" | "platform" | "objection" | "toggle";

export type ChipItem = {
  text: string;
  kind?: ChipKind;
  /** accent fill — the emphasised chip. */
  hot?: boolean;
  /** strike-through + dim — an objection dismissed. */
  struck?: boolean;
  /** leading emoji / glyph; "dot" draws a small accent dot instead. */
  icon?: string;
  /** seconds (relative to `start`) this chip lands; default = stagger index. */
  t?: number;
};

export type ChipRowProps = {
  chips: ChipItem[];
  align?: "left" | "center";
  size?: "sm" | "md" | "lg";
  /** allow the row to wrap into several rows (default true). */
  wrap?: boolean;
  /** y of the row's top edge in the 1080x1920 box. */
  y?: number;
  /** default gap in seconds between successive chip landings. */
  stagger?: number;
  /** hot / struck states flip this many seconds after the chip lands. */
  stateDelay?: number;
  /** optional small caps eyebrow above the row. */
  eyebrow?: string;
  theme?: CookTheme;
  accent?: string;
  bg?: string;
  transparent?: boolean;
  start?: number;
};

const SIZES = {
  sm: { font: 30, padX: 22, padY: 12, gap: 14, radius: 999, icon: 28 },
  md: { font: 40, padX: 30, padY: 16, gap: 18, radius: 999, icon: 38 },
  lg: { font: 54, padX: 40, padY: 22, gap: 24, radius: 999, icon: 50 },
} as const;

export const ChipRow: React.FC<ChipRowProps> = ({
  chips = [],
  align = "center",
  size = "md",
  wrap = true,
  y = 760,
  stagger = 0.22,
  stateDelay = 0.55,
  eyebrow,
  theme = "cream",
  accent,
  bg,
  transparent = false,
  start = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - start;
  const tok = themeTokens(theme, accent, bg);
  const S = SIZES[size];
  const cream = theme === "cream";

  const eyebrowOn = enter(t, 0, 0.4);

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: transparent ? "transparent" : tok.bg,
        fontFamily: SANS,
        overflow: "hidden",
      }}
    >
      <Fonts />
      {eyebrow ? (
        <div
          style={{
            position: "absolute",
            left: 80,
            right: 80,
            top: y - S.font * 1.4,
            textAlign: align,
            fontFamily: DISPLAY,
            fontSize: Math.round(S.font * 0.62),
            letterSpacing: 3,
            textTransform: "uppercase",
            color: tok.mute,
            opacity: eyebrowOn,
            transform: `translateY(${(1 - eyebrowOn) * 14}px)`,
          }}
        >
          {eyebrow}
        </div>
      ) : null}
      <div
        style={{
          position: "absolute",
          left: 80,
          width: 920,
          top: y,
          display: "flex",
          flexWrap: wrap ? "wrap" : "nowrap",
          justifyContent: align === "center" ? "center" : "flex-start",
          alignItems: "center",
          gap: S.gap,
        }}
      >
        {chips.map((c, i) => {
          const at = c.t ?? i * stagger;
          const p = enter(t, at, 0.42, 0.1);
          if (p <= 0) return null;
          const kind = c.kind ?? "label";
          const sp = 1 + settle(t, at + 0.3, 0.45) * 0.03;
          const st = t - (at + stateDelay);
          const hotP = c.hot ? Math.max(0, Math.min(1, st / 0.25)) : 0;
          const strikeP = c.struck ? Math.max(0, Math.min(1, st / 0.3)) : 0;
          const objection = kind === "objection";
          const model = kind === "model";
          const toggle = kind === "toggle";
          const platform = kind === "platform";

          // base surface per kind
          let fill = cream ? tok.card : tok.card;
          let fg = tok.ink;
          let border = `1.5px solid ${tok.line}`;
          if (objection) { fill = cream ? "#1C1C1A" : "#23232C"; fg = cream ? "#F4F2EC" : tok.ink; border = "1.5px solid transparent"; }
          if (model) { fill = cream ? rgba(tok.accent, 0.12) : rgba(tok.accent, 0.16); fg = tok.ink; border = `1.5px solid ${rgba(tok.accent, 0.45)}`; }
          if (toggle) { fill = cream ? "#DEDAD1" : "#1C1C26"; }
          // hot overrides
          const hotFill = tok.accent;
          const hotFg = cream ? "#FFFDF8" : "#0E0E14";
          const mixFill = hotP > 0 ? hotFill : fill;
          const mixFg = hotP > 0.5 ? hotFg : fg;
          const dim = strikeP > 0 ? 1 - 0.5 * strikeP : 1;

          return (
            <div
              key={i}
              style={{
                position: "relative",
                display: "inline-flex",
                alignItems: "center",
                gap: Math.round(S.icon * 0.3),
                padding: `${S.padY}px ${S.padX}px`,
                borderRadius: S.radius,
                background: mixFill,
                color: mixFg,
                border,
                fontSize: S.font,
                fontWeight: model ? 600 : 700,
                fontFamily: model ? `ui-monospace, Menlo, ${SANS}` : SANS,
                letterSpacing: model ? 0 : -0.4,
                whiteSpace: "nowrap",
                lineHeight: 1.1,
                opacity: Math.min(1, p * 1.3) * dim,
                transform: `translateY(${(1 - p) * 22}px) scale(${(0.84 + 0.16 * p) * sp * (1 + hotP * 0.04)})`,
                boxShadow:
                  hotP > 0
                    ? `0 14px 30px -12px ${rgba(tok.accent, 0.55 * hotP)}`
                    : cream
                    ? `0 6px 16px -10px ${rgba("#000", 0.35)}`
                    : `0 8px 20px -12px ${rgba("#000", 0.7)}`,
              }}
            >
              {toggle ? (
                <span
                  style={{
                    width: S.icon * 1.5,
                    height: S.icon * 0.85,
                    borderRadius: 999,
                    background: hotP > 0.5 ? rgba(hotFg, 0.35) : rgba(tok.mute, 0.35),
                    position: "relative",
                    flex: "none",
                  }}
                >
                  <span
                    style={{
                      position: "absolute",
                      top: 3,
                      left: 3 + (S.icon * 0.65) * hotP,
                      width: S.icon * 0.85 - 6,
                      height: S.icon * 0.85 - 6,
                      borderRadius: "50%",
                      background: hotP > 0.5 ? hotFg : "#fff",
                    }}
                  />
                </span>
              ) : c.icon === "dot" ? (
                <span
                  style={{
                    width: S.icon * 0.36,
                    height: S.icon * 0.36,
                    borderRadius: "50%",
                    background: hotP > 0.5 ? hotFg : tok.accent,
                    flex: "none",
                  }}
                />
              ) : c.icon ? (
                <span
                  style={{
                    fontSize: S.icon,
                    lineHeight: 1,
                    ...(platform
                      ? {
                          width: S.icon * 1.25,
                          height: S.icon * 1.25,
                          borderRadius: 8,
                          background: hotP > 0.5 ? rgba(hotFg, 0.22) : rgba(tok.ink, 0.08),
                          display: "inline-flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontSize: S.icon * 0.8,
                        }
                      : {}),
                  }}
                >
                  {c.icon}
                </span>
              ) : null}
              <span
                style={{
                  fontFamily: objection && strikeP > 0 ? SERIF : undefined,
                  fontStyle: objection && strikeP > 0 ? "italic" : undefined,
                }}
              >
                {c.text}
              </span>
              {strikeP > 0 ? (
                <span
                  style={{
                    position: "absolute",
                    left: S.padX * 0.7,
                    right: S.padX * 0.7,
                    top: "50%",
                    height: Math.max(3, Math.round(S.font * 0.08)),
                    background: tok.accent,
                    transformOrigin: "left center",
                    transform: `translateY(-50%) scaleX(${strikeP}) rotate(-3deg)`,
                    borderRadius: 2,
                  }}
                />
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export const chipRowDemo: ChipRowProps = {
  eyebrow: "Works with",
  chips: [
    { text: "Claude", kind: "model", icon: "dot", hot: true },
    { text: "GPT-5", kind: "model", icon: "dot" },
    { text: "Gemini", kind: "model", icon: "dot" },
    { text: "Mac", kind: "platform", icon: "💻" },
    { text: "Windows", kind: "platform", icon: "🪟" },
    { text: "Too expensive", kind: "objection", struck: true },
    { text: "Needs code", kind: "objection", struck: true },
    { text: "Auto-save", kind: "toggle", hot: true },
  ],
  align: "center",
  size: "md",
  wrap: true,
  y: 700,
  stagger: 0.24,
  theme: "cream",
  transparent: false,
};
