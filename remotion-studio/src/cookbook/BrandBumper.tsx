import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { DISPLAY, Fonts, SANS, SERIF, rgba, themeTokens, type CookTheme } from "./kit";
import { enter, settle, typeOn, idle } from "./motion";

/* =============================================================================
   BrandBumper — a 1.2–2s brand/product bumper card.
   An icon (emoji or glyph) lands on a radiating ray-burst + ring-burst, the
   wordmark slides in beside/under it, an optional tagline fades up, then HOLD.
   mode:"close" adds a CTA line + a subtle pulse on the icon disc.
   Clones: VE2Uxb9Fz7I "app icon on radiating starburst bumper";
           DirGcMXm4zw "brand bumper card" + "icon-orbit constellation intro".
   HONESTY: never render another company's REAL logo here — glyph enum + text
   only. Real marks live in brandmarks.ts. This is for OUR brand / a product
   NAME, not a counterfeit of a trademarked icon.
   ========================================================================== */

export type BrandBumperProps = {
  /** the wordmark text (2–14 chars reads best) */
  name: string;
  tagline?: string;
  /** emoji shown on the disc; wins over glyph when set */
  icon?: string;
  glyph?: "bolt" | "spark" | "orbit" | "none";
  mode?: "open" | "close";
  /** CTA line for mode:"close" (default "Follow for more") */
  cta?: string;
  theme?: CookTheme;
  accent?: string;
  bg?: string;
  transparent?: boolean;
  start?: number;
};

const Glyph: React.FC<{ kind: NonNullable<BrandBumperProps["glyph"]>; color: string; size: number; t: number }> = ({
  kind, color, size, t,
}) => {
  if (kind === "none") return null;
  if (kind === "bolt")
    return (
      <svg width={size} height={size} viewBox="0 0 100 100">
        <path d="M58 6 L22 56 H48 L42 94 L78 42 H52 Z" fill={color} stroke={color} strokeWidth={4} strokeLinejoin="round" />
      </svg>
    );
  if (kind === "spark")
    return (
      <svg width={size} height={size} viewBox="0 0 100 100">
        <path d="M50 4 C54 34 66 46 96 50 C66 54 54 66 50 96 C46 66 34 54 4 50 C34 46 46 34 50 4 Z" fill={color} />
        <circle cx={78} cy={22} r={6} fill={color} />
      </svg>
    );
  // orbit — small dots circling a core, slow rotation (the constellation intro)
  const rot = t * 40;
  return (
    <svg width={size} height={size} viewBox="0 0 100 100">
      <circle cx={50} cy={50} r={13} fill={color} />
      <g transform={`rotate(${rot} 50 50)`}>
        <ellipse cx={50} cy={50} rx={42} ry={16} fill="none" stroke={color} strokeWidth={3} opacity={0.55} />
        <circle cx={92} cy={50} r={6} fill={color} />
        <circle cx={8} cy={50} r={4} fill={color} opacity={0.7} />
      </g>
      <g transform={`rotate(${-rot * 0.7 + 60} 50 50)`}>
        <ellipse cx={50} cy={50} rx={42} ry={16} fill="none" stroke={color} strokeWidth={3} opacity={0.35} />
        <circle cx={50} cy={34} r={5} fill={color} opacity={0.85} />
      </g>
    </svg>
  );
};

