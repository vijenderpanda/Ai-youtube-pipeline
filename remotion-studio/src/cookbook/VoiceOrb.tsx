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
   VoiceOrb — a listening AI assistant: a glowing orb hears speech and the
   spoken words transcribe in under it, one at a time.
   Cookbook role: the invented AI-VOICE wow. Where ChatApp is the *typed* input
   metaphor and CommandPalette is the *keyboard* one, this is the VOICE one — the
   single beat that says "just talk to it." It is the one component in the kit
   whose subject is sound, so the whole frame is built to make silence look loud.

   WHY THIS LAYOUT
   - One orb, dead-center-upper, is the most literal "assistant is awake" glyph
     there is — no chrome, no app frame, nothing to read. The eye locks onto it
     in a frame, which is exactly the instant-read a 15s hold needs.
   - The orb is ALIVE, three ways at once, so it reads as *hearing* not just
     glowing: (1) a radial equalizer of ~60 bars rings it, each bar driven by a
     synthetic speech envelope so the ring breathes in bursts like real speech;
     (2) sound rings emanate outward on a loop like it's pulling voice in; (3) a
     rotating iridescent sheen + an env-reactive core keep the sphere itself
     restless. The waveform IS the wow — it's the proof the mic is open.
   - Under it the transcript TYPES word-by-word, each fresh word flashing accent
     then cooling to white — the visual grammar of live speech-to-text. A soft
     caret blinks at the writing edge. It grows and re-centers like real captions.
   - It LANDS: when the last word lands the orb settles — the equalizer calms to a
     quiet idle, the emanating rings stop, one confirm ring pushes out in a cool
     cyan, and the status pill flips from "Listening…" to the done label. A still
     near the end reads unmistakably as "heard you, on it" — a finished thought.

   9:16 SAFE: the orb is centered (well off both edges); the transcript block is
   inset 96px per side and hard-capped to 4 lines via maxHeight+overflow so no
   string can ever push into the caption band (its floor sits ~1400, clear of
   y=1517). JSON-safe: transcript/labels are strings, wps a number — no fn props.
   ========================================================================== */

export type VoiceOrbProps = {
  /** the "spoken" phrase that transcribes in word-by-word (the prompt). */
  transcript: string;
  /** pill text while the orb is hearing (default "Listening…"). */
  listeningLabel?: string;
  /** pill text once the phrase lands and the orb settles (default "Done ✦"). */
  doneLabel?: string;
  /** words per second the transcript types in at (default 2.4). */
  wps?: number;
  accent?: string; // orb + equalizer + caret (defaults to Sol magenta)
  ink?: string; // base fill
  start?: number; // seconds before the orb wakes and listening begins
  width?: number;
  height?: number;
  transparent?: boolean; // skip the backdrop (overlay use inside a composition)
};

/* deterministic 0..1 hash so every bar has a stable phase/speed across frames. */
const rnd = (n: number): number => {
  const s = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return s - Math.floor(s);
};

/* lerp two #hex colors → an rgb() string (freshly-heard word cools accent→white). */
const mixHex = (a: string, b: string, t: number): string => {
  const hex = (h: string) => {
    const s = h.replace("#", "");
    return parseInt(
      s.length === 3 ? s.split("").map((c) => c + c).join("") : s,
      16
    );
  };
  const pa = hex(a);
  const pb = hex(b);
  const l = (sh: number) =>
    Math.round(
      ((pa >> sh) & 255) + (((pb >> sh) & 255) - ((pa >> sh) & 255)) * clamp(t)
    );
  return `rgb(${l(16)},${l(8)},${l(0)})`;
};

