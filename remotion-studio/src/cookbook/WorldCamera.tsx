import React, { createContext, useContext } from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { OUT_E, IN_E, clamp01, vnoise1 } from "./motion";

/* =============================================================================
   WorldCamera — a real camera over an oversized world.

   THE GAP THIS CLOSES. The references do not animate elements on a static
   frame; they move a CAMERA through a world that is larger than the frame —
   Isenberg dollies across a canvas of cards, Hermes rides a terminal
   mega-scene for 15 unbroken seconds, Ravie orbits sculptures. Our 7px drift
   was set dressing; this is transportation. A camera move is the cheapest
   premium signal there is, because it implies the world continues beyond the
   frame — and it gives U5 its prepared boundaries for free (the camera
   accelerates INTO a move and settles out of it).

   MODEL. Author content anywhere on an unbounded world plane. The camera is a
   keyframe track: at time t it is at (x, y) with zoom z, meaning world point
   (x, y) sits at screen centre (540, 960) magnified z. Between keyframes it
   travels on an eased path with acceleration into and settle out of every
   move. Punches are 4-frame zoom hits layered on top. A breath of drift rides
   on everything so a parked camera is never dead (U1).

   PARALLAX. Children wrapped in <Parallax depth={d}> move at d times camera
   speed: d=1 rides the world exactly, d<1 lags behind (background), d>1
   overtakes (foreground). True depth from flat layers — the CSS-3D staging
   the fresh worlds need, with no WebGL and full frame-determinism.

     <WorldCamera track={[{t:0,x:540,y:960,z:1},{t:4,x:1400,y:800,z:1.6}]}
                  punches={[6.0]}>
       <Parallax depth={0.35}>…far background…</Parallax>
       …the world (depth 1)…
       <Parallax depth={1.4}>…foreground props…</Parallax>
     </WorldCamera>
   ========================================================================== */

export type CamKey = {
  /** film-absolute second this keyframe is REACHED. */
  t: number;
  /** world point that sits at screen centre when reached. */
  x: number;
  y: number;
  /** magnification. 1 = author scale. */
  z: number;
  /** seconds the travel INTO this key takes; default = full gap from the
   *  previous key (continuous glide). Shorter = arrive early and hold. */
  dur?: number;
};

export type WorldCameraProps = {
  track: CamKey[];
  /** film-absolute seconds of 4-frame punch-ins (a hit, not a move). */
  punches?: number[];
  punchScale?: number;
  /** breath amplitude in px at z=1. 0 disables. */
  breath?: number;
  width?: number;
  height?: number;
  children?: React.ReactNode;
};

type CamState = { x: number; y: number; z: number };
const CamCtx = createContext<CamState>({ x: 540, y: 960, z: 1 });

export const useCamera = () => useContext(CamCtx);

const easeInOut = (p: number) => {
  // acceleration in, settle out — U5 as a camera property
  const q = clamp01(p);
  return q < 0.5 ? 2 * q * q : 1 - Math.pow(-2 * q + 2, 2) / 2;
};

export const WorldCamera: React.FC<WorldCameraProps> = ({
  track,
  punches = [],
  punchScale = 1.09,
  breath = 5,
  width = 1080,
  height = 1920,
  children,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  const keys = track.length ? track : [{ t: 0, x: width / 2, y: height / 2, z: 1 }];

  // find the segment and interpolate
  let cam: CamState = { x: keys[0].x, y: keys[0].y, z: keys[0].z };
  for (let i = 0; i < keys.length; i++) {
    const k = keys[i];
    if (t < k.t && i > 0) {
      const prev = keys[i - 1];
      const dur = Math.min(k.dur ?? k.t - prev.t, k.t - prev.t);
      const start = k.t - dur;
      const p = easeInOut(clamp01((t - start) / Math.max(dur, 1e-6)));
      cam = {
        x: prev.x + (k.x - prev.x) * p,
        y: prev.y + (k.y - prev.y) * p,
        z: prev.z + (k.z - prev.z) * p,
      };
      break;
    }
    cam = { x: k.x, y: k.y, z: k.z };
  }

  // punches: a 4-frame hit that decays over ~0.3s — a cut that isn't a cut
  let punch = 1;
  for (const p of punches) {
    const d = t - p;
    if (d >= 0 && d < 0.3) {
      punch *= 1 + (punchScale - 1) * (d < 0.08 ? d / 0.08 : 1 - (d - 0.08) / 0.22);
    }
  }

  // the breath: never parked, never noticed
  const bx = breath ? (vnoise1(t * 0.23) - 0.5) * 2 * breath : 0;
  const by = breath ? (vnoise1(t * 0.19 + 31) - 0.5) * 2 * breath * 0.8 : 0;

  const z = cam.z * punch;
  const tx = width / 2 - (cam.x + bx) * z;
  const ty = height / 2 - (cam.y + by) * z;

  return (
    <CamCtx.Provider value={{ x: cam.x + bx, y: cam.y + by, z }}>
      <AbsoluteFill style={{ overflow: "hidden" }}>
        <div style={{
          position: "absolute", left: 0, top: 0,
          transform: `translate(${tx.toFixed(2)}px, ${ty.toFixed(2)}px) scale(${z.toFixed(4)})`,
          transformOrigin: "0 0",
        }}>
          {children}
        </div>
      </AbsoluteFill>
    </CamCtx.Provider>
  );
};

/* ---- Parallax: a layer that lives at a different depth -------------------
   Must be a child of WorldCamera. depth<1 lags the camera (far), depth>1
   overtakes it (near). The layer's own coordinates stay world coordinates —
   only its response to camera motion changes. */
export const Parallax: React.FC<{
  depth: number;
  children?: React.ReactNode;
}> = ({ depth, children }) => {
  const cam = useCamera();
  const { width, height } = useVideoConfig();
  // where the camera's centre WOULD be for this layer
  const dx = (cam.x - width / 2) * (1 - depth);
  const dy = (cam.y - height / 2) * (1 - depth);
  return (
    <div style={{
      position: "absolute", left: 0, top: 0,
      transform: `translate(${dx.toFixed(2)}px, ${dy.toFixed(2)}px)`,
    }}>
      {children}
    </div>
  );
};

/* ---- ZoomThrough: the signature transition as a camera act ----------------
   Returns the extra scale/opacity for a scene being LEFT via a dive into one
   of its elements. Pair with WhiteoutBloom at the boundary. Kept here because
   it is camera grammar, not scene grammar. */
export const zoomThrough = (t: number, at: number, dur = 0.4): { scale: number; fade: number } => {
  const p = clamp01((t - at) / dur);
  if (p <= 0) return { scale: 1, fade: 1 };
  return { scale: 1 + IN_E(p) * 7, fade: 1 - OUT_E(p) };
};
