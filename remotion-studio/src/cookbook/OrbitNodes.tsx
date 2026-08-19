import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BRAND, SANS, DISPLAY, rgba, clamp, coverBg, Fonts } from "./kit";

/* =============================================================================
   OrbitNodes — one glowing hub, many feature nodes on a slow-turning ring.
   -----------------------------------------------------------------------------
   Cookbook role: the invented SPATIAL wow — an *ecosystem / constellation*.
   Where LineReveal is the trend form and BentoGrid is the grid form, this is the
   RADIAL form: "one input → many outputs", "one tool, N powers", "a hub and its
   satellites". It reads a whole relationship in a single glance, which is exactly
   what a 15s hook beat needs (e.g. ONE PROMPT that can summarize / translate /
   write code / draft email / make slides / plan).

   The beat it plays:
     1. the hub chip pops in and lights a soft radial glow (the source);
     2. connector lines DRAW OUTWARD from the hub to each ring slot, staggered,
        a bright "packet" riding each drawing tip (the flow of the one input);
     3. as each line lands, its node chip EMERGES from the hub and springs into
        its slot (the many outputs materialising);
     4. the whole constellation then drifts in a very slow rotation — alive, not
        looping — and HOLDS with every node visible, so a still near the end
        shows the finished ecosystem.

   Why this layout / the anti-clip math (all figures at the 1080×1920 design box,
   uniformly scaled by s = width/1080 so the guarantees hold at any size):
     • centre is (width/2, height/2) ⇒ the constellation is balanced on y≈960,
       clear of both the top and the reserved bottom caption band (y>1517);
     • nodes sit on a ring of radius R=324·s; each chip is a pill capped at
       maxWidth 256·s, so its half-extent never exceeds 128·s. Because the ring
       rotates, EVERY node eventually passes the 3-o'clock slot, so we size for
       that worst case: outer edge = width/2 + 324·s + 128·s = 992·s ≤ (width−72·s)
       = 1008·s, and symmetrically ≥ 72·s on the left — a hard no-clip on x for
       any rotation angle. Vertically the lowest a chip reaches is
       height/2 + 324·s + 38·s = 1322 at 1920, well above the 1517 caption line.
     • Labels stay upright by CONSTRUCTION: node positions are computed in polar
       math and each pill is an un-rotated element, so we get the "counter-rotate
       the text" result without any transform that could re-introduce clipping.

   JSON-safe (build_ep_v2 feeds --props as JSON): hub/nodes are plain objects of
   strings; timing/appearance chosen via numbers, colours via `accent`. No fn
   props. Nodes are capped at 6 so the ring never crowds or overflows.
   ========================================================================== */

export type OrbitNodesProps = {
  hub: { label: string; icon?: string }; // the centre — DISPLAY label, optional glyph
  nodes: { label: string; icon?: string }[]; // ring satellites — capped at 6
  accent?: string; // hub + lines + accents (default brand magenta)
  ink?: string; // backdrop base
  start?: number; // seconds before the reveal begins (default 0.3)
  spin?: number; // ring drift, degrees/second (default 3 — VERY slow)
  width?: number;
  height?: number;
  transparent?: boolean; // skip the backdrop (overlay use)
};

const easeOutCubic = (x: number): number => 1 - Math.pow(1 - x, 3);

/* deterministic faint star specks (fractions of the frame) — a constellation
   whisper behind the ring; fixed so stills are reproducible, kept low-alpha and
   away from where the chips land. */
const STARS: Array<[number, number, number]> = [
  [0.14, 0.16, 2.4], [0.86, 0.12, 1.8], [0.22, 0.83, 2.0], [0.78, 0.86, 2.6],
  [0.5, 0.08, 1.6], [0.1, 0.5, 1.7], [0.9, 0.52, 2.1], [0.34, 0.1, 1.5],
  [0.66, 0.9, 1.9], [0.5, 0.93, 1.6], [0.08, 0.72, 1.4], [0.92, 0.74, 1.5],
];