export const VoiceOrb: React.FC<VoiceOrbProps> = ({
  transcript,
  listeningLabel = "Listening…",
  doneLabel = "Done ✦",
  wps = 2.4,
  accent = BRAND.mag,
  ink = BRAND.ink,
  start = 0.4,
  width = 1080,
  height = 1920,
  transparent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const confirmC = BRAND.cyan; // the cool "got it" tint the orb settles into

  const words = transcript.split(/\s+/).filter(Boolean);
  const N = words.length;

  // ── timeline (all in seconds from `start`) ──────────────────────────────
  const t = frame / fps - start; // seconds into the beat
  const wp = Math.max(0, t) * (wps > 0 ? wps : 2.4); // words progressed
  const doneAt = N / (wps > 0 ? wps : 2.4); // seconds the last word lands
  const dt = t - doneAt; // seconds since the phrase finished (neg before)
  const settle = clamp(dt / 0.6); // 0..1 ease into the settled/idle state

  // orb wakes with a spring; a springy confirm drives the done-ring + pill flip
  const appear = spring({
    frame: frame - start * fps,
    fps,
    config: { damping: 14, mass: 0.8, stiffness: 90 },
  });
  const conf = spring({
    frame: frame - (start + doneAt) * fps,
    fps,
    config: { damping: 13, mass: 0.7, stiffness: 120 },
  });

  // ── synthetic speech envelope: two slow sines multiplied = burst-y like a
  //    voice; it decays to a small idle breath as the orb settles. ──────────
  const speech =
    0.35 +
    0.65 *
      (0.5 + 0.5 * Math.sin(t * 6.1 + 0.4)) *
      (0.6 + 0.4 * Math.sin(t * 2.6));
  const idle = 0.16 + 0.05 * Math.sin(t * 1.4);
  const env = clamp(speech + (idle - speech) * settle, 0, 1) * appear;

  // ── geometry ────────────────────────────────────────────────────────────
  const cx = width / 2;
  const cy = Math.round(height * 0.33);
  const R = 190; // orb radius
  const NBARS = 60;
  const barInner = R + 18;
  const baseLen = 8;
  const amp = 88;
  const rot = t * 22; // slow iridescent-sheen rotation (deg)

  // orb breathes with the envelope, plus a one-shot swell the instant it lands
  const confBump =
    dt >= 0 && dt <= 0.5 ? Math.sin(clamp(dt / 0.5) * Math.PI) * 0.05 : 0;
  const breath =
    1 + 0.02 * Math.sin(t * 2.2) + 0.03 * env * (1 - settle) + confBump;
  const orbScale = interpolate(appear, [0, 1], [0.82, 1]) * breath;
  const coreScale = 0.7 + 0.55 * env; // bright inner core reacts to the voice

  // ── transcript typography (hard-capped so it can never reach the caption band)
  const FS = 60;
  const LH = Math.round(FS * 1.3);
  const caretOp =
    (0.28 + 0.72 * (0.5 + 0.5 * Math.sin(t * 8))) * (1 - settle) * appear;

  return (
    <AbsoluteFill
      style={{
        background: transparent ? undefined : coverBg(accent, ink),
        fontFamily: SANS,
        overflow: "hidden",
      }}
    >
      <Fonts />

      {/* ── status pill: "Listening…" crossfades to the done label ────────── */}
      <div
        style={{
          position: "absolute",
          top: Math.round(height * 0.075),
          width: "100%",
          display: "flex",
          justifyContent: "center",
        }}
      >
        <div style={{ position: "relative", opacity: appear }}>
          {/* listening pill */}
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 18,
              padding: "16px 34px 16px 28px",
              borderRadius: 999,
              background: rgba("#ffffff", 0.07),
              border: `1px solid ${rgba("#ffffff", 0.14)}`,
              boxShadow: `inset 0 1px 0 ${rgba("#ffffff", 0.2)}`,
              backdropFilter: "blur(20px)",
              WebkitBackdropFilter: "blur(20px)",
              opacity: 1 - clamp(conf),
            }}
          >
            {/* live mini-equalizer — 4 bars bouncing on the same envelope */}
            <div style={{ display: "flex", alignItems: "center", gap: 5, height: 34 }}>
              {[0, 1, 2, 3].map((k) => {
                const h =
                  10 + 24 * (0.5 + 0.5 * Math.sin(t * (7 + k) + k * 1.7)) * env;
                return (
                  <span
                    key={k}
                    style={{
                      width: 6,
                      height: h,
                      borderRadius: 4,
                      background: accent,
                      boxShadow: `0 0 10px ${rgba(accent, 0.8)}`,
                    }}
                  />
                );
              })}
            </div>
            <span
              style={{
                fontSize: 32,
                fontWeight: 700,
                letterSpacing: 3,
                textTransform: "uppercase",
                color: rgba(BRAND.paper, 0.86),
              }}
            >
              {listeningLabel}
            </span>
          </div>

          {/* done pill (cyan confirm) — sits on top, fades in on land */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 16,
              padding: "16px 36px",
              borderRadius: 999,
              background: `linear-gradient(180deg, ${rgba(confirmC, 0.3)}, ${rgba(
                confirmC,
                0.16
              )})`,
              border: `1px solid ${rgba(confirmC, 0.5)}`,
              boxShadow: `0 0 34px ${rgba(confirmC, 0.4)}, inset 0 1px 0 ${rgba(
                "#ffffff",
                0.3
              )}`,
              backdropFilter: "blur(20px)",
              WebkitBackdropFilter: "blur(20px)",
              opacity: clamp(conf),
              transform: `scale(${0.9 + 0.1 * clamp(conf)})`,
              whiteSpace: "nowrap",
            }}
          >
            <span
              style={{
                width: 34,
                height: 34,
                borderRadius: 999,
                background: confirmC,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: ink,
                fontSize: 22,
                fontWeight: 900,
                boxShadow: `0 0 16px ${rgba(confirmC, 0.9)}`,
              }}
            >
              ✓
            </span>
            <span
              style={{
                fontSize: 32,
                fontWeight: 800,
                letterSpacing: 2,
                textTransform: "uppercase",
                color: BRAND.paper,
              }}
            >
              {doneLabel}
            </span>
          </div>
        </div>
      </div>

      {/* ── outer glow bloom behind the orb (breathes with the orb) ───────── */}
      <div
        style={{
          position: "absolute",
          left: cx,
          top: cy,
          width: 900,
          height: 900,
          marginLeft: -450,
          marginTop: -450,
          background: `radial-gradient(circle at 50% 50%, ${rgba(
            settle > 0.5 ? confirmC : accent,
            0.34 * appear
          )} 0%, ${rgba(accent, 0)} 62%)`,
          filter: "blur(52px)",
          transform: `scale(${0.9 + 0.14 * env})`,
        }}
      />

      {/* ── the orb machinery: emanating rings, equalizer, confirm ring ───── */}
      <svg
        width={width}
        height={height}
        style={{ position: "absolute", inset: 0, pointerEvents: "none" }}
      >
        {/* sound rings emanate outward on a loop while listening */}
        {[0, 1, 2].map((k) => {
          const period = 2.4;
          const phase = (((t + (k * period) / 3) % period) + period) % period;
          const f = phase / period; // 0..1
          const rr = R + 8 + f * 150;
          const op = (1 - f) * 0.3 * (1 - settle) * appear;
          return op > 0.01 ? (
            <circle
              key={k}
              cx={cx}
              cy={cy}
              r={rr}
              fill="none"
              stroke={accent}
              strokeWidth={3}
              opacity={op}
            />
          ) : null;
        })}

        {/* the radial equalizer — the live waveform, the wow */}
        <g style={{ filter: `drop-shadow(0 0 9px ${rgba(accent, 0.55)})` }}>
          {Array.from({ length: NBARS }).map((_, j) => {
            const a = (j / NBARS) * Math.PI * 2 - Math.PI / 2;
            const ph = rnd(j) * 6.283;
            const spd = 5 + rnd(j + 9) * 4;
            const wob = 0.5 + 0.5 * Math.sin(t * spd + ph);
            const wob2 = 0.5 + 0.5 * Math.sin(t * spd * 0.5 - j * 0.7 + 1.3);
            const travel = 0.5 + 0.5 * Math.sin(a * 3 - t * 4); // energy circulates
            const barN = clamp(wob * 0.5 + wob2 * 0.3 + travel * 0.2);
            const len = baseLen + amp * env * barN;
            const x1 = cx + barInner * Math.cos(a);
            const y1 = cy + barInner * Math.sin(a);
            const x2 = cx + (barInner + len) * Math.cos(a);
            const y2 = cy + (barInner + len) * Math.sin(a);
            return (
              <line
                key={j}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={mixHex(accent, confirmC, settle * 0.55)}
                strokeWidth={6}
                strokeLinecap="round"
                opacity={(0.4 + 0.6 * barN) * appear}
              />
            );
          })}
        </g>

        {/* the confirm ring — one cool pulse pushes out the moment it lands */}
        {conf > 0.001 ? (
          <circle
            cx={cx}
            cy={cy}
            r={R + 10 + conf * 210}
            fill="none"
            stroke={confirmC}
            strokeWidth={5}
            opacity={(1 - conf) * 0.9}
          />
        ) : null}
      </svg>

      {/* ── the glass orb itself (layered gradients + rotating sheen + core) ─ */}
      <div
        style={{
          position: "absolute",
          left: cx - R,
          top: cy - R,
          width: R * 2,
          height: R * 2,
          borderRadius: "50%",
          overflow: "hidden",
          transform: `scale(${orbScale})`,
          opacity: appear,
          background: [
            `radial-gradient(circle at 36% 30%, ${rgba("#ffffff", 0.85)} 0%, ${rgba(
              "#ffffff",
              0
            )} 20%)`,
            `radial-gradient(circle at 50% 64%, ${rgba(ink, 0.55)} 0%, ${rgba(
              ink,
              0
            )} 58%)`,
            `radial-gradient(circle at 50% 46%, ${rgba(accent, 0.98)} 0%, ${rgba(
              accent,
              0.7
            )} 40%, ${rgba(accent, 0.22)} 72%, ${rgba(accent, 0)} 100%)`,
          ].join(","),
          boxShadow: `0 0 120px ${rgba(accent, 0.6 * appear)}, inset 0 0 70px ${rgba(
            "#ffffff",
            0.16
          )}, inset 0 -34px 66px ${rgba(ink, 0.5)}`,
          backdropFilter: "blur(4px)",
          WebkitBackdropFilter: "blur(4px)",
        }}
      >
        {/* rotating iridescent sheen — the "subtle rotation" that keeps it alive */}
        <div
          style={{
            position: "absolute",
            inset: "-12%",
            borderRadius: "50%",
            background: `conic-gradient(from 0deg, ${rgba(confirmC, 0)}, ${rgba(
              confirmC,
              0.5
            )}, ${rgba(accent, 0)}, ${rgba("#ffffff", 0.4)}, ${rgba(accent, 0)}, ${rgba(
              confirmC,
              0
            )})`,
            filter: "blur(16px)",
            opacity: 0.55,
            mixBlendMode: "screen",
            transform: `rotate(${rot}deg)`,
          }}
        />
        {/* the reactive voice core — swells with the envelope */}
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            width: R,
            height: R,
            marginLeft: -R / 2,
            marginTop: -R / 2,
            borderRadius: "50%",
            background: `radial-gradient(circle at 50% 50%, ${rgba(
              "#ffffff",
              0.95
            )} 0%, ${rgba("#ffffff", 0.35)} 34%, ${rgba("#ffffff", 0)} 66%)`,
            filter: "blur(8px)",
            transform: `scale(${coreScale})`,
            opacity: 0.9,
            mixBlendMode: "screen",
          }}
        />
        {/* cyan confirm wash blooms across the orb as it settles */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "50%",
            background: `radial-gradient(circle at 50% 50%, ${rgba(
              confirmC,
              0.5
            )} 0%, ${rgba(confirmC, 0)} 68%)`,
            opacity: clamp(conf) * 0.7,
            mixBlendMode: "screen",
          }}
        />
        {/* specular top-left glass highlight */}
        <div
          style={{
            position: "absolute",
            left: "24%",
            top: "16%",
            width: "34%",
            height: "24%",
            borderRadius: "50%",
            background: `radial-gradient(circle at 50% 50%, ${rgba(
              "#ffffff",
              0.9
            )} 0%, ${rgba("#ffffff", 0)} 70%)`,
            filter: "blur(4px)",
          }}
        />
      </div>

      {/* ── the transcript — types in word-by-word under the orb ──────────── */}
      <div
        style={{
          position: "absolute",
          top: Math.round(height * 0.565),
          left: 96,
          width: width - 192,
          maxHeight: LH * 4, // hard cap: 4 lines, never reaches the caption band
          overflow: "hidden",
          textAlign: "center",
          lineHeight: `${LH}px`,
        }}
      >
        {words.map((w, i) => {
          if (wp <= i) return null; // not yet reached this word
          const local = clamp(wp - i); // 0..1 reveal window for this word
          const rise = (1 - clamp(local * 2)) * 16;
          return (
            <span
              key={i}
              style={{
                display: "inline-block",
                marginRight: "0.3em",
                fontSize: FS,
                fontWeight: 700,
                letterSpacing: 0.3,
                // fresh word flashes accent then cools to paper white
                color: mixHex(accent, BRAND.paper, clamp(local * 1.5)),
                opacity: clamp(local * 3),
                transform: `translateY(${rise}px)`,
                textShadow:
                  local < 1
                    ? `0 0 26px ${rgba(accent, (1 - local) * 0.7)}`
                    : "none",
              }}
            >
              {w}
            </span>
          );
        })}
        {/* the writing caret — a soft accent bar that blinks, gone once settled */}
        <span
          style={{
            display: "inline-block",
            width: 6,
            height: FS * 0.9,
            verticalAlign: "-0.12em",
            borderRadius: 3,
            background: accent,
            boxShadow: `0 0 16px ${rgba(accent, 0.9)}`,
            opacity: caretOp,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

export const voiceOrbDemo: VoiceOrbProps = {
  transcript: "summarize my inbox and draft three replies",
  listeningLabel: "Listening…",
  doneLabel: "On it ✦",
  wps: 2.4,
};
