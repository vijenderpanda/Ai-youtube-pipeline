import React from "react";
import {
  AbsoluteFill,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BRAND, SANS, MONO, rgba, clamp, coverBg, Fonts } from "./kit";

/* =============================================================================
   MorphField — ONE object with three states instead of three objects appearing
   and disappearing: a call-to-action button that widens into an input field,
   accepts a typed value, then collapses into a confirmed pill with a drawn
   checkmark. The single-element morph the web loves, ported to a frame clock.
   Cookbook role: interaction / CTA. The clean way to show "type X → you're in"
   — a signup, a capture, a one-field ask — without three hard cuts.

   THE PORT
   - Web version morphs on click/blur. Here the three states are keyed to time:
     idle → (spring) widen+square → type the value char-by-char → (brief) send →
     (spring) collapse+turn accent-success, checkmark strokes in. It LANDS holding
     the confirmed pill.
   - The width + corner-radius are the morph — one box the whole way through, so
     the eye tracks a single object changing rather than a cut. Validation reads
     as the field turning "ready" the instant the value looks complete.

   9:16 SAFE: centered at (540, 900), max width 780 (≥150px margins); the caption
   band at y=1517 is far below. Value/labels are single-line. JSON-safe.
   ========================================================================== */

export type MorphFieldProps = {
  /** the button label in the idle state, e.g. "Join the list". */
  cta?: string;
  /** placeholder shown before typing, e.g. "you@studio.com". */
  placeholder?: string;
  /** the value that types itself in. */
  value?: string;
  /** the send-button label inside the field. */
  sendLabel?: string;
  /** the confirmed-state label, e.g. "You're in". */
  doneLabel?: string;
  /** seconds the button idles before it opens. */
  idle?: number; // default 0.8
  /** seconds spent typing the value. */
  typeFor?: number; // default 1.1
  /** seconds the field holds full before it sends. */
  holdFor?: number; // default 0.5
  accent?: string; // brand accent (defaults to Sol magenta)
  ink?: string; // base fill
  start?: number;
  width?: number;
  height?: number;
  transparent?: boolean;
};

const CX = 540;
const CY = 900;
const H = 128;
const OK = "#37E0B0";

