import React from "react";
import {
  AbsoluteFill,
  Easing,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {
  BRAND, SANS, MONO, DISPLAY, rgba, clamp, Fonts, AuroraBed,
  glassChrome,
} from "./kit";
import { resolveBrand, CAT_HUE, type BrandCat } from "./brandmarks";

/* =============================================================================
   TapStack — the receipt that will not stop arriving.

   Cookbook role: the MOTION HOOK for a spend episode. It exists because the
   channel's opening frame is measurably losing — relativeRetentionPerformance
   reads 0.43 at the first sampled point, i.e. below the median comparable Short
   from half a second in, before any content exists. Shorts has no thumbnail, so
   the first frame is the only image that argues for the watch.

   THE DESIGN RULE IT IS BUILT ON: an autobiographical/real image is recognised
   in ~150-250ms; a designed ABSTRACTION takes 700-1200ms. So frame 0 is ONE
   NAMEABLE OBJECT and nothing else — a UPI payment receipt with the four
   over-learned cues (PAID TO / merchant medallion / green success ring / a big
   rupee figure), drawn in our own glass language rather than photographed.
   No headline, no HUD, no second card. Legibility requires no run-up.

   The mechanic is arithmetic, not vibe: the gap between arrivals shrinks and
   then plateaus at 4 frames. Contraction is spent before 0.8s (where the
   measurement is) and the floor is the densest rate that still resolves at 2x
   playback, which Shorts now offers.

   STRUCTURALLY UNSPOILABLE — and that is a deliberate constraint, not an
   omission. The film withholds its hero figure and pays it out one digit at a
   time, completing at 20.43s. This component has no HUD, no tally, no total, no
   counter and no digit plate, and it CANNOT draw one. A competing hook concept
   was disqualified for opening on four sealed digit plates above the word
   BLINKIT — leaking the payoff's shape at frame 0.

   It also never captures anything. The pile recedes and leaves an EMPTY
   container for the real tape to fill: a graphic may hand off a container, never
   an artifact. Manufacturing a "screenshot" out of drawn cards would assert that
   the tape came from the graphic, which is false.

   HONESTY: every card is a transaction that exists in the creator's real data.
   Person-to-person cards carry merchant "" — the identity is absent from the
   PROPS, not hidden at render — and draw a mask plate where the name would be,
   with the amount still visible. That move is in the hook, not bolted on later.

   Geometry constants are mirrored in ScreenStage (the handoff rect). Change one,
   change both. JSON-safe props only; Math.random is banned pipeline-wide.
   ========================================================================== */

/* ---- geometry ------------------------------------------------------------ */
const CARD_X = 100;
const CARD_W = 880;
const CARD_H = 500;
const CARD_TOP = 560;
const STRIP = 196; // visible height of an older card once pushed down
const SETTLE = Easing.bezier(0.2, 0.9, 0.25, 1);

/* handoff container — MIRRORED FROM ScreenStage: HW = width*0.92, insetScale
   0.62, aspect 16:9 inverted. Do not retype these; they are derived. */
const HO_W = 616;
const HO_H = 1095;
const HO_X = 232;
const HO_Y = 412;

/** Brand hues are authored for each brand's own ground. On a near-white
 *  receipt a light mark (Blinkit #F8CB46) drops under 2:1 and the letter
 *  disappears. Darken toward black until it clears ~4.5:1 on paper. */
const onPaper = (hex: string): string => {
  const h = hex.replace("#", "");
  let r = parseInt(h.slice(0, 2), 16),
      g = parseInt(h.slice(2, 4), 16),
      b = parseInt(h.slice(4, 6), 16);
  const lum = (R: number, G: number, B: number) => {
    const f = (c: number) => {
      const v = c / 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * f(R) + 0.7152 * f(G) + 0.0722 * f(B);
  };
  for (let k = 0; k < 24; k++) {
    if ((1.05) / (lum(r, g, b) + 0.05) >= 4.5) break;
    r = Math.round(r * 0.9); g = Math.round(g * 0.9); b = Math.round(b * 0.9);
  }
  return `#${[r, g, b].map((c) => c.toString(16).padStart(2, "0")).join("")}`;
};

/** seeded jitter — Math.random breaks resumability, see LedgerFlow */
const jit = (i: number) => Math.sin(i * 12.9898 + 4.1414);

export type TapCard = {
  id: string;
  /** merchant as printed. EMPTY STRING for person-to-person — the name never
   *  enters the props at all. */
  merchant: string;
  amount: number;
  day?: string;
  /** our own category label — NOT a brand claim. Used to colour merchants that
   *  have no licence-clean mark, so an unknown payee still reads as a KIND of
   *  spend instead of a generic grey chip. */
  cat?: BrandCat;
  masked?: boolean;
  /** mark this card without explaining it — used for the figure a later beat kills */
  hot?: boolean;
};

export type TapStackProps = {
  cards: TapCard[]; // capped 14
  /** absolute land times in seconds, one per card. Explicit, never derived at
   *  render time — the cadence is the story and must be auditable. */
  gaps?: number[];
  /** the first line, burned over the motion. Small on purpose: it must be
   *  witnessed at the ~0.5s sample without winning first fixation. */
  claimLines?: string[];
  claimHot?: string;
  claimAt?: number;
  claimOut?: number;
  /** the open loop. Zero digits, zero merchant, zero aggregate. */
  debt?: string;
  debtHot?: string;
  debtAt?: number;
  /** provenance, in words — never by manufacturing phone chrome */
  provenance?: string;
  /** the denominator, planted free under the hero amount */
  unitLabel?: string;
  maskLabel?: string;
  /** the pile recedes and leaves an empty container for real tape */
  handoffAt?: number;
  start?: number;
  accent?: string;
  ink?: string;
  transparent?: boolean;
  width?: number;
  height?: number;
};

const money = (n: number) => "₹" + n.toLocaleString("en-IN");

/* ---- one receipt --------------------------------------------------------- */
/* A PAYMENT RECEIPT IS A WHITE CARD. The first version drew these in the
   channel's glass language and the aurora refracted straight through them, so
   each "receipt" rendered as a magenta-to-blue gradient panel — beautiful, and
   recognised as nothing. The whole component rests on frame 0 being nameable in
   ~200ms, so the surface is opaque near-white with dark ink, exactly like the
   PhonePe/GPay receipts this audience taps several times a day. It also means
   the stack can never merge into the background, whatever the bed is doing. */
const Receipt: React.FC<{
  card: TapCard; t: number; landed: number; hero: boolean;
  accent: string; maskLabel: string; unitLabel?: string;
}> = ({ card, t, landed, hero, accent, maskLabel, unitLabel }) => {
  const b = resolveBrand(card.merchant, !!card.masked);
  // an unrecognised merchant falls back to its CATEGORY hue rather than the
  // neutral chip — the stack has to read as varied spend inside 2.55s
  const hue = b.kind === "wordmark" && b.cat === "other" && card.cat
    ? CAT_HUE[card.cat] : b.hex;
  const since = t - landed;
  const flash = clamp(1 - since / 0.12);
  const hotFlash = card.hot ? clamp(1 - since / 0.16) : 0;
  const PAPER = "#FBFBFD";
  const INK = "#15151E";
  return (
    <div
      style={{
        position: "absolute", left: 0, top: 0, width: CARD_W, height: CARD_H,
        borderRadius: 34, overflow: "hidden",
        background: `linear-gradient(180deg, ${PAPER} 0%, #EFEFF4 100%)`,
        border: `1px solid ${rgba("#ffffff", 0.7)}`,
        boxShadow: card.hot && hotFlash > 0
          ? `0 0 ${8 + hotFlash * 26}px ${rgba(accent, hotFlash * 0.9)}, 0 34px 76px -24px ${rgba("#000", 0.86)}`
          : `0 34px 76px -24px ${rgba("#000", 0.86)}, inset 0 1px 0 ${rgba("#ffffff", 0.9)}`,
      }}
    >
      {/* arrival flash — a receipt lights once as it lands, then goes quiet */}
      {flash > 0 ? (
        <div style={{ position: "absolute", inset: 0,
                      background: rgba("#ffffff", flash * 0.3) }} />
      ) : null}
      {/* brand edge bar — carries identity once the card is a 196px strip */}
      <div style={{ position: "absolute", left: 0, top: 0, width: 12, height: "100%",
                    background: card.masked ? "#9A9AAE" : hue }} />
      {/* medallion + success ring — two of the four over-learned cues */}
      <div style={{
        position: "absolute", left: 46, top: 48, width: 112, height: 112, borderRadius: 56,
        background: rgba(card.masked ? "#9A9AAE" : hue, 0.14),
        border: `3.5px solid ${card.masked ? rgba("#9A9AAE", 0.5) : "#1FA85C"}`,
        display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        {card.masked ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
            {[42, 30, 20].map((w, k) => (
              <div key={k} style={{ width: w, height: 7, borderRadius: 4, background: rgba(INK, 0.22) }} />
            ))}
          </div>
        ) : b.kind === "glyph" && b.d ? (
          <svg viewBox="0 0 24 24" width={52} height={52} fill={onPaper(hue)}><path d={b.d} /></svg>
        ) : (
          <span style={{ fontFamily: SANS, fontSize: 50, fontWeight: 800, color: onPaper(hue) }}>
            {(card.merchant || "?").charAt(0).toUpperCase()}
          </span>
        )}
      </div>
      {!card.masked ? (
        <div style={{
          position: "absolute", left: 128, top: 132, width: 38, height: 38, borderRadius: 19,
          background: "#1FA85C", border: `3px solid ${PAPER}`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 20, lineHeight: "20px", color: "#fff", fontWeight: 900,
        }}>✓</div>
      ) : null}
      <div style={{ position: "absolute", left: 196, top: 56, fontFamily: MONO, fontSize: 25,
                    letterSpacing: 4, color: rgba(INK, 0.42) }}>PAID TO</div>
      {card.masked ? (
        <div style={{ position: "absolute", left: 196, top: 98, fontFamily: MONO, fontSize: 30,
                      letterSpacing: 1.5, color: rgba(INK, 0.5) }}>{maskLabel}</div>
      ) : (
        <div style={{ position: "absolute", left: 196, top: 92, fontFamily: SANS, fontSize: 54,
                      fontWeight: 700, color: INK, whiteSpace: "nowrap" }}>{card.merchant}</div>
      )}
      {card.day ? (
        <div style={{ position: "absolute", right: 46, top: 58, fontFamily: MONO, fontSize: 26,
                      color: rgba(INK, 0.36) }}>{card.day}</div>
      ) : null}
      {/* hairline — the tear-off rule every receipt has */}
      <div style={{ position: "absolute", left: 46, right: 46, top: 208, height: 1,
                    background: rgba(INK, 0.1) }} />
      <div style={{
        position: "absolute", left: 196, top: 252, fontFamily: DISPLAY, fontSize: 156,
        lineHeight: "150px", fontVariantNumeric: "tabular-nums",
        color: card.hot ? "#B8104A" : INK,
      }}>{money(card.amount)}</div>
      {hero && unitLabel ? (
        <div style={{ position: "absolute", left: 200, top: 418, fontFamily: MONO, fontSize: 27,
                      letterSpacing: 5, color: rgba(INK, 0.4) }}>{unitLabel}</div>
      ) : null}
    </div>
  );
};

/* ---- component ----------------------------------------------------------- */
export const TapStack: React.FC<TapStackProps> = ({
  cards = [],
  gaps,
  claimLines,
  claimHot,
  claimAt = 0.467,
  claimOut = 1.8,
  debt,
  debtHot,
  debtAt = 1.933,
  provenance,
  unitLabel,
  maskLabel = "PERSONAL — HIDDEN",
  handoffAt = 2.2,
  start = 0,
  accent = BRAND.mag,
  ink = BRAND.ink,
  transparent,
  width = 1080,
  height = 1920,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - start;
  const C = (cards || []).slice(0, 14);
  const LAND = gaps && gaps.length >= C.length
    ? gaps
    : C.map((_, i) => (i === 0 ? 0 : 0.3 + (i - 1) * 0.133));

  /* -- stack maths: depth, push-down, group scale ------------------------- */
  const settled = (k: number) => SETTLE(clamp((t - LAND[k]) / 0.18));
  const depth = (i: number) => {
    let d = 0;
    for (let k = i + 1; k < C.length; k++) d += settled(k);
    return d;
  };
  let L = 0;
  for (let k = 0; k < C.length; k++) L += clamp((t - LAND[k]) / 0.18);
  const K = clamp(1 - 0.029 * Math.max(0, L - 1), 0.681, 1);
  const drift = STRIP * 0.06 * Math.sin(t * 0.9) + Math.max(0, t - 1.733) * 26;

  /* -- the recede: nothing is captured ------------------------------------ */
  const rec = SETTLE(clamp((t - handoffAt) / 0.3));
  const groupK = K - rec * (K - 0.44);

  /* -- burned copy --------------------------------------------------------- */
  const claimIn = clamp((t - claimAt) / 0.25);
  const claimOff = clamp((t - claimOut) / 0.117);
  const claimOp = claimIn * (1 - claimOff);
  const debtIn = clamp((t - debtAt) / 0.167);
  const debtOff = clamp((t - (debtAt + 0.367)) / 0.12);
  const debtOp = debtIn * (1 - debtOff);
  const rule = clamp((t - (debtAt + 0.167)) / 0.15);
  const provOp = clamp(t / 0.1) * (1 - clamp((t - 2.2) / 0.12));
  const hoIn = clamp((t - handoffAt) / 0.3);

  const word = (s: string, hot?: string, size = 76) =>
    s.split(" ").map((w, i) => (
      <span key={i} style={{
        color: hot && w.replace(/[^A-Za-z]/g, "").toUpperCase() === hot.toUpperCase()
          ? accent : BRAND.paper,
      }}>{w}{" "}</span>
    ));

  return (
    <AbsoluteFill style={{ width, height, background: transparent ? undefined : ink }}>
      <Fonts />
      {transparent ? null : <AuroraBed t={t} accent={accent} ink={ink} opacity={0.34} />}

      {/* provenance — stated in WORDS, never by faking phone chrome */}
      {provenance ? (
        <div style={{
          position: "absolute", left: CARD_X, top: 494, fontFamily: MONO, fontSize: 24,
          letterSpacing: 3, color: rgba(BRAND.paper, 0.38 * provOp),
        }}>{provenance}</div>
      ) : null}

      {/* the stack */}
      <div style={{
        position: "absolute", left: 0, top: CARD_TOP, width,
        transformOrigin: "540px 0px",
        transform: `scale(${groupK}) translateY(${rec * -120}px)`,
        opacity: 1 - rec,
        filter: rec > 0.02 ? `blur(${rec * 6}px)` : undefined,
      }}>
        {C.map((c, i) => {
          if (t < LAND[i] - 0.4) return null;
          // THE HERO DOES NOT ARRIVE. Card 0 is the ground state — fully present,
          // unanimated, at frame 0. Every other card springs in on top of it.
          // Springing the hero would make frame 0 an empty aurora, which is the
          // exact failure this component was built to prevent: on Shorts there is
          // no thumbnail, so frame 0 is the only image that argues for the watch.
          const sp = i === 0 ? 1 : spring({
            frame: frame - Math.round((start + LAND[i]) * fps),
            fps, config: { damping: 15, stiffness: 190, mass: 0.8 },
          });
          const d = depth(i);
          const y = STRIP * d + (1 - sp) * -170 + drift;
          return (
            <div key={c.id} style={{
              position: "absolute", left: CARD_X, top: y, width: CARD_W, height: CARD_H,
              transform: `scale(${1 + (1 - sp) * 0.1}) rotate(${jit(i) * 0.8 * clamp(d)}deg)`,
              opacity: sp * clamp(1 - d * 0.05, 0.28, 1),
              zIndex: i, // newest in front — it landed last
            }}>
              <Receipt card={c} t={t} landed={LAND[i]} hero={i === 0}
                       accent={accent} maskLabel={maskLabel}
                       unitLabel={i === 0 ? unitLabel : undefined} />
              {d > 0.02 ? (
                <div style={{
                  position: "absolute", inset: 0, borderRadius: 34,
                  background: rgba(ink, Math.min(0.48, d * 0.04)),
                }} />
              ) : null}
            </div>
          );
        })}
      </div>

      {/* bottom scrim — the rest of the pile falls into the dark */}
      <div style={{
        position: "absolute", left: 0, right: 0, top: 1330, height: 590,
        background: `linear-gradient(180deg, ${rgba(ink, 0)} 0%, ${rgba(ink, 1)} 100%)`,
      }} />

      {/* the claim — small on purpose */}
      {claimLines?.length ? (
        <div style={{
          position: "absolute", left: 56, right: 56, top: 210,
          opacity: claimOp, transform: `translateY(${claimOff * -34}px)`,
        }}>
          {claimLines.slice(0, 2).map((ln, i) => (
            <div key={i} style={{
              fontFamily: DISPLAY, fontSize: 76, lineHeight: "70px",
              textShadow: `0 6px 40px ${rgba(ink, 0.9)}`,
            }}>{word(ln, claimHot)}</div>
          ))}
        </div>
      ) : null}

      {/* the debt — an open loop with ZERO digits for the 5-7s knee to pay */}
      {debt ? (
        <div style={{
          position: "absolute", left: 56, right: 56, top: 210,
          opacity: debtOp, transform: `translateY(${debtOff * -26}px)`,
        }}>
          <div style={{ fontFamily: DISPLAY, fontSize: 92, lineHeight: "86px",
                        textShadow: `0 6px 40px ${rgba(ink, 0.9)}` }}>
            {word(debt, debtHot)}
          </div>
          <div style={{ marginTop: 14, height: 2, width: 560 * rule, background: accent }} />
        </div>
      ) : null}

      {/* THE CONTAINER — empty. A graphic hands off a container, never an artifact. */}
      {hoIn > 0 ? (
        <div style={{
          position: "absolute", left: HO_X, top: HO_Y, width: HO_W, height: HO_H,
          borderRadius: 40,
          border: `2px solid ${rgba(accent, 0.35 + hoIn * 0.2)}`,
          background: "transparent",
          opacity: hoIn,
          transform: `scale(${0.86 + hoIn * 0.14})`,
          filter: hoIn < 1 ? `blur(${(1 - hoIn) * 18}px)` : undefined,
        }} />
      ) : null}
    </AbsoluteFill>
  );
};

/* ---- canonical demo ------------------------------------------------------ */
export const tapStackDemo: TapStackProps = {
  cards: [
    { id: "u02", merchant: "Zomato",   amount: 1072, day: "18 AUG", cat: "food" },
    { id: "u03", merchant: "Zomato",   amount: 897,  day: "18 AUG", cat: "food" },
    { id: "u04", merchant: "Amazon",   amount: 1414, day: "18 AUG", cat: "shopping" },
    { id: "u05", merchant: "",         amount: 100,  day: "18 AUG", masked: true },
    { id: "u06", merchant: "Blinkit",  amount: 710,  day: "17 AUG", cat: "grocery" },
    { id: "u07", merchant: "Blinkit",  amount: 649,  day: "17 AUG", cat: "grocery" },
    { id: "u08", merchant: "Snabbit",  amount: 399,  day: "17 AUG", cat: "other" },
    { id: "u09", merchant: "DMart",    amount: 5931, day: "17 AUG", cat: "grocery", hot: true },
    { id: "u10", merchant: "Blinkit",  amount: 1843, day: "16 AUG", cat: "grocery" },
    { id: "u11", merchant: "",         amount: 2800, day: "16 AUG", masked: true },
    { id: "u12", merchant: "Maestro",  amount: 199,  day: "15 AUG", cat: "other" },
    { id: "u13", merchant: "Gas Bill", amount: 1500, day: "14 AUG", cat: "bills" },
  ],
  // front-loaded then plateaued at 4 frames — the densest rate that still
  // resolves at 2x playback, which Shorts now offers
  gaps: [0, 0.3, 0.5, 0.667, 0.8, 0.933, 1.067, 1.2, 1.333, 1.467, 1.6, 1.733],
  provenance: "FROM MY OWN SCREENSHOTS",
  unitLabel: "ONE TAP",
  claimLines: ["I SCREENSHOTTED", "MY UPI HISTORY"],
  claimHot: "UPI",
  claimAt: 0.467,
  claimOut: 1.8,
  debt: "I NEVER ADDED THEM UP",
  debtHot: "NEVER",
  debtAt: 1.933,
  handoffAt: 2.2,
};
