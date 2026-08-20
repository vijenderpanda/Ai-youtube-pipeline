import React from "react";
import {
  AbsoluteFill,
  Easing,
  OffthreadVideo,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BRAND, MONO, rgba, clamp, Fonts, AuroraBed } from "./kit";

/* =============================================================================
   ScreenStage — REAL recorded footage, staged with the cookbook's plates.

   Every other cookbook component draws invented data. This one is the opposite
   and that is the point: the tape stays the evidence, we only change how it is
   PRESENTED. A raw screen recording is the most honest thing in the cut and,
   visually, the weakest: browser chrome, dead margins, 30px type, and a flat
   rectangle pasted on a flat frame.

   Built from the plates in the "Wow Mechanics" field study (artifact b9570dbc)
   that section C says survive the port to a frame clock:

     · Plate 07 "Depth without 3D" — "Swap pointer position for a slow scripted
       camera path. Layer offsets, sheen sweep and grain all survive intact."
       So: perspective, the card tilting +/-8deg on a scripted path, a shadow
       plane and the sheen travelling at different depths, plus SVG grain. Four
       flat layers at four speeds read as one solid object, with no renderer.
     · Plate 01 "Refractive glass" — the bezel. "The trick is the inset
       highlight, not the blur": a 1px hairline, an inset white highlight and a
       3px caustic top edge do the work; there is no backdrop-filter here
       (unreliable headless) and none is needed, because the card is opaque.
     · Plate 05 "Element morph" — "No View Transitions API in a render, but the
       effect - one object travelling between two layouts - is exactly what
       interpolating a bounding box does." So `morph` interpolates the card's
       (x, y, w, h) from an inset card to the hero box on the Plate 06 settle
       curve. The recording does not cut to full-frame; it TRAVELS there.

   Honesty: the pixels inside the card are never altered, never re-timed and
   never cropped to mislead - `fit` only chooses cover vs contain. The staging
   is chrome around real evidence.
   ========================================================================== */

export type ScreenStageProps = {
  src: string; // the recording, resolved via staticFile() unless it is a URL
  from?: number; // seconds into the source to start playing
  label?: string; // small MONO chip pinned to the stage (e.g. "REAL SCREEN RECORDING")
  /* Plate 05 — bounding-box morph. Off = a static hero card. */
  morph?: boolean;
  morphStart?: number; // seconds before the travel begins
  morphDur?: number; // seconds the travel takes
  insetScale?: number; // starting width as a fraction of the hero width
  /* Plate 07 — scripted camera. */
  tilt?: number; // max degrees of rotateX/rotateY. DEFAULT 0 — the tilt made the
                 // recording look staged rather than shown; the depth now comes
                 // from the layered parallax + shadow plane alone (Plate 07).
  drift?: number; // px of layer travel at the deepest layer
  sheen?: boolean;
  grain?: boolean;
  /* framing */
  fit?: "cover" | "contain";
  radius?: number;
  heroWidth?: number; // hero card width in px (default 0.92 of frame)
  heroAspect?: number; // h/w of the card (default 16/9 portrait = 1.777)
  accent?: string;
  ink?: string;
  transparent?: boolean; // drop the ground so the stage floats over the comp
  /* Host PIP — a HeyGen clip cut from THIS beat's own VO slice, so the lipsync
     matches the words being spoken over the recording. build_ep_v2 generates it
     and swaps the real path in when the episode spec sets `host: true`. */
  host?: string;
  hostSize?: number;   // pip WIDTH in px (16:9 card), default 360
  hostFrom?: number;   // seconds into the host clip
  width?: number;
  height?: number;
};

const SETTLE = Easing.bezier(0.2, 0.9, 0.25, 1); // Plate 06

