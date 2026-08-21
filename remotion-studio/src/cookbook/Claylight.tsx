import React from "react";
import {
  AbsoluteFill, Img, OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { rgba, clamp } from "./kit";
import { enter, settle, idle, clamp01, mhash } from "./motion";

/* =============================================================================
   Claylight — the stage components of the CLAYLIGHT world.

   The lock is channels/claude-tricks/films/CLAYLIGHT.lock.json; this file is
   its runtime. Everything here exists to keep two promises the hit evidence
   extracted: the load-bearing pixels are VERIFIABLE REALITY (captures embedded
   with optical craft + a visible provenance strip), and the dimensional
   elements are FLUX clay sprites with one canonical angle — never promising
   rotation a flat sprite cannot render.

   Components:
   - ClayFonts   : Baloo 2 + IBM Plex Mono @font-face (public/fonts)
   - ToyStage    : espresso ground, lamplight pool, amber bind, grain, vignette
   - SpriteLayer : a library sprite on the world plane — drop-in entrance,
                   auto shadow ellipse (non-optional), lighting states, idle
   - SlabScreen  : the slab sprite with a REAL capture showing through its
                   keyed-out screen hole, light-wrap + sheen + hue spill, and
                   the provenance strip (REAL CAPTURE vs STAGED)
   - ChipClay    : the chip system in CLAYLIGHT type (Baloo 2, coral pill hot)
   - CounterClay : Plex Mono amber counter — MEASURED numbers only
   ========================================================================== */

export const CLAY = {
  ground: "#1A1214",
  pool: "#241A1C",
  cream: "#EFE3D3",
  coral: "#FF6B5E",
  amber: "#FFB454",
  mint: "#6FD5A8",
} as const;

export const BALOO = '"Baloo 2", "Baloo 2 Devanagari", "Arial Rounded MT Bold", sans-serif';
export const PLEX = '"IBM Plex Mono", "SF Mono", monospace';

export const ClayFonts: React.FC = () => (
  <style>{`
    @font-face { font-family: 'Baloo 2'; src: url('${staticFile("fonts/Baloo2-ExtraBold.ttf")}'); font-weight: 400 800; }
    @font-face { font-family: 'IBM Plex Mono'; src: url('${staticFile("fonts/IBMPlexMono-Medium.ttf")}'); font-weight: 500; }
  `}</style>
);

/* ---- THE STAGE ----------------------------------------------------------- */
export const ToyStage: React.FC<{
  /** lamplight pool centre in frame coords. */
  poolX?: number;
  poolY?: number;
  children?: React.ReactNode;
}> = ({ poolX = 540, poolY = 760, children }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: CLAY.ground }}>
      <ClayFonts />
      {/* the lamplight pool — the one light source everything pretends to share */}
      <div style={{
        position: "absolute", inset: 0,
        background: `radial-gradient(72% 46% at ${poolX / 10.8}% ${poolY / 19.2}%, ${CLAY.pool} 0%, ${rgba(CLAY.ground, 0)} 70%)`,
      }} />
      {children}
      {/* the 2% amber bind — what makes disparate sprites share one world */}
      <div style={{ position: "absolute", inset: 0, background: CLAY.amber, opacity: 0.02, pointerEvents: "none" }} />
      {/* frame-indexed grain */}
      <svg style={{ position: "absolute", inset: 0, opacity: 0.03, mixBlendMode: "overlay", pointerEvents: "none" }}>
        <filter id="clay-grain">
          <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed={(frame % 7) + 1} />
        </filter>
        <rect width="100%" height="100%" filter="url(#clay-grain)" />
      </svg>
      <div style={{
        position: "absolute", inset: 0, pointerEvents: "none",
        background: `radial-gradient(135% 100% at 50% 44%, ${rgba("#000", 0)} 52%, ${rgba("#000", 0.5)} 100%)`,
      }} />
    </AbsoluteFill>
  );
};

