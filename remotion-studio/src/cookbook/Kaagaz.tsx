import React from "react";
import { AbsoluteFill, staticFile, useVideoConfig } from "remotion";
import { rgba } from "./kit";
import { clamp01, mhash, vnoise1, OUT_E, settle } from "./motion";
import { useFilmT } from "./filmclock";

/* =============================================================================
   Kaagaz — the paper world, and its first CHARACTER.

   VJ's redirect, verbatim: "for each episode we will try to have different
   worlds which best suits the content and the vo script — no repeated box
   corals message assets we created for ep1." The lock model changes: a world
   belongs to an EPISODE, chosen at design time; CLAYLIGHT was ep1's world,
   this is the paper world the reference frames he sent live in — warm cream
   ground, faint blueprint watermark, chunky serif that speaks in italics, and
   paper-cut characters with real eyes.

   THE OCTOPUS. The reference that impressed him is a paper-cut octopus
   representing the AI — arms as capabilities, eyes that glare. A flat sprite
   cannot do that, so OctoPuppet is a VECTOR PUPPET:
   - each arm is a chain of 14 segments whose bend integrates a curl profile —
     arms genuinely CURL, wave, point and burst, deterministically;
   - the body is a wobble-edged paper disc with a cut-paper drop shadow;
   - the eyes blink on a deterministic schedule, look where told, and carry a
     MOOD (calm / glare — the angry lids of the reference frame).
   Every motion is a pure function of the film clock. No rigs, no libraries.
   ========================================================================== */

export const PAPER = {
  ground: "#EFE7DA",       // warm cream, the reference's wall
  ink: "#2E2A26",          // near-black warm ink
  coral: "#E8825A",        // the paper-cut orange of the reference character
  coralDeep: "#D96C42",
  green: "#3E6B5C",        // the reference's deep green (pills, italic words)
  greenSoft: "#7FA692",
  shadow: "rgba(60,45,30,0.18)",
} as const;

export const FRAUNCES = '"Fraunces", "Georgia", serif';
export const FRAUNCES_IT = '"Fraunces Italic", "Fraunces", Georgia, serif';

export const PaperFonts: React.FC = () => (
  <style>{`
    @font-face { font-family: 'Fraunces'; src: url('${staticFile("fonts/Fraunces.ttf")}'); font-weight: 300 900; }
    @font-face { font-family: 'Fraunces Italic'; src: url('${staticFile("fonts/Fraunces-Italic.ttf")}'); font-weight: 300 900; font-style: italic; }
  `}</style>
);

/* ---- THE STAGE ------------------------------------------------------------ */
export const PaperStage: React.FC<{
  /** faint blueprint watermark behind everything, like the reference. */
  watermark?: boolean;
  children?: React.ReactNode;
}> = ({ watermark = true, children }) => {
  const t = useFilmT();
  return (
    <AbsoluteFill style={{ background: PAPER.ground }}>
      <PaperFonts />
      {/* soft top-light gradient — paper under a window, not a void */}
      <div style={{
        position: "absolute", inset: 0,
        background: `linear-gradient(178deg, ${rgba("#FFFFFF", 0.5)} 0%, ${rgba("#FFFFFF", 0)} 30%, ${rgba("#B8A88F", 0.16)} 100%)`,
      }} />
      {watermark ? (
        <svg width="1080" height="1920" style={{ position: "absolute", inset: 0, opacity: 0.05 }}>
          {[[240, 420, 150], [820, 300, 90], [640, 1100, 210], [180, 1500, 120], [900, 1660, 140]].map(([cx, cy, r], i) => (
            <g key={i} stroke={PAPER.ink} fill="none" strokeWidth={1.5}>
              <circle cx={cx} cy={cy} r={r} />
              <circle cx={cx} cy={cy} r={r * 0.62} strokeDasharray="6 8" />
              <line x1={cx - r} y1={cy} x2={cx + r} y2={cy} />
            </g>
          ))}
        </svg>
      ) : null}
      {children}
      {/* paper grain — barely there */}
      <svg style={{ position: "absolute", inset: 0, opacity: 0.05, mixBlendMode: "multiply", pointerEvents: "none" }}>
        <filter id="paper-grain">
          <feTurbulence type="fractalNoise" baseFrequency="0.7" numOctaves="2" seed={4} />
        </filter>
        <rect width="100%" height="100%" filter="url(#paper-grain)" />
      </svg>
    </AbsoluteFill>
  );
};

