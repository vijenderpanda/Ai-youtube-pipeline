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
   SwipeDeck — a Tinder-style stack of option cards where the rejects fling away
   one by one and the last one standing gets slammed with a "PICKED" stamp.
   Cookbook role: the invented DECISION wow. Where NotificationStack is the
   "results ACCRUE" form and LineReveal is the "trend" form, this is the
   "a CHOICE gets made" form — a beat that says the model didn't just answer, it
   *sifted*: it held several options up, threw out the weak ones, and committed
   to the sharp one.

   WHY THIS LAYOUT
   - A swipe deck is a metaphor the eye decodes instantly: a fanned pile of cards,
     the top one crisp, the rest peeking below. No legend, no reading required to
     grok "these are competing options." That instant read is what buys the 15s.
   - The verdict lives in the motion, not in prose. Each reject card carries its
     own damning one-liner ("too vague"), then physically swipes off-screen with a
     red NOPE slapped across it — alternating left/right like a thumb flick — and
     the next contender rises into focus underneath. You *watch* options die.
   - The payoff is a single held frame: when only the winner remains it scales up,
     its frost warms to the accent, a glow blooms, and a rotated stamp slams in
     with an overshoot + impact ring. A still near the end reads as "decided."
   - Everything is time-sliced off `start`. One continuous `advance` value (the
     summed fling-progress of every reject) drives the whole rig: the flinging
     card flies, and every card behind it eases forward one slot at the same time.
     Between swipes there's a short hold so each contender gets a readable beat.

   9:16 SAFE: the 772px card is centered (154px off both edges); the fanned pile
   bottoms out near y≈1275, and the scaled-up winner near y≈1190 — both clear of
   the y>1517 caption band. Titles are 2-line-clamped and notes single-line, so no
   string can overflow its card. Cards are capped at 6. JSON-safe throughout: no
   function props — the verdict is the card's `note` string, the badge text is
   `stampText`, and the winner is simply the LAST card in the array.
   ========================================================================== */

export type SwipeDeckProps = {
  /** option cards in judging order. Every card except the LAST flings away as a
      reject; the LAST card is the winner that stays and gets stamped. Cap ~6. */
  cards: {
    title: string; // the option text (2-line clamp — never overflows)
    note?: string; // short verdict, e.g. "too vague" / "sharp + specific"
  }[];
  stampText?: string; // badge slammed onto the winner (default "PICKED")
  rejectText?: string; // label smeared across each flung reject (default "NOPE")
  prompt?: string; // small eyebrow: the decision being made
  perSwipe?: number; // seconds per card = swipe + settle hold (default 0.9)
  accent?: string; // brand accent — winner stamp/glow (default Sol magenta)
  ink?: string; // base fill
  start?: number; // seconds before the first card flings
  width?: number;
  height?: number;
  transparent?: boolean; // skip the backdrop (overlay use inside a composition)
};

