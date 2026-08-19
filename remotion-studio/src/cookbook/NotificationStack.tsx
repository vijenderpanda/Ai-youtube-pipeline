import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BRAND, SANS, DISPLAY, rgba, clamp, coverBg, Fonts } from "./kit";

/* =============================================================================
   NotificationStack — frosted lock-screen alerts that pile up with real depth.
   Cookbook role: the invented DEPTH wow. Where LineReveal is the trend form and
   BentoGrid is the "many facts at once" form, this is the "results ACCRUE" form —
   a beat that says an assistant is *doing work while you watch*: drafts land,
   summaries post, tasks get pulled, one alert after another.

   WHY THIS LAYOUT
   - A phone lock-screen (clock + a growing "N new" tally) is a metaphor the eye
     decodes in well under a second — no legend, no reading required to grok
     "things are stacking up." That instant read is what buys the 15s hold.
   - The physics sell it: each new card drops from the top, lands crisp IN FRONT,
     and shoves the whole deck down/back — older cards scale down, shift down,
     dim, and blur into a receding staircase. The freshest result is always the
     sharp one you read; the pile behind it is the story ("look how much it did").
   - Everything is time-sliced off `start`: cards arrive one per `perNote`, the
     newest springs in, the rest ease to their new depth, and the composition
     LANDS holding the finished deck so a still near the end reads as complete.

   9:16 SAFE: cards are 84px off both edges; the deck is anchored in the upper-
   middle and the deepest card bottoms out well above y=1517 (the caption band).
   Titles are single-line-ellipsised and bodies are 2-line-clamped, so no string
   can ever overflow its card. Notes are capped at 5. JSON-safe throughout: no
   function props — glyphs/labels are plain strings, the accent card is a bool.
   ========================================================================== */

export type NotificationStackProps = {
  /** the alerts, oldest → newest (the LAST one ends crisp in front). Cap ~5. */
  notes: {
    app: string; // source app name, e.g. "Prompt Deck"
    title: string; // bold headline (single line — ellipsised if long)
    body: string; // 1–2 line detail (clamped to 2 lines)
    time?: string; // right-aligned timestamp, e.g. "now", "2m" (default "now")
    icon?: string; // glyph for the app tile (emoji ok); falls back to app initial
    accent?: boolean; // tint this card's tile/glow with the brand accent
  }[];
  perNote?: number; // seconds between arrivals (default 0.9)
  clock?: string; // lock-screen time text (default "9:41")
  dateLabel?: string; // lock-screen date line (default a friendly date)
  accent?: string; // brand accent (defaults to Sol magenta)
  ink?: string; // base fill
  start?: number; // seconds before the first card drops
  width?: number;
  height?: number;
  transparent?: boolean; // skip the backdrop (overlay use inside a composition)
};

/* on-brand tile gradients cycled by note index; the accent card overrides. */
const ICON_GRADS: [string, string][] = [
  ["#22D3EE", "#3B82F6"], // cyan → blue
  ["#A855F7", "#6366F1"], // violet → indigo
  ["#FFD60A", "#FB923C"], // yellow → orange
  ["#34D399", "#14B8A6"], // mint → teal
];

/* emoji-first stack so color glyphs render across mac/win headless Chromium,
   falling back to the system sans (never blocks on a web font). */
const GLYPH = '"Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji", ' + SANS;