export const MorphField: React.FC<MorphFieldProps> = ({
  cta = "Join the list",
  placeholder = "you@studio.com",
  value = "vj@studio.com",
  sendLabel = "Send",
  doneLabel = "You're in",
  idle = 0.8,
  typeFor = 1.1,
  holdFor = 0.5,
  accent = BRAND.mag,
  ink = BRAND.ink,
  start = 0.3,
  width = 1080,
  height = 1920,
  transparent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - start;

  // ── phase timeline ───────────────────────────────────────────────────────
  const tOpen = idle;
  const tTyped = tOpen + typeFor;
  const tSend = tTyped + holdFor;
  const done = t >= tSend;

  // widen/square spring (button → field)
  const open = clamp(
    spring({
      frame: frame - (start + tOpen) * fps,
      fps,
      config: { damping: 15, mass: 0.8, stiffness: 120 },
    })
  );
  // collapse/confirm spring (field → pill)
  const close = clamp(
    spring({
      frame: frame - (start + tSend) * fps,
      fps,
      config: { damping: 14, mass: 0.8, stiffness: 130 },
    })
  );
  // entrance
  const intro = clamp(
    spring({
      frame: frame - start * fps,
      fps,
      config: { damping: 16, mass: 0.7, stiffness: 140 },
    })
  );

  // width morph: 420 (btn) → 780 (field) → 460 (pill)
  const wField = 420 + (780 - 420) * open;
  const w = wField - (780 - 460) * close;
  const radius = 64 - 44 * open + 44 * close; // pill → rounded-rect → pill
  const isField = open > 0.02 && close < 0.5;

  // typing
  const typed = clamp((t - tOpen) / typeFor);
  const nChars = Math.round(typed * value.length);
  const shown = value.slice(0, nChars);
  const valid = nChars >= value.length && value.includes("@") && value.includes(".");
  const caretOn = Math.floor((frame / fps) * 2) % 2 === 0 && isField && !valid;

  // colors per state
  const bg = done
    ? OK
    : isField
    ? rgba("#0f1720", 0.95)
    : accent;
  const border = done
    ? OK
    : isField
    ? rgba("#ffffff", 0.14)
    : "transparent";

  const left = CX - w / 2;

  return (
    <AbsoluteFill
      style={{
        background: transparent ? undefined : coverBg(accent, ink),
        fontFamily: SANS,
        overflow: "hidden",
      }}
    >
      <Fonts />

      {/* a faint helper caption above, so the interaction reads even muted */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: CY - 150,
          textAlign: "center",
          fontFamily: MONO,
          fontSize: 24,
          letterSpacing: 4,
          textTransform: "uppercase",
          color: rgba(BRAND.paper, 0.4),
          opacity: intro * (done ? 0 : 1),
        }}
      >
        {isField ? "one field" : "one tap"}
      </div>

      <div
        style={{
          position: "absolute",
          left,
          top: CY - H / 2,
          width: w,
          height: H,
          borderRadius: radius,
          background: bg,
          border: `1px solid ${border}`,
          boxShadow: done
            ? `0 20px 60px -18px ${rgba(OK, 0.6)}`
            : isField
            ? `0 20px 60px -20px ${rgba("#000", 0.6)}, 0 0 0 1px ${rgba(accent, 0.25)}`
            : `0 20px 60px -18px ${rgba(accent, 0.6)}`,
          transform: `scale(${0.8 + intro * 0.2})`,
          transformOrigin: "50% 50%",
          opacity: intro,
          overflow: "hidden",
          display: "flex",
          alignItems: "center",
        }}
      >
        {/* IDLE button label */}
        {!isField && !done ? (
          <div
            style={{
              flex: 1,
              textAlign: "center",
              fontFamily: MONO,
              fontSize: 34,
              fontWeight: 700,
              letterSpacing: 3,
              textTransform: "uppercase",
              color: "#160a03",
            }}
          >
            {cta}
          </div>
        ) : null}

        {/* FIELD state: typed value + send button */}
        {isField ? (
          <>
            <div
              style={{
                flex: 1,
                paddingLeft: 36,
                fontFamily: MONO,
                fontSize: 38,
                color: nChars ? "#fff" : rgba(BRAND.paper, 0.4),
                whiteSpace: "nowrap",
                overflow: "hidden",
              }}
            >
              {nChars ? shown : placeholder}
              <span
                style={{
                  display: "inline-block",
                  width: 3,
                  height: 40,
                  marginLeft: 4,
                  verticalAlign: "-6px",
                  background: accent,
                  opacity: caretOn ? 1 : 0,
                }}
              />
            </div>
            <div
              style={{
                margin: 14,
                height: H - 28,
                padding: "0 34px",
                borderRadius: radius - 16,
                background: valid ? accent : rgba("#ffffff", 0.1),
                color: valid ? "#160a03" : rgba(BRAND.paper, 0.4),
                display: "flex",
                alignItems: "center",
                fontFamily: MONO,
                fontSize: 28,
                fontWeight: 700,
                letterSpacing: 3,
                textTransform: "uppercase",
              }}
            >
              {sendLabel}
            </div>
          </>
        ) : null}

        {/* DONE state: checkmark + label */}
        {done ? (
          <div
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 16,
              color: "#03211f",
              fontFamily: MONO,
              fontSize: 34,
              fontWeight: 700,
              letterSpacing: 3,
              textTransform: "uppercase",
            }}
          >
            <svg width={40} height={40} viewBox="0 0 24 24">
              <path
                d="M5 12.5 L10 17.5 L19 6.5"
                fill="none"
                stroke="#03211f"
                strokeWidth={2.8}
                strokeLinecap="round"
                strokeLinejoin="round"
                pathLength={100}
                strokeDasharray={100}
                strokeDashoffset={100 * (1 - clamp((close - 0.2) / 0.6))}
              />
            </svg>
            {doneLabel}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

export const morphFieldDemo: MorphFieldProps = {
  cta: "Join the list",
  placeholder: "you@studio.com",
  value: "vj@studio.com",
  sendLabel: "Send",
  doneLabel: "You're in",
  idle: 0.8,
  typeFor: 1.1,
  holdFor: 0.5,
};
