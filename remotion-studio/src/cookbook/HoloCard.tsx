import React from "react";
import {
  AbsoluteFill,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BRAND, SANS, MONO, DISPLAY, rgba, clamp, coverBg, Fonts } from "./kit";

/* =============================================================================
   HoloCard — one subject presented as a floating, dimensional artifact. Four
   flat layers (glow, rings, emblem, type) parallax at four depths on a slow
   SCRIPTED camera orbit, so a plain card reads as solid 3D with no renderer.
   Cookbook role: the low-density HERO / spotlight — the counterpart to BentoGrid
   (which packs many facts) and StatBars (which quantifies). This one makes a
   SINGLE thing — a feature, a product, an idea — feel premium and physical.

   THE PORT (why it works in a render)
   - The web version of "depth without 3D" reacts to the cursor. A render has no
     cursor, so the camera is a scripted path: a gentle sinusoidal orbit drives
     card tilt + per-layer offset (offset = camera × depth). The result is the
     same solid-object illusion, but choreographed instead of interactive — which
     is what a video wants anyway.
   - The intro is the wow: every layer assembles FROM its depth. Deep layers start
     further back (smaller, lower) and spring to rest, staggered, so the card
     builds itself in z. After it settles it only drifts, holding a clean hero.
   - A specular sheen sweeps once and a faint grain sits on top (inline SVG
     turbulence) — the two cheap touches that sell "one physical object" over
     "some divs".

   9:16 SAFE: the card is 760×980, centered at (540, 900) → bottom ≈1390, clear of
   the y=1517 caption band; ≥160px side margins even at the tilt's extreme. Title
   is Anton, auto-fit to two lines; eyebrow/specs are single-line. Emblem is a
   short glyph/emoji (self-contained — no image assets). JSON-safe throughout.
   ========================================================================== */

export type HoloCardProps = {
  /** tiny label above the title, e.g. "NEW" / "SHIPPED" / "v2". */
  eyebrow?: string;
  /** the hero name — the one thing this card is about (Anton display face). */
  title: string;
  /** one supporting line under the title. */
  subtitle?: string;
  /** the floating centerpiece — an emoji or 1–3 chars (e.g. "⚡" or "AI"). */
  emblem?: string;
  /** up to 4 spec chips shown in depth around the card, e.g. {k:"SPEED",v:"60fps"}. */
  specs?: { k: string; v: string }[];
  accent?: string; // brand accent (defaults to Sol magenta)
  ink?: string; // base fill
  start?: number; // seconds before it assembles
  width?: number;
  height?: number;
  transparent?: boolean; // skip the backdrop (overlay use inside a composition)
};

const CARD_W = 760;
const CARD_H = 980;
const CX = 540;
const CY = 900;

