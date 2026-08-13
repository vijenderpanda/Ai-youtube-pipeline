import React from "react";
import {
  interpolate,
  OffthreadVideo,
  spring,
  staticFile,
  useCurrentFrame,
} from "remotion";

/**
 * Build Club (Friday series) segment components — LOCKED format 2026-08-13.
 *
 * ChapterCard — full-frame chapter-book opener on a blueprint grid (the one
 *   element stolen from mockup direction B; VJ-approved).
 * PauseCard  — a beat DESIGNED to be paused: the real shared prompt, with the
 *   three section headers highlighted. Never a simplified version of the
 *   pinned prompt (BUILD-CLUB.md rule).
 * RecipeCard — screenshot-able recap: ticked steps + homework + next-chapter
 *   tease + season dots.
 * BuildRail  — persistent 3-node progress rail over the teaching window
 *   (PROMPT -> FILE -> LIVE). Rendered as an overlay from ShortProps.rail,
 *   not a segment.
 *
 * All cards keep meaningful content above y≈1400 — the karaoke caption band
 * (y1440-1517) keeps running over these beats by design.
 */

const MAG = "#E0218A";
const YELLOW = "#FFD60A";
const INK = "#0E0E14";
const TXT = "#F7F7FA";
const DIM = "#9696A4";
const FAINT = "#686878";
const CARD = "#171720";
const CARD_EDGE = "#262634";

export type ChapterPayload = {
  kicker: string;      // "BUILD CLUB"
  word: string;        // "CHAPTER"
  num: string;         // "ONE"
  chip: string;        // "YOUR IDEA GOES LIVE"
  sub: string;         // "one move, every friday"
  season: [number, number]; // [1, 6]
};
export type PausePayload = {
  title: string;                          // "PAUSE — COPY THIS PROMPT"
  lines: {t: string; hot?: boolean}[];    // the REAL prompt, abridged views
  note: string;                           // "no editing — it interviews YOU"
  sub: string;                            // "full prompt in the pinned comment"
};
export type RecipePayload = {
  title: string;
  rows: {t: string; sub: string}[];
  hwTitle: string;   // "HOMEWORK"
  hwLine: string;    // "Ship yours this week."
  hwChip: string;    // "DROP YOUR LIVE LINK 👇"
  tease: string;     // "NEXT FRIDAY · CH 2 — YOUR SITE GETS SMART"
  season: [number, number];
};
export type RailPayload = {
  labels: string[];  // ["1 PROMPT", "2 FILE", "3 LIVE"]
  starts: number[];  // absolute secs each node becomes ACTIVE
  until: number;     // absolute sec the rail hides
};

const GRID_BG: React.CSSProperties = {
  background: `linear-gradient(180deg, #0B0A10 0%, #15101B 100%)`,
};
const gridLines = (
  <div
    style={{
      position: "absolute",
      inset: 0,
      backgroundImage:
        "repeating-linear-gradient(0deg, rgba(70,66,92,0.35) 0 1px, transparent 1px 72px)," +
        "repeating-linear-gradient(90deg, rgba(70,66,92,0.35) 0 1px, transparent 1px 72px)",
    }}
  />
);

const SeasonDots: React.FC<{season: [number, number]; y: number}> = ({season, y}) => {
  const [filled, n] = season;
  return (
    <div
      style={{
        position: "absolute",
        top: y,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        gap: 26,
      }}
    >
      {Array.from({length: n}, (_, i) => (
        <div
          key={i}
          style={{
            width: 28,
            height: 28,
            borderRadius: 14,
            background: i < filled ? MAG : "transparent",
            border: i < filled ? "none" : `2px solid ${FAINT}`,
          }}
        />
      ))}
    </div>
  );
};

