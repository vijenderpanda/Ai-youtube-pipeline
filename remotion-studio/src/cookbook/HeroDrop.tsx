import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { BRAND, SANS, SERIF, DISPLAY, rgba, clamp, Fonts, AuroraBed } from "./kit";
import { clamp01, enter, settle, idle, mhash } from "./motion";

/* =============================================================================
   HeroDrop — the hero-asset drop with physics: the "crown moment" (Repo King's
   cold-open, crown falls onto the repo). An image (or giant emoji fallback)
   drops from the top of frame onto an optional backdrop still and LANDS with
   mass, then a mixed-register caption line arrives beneath it.

   Physics follows the craft.tsx TravelSprite recipe (C3 — mass is free):
     anticipation  a small upward gather before the plunge (the wrong-direction
                   beat that sells intent)
     fall          gravity-eased descent with slight rotation, vertical smear
                   stretch + a touch of motion blur at peak velocity
     landing       squash at the bottom origin + overshoot ripple (settle()),
                   rotation damps to rest
     dust burst    ≤12 gold #FFB454 particles (hard cap in code) fan up-and-out
                   from the impact point on ballistic arcs — the Repo King DNA;
                   gold is rationed to crown/CTA moments, so the burst is gold
                   regardless of `accent`
     hold          idle() wobble + a slow backdrop drift — never static (U1)

   The asset starts with its top just BELOW SAFE.headerFloor (y=150) so a
   mid-fall still never violates the wordmark band, and lands with its bottom
   at y≈1010 — the caption anchors at 1290, well above the 1560 caption ceiling.

   Caption parts use the SAME shape as SerifCap parts (sans / serif-italic /
   display registers, one accent word max) — duplicated here, not imported,
   because cookbook files stay self-contained (contract: exactly 3 exports).
   The caption lands 0.25s after impact — the eye is still on the squash when
   the words begin to rise.

   All props JSON-serialisable; time-sliced from `start`, held final state.
   ========================================================================== */

export type HeroDropProps = {
  src?: string; // hero asset image — staticFile path unless http URL
  emoji?: string; // fallback: renders a giant emoji when no src (default 👑)
  onSrc?: string; // optional backdrop image/still the asset drops ONTO (full-bleed cover)
  caption?: {
    // same part shape as SerifCap — one line, lands 0.25s after impact
    parts: Array<{ t: string; face?: "sans" | "serif" | "display"; accent?: boolean }>;
  };
  dropAt?: number; // seconds (component clock) the drop begins (default 0.15)
  captionAt?: number; // seconds the caption lands (default impact+0.25) — set it ON the spoken word (U2)
  partAt?: number[]; // per-part land times (component clock); overrides captionAt for that part — e.g. the accent word lands ON its VO word
  size?: number; // hero box px, square, asset contained (default 420)
  start?: number; // seconds before the component clock begins
  accent?: string; // caption accent word tint (magenta default; pass gold for crown/CTA)
  ink?: string;
  width?: number;
  height?: number;
  transparent?: boolean; // skip the aurora backdrop (onSrc still renders if given)
};

const GOLD = "#FFB454"; // dust burst — always gold, the crown signature
const PAPER = "#F5F2EC";

// mixed-register caption faces — mirrors SerifCap (see its header for why the
// serif face is italic-only and scaled 1.08).
const FACE = {
  sans: { adv: 0.6, scale: 1.0 },
  serif: { adv: 0.52, scale: 1.08 },
  display: { adv: 0.58, scale: 0.9 },
} as const;

const faceStyle = (face: "sans" | "serif" | "display", fs: number): React.CSSProperties =>
  face === "serif"
    ? { fontFamily: SERIF, fontStyle: "italic", fontWeight: 500, fontSize: Math.round(fs * FACE.serif.scale) }
    : face === "display"
      ? {
          fontFamily: DISPLAY,
          fontWeight: 400,
          fontSize: Math.round(fs * FACE.display.scale),
          textTransform: "uppercase",
          letterSpacing: 2,
        }
      : { fontFamily: SANS, fontWeight: 800, fontSize: fs, letterSpacing: 0.5 };

