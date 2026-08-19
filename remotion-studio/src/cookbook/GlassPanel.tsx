import React from "react";
import {
  AbsoluteFill,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BRAND, SANS, MONO, DISPLAY, rgba, clamp, Fonts } from "./kit";

/* =============================================================================
   GlassPanel — the Liquid-Glass-2026 material as a usable component: a frosted,
   REFRACTIVE panel floating over a live color bed, carrying a headline figure and
   a few key/value rows. This is the "style" flex — a premium surface that admits
   it's sitting on top of something and bends what's underneath.
   Cookbook role: device-ui / material. The glassy way to present ONE hero
   number + supporting detail with taste (vs. StatBars' quantified bars or
   BentoGrid's dense grid).

   HOW THE GLASS IS REAL (and render-safe)
   - `backdrop-filter` is unreliable in headless Chromium, so the refraction is
     BAKED: the same color bed is drawn a SECOND time, clipped to the panel,
     scaled up ~6% and blurred hard — that layer IS the light bent through the
     glass. Over it sit an inset white hairline, a moving specular sheen, and a
     bright caustic top edge. The look survives a render exactly.
   - `transparent` switches modes: over a live composition it drops the bed and
     falls back to a real `backdrop-filter` blur of whatever is behind, so the
     panel still reads as glass as an overlay.

   9:16 SAFE: panel is 840×920 centered at (540, 900) → bottom ≈1360, clear of the
   y=1517 caption band; ≥120px side margins. Headline auto-sizes; rows are capped
   at 4 and single-line. JSON-safe throughout.
   ========================================================================== */

export type GlassPanelProps = {
  /** tiny label at the top of the panel, e.g. "THIS WEEK". */
  eyebrow?: string;
  /** the hero value (big) — a number or a very short phrase, e.g. "41,200". */
  headline: string;
  /** one line under the headline, e.g. "views · +38% vs last week". */
  caption?: string;
  /** up to 4 supporting key/value rows shown inside the glass. */
  rows?: { k: string; v: string }[];
  accent?: string; // brand accent (defaults to Sol magenta)
  ink?: string; // base fill (also tints the bed)
  start?: number; // seconds before the panel flies in
  width?: number;
  height?: number;
  transparent?: boolean; // overlay mode: drop the bed, use backdrop-filter
};

const PW = 840;
const PH = 920;
const CX = 540;
const CY = 900;

/** the color bed — drifting blobs, drawn once behind and once (blurred) as the
    refraction sample inside the glass. */
const Bed: React.FC<{ t: number; accent: string; ink: string }> = ({
  t,
  accent,
  ink,
}) => {
  const blob = (
    x: number,
    y: number,
    r: number,
    color: string,
    ph: number
  ): React.CSSProperties => ({
    position: "absolute",
    left: `${x + Math.sin(t * 0.4 + ph) * 6}%`,
    top: `${y + Math.cos(t * 0.33 + ph) * 6}%`,
    width: r,
    height: r,
    marginLeft: -r / 2,
    marginTop: -r / 2,
    borderRadius: "50%",
    background: color,
    filter: "blur(70px)",
  });
  return (
    <div style={{ position: "absolute", inset: 0, background: ink }}>
      <div style={blob(28, 26, 620, accent, 0)} />
      <div style={blob(74, 34, 560, "#2F6BFF", 1.3)} />
      <div style={blob(50, 82, 640, BRAND.cyan, 2.1)} />
      <div style={blob(82, 74, 460, "#C43BFF", 3.0)} />
    </div>
  );
};