// ---------------------------------------------------------------- ChapterCard
export const ChapterCard: React.FC<{chapter: ChapterPayload; fps: number}> = ({
  chapter,
  fps,
}) => {
  const f = useCurrentFrame();
  const up = (delay: number) =>
    spring({frame: f - delay, fps, config: {damping: 16, stiffness: 120}});
  const s1 = up(2);
  const s2 = up(7);
  const s3 = up(13);
  const s4 = up(19);
  return (
    <div style={{position: "absolute", inset: 0, ...GRID_BG}}>
      {gridLines}
      {/* magenta bloom behind the chapter number — kills the flat-ink dead feel */}
      <div
        style={{
          position: "absolute",
          top: 420,
          left: -200,
          right: -200,
          height: 1100,
          background:
            "radial-gradient(ellipse 52% 44% at 50% 52%, rgba(224,33,138,0.34) 0%, rgba(224,33,138,0.10) 55%, transparent 75%)",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 386,
          width: "100%",
          textAlign: "center",
          fontFamily: "Anton",
          fontSize: 40,
          letterSpacing: 16,
          color: DIM,
          opacity: s1,
        }}
      >
        {chapter.kicker}
      </div>
      <div
        style={{
          position: "absolute",
          top: 464,
          width: "100%",
          textAlign: "center",
          fontFamily: "Anton",
          fontSize: 150,
          letterSpacing: 6,
          color: TXT,
          opacity: s2,
          transform: `translateY(${(1 - s2) * 40}px)`,
        }}
      >
        {chapter.word}
      </div>
      <div
        style={{
          position: "absolute",
          top: 596,
          width: "100%",
          textAlign: "center",
          fontFamily: "Anton",
          fontSize: 340,
          letterSpacing: 8,
          color: MAG,
          opacity: s3,
          transform: `scale(${0.7 + 0.3 * s3})`,
          textShadow: "0 0 90px rgba(224,33,138,0.55)",
        }}
      >
        {chapter.num}
      </div>
      <div
        style={{
          position: "absolute",
          top: 1108,
          width: "100%",
          display: "flex",
          justifyContent: "center",
          opacity: s4,
        }}
      >
        <div
          style={{
            background: YELLOW,
            color: INK,
            fontFamily: "Anton",
            fontSize: 60,
            letterSpacing: 2,
            padding: "20px 46px",
            transform: `rotate(-3deg) scale(${0.8 + 0.2 * s4})`,
          }}
        >
          {chapter.chip}
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          top: 1256,
          width: "100%",
          textAlign: "center",
          fontFamily: "Helvetica Neue, Helvetica",
          fontSize: 38,
          color: DIM,
          opacity: s4,
        }}
      >
        {chapter.sub}
      </div>
      <SeasonDots season={chapter.season} y={1352} />
    </div>
  );
};

// ----------------------------------------------------------------- PauseCard
export const PauseCard: React.FC<{pause: PausePayload; fps: number}> = ({
  pause,
  fps,
}) => {
  const f = useCurrentFrame();
  const t = f / fps;
  const enter = spring({frame: f, fps, config: {damping: 15, stiffness: 130}});
  const pulse = 1 + 0.06 * Math.sin(t * Math.PI * 2 * 1.1);
  return (
    <div style={{position: "absolute", inset: 0, ...GRID_BG}}>
      <div
        style={{
          position: "absolute",
          top: 300,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          opacity: enter,
        }}
      >
        <div
          style={{
            width: 96,
            height: 96,
            borderRadius: 48,
            background: YELLOW,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 12,
            transform: `scale(${pulse})`,
          }}
        >
          <div style={{width: 12, height: 44, borderRadius: 4, background: INK}} />
          <div style={{width: 12, height: 44, borderRadius: 4, background: INK}} />
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          top: 430,
          width: "100%",
          textAlign: "center",
          fontFamily: "Anton",
          fontSize: 60,
          letterSpacing: 2,
          color: TXT,
          opacity: enter,
        }}
      >
        {pause.title}
      </div>
      <div
        style={{
          position: "absolute",
          top: 550,
          left: 96,
          right: 96,
          bottom: 750,
          borderRadius: 32,
          background: CARD,
          border: `3px solid ${YELLOW}`,
          padding: "44px 52px",
          opacity: enter,
        }}
      >
        {pause.lines.map((ln, i) => {
          const lo = interpolate(f, [4 + i * 2, 10 + i * 2], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <div
              key={i}
              style={{
                fontFamily: "SF Mono, Menlo, monospace",
                fontSize: 34,
                lineHeight: 1.9,
                color: ln.hot ? YELLOW : TXT,
                opacity: lo,
              }}
            >
              {ln.t}
            </div>
          );
        })}
      </div>
      <div
        style={{
          position: "absolute",
          top: 1218,
          width: "100%",
          textAlign: "center",
          fontFamily: "Helvetica Neue, Helvetica",
          fontWeight: 700,
          fontSize: 36,
          color: MAG,
          opacity: enter,
        }}
      >
        {pause.note}
      </div>
      <div
        style={{
          position: "absolute",
          top: 1274,
          width: "100%",
          textAlign: "center",
          fontFamily: "Helvetica Neue, Helvetica",
          fontSize: 30,
          color: DIM,
          opacity: enter,
        }}
      >
        {pause.sub}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- RecipeCard