// VJ 2026-08-23 STANDARD: a heavy "crown drop" — bigger anticipation, a fast
// plunge, a hard impact (deep squash + screen shake + shockwave). Applies to
// every HeroDrop across the channel.
const ANT = 0.20; // anticipation gather (deeper wind-up)
const FALL = 0.34; // descent — faster = higher impact velocity
const BURST_LIFE = 0.75; // particle lifetime
const BURST_N = 12; // hard cap — ≤12 particles by spec

export const HeroDrop: React.FC<HeroDropProps> = ({
  src,
  emoji,
  onSrc,
  caption,
  dropAt = 0.15,
  captionAt,
  partAt,
  size = 420,
  start = 0,
  accent = BRAND.mag,
  ink = BRAND.ink,
  width = 1080,
  height = 1920,
  transparent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tBed = frame / fps;
  const tt = tBed - start;

  const resolve = (p: string) => (/^https?:\/\//.test(p) ? p : staticFile(p));

  const cx = width / 2;
  const startTop = 138; // just below SAFE.headerFloor — a mid-fall still stays legal
  const landBottom = 1010; // asset bottom at rest
  const landTop = landBottom - size;
  const dist = landTop - startTop;

  const tFall = dropAt + ANT;
  const tImpact = tFall + FALL;

  // ---- vertical position + fall-phase deformation --------------------------
  let topY = startTop;
  let rot = -6;
  let sx = 1;
  let sy = 1;
  let blurPx = 0;
  if (tt < dropAt) {
    // pre-drop hold: hanging, alive
  } else if (tt < tFall) {
    // anticipation: gather UP before the plunge (the wrong direction first)
    const a = clamp01((tt - dropAt) / ANT);
    topY = startTop - Math.sin(a * Math.PI) * 16;
    sy = 1 + Math.sin(a * Math.PI) * 0.04;
    sx = 1 / sy;
  } else if (tt < tImpact) {
    // gravity descent: accelerating hard, stretching along travel, motion-blur
    const fp = clamp01((tt - tFall) / FALL);
    const ease = fp * fp * fp; // cubic — snaps down at the end (heavier)
    topY = startTop + dist * ease;
    rot = -8 + fp * 11;
    sy = 1 + ease * 0.2; // more stretch at speed
    sx = 1 / sy;
    blurPx = ease * 7; // stronger motion blur on the plunge
  } else {
    // HARD landing: deep squash + overshoot ripple at the bottom origin
    topY = landTop;
    const sq = settle(tt, tImpact, 0.5);
    sx = 1 + sq * 0.30; // deep squash (was .16)
    sy = 1 - sq * 0.30;
    rot = 4 * Math.exp(-(tt - tImpact) * 9) + settle(tt, tImpact, 0.5) * 3;
  }
  // impact envelope (1 at landing -> 0 over ~0.5s) for shake + shockwave + flash
  const impact = tt >= tImpact ? Math.max(0, 1 - (tt - tImpact) / 0.5) : 0;
  const shakeX = impact * Math.sin((tt - tImpact) * 90) * 9 * impact;
  const shakeY = impact * Math.cos((tt - tImpact) * 76) * 13 * impact;

  // hold = life, never freeze. VJ 2026-08-23 (fcc 0-3s audit): 1.8px read as a
  // freeze at feed size — the hold now FLOATS (slow sine hover, ±7px) on top of
  // the idle wobble, and the backdrop push-in below is a visible 2%/s.
  const held = tt >= tImpact ? clamp01((tt - tImpact - 0.55) / 0.6) : 0;
  const wob0 = idle(tt, 3, tt >= tImpact ? 2.2 : 0.8);
  const wob = { ...wob0, y: wob0.y + Math.sin((tt - tImpact) * 2.4) * 7 * held };
  const alt = clamp01((landBottom - (topY + size)) / Math.max(dist, 1)); // 1 = high up

  // ---- caption fit (single line, mirrors SerifCap math) --------------------
  const capParts = (caption?.parts ?? []).slice(0, 8);
  const capAt = captionAt ?? tImpact + 0.25; // default: lands while the squash is still settling
  const sideSafe = 72;
  const colW = width - sideSafe * 2;
  const capEm = capParts.reduce(
    (sum, part) => {
      const f = FACE[part.face ?? "sans"];
      return sum + part.t.length * f.adv * f.scale;
    },
    Math.max(0, capParts.length - 1) * 0.3
  );
  const capFs = clamp(Math.min(64, (colW * 0.96) / Math.max(capEm, 1)), 34, 96);
  const accentIdx = capParts.findIndex((q) => !!q.accent); // ONE accent word max (N3)

  return (
    <AbsoluteFill style={{ background: transparent ? undefined : ink, fontFamily: SANS,
      transform: `translate(${shakeX.toFixed(2)}px, ${shakeY.toFixed(2)}px)` }}>
      <Fonts />
      {transparent || onSrc ? null : <AuroraBed t={tBed} accent={accent} ink={ink} />}

      {/* backdrop still the asset drops ONTO — slow drift-zoom so it never sits dead */}
      {onSrc ? (
        <>
          <Img
            src={resolve(onSrc)}
            style={{
              position: "absolute",
              inset: 0,
              width: "100%",
              height: "100%",
              objectFit: "cover",
              transform: `scale(${(1.02 + Math.min(tBed * 0.02, 0.1)).toFixed(3)})`,
            }}
          />
          {/* scrim: keeps the hero + caption legible over any still */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              background: `linear-gradient(180deg, ${rgba(ink, 0.34)} 0%, ${rgba(ink, 0.08)} 38%, ${rgba(
                ink,
                0.58
              )} 100%)`,
            }}
          />
        </>
      ) : null}

      {/* cast shadow — grows/darkens as the asset approaches the ground */}
      <div
        style={{
          position: "absolute",
          left: cx - size * 0.39,
          top: landBottom - 4,
          width: size * 0.78,
          height: size * 0.16,
          borderRadius: "50%",
          transform: `scale(${(0.5 + 0.5 * (1 - alt)).toFixed(2)})`,
          background: `radial-gradient(50% 50% at 50% 50%, ${rgba("#000", 0.34 * (1 - alt * 0.7))} 0%, ${rgba(
            "#000",
            0
          )} 70%)`,
        }}
      />

      {/* post-landing bloom behind the asset — breathes so the hold never sits dead */}
      {tt >= tImpact ? (
        <div
          style={{
            position: "absolute",
            left: cx - size * 0.9,
            top: topY - size * 0.4,
            width: size * 1.8,
            height: size * 1.8,
            borderRadius: "50%",
            opacity: held * (0.28 + Math.sin((tt - tImpact) * 3.1) * 0.14),
            background: `radial-gradient(50% 50% at 50% 50%, ${rgba(accent, 0.55)} 0%, ${rgba(accent, 0)} 68%)`,
            filter: "blur(6px)",
          }}
        />
      ) : null}
      {/* IMPACT: white flash + expanding shockwave ring at the landing point */}
      {impact > 0 ? (
        <>
          <div style={{ position: "absolute", inset: 0, background: "#ffffff",
            opacity: impact * impact * 0.22, mixBlendMode: "screen", pointerEvents: "none" }} />
          <div style={{ position: "absolute",
            left: cx - (size * 0.5) - (1 - impact) * size * 1.4,
            top: landBottom - 30 - (1 - impact) * size * 0.5,
            width: size + (1 - impact) * size * 2.8,
            height: (size + (1 - impact) * size * 2.8) * 0.42,
            borderRadius: "50%",
            border: `${(impact * 8).toFixed(1)}px solid ${rgba(GOLD, impact * 0.7)}`,
            opacity: impact, pointerEvents: "none" }} />
        </>
      ) : null}

      {/* the hero asset (or giant emoji) — bottom-origin so squash reads as impact */}
      <div
        style={{
          position: "absolute",
          left: cx - size / 2,
          top: topY,
          width: size,
          height: size,
          transform: `translate(${wob.x.toFixed(1)}px, ${wob.y.toFixed(1)}px) rotate(${rot.toFixed(
            2
          )}deg) scale(${sx.toFixed(3)}, ${sy.toFixed(3)})`,
          transformOrigin: "50% 100%",
          filter: blurPx > 0.4 ? `blur(${blurPx.toFixed(1)}px)` : undefined,
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "center",
        }}
      >
        {src ? (
          <Img src={resolve(src)} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
        ) : (
          <div
            style={{
              fontSize: Math.round(size * 0.86),
              lineHeight: 1,
              filter: `drop-shadow(0 18px 44px ${rgba("#000", 0.5)})`,
            }}
          >
            {emoji ?? "👑"}
          </div>
        )}
      </div>

      {/* dust/sparkle burst — ≤12 gold particles on ballistic arcs from impact */}
      {tt > tImpact && tt < tImpact + BURST_LIFE
        ? Array.from({ length: BURST_N }, (_, i) => {
            const d = tt - tImpact;
            const a = -Math.PI * (0.08 + 0.84 * mhash(i + 7)); // upward fan, wide
            const v = 520 + mhash(i + 13) * 620; // faster on the hard impact
            const px = cx + Math.cos(a) * v * d;
            const py = landBottom - 44 + Math.sin(a) * v * d + 520 * d * d;
            const ps = 9 + mhash(i + 29) * 10;
            const sparkle = i % 3 === 0; // every third is a diamond glint
            return (
              <div
                key={i}
                style={{
                  position: "absolute",
                  left: px - ps / 2,
                  top: py - ps / 2,
                  width: ps,
                  height: ps,
                  borderRadius: sparkle ? 2 : "50%",
                  transform: sparkle ? `rotate(${45 + d * 240}deg)` : undefined,
                  background: GOLD,
                  boxShadow: `0 0 ${Math.round(ps * 1.6)}px ${rgba(GOLD, 0.7)}`,
                  opacity: 1 - d / BURST_LIFE,
                }}
              />
            );
          })
        : null}

      {/* caption — one mixed-register line, cluster rise+settle, 0.25s post-impact */}
      {capParts.length ? (
        <div
          style={{
            position: "absolute",
            left: sideSafe,
            width: colW,
            bottom: height - 1290, // block bottom well above the 1560 caption ceiling
            display: "flex",
            justifyContent: "center",
            alignItems: "baseline",
            columnGap: Math.round(capFs * 0.3),
            whiteSpace: "nowrap",
            lineHeight: 1.15,
          }}
        >
          {capParts.map((part, i) => {
            const appear = partAt?.[i] ?? capAt + i * 0.07;
            const prog = enter(tt, appear, 0.44, 0.08);
            const op = clamp01((tt - appear) / 0.16);
            const hot = i === accentIdx;
            // the accent word POPS on arrival (scale overshoot) — a visual twin of its VO word
            const popS = hot ? 1 + (1 - settle(tt, appear, 0.5)) * 0 + Math.max(0, 0.18 - (tt - appear) * 0.6) : 1;
            return (
              <span
                key={i}
                style={{
                  ...faceStyle(part.face ?? "sans", Math.round(capFs)),
                  display: "inline-block",
                  color: hot ? accent : PAPER,
                  opacity: op,
                  transform: `translateY(${((1 - prog) * 40).toFixed(1)}px) scale(${(tt >= appear ? popS : 1).toFixed(3)})`,
                  transformOrigin: "50% 100%",
                  textShadow: hot
                    ? `0 6px 30px ${rgba(accent, 0.5)}, 0 4px 14px ${rgba("#000", 0.5)}`
                    : `0 4px 14px ${rgba("#000", 0.5)}, 0 12px 40px ${rgba("#000", 0.42)}`,
                }}
              >
                {part.t}
              </span>
            );
          })}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

export const heroDropDemo: HeroDropProps = {
  emoji: "👑",
  caption: {
    parts: [
      { t: "meet the", face: "sans" },
      { t: "repo king.", face: "serif", accent: true },
    ],
  },
  dropAt: 0.15,
  size: 420,
  accent: GOLD, // crown moment — gold is earned here
};
