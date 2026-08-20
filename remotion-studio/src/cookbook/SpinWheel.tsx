import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BRAND, SANS, MONO, DISPLAY, rgba, clamp, Fonts, AuroraBed } from "./kit";

/* =============================================================================
   SpinWheel — a decision wheel that actually spins, as DESIGNED motion.

   Cookbook role: the "chance / decision" form, and the cookbook's first
   MOTION-HOOK component. Where SwipeDeck shows a decision being sifted and
   Odometer shows a number settling, this shows a decision being SURRENDERED to
   chance — the one interaction whose motion is the payoff.

   Why it exists (2026-08-19): the channel's measured ceiling is Shorts-feed
   selection — the swipe window, not retention. A screen recording of an app
   opening is proof, but it starts static. This component gives the first ~2s
   CONTINUOUS, on-brand motion (a wheel accelerating, blurring, easing to a
   stop, landing with a flare), so the hook moves before the real tape takes
   over as proof. Designed reveal first, real evidence second.

   The four phases, timed off `spinStart`/`spinDur` (seconds, absolute):
     P0  ARMED   — the wheel breathes, hub glows, pointer rests.
     P1  LAUNCH  — hub depresses, the wheel snaps into rotation.
     P2  SPIN    — many turns; a radial speed-smear + rim streak scale with
                   angular velocity, so fast reads as fast without a real blur.
     P3  LAND    — cubic ease-out onto `winner`'s slice centre, the pointer
                   ticks, the winning wedge lifts + brightens, a ring flares,
                   and the result pill springs up. It HOLDS the landed state,
                   so a still near the end is a finished, readable frame.

   Geometry: slices are SVG paths on a fixed viewBox, so nothing reflows and
   the wheel can never clip. The landing angle is computed so `winner` ends
   exactly under the 12-o'clock pointer — the result is authored, not random
   (Math.random is unavailable in this pipeline and would break resumability).

   JSON-safe: `options` is data ({label, emoji?}); colors are strings; no
   function props (build_ep_v2 feeds --props as JSON).
   ========================================================================== */

/** one wedge — module-local so the file exports exactly the three symbols. */
type WheelOption = {
  label: string; // wedge text (auto-sized; keep to ~12 chars for legibility)
  emoji?: string; // optional glyph drawn under the label
};

export type SpinWheelProps = {
  options: WheelOption[]; // 3–8 wedges (more than 8 stops being legible at 9:16)
  winner: number; // index in `options` the pointer lands on
  title?: string; // headline above the wheel
  kicker?: string; // tiny uppercase label over the title
  hubLabel?: string; // text in the centre hub (default "SPIN")
  resultPrefix?: string; // pill text before the winner (default "It's")
  resultSuffix?: string; // pill text after the winner
  palette?: string[]; // wedge fills, cycled; defaults to a warm food-safe set
  accent?: string; // pointer + hub + result pill (brand magenta)
  ink?: string; // backdrop fill
  spinStart?: number; // seconds before launch (default 0.35)
  spinDur?: number; // seconds of spin+land (default 2.6)
  turns?: number; // full rotations before landing (default 5)
  transparent?: boolean; // skip the backdrop (overlay use)
  /* The episode's burned claim, carried BY this component instead of by a static
     hook image. VJ 2026-08-19 asked to open on the spinning wheel rather than a
     still, but shortening the static hook made the claim flash past unread. So
     the claim now rides OVER the motion: it holds, readable, while the wheel is
     already spinning, then clears. Motion and message at the same time. */
  claimLines?: string[]; // up to 2 lines, set in Anton
  claimHot?: string;     // the one word that takes the accent
  claimHold?: number;    // seconds fully visible before it fades (default 2.2)
  /* Seconds before ANY overlay text (kicker/title/claim) appears. The hook card
     cross-dissolves for its whole life when `until` is short, so if this
     component draws its text during that window you get two offset ghost copies
     of the same words. Hold the text until the hook has fully cleared; the WHEEL
     still spins underneath from frame 0, so the opening is motion either way. */
  contentStart?: number;
  width?: number;
  height?: number;
};

