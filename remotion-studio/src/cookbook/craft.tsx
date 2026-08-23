import React from "react";
import { Img, staticFile, useVideoConfig, AbsoluteFill } from "remotion";
import { rgba } from "./kit";
import { clamp01, smear, settle, idle, OUT_E, IN_E, mhash } from "./motion";
import { useFilmT } from "./filmclock";

/* =============================================================================
   craft.tsx — the Ravie-tier animation vocabulary.

   VJ's level-up demand: "animation motion to graphics like the references."
   The reference craft laws (C1-C4) were deferred at launch; these four
   primitives make them buildable properties instead of aspirations:

   - TravelSprite  : C3 physics acting as a COMPONENT. A sprite following a
                     keyframed path automatically gets anticipation before
                     departures, velocity smear during travel, apex hang on
                     ballistic arcs, and squash+overshoot on every arrival.
                     The choreographer writes WHERE and WHEN; mass is free.
   - MorphSwap     : C2's transformation for FLAT sprites. A true morph is
                     impossible with stills, so this is the Ravie fake, timed
                     off their films: the outgoing object crushes into a
                     sliver along its motion axis, one to two frames flash,
                     and the incoming object emerges from the sliver with
                     overshoot. Read at speed, one thing BECAME the other.
   - ExposureScore : C1 as a system. Luminance is keyframed like music —
                     the world dims into near-black breaths between stations
                     and blooms on hits. Wraps the WORLD, never the chips.
   - FlashCut      : the 1-2 frame punctuation mark (smartwater's flicker,
                     Anthem's palette pops). Harder and shorter than
                     WhiteoutBloom; use where a beat lands, never decoratively.

   Everything reads useFilmT(), so it is Sequence-safe by construction.
   ========================================================================== */

/* ---- TravelSprite --------------------------------------------------------- */
export type PathKey = {
  /** film-absolute second this key is REACHED. */
  t: number;
  x: number;
  y: number;
  /** hold = arrive then sit (settle fires); pass = move through smoothly;
   *  ballistic = the segment INTO this key is a gravity arc with apex hang. */
  mode?: "hold" | "pass" | "ballistic";
};

export type TravelSpriteProps = {
  src: string;
  aspect: number;
  h: number;
  path: PathKey[];
  /** frames of lean-away before each departure from a hold. */
  anticipateFrames?: number;
  /** ground level for the cast shadow; omit = shadow rides the sprite. */
  groundY?: number;
  visibleFrom?: number;
  visibleTo?: number;
  seed?: number;
  zIndex?: number;
  children?: React.ReactNode;
};

const seg = (path: PathKey[], t: number) => {
  let i = 0;
  while (i < path.length - 1 && t >= path[i + 1].t) i++;
  return i;
};