export const NotificationStack: React.FC<NotificationStackProps> = ({
  notes,
  perNote = 0.9,
  clock = "9:41",
  dateLabel = "Tuesday, August 19",
  accent = BRAND.mag,
  ink = BRAND.ink,
  start = 0.3,
  width = 1080,
  height = 1920,
  transparent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const cards = notes.slice(0, 5);
  const N = cards.length;

  // seconds since the deck began; which card is the newest arrived (front)
  const step = perNote > 0 ? perNote : 0.9; // guard: never divide by 0
  const t = frame / fps - start;
  const m = t < 0 ? -1 : Math.min(N - 1, Math.floor(t / step));

  // entry progress of the current newest card — this single spring drives BOTH
  // the newcomer's drop-in AND every older card's ease to its deeper slot.
  const arriveFrame = (start + Math.max(m, 0) * step) * fps;
  const ep =
    m < 0
      ? 0
      : spring({
          frame: frame - arriveFrame,
          fps,
          config: { damping: 15, mass: 0.9, stiffness: 110 },
        });
  const epC = clamp(ep);

  // deck geometry
  const SIDE = 84;
  const W = width - SIDE * 2;
  const cardH = 248;
  const stackTop = Math.round(height * 0.34);
  const peek = 128; // px of each older card's HEADER kept visible above the next
  const scaleStep = 0.05; // …deeper cards shrink by this
  const dimStep = 0.17; // …and dim by this
  const blurStep = 1.2; // …and blur by this (receding frost)
  const maxDepth = 3; // cards deeper than this collapse into the same back slot
  const D = Math.min(Math.max(m, 0), maxDepth); // fan size behind the newest card

  // 2-line clamp for the body (vendor props set via any to satisfy TS)
  const clampBox: React.CSSProperties = { display: "-webkit-box", overflow: "hidden" };
  (clampBox as any).WebkitBoxOrient = "vertical";
  (clampBox as any).WebkitLineClamp = 2;

  /* The newest card lands crisp at the FRONT (lowest slot); every older card
     fans UP behind it, each leaving a `peek`-tall header strip (icon + app +
     title) visible, shrinking/dimming/blurring with depth. When a new card
     arrives the whole pile eases up one slot — effDepth carries the fractional
     ease via epC. zIndex (10+i in the render) keeps the newest drawn on top. */
  const place = (i: number) => {
    if (i === m) {
      const rise = (1 - epC) * 46; // slides up into the front slot as it settles
      return {
        scale: interpolate(epC, [0, 1], [0.94, 1]),
        ty: D * peek + rise,
        opacity: clamp(epC / 0.5),
        blur: 0,
        entering: true,
      };
    }
    const effDepth = Math.min(Math.max(m - i - (1 - epC), 0), maxDepth);
    return {
      scale: 1 - effDepth * scaleStep,
      ty: (D - effDepth) * peek, // deeper → higher up (smaller ty), header peeks out
      opacity: clamp(1 - effDepth * dimStep, 0.34, 1),
      blur: effDepth * blurStep,
      entering: false,
    };
  };

  const tile = (i: number, isAccent?: boolean): string =>
    isAccent
      ? `linear-gradient(150deg, #FF6EC7 0%, ${accent} 100%)`
      : `linear-gradient(150deg, ${ICON_GRADS[i % ICON_GRADS.length][0]} 0%, ${
          ICON_GRADS[i % ICON_GRADS.length][1]
        } 100%)`;

  return (
    <AbsoluteFill
      style={{
        background: transparent ? undefined : coverBg(accent, ink),
        fontFamily: SANS,
        overflow: "hidden",
      }}
    >
      <Fonts />

      {/* ── lock-screen chrome: padlock, clock, date ─────────────────────── */}
      <div
        style={{
          position: "absolute",
          top: Math.round(height * 0.075),
          width: "100%",
          textAlign: "center",
        }}
      >
        <svg width={44} height={48} viewBox="0 0 44 48" style={{ opacity: 0.72, marginBottom: 8 }}>
          <rect x={9} y={20} width={26} height={22} rx={6} fill="none" stroke={BRAND.paper} strokeWidth={3} />
          <path d="M14 20 v-4 a8 8 0 0 1 16 0 v4" fill="none" stroke={BRAND.paper} strokeWidth={3} />
          <circle cx={22} cy={30} r={2.6} fill={BRAND.paper} />
        </svg>
        <div
          style={{
            fontSize: 138,
            fontWeight: 300,
            letterSpacing: -3,
            lineHeight: 0.9,
            color: rgba(BRAND.paper, 0.97),
            textShadow: `0 8px 40px ${rgba("#000000", 0.4)}`,
          }}
        >
          {clock}
        </div>
        <div
          style={{
            marginTop: 12,
            fontSize: 30,
            fontWeight: 600,
            letterSpacing: 4,
            textTransform: "uppercase",
            color: rgba(BRAND.paper, 0.55),
          }}
        >
          {dateLabel}
        </div>
      </div>

      {/* ── "N new" tally — literally counts the pile as it grows ─────────── */}
      {m >= 0 ? (
        <div
          style={{
            position: "absolute",
            top: stackTop - 128,
            width: "100%",
            display: "flex",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 18,
              padding: "14px 34px 14px 26px",
              borderRadius: 999,
              background: rgba("#ffffff", 0.08),
              border: `1px solid ${rgba("#ffffff", 0.14)}`,
              boxShadow: `inset 0 1px 0 ${rgba("#ffffff", 0.2)}`,
            }}
          >
            <span
              style={{
                width: 18,
                height: 18,
                borderRadius: 999,
                background: accent,
                boxShadow: `0 0 18px ${rgba(accent, 0.9)}`,
              }}
            />
            <span
              style={{
                fontFamily: DISPLAY,
                fontSize: 54,
                lineHeight: 0.9,
                color: accent,
                display: "inline-block",
                transform: `scale(${1 + (1 - epC) * 0.12})`,
                transformOrigin: "center",
              }}
            >
              {m + 1}
            </span>
            <span
              style={{
                fontSize: 30,
                fontWeight: 700,
                letterSpacing: 3,
                textTransform: "uppercase",
                color: rgba(BRAND.paper, 0.82),
              }}
            >
              New Alerts
            </span>
          </div>
        </div>
      ) : null}

      {/* accent glow bloom behind the deck for depth */}
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: stackTop + 40,
          width: 800,
          height: 460,
          marginLeft: -400,
          background: `radial-gradient(circle at 50% 40%, ${rgba(accent, 0.34)} 0%, ${rgba(
            accent,
            0
          )} 68%)`,
          filter: "blur(46px)",
          zIndex: 0,
        }}
      />

      {/* ── the receding card deck ───────────────────────────────────────── */}
      {cards.map((note, i) => {
        if (i > m) return null; // not arrived yet
        const p = place(i);
        const isAccent = !!note.accent;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: "50%",
              top: stackTop,
              width: W,
              marginLeft: -W / 2,
              transformOrigin: "50% 0%",
              transform: `translateY(${p.ty}px) scale(${p.scale})`,
              opacity: p.opacity,
              filter: p.blur ? `blur(${p.blur}px)` : undefined,
              zIndex: 10 + i,
            }}
          >
            <div
              style={{
                height: cardH,
                boxSizing: "border-box",
                display: "flex",
                gap: 26,
                padding: 32,
                borderRadius: 44,
                background: isAccent
                  ? `linear-gradient(180deg, ${rgba(accent, 0.22)}, ${rgba(accent, 0.1)}), linear-gradient(180deg, ${rgba(
                      "#ffffff",
                      0.13
                    )}, ${rgba("#ffffff", 0.06)})`
                  : `linear-gradient(180deg, ${rgba("#ffffff", 0.14)}, ${rgba("#ffffff", 0.06)})`,
                backdropFilter: "blur(30px)",
                WebkitBackdropFilter: "blur(30px)",
                border: `1px solid ${rgba("#ffffff", isAccent ? 0.24 : 0.16)}`,
                boxShadow: `0 30px 60px ${rgba("#000000", 0.5)}, inset 0 1px 0 ${rgba(
                  "#ffffff",
                  0.28
                )}${isAccent ? `, 0 0 0 1px ${rgba(accent, 0.35)}` : ""}`,
                overflow: "hidden",
              }}
            >
              {/* app tile */}
              <div style={{ position: "relative", flexShrink: 0 }}>
                <div
                  style={{
                    width: 108,
                    height: 108,
                    borderRadius: 28,
                    background: tile(i, isAccent),
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontFamily: note.icon ? GLYPH : DISPLAY,
                    fontSize: note.icon ? 54 : 58,
                    color: "#ffffff",
                    boxShadow: `0 10px 26px ${rgba(isAccent ? accent : ICON_GRADS[i % ICON_GRADS.length][0], 0.5)}, inset 0 1px 0 ${rgba(
                      "#ffffff",
                      0.4
                    )}`,
                  }}
                >
                  {note.icon || note.app.charAt(0).toUpperCase()}
                </div>
                {/* pulse ring on the freshest card only */}
                {p.entering ? (
                  <div
                    style={{
                      position: "absolute",
                      inset: 0,
                      borderRadius: 28,
                      border: `3px solid ${accent}`,
                      opacity: (1 - epC) * 0.6,
                      transform: `scale(${1 + (1 - epC) * 0.5})`,
                    }}
                  />
                ) : null}
              </div>

              {/* text column */}
              <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
                <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
                  <span
                    style={{
                      flex: 1,
                      minWidth: 0,
                      fontSize: 26,
                      fontWeight: 700,
                      letterSpacing: 2.5,
                      textTransform: "uppercase",
                      color: rgba(BRAND.paper, 0.6),
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {note.app}
                  </span>
                  <span style={{ fontSize: 26, fontWeight: 600, color: rgba(BRAND.paper, 0.45), whiteSpace: "nowrap" }}>
                    {note.time || "now"}
                  </span>
                </div>
                <div
                  style={{
                    marginTop: 6,
                    fontSize: 42,
                    fontWeight: 800,
                    letterSpacing: 0.2,
                    color: BRAND.paper,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {note.title}
                </div>
                <div
                  style={{
                    ...clampBox,
                    marginTop: 8,
                    fontSize: 33,
                    lineHeight: 1.28,
                    color: rgba(BRAND.paper, 0.74),
                  }}
                >
                  {note.body}
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

export const notificationStackDemo: NotificationStackProps = {
  clock: "9:41",
  dateLabel: "Tuesday, August 19",
  perNote: 0.9,
  notes: [
    {
      app: "Prompt Deck",
      title: "Research compiled",
      body: "12 sources summarized into a one-page brief with citations.",
      time: "6m",
      icon: "🔎",
    },
    {
      app: "Prompt Deck",
      title: "Meeting notes saved",
      body: "Full transcript plus highlights saved to your workspace.",
      time: "4m",
      icon: "📝",
    },
    {
      app: "Prompt Deck",
      title: "3 tasks extracted",
      body: "Pulled 3 to-dos from your call and added them to Today.",
      time: "2m",
      icon: "✅",
    },
    {
      app: "Prompt Deck",
      title: "Summary sent to Slack",
      body: "Recap posted to #product with action items highlighted.",
      time: "1m",
      icon: "💬",
    },
    {
      app: "Prompt Deck",
      title: "Draft ready",
      body: "Your launch email is drafted — 3 subject-line options included.",
      time: "now",
      icon: "✉️",
      accent: true,
    },
  ],
};