export const RecipeCard: React.FC<{recipe: RecipePayload; fps: number}> = ({
  recipe,
  fps,
}) => {
  const f = useCurrentFrame();
  const up = (delay: number) =>
    spring({frame: f - delay, fps, config: {damping: 16, stiffness: 120}});
  const sTitle = up(0);
  const sHw = up(26);
  const sTease = up(34);
  return (
    <div style={{position: "absolute", inset: 0, ...GRID_BG}}>
      <div
        style={{
          position: "absolute",
          top: 210,
          width: "100%",
          textAlign: "center",
          fontFamily: "Anton",
          fontSize: 96,
          letterSpacing: 3,
          color: TXT,
          opacity: sTitle,
        }}
      >
        {recipe.title}
      </div>
      {recipe.rows.map((r, i) => {
        const s = up(8 + i * 6);
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              top: 372 + i * 156,
              left: 72,
              right: 72,
              height: 132,
              borderRadius: 26,
              background: CARD,
              border: `2px solid ${CARD_EDGE}`,
              opacity: s,
              transform: `translateX(${(1 - s) * 60}px)`,
              display: "flex",
              alignItems: "center",
            }}
          >
            <svg width="60" height="60" style={{marginLeft: 34}} viewBox="0 0 60 60">
              <circle cx="30" cy="30" r="26" stroke="#56D68A" strokeWidth="3" fill="none" />
              <path
                d="M18 30 L27 40 L43 19"
                stroke="#56D68A"
                strokeWidth="5"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <div style={{marginLeft: 26}}>
              <div
                style={{
                  fontFamily: "Helvetica Neue, Helvetica",
                  fontWeight: 700,
                  fontSize: 38,
                  color: TXT,
                }}
              >
                {r.t}
              </div>
              <div
                style={{
                  fontFamily: "Helvetica Neue, Helvetica",
                  fontSize: 27,
                  color: DIM,
                  marginTop: 4,
                }}
              >
                {r.sub}
              </div>
            </div>
          </div>
        );
      })}
      <div
        style={{
          position: "absolute",
          top: 872,
          left: 72,
          right: 72,
          height: 252,
          borderRadius: 32,
          background: "#351020",
          border: `3px solid ${MAG}`,
          padding: "28px 44px",
          opacity: sHw,
          transform: `translateY(${(1 - sHw) * 40}px)`,
        }}
      >
        <div
          style={{
            fontFamily: "Anton",
            fontSize: 34,
            letterSpacing: 5,
            color: MAG,
          }}
        >
          {recipe.hwTitle}
        </div>
        <div
          style={{
            fontFamily: "Helvetica Neue, Helvetica",
            fontWeight: 700,
            fontSize: 44,
            color: TXT,
            marginTop: 10,
          }}
        >
          {recipe.hwLine}
        </div>
        <div
          style={{
            display: "inline-block",
            marginTop: 18,
            background: YELLOW,
            color: INK,
            fontFamily: "Helvetica Neue, Helvetica",
            fontWeight: 700,
            fontSize: 34,
            padding: "14px 30px",
            borderRadius: 36,
          }}
        >
          {recipe.hwChip}
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          top: 1180,
          width: "100%",
          textAlign: "center",
          fontFamily: "Helvetica Neue, Helvetica",
          fontWeight: 700,
          fontSize: 35,
          color: YELLOW,
          opacity: sTease,
        }}
      >
        {recipe.tease}
      </div>
      <SeasonDots season={recipe.season} y={1268} />
    </div>
  );
};