/* ---- THE PUPPET ----------------------------------------------------------- */
export type ArmPose = {
  /** 0 = hang loose, 1 = full curl inward, -1 = flared back. */
  curl?: number;
  /** arm length multiplier (reach). */
  reach?: number;
  /** extra base-angle swing in degrees. */
  swing?: number;
};

export type OctoPose = {
  /** film-absolute second this pose is REACHED (eased from the previous). */
  t: number;
  /** per-arm overrides; missing arms interpolate the `all` pose. */
  all?: ArmPose;
  arms?: Record<number, ArmPose>;
  /** eye mood + gaze. */
  mood?: "calm" | "glare" | "wide";
  lookX?: number;            // -1..1
  lookY?: number;
  /** body position + scale in frame coords. */
  x?: number;
  y?: number;
  s?: number;
  tilt?: number;             // degrees
};

export type OctoPuppetProps = {
  poses: OctoPose[];
  armCount?: number;
  color?: string;
  /** deterministic entrance: scale-pop at this second; omit = always there. */
  enterAt?: number;
  seed?: number;
  zIndex?: number;
};

const SEGS = 14;

export const OctoPuppet: React.FC<OctoPuppetProps> = ({
  poses,
  armCount = 10,
  color = PAPER.coral,
  enterAt,
  seed = 0,
  zIndex,
}) => {
  const t = useFilmT();
  const { fps } = useVideoConfig();

  /* pose interpolation */
  const lerp = (a: number, b: number, p: number) => a + (b - a) * p;
  const poseAt = (): Required<Omit<OctoPose, "arms" | "all">> & { armPose: (i: number) => Required<ArmPose> } => {
    const def = { mood: "calm" as const, lookX: 0, lookY: 0, x: 540, y: 900, s: 1, tilt: 0 };
    let a: OctoPose = { t: -1, ...def }, b: OctoPose | null = null, p = 1;
    for (let i = 0; i < poses.length; i++) {
      if (t >= poses[i].t) a = { ...def, ...a, ...poses[i] };
      else { b = poses[i]; break; }
    }
    if (b) {
      const bb = { ...a, ...b };
      p = OUT_E(clamp01((t - a.t) / Math.max(b.t - a.t, 1e-6)));
      const armPose = (i: number): Required<ArmPose> => {
        const A = { curl: 0, reach: 1, swing: 0, ...(a.all ?? {}), ...(a.arms?.[i] ?? {}) };
        const B = { curl: 0, reach: 1, swing: 0, ...(bb.all ?? a.all ?? {}), ...(bb.arms?.[i] ?? a.arms?.[i] ?? {}) };
        return { curl: lerp(A.curl, B.curl, p), reach: lerp(A.reach, B.reach, p), swing: lerp(A.swing, B.swing, p) };
      };
      return {
        t, mood: p > 0.5 ? (bb.mood ?? a.mood ?? "calm") : (a.mood ?? "calm"),
        lookX: lerp(a.lookX ?? 0, bb.lookX ?? a.lookX ?? 0, p),
        lookY: lerp(a.lookY ?? 0, bb.lookY ?? a.lookY ?? 0, p),
        x: lerp(a.x ?? 540, bb.x ?? a.x ?? 540, p),
        y: lerp(a.y ?? 900, bb.y ?? a.y ?? 900, p),
        s: lerp(a.s ?? 1, bb.s ?? a.s ?? 1, p),
        tilt: lerp(a.tilt ?? 0, bb.tilt ?? a.tilt ?? 0, p),
        armPose,
      };
    }
    const armPose = (i: number): Required<ArmPose> =>
      ({ curl: 0, reach: 1, swing: 0, ...(a.all ?? {}), ...(a.arms?.[i] ?? {}) });
    return { t, mood: a.mood ?? "calm", lookX: a.lookX ?? 0, lookY: a.lookY ?? 0,
             x: a.x ?? 540, y: a.y ?? 900, s: a.s ?? 1, tilt: a.tilt ?? 0, armPose };
  };

  const P = poseAt();
  const enter = enterAt == null ? 1 : clamp01((t - enterAt) / 0.45);
  if (enter <= 0) return null;
  const pop = enterAt == null ? 1 : OUT_E(enter) * (1 + settle(t, enterAt + 0.45, 0.4) * 0.06);

  /* the breath every living thing needs (U1) */
  const breathe = 1 + Math.sin(t * 1.7 + seed) * 0.012;

  /* deterministic blink schedule: ~ every 2.8-3.8s, 4 frames */
  const blinkPhase = (() => {
    let bt = 0.9 + mhash(seed) * 1.2, i = 0;
    while (bt < t - 0.2 && i < 200) { bt += 2.8 + mhash(seed * 7 + i) * 1.0; i++; }
    const d = t - (bt - (2.8 + mhash(seed * 7 + Math.max(0, i - 1)) * 1.0)); // last blink time
    // simpler: find most recent blink strictly before now
    let last = 0.9 + mhash(seed) * 1.2, j = 0;
    while (true) {
      const nxt = last + 2.8 + mhash(seed * 7 + j) * 1.0;
      if (nxt > t) break;
      last = nxt; j++;
      if (j > 200) break;
    }
    const dd = t - last;
    return dd >= 0 && dd < 0.14 ? Math.sin((dd / 0.14) * Math.PI) : 0;
  })();

  const BODY_R = 132;

  /* ---- an arm: segment chain with integrated bend ---- */
  const arm = (i: number) => {
    const ap = P.armPose(i);
    const baseAng = (i / armCount) * Math.PI * 2 - Math.PI / 2 + (ap.swing * Math.PI) / 180;
    // idle life: each arm waves on its own phase, always
    const wave = Math.sin(t * 2.1 + i * 1.7 + seed) * 0.10 + Math.sin(t * 1.3 + i * 0.9) * 0.06;
    const segLen = (BODY_R * 1.62 * ap.reach) / SEGS;
    let x = Math.cos(baseAng) * BODY_R * 0.86;
    let y = Math.sin(baseAng) * BODY_R * 0.86;
    let ang = baseAng;
    const pts: [number, number][] = [[x, y]];
    for (let k = 1; k <= SEGS; k++) {
      const kf = k / SEGS;
      // curl profile grows toward the tip; wave rides on top
      const bend = ap.curl * 0.34 * kf + wave * kf * 0.55;
      ang += bend;
      x += Math.cos(ang) * segLen;
      y += Math.sin(ang) * segLen;
      pts.push([x, y]);
    }
    // build a tapered filled shape from the centreline
    const w0 = 34, w1 = 6;
    const left: string[] = [], right: string[] = [];
    for (let k = 0; k < pts.length; k++) {
      const kf = k / (pts.length - 1);
      const wHalf = (w0 + (w1 - w0) * kf) / 2;
      const [px, py] = pts[k];
      const [nx, ny] = pts[Math.min(k + 1, pts.length - 1)];
      const [bx, by] = pts[Math.max(k - 1, 0)];
      const dirA = Math.atan2(ny - by, nx - bx) + Math.PI / 2;
      left.push(`${(px + Math.cos(dirA) * wHalf).toFixed(1)},${(py + Math.sin(dirA) * wHalf).toFixed(1)}`);
      right.unshift(`${(px - Math.cos(dirA) * wHalf).toFixed(1)},${(py - Math.sin(dirA) * wHalf).toFixed(1)}`);
    }
    return `M${left.join(" L")} L${right.join(" L")} Z`;
  };

  const armPaths = Array.from({ length: armCount }, (_, i) => arm(i));

  /* ---- eyes ---- */
  const eyeY = -14 + P.lookY * 10;
  const eyeDX = 44;
  const pupilDX = P.lookX * 11;
  const lidAngle = P.mood === "glare" ? 24 : 0;
  const eyeH = (P.mood === "wide" ? 34 : 26) * (1 - blinkPhase * 0.92);

  return (
    <div style={{
      position: "absolute", left: P.x, top: P.y, zIndex,
      transform: `translate(-50%, -50%) rotate(${P.tilt.toFixed(1)}deg) scale(${(P.s * pop * breathe).toFixed(3)})`,
    }}>
      <svg width={900} height={900} viewBox="-450 -450 900 900" style={{ display: "block", overflow: "visible" }}>
        {/* cut-paper drop shadow: the whole puppet, offset — depth without light */}
        <g transform="translate(7 12)" opacity={0.9}>
          {armPaths.map((d, i) => <path key={`s${i}`} d={d} fill={PAPER.shadow} />)}
          <circle r={BODY_R} fill={PAPER.shadow} />
        </g>
        {armPaths.map((d, i) => (
          <path key={i} d={d} fill={i % 2 ? color : PAPER.coralDeep} />
        ))}
        <circle r={BODY_R} fill={color} />
        {/* a paper highlight edge on the body */}
        <circle r={BODY_R} fill="none" stroke={rgba("#FFFFFF", 0.35)} strokeWidth={3}
                strokeDasharray={`${BODY_R * 2.2} ${BODY_R * 5}`} transform="rotate(-118)" />
        {/* eyes */}
        {[-1, 1].map((sgn) => (
          <g key={sgn} transform={`translate(${sgn * eyeDX} ${eyeY})`}>
            <ellipse rx={20} ry={Math.max(1.6, eyeH)} fill="#FFF8EE" />
            <circle cx={pupilDX} cy={0} r={Math.min(8.5, eyeH * 0.5)} fill={PAPER.ink} />
            {lidAngle ? (
              <rect x={-24} y={-30} width={48} height={22} fill={color}
                    transform={`rotate(${sgn * lidAngle})`} />
            ) : null}
          </g>
        ))}
      </svg>
    </div>
  );
};