/* small SVG verdict markers so the check/cross never depend on a symbol font. */
const Check: React.FC<{ c: string; s?: number }> = ({ c, s = 26 }) => (
  <svg width={s} height={s} viewBox="0 0 24 24">
    <path d="M4.5 12.5l4.5 4.5L19.5 6" fill="none" stroke={c} strokeWidth={3.4} strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
const Cross: React.FC<{ c: string; s?: number }> = ({ c, s = 24 }) => (
  <svg width={s} height={s} viewBox="0 0 24 24">
    <path d="M6 6l12 12M18 6L6 18" fill="none" stroke={c} strokeWidth={3.4} strokeLinecap="round" />
  </svg>
);

const REJECT_RED = "#FF3B6B";

export const SwipeDeck: React.FC<SwipeDeckProps> = ({
  cards,
  stampText = "PICKED",
  rejectText = "NOPE",
  prompt = "Pick the best",
  perSwipe = 0.9,
  accent = BRAND.mag,
  ink = BRAND.ink,
  start = 0.4,
  width = 1080,
  height = 1920,
  transparent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const deck = cards.slice(0, 6);
  const N = deck.length;
  const winnerIdx = N - 1;
  const REJECTS = Math.max(N - 1, 0);

  const step = perSwipe > 0 ? perSwipe : 0.9; // guard divide-by-zero
  const flingDur = step * 0.6; // seconds a card takes to leave; rest is a hold
  const t = frame / fps - start;

  // per-reject fling progress 0..1; their SUM is a continuous "deck advance"
  // in [0, N-1] — the single value that drives the whole rig.
  const flingOf = (i: number) => (i >= REJECTS ? 0 : clamp((t - i * step) / flingDur));
  let advance = 0;
  for (let i = 0; i < REJECTS; i++) advance += flingOf(i);
  const front = Math.min(Math.floor(advance + 1e-6), winnerIdx); // current top index

  // winner celebration — fires the instant the last reject clears frame
  const winnerRevealSec = REJECTS > 0 ? (REJECTS - 1) * step + flingDur : 0;
  const winAnchor = (start + winnerRevealSec + 0.12) * fps;
  const ws = clamp(
    spring({ frame: frame - winAnchor, fps, config: { damping: 13, mass: 0.85, stiffness: 120 } })
  );
  const stampRaw = spring({
    frame: frame - winAnchor - Math.round(0.06 * fps),
    fps,
    config: { damping: 9, mass: 0.7, stiffness: 150 },
  });
  const stampP = clamp(stampRaw); // 0..1 for opacity / ring
  // slam from big → 1 with a tiny spring bounce. Amplitude kept at 0.9 so the
  // largest *visible* frame (~1.9x, while opacity is still ramping in) never
  // pushes the rotated badge past the 1080 right edge.
  const stampScale = 1 + (1 - stampRaw) * 0.9;

  // deck geometry — centered, upper-middle, clear of the caption band
  const CARD_W = 772;
  const CARD_H = 596;
  const cx = width / 2;
  const stackTop = Math.round(height * 0.3);
  const cardMidY = stackTop + CARD_H / 2;
  const maxDepth = 3;
  // stamp + impact-ring center: over the winner card's upper-right, but pulled
  // in from the +232 edge so the slam-in scale transient stays inside 1080px.
  const stampCX = cx + 200;
  const stampCY = stackTop + 4;

  type Placed = {
    fling: boolean;
    tx: number;
    ty: number;
    rot: number;
    scale: number;
    opacity: number;
    blur: number;
    dir: number;
    p: number;
    z: number;
  } | null;

  const place = (i: number): Placed => {
    const depth = i - advance; // 0 = crisp front; grows toward the back
    if (i < REJECTS && depth <= -1 + 1e-3) return null; // fully flung — gone

    if (depth < 0) {
      // this card is mid-fling (depth in (-1,0)); p = how far it has swiped
      const p = -depth;
      const dir = i % 2 === 0 ? -1 : 1; // alternate thumb-flick left / right
      const e = Math.pow(p, 1.7); // accelerate off-screen
      return {
        fling: true,
        tx: dir * width * 1.35 * e,
        ty: 78 * p,
        rot: dir * 22 * p,
        scale: 1 - p * 0.03,
        opacity: 1 - clamp((p - 0.5) / 0.38),
        blur: 0,
        dir,
        p,
        z: (N - i) * 10 + 5,
      };
    }

    // resting fan — front card crisp, each one behind peeks/dims/blurs
    const d = Math.min(depth, maxDepth);
    const sign = i % 2 === 0 ? 1 : -1;
    return {
      fling: false,
      tx: sign * d * 11,
      ty: d * 34,
      rot: sign * d * 2.4,
      scale: 1 - d * 0.055,
      opacity: clamp(1 - d * 0.22, 0.22, 1),
      blur: d * 0.9,
      dir: 0,
      p: 0,
      z: (N - i) * 10,
    };
  };

  // 2-line clamp for the card title (vendor props via any to satisfy TS)
  const clampBox: React.CSSProperties = { display: "-webkit-box", overflow: "hidden" };
  (clampBox as any).WebkitBoxOrient = "vertical";
  (clampBox as any).WebkitLineClamp = 2;

  return (
    <AbsoluteFill
      style={{
        background: transparent ? undefined : coverBg(accent, ink),
        fontFamily: SANS,
        overflow: "hidden",
      }}
    >
      <Fonts />

      {/* ── header: the decision + a live pip row that sheds rejects ───────── */}
      <div style={{ position: "absolute", top: Math.round(height * 0.088), width: "100%", textAlign: "center", zIndex: 40 }}>
        <div style={{ fontSize: 34, fontWeight: 700, letterSpacing: 6, textTransform: "uppercase", color: rgba(BRAND.paper, 0.5) }}>
          {prompt}
        </div>
        <div style={{ marginTop: 26, display: "flex", justifyContent: "center", alignItems: "center", gap: 16 }}>
          {deck.map((_, i) => {
            const rejected = i < REJECTS && flingOf(i) >= 0.5;
            const won = i === winnerIdx && ws > 0.05;
            const isFront = i === front && !won;
            const sz = won ? 30 : rejected ? 15 : 20;
            const col = won ? accent : rejected ? rgba(REJECT_RED, 0.7) : rgba(BRAND.paper, isFront ? 0.95 : 0.4);
            return (
              <span
                key={i}
                style={{
                  width: sz,
                  height: sz,
                  borderRadius: 999,
                  background: col,
                  transition: "none",
                  boxShadow: won
                    ? `0 0 22px ${rgba(accent, 0.95)}`
                    : isFront
                    ? `0 0 14px ${rgba(BRAND.paper, 0.5)}`
                    : "none",
                  transform: `scale(${isFront ? 1.08 : 1})`,
                }}
              />
            );
          })}
        </div>
      </div>

      {/* accent glow bloom behind the deck — swells when the winner locks in */}
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: cardMidY - 240,
          width: 900,
          height: 620,
          marginLeft: -450,
          background: `radial-gradient(circle at 50% 45%, ${rgba(accent, 0.24 + ws * 0.34)} 0%, ${rgba(accent, 0)} 66%)`,
          filter: "blur(52px)",
          zIndex: 1,
        }}
      />

      {/* ── the swipe deck ────────────────────────────────────────────────── */}
      {deck.map((card, i) => {
        const pl = place(i);
        if (!pl) return null;
        const isWinner = i === winnerIdx;
        const winScale = isWinner ? ws * 0.06 : 0;

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: cx - CARD_W / 2,
              top: stackTop,
              width: CARD_W,
              transformOrigin: "50% 50%",
              transform: `translate(${pl.tx}px, ${pl.ty}px) rotate(${pl.rot}deg) scale(${pl.scale + winScale})`,
              opacity: pl.opacity,
              filter: pl.blur ? `blur(${pl.blur}px)` : undefined,
              zIndex: pl.z,
            }}
          >
            <div
              style={{
                position: "relative",
                height: CARD_H,
                boxSizing: "border-box",
                display: "flex",
                flexDirection: "column",
                padding: 46,
                borderRadius: 52,
                background: isWinner
                  ? `linear-gradient(180deg, ${rgba(accent, 0.16 * ws)}, ${rgba(accent, 0.05 * ws)}), linear-gradient(180deg, ${rgba("#ffffff", 0.15)}, ${rgba("#ffffff", 0.06)})`
                  : `linear-gradient(180deg, ${rgba("#ffffff", 0.15)}, ${rgba("#ffffff", 0.06)})`,
                backdropFilter: "blur(30px)",
                WebkitBackdropFilter: "blur(30px)",
                border: `1px solid ${isWinner ? rgba(accent, 0.2 + ws * 0.5) : rgba("#ffffff", 0.16)}`,
                boxShadow: `0 40px 80px ${rgba("#000000", 0.55)}, inset 0 1px 0 ${rgba("#ffffff", 0.3)}${
                  isWinner && ws > 0 ? `, 0 0 0 ${(2.5 * ws).toFixed(2)}px ${rgba(accent, 0.55)}, 0 0 90px ${rgba(accent, 0.4 * ws)}` : ""
                }`,
                overflow: "hidden",
              }}
            >
              {/* top row: option index + a small verdict glyph */}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span
                  style={{
                    fontSize: 26,
                    fontWeight: 800,
                    letterSpacing: 4,
                    textTransform: "uppercase",
                    color: rgba(BRAND.paper, 0.5),
                    padding: "10px 20px",
                    borderRadius: 999,
                    background: rgba("#ffffff", 0.07),
                    border: `1px solid ${rgba("#ffffff", 0.12)}`,
                  }}
                >
                  {`Option ${String(i + 1).padStart(2, "0")}`}
                </span>
                <span
                  style={{
                    width: 56,
                    height: 56,
                    borderRadius: 999,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    background: isWinner ? rgba(accent, 0.18) : rgba(REJECT_RED, 0.14),
                    border: `1.5px solid ${isWinner ? rgba(accent, 0.6) : rgba(REJECT_RED, 0.45)}`,
                  }}
                >
                  {isWinner ? <Check c={accent} s={30} /> : <Cross c={REJECT_RED} s={26} />}
                </span>
              </div>

              {/* the option text — the thing being chosen between */}
              <div
                style={{
                  ...clampBox,
                  marginTop: 34,
                  flex: 1,
                  fontSize: 60,
                  fontWeight: 800,
                  lineHeight: 1.12,
                  letterSpacing: -0.5,
                  color: BRAND.paper,
                }}
              >
                {card.title}
              </div>

              {/* verdict note — muted ✕ for rejects, accent ✓ for the winner */}
              {card.note ? (
                <div style={{ display: "flex", alignItems: "center", gap: 16, marginTop: 20 }}>
                  {isWinner ? <Check c={accent} s={30} /> : <Cross c={rgba(BRAND.paper, 0.45)} s={26} />}
                  <span
                    style={{
                      fontSize: 36,
                      fontWeight: 700,
                      letterSpacing: 1,
                      color: isWinner ? accent : rgba(BRAND.paper, 0.5),
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {card.note}
                  </span>
                </div>
              ) : null}

              {/* NOPE smear that slaps across a card as it swipes away */}
              {pl.fling ? (
                <div
                  style={{
                    position: "absolute",
                    top: "34%",
                    left: 0,
                    width: "100%",
                    display: "flex",
                    justifyContent: "center",
                    opacity: clamp(pl.p * 7),
                    transform: `rotate(${pl.dir < 0 ? 13 : -13}deg)`,
                  }}
                >
                  <span
                    style={{
                      fontFamily: DISPLAY,
                      fontSize: 118,
                      lineHeight: 0.9,
                      letterSpacing: 4,
                      color: REJECT_RED,
                      padding: "10px 34px",
                      borderRadius: 22,
                      border: `7px solid ${REJECT_RED}`,
                      background: rgba(REJECT_RED, 0.1),
                      textShadow: `0 6px 24px ${rgba(REJECT_RED, 0.5)}`,
                    }}
                  >
                    {rejectText}
                  </span>
                </div>
              ) : null}
            </div>
          </div>
        );
      })}

      {/* ── the winning stamp: impact ring + rubber-stamp slam ────────────── */}
      {N > 0 && stampP > 0.001 ? (
        <>
          {/* impact ring — expands and fades at the moment of the slam */}
          <div
            style={{
              position: "absolute",
              left: stampCX,
              top: stampCY,
              width: 260,
              height: 260,
              marginLeft: -130,
              marginTop: -130,
              borderRadius: 999,
              border: `6px solid ${accent}`,
              opacity: (1 - stampP) * 0.7,
              transform: `scale(${interpolate(stampP, [0, 1], [0.35, 2.3])})`,
              zIndex: 190,
            }}
          />
          {/* the badge */}
          <div
            style={{
              position: "absolute",
              left: stampCX,
              top: stampCY,
              transform: `translate(-50%, -50%) rotate(-12deg) scale(${stampScale})`,
              transformOrigin: "50% 50%",
              opacity: clamp(stampP * 3),
              zIndex: 200,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 14,
                padding: "16px 32px 16px 26px",
                borderRadius: 20,
                background: accent,
                border: `4px solid ${rgba("#ffffff", 0.92)}`,
                boxShadow: `0 16px 44px ${rgba(accent, 0.75)}, inset 0 2px 0 ${rgba("#ffffff", 0.35)}`,
              }}
            >
              <span
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: 999,
                  background: rgba("#ffffff", 0.95),
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Check c={accent} s={30} />
              </span>
              <span style={{ fontFamily: DISPLAY, fontSize: 66, lineHeight: 0.9, letterSpacing: 3, color: "#ffffff" }}>
                {stampText}
              </span>
            </div>
          </div>
        </>
      ) : null}
    </AbsoluteFill>
  );
};

export const swipeDeckDemo: SwipeDeckProps = {
  prompt: "Which prompt wins?",
  stampText: "PICKED",
  rejectText: "NOPE",
  perSwipe: 0.95,
  cards: [
    { title: "Make me a logo", note: "too vague" },
    { title: "Cool modern logo", note: "still vague" },
    {
      title: "Wordmark, geometric sans, magenta on ink — 3 SVG variants",
      note: "sharp + specific",
    },
  ],
};