// ------------------------------------------------------------------ PhoneFrame
/** High-end Android device casing for real phone recordings (VJ 2026-08-13:
 * "case the recording in a good high-end android phone placeholder").
 * Drawn bezel — punch-hole camera, glass corners, side keys, float shadow —
 * over the series grid; no trademarked device. Footage 1080x2400 cover-fits
 * the screen. Captions ride the low strip (capLow), under the device. */
export const PhoneFrame: React.FC<{
  seg: {src?: string; from?: number};
  fps: number;
}> = ({seg, fps}) => {
  const W = 620;
  const H = 1310;
  const left = (1080 - W) / 2;
  return (
    <div style={{position: "absolute", inset: 0, ...GRID_BG}}>
      {gridLines}
      <div
        style={{
          position: "absolute",
          top: 250,
          left: left - 7,
          width: 7,
          height: 0,
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 470,
          left: left - 7,
          width: 7,
          height: 130,
          borderRadius: 4,
          background: "#2a2a33",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 440,
          left: left + W,
          width: 7,
          height: 95,
          borderRadius: 4,
          background: "#2a2a33",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 250,
          left,
          width: W,
          height: H,
          borderRadius: 66,
          background: "linear-gradient(160deg, #3d3d47 0%, #17171e 60%)",
          boxShadow:
            "0 60px 130px rgba(0,0,0,0.7), 0 0 0 2px rgba(255,255,255,0.09), 0 14px 60px rgba(224,33,138,0.14)",
          padding: 13,
        }}
      >
        <div
          style={{
            width: "100%",
            height: "100%",
            borderRadius: 54,
            overflow: "hidden",
            background: "#000",
            position: "relative",
          }}
        >
          <OffthreadVideo
            src={seg.src!.startsWith("http") ? seg.src! : staticFile(seg.src!)}
            startFrom={Math.round((seg.from ?? 0) * fps)}
            muted
            style={{width: "100%", height: "100%", objectFit: "cover"}}
          />
          <div
            style={{
              position: "absolute",
              top: 16,
              left: "50%",
              transform: "translateX(-50%)",
              width: 26,
              height: 26,
              borderRadius: 13,
              background: "#000",
              border: "2px solid #1e1e26",
            }}
          />
        </div>
      </div>
    </div>
  );
};

// ------------------------------------------------------------------ BuildRail
export const BuildRail: React.FC<{rail: RailPayload; t: number; fps: number}> = ({
  rail,
  t,
  fps,
}) => {
  if (t < rail.starts[0] - 0.1 || t >= rail.until) {
    return null;
  }
  const active = rail.starts.reduce((acc, s, i) => (t >= s ? i : acc), 0);
  const appear = Math.min(1, Math.max(0, (t - (rail.starts[0] - 0.1)) / 0.4));
  const segW = 288;
  const gap = 24;
  return (
    <div
      style={{
        position: "absolute",
        top: 170,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        gap,
        opacity: appear,
        transform: `translateY(${(1 - appear) * -24}px)`,
      }}
    >
      {rail.labels.map((lab, i) => {
        const done = i < active;
        const isActive = i === active;
        return (
          <div
            key={i}
            style={{
              width: segW,
              height: 64,
              borderRadius: 32,
              background: done ? MAG : isActive ? YELLOW : "rgba(23,23,32,0.82)",
              border: `2px solid ${done ? MAG : isActive ? YELLOW : CARD_EDGE}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 10,
              fontFamily: "Helvetica Neue, Helvetica",
              fontWeight: 700,
              fontSize: 28,
              color: done || isActive ? INK : FAINT,
            }}
          >
            {done ? (
              <svg width="26" height="26" viewBox="0 0 26 26">
                <path
                  d="M5 13 L11 19 L21 7"
                  stroke={INK}
                  strokeWidth="4"
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            ) : null}
            {lab}
          </div>
        );
      })}
    </div>
  );
};
