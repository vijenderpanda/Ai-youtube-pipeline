import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BRAND, SANS, MONO, DISPLAY, rgba, clamp, Fonts, AuroraBed } from "./kit";

/* =============================================================================
   ReactionMeter — WAIT -> GREEN -> a number that ARRIVES.

   Cookbook role: the "measurement" form, and the library's first true Plate 09
   block. SpinWheel surrenders a decision to chance; Odometer settles a value
   that was already there; this one MEASURES something live and reports it. The
   payoff is a single number, so the whole component exists to make that number
   land hard.

   Straight from the wow-mechanics artifact:
     · Plate 09 "numbers that arrive" — the artifact calls this "the single
       highest-value block for a data-driven short". The ring draws via
       stroke-dasharray -> dashoffset 0; the digits are never simply present.
     · Plate 03 kinetic type — per-glyph 26ms stagger, rotateX(-82deg) -> 0,
       scaleX 1.7 -> 1. The digits rotate up into place rather than fading.
     · Plate 06 settle — cubic-bezier(.2,.9,.25,1) on the state changes.
     · Plate 01 glass — the readout sits on the frosted panel with the inset
       highlight ("the trick is the inset highlight, not the blur").

   Why it exists (2026-08-20): the channel's builds win distribution but bleed
   retention (39.8% AVP on tip #2 vs a 50.9% tip median), and two builds in a
   row drew ZERO comments on 218 views. A reaction test fixes both in one shape —
   the viewer waits for a number (retention) and immediately has their own to
   report (comments). The `avgMs` marker is what turns a readout into a
   challenge: a bar you can be on either side of.

   The four phases, timed off `start` (seconds, absolute):
     P0  ARMED  — the panel breathes on a hold colour, "WAIT FOR GREEN".
     P1  GREEN  — a hard, instant snap to green. No easing IN; the whole point
                  is that it is a startle. This is the frame the viewer reacts to.
     P2  ARRIVE — green clears, the ring draws, digits rotate up one by one.
     P3  HOLD   — the landed readout with the average marker, so any still near
                  the end is a finished, readable frame.

   Honesty: `ms` is authored by the episode to the value the REAL tape lands on,
   the same convention SpinWheel uses for its winner. This is a stylized
   restatement of what the recording then proves, never a fabricated result.

   JSON-safe: numbers and strings only; no function props (build_ep_v2 feeds
   --props as JSON).
   ========================================================================== */

export type ReactionMeterProps = {
  ms: number; // the reaction time to report — mirror the real tape
  avgMs?: number; // the "average human" marker that makes it a challenge (default 250)
  avgLabel?: string; // marker caption (default "AVERAGE HUMAN")
  /* The right-hand slot. It deliberately does NOT render a FASTER/SLOWER verdict:
     grading my own score is a judgment nobody asked for, and on a slow take it
     undercuts the flex. Asking instead is what closes the measured gap — two
     builds in a row drew ZERO comments because the CTA was not answerable. */
  challenge?: string; // default "CAN YOU BEAT IT?"
  scaleMs?: number; // full-scale for the ring/bar (default 500)
  title?: string; // headline over the panel
  kicker?: string; // tiny uppercase label over the title
  waitLabel?: string; // P0 copy (default "WAIT FOR GREEN")
  goLabel?: string; // P1 copy (default "TAP!")
  unitLabel?: string; // under the digits (default "MILLISECONDS")
  readoutLabel?: string; // over the digits (default "YOUR REACTION TIME")
  start?: number; // seconds before the ARMED phase begins (default 0.05)
  waitDur?: number; // seconds held on WAIT (default 1.15)
  greenDur?: number; // seconds the green startle holds (default 0.5)
  accent?: string; // digits + ring (brand magenta)
  green?: string; // the GO colour
  ink?: string; // backdrop fill
  transparent?: boolean; // skip the backdrop (overlay use)
  /* The episode's burned claim, carried BY this component instead of by a static
     hook image — same contract as SpinWheel. It rides over the motion so the
     opening has message AND movement at once, then clears. */
  claimLines?: string[]; // up to 2 lines, set in Anton
  claimHot?: string; // the one word that takes the accent
  claimHold?: number; // seconds fully visible before it fades (default 2.2)
  /* Seconds before ANY overlay text appears. A short hook `until` means the hook
     card is still cross-dissolving over this component; drawing text during that
     window ghosts two offset copies of the same words. The PANEL still animates
     from frame 0, so the opening is motion either way. */
  contentStart?: number;
  width?: number;
  height?: number;
};