export const OrbitNodes: React.FC<OrbitNodesProps> = ({
  hub,
  nodes,
  accent = BRAND.mag,
  ink = BRAND.ink,
  start = 0.3,
  spin = 3,
  width = 1080,
  height = 1920,
  transparent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const s = width / 1080; // uniform scale — every px below is authored at s=1
  const cx = width / 2;
  const cy = height / 2;
  const t = frame / fps; // absolute seconds
  const tl = t - start; // seconds since the reveal began

  // ---- geometry (see header for the no-clip derivation) --------------------
  const R = 324 * s; // ring radius (node CENTRES sit here)
  const PILL_MAXW = 256 * s; // ⇒ half-extent ≤ 128·s ⇒ x stays in [72·s, 1008·s]
  const PILL_H = 76 * s;
  const items = nodes.slice(0, 6); // hard cap — the ring never crowds
  const n = items.length;
  const step = n > 0 ? 360 / n : 360;
  const spinDeg = spin * Math.max(0, tl); // continuous, very slow drift

  // ---- hub reveal ----------------------------------------------------------
  const hubSp = spring({
    frame: frame - Math.round(start * fps),
    fps,
    config: { damping: 14, mass: 0.9, stiffness: 120 },
  });
  const hubScale = interpolate(hubSp, [0, 1], [0.6, 1]); // pops in
  const breathe = 1 + 0.03 * Math.sin(t * 1.6); // living glow
  const glowIn = clamp(tl / 0.5);
  const ringIn = clamp((tl - 0.05) / 0.6); // faint orbit guide fades up

  // pre-compute each node's line-draw progress, pop spring, and slot point
  const rendered = items.map((it, i) => {
    const lineStart = start + 0.3 + i * 0.1;
    const g = easeOutCubic(clamp((t - lineStart) / 0.55)); // 0→1 line growth
    const sp = spring({
      frame: frame - Math.round((lineStart + 0.4) * fps),
      fps,
      config: { damping: 13, mass: 0.8, stiffness: 140 },
    });
    const ang = (-90 + i * step + spinDeg) * (Math.PI / 180);
    const dx = Math.cos(ang);
    const dy = Math.sin(ang);
    // line always targets the full slot; the node EMERGES from 0.85R → R
    const fullX = cx + R * dx;
    const fullY = cy + R * dy;
    const effR = R * interpolate(clamp(sp), [0, 1], [0.85, 1]);
    return {
      it,
      i,
      g,
      dx,
      dy,
      fullX,
      fullY,
      tipX: cx + g * (fullX - cx),
      tipY: cy + g * (fullY - cy),
      nodeX: cx + effR * dx,
      nodeY: cy + effR * dy,
      scale: interpolate(sp, [0, 1], [0.5, 1]), // spring overshoot → crisp pop
      op: clamp(sp * 1.5),
    };
  });

  return (
    <AbsoluteFill
      style={{
        background: transparent ? undefined : coverBg(accent, ink),
        fontFamily: SANS,
        overflow: "hidden",
      }}
    >
      <Fonts />

      {/* faint star specks — constellation whisper */}
      {STARS.map(([fx, fy, r], i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: fx * width,
            top: fy * height,
            width: r * 2 * s,
            height: r * 2 * s,
            borderRadius: "50%",
            background: rgba(BRAND.paper, 0.5),
            opacity: 0.16 * glowIn,
            filter: `blur(${0.5 * s}px)`,
          }}
        />
      ))}

      {/* soft radial glow behind the hub (the source) */}
      <div
        style={{
          position: "absolute",
          left: cx,
          top: cy,
          width: 760 * s,
          height: 760 * s,
          transform: `translate(-50%,-50%) scale(${breathe})`,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${rgba(accent, 0.42)} 0%, ${rgba(
            accent,
            0.12
          )} 34%, ${rgba(accent, 0)} 66%)`,
          opacity: glowIn,
          pointerEvents: "none",
        }}
      />

      {/* orbit ring + connector lines + travelling packets */}
      <svg
        width={width}
        height={height}
        style={{ position: "absolute", inset: 0 }}
      >
        {/* faint orbit guide — the ring the powers live on */}
        <circle
          cx={cx}
          cy={cy}
          r={R}
          fill="none"
          stroke={rgba(accent, 0.16)}
          strokeWidth={2 * s}
          strokeDasharray={`${2 * s} ${12 * s}`}
          opacity={ringIn}
        />

        {/* connector lines — drawn outward from the hub, glowing */}
        <g
          style={{
            filter: `drop-shadow(0 0 ${8 * s}px ${rgba(accent, 0.5)})`,
          }}
        >
          {rendered.map((r) =>
            r.g > 0.001 ? (
              <line
                key={r.i}
                x1={cx}
                y1={cy}
                x2={r.tipX}
                y2={r.tipY}
                stroke={rgba(accent, 0.55)}
                strokeWidth={4.5 * s}
                strokeLinecap="round"
              />
            ) : null
          )}
        </g>

        {/* packet riding each drawing tip — the input flowing out */}
        {rendered.map((r) =>
          r.g > 0.001 && r.g < 0.999 ? (
            <g key={`p${r.i}`}>
              <circle cx={r.tipX} cy={r.tipY} r={20 * s} fill={rgba(accent, 0.35)} />
              <circle
                cx={r.tipX}
                cy={r.tipY}
                r={9 * s}
                fill={BRAND.paper}
                stroke={accent}
                strokeWidth={3 * s}
              />
            </g>
          ) : null
        )}
      </svg>

      {/* node pills — capped width, upright by construction (no counter-rotate) */}
      {rendered.map((r) => (
        <div
          key={`n${r.i}`}
          style={{
            position: "absolute",
            left: r.nodeX,
            top: r.nodeY,
            transform: `translate(-50%,-50%) scale(${r.scale})`,
            opacity: r.op,
            display: "flex",
            alignItems: "center",
            gap: 12 * s,
            maxWidth: PILL_MAXW,
            height: PILL_H,
            padding: `0 ${22 * s}px`,
            borderRadius: PILL_H / 2,
            boxSizing: "border-box",
            background: `linear-gradient(180deg, ${rgba(BRAND.paper, 0.09)} 0%, ${rgba(
              BRAND.paper,
              0.03
            )} 100%)`,
            border: `${1.5 * s}px solid ${rgba(BRAND.paper, 0.16)}`,
            boxShadow: `0 ${10 * s}px ${28 * s}px ${rgba(ink, 0.5)}, inset 0 ${1 * s}px 0 ${rgba(
              BRAND.paper,
              0.14
            )}`,
            backdropFilter: "blur(6px)",
          }}
        >
          {/* connector port / marker — a live accent dot */}
          <div
            style={{
              flex: "none",
              width: r.it.icon ? 30 * s : 12 * s,
              height: r.it.icon ? 30 * s : 12 * s,
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 18 * s,
              color: BRAND.paper,
              background: accent,
              boxShadow: `0 0 ${12 * s}px ${rgba(accent, 0.8)}`,
            }}
          >
            {r.it.icon ?? ""}
          </div>
          <span
            style={{
              minWidth: 0, // flex item must be allowed to shrink or ellipsis never engages → label overflows the pill's maxWidth
              fontSize: 30 * s,
              fontWeight: 700,
              letterSpacing: 0.2,
              color: BRAND.paper,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {r.it.label}
          </span>
        </div>
      ))}

      {/* the hub chip — glowing magenta core, DISPLAY label + drawn spark */}
      <div
        style={{
          position: "absolute",
          left: cx,
          top: cy,
          transform: `translate(-50%,-50%) scale(${hubScale})`,
          opacity: clamp(hubSp * 1.4),
          display: "flex",
          alignItems: "center",
          gap: 14 * s,
          // sized to content (never truncated); half-width ≈ 166·s stays clear of
          // the nearest node's inner edge (R − 128·s = 196·s) with room to spare,
          // and nowhere near the frame edges since the hub is centred.
          padding: `${22 * s}px ${26 * s}px`,
          borderRadius: 30 * s,
          boxSizing: "border-box",
          background: `linear-gradient(155deg, ${accent} 0%, ${rgba(accent, 0.82)} 55%, #A0155F 100%)`,
          border: `${2 * s}px solid ${rgba(BRAND.paper, 0.35)}`,
          boxShadow: `0 0 ${60 * s * breathe}px ${rgba(accent, 0.65)}, 0 ${16 * s}px ${40 * s}px ${rgba(
            ink,
            0.6
          )}, inset 0 ${2 * s}px 0 ${rgba(BRAND.paper, 0.35)}`,
        }}
      >
        {hub.icon ? (
          <span style={{ fontSize: 40 * s, lineHeight: 1, color: BRAND.paper }}>
            {hub.icon}
          </span>
        ) : (
          // drawn 4-point spark — always renders (no emoji font dependency)
          <svg width={38 * s} height={38 * s} viewBox="0 0 40 40" style={{ flex: "none" }}>
            <path
              d="M20 2 L24 16 L38 20 L24 24 L20 38 L16 24 L2 20 L16 16 Z"
              fill={BRAND.paper}
              opacity={0.95}
            />
          </svg>
        )}
        <span
          style={{
            fontFamily: DISPLAY,
            fontSize: 46 * s,
            lineHeight: 1,
            letterSpacing: 1,
            color: BRAND.paper,
            textTransform: "uppercase",
            whiteSpace: "nowrap",
            textShadow: `0 ${4 * s}px ${18 * s}px ${rgba(ink, 0.5)}`,
          }}
        >
          {hub.label}
        </span>
      </div>
    </AbsoluteFill>
  );
};

export const orbitNodesDemo: OrbitNodesProps = {
  hub: { label: "One Prompt" },
  nodes: [
    { label: "Summarize" },
    { label: "Translate" },
    { label: "Write code" },
    { label: "Draft email" },
    { label: "Make slides" },
    { label: "Plan" },
  ],
};
