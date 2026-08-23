import React from "react";
import {
  AbsoluteFill,
  Easing,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BRAND, SANS, MONO, DISPLAY, rgba, clamp, Fonts, AuroraBed } from "./kit";

/* =============================================================================
   GenerativeUI — a prompt goes in, and COMPONENTS land. Not sentences.

   Plate 08 of the "Wow Mechanics" field study (artifact b9570dbc), which is
   blunt about the idea: "The model does not write you a paragraph about your
   numbers. It hands you the chart and the approve button." — tool call ->
   component, NOT tokens -> prose. The agent picks from a fixed catalogue of
   approved components; you keep the render layer. Its own summary: "Chat is
   the fallback, not the interface."

   Section C's port verdict is why this exists instead of a chat mock:
     "Ports as staging - As a fake app on screen this is ideal: components
      landing one by one on a timeline is far more watchable than a text
      response streaming."
   An earlier attempt at this beat used chat bubbles and was rejected, correctly:
   bubbles ARE prose, so they port the fallback rather than the interface.

   The shape: a MONO prompt row (the one line, with a caret that settles), an
   accent rule that DRAWS to separate ask from answer, then N items landing on a
   stagger - each a UI OBJECT, never a paragraph:
     · "spec"   — Anton title + up to 3 MONO chips (facts, not sentences)
     · "tile"   — a media tile with a caustic top edge and a MONO caption
     · "action" — a house hairline row: SANS label left, Anton accent value right
     · "stat"   — MONO label + big Anton value

   House style is obeyed to the value (GlassPanel): MONO eyebrows at 24/ls 6,
   Anton for titles and values at ls -1, SANS body, 1px hairlines at
   rgba(#fff,.12), NO pills, left-aligned. Restraint is the skill.

   Honesty: this is an ILLUSTRATIVE staging device, not evidence. It must not be
   dressed as a screenshot of a real product - it carries its own neutral chrome,
   and any episode using it should still show the real tape for the claim itself.
   ========================================================================== */

export type GenItem = {
  kind: "spec" | "tile" | "action" | "stat";
  title?: string; // spec/tile title, action label, stat label
  subtitle?: string; // spec/tile secondary line — keep it to a phrase, never prose
  chips?: string[]; // spec: up to 2 short MONO facts (3 is unreadable at feed size)
  value?: string; // action/stat right-hand value (Anton, accent)
  media?: string; // tile: image path, resolved via staticFile()
  mediaHeight?: number; // tile height in px (default 420)
};

export type GenerativeUIProps = {
  prompt: string; // the single line that was asked
  promptLabel?: string; // MONO eyebrow over the prompt (default "PROMPT")
  /* Prompt type size. Defaults by LENGTH: a real typed prompt is often a
     paragraph, not a slogan, and hardcoding 56px overflowed the card. Showing
     the REAL text matters more than showing a short one — quoting a prettier
     line than the one actually typed is a fabricated quotation. */
  promptSize?: number;
  items: GenItem[]; // what LANDS, in order
  start?: number; // seconds before the prompt appears
  promptHold?: number; // seconds the prompt holds before the first item lands
  perItem?: number; // seconds between item landings
  accent?: string;
  accent2?: string;
  ink?: string;
  transparent?: boolean;
  width?: number;
  height?: number;
};

const SETTLE = Easing.bezier(0.2, 0.9, 0.25, 1); // Plate 06