const DEFAULT_PALETTE = [
  "#F2555A", // rose
  "#F79B2C", // amber
  "#FFD60A", // yellow
  "#3DBE6E", // green
  "#3FA9F5", // blue
  "#A855F7", // violet
  "#22D3EE", // cyan
  "#FF7A9C", // pink
];

const easeOutCubic = (x: number) => 1 - Math.pow(1 - clamp(x), 3);
const easeInQuad = (x: number) => clamp(x) * clamp(x);

/** polar -> cartesian on the wheel's viewBox (0deg = 12 o'clock, clockwise). */
const pt = (cx: number, cy: number, r: number, deg: number) => {
  const a = ((deg - 90) * Math.PI) / 180;
  return [cx + r * Math.cos(a), cy + r * Math.sin(a)];
};

/** an SVG wedge path from a0 -> a1 degrees. */
const wedge = (cx: number, cy: number, r: number, a0: number, a1: number) => {
  const [x0, y0] = pt(cx, cy, r, a0);
  const [x1, y1] = pt(cx, cy, r, a1);
  const large = a1 - a0 > 180 ? 1 : 0;
  return `M ${cx} ${cy} L ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1} Z`;
};

export const SpinWheel: React.FC<SpinWheelProps> = ({
  options,
  winner,
  title,
  kicker,
  hubLabel = "SPIN",
  resultPrefix = "It's",
  resultSuffix,
  palette = DEFAULT_PALETTE,
  accent = BRAND.mag,
  ink = BRAND.ink,
  spinStart = 0.35,
  spinDur = 2.6,
  turns = 5,
  transparent,
  claimLines,
  claimHot,
  claimHold = 2.2,
  contentStart = 0,
  width = 1080,
  height = 1920,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  const opts = (options || []).slice(0, 8);
  const n = Math.max(opts.length, 1);
  const win = Math.min(Math.max(winner ?? 0, 0), n - 1);
  const step = 360 / n;

  /* ---- rotation: accelerate, then cubic-ease onto the winner ----
     Wedge i spans [i*step, (i+1)*step) with its centre at (i+0.5)*step measured
     clockwise from 12 o'clock. To park that centre under the pointer we rotate
     by -(centre) plus whole turns. */
  const targetDeg = turns * 360 - (win + 0.5) * step;
  const p = clamp((t - spinStart) / Math.max(spinDur, 0.001));
  // blend a short ease-in (launch snap) into the long ease-out (landing)
  const eased = p < 0.18 ? easeInQuad(p / 0.18) * easeOutCubic(0.18) : easeOutCubic(p);
  const rot = targetDeg * eased;

  // angular velocity (deg/frame) drives the speed treatments
  const pPrev = clamp((t - 1 / fps - spinStart) / Math.max(spinDur, 0.001));
  const easedPrev =
    pPrev < 0.18 ? easeInQuad(pPrev / 0.18) * easeOutCubic(0.18) : easeOutCubic(pPrev);
  const vel = Math.abs(rot - targetDeg * easedPrev); // deg per frame
  const speed = clamp(vel / 26); // 0..1 normalised

  const landed = p >= 1;
  const landT = landed ? t - (spinStart + spinDur) : 0;

  /* ---- layout: a square wheel centred in the 9:16 box, clear of the bottom
     ~21% caption band (COOKBOOK.md rule 4). */
  const S = Math.min(width * 0.86, height * 0.46);
  const CX = width / 2;
  const CY = height * 0.495;
  const R = S / 2;

  const idle = Math.sin(t * 2.2) * (landed ? 0 : 1);
  const hubPress = p > 0 && p < 0.12 ? 1 - p / 0.12 : 0;

  // winning wedge pop
  const winPop = landed
    ? spring({ frame: frame - Math.round((spinStart + spinDur) * fps), fps, config: { damping: 12, stiffness: 180 } })
    : 0;
  const flare = landed ? clamp(landT / 0.55) : 0;

  const resultSpring = landed
    ? spring({
        frame: frame - Math.round((spinStart + spinDur + 0.12) * fps),
        fps,
        config: { damping: 14, stiffness: 160 },
      })
    : 0;

  const winLabel = opts[win]?.label ?? "";
  const winEmoji = opts[win]?.emoji ?? "";

  return (
    <AbsoluteFill
      style={{
        background: transparent ? undefined : ink,
        fontFamily: SANS,
      }}
    >
      <Fonts />
      {!transparent && <AuroraBed t={t} accent={accent} ink={ink} opacity={0.32} />}

      {/* ambient glow that brightens as it lands */}
      {!transparent && (
        <div
          style={{
            position: "absolute",
            left: CX - R * 1.5,
            top: CY - R * 1.5,
            width: R * 3,
            height: R * 3,
            borderRadius: "50%",
            background: `radial-gradient(circle, ${rgba(accent, 0.16 + flare * 0.16)} 0%, transparent 62%)`,
            filter: "blur(40px)",
          }}
        />
      )}

      {/* headline */}
      <div
        style={{
          position: "absolute",
          top: height * 0.178,   // clears a 2-line claim block (96 + ~2 lines)
          width,
          textAlign: "center",
          padding: "0 70px",
          opacity: clamp((t - contentStart) / 0.22),
        }}
      >
        {kicker && (
          <div
            style={{
              fontFamily: MONO,
              fontSize: 24,
              letterSpacing: 6,
              color: rgba(BRAND.paper, 0.72),
              marginBottom: 16,
              textTransform: "uppercase",
            }}
          >
            {kicker}
          </div>
        )}
        {title && (
          <div
            style={{
              fontFamily: DISPLAY,
              fontSize: 82,
              letterSpacing: -1,
              color: "#fff",
              lineHeight: 1.04,
            }}
          >
            {title}
          </div>
        )}
      </div>

      {/* the wheel */}
      <svg
        width={S}
        height={S}
        viewBox={`0 0 ${S} ${S}`}
        style={{
          position: "absolute",
          left: CX - R,
          top: CY - R + idle * 3,
          overflow: "visible",
        }}
      >
        <defs>
          {/* speed smear: a soft blur that only bites while the wheel is fast */}
          <filter id="sw-speed" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation={speed * 5.5} />
          </filter>
          <radialGradient id="sw-hub">
            <stop offset="0%" stopColor="#FFFFFF" />
            <stop offset="70%" stopColor={rgba(accent, 0.95)} />
            <stop offset="100%" stopColor={accent} />
          </radialGradient>
        </defs>

        {/* rim */}
        <circle cx={R} cy={R} r={R - 4} fill="none" stroke={rgba("#FFFFFF", 0.16)} strokeWidth={10} />

        <g transform={`rotate(${rot} ${R} ${R})`} filter={speed > 0.06 ? "url(#sw-speed)" : undefined}>
          {opts.map((o, i) => {
            const a0 = i * step;
            const a1 = (i + 1) * step;
            const isWin = landed && i === win;
            const [lx, ly] = pt(R, R, R * 0.66, a0 + step / 2);
            const [ex, ey] = pt(R, R, R * 0.86, a0 + step / 2);
            return (
              <g key={i} style={{ transformOrigin: `${R}px ${R}px`, transform: `scale(${1 + (isWin ? winPop * 0.035 : 0)})` }}>
                <path
                  d={wedge(R, R, R - 9, a0, a1)}
                  fill={palette[i % palette.length]}
                  stroke={rgba("#FFFFFF", 0.5)}
                  strokeWidth={3}
                  opacity={landed && !isWin ? 0.78 : 1}
                />
                {o.emoji && (
                  <text
                    x={ex}
                    y={ey}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontSize={R * 0.11}
                    transform={`rotate(${a0 + step / 2} ${ex} ${ey})`}
                  >
                    {o.emoji}
                  </text>
                )}
                <text
                  x={lx}
                  y={ly}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fill="#12121A"
                  fontSize={Math.min(R * 0.115, (R * 1.35) / Math.max(o.label.length, 5))}
                  fontWeight={900}
                  fontFamily={SANS}
                  transform={`rotate(${
                    // flip labels on the lower arc so none render upside-down
                    ((a0 + step / 2) % 360) > 90 && ((a0 + step / 2) % 360) < 270
                      ? a0 + step / 2 + 180
                      : a0 + step / 2
                  } ${lx} ${ly})`}
                >
                  {o.label}
                </text>
              </g>
            );
          })}
        </g>

        {/* landing flare ring */}
        {landed && flare > 0 && (
          <circle
            cx={R}
            cy={R}
            r={(R - 6) * (0.9 + flare * 0.16)}
            fill="none"
            stroke={rgba(accent, 0.85 * (1 - flare))}
            strokeWidth={10 * (1 - flare) + 2}
          />
        )}

        {/* hub */}
        <circle cx={R} cy={R} r={R * 0.21 * (1 - hubPress * 0.08)} fill="url(#sw-hub)" />
        <text
          x={R}
          y={R}
          textAnchor="middle"
          dominantBaseline="central"
          fill="#1A0A14"
          fontSize={R * 0.085}
          fontWeight={900}
          letterSpacing={2}
        >
          {hubLabel}
        </text>
      </svg>

      {/* pointer at 12 o'clock — ticks against the speed */}
      <div
        style={{
          position: "absolute",
          left: CX - 26,
          top: CY - R - 34,
          width: 52,
          height: 46,
          transformOrigin: "50% 90%",
          transform: `rotate(${Math.sin(t * 46) * speed * 11}deg)`,
          filter: `drop-shadow(0 6px 14px ${rgba("#000000", 0.5)})`,
        }}
      >
        <svg width={52} height={46} viewBox="0 0 52 46">
          <path d="M26 46 L2 2 L50 2 Z" fill={BRAND.paper} />
        </svg>
      </div>

      {/* the burned claim — rides over the motion, then clears */}
      {claimLines && claimLines.length > 0 && (
        <div
          style={{
            position: "absolute",
            left: 64,
            right: 64,
            top: 96,
            opacity: interpolate(
              t,
              [contentStart, contentStart + 0.18, contentStart + claimHold, contentStart + claimHold + 0.45],
              [0, 1, 1, 0],
              {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }
            ),
          }}
        >
          {claimLines.slice(0, 2).map((ln, li) => (
            <div
              key={li}
              style={{
                fontFamily: DISPLAY,
                fontSize: 104,
                lineHeight: 1.02,
                letterSpacing: -1,
                color: "#fff",
                textShadow: `0 8px 30px ${rgba("#000", 0.75)}`,
              }}
            >
              {ln.split(" ").map((wd, wi) => (
                <span
                  key={wi}
                  style={{ color: claimHot && wd.toUpperCase() === claimHot.toUpperCase() ? accent : undefined }}
                >
                  {wd}{" "}
                </span>
              ))}
            </div>
          ))}
        </div>
      )}

      {/* result pill */}
      {landed && (
        <div
          style={{
            position: "absolute",
            top: CY + R + 66,
            width,
            textAlign: "center",
            opacity: resultSpring,
            transform: `translateY(${(1 - resultSpring) * 26}px) scale(${0.9 + resultSpring * 0.1})`,
          }}
        >
          <div
            style={{
              margin: "0 auto",
              width: S,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "24px 0",
              borderTop: `1px solid ${rgba("#ffffff", 0.12)}`,
            }}
          >
            <span style={{ fontFamily: SANS, fontSize: 38, color: rgba(BRAND.paper, 0.82) }}>
              {resultPrefix}
            </span>
            <span style={{ fontFamily: DISPLAY, fontSize: 56, color: accent, letterSpacing: 0.5 }}>
              {winEmoji} {winLabel}
              {resultSuffix ? ` ${resultSuffix}` : ""}
            </span>
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};

export const spinWheelDemo: SpinWheelProps = {
  kicker: "One line built this",
  title: "What's for dinner?",
  options: [
    { label: "Biryani", emoji: "🍛" },
    { label: "Pizza", emoji: "🍕" },
    { label: "Pasta", emoji: "🍝" },
    { label: "Tacos", emoji: "🌮" },
    { label: "Sushi", emoji: "🍣" },
    { label: "Burger", emoji: "🍔" },
  ],
  winner: 0,
  resultPrefix: "Tonight:",
  spinStart: 0.35,
  spinDur: 2.6,
  turns: 5,
};