export const ScreenStage: React.FC<ScreenStageProps> = ({
  src,
  from = 0,
  label,
  morph = true,
  morphStart = 0.2,
  morphDur = 0.9,
  insetScale = 0.62,
  tilt = 0,   // VJ 2026-08-19: NOT tilted — square-on reads truer for real evidence
  drift = 14,
  sheen = true,
  grain = true,
  fit = "cover",
  radius = 40,
  heroWidth,
  heroAspect = 1.7778,
  accent = BRAND.mag,
  ink = BRAND.ink,
  transparent,
  host,
  hostSize = 360,
  hostFrom = 0,
  width = 1080,
  height = 1920,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  // ---- Plate 05: interpolate the bounding box, do not cut ----
  const HW = heroWidth ?? width * 0.92;
  const HH = HW * heroAspect;
  const heroX = (width - HW) / 2;
  const heroY = (height - HH) / 2;

  const m = morph
    ? interpolate(t, [morphStart, morphStart + morphDur], [0, 1], {
        easing: SETTLE,
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 1;

  const w = HW * (insetScale + (1 - insetScale) * m);
  const h = w * heroAspect;
  const x = heroX + (HW - w) / 2;
  const y = heroY + (HH - h) / 2;

  // ---- Plate 07: scripted camera (there is no cursor in a render) ----
  const cx = Math.sin(t * 0.38) * 1 + Math.sin(t * 0.17 + 1) * 0.4;
  const cy = Math.cos(t * 0.31) * 0.9;
  const rotY = cx * tilt * 0.5;
  const rotX = -cy * tilt * 0.5;
  const layer = (k: number) => `translate3d(${cx * drift * k}px, ${cy * drift * 0.8 * k}px, 0)`;

  /* The sweep is NOT one-shot. A screen recording of a flat-colour result screen
     does not move at all, so once the entry sweep finished the frame sat literally
     static — measured 0.04 motion at 0:21-0:22, inside the exact 0:15-0:25 window
     YouTube analytics flags as this channel's drop-off. Repeat it on a slow cycle so
     genuinely-still evidence still breathes. The jump back is invisible: the sheen is
     off-canvas at both ends (-130% / +130%). */
  const sheenT = t - morphStart - 0.25;
  const sheenP = sheenT < 1.5 ? clamp(sheenT / 1.5) : ((sheenT - 1.5) % 3.2) / 3.2;

  return (
    <AbsoluteFill style={{ background: transparent ? undefined : ink, overflow: "hidden" }}>
      <Fonts />
      {/* one shared material across the whole cut (VJ: unify on aurora + glass) */}
      {!transparent && <AuroraBed t={t} accent={accent} ink={ink} opacity={0.34} />}

      {/* accent bloom behind the card — deepest layer (0.2) */}
      {!transparent && (
        <div
          style={{
            position: "absolute",
            left: x - w * 0.18,
            top: y - h * 0.08,
            width: w * 1.36,
            height: h * 1.16,
            borderRadius: "50%",
            background: `radial-gradient(closest-side, ${rgba(accent, 0.28)}, transparent 70%)`,
            filter: "blur(60px)",
            transform: layer(0.2),
          }}
        />
      )}

      <div style={{ position: "absolute", inset: 0, perspective: 1500 }}>
        {/* shadow plane — layer 0.5, sits behind and below the card */}
        <div
          style={{
            position: "absolute",
            left: x,
            top: y + 26,
            width: w,
            height: h,
            borderRadius: radius,
            background: rgba("#000000", 0.55),
            filter: "blur(38px)",
            transform: layer(0.5),
            opacity: 0.8,
          }}
        />

        {/* the card — layer 0.9 (front) */}
        <div
          style={{
            position: "absolute",
            left: x,
            top: y,
            width: w,
            height: h,
            borderRadius: radius,
            overflow: "hidden",
            // The card must be an OPAQUE object. OffthreadVideo can miss its very
            // first frame after a startFrom seek, and with no background behind it
            // the card became a HOLE for one frame — a visible blank flash at every
            // hard cut into a recording (caught on _game at 16.03s).
            background: ink,
            transform: `${layer(0.9)} rotateY(${rotY}deg) rotateX(${rotX}deg)`,
            transformStyle: "preserve-3d",
            // Plate 01 — hairline + inset highlight is the trick
            border: `1px solid ${rgba("#ffffff", 0.28)}`,
            boxShadow: `0 60px 130px -40px ${rgba("#000000", 0.85)}, inset 0 1px 0 ${rgba(
              "#ffffff",
              0.5
            )}, inset 0 -1px 0 ${rgba("#ffffff", 0.07)}`,
          }}
        >
          {/* THE EVIDENCE — untouched pixels */}
          <OffthreadVideo
            src={src.startsWith("http") ? src : staticFile(src)}
            startFrom={Math.round(from * fps)}
            muted
            style={{ width: "100%", height: "100%", objectFit: fit }}
          />

          {/* 3px caustic top edge */}
          <div
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              top: 0,
              height: 3,
              background: `linear-gradient(90deg, ${rgba("#fff", 0)} 0%, ${rgba(
                "#fff",
                0.62
              )} 50%, ${rgba("#fff", 0)} 100%)`,
            }}
          />

          {/* one specular pass across the glass */}
          {sheen && (
            <div
              style={{
                position: "absolute",
                inset: 0,
                background: `linear-gradient(100deg, transparent 36%, ${rgba(
                  "#ffffff",
                  0.13
                )} 50%, transparent 64%)`,
                transform: `translateX(${interpolate(sheenP, [0, 1], [-130, 130])}%)`,
                pointerEvents: "none",
              }}
            />
          )}
        </div>
      </div>

      {/* host PIP — bottom-left, clear of the caption band */}
      {host && (
        <div
          style={{
            position: "absolute",
            left: 56,
            top: height - Math.round(hostSize * 0.5625) - 320,
            width: hostSize,
            height: Math.round(hostSize * 0.5625),   // 16:9 — matches the wide avatar
            borderRadius: 24,
            overflow: "hidden",
            border: `2px solid ${rgba("#ffffff", 0.5)}`,
            boxShadow: `0 26px 60px -18px ${rgba("#000", 0.85)}`,
            transform: layer(0.9),
          }}
        >
          <OffthreadVideo
            src={host.startsWith("http") ? host : staticFile(host)}
            startFrom={Math.round(hostFrom * fps)}
            muted
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </div>
      )}

      {/* grain over everything (Plate 07) */}
      {grain && (
        <svg style={{ position: "absolute", inset: 0, opacity: 0.12, mixBlendMode: "overlay" }}>
          <filter id="ss-grain">
            <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" />
          </filter>
          <rect width="100%" height="100%" filter="url(#ss-grain)" />
        </svg>
      )}

      {/* provenance chip — says plainly that the pixels are real */}
      {label && (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: y - 58,
            textAlign: "center",
            fontFamily: MONO,
            fontSize: 24,
            letterSpacing: 6,
            color: rgba(BRAND.paper, 0.72),
            opacity: clamp((t - morphStart) / 0.5),
          }}
        >
          {label}
        </div>
      )}
    </AbsoluteFill>
  );
};

export const screenStageDemo: ScreenStageProps = {
  src: "assets/ep_wheel/app_shift.mp4",
  from: 4,
  label: "REAL SCREEN RECORDING",
  morph: true,
  morphStart: 0.2,
  morphDur: 0.9,
  insetScale: 0.62,
};