export const GenerativeUI: React.FC<GenerativeUIProps> = ({
  prompt,
  promptLabel = "PROMPT",
  promptSize,
  items,
  start = 0.15,
  promptHold = 0.75,
  perItem = 0.5,
  accent = BRAND.mag,
  accent2 = BRAND.cyan,
  ink = BRAND.ink,
  transparent,
  width = 1080,
  height = 1920,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const st = t - start;

  const PAD = 72;
  const CW = width - PAD * 2;

  const promptIn = interpolate(st, [0, 0.42], [0, 1], {
    easing: SETTLE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // the rule draws once the ask has landed — ask, then answer
  const ruleE = interpolate(st, [0.5, 0.92], [0, 1], {
    easing: SETTLE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // caret blinks while waiting, then stops when the first item lands
  const firstLand = promptHold + 0.2;
  const caretOn = st < firstLand && Math.floor(st * 2.2) % 2 === 0;

  const landAt = (i: number) => promptHold + 0.2 + i * perItem;

  return (
    <AbsoluteFill
      style={{
        background: transparent ? undefined : ink,
        fontFamily: SANS,
        overflow: "hidden",
      }}
    >
      <Fonts />
      {!transparent && <AuroraBed t={t} accent={accent} ink={ink} opacity={0.34} />}

      <div style={{ position: "absolute", left: PAD, top: 300, width: CW }}>
        {/* ── the ask ─────────────────────────────────────────────── */}
        <div
          style={{
            fontFamily: MONO,
            fontSize: 24,
            letterSpacing: 6,
            color: rgba(BRAND.paper, 0.72),
            opacity: promptIn,
          }}
        >
          {promptLabel}
        </div>
        <div
          style={{
            marginTop: 18,
            fontSize:
              promptSize ??
              (prompt.length > 150 ? 32 : prompt.length > 90 ? 40 : 56),
            lineHeight: 1.24,
            color: BRAND.paper,
            opacity: promptIn,
            transform: `translateY(${(1 - promptIn) * 14}px)`,
          }}
        >
          {prompt}
          <span
            style={{
              display: "inline-block",
              width: 4,
              height: 42,
              marginLeft: 10,
              verticalAlign: "-6px",
              background: accent,
              opacity: caretOn ? 1 : 0,
            }}
          />
        </div>

        {/* accent rule — draws to separate ask from answer */}
        <svg
          width={CW}
          height={10}
          viewBox={`0 0 ${CW} 10`}
          style={{ display: "block", marginTop: 34, overflow: "visible", opacity: ruleE > 0 ? 1 : 0 }}
        >
          <defs>
            <linearGradient id="gu-rule" gradientUnits="userSpaceOnUse" x1={0} y1={0} x2={CW} y2={0}>
              <stop offset="0%" stopColor={accent} />
              <stop offset="100%" stopColor={accent2} />
            </linearGradient>
          </defs>
          <line
            x1={2}
            y1={5}
            x2={CW - 2}
            y2={5}
            stroke="url(#gu-rule)"
            strokeWidth={4}
            strokeLinecap="round"
            strokeDasharray={CW - 4}
            strokeDashoffset={(CW - 4) * (1 - ruleE)}
          />
        </svg>

        {/* ── what lands: components, one by one ──────────────────── */}
        <div style={{ marginTop: 40 }}>
          {items.map((it, i) => {
            const d = landAt(i);
            const s = spring({
              frame: frame - Math.round((start + d) * fps),
              fps,
              config: { damping: 17, mass: 0.8, stiffness: 120 },
            });
            if (s <= 0) return null;
            const op = clamp(s * 1.4);
            const lift = (1 - s) * 22;
            // a single sheen pass as each component materialises
            const sh = clamp((st - d) / 0.7);

            const shell: React.CSSProperties = {
              position: "relative",
              opacity: op,
              transform: `translateY(${lift}px) scale(${interpolate(s, [0, 1], [0.97, 1])})`,
              marginBottom: 22,
              overflow: "hidden",
            };

            if (it.kind === "action") {
              return (
                <div
                  key={i}
                  style={{
                    ...shell,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "24px 0",
                    borderTop: `1px solid ${rgba("#ffffff", 0.12)}`,
                  }}
                >
                  <span style={{ fontSize: 38, color: rgba(BRAND.paper, 0.82) }}>{it.title}</span>
                  <span style={{ fontFamily: DISPLAY, fontSize: 44, color: accent2, letterSpacing: 0.5 }}>
                    {it.value}
                  </span>
                </div>
              );
            }

            if (it.kind === "stat") {
              return (
                <div key={i} style={shell}>
                  <div style={{ fontFamily: MONO, fontSize: 22, letterSpacing: 5, color: rgba(BRAND.paper, 0.6) }}>
                    {it.title}
                  </div>
                  <div style={{ fontFamily: DISPLAY, fontSize: 96, letterSpacing: -1, color: "#fff" }}>
                    {it.value}
                  </div>
                </div>
              );
            }

            if (it.kind === "tile") {
              const H = it.mediaHeight ?? 420;
              return (
                <div
                  key={i}
                  style={{
                    ...shell,
                    borderRadius: 28,
                    border: `1px solid ${rgba("#ffffff", 0.22)}`,
                    boxShadow: `0 34px 80px -34px ${rgba("#000", 0.85)}, inset 0 1px 0 ${rgba("#fff", 0.4)}`,
                  }}
                >
                  <div style={{ position: "relative", height: H, overflow: "hidden" }}>
                    {it.media && (
                      <Img
                        src={it.media.startsWith("http") ? it.media : staticFile(it.media)}
                        style={{ width: "100%", height: "100%", objectFit: "cover" }}
                      />
                    )}
                    <div
                      style={{
                        position: "absolute",
                        left: 0,
                        right: 0,
                        top: 0,
                        height: 3,
                        background: `linear-gradient(90deg, ${rgba("#fff", 0)} 0%, ${rgba(
                          "#fff",
                          0.6
                        )} 50%, ${rgba("#fff", 0)} 100%)`,
                      }}
                    />
                    <div
                      style={{
                        position: "absolute",
                        inset: 0,
                        background: `linear-gradient(100deg, transparent 36%, ${rgba("#fff", 0.16)} 50%, transparent 64%)`,
                        transform: `translateX(${interpolate(sh, [0, 1], [-130, 130])}%)`,
                      }}
                    />
                  </div>
                  {(it.title || it.subtitle) && (
                    <div style={{ padding: "20px 24px", background: rgba("#0a0b12", 0.5) }}>
                      {it.title && (
                        <div style={{ fontFamily: DISPLAY, fontSize: 40, letterSpacing: -0.5, color: "#fff" }}>
                          {it.title}
                        </div>
                      )}
                      {it.subtitle && (
                        <div style={{ fontFamily: MONO, fontSize: 22, letterSpacing: 4, color: rgba(BRAND.paper, 0.6), marginTop: 6 }}>
                          {it.subtitle}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            }

            // "spec" — a fact card, never a paragraph
            return (
              <div
                key={i}
                style={{
                  ...shell,
                  padding: "26px 28px",
                  borderRadius: 24,
                  background: `linear-gradient(160deg, ${rgba("#0a0b12", 0.34)}, ${rgba("#0a0b12", 0.6)})`,
                  border: `1px solid ${rgba("#ffffff", 0.14)}`,
                  boxShadow: `inset 0 1px 0 ${rgba("#fff", 0.3)}`,
                }}
              >
                {it.title && (
                  <div style={{ fontFamily: DISPLAY, fontSize: 58, letterSpacing: -0.5, color: "#fff" }}>
                    {it.title}
                  </div>
                )}
                {it.chips && it.chips.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 16 }}>
                    {it.chips.slice(0, 2).map((c, ci) => {
                      const cs = clamp((st - d - 0.12 - ci * 0.09) / 0.3);
                      return (
                        <span
                          key={ci}
                          style={{
                            fontFamily: MONO,
                            fontSize: 28,
                            letterSpacing: 3,
                            color: rgba(BRAND.paper, 0.78),
                            padding: "10px 16px",
                            borderRadius: 10,
                            border: `1px solid ${rgba("#ffffff", 0.16)}`,
                            opacity: cs,
                            transform: `translateY(${(1 - cs) * 8}px)`,
                          }}
                        >
                          {c}
                        </span>
                      );
                    })}
                  </div>
                )}
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    background: `linear-gradient(100deg, transparent 36%, ${rgba("#fff", 0.1)} 50%, transparent 64%)`,
                    transform: `translateX(${interpolate(sh, [0, 1], [-130, 130])}%)`,
                    pointerEvents: "none",
                  }}
                />
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const generativeUIDemo: GenerativeUIProps = {
  promptLabel: "ONE LINE",
  prompt: "build me a spin-the-wheel dinner picker",
  items: [
    { kind: "spec", title: "Dinner wheel", chips: ["6 OPTIONS", "SPIN BUTTON", "SINGLE FILE"] },
    {
      kind: "tile",
      media: "assets/ep_wheel/hook.png",
      title: "Ready to run",
      subtitle: "HTML · NO SETUP",
      mediaHeight: 460,
    },
    { kind: "action", title: "Open it", value: "↳" },
  ],
  promptHold: 0.8,
  perItem: 0.55,
};
