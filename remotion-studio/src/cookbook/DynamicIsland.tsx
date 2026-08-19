import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BRAND, SANS, rgba, clamp, coverBg, Fonts } from "./kit";

/* =============================================================================
   DynamicIsland — an iOS "Dynamic Island" pill that morphs from an idle nub into
   a running LIVE ACTIVITY, drives an AI task through its phases, and snaps to a
   satisfying DONE.
   Cookbook role: the invented DEVICE-UI wow — a sibling to NotificationStack's
   frosted lock-screen. Where NotificationStack is the "results ACCRUE" form, this
   is the "one task, watched to completion" form: a beat that says *the assistant
   is on it right now* — reading, drafting, polishing — and then *it's done*.

   WHY THIS LAYOUT
   - The Dynamic Island is one of the most-recognized micro-UIs on earth. A black
     pill fluidly ballooning into a live card is a gesture the eye reads as "a
     process just started, live" with zero labels — that instant grok is what
     buys the 15s hold. We lean on the recognition instead of explaining it.
   - The morph IS the wow. A spring grows the pill wider + taller while the corner
     radius eases and the compact glyphs cross-dissolve into a full card revealed
     from the center outward (the box clips its own content as it opens). It's the
     rubbery, physical "liquid" feel of the real thing, invented in pure CSS/SVG.
   - The phases carry the message. A leading glyph tile spins a "thinking" ring,
     the title cross-fades up through each step, a slim progress bar fills across
     the phases with a ticking %, and on completion the whole thing POPS: the tile
     morphs into a drawn checkmark, the title becomes doneTitle, a result line
     (doneNote) lands, and an accent bloom flares. It LANDS holding that done card,
     so a still near the end reads unmistakably as "finished".

   9:16 SAFE: the island is centered in the top third and anchored by its TOP so it
   only ever grows DOWNWARD — the expanded card bottoms out near y=560, miles above
   the y=1517 caption band. The expanded box is 820px wide (>=130px off both edges,
   even at the spring's overshoot peak). Title/sub/eyebrow are single-line ellipsised
   and the step list is capped, so no string can overflow. JSON-safe throughout: no
   function props — phases are plain {title,status} strings, timing is numbers.
   ========================================================================== */

export type DynamicIslandProps = {
  /** compact-pill label / the assistant's name shown as the activity source. */
  idleLabel?: string;
  /** the work phases, in order; the title advances through them as it fills. */
  steps: {
    title: string; // phase headline (single line — ellipsised if long)
    status?: string; // optional right/sub detail (defaults to "Step i of n")
  }[];
  /** headline shown when the task completes (default "Done"). */
  doneTitle?: string;
  /** result line under the done headline, e.g. "3 subject lines included". */
  doneNote?: string;
  /** seconds each phase holds before the next (progress fills across all). */
  perStep?: number; // default 1.1
  /** seconds the compact pill idles before it morphs open. */
  idle?: number; // default 0.9
  accent?: string; // brand accent (defaults to Sol magenta)
  ink?: string; // base fill
  start?: number; // seconds before the pill pops in
  width?: number;
  height?: number;
  transparent?: boolean; // skip the backdrop (overlay use inside a composition)
};

/* ---- geometry: compact nub → expanded card (the morph endpoints) ---------- */
const COMPACT_W = 380;
const COMPACT_H = 96;
const COMPACT_R = 48;
const EXPAND_W = 820;
const EXPAND_H = 300;
const EXPAND_R = 62;
const PAD = 40; // card padding
const TILE = 132; // glyph-tile side