const easeSettle = (x: number) => {
  // cubic-bezier(.2,.9,.25,1) closely enough for a scalar clock (Plate 06)
  const c = clamp(x);
  return 1 - Math.pow(1 - c, 3.2);
};

export const ReactionMeter: React.FC<ReactionMeterProps> = ({
  ms,
  avgMs = 250,
  avgLabel = "AVERAGE HUMAN",
  challenge = "CAN YOU BEAT IT?",
  scaleMs = 500,
  title,
  kicker,
  waitLabel = "WAIT FOR GREEN",
  goLabel = "TAP!",
  unitLabel = "MILLISECONDS",
  readoutLabel = "YOUR REACTION TIME",
  start = 0.05,
  waitDur = 1.15,
  greenDur = 0.5,
  accent = BRAND.mag,
  green = "#22C55E",
  ink = BRAND.ink,
  transparent,
  claimLines,
  claimHot,
  claimHold = 2.2,
  contentStart = 0,
  width = 1080,
  height = 1920,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  /* ---- phase clocks ---- */
  const tGreen = start + waitDur; // the startle
  const tArrive = tGreen + greenDur; // the number
  const inWait = t >= start && t < tGreen;
  const inGreen = t >= tGreen && t < tArrive;
  const arrived = t >= tArrive;
  const at = arrived ? t - tArrive : 0; // clock since the number began arriving

  /* ---- panel geometry: square-ish, clear of the bottom ~21% caption band ---- */
  const PW = width * 0.82;
  const PH = height * 0.42;
  const PX = (width - PW) / 2;
  const PY = height * 0.285;

  /* ---- the panel breathes for the WHOLE beat, not just the wait ----
     A landed readout that sits perfectly still is the still-hold pattern that
     cost tip #2 its retention (measured 0:15-0:25 drop-off on two frozen
     holds). The breathe continues after the number arrives, at a much smaller
     amplitude, so the frame is never actually static. */
  const breathe = Math.sin((t - start) * 3.4) * 0.5 + 0.5;
  const breatheAmp = inWait ? 0.006 : arrived ? 0.0025 : 0;

  /* ---- P1: the green snap. Instant IN (a startle cannot ease in), soft OUT. */
  const greenOn = inGreen ? 1 : 0;
  const greenFade = arrived ? clamp(1 - at / 0.22) : greenOn;

  /* ---- P2: Plate 09 — the ring draws, then the digits rotate up ---- */
  const RING_R = PW * 0.34;   // wide enough that the 3-digit readout never crosses the stroke
  const RING_C = 2 * Math.PI * RING_R;
  const ringP = arrived ? easeSettle((at - 0.06) / 0.72) : 0;
  const frac = clamp(ms / Math.max(scaleMs, 1));

  const digits = String(Math.round(ms)).split("");
  // digits count UP to the real value while the ring draws, then lock. The number
  // is never simply present — it arrives.
  const counting = arrived && at < 0.66;
  const shown = counting
    ? String(Math.max(Math.round(ms * easeSettle(at / 0.66)), 0)).padStart(digits.length, "0")
    : String(Math.round(ms));

  const readoutIn = arrived ? clamp((at - 0.04) / 0.3) : 0;
  const markerIn = arrived ? clamp((at - 0.86) / 0.4) : 0;

  const verdictSpring = arrived
    ? spring({
        frame: frame - Math.round((tArrive + 1.05) * fps),
        fps,
        config: { damping: 14, stiffness: 170 },
      })
    : 0;

  const glassBg = `linear-gradient(160deg, ${rgba("#0a0b12", 0.34)}, ${rgba("#0a0b12", 0.5)})`;

  return (
    <AbsoluteFill style={{ background: transparent ? undefined : ink, fontFamily: SANS }}>
      <Fonts />
      {!transparent && <AuroraBed t={t} accent={accent} ink={ink} opacity={0.32} />}

      {/* the green startle washes the WHOLE frame — that is what makes it a cue */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at 50% 42%, ${rgba(green, 0.42)} 0%, transparent 66%)`,
          opacity: greenFade,
        }}
      />

      {/* headline */}
      <div
        style={{
          position: "absolute",
          top: height * 0.178,
          width,
          textAlign: "center",
          padding: "0 70px",
          opacity: clamp((t - contentStart) / 0.22) * (1 - greenFade * 0.7),
        }}
      >
        {kicker && (
          <div
            style={{
              fontFamily: MONO,
              fontSize: 24,
              letterSpacing: 6,
              color: rgba(BRAND.paper, 0.72),
              marginBottom: 16,
              textTransform: "uppercase",
            }}
          >
            {kicker}
          </div>
        )}
        {title && (
          <div
            style={{
              fontFamily: DISPLAY,
              fontSize: 82,
              letterSpacing: -1,
              color: "#fff",
              lineHeight: 1.04,
            }}
          >
            {title}
          </div>
        )}
      </div>

      {/* ---- the panel (Plate 01: baked refraction + inset hairline) ---- */}
      <div
        style={{
          position: "absolute",
          left: PX,
          top: PY,
          width: PW,
          height: PH,
          borderRadius: 44,
          background: inGreen
            ? `linear-gradient(160deg, ${rgba(green, 0.9)}, ${rgba(green, 0.72)})`
            : glassBg,
          backdropFilter: "blur(26px) saturate(200%) brightness(1.08)",
          WebkitBackdropFilter: "blur(26px) saturate(200%) brightness(1.08)",
          boxShadow: [
            `inset 0 1px 0 ${rgba("#ffffff", 0.55)}`,
            `inset 0 0 0 1px ${rgba("#ffffff", 0.1)}`,
            `0 40px 90px ${rgba("#000000", 0.55)}`,
            inGreen ? `0 0 120px ${rgba(green, 0.5)}` : `0 0 0 ${rgba("#000", 0)}`,
          ].join(", "),
          overflow: "hidden",
          transform: `scale(${1 + breathe * breatheAmp + (inGreen ? 0.014 : 0)})`,
          transition: "none",
        }}
      >
        {/* caustic top edge — the 3px bright lip that sells the material */}
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: 0,
            height: 3,
            background: `linear-gradient(90deg, transparent, ${rgba("#ffffff", 0.7)}, transparent)`,
          }}
        />

        {/* Specular sweep — the landed state stays ALIVE without adding noise.
            Same sheen language as the glass plate, on a slow repeat. */}
        {arrived && at > 0.9 && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              pointerEvents: "none",
              background: `linear-gradient(105deg, transparent 36%, ${rgba(
                "#ffffff",
                0.1
              )} 50%, transparent 64%)`,
              transform: `translateX(${(((at - 0.9) % 3.1) / 3.1) * 250 - 125}%)`,
            }}
          />
        )}

        {/* P0 — WAIT */}
        {inWait && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 28,
              opacity: clamp((t - contentStart) / 0.2),
            }}
          >
            <div
              style={{
                width: 132,
                height: 132,
                borderRadius: "50%",
                border: `6px solid ${rgba(BRAND.paper, 0.2 + breathe * 0.3)}`,
                boxShadow: `0 0 ${30 + breathe * 40}px ${rgba(BRAND.paper, 0.1 + breathe * 0.14)}`,
              }}
            />
            <div
              style={{
                fontFamily: MONO,
                fontSize: 30,
                letterSpacing: 8,
                color: rgba(BRAND.paper, 0.6 + breathe * 0.3),
              }}
            >
              {waitLabel}
            </div>
          </div>
        )}

        {/* P1 — GREEN */}
        {inGreen && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                fontFamily: DISPLAY,
                fontSize: 220,
                letterSpacing: -2,
                color: "#06210F",
                textShadow: `0 6px 40px ${rgba("#ffffff", 0.35)}`,
              }}
            >
              {goLabel}
            </div>
          </div>
        )}

        {/* P2/P3 — the number arrives */}
        {arrived && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {/* Plate 09: the ring is DRAWN, never revealed */}
            <svg
              width={PW}
              height={PH}
              viewBox={`0 0 ${PW} ${PH}`}
              style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}
            >
              <circle
                cx={PW / 2}
                cy={PH / 2}
                r={RING_R}
                fill="none"
                stroke={rgba("#ffffff", 0.1)}
                strokeWidth={10}
              />
              <circle
                cx={PW / 2}
                cy={PH / 2}
                r={RING_R}
                fill="none"
                stroke={accent}
                strokeWidth={10}
                strokeLinecap="round"
                strokeDasharray={RING_C}
                strokeDashoffset={RING_C * (1 - frac * ringP)}
                transform={`rotate(-90 ${PW / 2} ${PH / 2})`}
              />
            </svg>

            <div
              style={{
                fontFamily: MONO,
                fontSize: 26,
                letterSpacing: 7,
                color: rgba(BRAND.paper, 0.72),
                opacity: readoutIn,
                marginBottom: 10,
              }}
            >
              {readoutLabel}
            </div>

            {/* Plate 03 kinetic type — 26ms stagger, rotateX(-82deg) -> 0 */}
            <div style={{ display: "flex", perspective: 900 }}>
              {shown.split("").map((d, i) => {
                const gi = clamp((at - 0.04 - i * 0.026) / 0.34);
                return (
                  <span
                    key={i}
                    style={{
                      fontFamily: DISPLAY,
                      fontSize: 240,
                      lineHeight: 1,
                      letterSpacing: -2,
                      color: "#fff",
                      display: "inline-block",
                      transformOrigin: "50% 100%",
                      transform: `rotateX(${-82 * (1 - easeSettle(gi))}deg) scaleX(${
                        1 + 0.7 * (1 - easeSettle(gi))
                      })`,
                      opacity: gi > 0 ? 1 : 0,
                      textShadow: `0 10px 40px ${rgba("#000", 0.6)}`,
                    }}
                  >
                    {d}
                  </span>
                );
              })}
            </div>

            <div
              style={{
                fontFamily: MONO,
                fontSize: 28,
                letterSpacing: 8,
                color: rgba(BRAND.paper, 0.8),
                opacity: readoutIn,
                marginTop: 6,
              }}
            >
              {unitLabel}
            </div>
          </div>
        )}
      </div>

      {/* ---- the average marker: what turns a readout into a challenge ---- */}
      {arrived && (
        <div
          style={{
            position: "absolute",
            left: PX,
            top: PY + PH + 54,
            width: PW,
            opacity: markerIn,
          }}
        >
          <div
            style={{
              position: "relative",
              height: 14,
              borderRadius: 7,
              background: rgba("#ffffff", 0.1),
              overflow: "visible",
            }}
          >
            <div
              style={{
                position: "absolute",
                left: 0,
                top: 0,
                bottom: 0,
                width: `${frac * 100 * markerIn}%`,
                borderRadius: 7,
                background: `linear-gradient(90deg, ${accent}, ${rgba(accent, 0.6)})`,
              }}
            />
            {/* the marker itself — a hairline, not a pill */}
            <div
              style={{
                position: "absolute",
                left: `${clamp(avgMs / Math.max(scaleMs, 1)) * 100}%`,
                top: -14,
                bottom: -14,
                width: 2,
                background: rgba(BRAND.paper, 0.55),
              }}
            />
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginTop: 22,
              paddingTop: 20,
              borderTop: `1px solid ${rgba("#ffffff", 0.12)}`,
            }}
          >
            <span style={{ fontFamily: MONO, fontSize: 24, letterSpacing: 5, color: rgba(BRAND.paper, 0.62) }}>
              {avgLabel} {avgMs}
            </span>
            <span
              style={{
                fontFamily: DISPLAY,
                fontSize: 40,
                letterSpacing: 0.5,
                color: accent,
                opacity: verdictSpring,
                transform: `translateY(${(1 - verdictSpring) * 16}px)`,
              }}
            >
              {challenge}
            </span>
          </div>
        </div>
      )}

      {/* the burned claim — rides over the motion, then clears */}
      {claimLines && claimLines.length > 0 && (
        <div
          style={{
            position: "absolute",
            left: 64,
            right: 64,
            top: 96,
            opacity:
              interpolate(
                t,
                [contentStart, contentStart + 0.18, contentStart + claimHold, contentStart + claimHold + 0.45],
                [0, 1, 1, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ) * (1 - greenFade * 0.55),
          }}
        >
          {claimLines.slice(0, 2).map((ln, li) => (
            <div
              key={li}
              style={{
                fontFamily: DISPLAY,
                fontSize: 104,
                lineHeight: 1.02,
                letterSpacing: -1,
                color: "#fff",
                textShadow: `0 8px 30px ${rgba("#000", 0.75)}`,
              }}
            >
              {ln.split(" ").map((wd, wi) => (
                <span
                  key={wi}
                  style={{
                    color: claimHot && wd.toUpperCase() === claimHot.toUpperCase() ? accent : undefined,
                  }}
                >
                  {wd}{" "}
                </span>
              ))}
            </div>
          ))}
        </div>
      )}
    </AbsoluteFill>
  );
};

export const reactionMeterDemo: ReactionMeterProps = {
  kicker: "One line built this",
  title: "How fast are you?",
  ms: 284,
  avgMs: 250,
  start: 0.35,
  waitDur: 1.15,
  greenDur: 0.5,
};
