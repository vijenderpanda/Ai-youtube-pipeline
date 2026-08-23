import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { BRAND, rgba, clamp, AuroraBed } from "./kit";
import { cameraDrift, IN_E, clamp01 } from "./motion";

/* =============================================================================
   FilmLayers — the three global layers of a motion-graphics film.

   Gap 3 of the reference study: our beats were islands — every cut reset the
   background, the palette position and the viewer's orientation. All 11
   references keep ONE world: a persistent canvas the camera explores, a carry
   element that crosses every boundary, and optics (drift, blur, grain) applied
   to the WHOLE frame so every scene demonstrably lives in the same place.

   Composition order in Short.tsx for a film episode:

     <FilmCanvas>            — the world: ground, plate, grain, vignette
       <CameraRig>           — one drift for everything inside the world
         ...scenes...        — each may also wrap itself in <CutPrep>
       </CameraRig>
       <WhiteoutBloom .../>  — the signature boundary, mounted at film level
     </FilmCanvas>
     <ChipCaption .../>      — OUTSIDE the rig: the anchor is locked (U7)

   Nothing opts out. A scene that wants a different background flips the
   canvas' plate — it does not paint its own floor-to-ceiling fill, because
   that is exactly the island behaviour this layer exists to end.
   ========================================================================== */

/* ---- THE CANVAS ---------------------------------------------------------- */
export const FilmCanvas: React.FC<{
  accent?: string;
  ink?: string;
  /** optional raster world plate (a FLUX texture that passed ingest_plate.py),
   *  path relative to public/. Rendered dim under the aurora — atmosphere,
   *  never meaning. */
  plate?: string;
  plateOpacity?: number;
  grain?: number;
  children?: React.ReactNode;
}> = ({ accent = BRAND.mag, ink = BRAND.ink, plate, plateOpacity = 0.35, grain = 0.12, children }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  return (
    <AbsoluteFill style={{ background: ink }}>
      {plate ? (
        <Img src={staticFile(plate)} style={{
          position: "absolute", inset: 0, width: "100%", height: "100%",
          objectFit: "cover", opacity: plateOpacity,
        }} />
      ) : null}
      <AuroraBed t={t} accent={accent} ink={ink} opacity={0.28} />
      {children}
      {/* film grain — SVG turbulence, cheap and deterministic */}
      <svg style={{ position: "absolute", inset: 0, opacity: grain, mixBlendMode: "overlay", pointerEvents: "none" }}>
        <filter id="film-grain">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed={7} />
        </filter>
        <rect width="100%" height="100%" filter="url(#film-grain)" />
      </svg>
      {/* vignette — the exposure shaping C1 asks for, in its mildest form */}
      <div style={{
        position: "absolute", inset: 0, pointerEvents: "none",
        background: `radial-gradient(140% 105% at 50% 42%, ${rgba("#000", 0)} 55%, ${rgba("#000", 0.42)} 100%)`,
      }} />
    </AbsoluteFill>
  );
};

/* ---- THE CAMERA RIG ------------------------------------------------------ */
export const CameraRig: React.FC<{
  amp?: number;
  children?: React.ReactNode;
}> = ({ amp = 7, children }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const d = cameraDrift(frame / fps, amp);
  return (
    <AbsoluteFill style={{
      transform: `translate(${d.x.toFixed(2)}px, ${d.y.toFixed(2)}px) scale(${d.s.toFixed(4)})`,
    }}>
      {children}
    </AbsoluteFill>
  );
};

/* ---- CUT PREP — U5 made structural --------------------------------------
   Wrap a scene that ends at a hard boundary. In its last `exitFrames` the
   content accelerates (scale + directional stretch + blur); in its first
   `settleFrames` it lands defocused and racks sharp. A scene wrapped in this
   cannot "just stop" — the law passes by construction. */
export const CutPrep: React.FC<{
  /** scene duration in seconds (Sequence-local). */
  dur: number;
  exitFrames?: number;
  settleFrames?: number;
  /** exit travel: how hard the scene dives into the boundary. */
  exitScale?: number;
  children?: React.ReactNode;
}> = ({ dur, exitFrames = 4, settleFrames = 6, exitScale = 1.35, children }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const total = Math.round(dur * fps);
  const toEnd = total - frame;

  let scale = 1, blur = 0, stretch = 1;
  if (toEnd <= exitFrames && toEnd >= 0) {
    const p = IN_E(clamp01(1 - toEnd / exitFrames));
    scale = 1 + (exitScale - 1) * p;
    stretch = 1 + 0.12 * p;
    blur = 7 * p;
  } else if (frame < settleFrames) {
    const p = clamp01(frame / settleFrames);
    blur = 6 * (1 - p) * (1 - p);
    scale = 1.02 - 0.02 * p;
  }
  return (
    <AbsoluteFill style={{
      transform: `scale(${(scale * stretch).toFixed(3)}, ${scale.toFixed(3)})`,
      filter: blur > 0.3 ? `blur(${blur.toFixed(1)}px)` : undefined,
    }}>
      {children}
    </AbsoluteFill>
  );
};

/* ---- WHITEOUT BLOOM — the signature boundary -----------------------------
   The cheapest of the reference morphs (Weavy 12.9s): the outgoing scene dives
   (CutPrep), a white bloom swallows the frame for ~5 frames, and the incoming
   scene is already there when it clears. Mount ONCE at film level with the
   film-absolute boundary times. */
export const WhiteoutBloom: React.FC<{
  /** film-absolute seconds of each boundary the bloom should cover. */
  at: number[];
  color?: string;
}> = ({ at, color = "#FFFFFF" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  let a = 0;
  for (const b of at) {
    const d = t - (b - 0.12);
    if (d >= 0 && d < 0.24) {
      const p = d / 0.24;                    // triangle: up in 0.12, down in 0.12
      a = Math.max(a, 1 - Math.abs(p * 2 - 1));
    }
  }
  if (a <= 0.01) return null;
  return (
    <AbsoluteFill style={{
      background: `radial-gradient(120% 90% at 50% 46%, ${rgba(color, clamp(a) * 0.96)} 0%, ${rgba(color, clamp(a) * 0.5)} 55%, ${rgba(color, 0)} 100%)`,
      pointerEvents: "none", zIndex: 30,
    }} />
  );
};