export const TravelSprite: React.FC<TravelSpriteProps> = ({
  src, aspect, h, path, anticipateFrames = 6, groundY,
  visibleFrom, visibleTo, seed = 0, zIndex, children,
}) => {
  const t = useFilmT();
  const { fps } = useVideoConfig();
  if (!path.length) return null;
  if (visibleFrom != null && t < visibleFrom) return null;
  if (visibleTo != null && t > visibleTo) return null;

  const pos = (tt: number): { x: number; y: number } => {
    if (tt <= path[0].t) return { x: path[0].x, y: path[0].y };
    const last = path[path.length - 1];
    if (tt >= last.t) return { x: last.x, y: last.y };
    const i = seg(path, tt);
    const a = path[i], b = path[i + 1];
    const p = clamp01((tt - a.t) / Math.max(b.t - a.t, 1e-6));
    if (b.mode === "ballistic") {
      // gravity arc: linear x, parabolic y with the apex hang built in
      const x = a.x + (b.x - a.x) * p;
      const apexLift = Math.max(110, Math.abs(b.y - a.y) * 0.3);
      const y = a.y + (b.y - a.y) * p * p + -4 * apexLift * p * (1 - p);
      return { x, y };
    }
    const e = b.mode === "pass" ? p : OUT_E(p);
    return { x: a.x + (b.x - a.x) * e, y: a.y + (b.y - a.y) * e };
  };

  const cur = pos(t);
  const dt = 1 / fps;
  const before = pos(t - dt), after = pos(t + dt);
  const vx = (after.x - before.x) / (2 * dt);
  const vy = (after.y - before.y) / (2 * dt);
  const speed = Math.hypot(vx, vy);
  const sm = smear(speed, 500);

  // arrivals: every HOLD key fires a settle when reached
  let sq = 0;
  for (const k of path) {
    if ((k.mode ?? "hold") === "hold" && t >= k.t) sq += settle(t, k.t, 0.45);
  }
  // anticipation: lean away just before leaving a hold
  let lean = 0;
  for (let i = 0; i < path.length - 1; i++) {
    const k = path[i];
    if ((k.mode ?? "hold") !== "hold") continue;
    const departAt = path[i + 1].t - Math.max(path[i + 1].t - k.t, 0) * 0; // depart = key i time onward
    const antStart = path[i + 1].t - (path[i + 1].t - k.t) - 0; // segment starts at k.t
    const aFrames = anticipateFrames / fps;
    // the segment out of this hold starts at k.t; lean in the window BEFORE motion
    const d = t - (k.t - aFrames);
    if (d >= 0 && t < k.t + 0.02 && path[i + 1].x !== k.x) {
      const p = clamp01(d / aFrames);
      lean += Math.sin(p * Math.PI) * (path[i + 1].x > k.x ? -1 : 1) * 7;
    }
  }

  const w = h * aspect;
  const dom = Math.abs(vx) >= Math.abs(vy);
  const wob = idle(t, seed, 1.2);
  // squash: settle compresses y and bulges x (landing); smear stretches along travel
  const sx = (dom ? sm.stretch : 1 / sm.stretch) * (1 + sq * 0.07);
  const sy = (dom ? 1 / sm.stretch : sm.stretch) * (1 - sq * 0.07);

  const shadowY = groundY ?? cur.y;
  const alt = clamp01((shadowY - cur.y) / 500);

  return (
    <div style={{ position: "absolute", left: 0, top: 0, zIndex }}>
      <div style={{
        position: "absolute", left: cur.x - w * 0.45, top: shadowY - 12,
        width: w * 0.9, height: h * 0.2,
        transform: `scale(${(1 - alt * 0.45).toFixed(2)})`,
        background: `radial-gradient(50% 50% at 50% 50%, ${rgba("#000", 0.25 * (1 - alt * 0.6))} 0%, ${rgba("#000", 0)} 70%)`,
      }} />
      <div style={{
        position: "absolute", left: cur.x - w / 2, top: cur.y - h,
        width: w, height: h,
        transform: `translate(${(wob.x + lean).toFixed(1)}px, ${wob.y.toFixed(1)}px) scale(${sx.toFixed(3)}, ${sy.toFixed(3)})`,
        transformOrigin: "50% 100%",
        filter: sm.blurPx > 0.4 ? `blur(${sm.blurPx.toFixed(1)}px)` : undefined,
      }}>
        <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
        {children}
      </div>
    </div>
  );
};

/* ---- MorphSwap ------------------------------------------------------------ */
export type MorphSwapProps = {
  from: { src: string; aspect: number };
  to: { src: string; aspect: number };
  /** film-absolute second of the crush frame. */
  at: number;
  x: number;
  y: number;                 // bottom-centre, like SpriteLayer
  h: number;
  /** crush axis: "x" flattens vertically (a press), "y" flattens horizontally. */
  axis?: "x" | "y";
  flashColor?: string;
  /** the from-sprite exists only from here — without it a MorphSwap mounted
   *  alongside a TravelSprite duplicates the hero (the smoke test caught it). */
  visibleFrom?: number;
  seed?: number;
  zIndex?: number;
};

