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
   OutroGlass — the channel's question-CTA sting, in the GlassPanel language.

   WHY (VJ, 2026-08-19): the shipped sting (gen_outro_card.py) is a FLAT PIL
   still with a Ken-Burns push — no material, no depth, no motion. My first
   rebuild fixed the material but VJ called it: "not looking sleek and premium,
   some buttons are fat, some weird text fonts, not appealing — you created good
   components earlier." Right on all three. So this version stops inventing and
   follows the house style that already works (GlassPanel, the one VJ said he
   loves), to the value:

     · frost wash 0.34 -> 0.50 (NOT darker) so the aurora reads THROUGH the
       glass — a dark wash kills the refraction and the panel dies as a grey box
     · a 3px caustic bright top edge — the single detail that sells real glass
     · MONO eyebrow at 24/ls 6, DISPLAY (Anton) headline at ls -1, SANS body
       (NO Playfair italic — that was the "weird font")
     · NO fat pills: rows separated by 1px hairlines at rgba(#fff,.12), values
       right-aligned in Anton. Restraint is the entire skill here.
     · left-aligned with a 60px pad, not centred mush

   Motion still comes from the Wow Mechanics research (artifact b9570dbc):
   Plate 01 refractive glass (baked blur — backdrop-filter is unreliable
   headless; "the trick is the inset highlight, not the blur"), Plate 03 kinetic
   type (per-word 26ms stagger, rotateX(-82deg)->0, scaleX 1.7->1), Plate 07
   depth-without-3D (scripted camera, layered parallax, sheen, SVG grain).

   Brand vocabulary preserved: host disc, the question, comment CTA, subscribe,
   "one AI trick, every single day". Holds a readable end state.
   ========================================================================== */

export type OutroGlassProps = {
  question: string; // lines split by "|" — the hero, set in Anton
  eyebrow?: string; // tiny mono caps above the question
  commentLabel?: string; // left cell of the comment row
  commentValue?: string; // right cell, accent
  subscribeLabel?: string; // left cell of the subscribe row
  subscribeValue?: string; // right cell, accent
  tagline?: string; // small line under the panel
  avatar?: string; // host disc, resolved via staticFile()
  accent?: string; // brand magenta
  accent2?: string; // cyan
  ink?: string;
  start?: number;
  /* PROMPT REVEAL (Studio recommendation, 2026-08-20): "show the result first,
     then end with a very quick flash of the prompt used - this encourages
     viewers to rewatch or pause". So the sting opens on the ACTUAL typed line,
     set chunky, with an explicit pause affordance, then resolves into the CTA
     card. The text must be the real prompt, verbatim - it is the thing the
     video claims built the app. */
  promptText?: string;
  promptLabel?: string;   // MONO eyebrow over it
  promptHint?: string;    // the pause affordance
  promptDur?: number;     // seconds the prompt phase owns
  width?: number;
  height?: number;
  /* --- draw-rule: Plate 09's draw grammar applied to the panel's OWN rules ---
     Chosen over four candidates by an adversarial design panel. Every rival
     answered "add a wow bar" by adding an OBJECT (a comb, a rail, a calendar
     strip) and each had to be argued out of looking like a statistic. This adds
     no object, no string, no numeral and no font: the three lines the panel
     already owns stop APPEARING and start DRAWING. */
  rule?: boolean;        // master switch for the accent rule (collision guard can force off)
  ruleWeight?: number;   // accent stroke px, default 4, hard-capped at 6
  ruleGap?: number;      // px between the question block and the rule
  ruleColorMid?: string; // mid gradient stop
  ruleGlow?: boolean;    // subtle magenta drop-shadow
  ruleDelay?: number;    // s after `start` before the rule draws
  ruleDraw?: number;     // s the rule takes to draw
  rowDrawDelay?: number; // s after `start` before hairline 1 draws
  rowDraw?: number;      // s each hairline takes
  rowDrawStagger?: number; // s between hairline 1 and 2
  drawEdge?: boolean;    // wet leading edge on the hairlines
};


export const OutroGlass: React.FC<OutroGlassProps> = ({
  question,
  eyebrow = "BEFORE YOU GO",
  commentLabel = "Drop it in the comments",
  commentValue = "↳",
  subscribeLabel = "Subscribe",
  subscribeValue = "ONE / DAY",
  tagline = "one AI trick, every single day",
  avatar,
  accent = BRAND.mag,
  accent2 = BRAND.cyan,
  ink = BRAND.ink,
  start = 0.15,
  promptText,
  promptLabel = "THE PROMPT",
  promptHint = "pause to copy",
  promptDur = 1.5,
  rule = true,
  ruleWeight = 4,
  ruleGap = 44,
  ruleColorMid = "#C43BFF",
  ruleGlow = true,
  ruleDelay = 0.4,
  ruleDraw = 0.42,
  rowDrawDelay = 0.46,
  rowDraw = 0.46,
  rowDrawStagger = 0.14,
  drawEdge = true,
  width = 1080,
  height = 1920,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const hasPrompt = !!promptText;
  const pDur = hasPrompt ? promptDur : 0;
  // everything the CTA card does is offset behind the prompt phase
  const st = t - start - pDur;
  const pt = t - start;                         // prompt-phase clock
  const pIn = clamp(pt / 0.3);                  // prompt rises
  const pOut = hasPrompt ? clamp((pt - (pDur - 0.34)) / 0.34) : 1;  // and clears

  // Plate 07 — slow scripted camera (no cursor in a render)
  const camX = Math.sin(t * 0.42) * 1.0 + Math.sin(t * 0.19 + 1) * 0.4;
  const camY = Math.cos(t * 0.35) * 0.8;
  const depth = (k: number) => `translate3d(${camX * k * 12}px, ${camY * k * 10}px, 0)`;

  const assemble = spring({
    frame: frame - Math.round(start * fps),
    fps,
    config: { damping: 18, mass: 0.9, stiffness: 90 },
  });
  const sheen = clamp((st - 0.35) / 1.25);

  const PW = width - 168;
  const PH = 700;   // sized to content — 900 left a void between question and rows
  const PX = (width - PW) / 2;
  const PY = 672;
  const PAD = 60;

  const lines = question.split("|").map((l) => l.trim()).filter(Boolean);
  const words: { w: string; i: number; line: number }[] = [];
  let wi = 0;
  lines.forEach((ln, li) => ln.split(" ").forEach((w) => words.push({ w, i: wi++, line: li })));
  // Anton is condensed (~0.52em advance); fit the longest line inside the pad
  const longest = Math.max(...lines.map((l) => l.length), 1);
  const qSize = Math.min(104, Math.floor((PW - PAD * 2) / (longest * 0.5)));

  /* ---- draw clocks (Plate 06 settle, NOT a spring: a line that overshoots its
     own length is wrong). One easing for every drawn line. ---- */
  const ROW_W = PW - PAD * 2;                       // 792 — the one width every line uses
  const EASE = Easing.bezier(0.2, 0.9, 0.25, 1);
  const drawP = (a: number, b: number) =>
    interpolate(st, [a, b], [0, 1], {
      easing: EASE,
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  const ruleE = drawP(ruleDelay, ruleDelay + ruleDraw);
  const h1P = drawP(rowDrawDelay, rowDrawDelay + rowDraw);
  const h2P = drawP(rowDrawDelay + rowDrawStagger, rowDrawDelay + rowDrawStagger + rowDraw);
  const ruleW = Math.min(6, Math.max(1, ruleWeight));  // >6px next to 1px hairlines = a slab

  /* Collision guard: the rows are BOTTOM-anchored while the rule is in normal
     flow from the top, so they converge as the question grows. Without this a
     3-line question drives the rule straight through hairline 1. Ships with the
     feature, not after it. */
  const EB_H = 28.8;                                  // MONO 24 at normal line-height
  const qBlockH = lines.length * qSize * 1.04;
  const ruleBottomLocal = EB_H + 26 + qBlockH + ruleGap + 12;
  const ROWS_RESERVE = 238;
  const showRule = rule && ruleBottomLocal <= PH - PAD * 2 - ROWS_RESERVE;

  const rowIn = (d: number) => clamp((st - d) / 0.5);

  const Row: React.FC<{
    label: string;
    value: string;
    color: string;
    d: number;
    p: number;
  }> = ({ label, value, color, d, p }) => {
    const inP = rowIn(d);
    const shift = `translateY(${(1 - inP) * 14}px)`;
    const headX = p * ROW_W;
    // wet leading edge — same idea as the panel's caustic top edge: it sells the
    // line as light rather than a wipe. Exactly 0 at p=1, so the held frame is clean.
    const edgeOp = drawEdge ? clamp(p / 0.06) * clamp((1 - p) / 0.14) : 0;
    return (
      <div
        style={{
          position: "relative",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "26px 0",
          // kept transparent so the box model is pixel-identical to the painted
          // border it replaces; the drawn hairline sits inside that band.
          borderTop: "1px solid transparent",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 0,
            top: -1,
            height: 1,
            width: headX,
            background: rgba("#ffffff", 0.12),
          }}
        />
        {edgeOp > 0 && (
          <div
            style={{
              position: "absolute",
              top: -1,
              height: 1,
              left: Math.max(0, headX - 40),
              width: Math.min(40, headX),
              background: `linear-gradient(90deg, ${rgba("#ffffff", 0)} 0%, ${rgba(
                "#ffffff",
                0.3
              )} 100%)`,
              opacity: edgeOp,
            }}
          />
        )}
        <span
          style={{
            display: "inline-block",
            fontFamily: SANS,
            fontSize: 38,
            color: rgba(BRAND.paper, 0.82),
            opacity: inP,
            transform: shift,
          }}
        >
          {label}
        </span>
        <span
          style={{
            display: "inline-block",
            fontFamily: DISPLAY,
            fontSize: 44,
            color,
            letterSpacing: 0.5,
            opacity: inP,
            transform: shift,
          }}
        >
          {value}
        </span>
      </div>
    );
  };

  return (
    <AbsoluteFill style={{ background: ink, fontFamily: SANS, overflow: "hidden" }}>
      <Fonts />
      <AuroraBed t={t} accent={accent} ink={ink} opacity={0.38} />

      {/* SVG grain (Plate 07) */}
      <svg style={{ position: "absolute", inset: 0, opacity: 0.14, mixBlendMode: "overlay" }}>
        <filter id="og-grain">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" />
        </filter>
        <rect width="100%" height="100%" filter="url(#og-grain)" />
      </svg>

      {/* ── PROMPT REVEAL — the real typed line, chunky, pausable ────────── */}
      {hasPrompt && pOut < 1 && (
        <div
          style={{
            position: "absolute",
            left: 84,
            right: 84,
            top: 500,   // longer prompt needs more vertical room
            opacity: pIn * (1 - pOut),
            transform: `translateY(${(1 - pIn) * 24 - pOut * 26}px)`,
          }}
        >
          <div
            style={{
              fontFamily: MONO,
              fontSize: 26,
              letterSpacing: 7,
              color: accent2,
              marginBottom: 22,
            }}
          >
            {promptLabel}
          </div>
          <div
            style={{
              padding: "52px 48px",
              borderRadius: 40,
              background: `linear-gradient(160deg, ${rgba("#0a0b12", 0.42)}, ${rgba("#0a0b12", 0.66)})`,
              border: `1px solid ${rgba("#ffffff", 0.30)}`,
              boxShadow: `0 50px 110px -46px ${rgba("#000", 0.8)}, inset 0 1px 0 ${rgba("#ffffff", 0.5)}`,
            }}
          >
            {/* caustic top edge — same glass grammar as the card below */}
            <div
              style={{
                position: "absolute",
                left: 46,
                right: 46,
                marginTop: -44,
                height: 3,
                background: `linear-gradient(90deg, ${rgba("#fff", 0)} 0%, ${rgba("#fff", 0.7)} 50%, ${rgba("#fff", 0)} 100%)`,
              }}
            />
            <div
              style={{
                fontFamily: DISPLAY,
                fontSize: 54,   // sized to the REAL prompt's length, not shrunk to fit a trim
                lineHeight: 1.2,
                letterSpacing: -0.5,
                color: "#fff",
              }}
            >
              {/* WORD-BY-WORD, over ~1.8s, then held. A prompt card is a reading
                  surface -- the viewer is being asked to pause and copy it -- so
                  it must NOT keep animating. But a card that arrives complete
                  leaves the film's last five seconds on a frozen frame, which is
                  the measured retention killer. Revealing then holding gets both:
                  motion on the cut, stillness to copy from. */}
              {String(promptText).split(" ").map((w, i, arr) => (
                <span key={i} style={{
                  opacity: clamp((pt - 0.22 - (i / Math.max(arr.length - 1, 1)) * 1.55) / 0.34),
                }}>{w}{i < arr.length - 1 ? " " : ""}</span>
              ))}
            </div>
          </div>
          {promptHint && (
            <div
              style={{
                marginTop: 26,
                textAlign: "center",
                fontFamily: MONO,
                fontSize: 26,
                letterSpacing: 5,
                textTransform: "uppercase",
                color: rgba(BRAND.paper, 0.62),
                // only once there is something to copy
                opacity: clamp((pt - 1.85) / 0.4),
              }}
            >
              {promptHint}
            </div>
          )}
        </div>
      )}

      {/* host disc — deepest layer, small and restrained */}
      {avatar && (
        <div
          style={{
            position: "absolute",
            left: width / 2 - 104,
            top: 356,
            width: 208,
            height: 208,
            borderRadius: "50%",
            overflow: "hidden",
            border: `4px solid ${rgba("#ffffff", 0.9)}`,
            boxShadow: `0 24px 60px -18px ${rgba("#000", 0.8)}`,
            transform: `${depth(0.2)} scale(${interpolate(assemble, [0, 1], [0.92, 1])})`,
            opacity: clamp(assemble * 1.3) * clamp(pOut),
          }}
        >
          <Img
            src={avatar.startsWith("http") ? avatar : staticFile(avatar)}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </div>
      )}

      {/* glass panel */}
      <div
        style={{
          position: "absolute",
          left: PX,
          top: PY,
          width: PW,
          height: PH,
          borderRadius: 48,
          overflow: "hidden",
          border: `1px solid ${rgba("#ffffff", 0.35)}`,
          // Plate 01 — the inset highlight is the trick, not the blur
          boxShadow: `0 60px 130px -46px ${rgba("#000", 0.75)}, inset 0 1px 0 ${rgba(
            "#ffffff",
            0.55
          )}, inset 0 -1px 0 ${rgba("#ffffff", 0.08)}`,
          transform: `${depth(0.5)} scale(${interpolate(assemble, [0, 1], [0.965, 1])})`,
          opacity: clamp(assemble * 1.2) * clamp(pOut),
        }}
      >
        {/* BAKED refraction — the bed again, clipped, blown up + blurred */}
        <div
          style={{
            position: "absolute",
            left: -PX * 1.06 - PW * 0.03,
            top: -PY * 1.06 - PH * 0.03,
            width: width * 1.06,
            height: height * 1.06,
            filter: "blur(26px) saturate(200%) brightness(1.08)",
          }}
        >
          <AuroraBed t={t} accent={accent} ink={ink} opacity={0.38} />
        </div>

        {/* frost wash — LIGHT, so the aurora still reads through the glass */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: `linear-gradient(160deg, ${rgba("#0a0b12", 0.34)} 0%, ${rgba(
              "#0a0b12",
              0.5
            )} 100%)`,
          }}
        />
        {/* caustic bright top edge — the detail that sells real glass */}
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: 0,
            height: 3,
            background: `linear-gradient(90deg, ${rgba("#fff", 0)} 0%, ${rgba(
              "#fff",
              0.7
            )} 50%, ${rgba("#fff", 0)} 100%)`,
          }}
        />
        {/* one specular pass */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: `linear-gradient(100deg, transparent 34%, ${rgba(
              "#ffffff",
              0.14
            )} 50%, transparent 66%)`,
            transform: `translateX(${interpolate(sheen, [0, 1], [-130, 130])}%)`,
          }}
        />

        {/* content */}
        <div style={{ position: "absolute", inset: 0, padding: PAD }}>
          <div
            style={{
              fontFamily: MONO,
              fontSize: 24,
              letterSpacing: 6,
              color: rgba(BRAND.paper, 0.72),
              opacity: clamp(assemble * 1.4),
            }}
          >
            {eyebrow}
          </div>

          {/* Plate 03 — kinetic question, set in Anton */}
          <div style={{ marginTop: 26, perspective: 900 }}>
            {lines.map((_, li) => (
              <div key={li} style={{ display: "flex", flexWrap: "wrap", gap: "0 16px" }}>
                {words
                  .filter((w) => w.line === li)
                  .map((w) => {
                    const d = 0.18 + w.i * 0.026; // 26ms stagger, per research
                    const s = spring({
                      frame: frame - Math.round((start + d) * fps),
                      fps,
                      config: { damping: 15, mass: 0.7, stiffness: 130 },
                    });
                    return (
                      <span
                        key={w.i}
                        style={{
                          display: "inline-block",
                          fontFamily: DISPLAY,
                          fontSize: qSize,
                          lineHeight: 1.04,
                          letterSpacing: -1,
                          color: "#fff",
                          opacity: clamp(s * 1.5),
                          transformOrigin: "50% 100%",
                          transform: `rotateX(${interpolate(s, [0, 1], [-82, 0])}deg) scaleX(${interpolate(
                            s,
                            [0, 1],
                            [1.7, 1]
                          )})`,
                        }}
                      >
                        {w.w}
                      </span>
                    );
                  })}
              </div>
            ))}
          </div>

          {/* HONESTY INVARIANT — do not weaken, do not "improve":
              · This rule is typographic punctuation. It is the bottom of the
                sentence. It is NOT a chart, a meter, a progress bar or a proportion.
              · It is ALWAYS 100% of the content width. There is deliberately no
                length / value / percent / count / target prop, and none may ever
                be added — the invariant is enforced in code, not in review.
              · There is NO pre-drawn track behind it. The rule draws onto empty
                ground, so no reference length exists on any frame and therefore
                no proportion can be read.
              · No numeral, unit, tick, axis, label or counter may be attached.
              · In the held frame every drawn line is at 100% of its own extent. */}
          {showRule && (
            <svg
              width={ROW_W}
              height={12}
              viewBox={`0 0 ${ROW_W} 12`}
              style={{
                display: "block",
                marginTop: ruleGap,
                overflow: "visible",           // round caps must not clip
                opacity: ruleE > 0 ? 1 : 0,    // a cap can never leave a dot at zero length
                filter: ruleGlow ? `drop-shadow(0 0 8px ${rgba(accent, 0.22)})` : undefined,
              }}
            >
              <defs>
                {/* userSpaceOnUse is MANDATORY: a horizontal <line> has a
                    zero-height bbox, and an objectBoundingBox gradient on a
                    zero-height bbox makes the element not render at all. */}
                <linearGradient
                  id="og-rule"
                  gradientUnits="userSpaceOnUse"
                  x1={0}
                  y1={0}
                  x2={ROW_W}
                  y2={0}
                >
                  <stop offset="0%" stopColor={accent} />
                  <stop offset="55%" stopColor={ruleColorMid} />
                  <stop offset="100%" stopColor={accent2} />
                </linearGradient>
              </defs>
              {/* the bed distilled into a straight line — the gradient is spatially
                  fixed and the dash reveals it, so colour arrives positionally. */}
              <line
                x1={ruleW / 2}
                y1={6}
                x2={ROW_W - ruleW / 2}
                y2={6}
                stroke="url(#og-rule)"
                strokeWidth={ruleW}
                strokeLinecap="round"
                strokeDasharray={ROW_W - ruleW}
                strokeDashoffset={(ROW_W - ruleW) * (1 - ruleE)}
              />
            </svg>
          )}

          {/* hairline rows — no pills; each row now DRAWS its own hairline, and
              the line leads its text in (starts ~0.04s before, completes ~0.06-0.08s
              before the text settles). Row timings themselves are UNCHANGED. */}
          <div style={{ position: "absolute", left: PAD, right: PAD, bottom: PAD }}>
            <Row label={commentLabel} value={commentValue} color={accent2} d={0.5} p={h1P} />
            <Row label={subscribeLabel} value={subscribeValue} color={accent} d={0.62} p={h2P} />
          </div>
        </div>
      </div>

      {/* tagline under the glass */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: PY + PH + 34,
          textAlign: "center",
          fontSize: 30,
          letterSpacing: 1,
          color: rgba(BRAND.paper, 0.55),
          opacity: rowIn(0.78) * clamp(pOut),
        }}
      >
        {tagline}
      </div>
    </AbsoluteFill>
  );
};

export const outroGlassDemo: OutroGlassProps = {
  eyebrow: "BEFORE YOU GO",
  question: "What should I build|with one line next?",
  commentLabel: "Drop it in the comments",
  commentValue: "↳",
  subscribeLabel: "Subscribe",
  subscribeValue: "ONE / DAY",
  tagline: "one AI trick, every single day",
  avatar: "assets/character/host_library/outfit_11_sol_magenta/cropeed_center_final.jpeg",
};