export const DynamicIsland: React.FC<DynamicIslandProps> = ({
  idleLabel = "Sol",
  steps,
  doneTitle = "Done",
  doneNote,
  perStep = 1.1,
  idle = 0.9,
  accent = BRAND.mag,
  ink = BRAND.ink,
  start = 0.3,
  width = 1080,
  height = 1920,
  transparent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const S = steps.slice(0, 6);
  const n = Math.max(S.length, 1);
  const step = perStep > 0 ? perStep : 1.1;

  // ── timeline (all in seconds from `start`) ───────────────────────────────
  const t = frame / fps - start;
  const stepsDur = n * step;
  const tDone = idle + stepsDur; // moment the task completes
  const done = t >= tDone;

  // fractional fill across every phase (0 at expand, 1 at done, held after)
  const fill = clamp((t - idle) / stepsDur);
  const pct = Math.round(fill * 100);

  // active slide: 0..n-1 while working, `n` = the done slide
  const si = done ? n : clamp(Math.floor((t - idle) / step), 0, n - 1);
  const slideStart = (i: number) => idle + i * step; // (i=n → tDone)

  // ── the fluid morph spring (idle nub → open card) ────────────────────────
  const mp = spring({
    frame: frame - (start + idle) * fps,
    fps,
    config: { damping: 14, mass: 0.85, stiffness: 120 },
  });
  const mpC = clamp(mp);

  // a light overshoot on w/h gives the rubbery "liquid" bounce; radius eases clean
  const w = Math.min(COMPACT_W + (EXPAND_W - COMPACT_W) * mp, EXPAND_W * 1.02);
  const h = Math.min(COMPACT_H + (EXPAND_H - COMPACT_H) * mp, EXPAND_H * 1.02);
  const r = COMPACT_R + (EXPAND_R - COMPACT_R) * mpC;

  const compactFade = clamp(1 - mp * 2.4); // compact glyphs gone by ~40% open
  const expandFade = clamp((mp - 0.4) / 0.5); // card content in from 40→90% open

  // ── entrance pop + completion pop ────────────────────────────────────────
  const introP = spring({
    frame: frame - start * fps,
    fps,
    config: { damping: 16, mass: 0.7, stiffness: 140 },
  });
  const introScale = interpolate(clamp(introP), [0, 1], [0.72, 1]);

  const dp = spring({
    frame: frame - (start + tDone) * fps,
    fps,
    config: { damping: 12, mass: 0.8, stiffness: 150 },
  });
  const dpC = clamp(dp);

  // a brief scale kick the instant it finishes (rise-then-settle)
  const sinceDone = t - tDone;
  const popup =
    sinceDone < 0
      ? 0
      : interpolate(sinceDone, [0, 0.12, 0.34], [0, 1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
  const S_scale = introScale * (1 + popup * 0.04);

  const topY = Math.round(height * 0.13);

  // one-line ellipsis helper
  const oneLine: React.CSSProperties = {
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  };

  const slideTitle = (i: number) => (i >= n ? doneTitle : S[i]?.title ?? "");
  const slideSub = (i: number) =>
    i >= n ? doneNote || "" : S[i]?.status || `Step ${i + 1} of ${n}`;

  // vertical cross-fade between the outgoing (si-1) and incoming (si) slide
  const trDur = Math.min(0.26, step * 0.4);
  const tr = clamp((t - slideStart(si)) / (trDur > 0 ? trDur : 0.26));

  const renderSlide = (i: number, opacity: number, ty: number) => {
    if (i < 0 || opacity <= 0.001) return null;
    const isDone = i >= n;
    return (
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 0,
          opacity,
          transform: `translateY(${ty}px)`,
        }}
      >
        <div
          style={{
            fontSize: 42,
            fontWeight: 800,
            letterSpacing: 0.2,
            color: BRAND.paper,
            lineHeight: 1.02,
            ...oneLine,
          }}
        >
          {slideTitle(i)}
        </div>
        <div
          style={{
            marginTop: 12,
            fontSize: 29,
            fontWeight: 600,
            letterSpacing: 0.4,
            color: isDone ? rgba(accent, 0.95) : rgba(BRAND.paper, 0.56),
            ...oneLine,
          }}
        >
          {slideSub(i)}
        </div>
      </div>
    );
  };

  // ── glyph tile: spinning "thinking" ring → drawn checkmark on done ───────
  const spin = (frame / fps) * 300; // deg — indeterminate activity spin
  const checkScale = interpolate(dpC, [0, 1], [0.4, 1]);
  const CHK_LEN = 100; // normalized pathLength for the draw-in

  return (
    <AbsoluteFill
      style={{
        background: transparent ? undefined : coverBg(accent, ink),
        fontFamily: SANS,
        overflow: "hidden",
      }}
    >
      <Fonts />

      {/* island — anchored by its TOP center so it only grows downward */}
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: topY,
          transform: `translateX(-50%) scale(${S_scale})`,
          transformOrigin: "50% 0%",
          opacity: clamp(introP),
        }}
      >
        {/* accent bloom behind the island (blooms outward, intensifies on done) */}
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: -70,
            width: 920,
            height: 520,
            marginLeft: -460,
            background: `radial-gradient(circle at 50% 42%, ${rgba(
              accent,
              0.5
            )} 0%, ${rgba(accent, 0)} 66%)`,
            filter: "blur(58px)",
            opacity: 0.28 + expandFade * 0.4 + dpC * 0.5,
            zIndex: 0,
          }}
        />

        {/* the morphing black-frosted box (clips its own content as it opens) */}
        <div
          style={{
            position: "relative",
            width: w,
            height: h,
            borderRadius: r,
            overflow: "hidden",
            background: `linear-gradient(180deg, ${rgba("#15151c", 0.86)} 0%, ${rgba(
              "#08080c",
              0.9
            )} 100%)`,
            backdropFilter: "blur(26px)",
            WebkitBackdropFilter: "blur(26px)",
            border: `1px solid ${rgba(accent, 0.12 + mpC * 0.16 + dpC * 0.26)}`,
            boxShadow: `0 40px 90px ${rgba("#000000", 0.55)}, 0 0 ${
              40 + mpC * 40 + dpC * 70
            }px ${rgba(accent, 0.16 + mpC * 0.12 + dpC * 0.5)}, inset 0 1px 0 ${rgba(
              "#ffffff",
              0.12
            )}`,
            zIndex: 1,
          }}
        >
          {/* inner accent wash (top-left, near the tile) for the frosted glow */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              background: `radial-gradient(62% 130% at 14% 26%, ${rgba(
                accent,
                0.16
              )} 0%, ${rgba(accent, 0)} 60%)`,
              opacity: expandFade,
            }}
          />

          {/* ── COMPACT content: dot + label + a live "listening" pulse ───── */}
          <div
            style={{
              position: "absolute",
              left: "50%",
              top: 0,
              width: COMPACT_W,
              height: COMPACT_H,
              marginLeft: -COMPACT_W / 2,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "0 38px",
              boxSizing: "border-box",
              opacity: compactFade,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
              <span
                style={{
                  width: 20,
                  height: 20,
                  borderRadius: 999,
                  background: accent,
                  boxShadow: `0 0 18px ${rgba(accent, 0.9)}`,
                  transform: `scale(${1 + Math.sin((frame / fps) * 7) * 0.14})`,
                }}
              />
              <span
                style={{ fontSize: 36, fontWeight: 700, color: BRAND.paper, ...oneLine }}
              >
                {idleLabel}
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
              {[0, 1, 2].map((i) => {
                const a = 0.35 + (Math.sin((frame / fps) * 7 - i * 0.8) * 0.5 + 0.5) * 0.65;
                return (
                  <span
                    key={i}
                    style={{
                      width: 12,
                      height: 12,
                      borderRadius: 999,
                      background: accent,
                      opacity: a,
                      transform: `scale(${0.7 + a * 0.4})`,
                    }}
                  />
                );
              })}
            </div>
          </div>

          {/* ── EXPANDED content: revealed from center as the box opens ───── */}
          <div
            style={{
              position: "absolute",
              left: "50%",
              top: 0,
              width: EXPAND_W,
              height: EXPAND_H,
              marginLeft: -EXPAND_W / 2,
              opacity: expandFade,
            }}
          >
            {/* leading glyph tile */}
            <div
              style={{
                position: "absolute",
                left: PAD,
                top: PAD,
                width: TILE,
                height: TILE,
                borderRadius: 34,
                background: `linear-gradient(150deg, ${rgba(accent, 0.2)} 0%, ${rgba(
                  accent,
                  0.05
                )} 100%), ${rgba("#0b0b12", 0.7)}`,
                boxShadow: `inset 0 1px 0 ${rgba("#ffffff", 0.16)}, 0 10px 28px ${rgba(
                  "#000000",
                  0.4
                )}`,
                overflow: "hidden",
              }}
            >
              {/* accent-fill flush-in on done */}
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  background: `linear-gradient(150deg, #FF6EC7 0%, ${accent} 100%)`,
                  opacity: dpC,
                }}
              />
              {/* completion ripple */}
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  borderRadius: 34,
                  border: `3px solid ${accent}`,
                  opacity: (1 - dpC) * dpC * 2.2,
                  transform: `scale(${1 + dpC * 0.5})`,
                }}
              />
              <svg
                width={TILE}
                height={TILE}
                viewBox="0 0 132 132"
                style={{ position: "absolute", inset: 0 }}
              >
                {/* WORKING: faint track + a spinning arc + a sparkle glyph */}
                <g opacity={1 - dpC}>
                  <circle
                    cx={66}
                    cy={66}
                    r={47}
                    fill="none"
                    stroke={rgba(accent, 0.16)}
                    strokeWidth={6}
                  />
                  <circle
                    cx={66}
                    cy={66}
                    r={47}
                    fill="none"
                    stroke={accent}
                    strokeWidth={6}
                    strokeLinecap="round"
                    strokeDasharray="74 220"
                    transform={`rotate(${spin} 66 66)`}
                    style={{ filter: `drop-shadow(0 0 8px ${rgba(accent, 0.7)})` }}
                  />
                  <path
                    d="M66 32 C68.5 54 78 63.5 100 66 C78 68.5 68.5 78 66 100 C63.5 78 54 68.5 32 66 C54 63.5 63.5 54 66 32 Z"
                    fill={accent}
                    opacity={0.92}
                  />
                </g>
                {/* DONE: a checkmark that draws + pops in */}
                <g
                  opacity={dpC}
                  style={{ transformOrigin: "66px 66px" } as React.CSSProperties}
                  transform={`translate(66 66) scale(${checkScale}) translate(-66 -66)`}
                >
                  <path
                    d="M44 68 L60 84 L90 48"
                    fill="none"
                    stroke="#ffffff"
                    strokeWidth={11}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    pathLength={CHK_LEN}
                    strokeDasharray={CHK_LEN}
                    strokeDashoffset={CHK_LEN * (1 - dpC)}
                  />
                </g>
              </svg>
            </div>

            {/* eyebrow: source + LIVE/DONE tag (static; identity of the activity) */}
            <div
              style={{
                position: "absolute",
                left: PAD + TILE + 30,
                top: PAD + 2,
                width: 438,
                display: "flex",
                alignItems: "center",
                gap: 12,
              }}
            >
              <span
                style={{
                  width: 13,
                  height: 13,
                  borderRadius: 999,
                  background: accent,
                  opacity: done ? 1 : 0.55 + Math.sin((frame / fps) * 6) * 0.35 + 0.1,
                  boxShadow: `0 0 12px ${rgba(accent, 0.8)}`,
                }}
              />
              <span
                style={{
                  fontSize: 25,
                  fontWeight: 700,
                  letterSpacing: 3,
                  textTransform: "uppercase",
                  color: rgba(BRAND.paper, 0.62),
                  ...oneLine,
                }}
              >
                {idleLabel} · {done ? "Done" : "Live"}
              </span>
            </div>

            {/* title + sub — cross-fades up through the phases */}
            <div
              style={{
                position: "absolute",
                left: PAD + TILE + 30,
                top: PAD + 44,
                width: 438,
                height: 116,
              }}
            >
              {renderSlide(si - 1, 1 - tr, -20 * tr)}
              {renderSlide(si, tr, 20 * (1 - tr))}
            </div>

            {/* right status: ticking % while working, fades as the check lands */}
            <div
              style={{
                position: "absolute",
                right: PAD,
                top: PAD + 6,
                width: 130,
                textAlign: "right",
                fontSize: 40,
                fontWeight: 800,
                fontVariantNumeric: "tabular-nums",
                letterSpacing: -1,
                color: accent,
                opacity: (1 - dpC) * clamp(expandFade * 1.4),
                textShadow: `0 0 18px ${rgba(accent, 0.5)}`,
              }}
            >
              {pct}%
            </div>

            {/* slim progress bar — fills across the phases, glows full on done */}
            <div
              style={{
                position: "absolute",
                left: PAD,
                right: PAD,
                bottom: PAD,
                height: 16,
                borderRadius: 999,
                background: rgba("#ffffff", 0.09),
                border: `1px solid ${rgba("#ffffff", 0.08)}`,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  position: "absolute",
                  left: 0,
                  top: 0,
                  bottom: 0,
                  width: `${Math.max(fill * 100, 2)}%`,
                  borderRadius: 999,
                  background: `linear-gradient(90deg, ${rgba(accent, 0.85)} 0%, ${
                    accent
                  } 78%, #FF6EC7 100%)`,
                  boxShadow: `0 0 ${14 + dpC * 26}px ${rgba(
                    accent,
                    0.5 + dpC * 0.4
                  )}, inset 0 1px 0 ${rgba("#ffffff", 0.4)}`,
                }}
              />
              {/* leading spark cap while filling */}
              {!done && fill > 0.02 && fill < 0.995 ? (
                <div
                  style={{
                    position: "absolute",
                    top: -3,
                    bottom: -3,
                    left: `calc(${fill * 100}% - 5px)`,
                    width: 10,
                    borderRadius: 999,
                    background: "#ffffff",
                    boxShadow: `0 0 16px ${rgba("#ffffff", 0.9)}, 0 0 30px ${rgba(
                      accent,
                      0.9
                    )}`,
                  }}
                />
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const dynamicIslandDemo: DynamicIslandProps = {
  idleLabel: "Sol",
  steps: [
    { title: "Reading your notes" },
    { title: "Drafting" },
    { title: "Polishing" },
  ],
  doneTitle: "Draft ready",
  doneNote: "3 subject lines included",
  perStep: 1.1,
  idle: 0.9,
};