/* ---- kinetic serif: the reference's talking typography -------------------- */
export const PaperWord: React.FC<{
  parts: { text: string; italic?: boolean; color?: string }[];
  at: number;
  until?: number;
  x?: number;
  y?: number;
  size?: number;
  align?: "left" | "center";
}> = ({ parts, at, until, x = 540, y = 760, size = 96, align = "center" }) => {
  const t = useFilmT();
  if (t < at || (until != null && t > until)) return null;
  return (
    <div style={{
      position: "absolute", left: align === "center" ? 0 : x, right: align === "center" ? 0 : undefined,
      top: y, textAlign: align, zIndex: 20, padding: "0 60px",
    }}>
      {parts.map((p, i) => {
        const on = OUT_E(clamp01((t - at - i * 0.09) / 0.3));
        return (
          <span key={i} style={{
            display: "inline-block",
            fontFamily: p.italic ? FRAUNCES_IT : FRAUNCES,
            fontStyle: p.italic ? "italic" : undefined,
            fontWeight: 800, fontSize: size, lineHeight: 1.06,
            color: p.color ?? PAPER.ink,
            opacity: Math.min(1, on * 1.5),
            transform: `translateY(${(1 - on) * 46}px) rotate(${(1 - on) * (i % 2 ? 3 : -3)}deg)`,
            marginRight: size * 0.22,
            textShadow: `2px 3px 0 ${rgba("#B8A88F", 0.35)}`,
          }}>{p.text}</span>
        );
      })}
    </div>
  );
};