export const HoloCard: React.FC<HoloCardProps> = ({
  eyebrow = "SHIPPED",
  title,
  subtitle,
  emblem = "⚡",
  specs = [],
  accent = BRAND.mag,
  ink = BRAND.ink,
  start = 0.3,
  width = 1080,
  height = 1920,
  transparent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - start;

  const SP = specs.slice(0, 4);

  // ── scripted camera: a slow figure-drift the whole card tilts to ─────────
  const camX = Math.sin(t * 0.55) * 1 + Math.sin(t * 0.23 + 1) * 0.4;
  const camY = Math.sin(t * 0.4 + 0.6) * 0.7;
  const rotY = camX * 9; // deg
  const rotX = -camY * 8;

  // ── intro assembly spring (layers fly in from their depth) ───────────────
  const intro = clamp(
    spring({
      frame: frame - start * fps,
      fps,
      config: { damping: 18, mass: 0.9, stiffness: 90 },
    })
  );

  // a layer's transform: parallax by camera×depth, plus a depth-staggered fly-in
  const layer = (depth: number, extra?: React.CSSProperties): React.CSSProperties => {
    const px = -camX * 46 * depth;
    const py = -camY * 46 * depth;
    const assemble = clamp((intro - depth * 0.18) / (1 - depth * 0.18));
    const z = (1 - assemble) * (60 + depth * 120); // starts pushed back
    const ty = (1 - assemble) * (40 + depth * 60);
    return {
      position: "absolute",
      inset: 0,
      transform: `translate3d(${px}px, ${py + ty}px, ${-z}px) scale(${
        0.9 + assemble * 0.1
      })`,
      opacity: assemble,
      ...extra,
    };
  };

  // one specular sweep across the glass
  const sheen = clamp((t - 0.5) / 1.1);

  return (
    <AbsoluteFill
      style={{
        background: transparent ? undefined : coverBg(accent, ink),
        fontFamily: SANS,
        overflow: "hidden",
      }}
    >
      <Fonts />
      <svg width={0} height={0} style={{ position: "absolute" }}>
        <filter id="holoGrain">
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.9"
            numOctaves={2}
            stitchTiles="stitch"
          />
          <feColorMatrix type="saturate" values="0" />
        </filter>
      </svg>

      <div
        style={{
          position: "absolute",
          left: CX,
          top: CY,
          width: CARD_W,
          height: CARD_H,
          marginLeft: -CARD_W / 2,
          marginTop: -CARD_H / 2,
          perspective: 1500,
        }}
      >
        <div
          style={{
            position: "relative",
            width: "100%",
            height: "100%",
            transformStyle: "preserve-3d",
            transform: `rotateY(${rotY}deg) rotateX(${rotX}deg)`,
          }}
        >
          {/* card body */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              borderRadius: 40,
              overflow: "hidden",
              background: `linear-gradient(165deg, ${rgba("#171826", 0.96)} 0%, ${rgba(
                "#0a0b12",
                0.98
              )} 62%)`,
              border: `1px solid ${rgba("#ffffff", 0.12)}`,
              boxShadow: `0 60px 120px -40px ${rgba("#000000", 0.85)}, 0 0 90px -20px ${rgba(
                accent,
                0.4
              )}`,
              opacity: intro,
            }}
          >
            {/* glow */}
            <div style={layer(0.18, {
              background: `radial-gradient(58% 42% at 50% 30%, ${rgba(accent, 0.6)} 0%, ${rgba(accent, 0)} 70%)`,
            })} />

            {/* concentric rings */}
            <div style={layer(0.32)}>
              {[0.5, 0.72, 0.94].map((s, i) => (
                <div
                  key={i}
                  style={{
                    position: "absolute",
                    left: "50%",
                    top: "34%",
                    width: CARD_W * s,
                    height: CARD_W * s,
                    marginLeft: (-CARD_W * s) / 2,
                    marginTop: (-CARD_W * s) / 2,
                    borderRadius: "50%",
                    border: `1px solid ${rgba("#ffffff", 0.1 - i * 0.02)}`,
                  }}
                />
              ))}
            </div>

            {/* emblem orb */}
            <div style={layer(0.62)}>
              <div
                style={{
                  position: "absolute",
                  left: "50%",
                  top: "34%",
                  width: 300,
                  height: 300,
                  marginLeft: -150,
                  marginTop: -150,
                  borderRadius: "50%",
                  display: "grid",
                  placeItems: "center",
                  background: `radial-gradient(38% 34% at 36% 28%, ${rgba("#ffffff", 0.9)} 0%, ${rgba(
                    accent,
                    0.9
                  )} 42%, ${rgba("#3a0a26", 0.9)} 86%)`,
                  boxShadow: `0 30px 80px -20px ${rgba(accent, 0.8)}, inset 0 2px 10px ${rgba(
                    "#ffffff",
                    0.5
                  )}`,
                  fontSize: 140,
                  fontFamily: DISPLAY,
                  color: "#fff",
                  textShadow: `0 2px 20px ${rgba("#000", 0.4)}`,
                }}
              >
                {emblem}
              </div>
            </div>

            {/* spec chips — fanned in depth across the lower third */}
            <div style={layer(0.76)}>
              {SP.map((sp, i) => {
                const cols = SP.length <= 2 ? SP.length : 2;
                const col = i % cols;
                const row = Math.floor(i / cols);
                const gw = 300;
                const gx = CARD_W / 2 + (col - (cols - 1) / 2) * (gw + 24) - gw / 2;
                const gy = 700 + row * 96;
                return (
                  <div
                    key={i}
                    style={{
                      position: "absolute",
                      left: gx,
                      top: gy,
                      width: gw,
                      height: 76,
                      borderRadius: 16,
                      background: rgba("#ffffff", 0.05),
                      border: `1px solid ${rgba("#ffffff", 0.1)}`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "0 20px",
                      boxSizing: "border-box",
                    }}
                  >
                    <span
                      style={{
                        fontFamily: MONO,
                        fontSize: 18,
                        letterSpacing: 2,
                        color: rgba(BRAND.paper, 0.5),
                      }}
                    >
                      {sp.k}
                    </span>
                    <span
                      style={{
                        fontFamily: DISPLAY,
                        fontSize: 30,
                        color: accent,
                        fontVariantNumeric: "tabular-nums",
                      }}
                    >
                      {sp.v}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* title block */}
            <div style={layer(0.9)}>
              <div
                style={{
                  position: "absolute",
                  left: 56,
                  right: 56,
                  top: 500,
                  textAlign: "center",
                }}
              >
                {eyebrow ? (
                  <div
                    style={{
                      fontFamily: MONO,
                      fontSize: 22,
                      letterSpacing: 8,
                      color: accent,
                      marginBottom: 18,
                    }}
                  >
                    {eyebrow}
                  </div>
                ) : null}
                <div
                  style={{
                    fontFamily: DISPLAY,
                    fontSize: title.length > 14 ? 96 : 128,
                    lineHeight: 0.9,
                    color: BRAND.paper,
                    textTransform: "uppercase",
                    letterSpacing: 1,
                    textShadow: `0 6px 40px ${rgba("#000", 0.5)}`,
                  }}
                >
                  {title}
                </div>
                {subtitle ? (
                  <div
                    style={{
                      marginTop: 20,
                      fontSize: 30,
                      color: rgba(BRAND.paper, 0.66),
                      lineHeight: 1.3,
                    }}
                  >
                    {subtitle}
                  </div>
                ) : null}
              </div>
            </div>

            {/* specular sheen — one diagonal pass */}
            <div
              style={{
                position: "absolute",
                inset: 0,
                background: `linear-gradient(115deg, ${rgba("#fff", 0)} ${
                  sheen * 100 - 22
                }%, ${rgba("#fff", 0.14)} ${sheen * 100}%, ${rgba("#fff", 0)} ${
                  sheen * 100 + 22
                }%)`,
                mixBlendMode: "overlay",
                pointerEvents: "none",
              }}
            />
            {/* grain */}
            <div
              style={{
                position: "absolute",
                inset: 0,
                filter: "url(#holoGrain)",
                opacity: 0.28,
                mixBlendMode: "overlay",
                pointerEvents: "none",
              }}
            />
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const holoCardDemo: HoloCardProps = {
  eyebrow: "SHIPPED TODAY",
  title: "One-Line App",
  subtitle: "typed a sentence, got a working tool",
  emblem: "⚡",
  specs: [
    { k: "BUILD", v: "38s" },
    { k: "DEPLOY", v: "1 click" },
    { k: "COST", v: "$0" },
    { k: "STACK", v: "0 deps" },
  ],
};