export const MorphSwap: React.FC<MorphSwapProps> = ({
  from, to, at, x, y, h, axis = "y", flashColor = "#FFE8C4", visibleFrom, seed = 0, zIndex,
}) => {
  const t = useFilmT();
  if (visibleFrom != null && t < visibleFrom) return null;
  const { fps } = useVideoConfig();
  const wob = idle(t, seed, 1.2);
  const PRE = 0.22;          // anticipation squash
  const CRUSH = 0.1;         // into the sliver
  const EMERGE = 0.3;        // out with overshoot

  const render = (spec: { src: string; aspect: number }, scaleX: number, scaleY: number, o = 1) => {
    const w = h * spec.aspect;
    return (
      <div style={{
        position: "absolute", left: x - w / 2, top: y - h, width: w, height: h,
        transform: `translate(${wob.x}px, ${wob.y}px) scale(${scaleX.toFixed(3)}, ${scaleY.toFixed(3)})`,
        transformOrigin: "50% 100%", opacity: o, zIndex,
      }}>
        <Img src={staticFile(spec.src)} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
      </div>
    );
  };

  if (t < at - PRE) return render(from, 1, 1);
  if (t < at) {
    // anticipation: gather INTO the crush — the wrong direction first, per C3
    const p = clamp01((t - (at - PRE)) / PRE);
    const g = 1 + Math.sin(p * Math.PI * 0.5) * 0.08;
    return render(from, axis === "y" ? g : 1 / g, axis === "y" ? 1 / g : g);
  }
  if (t < at + CRUSH) {
    const p = IN_E(clamp01((t - at) / CRUSH));
    const flat = 1 - p * 0.94;
    return (
      <>
        {render(from, axis === "y" ? 1 + p * 0.5 : flat, axis === "y" ? flat : 1 + p * 0.5)}
        {/* the flash lives only on the crush's last frame */}
        {t > at + CRUSH - 1.5 / fps ? (
          <AbsoluteFill style={{ background: rgba(flashColor, 0.4), zIndex: 30, pointerEvents: "none" }} />
        ) : null}
      </>
    );
  }
  const p = clamp01((t - at - CRUSH) / EMERGE);
  const e = OUT_E(p) * 1.08 - Math.max(0, p - 0.7) / 0.3 * 0.08;   // overshoot, then rest
  const flat = 0.06 + e * 0.94;
  return render(to, axis === "y" ? 1 : flat, axis === "y" ? flat : 1);
};

/* ---- ExposureScore -------------------------------------------------------- */
export const ExposureScore: React.FC<{
  /** [t, level 0..1] — 1 = full light, 0.1 = near-black breath. Interpolated. */
  keys: [number, number][];
  children?: React.ReactNode;
}> = ({ keys, children }) => {
  const t = useFilmT();
  let lv = keys.length ? keys[0][1] : 1;
  for (let i = 0; i < keys.length; i++) {
    if (t >= keys[i][0]) {
      const nxt = keys[i + 1];
      if (nxt && t < nxt[0]) {
        const p = clamp01((t - keys[i][0]) / Math.max(nxt[0] - keys[i][0], 1e-6));
        lv = keys[i][1] + (nxt[1] - keys[i][1]) * (p * p * (3 - 2 * p));
      } else lv = keys[i][1];
    }
  }
  const bright = 0.3 + lv * 0.85;
  return (
    <div style={{ position: "absolute", inset: 0, filter: `brightness(${bright.toFixed(3)})` }}>
      {children}
      {/* deep dips also close the vignette in — darkness with shape, not a fade */}
      {lv < 0.55 ? (
        <div style={{
          position: "absolute", inset: 0, pointerEvents: "none",
          background: `radial-gradient(90% 70% at 50% 50%, ${rgba("#000", 0)} 30%, ${rgba("#000", (0.55 - lv) * 1.1)} 95%)`,
        }} />
      ) : null}
    </div>
  );
};

/* ---- FlashCut ------------------------------------------------------------- */
export const FlashCut: React.FC<{
  /** film-absolute seconds; each fires a 2-frame hard flash. */
  at: number[];
  color?: string;
  opacity?: number;
}> = ({ at, color = "#FFE8C4", opacity = 0.5 }) => {
  const t = useFilmT();
  const { fps } = useVideoConfig();
  const dur = 2.4 / fps;
  const hit = at.some((a) => t >= a && t < a + dur);
  if (!hit) return null;
  return <AbsoluteFill style={{ background: rgba(color, opacity), zIndex: 32, pointerEvents: "none" }} />;
};
