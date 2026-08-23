import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {
  BRAND,
  MONO,
  rgba,
  clamp,
  AuroraBed,
  glassChrome,
  GlassInner,
} from "./kit";

/* =============================================================================
   TermRun — a cookbook-native full-frame terminal (the "one command" beat).

   Ports the terminal HALF of components/CodeDemo.tsx (Ep11's VS Code
   recreation) into the cookbook contract: 1080x1920-native, aurora + glass
   material, JSON props. Where CodeDemo staged a whole IDE for the pipCallout
   top zone, this is the naked moment the web-tour grammar needs — one prompt,
   one command typing itself, the response streaming in.

   The staging in three phases:
     1. TYPE   the command types char-by-char behind a solid block cursor
               (charsPerSec, real typing has no blink), then the cursor blinks
               while the "machine thinks" for a beat.
     2. STREAM response lines rise in one after another on CodeDemo's spring
               (damping 20, mass 0.5), each tinted by tone — ok mint, accent
               gold, warn brand yellow, info muted paper.
     3. HELD   a fresh prompt appears under the output with a blinking block
               cursor — the classic "command finished" state. The blink + the
               panel's repeating sheen keep the held final state breathing
               (never static, N5).

   The card is dark glass: GlassInner's refraction sample under an extra ink
   wash, so it reads as the same material as the rest of the cut while staying
   terminal-dark for legibility. Mono size auto-fits the longest line so
   nothing can clip sideways; response hard-caps at 12 lines (safe band).
   JSON-safe props only (build_ep_v2 feeds --props as JSON).
   ========================================================================== */

/** one streamed response line — module-local so the file exports exactly the
    three cookbook symbols (the Props type inlines this shape). */
type TermLine = {
  t: string; // the line's text
  tone?: "ok" | "info" | "warn" | "accent"; // tint (default info)
};

export type TermRunProps = {
  cmd: string; // the command typed after the prompt
  typeStart?: number; // seconds before typing begins (default 0.6)
  charsPerSec?: number; // typing speed (default 28)
  response?: TermLine[]; // streamed output, max 12 — hard-capped by slice
  lineStagger?: number; // seconds between response lines (default 0.18)
  promptLabel?: string; // the cwd shown at the prompt (default "~/work")
  cursor?: boolean; // block cursors on (default true)
  accent?: string; // prompt caret tint (default brand magenta)
  ink?: string;
  start?: number; // seconds before the component begins
  width?: number;
  height?: number;
  transparent?: boolean; // skip the bed (overlay use inside a live comp)
};

/* tone palette — ok mint / accent gold are the web-tour template's calls */
const TONES: Record<NonNullable<TermLine["tone"]>, string> = {
  ok: "#6FD5A8",
  info: rgba(BRAND.paper, 0.78),
  warn: BRAND.yellow,
  accent: "#FFB454",
};

const easeOut = (x: number) => 1 - Math.pow(1 - clamp(x), 3);