export const GlassPanel: React.FC<GlassPanelProps> = ({
  eyebrow = "THIS WEEK",
  headline,
  caption,
  rows = [],
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

  const R = rows.slice(0, 4);

  const intro = clamp(
    spring({
      frame: frame - start * fps,
      fps,
      config: { damping: 16, mass: 0.8, stiffness: 110 },
    })
  );
  const scale = 0.86 + intro * 0.14;
  const sheen = clamp((t - 0.4) / 1.3); // one specular pass

  const left = CX - PW / 2;
  const top = CY - PH / 2;

  return (
    <AbsoluteFill style={{ fontFamily: SANS, overflow: "hidden" }}>
      <Fonts />

      {/* the color bed (skipped in overlay mode — the composition is the bed) */}
      {!transparent ? <Bed t={t} accent={accent} ink={ink} /> : null}

      <div
        style={{
          position: "absolute",
          left,
          top,
          width: PW,
          height: PH,
          transform: `scale(${scale})`,
          transformOrigin: "50% 50%",
          opacity: intro,
          borderRadius: 48,
          overflow: "hidden",
          border: `1px solid ${rgba("#ffffff", 0.35)}`,
          boxShadow: `0 50px 110px -40px ${rgba("#000", 0.7)}, inset 0 1px 0 ${rgba(
            "#ffffff",
            0.5
          )}, inset 0 -1px 0 ${rgba("#ffffff", 0.08)}`,
          backdropFilter: transparent ? "blur(26px) saturate(180%)" : undefined,
          WebkitBackdropFilter: transparent ? "blur(26px) saturate(180%)" : undefined,
          background: transparent ? rgba("#0b0c14", 0.28) : undefined,
        }}
      >
        {/* BAKED refraction: the bed again, clipped to the panel, blown up + blurred */}
        {!transparent ? (
          <div
            style={{
              position: "absolute",
              left: -left * 1.06 - PW * 0.03,
              top: -top * 1.06 - PH * 0.03,
              width: width * 1.06,
              height: height * 1.06,
              filter: "blur(26px) saturate(200%) brightness(1.08)",
            }}
          >
            <Bed t={t} accent={accent} ink={ink} />
          </div>
        ) : null}

        {/* frost wash so text stays legible over the bright refraction */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: `linear-gradient(160deg, ${rgba("#0a0b12", 0.34)} 0%, ${rgba(
              "#0a0b12",
              0.5
            )} 100%)`,
          }}
        />
        {/* caustic bright top edge */}
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: 0,
            height: 3,
            background: `linear-gradient(90deg, ${rgba("#fff", 0)} 0%, ${rgba(
              "#fff",
              0.7
            )} 50%, ${rgba("#fff", 0)} 100%)`,
          }}
        />

        {/* ── content ─────────────────────────────────────────────────────── */}
        <div style={{ position: "absolute", inset: 0, padding: 60 }}>
          {eyebrow ? (
            <div
              style={{
                fontFamily: MONO,
                fontSize: 24,
                letterSpacing: 6,
                color: rgba(BRAND.paper, 0.72),
                opacity: clamp((intro - 0.2) / 0.6),
              }}
            >
              {eyebrow}
            </div>
          ) : null}

          <div
            style={{
              fontFamily: DISPLAY,
              fontSize: headline.length > 8 ? 150 : 210,
              lineHeight: 0.92,
              color: "#fff",
              marginTop: 18,
              letterSpacing: -1,
              fontVariantNumeric: "tabular-nums",
              textShadow: `0 4px 40px ${rgba(accent, 0.5)}`,
              opacity: clamp((intro - 0.25) / 0.6),
            }}
          >
            {headline}
          </div>

          {caption ? (
            <div
              style={{
                fontSize: 32,
                color: rgba(BRAND.paper, 0.82),
                marginTop: 10,
                opacity: clamp((intro - 0.35) / 0.6),
              }}
            >
              {caption}
            </div>
          ) : null}

          {/* rows */}
          <div
            style={{
              position: "absolute",
              left: 60,
              right: 60,
              bottom: 60,
              display: "flex",
              flexDirection: "column",
              gap: 0,
            }}
          >
            {R.map((r, i) => {
              const rIn = clamp((intro - 0.4 - i * 0.08) / 0.5);
              return (
                <div
                  key={r.k}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "22px 4px",
                    borderTop: `1px solid ${rgba("#ffffff", 0.12)}`,
                    opacity: rIn,
                    transform: `translateX(${(1 - rIn) * 18}px)`,
                  }}
                >
                  <span
                    style={{
                      fontSize: 28,
                      letterSpacing: 1,
                      color: rgba(BRAND.paper, 0.66),
                    }}
                  >
                    {r.k}
                  </span>
                  <span
                    style={{
                      fontFamily: DISPLAY,
                      fontSize: 40,
                      color: accent,
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {r.v}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* specular sweep across the whole panel */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: `linear-gradient(118deg, ${rgba("#fff", 0)} ${
              sheen * 130 - 26
            }%, ${rgba("#fff", 0.22)} ${sheen * 130}%, ${rgba("#fff", 0)} ${
              sheen * 130 + 26
            }%)`,
            mixBlendMode: "overlay",
            pointerEvents: "none",
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

export const glassPanelDemo: GlassPanelProps = {
  eyebrow: "THIS WEEK",
  headline: "41,200",
  caption: "views · +38% vs last week",
  rows: [
    { k: "Retention @30s", v: "71%" },
    { k: "New subscribers", v: "+512" },
    { k: "Avg watch", v: "0:34" },
    { k: "Best hook", v: "Ep 16" },
  ],
};
