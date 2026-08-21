import React from "react";
import {
  AbsoluteFill,
  Easing,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {
  BRAND, SANS, MONO, DISPLAY, rgba, clamp, Fonts, AuroraBed, SAFE,
} from "./kit";

/* =============================================================================
   CaseBullets — the sentences you actually write down.

   The second half of the self-appraisal short. CareerArc ends holding a rising
   arc; this picks it up, shrinks it to a header, and extrudes a written line
   from each node — the literal words that go in the form.

   IT MUST READ AS SPEECH, NEVER AS DATA. That distinction is the whole design.
   A part-of-whole bar or a slamming counter carries MEASUREMENT grammar, and
   muted at 2x the picture IS the claim — which is what killed three concepts on
   2026-08-21. These are quotation cards: left-aligned prose, quote marks, a
   speech-coloured edge bar, no alignment to any axis, no figures typeset as
   figures. The numbers inside a sentence ("six days to two") are the VIEWER'S
   OWN words, spoken in a sentence, not a readout.

   THE HOLD PROBLEM THIS SOLVES. Prose at 2x on mute is unreadable texture, and
   this beat is 15 seconds — by far the longest in the film. A static stack of
   paragraphs would be a dead frame at exactly the length where dead frames cost
   most. So the cards do not fade in: each one is PULLED from its arc node along
   a visible tether, and the node dims as the sentence takes its place. The eye
   always has one thing travelling, and the travel says "this became that".

   Authored for 1080x1920. SAFE.headerFloor (132) owns the top; the caption band
   owns from y=1380 down, so cards must finish above it.
   ========================================================================== */

const M = 84;                    // left margin, shared with CareerArc's plot
const R = 996;
const ARC_TOP = 300;             // the arc, demoted to a header strip
const ARC_BASE = 470;
const CARD_X = 76;
const CARD_W = 928;
const CARD_MIN_H = 148;
const FIRST_Y = 560;
const GAP = 26;

const OUT = Easing.bezier(0.16, 1, 0.3, 1);

export type CaseLine = {
  /** the sentence, as it would be written. Quote marks are drawn, not typed. */
  text: string;
  /** which arc node it is pulled from, 0-indexed. */
  from?: number;
  /** beat-local second the pull starts. */
  at: number;
};

export type CaseBulletsProps = {
  lines: CaseLine[];
  /** the arc carried over from CareerArc, so the two beats are continuous. */
  points?: { lift: number }[];
  runLabel?: string;
  /** small mono label under the stack. */
  footNote?: string;
  /** Beat-local second a slow read-sweep starts after the cards have landed.
   *  THIS BEAT IS 15s AND THE CARDS LAND IN THE FIRST 7 — without a tail the
   *  frame is static for eight seconds, which is the measured retention killer.
   *  The sweep re-lights each card in reading order, so the eye always has one
   *  thing to follow and the viewer is being PACED through the sentences rather
   *  than left staring at a finished stack. */
  sweepFrom?: number;
  /** seconds per card in the sweep. */
  sweepStep?: number;
  /** Sol's wide clip as a card. The upper frame is mostly empty once the arc is
   *  demoted, so the host belongs up there rather than in a busy corner. */
  host?: string;
  hostSize?: number;
  hostAnchor?: "tl" | "tr";
  hostFrom?: number;
  accent?: string;
  ink?: string;
  transparent?: boolean;
  start?: number;
  width?: number;
  height?: number;
};

export const CaseBullets: React.FC<CaseBulletsProps> = ({
  lines = [],
  points = [],
  runLabel,
  footNote,
  sweepFrom,
  sweepStep = 1.9,
  host,
  hostSize = 420,
  hostAnchor = "tr",
  hostFrom = 0,
  accent = BRAND.mag,
  ink = BRAND.ink,
  transparent,
  start = 0,
  width = 1080,
  height = 1920,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - start;
  const L = (lines || []).slice(0, 4);
  const P = points.length ? points : L.map((_, i) => ({ lift: (i + 1) / (L.length + 1) }));
  const n = Math.max(P.length, 1);

  const nodeX = (i: number) => M + ((R - M) * (i + 0.6)) / (n + 0.2);
  const nodeY = (i: number) => ARC_BASE - (ARC_BASE - ARC_TOP) * clamp(P[i]?.lift ?? 0.5);
  const arcPath = P.map((_, i) => `${i ? "L" : "M"}${nodeX(i)} ${nodeY(i)}`).join(" ");

  // stack the cards, measuring each so a long sentence does not overlap the next
  const heights = L.map((l) => Math.max(CARD_MIN_H, 96 + Math.ceil(l.text.length / 34) * 52));
  const cardY = (i: number) => FIRST_Y + heights.slice(0, i).reduce((a, b) => a + b + GAP, 0);

  return (
    <AbsoluteFill style={{ width, height, background: transparent ? undefined : ink }}>
      <Fonts />
      {transparent ? null : <AuroraBed t={t} accent={accent} ink={ink} opacity={0.3} />}

      {runLabel ? (
        <div style={{
          position: "absolute", left: M, top: SAFE.headerFloor + 46,
          fontFamily: MONO, fontSize: 25, letterSpacing: 6,
          color: rgba(BRAND.paper, 0.4),
        }}>{runLabel}</div>
      ) : null}

      <svg width={width} height={height} style={{ position: "absolute", inset: 0 }}>
        <defs>
          <linearGradient id="cb-arc" x1="0" y1="1" x2="1" y2="0">
            <stop offset="0%" stopColor={accent} />
            <stop offset="100%" stopColor="#FFC2E4" />
          </linearGradient>
          <filter id="cb-glow" x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="8" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {/* the arc, carried over and demoted — continuity with the previous beat */}
        <path d={arcPath} stroke="url(#cb-arc)" strokeWidth={8} fill="none"
              strokeLinecap="round" strokeLinejoin="round" opacity={0.7} />

        {L.map((l, i) => {
          const src = l.from ?? i;
          const pull = clamp((t - l.at) / 0.42);
          if (pull <= 0) return null;
          const e = OUT(pull);
          const x0 = nodeX(src), y0 = nodeY(src);
          const y1 = cardY(i) + 30;
          // the tether: the sentence is visibly PULLED from its node, so the eye
          // always has one thing travelling through a 15-second beat
          return (
            <g key={`t${i}`} opacity={(1 - pull) * 0.85}>
              <line x1={x0} y1={y0} x2={x0} y2={y0 + (y1 - y0) * e}
                    stroke={accent} strokeWidth={3} strokeLinecap="round" />
            </g>
          );
        })}

        {P.map((_, i) => {
          // a node dims once its sentence has landed — "this became that"
          const owner = L.find((l, k) => (l.from ?? k) === i);
          const spent = owner ? clamp((t - owner.at - 0.42) / 0.3) : 0;
          return (
            <circle key={`n${i}`} cx={nodeX(i)} cy={nodeY(i)} r={13 - spent * 4}
                    fill="#FFFFFF" opacity={1 - spent * 0.62} filter="url(#cb-glow)" />
          );
        })}
      </svg>

      {L.map((l, i) => {
        const sp = spring({
          frame: frame - Math.round((start + l.at + 0.28) * fps),
          fps, config: { damping: 18, stiffness: 165, mass: 0.85 },
        });
        if (sp <= 0.001) return null;
        const y = cardY(i);
        const h = heights[i];
        // the read-sweep: a card lifts and its edge brightens as the eye is
        // walked down the stack, then hands off to the next
        const sw = sweepFrom == null ? 0
          : clamp(1 - Math.abs(t - (sweepFrom + i * sweepStep)) / (sweepStep * 0.62));
        const lift = OUT(sw);
        return (
          <div key={i} style={{
            position: "absolute", left: CARD_X, top: y, width: CARD_W, height: h,
            opacity: sp,
            transform: `translateY(${(1 - sp) * -26 - lift * 9}px) scale(${0.97 + sp * 0.03 + lift * 0.012})`,
            borderRadius: 22, overflow: "hidden",
            background: `linear-gradient(180deg, ${rgba("#ffffff", 0.075 + lift * 0.05)} 0%, ${rgba("#ffffff", 0.022 + lift * 0.03)} 100%)`,
            border: `1px solid ${rgba("#ffffff", 0.16 + lift * 0.22)}`,
            boxShadow: `0 ${26 + lift * 14}px ${60 + lift * 26}px -30px ${rgba("#000", 0.85)}`,
            display: "flex", alignItems: "center",
          }}>
            {/* a SPEECH-coloured edge, not a data colour — these are words said
                out loud, and the cyan reads as voice against the magenta arc */}
            <div style={{
              position: "absolute", left: 0, top: 0, width: 6 + lift * 3, height: "100%",
              background: BRAND.cyan,
              boxShadow: lift > 0.02 ? `0 0 ${lift * 26}px ${rgba(BRAND.cyan, lift * 0.9)}` : undefined,
            }} />
            <div style={{
              position: "absolute", left: 34, top: 18, fontFamily: DISPLAY,
              fontSize: 64, lineHeight: "50px", color: rgba(BRAND.cyan, 0.32),
            }}>&ldquo;</div>
            <div style={{
              paddingLeft: 84, paddingRight: 44,
              fontFamily: SANS, fontSize: 44, fontWeight: 600, lineHeight: "58px",
              color: BRAND.paper, letterSpacing: -0.2,
            }}>{l.text}</div>
          </div>
        );
      })}

      {footNote ? (
        <div style={{
          position: "absolute", left: M, top: cardY(L.length) + 8,
          fontFamily: MONO, fontSize: 25, letterSpacing: 5,
          color: rgba(BRAND.paper, 0.4),
        }}>{footNote}</div>
      ) : null}

      {host ? (
        <div style={{
          position: "absolute",
          [hostAnchor === "tl" ? "left" : "right"]: 64,
          top: SAFE.headerFloor + 26,
          width: hostSize, height: Math.round(hostSize * 0.5625),
          borderRadius: 18, overflow: "hidden",
          border: `1px solid ${rgba("#ffffff", 0.18)}`,
          boxShadow: `0 22px 54px -26px ${rgba("#000", 0.9)}`,
        } as React.CSSProperties}>
          <video src={host} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

/* ---- canonical demo ------------------------------------------------------ */
export const caseBulletsDemo: CaseBulletsProps = {
  runLabel: "WHAT YOU ACTUALLY WRITE",
  points: [{ lift: 0.26 }, { lift: 0.48 }, { lift: 0.66 }, { lift: 0.86 }],
  lines: [
    { text: "I cut onboarding from six days to two.", from: 0, at: 0.5 },
    { text: "I took the on-call rota in March and kept it.", from: 1, at: 2.2 },
    { text: "I shipped billing with no rollback.", from: 2, at: 3.9 },
    { text: "I trained two juniors who now run releases.", from: 3, at: 5.6 },
  ],
  footNote: "PASTE THESE STRAIGHT IN",
  sweepFrom: 7.2,
  sweepStep: 1.9,
};