export const TermRun: React.FC<TermRunProps> = ({
  cmd,
  typeStart = 0.6,
  charsPerSec = 28,
  response = [],
  lineStagger = 0.18,
  promptLabel = "~/work",
  cursor = true,
  accent = BRAND.mag,
  ink = BRAND.ink,
  start = 0,
  width = 1080,
  height = 1920,
  transparent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = (frame - start * fps) / fps; // seconds on this component's clock

  const lines = (response ?? []).slice(0, 12); // hard cap — safe band

  /* ---- typing math (CodeDemo's, re-based on a speed knob) ---- */
  const typedChars = Math.max(
    0,
    Math.min(cmd.length, Math.floor((t - typeStart) * charsPerSec))
  );
  const typed = cmd.slice(0, typedChars);
  const typeDone = typeStart + cmd.length / charsPerSec;
  const typing = t >= typeStart && typedChars < cmd.length;
  const blinkOn = Math.floor(t * 2) % 2 === 0; // 2Hz, CodeDemo's blink

  /* ---- stream + held-prompt timeline ---- */
  const respStart = typeDone + 0.35; // the machine "thinks" for a beat
  const lineAt = (i: number) => respStart + i * lineStagger;
  const promptAt = lineAt(Math.max(0, lines.length - 1)) + 0.6;
  const promptP = easeOut((t - promptAt) / 0.35);

  /* ---- geometry — auto-fit mono so no line can clip sideways ---- */
  const cardX = 56;
  const cardW = width - cardX * 2; // 968
  const padX = 40;
  const headerH = 92;
  const maxChars = Math.max(
    promptLabel.length + 2 + cmd.length,
    ...lines.map((l) => l.t.length),
    1
  );
  const CH = 0.6; // mono advance ≈ 0.6em
  const fontSize = clamp((cardW - padX * 2) / (maxChars * CH), 22, 36);
  const lineH = Math.round(fontSize * 1.62);
  const cmdH = Math.round(fontSize * 1.7);
  const padY = 32;
  const cardH =
    headerH + padY + cmdH + 14 + lines.length * lineH + cmdH + padY;

  // center in the safe band (132..1580)
  const bandTop = 152;
  const bandBot = 1560;
  const cardY = Math.max(bandTop, bandTop + (bandBot - bandTop - cardH) / 2);

  /* ---- entrance + idle drift + sheen cycle ---- */
  const panelP = spring({
    frame: frame - start * fps,
    fps,
    durationInFrames: Math.round(0.55 * fps),
    config: { damping: 200, mass: 0.9 },
  });
  const driftX = Math.sin(t * 0.37) * 3;
  const driftY = Math.cos(t * 0.31) * 2.5;
  // entry pass, then a slow repeat so the held terminal still breathes
  const sheenT = t - 0.4;
  const sheenP = sheenT < 1.5 ? clamp(sheenT / 1.5) : ((sheenT - 1.5) % 3.2) / 3.2;

  const block = (on: boolean) =>
    on ? (
      <span
        style={{
          display: "inline-block",
          width: Math.round(fontSize * 0.55),
          height: fontSize,
          marginLeft: 4,
          verticalAlign: "text-bottom",
          background: "#E8E8E8",
          borderRadius: 2,
        }}
      />
    ) : null;

  return (
    <AbsoluteFill
      style={{
        background: transparent ? undefined : ink,
        fontFamily: MONO,
        overflow: "hidden",
      }}
    >
      {!transparent && <AuroraBed t={t} accent={accent} ink={ink} />}

      {/* the dark-glass terminal card */}
      <div
        style={{
          position: "absolute",
          left: cardX,
          top: cardY,
          width: cardW,
          height: cardH,
          ...glassChrome(30),
          transform: `translate3d(${driftX}px, ${driftY + (1 - panelP) * 30}px, 0) scale(${0.96 + panelP * 0.04})`,
          transformOrigin: "center top",
          opacity: clamp(panelP * 1.4),
        }}
      >
        <GlassInner
          t={t}
          x={cardX}
          y={cardY}
          w={cardW}
          h={cardH}
          accent={accent}
          ink={ink}
          sheen={sheenP}
          stageW={width}
          stageH={height}
        />
        {/* extra ink wash — glass, but terminal-dark for mono legibility */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: rgba("#07080d", 0.52),
          }}
        />

        {/* title bar — traffic lights + session label */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: "100%",
            height: headerH,
            display: "flex",
            alignItems: "center",
            padding: `0 ${padX - 8}px`,
            borderBottom: `1px solid ${rgba("#ffffff", 0.08)}`,
            background: rgba("#ffffff", 0.02),
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
              position: "absolute",
              left: 0,
              right: 0,
              textAlign: "center",
              fontSize: 26,
              letterSpacing: 1,
              color: BRAND.mute,
              pointerEvents: "none",
            }}
          >
            {promptLabel} — claude
          </div>
        </div>

        {/* the session */}
        <div
          style={{
            position: "absolute",
            left: padX,
            right: padX,
            top: headerH + padY,
            bottom: padY,
            overflow: "hidden",
          }}
        >
          {/* command line */}
          <div style={{ fontSize, lineHeight: `${cmdH}px`, whiteSpace: "nowrap" }}>
            <span style={{ color: BRAND.mute }}>{promptLabel} </span>
            <span style={{ color: accent, fontWeight: 700 }}>❯ </span>
            <span style={{ color: "#FFFFFF" }}>{typed}</span>
            {/* solid while typing, blinking while the machine thinks */}
            {cursor && (typing || (t >= typeDone && t < respStart))
              ? block(typing || blinkOn)
              : null}
          </div>

          {/* response stream — CodeDemo's spring rise, tone-tinted */}
          <div style={{ marginTop: 14 }}>
            {lines.map((l, i) => {
              const at = lineAt(i);
              if (t < at) return null;
              const s = spring({
                frame: frame - Math.round((start + at) * fps),
                fps,
                config: { damping: 20, mass: 0.5 },
              });
              return (
                <div
                  key={i}
                  style={{
                    fontSize,
                    lineHeight: `${lineH}px`,
                    color: TONES[l.tone ?? "info"],
                    opacity: interpolate(s, [0, 1], [0, 1]),
                    transform: `translateY(${interpolate(s, [0, 1], [8, 0])}px)`,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {l.t}
                </div>
              );
            })}

            {/* the held state — a fresh prompt, cursor blinking */}
            {promptP > 0 ? (
              <div
                style={{
                  fontSize,
                  lineHeight: `${cmdH}px`,
                  opacity: promptP,
                  whiteSpace: "nowrap",
                }}
              >
                <span style={{ color: BRAND.mute }}>{promptLabel} </span>
                <span style={{ color: accent, fontWeight: 700 }}>❯</span>
                {cursor ? block(blinkOn) : null}
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const termRunDemo: TermRunProps = {
  cmd: 'claude "add dark mode to my app"',
  typeStart: 0.6,
  charsPerSec: 28,
  response: [
    { t: "● reading the repo…", tone: "info" },
    { t: "✓ 12 files scanned", tone: "ok" },
    { t: "✓ theme.css written", tone: "ok" },
    { t: "✓ toggle wired into the header", tone: "ok" },
    { t: "done in 45s — review the diff", tone: "accent" },
  ],
  lineStagger: 0.18,
  promptLabel: "~/work",
};