/* ---- A SPRITE ON THE WORLD PLANE ----------------------------------------- */
export type SpriteProps = {
  /** library path relative to public/ (e.g. "assets/claylight/library/toybox.png"). */
  src: string;
  /** world coords of the sprite's BOTTOM-CENTRE — where it stands. */
  x: number;
  y: number;
  /** rendered height in world px. Never scale a sprite past 1.4x native. */
  h: number;
  /** image aspect w/h (from the sprite's .meta.json). */
  aspect: number;
  /** film-absolute drop-in second; omit = present from frame 0. */
  enterAt?: number;
  /** film-absolute exit (falls off-world with gravity + fade). */
  exitAt?: number;
  /** "eject": rise out of a container's mouth, arc over the back rim, then
   *  fall and blur out of the lamplight — the loss, told with mass. */
  exitStyle?: "fall" | "eject";
  /** lighting state — a colour wash, never a repaint. */
  state?: "neutral" | "amber" | "mint" | "coral";
  idleAmp?: number;
  opacity?: number;
  zIndex?: number;
  seed?: number;
};

export const SpriteLayer: React.FC<SpriteProps> = ({
  src, x, y, h, aspect, enterAt, exitAt, state = "neutral",
  idleAmp = 1.6, opacity = 1, zIndex, seed = 0,
  exitStyle = "fall",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const w = h * aspect;

  // drop-in: from the camera (big + blurred) onto its mark, 8f overshoot
  const e = enterAt == null ? 1 : enter(t, enterAt, 0.34, 0.07);
  if (e <= 0.001) return null;
  const scale = enterAt == null ? 1 : 3 - 2 * Math.min(e, 1.02);
  const blur = enterAt == null ? 0 : Math.max(0, (1 - e) * 12);
  // shadow arrives 4 frames AFTER contact — mass, not decal
  const shadowIn = enterAt == null ? 1 : clamp01((t - enterAt - 0.34 - 4 / fps) / 0.2);

  // exit: leave the world with mass, not by vanishing
  let fallY = 0, fallX = 0, fallR = 0, fade = 1, fallBlur = 0;
  if (exitAt != null && t >= exitAt) {
    const d = t - exitAt;
    if (exitStyle === "eject") {
      // rise out of the mouth, hang, arc over the back rim, drop into the dark
      const rise = Math.min(d, 0.4) / 0.4;
      fallY = -240 * Math.sin(rise * Math.PI / 2);
      if (d > 0.4) {
        const dd = d - 0.4;
        fallY += 0.5 * 2400 * dd * dd;
        fallX = -150 * Math.min(dd / 0.7, 1);
        fallR = -34 * Math.min(dd, 1);
        fallBlur = Math.min(dd * 9, 7);
        fade = Math.max(0, 1 - Math.max(0, dd - 0.35) * 1.1);
      }
    } else {
      fallY = 0.5 * 2600 * d * d;
      fallR = (mhash(seed) - 0.5) * 50 * d;
      fade = Math.max(0, 1 - d * 0.9);
    }
  }
  if (fade <= 0.01) return null;

  const wob = idle(t, seed, idleAmp);
  const wash = state === "amber" ? rgba(CLAY.amber, 0.16)
    : state === "mint" ? rgba(CLAY.mint, 0.15)
    : state === "coral" ? rgba(CLAY.coral, 0.2) : undefined;

  return (
    <div style={{ position: "absolute", left: x - w / 2, top: y - h, width: w, height: h, zIndex }}>
      {/* the stage shadow — non-optional, drawn by the layer, never baked */}
      <div style={{
        position: "absolute", left: "5%", bottom: -h * 0.06, width: "90%", height: h * 0.22,
        background: `radial-gradient(50% 50% at 50% 50%, ${rgba("#000", 0.25 * shadowIn * fade)} 0%, ${rgba("#000", 0)} 70%)`,
      }} />
      <div style={{
        position: "absolute", inset: 0,
        transform: `translate(${wob.x + fallX}px, ${wob.y + (1 - Math.min(e, 1)) * -40 + fallY}px) rotate(${wob.r + fallR}deg) scale(${scale.toFixed(3)})`,
        opacity: Math.min(1, e * 1.4) * opacity * fade,
        filter: blur + fallBlur > 0.4 ? `blur(${(blur + fallBlur).toFixed(1)}px)` : undefined,
      }}>
        <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
        {wash ? (
          <div style={{
            position: "absolute", inset: 0, background: wash, mixBlendMode: "overlay",
            WebkitMaskImage: `url(${staticFile(src)})`, WebkitMaskSize: "100% 100%",
            maskImage: `url(${staticFile(src)})`, maskSize: "100% 100%",
          }} />
        ) : null}
      </div>
    </div>
  );
};

/* ---- THE SLAB: real pixels, witnessed ------------------------------------ */
const SLAB_HOLE = { x0: 0.2158, y0: 0.3398, x1: 0.749, y1: 0.7471 }; // measured on the keyed sprite

export type SlabProps = {
  /** capture path relative to public/ — a REAL screen recording or still. */
  capture: string;
  video?: boolean;
  captureFrom?: number;
  x: number; y: number; h: number;
  aspect: number;
  /** the provenance strip. Honesty as a visible brand asset. */
  provenance: string;
  staged?: boolean;
  /** dominant hue of the capture, for the spill (measured, not guessed). */
  spill?: string;
  enterAt?: number;
  zIndex?: number;
};

export const SlabScreen: React.FC<SlabProps> = ({
  capture, video, captureFrom = 0, x, y, h, aspect, provenance, staged,
  spill = "#3a3f4c", enterAt, zIndex,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const e = enterAt == null ? 1 : enter(t, enterAt, 0.38, 0.05);
  if (e <= 0.001) return null;
  const w = h * aspect;
  const hole = {
    left: SLAB_HOLE.x0 * w, top: SLAB_HOLE.y0 * h,
    width: (SLAB_HOLE.x1 - SLAB_HOLE.x0) * w, height: (SLAB_HOLE.y1 - SLAB_HOLE.y0) * h,
  };
  const media = video ? (
    <OffthreadVideo src={staticFile(capture)} muted startFrom={Math.round(captureFrom * fps)}
                    style={{ width: "100%", height: "100%", objectFit: "cover" }} />
  ) : (
    <Img src={staticFile(capture)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
  );
  return (
    <div style={{
      position: "absolute", left: x - w / 2, top: y - h, width: w, height: h, zIndex,
      opacity: Math.min(1, e * 1.4),
      transform: `translateY(${(1 - Math.min(e, 1)) * -34}px)`,
    }}>
      {/* light-wrap: the capture's own light bleeding behind the frame */}
      <div style={{
        position: "absolute", left: hole.left - w * 0.015, top: hole.top - h * 0.015,
        width: hole.width * 1.03, height: hole.height * 1.03,
        background: spill, filter: "blur(18px)", opacity: 0.15, mixBlendMode: "screen",
      }} />
      {/* the capture, behind the frame, showing through the keyed hole */}
      <div style={{ position: "absolute", ...hole, overflow: "hidden", filter: "blur(0.5px)" }}>
        {media}
        {/* sheen */}
        <div style={{
          position: "absolute", inset: 0,
          background: `linear-gradient(160deg, ${rgba("#fff", 0.07)} 0%, ${rgba("#fff", 0)} 40%)`,
        }} />
      </div>
      <Img src={staticFile("assets/claylight/library/slab.png")}
           style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "contain" }} />
      {/* hue spill onto the world around the slab */}
      <div style={{
        position: "absolute", left: "-12%", top: "-8%", width: "124%", height: "116%",
        background: `radial-gradient(55% 45% at 50% 52%, ${spill} 0%, ${rgba("#000", 0)} 70%)`,
        opacity: 0.12, mixBlendMode: "screen", pointerEvents: "none",
      }} />
      {/* THE PROVENANCE STRIP */}
      <div style={{
        position: "absolute", left: "6%", top: "101%",
        fontFamily: PLEX, fontSize: Math.max(17, h * 0.032), letterSpacing: 2,
        color: staged ? rgba(CLAY.cream, 0.6) : rgba(CLAY.mint, 0.9),
      }}>
        {staged ? "STAGED" : "✓ REAL CAPTURE"} · {provenance}
      </div>
    </div>
  );
};

/* ---- CHIPS, IN CLAY ------------------------------------------------------ */
export type ClayChip = { t: number; end?: number; text: string; hot?: boolean };

export const ChipClay: React.FC<{
  chips: ClayChip[];
  anchorY?: number;
  size?: number;
}> = ({ chips = [], anchorY = 1306, size = 72 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  let cur: ClayChip | null = null;
  for (let i = 0; i < chips.length; i++) {
    const c = chips[i];
    const end = c.end ?? chips[i + 1]?.t ?? c.t + 1.9;
    if (t >= c.t && t < end) { cur = c; break; }
  }
  if (!cur) return null;
  const pop = Math.min(1, (t - cur.t) * fps / 2);
  const sc = (0.92 + 0.08 * pop) * (1 + settle(t, cur.t, 0.4) * 0.05);
  return (
    <div style={{
      position: "absolute", left: 0, right: 0, top: anchorY, zIndex: 40,
      display: "flex", justifyContent: "center",
      transform: `translateY(-50%) scale(${sc.toFixed(3)})`, opacity: pop,
    }}>
      <div style={{
        fontFamily: BALOO, fontWeight: 800, fontSize: size,
        letterSpacing: size * 0.02, textTransform: "uppercase" as const,
        whiteSpace: "nowrap" as const,
        color: cur.hot ? CLAY.cream : CLAY.cream,
        background: cur.hot ? CLAY.coral : undefined,
        padding: cur.hot ? `${size * 0.08}px ${size * 0.34}px` : undefined,
        borderRadius: cur.hot ? size * 0.32 : undefined,
        boxShadow: cur.hot ? `0 ${size * 0.12}px ${size * 0.5}px -${size * 0.18}px ${rgba("#000", 0.8)}`
                           : `0 3px 22px ${rgba("#000", 0.7)}`,
        textShadow: cur.hot ? undefined : `0 3px 20px ${rgba("#000", 0.9)}`,
      }}>{cur.text}</div>
    </div>
  );
};

/* ---- THE COUNTER: measured numbers only ---------------------------------- */
export const CounterClay: React.FC<{
  /** [t, value] keyframes — MEASURED values (a tokenizer run, an export count).
   *  Plex Mono on an invented number is a QC fail by the lock. */
  keys: [number, number][];
  label?: string;
  x: number; y: number;
  size?: number;
  /** roll digits over this many seconds around each keyframe. */
}> = ({ keys, label, x, y, size = 44 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  if (!keys.length || t < keys[0][0]) return null;
  let v = keys[0][1];
  for (let i = 0; i < keys.length; i++) {
    if (t >= keys[i][0]) {
      const nxt = keys[i + 1];
      if (nxt && t < nxt[0]) {
        const p = clamp01((t - keys[i][0]) / Math.max(nxt[0] - keys[i][0], 1e-6));
        v = keys[i][1] + (nxt[1] - keys[i][1]) * p;
      } else v = keys[i][1];
    }
  }
  return (
    <div style={{ position: "absolute", left: x, top: y, textAlign: "left" }}>
      {label ? (
        <div style={{ fontFamily: PLEX, fontSize: size * 0.42, letterSpacing: 3,
                      color: rgba(CLAY.cream, 0.55), marginBottom: 4 }}>{label}</div>
      ) : null}
      <div style={{
        fontFamily: PLEX, fontSize: size, color: CLAY.amber,
        fontVariantNumeric: "tabular-nums" as const, letterSpacing: 1,
        textShadow: `0 0 24px ${rgba(CLAY.amber, 0.35)}`,
      }}>{Math.round(v).toLocaleString("en-IN")}</div>
    </div>
  );
};