export const BrandBumper: React.FC<BrandBumperProps> = ({
  name = "",
  tagline,
  icon,
  glyph = "bolt",
  mode = "open",
  cta = "Follow for more",
  theme = "cream",
  accent,
  bg,
  transparent = false,
  start = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = Math.max(0, frame / fps - start);
  const tk = themeTokens(theme, accent, bg);

  // timeline (s): 0 burst grows · 0.08 icon lands · 0.42 wordmark · 0.85 tagline · 1.1 cta
  const burst = enter(t, 0, 0.55, 0.04);
  const ringP = Math.min(1, t / 0.9);
  const iconIn = enter(t, 0.08, 0.42, 0.1);
  const stamp = 1 + settle(t, 0.5, 0.5) * 0.05;
  const wordChars = typeOn(t, 0.42, name.length, 30);
  const wordIn = enter(t, 0.42, 0.4, 0.04);
  const tagIn = enter(t, 0.85, 0.4, 0.02);
  const ctaIn = mode === "close" ? enter(t, 1.1, 0.4, 0.03) : 0;
  const pulse = mode === "close" && t > 1.2 ? 1 + Math.sin((t - 1.2) * 4.2) * 0.02 : 1;
  const id = idle(t, 3, 1.6);

  const cx = 540, cy = 760;
  const discR = 150;
  const rays = 24;
  const dark = theme === "cream" ? "#1F3A34" : tk.bg;

  return (
    <div style={{ position: "absolute", width: 1080, height: 1920, overflow: "hidden", fontFamily: SANS, background: transparent ? "transparent" : tk.bg }}>
      <Fonts />

      {/* ray-burst behind the disc — radiating wedges, scaled up with mass */}
      <div style={{
        position: "absolute", left: cx, top: cy, width: 0, height: 0,
        transform: `scale(${burst}) rotate(${t * 6}deg)`, opacity: Math.min(1, burst),
      }}>
        {Array.from({ length: rays }).map((_, i) => {
          const a = (360 / rays) * i;
          const len = 560 + (i % 2) * 80;
          return (
            <div key={i} style={{
              position: "absolute", left: 0, top: -14, width: len, height: 28,
              transformOrigin: "0 50%", transform: `rotate(${a}deg)`,
              background: `linear-gradient(90deg, ${rgba(tk.accent, i % 2 ? 0.22 : 0.34)} 0%, ${rgba(tk.accent, 0)} 100%)`,
              clipPath: "polygon(0 40%, 100% 0, 100% 100%, 0 60%)",
            }} />
          );
        })}
      </div>

      {/* ring-burst: two expanding, fading rings */}
      {[0, 0.18].map((d, i) => {
        const p = Math.max(0, Math.min(1, (ringP - d) / (1 - d)));
        const r = discR + p * 340;
        return (
          <div key={i} style={{
            position: "absolute", left: cx - r, top: cy - r, width: r * 2, height: r * 2,
            borderRadius: "50%", border: `${4 - i}px solid ${rgba(tk.accent, (1 - p) * 0.7)}`,
          }} />
        );
      })}

      {/* icon disc */}
      <div style={{
        position: "absolute", left: cx - discR, top: cy - discR, width: discR * 2, height: discR * 2,
        borderRadius: "50%", background: dark,
        boxShadow: `0 30px 70px -20px ${rgba("#000", 0.55)}, inset 0 2px 0 ${rgba("#fff", 0.18)}`,
        transform: `translate(${id.x}px,${id.y}px) scale(${iconIn * stamp * pulse})`,
        display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        {icon ? (
          <div style={{ fontSize: 150, lineHeight: 1 }}>{icon}</div>
        ) : (
          <Glyph kind={glyph} color={tk.accent} size={176} t={t} />
        )}
      </div>

      {/* wordmark — types on, slides up under the disc */}
      <div style={{
        position: "absolute", left: 80, width: 920, top: cy + discR + 70,
        textAlign: "center", fontFamily: DISPLAY, fontSize: 128, lineHeight: "128px",
        letterSpacing: 2, textTransform: "uppercase", color: tk.ink,
        opacity: Math.min(1, wordIn), transform: `translateY(${(1 - wordIn) * 40}px)`,
        whiteSpace: "nowrap",
      }}>
        {name.slice(0, wordChars)}
        <span style={{ color: tk.accent, opacity: wordChars < name.length ? 1 : 0 }}>|</span>
      </div>

      {/* tagline — serif italic punch */}
      {tagline ? (
        <div style={{
          position: "absolute", left: 80, width: 920, top: cy + discR + 230,
          textAlign: "center", fontFamily: SERIF, fontStyle: "italic", fontSize: 54, lineHeight: "64px",
          color: tk.mute, opacity: Math.min(1, tagIn), transform: `translateY(${(1 - tagIn) * 24}px)`,
        }}>
          {tagline}
        </div>
      ) : null}

      {/* close variant: CTA pill */}
      {mode === "close" ? (
        <div style={{
          position: "absolute", left: 0, right: 0, top: cy + discR + 340,
          display: "flex", justifyContent: "center",
          opacity: Math.min(1, ctaIn), transform: `translateY(${(1 - ctaIn) * 24}px) scale(${pulse})`,
        }}>
          <div style={{
            padding: "18px 44px", borderRadius: 999, background: tk.accent, color: "#fff",
            fontFamily: SANS, fontWeight: 800, fontSize: 40, letterSpacing: 0.5,
            boxShadow: `0 18px 44px -16px ${rgba(tk.accent, 0.7)}`,
          }}>
            {cta}
          </div>
        </div>
      ) : null}
    </div>
  );
};

export const brandBumperDemo: BrandBumperProps = {
  name: "AI Unpacked",
  tagline: "one AI trick a day",
  glyph: "bolt",
  mode: "close",
  theme: "cream",
};
