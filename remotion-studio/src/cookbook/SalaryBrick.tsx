import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { rgba } from "./kit";
import { clamp01, OUT_E, IN_E, settle } from "./motion";
import { FilmT } from "./filmclock";
import { ExposureScore, FlashCut } from "./craft";
import { EngagePing, Ping } from "./EngagePing";

/* =============================================================================
   SALARY BRICK — ep3 "I Asked AI Where My 34 LPA Actually Goes".

   Spine (VJ-picked, judge score 45/50):
   0.0  POV offer-letter moment: embossed CTC ₹12,00,000, confetti mid-fall,
        family chat sliding up — and a bank SMS sliding in whose amount is
        BLURRED and visibly TOO SHORT for 12 lakh. Both can't be true.
   3.0  the letter folds down; the CTC becomes a PHYSICAL brick of note
        bundles on a papercraft desk. Cleavers racked above.
   4.6  VARIABLE PAY — the biggest cleaver falls hardest (knee, loudest
        event): a ₹1,80,000 chunk carted off on a thela.
   6.0  the embossed ₹12,00,000 CRACKS digit-by-digit into six deduction
        labels (the absolute digit-break).
   ~11  the cascade: employer PF / gratuity / insurance — quicker, harder.
   ~16  THE TWIST: the red TAX cleaver winds up huge… and BOUNCES off a
        shield stamp — ₹12L tak naya regime, tax ZERO (verified FY25-26).
        RED is spent here and only here.
   ~21  employee PF + professional tax — small clean chops. A wafer remains.
   ~25  (75%) the wafer drops into the SMS bubble; the blur SNAPS off:
        ₹72,026 CREDITED at ~40% width.
   ~27  circle: the cart's chunks line up = ₹3,35,688 — the gap TO THE RUPEE.
   ~28.5 the give: CTC-decoder prompt complete + static, PINNED ✓, loop-out
        to the offer letter + SMS — frame 0 composition.

   The brick is the carry object. This component IS the spine: it computes
   film time from `start` and provides FilmT.
   ========================================================================== */

const W3 = {
  ground: "#F1EADB", ground2: "#F8F3E7", ink: "#2C261C",
  money: "#8FAF7E", moneyDeep: "#6E9160", band: "#EFE6CF",
  steel: "#7A828C", red: "#D9482B", green: "#4ADE80", amber: "#C77F14",
};
const MONO = "'JetBrains Mono', 'Courier New', monospace";
const DISP = "'Archivo Black', 'Arial Black', sans-serif";
const cardShadow = `0 6px 10px ${rgba("#000", 0.5)}, 0 36px 80px ${rgba("#000", 0.3)}`;
const P = (f: string) => staticFile(`assets/lpa/${f}`);

export type Chip = { t: number; end?: number; text: string; hot?: boolean; big?: boolean };

export type SalaryBrickProps = {
  start?: number; width?: number; height?: number;
  brickAt?: number; varpayAt?: number; crackAt?: number;
  cascadeAts?: number[];              // employer PF, gratuity, insurance, employee PF, prof tax
  taxAt?: number; bounceAt?: number;  // the red cleaver's windup + the ₹4L bounce
  ladderAts?: number[];               // six slab chops, accelerating
  taxStampAt?: number;                // the total lands on the cart
  creditAt?: number; gapAt?: number;
  giveAt?: number; endAt?: number;
  chips?: Chip[];
  pings?: Ping[];
};

/* the cut list drives brick height + cart contents; amounts in ₹/yr */
type Cut = { key: string; label: string; amt: string; frac: number };
const CUTS: Cut[] = [
  { key: "varpay", label: "VARIABLE PAY", amt: "−₹5,10,000", frac: 0.15 },
  { key: "epf", label: "EMPLOYER PF", amt: "−₹1,63,200", frac: 0.048 },
  { key: "grat", label: "GRATUITY", amt: "−₹65,416", frac: 0.0192 },
  { key: "ins", label: "INSURANCE", amt: "−₹25,000", frac: 0.0074 },
  { key: "mypf", label: "EMPLOYEE PF", amt: "−₹1,63,200", frac: 0.048 },
  { key: "ptax", label: "PROF TAX", amt: "−₹2,400", frac: 0.0007 },
  { key: "tax", label: "INCOME TAX", amt: "−₹3,62,352", frac: 0 },
];
/* the tax is chopped SLAB BY SLAB (VJ: step by step, realistic at 34 LPA);
   ladder slice amounts in ₹, cess folded into the last swing */
const TAX_STEPS = [
  { pct: "5%", amt: 20000 }, { pct: "10%", amt: 40000 }, { pct: "15%", amt: 60000 },
  { pct: "20%", amt: 80000 }, { pct: "25%", amt: 100000 }, { pct: "30%+cess", amt: 62352 },
];

/* one falling cleaver: windup above, accelerating fall, hit shake + dust.
   `red` marks the tax cleaver — the only red object in the film. */
const Cleaver: React.FC<{
  t: number; at: number; x: number; topY: number; scale?: number;
  label: string; red?: boolean; bounce?: boolean; bounceAt?: number;
}> = ({ t, at, x, topY, scale = 1, label, red = false, bounce = false, bounceAt = 0 }) => {
  if (t < at) return null;
  const wind = OUT_E(clamp01((t - at) / 0.4));
  const fallP = IN_E(clamp01((t - at - 0.4) / 0.25));
  const boP = bounce ? OUT_E(clamp01((t - bounceAt) / 0.5)) : 0;
  const gone = !bounce && t > at + 1.6;
  if (gone) return null;
  const y = topY - 420 + wind * 60 + fallP * 360 - boP * 300;
  const rot = -8 + wind * 8 - boP * 24;
  const fade = bounce ? 1 - clamp01((t - bounceAt - 0.8) / 0.5) : 1 - clamp01((t - at - 1.1) / 0.5);
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: `rotate(${rot}deg) scale(${scale})`,
      transformOrigin: "left bottom", opacity: Math.max(0, fade), zIndex: 24 }}>
      <svg width={330} height={110} viewBox="0 0 330 110">
        {/* a long cake knife: slim blade, wooden handle */}
        <rect x={252} y={34} width={74} height={26} rx={12} fill="#5A4632" />
        <path d="M 8 44 L 256 40 L 256 62 Q 120 76 16 60 Z"
          fill={red ? W3.red : W3.steel} stroke={rgba("#000", 0.25)} strokeWidth={2} />
        <path d="M 8 44 L 256 40 L 256 47 L 10 50 Z" fill={rgba("#FFF", 0.35)} />
      </svg>
      <div style={{ position: "absolute", left: 26, top: 8, fontFamily: MONO, fontSize: 22,
        letterSpacing: 1, color: "#FFF6EC", fontWeight: 700, background: rgba("#211A12", 0.85),
        borderRadius: 7, padding: "2px 10px",
        textShadow: `0 1px 3px ${rgba("#000", 0.5)}` }}>{label}</div>
    </div>
  );
};

export const SalaryBrick: React.FC<SalaryBrickProps> = ({
  start = 0, width = 1080, height = 1920,
  brickAt = 3.4, varpayAt = 4.6, crackAt = 6.0,
  cascadeAts = [10.9, 11.7, 12.4, 13.0, 13.6], taxAt = 15.0, bounceAt = 15.4,
  ladderAts = [16.0, 16.8, 17.5, 18.3, 18.9, 19.5], taxStampAt = 20.2,
  creditAt = 26.0, gapAt = 27.6, giveAt = 28.8, endAt = 33.1,
  chips = [], pings = [],
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - start;

  /* ---------------------------------------------------------- shake ------- */
  const cutTimes = [varpayAt + 0.65, ...cascadeAts.map((a) => a + 0.65),
    ...ladderAts.map((a) => a + 0.3)];
  let shake = 0;
  for (const [i, ct] of cutTimes.entries()) {
    const d = t - ct;
    if (d > 0 && d < 0.45) shake = Math.max(shake, Math.sin(d * 40) * (1 - d / 0.45) * (i === 0 ? 14 : 6));
  }
  const bShake = t > bounceAt && t < bounceAt + 0.5 ? Math.sin((t - bounceAt) * 34) * (1 - (t - bounceAt) / 0.5) * 10 : 0;
  shake += bShake;

  /* -------------------------------------------------- brick geometry ------ */
  /* how much of the brick has been chopped by time t */
  const cutAts = [varpayAt + 0.65, ...cascadeAts.map((a) => a + 0.65), taxStampAt];
  let choppedFrac = 0;
  CUTS.forEach((c, i) => { if (i < 6 && t >= cutAts[i]) choppedFrac += c.frac; });
  TAX_STEPS.forEach((st, i) => { if (t >= ladderAts[i] + 0.3) choppedFrac += st.amt / 3400000; });
  const BRICK_X = 190, BRICK_BOT = 1180, BRICK_W = 700, BRICK_H0 = 560;
  const brickH = BRICK_H0 * (1 - choppedFrac * (1 / 0.38) * 0.62);
  /* cuts sum to ~.38 of CTC; the wafer keeps ~38% visual height — the
     in-hand is still a real object, and the gap is a fresher's package */
  const cakeLift = OUT_E(clamp01((t - (gapAt + 0.1)) / 0.7));
  const brickOn = OUT_E(clamp01((t - brickAt) / 0.6)) * (1 - cakeLift);

  /* THE SALARY CAKE v2 (VJ's board note): an ISOLATED sprite composited
     straight onto the canvas — no photo card, no baked table. It sits on
     the desk with its own contact shadow, and its CUT STATE persists:
     full -> one wedge gone -> quarter gone -> half, per the knife hits. */
  const staticLanded = cutAts.slice(0, 6).filter((a) => t >= a).length;
  const ladderLanded = ladderAts.filter((a) => t >= a).length;
  const cakeState = staticLanded >= 3 || ladderLanded >= 1 ? "seq_cut3" : staticLanded >= 1 ? "seq_cut1" : "seq_full";
  const cakeScale = 1 - (staticLanded * 0.02 + ladderLanded * 0.015);
  const lastHit = Math.max(-10, ...[...cutAts.slice(0, 6), ...ladderAts].filter((a) => t >= a));
  const hitP = clamp01((t - lastHit) / 0.4);
  const CAKE_W = 620, CAKE_BOT = 1560;
  const brick = brickOn > 0.01 ? (
    <div style={{ position: "absolute", left: 540 - CAKE_W / 2, top: CAKE_BOT - CAKE_W, width: CAKE_W,
      height: CAKE_W, opacity: brickOn, zIndex: 12,
      transformOrigin: "bottom center",
      transform: `translateY(${(1 - OUT_E(clamp01((t - brickAt) / 0.6))) * 80 - cakeLift * 620}px) scale(${cakeScale * (1 + (1 - OUT_E(hitP)) * 0.06) * (1 - cakeLift * 0.45)})` }}>
      {/* contact shadow grounds it on the desk */}
      <div style={{ position: "absolute", left: "8%", bottom: -18, width: "84%", height: 56,
        borderRadius: "50%", background: `radial-gradient(ellipse, ${rgba("#3A2C18", 0.38)} 0%, transparent 70%)` }} />
      <Img src={P(`sprites/${cakeState}.png`)} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
    </div>
  ) : null;
  const brickTag = brickOn > 0.01 ? (
    <div style={{ position: "absolute", left: 540 + CAKE_W / 2 - 70, top: CAKE_BOT - CAKE_W * cakeScale - 10,
      opacity: brickOn, zIndex: 13, fontFamily: MONO, fontSize: 19,
      border: `1.5px solid ${rgba(W3.ink, 0.5)}`, borderRadius: 6, padding: "2px 10px",
      color: rgba(W3.ink, 0.65), background: rgba("#FFF", 0.6) }}>DEMO</div>
  ) : null;

  /* ------------------------------------------- flying chunks + the cart --- */  /* ------------------------------------------- flying chunks + the cart --- */  /* ------------------------------------------- flying chunks + the cart --- */
  /* THE EXPENSE PIE (VJ's board note): every cut wedge flies UP and lands
     as a segment of a donut chart building in the upper zone — the stats,
     shaped like what they were cut from. Tax builds in six slab steps and
     is the only red. IN-HAND closes the ring green at the gap beat. */
  const PIE_CX = 540, PIE_CY = 500, R_OUT = 280, R_IN = 148;
  const FR = 1 / 3400000;
  type Seg = { key: string; label: string; amt: number; color: string; landAt: number };
  const SEGS: Seg[] = [
    { key: "varpay", label: "HOLD", amt: 510000, color: "#5F7A52", landAt: cutAts[0] + 0.9 },
    { key: "epf", label: "EMPLR PF", amt: 163200, color: "#7A9A6C", landAt: cutAts[1] + 0.9 },
    { key: "grat", label: "GRATUITY", amt: 65416, color: "#93AC82", landAt: cutAts[2] + 0.9 },
    { key: "ins", label: "INSUR", amt: 25000, color: "#A9BC98", landAt: cutAts[3] + 0.9 },
    { key: "mypf", label: "MY PF", amt: 163200, color: "#86A375", landAt: cutAts[4] + 0.9 },
    { key: "ptax", label: "PT", amt: 2400, color: "#B8C7A8", landAt: cutAts[5] + 0.9 },
    ...TAX_STEPS.map((st, j) => ({ key: `tax${j}`, label: j === 5 ? "TAX+CESS" : `TAX ${st.pct}`,
      amt: st.amt, color: W3.red, landAt: ladderAts[j] + 0.35 })),
    { key: "inhand", label: "IN-HAND", amt: 2108432, color: W3.green, landAt: gapAt + 0.3 },
  ];
  const arc = (a0: number, a1: number, ro: number, ri: number) => {
    const P = (r: number, a: number) => [PIE_CX + r * Math.cos(a), PIE_CY + r * Math.sin(a)];
    const [x0, y0] = P(ro, a0), [x1, y1] = P(ro, a1), [x2, y2] = P(ri, a1), [x3, y3] = P(ri, a0);
    const lg = a1 - a0 > Math.PI ? 1 : 0;
    return `M ${x0} ${y0} A ${ro} ${ro} 0 ${lg} 1 ${x1} ${y1} L ${x2} ${y2} A ${ri} ${ri} 0 ${lg} 0 ${x3} ${y3} Z`;
  };
  const pieOn = OUT_E(clamp01((t - cutAts[0] - 0.5) / 0.5)) * (1 - clamp01((t - giveAt + 0.2) / 0.4));
  const pieDock = OUT_E(clamp01((t - (creditAt - 0.4)) / 0.5)) * (1 - OUT_E(clamp01((t - gapAt) / 0.5)));
  let gonePct = 0;
  SEGS.forEach((sg) => { if (sg.key !== "inhand" && t >= sg.landAt) gonePct += sg.amt * FR; });
  const cart = pieOn > 0.01 ? (
    <div style={{ position: "absolute", inset: 0, zIndex: 20, opacity: pieOn,
      transformOrigin: `${PIE_CX}px ${PIE_CY}px`,
      transform: `scale(${1 - pieDock * 0.5}) translate(${pieDock * -560}px, ${pieDock * -240}px)` }}>
      <svg width={1080} height={1920} style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
        <defs>
          {(() => {
            let a0 = -Math.PI / 2;
            return SEGS.map((sg) => {
              const span = sg.amt * FR * Math.PI * 2;
              const grow = sg.key === "inhand" ? OUT_E(clamp01((t - sg.landAt) / 0.8)) : OUT_E(clamp01((t - sg.landAt) / 0.35));
              const a1 = a0 + span * grow;
              const Px = (r: number, ang: number) => `${PIE_CX + r * Math.cos(ang)} ${PIE_CY + r * Math.sin(ang)}`;
              const lg = a1 - a0 > Math.PI ? 1 : 0;
              const el = (
                <clipPath key={sg.key} id={`sec-${sg.key}`}>
                  <path d={`M ${PIE_CX} ${PIE_CY} L ${Px(R_OUT, a0)} A ${R_OUT} ${R_OUT} 0 ${lg} 1 ${Px(R_OUT, a1)} Z`} />
                </clipPath>
              );
              a0 += span;
              return el;
            });
          })()}
        </defs>
        {/* faint waiting ring */}
        <circle cx={PIE_CX} cy={PIE_CY} r={R_OUT} fill={rgba("#211A12", 0.06)} />
        {(() => {
          let a0 = -Math.PI / 2;
          return SEGS.map((sg) => {
            const span = sg.amt * FR * Math.PI * 2;
            const grow = sg.key === "inhand" ? OUT_E(clamp01((t - sg.landAt) / 0.8)) : OUT_E(clamp01((t - sg.landAt) / 0.35));
            const myA0 = a0; a0 += span;
            if (grow < 0.001) return null;
            const a1 = myA0 + span * grow;
            const Px = (r: number, ang: number) => `${PIE_CX + r * Math.cos(ang)} ${PIE_CY + r * Math.sin(ang)}`;
            const lg = a1 - myA0 > Math.PI ? 1 : 0;
            const edge = `M ${PIE_CX} ${PIE_CY} L ${Px(R_OUT, myA0)} A ${R_OUT} ${R_OUT} 0 ${lg} 1 ${Px(R_OUT, a1)} Z`;
            const isTaxSeg = sg.key.startsWith("tax");
            return (
              <g key={sg.key}>
                {/* the slice: a piece of the SAME top-view cake render */}
                <image href={P("cake_topview_b.png")}
                  x={PIE_CX - (502 / 324) * R_OUT} y={PIE_CY - (522 / 324) * R_OUT}
                  width={(1024 / 324) * R_OUT} height={(1024 / 324) * R_OUT}
                  clipPath={`url(#sec-${sg.key})`} preserveAspectRatio="none" />
                {/* tint: tax red, in-hand green, others natural */}
                {isTaxSeg ? <path d={edge} fill={rgba("#C43A20", 0.48)} /> : null}
                {sg.key === "inhand" ? <path d={edge} fill={rgba("#2E7D4F", 0.26)} /> : null}
                {/* cut lines between slices */}
                <path d={edge} fill="none" stroke={rgba("#FFF", 0.9)} strokeWidth={3} />
                {t - sg.landAt < 0.18 ? <path d={edge} fill={rgba("#FFF", 0.5 * (1 - (t - sg.landAt) / 0.18))} /> : null}
                {/* leader label for readable spans */}
                {sg.amt * FR > 0.017 && grow > 0.9 ? (() => {
                  const mid = myA0 + span / 2;
                  const lx = PIE_CX + Math.cos(mid) * (R_OUT + 34), ly = PIE_CY + Math.sin(mid) * (R_OUT + 34);
                  const anchor = Math.cos(mid) >= 0 ? "start" : "end";
                  return (
                    <g>
                      <line x1={PIE_CX + Math.cos(mid) * (R_OUT + 4)} y1={PIE_CY + Math.sin(mid) * (R_OUT + 4)}
                        x2={lx} y2={ly} stroke={rgba(W3.ink, 0.5)} strokeWidth={2} />
                      <text x={lx + (anchor === "start" ? 6 : -6)} y={ly + 7} textAnchor={anchor}
                        fontFamily="'JetBrains Mono', monospace" fontSize={23} fontWeight={700}
                        fill={isTaxSeg ? "#A93A22" : W3.ink}>
                        {sg.label} ₹{sg.amt.toLocaleString("en-IN")}
                      </text>
                    </g>
                  );
                })() : null}
              </g>
            );
          });
        })()}
        {/* donut hole: a small cream disc keeps the centre stat readable */}
        <circle cx={PIE_CX} cy={PIE_CY} r={122} fill="#F5EEDF" opacity={0.97} />
        <circle cx={PIE_CX} cy={PIE_CY} r={122} fill="none" stroke={rgba("#211A12", 0.15)} strokeWidth={2} />
      </svg>
      {/* the centre stat */}      {/* the centre stat */}
      <div style={{ position: "absolute", left: PIE_CX - 130, top: PIE_CY - 56, width: 260,
        textAlign: "center", fontVariantNumeric: "tabular-nums" as const }}>
        {t < gapAt + 0.3 ? (
          <>
            <div style={{ fontFamily: MONO, fontSize: 22, color: rgba(W3.ink, 0.6), letterSpacing: 2 }}>CTC GONE</div>
            <div style={{ fontFamily: DISP, fontSize: 62, color: W3.ink }}>{Math.round(gonePct * 100)}%</div>
          </>
        ) : (
          <>
            <div style={{ fontFamily: MONO, fontSize: 21, color: rgba(W3.ink, 0.6), letterSpacing: 2 }}>GAP / YEAR</div>
            <div style={{ fontFamily: DISP, fontSize: 44, color: "#A93A22" }}>₹12,91,568</div>
            <div style={{ fontFamily: MONO, fontSize: 19, color: "#3E5A33", marginTop: 2 }}>a fresher's salary</div>
          </>
        )}
      </div>
      {/* wedge flights: cake -> segment centroid, spin + crush */}
      {SEGS.filter((sg) => sg.key !== "inhand").map((sg) => {
        const dep = sg.landAt - 0.55;
        const fp = clamp01((t - dep) / 0.55);
        if (fp <= 0 || fp >= 1) return null;
        let a0 = -Math.PI / 2;
        for (const q of SEGS) { if (q.key === sg.key) break; a0 += q.amt * FR * Math.PI * 2; }
        const mid = a0 + sg.amt * FR * Math.PI;
        const tx = PIE_CX + Math.cos(mid) * (R_OUT - 70), ty = PIE_CY + Math.sin(mid) * (R_OUT - 70);
        const e = OUT_E(fp);
        const x = 540 + (tx - 540) * e, y = 1080 + (ty - 1080) * e - Math.sin(e * Math.PI) * 190;
        const crush = fp > 0.85 ? (fp - 0.85) / 0.15 : 0;
        return (
          <div key={sg.key} style={{ position: "absolute", left: x - 70, top: y - 45, width: 140,
            transform: `rotate(${e * 300}deg) scale(${(1 - e * 0.35) * (1 + crush * 0.4)}, ${(1 - e * 0.35) * (1 - crush * 0.6)})` }}>
            <Img src={P("sprites/seq_wedge.png")} style={{ width: "100%",
              filter: sg.key.startsWith("tax") ? "sepia(0.5) hue-rotate(-30deg) saturate(2.4)" : undefined }} />
          </div>
        );
      })}
    </div>
  ) : null;

  /* --------------------------------------------------- the offer letter --- */
  const offerFold = IN_E(clamp01((t - brickAt + 0.4) / 0.6));
  const loopIn = clamp01((t - (endAt - 0.9)) / 0.6);
  const offerOn = Math.max(1 - offerFold, loopIn);
  /* the embossed CTC cracks at 6.00s into the six labels */
  const crackP = OUT_E(clamp01((t - crackAt) / 0.6));
  const offer = offerOn > 0.01 ? (
    <div style={{ position: "absolute", left: 90, top: 330, width: 900, zIndex: 18,
      opacity: offerOn, transform: `perspective(1200px) rotateX(${offerFold * 55}deg) translateY(${offerFold * 120}px)`,
      transformOrigin: "bottom center" }}>
      <div style={{ background: "linear-gradient(180deg, #FBF6EA, #EFE7D2)", borderRadius: 22,
        padding: "44px 50px 38px", boxShadow: cardShadow, border: `1px solid ${rgba("#B9AC8E", 0.6)}` }}>
        <div style={{ fontFamily: MONO, fontSize: 24, letterSpacing: 5, color: "#6B5636", fontWeight: 700 }}>OFFER LETTER</div>
        <div style={{ marginTop: 14, fontFamily: MONO, fontSize: 27, color: W3.ink, fontWeight: 700 }}>CTC · COST TO COMPANY</div>
        <div style={{ marginTop: 8, fontFamily: DISP, fontSize: 96, color: W3.ink, letterSpacing: 2,
          textShadow: `0 1px 0 ${rgba("#FFF", 0.9)}, 0 -1px 0 ${rgba("#000", 0.25)}`,
          fontVariantNumeric: "tabular-nums" as const,
          opacity: 1 - crackP, transform: `scale(${1 - crackP * 0.06})` }}>₹34,00,000</div>
        {/* the crack: six deduction labels burst out of the numerals */}
        {crackP > 0.01 ? (
          <div style={{ position: "absolute", left: 40, top: 150, width: 820, display: "flex",
            flexWrap: "wrap" as const, gap: 12, justifyContent: "center" }}>
            {CUTS.map((c, i) => (
              <div key={c.key} style={{
                fontFamily: MONO, fontSize: 25, color: "#FFF6EC", letterSpacing: 1,
                background: i === 999 ? W3.red : rgba("#3B342A", 0.95), borderRadius: 9,
                padding: "6px 14px", boxShadow: cardShadow,
                opacity: Math.min(1, crackP * 1.6),
                transform: `translateY(${(1 - OUT_E(clamp01((t - crackAt - i * 0.06) / 0.4))) * 60}px) rotate(${(i % 2 ? 1 : -1) * (1 - crackP) * 8}deg)`,
              }}>{c.label}</div>
            ))}
          </div>
        ) : null}
        <div style={{ marginTop: 12, height: 10, borderRadius: 5, background: rgba(W3.ink, 0.12), width: "70%" }} />
        <div style={{ marginTop: 8, height: 10, borderRadius: 5, background: rgba(W3.ink, 0.12), width: "55%" }} />
      </div>
    </div>
  ) : null;

  /* -------------------------------------------------- family chat + SMS --- */
  const chatOn = t < brickAt ? OUT_E(clamp01((t - 0.5) / 0.5)) : Math.max(0, 1 - clamp01((t - brickAt) / 0.4));
  const chat = chatOn > 0.01 ? (
    <div style={{ position: "absolute", left: 70, top: 1210, width: 620, zIndex: 20, opacity: chatOn,
      transform: `translateY(${(1 - OUT_E(clamp01((t - 0.5) / 0.5))) * 70}px)` }}>
      <div style={{ background: "#DCF3CC", borderRadius: "18px 18px 18px 4px", padding: "14px 20px",
        boxShadow: cardShadow, border: `1px solid ${rgba("#7BA05B", 0.4)}` }}>
        <div style={{ fontFamily: MONO, fontSize: 20, color: "#4A6B35", fontWeight: 700 }}>Family ❤ · Papa</div>
        <div style={{ fontFamily: MONO, fontSize: 27, color: "#2C3E1F", marginTop: 4 }}>
          34 lakh package! So proud! 🎉🎉
        </div>
      </div>
    </div>
  ) : null;

  /* the SMS: slides in at 1.0s, amount blurred and TOO SHORT; unblurs at credit */
  const smsIn = OUT_E(clamp01((t - 1.0) / 0.6));
  const credited = t >= creditAt;
  const creditPop = OUT_E(clamp01((t - creditAt) / 0.4));
  const smsDock = IN_E(clamp01((t - brickAt) / 0.6)) * (1 - OUT_E(clamp01((t - creditAt + 0.5) / 0.5)));
  /* full-size at the hook, docks small top-right during the chopping, returns big for the credit */
  const smsScale = 1 - smsDock * 0.45 + (credited ? settle(t, creditAt, 0.5) * 0.06 : 0);
  const smsX = 330 + smsDock * 340, smsY = 1490 - smsDock * 1330 - (credited ? 640 : 0);
  const sms = t >= 1.0 ? (
    <div style={{ position: "absolute", left: credited ? 150 : smsX, top: credited ? 830 : smsY,
      width: credited ? 780 : 640, zIndex: 30, opacity: smsIn * (1 - clamp01((t - giveAt + 0.2) / 0.4)),
      transformOrigin: "top left",
      transform: `translateX(${(1 - smsIn) * 300}px) scale(${credited ? 1.05 : smsScale})` }}>
      <div style={{ background: "#FFFFFF", borderRadius: 18, padding: "18px 24px",
        boxShadow: cardShadow, border: `1px solid ${rgba("#8A8A8A", 0.35)}` }}>
        <div style={{ fontFamily: MONO, fontSize: 20, color: "#6B6B6B", display: "flex",
          justifyContent: "space-between" }}>
          <span>BK-HDFCBK</span><span>{credited ? "now" : "1 Aug"}</span>
        </div>
        <div style={{ marginTop: 6, fontFamily: MONO, fontSize: credited ? 30 : 24, color: "#2B2B2B", lineHeight: 1.5 }}>
          Salary credited:{" "}
          <span style={{
            fontFamily: DISP, fontSize: credited ? 128 : 34, color: credited ? W3.moneyDeep : "#2B2B2B",
            filter: credited ? undefined : "blur(9px)",
            display: credited ? "block" : "inline",
            textShadow: credited ? `0 0 30px ${rgba(W3.money, 0.8)}` : undefined,
            fontVariantNumeric: "tabular-nums" as const,
            transform: credited ? `scale(${1 + creditPop * 0.05})` : undefined,
          }}>₹1,75,702</span>
          {credited ? <span style={{ fontFamily: MONO, fontSize: 24, color: "#6B6B6B" }}>a/c XX4021 · 1st of month</span> : null}
        </div>
      </div>
      {!credited && t < brickAt ? (
        <div style={{ marginTop: 10, textAlign: "center", fontFamily: MONO, fontSize: 24,
          color: W3.ink, opacity: clamp01((t - 1.8) / 0.4) }}>
          why so small? 🤔
        </div>
      ) : null}
    </div>
  ) : null;

  /* credit beat dressing: 34L ÷ 12 = the EXPECTED month, struck through as
     the real credit lands; the monthly hole named; the surviving wafer drops
     INTO the SMS so the payoff frame is never still */
  const expectOn = OUT_E(clamp01((t - creditAt + 0.5) / 0.4));
  const strike = clamp01((t - creditAt - 0.5) / 0.4);
  const holeOn = OUT_E(clamp01((t - creditAt - 1.0) / 0.4));
  const creditMath = t >= creditAt - 0.5 && t < giveAt ? (
    <div style={{ position: "absolute", left: 0, right: 0, top: 560, textAlign: "center", zIndex: 29,
      opacity: expectOn * (1 - clamp01((t - gapAt) / 0.4)) }}>
      <div style={{ display: "inline-block", fontFamily: MONO, fontSize: 34, color: W3.ink,
        background: rgba("#FFF", 0.85), borderRadius: 14, padding: "10px 24px", boxShadow: cardShadow,
        fontVariantNumeric: "tabular-nums" as const, position: "relative" }}>
        34 LAKH ÷ 12 = ₹2,83,333
        <div style={{ position: "absolute", left: "4%", top: "52%", height: 4, borderRadius: 2,
          width: `${strike * 92}%`, background: W3.red }} />
      </div>
      {holeOn > 0.01 ? (
        <div style={{ marginTop: 14, display: "inline-block", fontFamily: DISP, fontSize: 44,
          color: "#FFF6EC", background: rgba("#7A2515", 0.95), borderRadius: 14,
          padding: "6px 26px", boxShadow: cardShadow, opacity: holeOn,
          transform: `scale(${0.9 + holeOn * 0.1})`, fontVariantNumeric: "tabular-nums" as const }}>
          −₹1,07,631 / MONTH
        </div>
      ) : null}
    </div>
  ) : null;
  /* the wafer: the last piece of the brick arcs into the SMS */
  const waferP = clamp01((t - creditAt + 0.15) / 0.5);
  const wafer = t >= creditAt - 0.15 && waferP < 1 ? (() => {
    const e = OUT_E(waferP);
    const x0 = BRICK_X + 180, y0 = BRICK_BOT - 80, x1 = 480, y1 = 900;
    return (
      <div style={{ position: "absolute", left: x0 + (x1 - x0) * e,
        top: y0 + (y1 - y0) * e - Math.sin(e * Math.PI) * 160,
        width: 220, height: 60, borderRadius: 8, overflow: "hidden", zIndex: 31,
        transform: `rotate(${e * -14}deg)`, boxShadow: cardShadow }}>
        <Img src={P("cake_slice_plate.png")} style={{ position: "absolute", left: -10, top: -40,
          width: 240, height: 150, objectFit: "cover" }} />
      </div>
    );
  })() : null;

  /* ---- brand inside 1s (law 3) ---- */
  const brandOn = OUT_E(clamp01((t - 0.45) / 0.4));
  const brand = (
    <div style={{ position: "absolute", right: 60, top: 240, zIndex: 34, opacity: brandOn,
      display: "flex", gap: 12, alignItems: "center",
      background: rgba("#211A12", 0.9), borderRadius: 14, padding: "10px 20px", boxShadow: cardShadow }}>
      <span style={{ fontSize: 28 }}>✳</span>
      <span style={{ fontFamily: MONO, fontSize: 24, color: "#F6EEDF", letterSpacing: 2 }}>FREE AI</span>
    </div>
  );

  /* ----------------------------------------------------- confetti (hook) -- */
  const confetti = t < 3.2 ? (
    <svg width={1080} height={1920} style={{ position: "absolute", inset: 0, zIndex: 8, pointerEvents: "none" }}>
      {Array.from({ length: 26 }).map((_, i) => {
        const seed = (i * 137) % 1080;
        const fall = ((t * (90 + (i % 5) * 30)) + i * 67) % 900;
        const op = t < 2.4 ? 0.85 : Math.max(0, 0.85 - (t - 2.4) * 1.1);
        return <rect key={i} x={seed} y={120 + fall} width={12} height={7}
          transform={`rotate(${(t * 140 + i * 40) % 360} ${seed} ${120 + fall})`}
          fill={[W3.money, W3.amber, "#D98A6A", W3.band][i % 4]} opacity={op} />;
      })}
    </svg>
  ) : null;

  /* -------------------------------------------------- the tax bounce ------ */
  const shieldOn = OUT_E(clamp01((t - bounceAt) / 0.35));
  const shield = t >= bounceAt && t < ladderAts[1] ? (
    <div style={{ position: "absolute", left: 200, top: 620, width: 680, zIndex: 26,
      textAlign: "center", opacity: shieldOn * (1 - clamp01((t - ladderAts[0] - 0.5) / 0.4)),
      transform: `scale(${0.85 + shieldOn * 0.15 + settle(t, bounceAt, 0.5) * 0.08})` }}>
      <div style={{ display: "inline-block", background: rgba("#211A12", 0.93), borderRadius: 18,
        padding: "14px 30px", boxShadow: cardShadow, border: `3px solid ${W3.green}` }}>
        <div style={{ fontFamily: DISP, fontSize: 52, color: W3.green }}>FIRST ₹4L — TAX ₹0</div>
        <div style={{ fontFamily: MONO, fontSize: 22, color: "#F6EEDF", marginTop: 4 }}>
          new regime FY25-26 · slab 1
        </div>
      </div>
    </div>
  ) : null;

  /* dead-space fill on the ladder beat: the taxable base on the left, and a
     red sliver flying brick->card on every swing */
  const taxableOn = OUT_E(clamp01((t - taxAt) / 0.4));
  const taxablePanel = t >= taxAt && t < creditAt ? (
    <div style={{ position: "absolute", left: 46, top: 560, zIndex: 26,
      opacity: taxableOn * (1 - clamp01((t - creditAt + 0.4) / 0.4)),
      background: rgba("#211A12", 0.9), borderRadius: 14, padding: "12px 18px", boxShadow: cardShadow }}>
      <div style={{ fontFamily: MONO, fontSize: 19, letterSpacing: 2, color: rgba("#F6EEDF", 0.6) }}>TAXABLE BASE</div>
      <div style={{ fontFamily: DISP, fontSize: 34, color: "#F6EEDF", fontVariantNumeric: "tabular-nums" as const }}>₹25,61,384</div>
      <div style={{ fontFamily: MONO, fontSize: 16, color: rgba("#F6EEDF", 0.55), marginTop: 2 }}>gross − ₹75,000 std ded</div>
    </div>
  ) : null;
  const slivers = ladderAts.map((a, i) => {
    const pr = clamp01((t - a - 0.15) / 0.35);
    if (pr <= 0 || pr >= 1) return null;
    const x0 = BRICK_X + 300, y0 = BRICK_BOT - brickH + 20;
    const x1 = 700, y1 = 620 + 40 * i;
    const e = OUT_E(pr);
    return (
      <div key={i} style={{ position: "absolute", left: x0 + (x1 - x0) * e,
        top: y0 + (y1 - y0) * e - Math.sin(e * Math.PI) * 90,
        width: 54, height: 20, borderRadius: 5, zIndex: 27,
        background: `linear-gradient(180deg, ${W3.red}, #A93A22)`,
        transform: `rotate(${e * 220}deg)`, boxShadow: `0 3px 8px ${rgba("#000", 0.4)}` }} />
    );
  });

  /* the ladder counter: slab rows land as the cleaver chops — step by step */
  const ladderOn = OUT_E(clamp01((t - ladderAts[0]) / 0.4));
  const ladder = t >= ladderAts[0] && t < creditAt ? (
    <div style={{ position: "absolute", right: 46, top: 560, width: 400, zIndex: 26,
      opacity: ladderOn * (1 - clamp01((t - creditAt + 0.4) / 0.4)),
      background: rgba("#211A12", 0.93), borderRadius: 18, padding: "16px 22px",
      boxShadow: cardShadow, border: `2px solid ${rgba(W3.red, 0.6)}` }}>
      <div style={{ fontFamily: MONO, fontSize: 21, letterSpacing: 2, color: "#FFB0A0" }}>TAX · SLAB BY SLAB</div>
      {TAX_STEPS.map((st, i) => {
        const on = OUT_E(clamp01((t - ladderAts[i] - 0.25) / 0.3));
        if (on < 0.01) return null;
        return (
          <div key={i} style={{ display: "flex", justifyContent: "space-between", marginTop: 8,
            fontFamily: MONO, fontSize: 24, color: "#F6EEDF", opacity: on,
            transform: `translateX(${(1 - on) * 40}px)`,
            fontVariantNumeric: "tabular-nums" as const }}>
            <span style={{ color: rgba("#F6EEDF", 0.6) }}>{st.pct}</span>
            <span>−₹{st.amt.toLocaleString("en-IN")}</span>
          </div>
        );
      })}
      {t >= taxStampAt ? (
        <div style={{ marginTop: 10, paddingTop: 10, borderTop: `1.5px solid ${rgba("#FFF", 0.25)}`,
          display: "flex", justifyContent: "space-between", fontFamily: DISP, fontSize: 30,
          color: "#FFB0A0", transform: `scale(${1 + settle(t, taxStampAt, 0.4) * 0.08})`,
          fontVariantNumeric: "tabular-nums" as const }}>
          <span>TOTAL</span><span>−₹3,62,352</span>
        </div>
      ) : null}
    </div>
  ) : null;

  /* ------------------------------------------------------------- give ----- */
  const PROMPT = "Break my CTC of ₹____ into real monthly in-hand (new regime FY25-26). List every deduction — PF ×2, gratuity, variable held, prof tax, income tax after 87A. Then: the ONE line to negotiate, and its per-month worth.";
  const giveP = OUT_E(clamp01((t - giveAt) / 0.5));
  const typed = Math.floor(clamp01((t - giveAt - 0.1) / 0.9) * PROMPT.length);
  const give = t >= giveAt ? (
    <div style={{ position: "absolute", left: 70, top: 380, width: 940, zIndex: 32,
      opacity: giveP * (1 - clamp01((t - (endAt - 0.9)) / 0.5)) }}>
      <div style={{ background: "linear-gradient(180deg, #14231A, #0D1811)", borderRadius: 20,
        padding: "24px 28px", boxShadow: cardShadow, border: `1.5px solid ${rgba(W3.green, 0.35)}` }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontFamily: MONO, fontSize: 22, color: W3.green, letterSpacing: 2 }}>✳ CTC DECODER</span>
          <span style={{ fontFamily: MONO, fontSize: 20, color: "#0D1811", background: W3.green,
            borderRadius: 8, padding: "4px 12px", fontWeight: 700,
            opacity: typed >= PROMPT.length ? 1 : 0.25 }}>PINNED ✓ COPY KARO</span>
        </div>
        <div style={{ marginTop: 14, fontFamily: MONO, fontSize: 27, lineHeight: 1.55,
          color: "#D9F2E2", minHeight: 180 }}>
          {"> "}{PROMPT.slice(0, typed)}
          {typed < PROMPT.length ? <span style={{ opacity: Math.sin(t * 9) > 0 ? 1 : 0 }}>▌</span> : null}
        </div>
        {/* the reply: what the viewer GETS when they paste the line */}
        {(() => {
          const rOn = OUT_E(clamp01((t - giveAt - 1.5) / 0.5));
          if (rOn < 0.01) return null;
          const BARS = [
            { l: "CTC", v: 3400000, c: W3.money },
            { l: "HOLD", v: 510000, c: "#5F7A52" },
            { l: "PF+SAATHI", v: 419216, c: "#5F7A52" },
            { l: "TAX", v: 362352, c: W3.red },
            { l: "IN-HAND", v: 2108432, c: W3.green },
          ];
          return (
            <div style={{ marginTop: 14, opacity: rOn }}>
              <div style={{ fontFamily: MONO, fontSize: 20, color: "#4ADE80", letterSpacing: 2 }}>✳ CLAUDE: · figures per YEAR</div>
              {BARS.map((b, i) => {
                const w = (b.v / 3400000) * 100;
                const grow = OUT_E(clamp01((t - giveAt - 1.6 - i * 0.16) / 0.4));
                return (
                  <div key={b.l} style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 7 }}>
                    <span style={{ fontFamily: MONO, fontSize: 17, color: rgba("#D9F2E2", 0.8),
                      width: 118, textAlign: "right" as const }}>{b.l}</span>
                    <div style={{ height: 24, width: `${w * grow * 0.62}%`, borderRadius: 5,
                      background: b.c, boxShadow: `0 2px 5px ${rgba("#000", 0.4)}` }} />
                    <span style={{ fontFamily: MONO, fontSize: 16, color: rgba("#D9F2E2", 0.65),
                      opacity: grow, fontVariantNumeric: "tabular-nums" as const }}>₹{b.v.toLocaleString("en-IN")}</span>
                  </div>
                );
              })}
              <div style={{ marginTop: 10, fontFamily: MONO, fontSize: 20, color: "#D9F2E2" }}>
                in-hand ₹21,08,432 ÷ 12 = <span style={{ color: W3.green, fontWeight: 700 }}>₹1,75,702/month</span> — matches your SMS ✓
              </div>
              <div style={{ marginTop: 6, fontFamily: MONO, fontSize: 19, color: rgba("#D9F2E2", 0.7) }}>
                this exact breakup, one line — copy · paste · run
              </div>
            </div>
          );
        })()}
        <div style={{ marginTop: 10, fontFamily: MONO, fontSize: 21, color: rgba("#D9F2E2", 0.6) }}>
          model: fable-5 ✓ · cost: ₹0
        </div>
      </div>
    </div>
  ) : null;

  /* ------------------------------------------------------------ chips ----- */
  const chipEl = (() => {
    let cur: Chip | null = null;
    for (const c of chips) { const end = c.end ?? c.t + 1.9; if (t >= c.t && t < end) { cur = c; break; } }
    if (!cur) return null;
    const pop = clamp01((t - cur.t) * fps / 2);
    if (cur.big) {
      return (
        <div style={{ position: "absolute", left: 0, right: 0, top: 1290, textAlign: "center", zIndex: 40,
          opacity: pop, transform: `scale(${0.92 + 0.08 * pop + settle(t, cur.t, 0.4) * 0.05})` }}>
          <span style={{ fontFamily: DISP, fontSize: 78, color: "#FFF6EC",
            background: cur.text.startsWith("TAX") ? W3.red : rgba("#211A12", 0.94),
            padding: "6px 32px", borderRadius: 20, boxShadow: cardShadow }}>{cur.text}</span>
        </div>
      );
    }
    return (
      <div style={{ position: "absolute", left: 0, right: 0, top: 1455, display: "flex",
        justifyContent: "center", zIndex: 40, opacity: pop,
        transform: `translateY(-50%) scale(${(0.94 + 0.06 * pop) * (1 + settle(t, cur.t, 0.4) * 0.05)})` }}>
        <div style={{ fontFamily: DISP, fontWeight: 800, fontSize: 56, textTransform: "uppercase" as const,
          whiteSpace: "nowrap" as const, color: cur.hot ? "#FFF6EC" : "#F2E8D8",
          background: cur.hot ? W3.red : rgba("#211A12", 0.92),
          padding: "8px 28px", borderRadius: 18, boxShadow: cardShadow,
          border: cur.hot ? undefined : `1.5px solid ${rgba("#FFF6E8", 0.18)}` }}>{cur.text}</div>
      </div>
    );
  })();

  /* -------------------------------------------------------- exposure ------ */
  const expo: [number, number][] = [
    [0, 1.02], [brickAt, 1.0], [varpayAt + 0.6, 1.06], [varpayAt + 1.0, 0.97],
    [taxAt, 0.9], [bounceAt, 1.08], [bounceAt + 0.5, 0.99],
    [creditAt, 1.07], [creditAt + 0.5, 1.0], [endAt, 1.01],
  ];

  /* cleavers rack: which cleaver hangs where over the brick */
  const cleavers = (
    <>
      <Cleaver t={t} at={varpayAt} x={250} topY={BRICK_BOT - 620 * (1 - choppedFrac * (1 / 0.38) * 0.45)} scale={1.25} label="VARIABLE PAY" />
      <Cleaver t={t} at={cascadeAts[0]} x={320} topY={BRICK_BOT - 620 * (1 - choppedFrac * (1 / 0.38) * 0.45)} label="EMPLOYER PF" />
      <Cleaver t={t} at={cascadeAts[1]} x={420} topY={BRICK_BOT - 620 * (1 - choppedFrac * (1 / 0.38) * 0.45)} scale={0.88} label="GRATUITY" />
      <Cleaver t={t} at={cascadeAts[2]} x={360} topY={BRICK_BOT - 620 * (1 - choppedFrac * (1 / 0.38) * 0.45)} scale={0.8} label="INSURANCE" />
      <Cleaver t={t} at={cascadeAts[3]} x={300} topY={BRICK_BOT - 620 * (1 - choppedFrac * (1 / 0.38) * 0.45)} scale={0.95} label="EMPLOYEE PF" />
      <Cleaver t={t} at={cascadeAts[4]} x={440} topY={BRICK_BOT - 620 * (1 - choppedFrac * (1 / 0.38) * 0.45)} scale={0.66} label="PROF TAX" />
      {/* the boss: winds up huge, BOUNCES on the first 4L, then chops the
          ladder — each swing faster, the LAST one the hardest (30% + cess) */}
      <Cleaver t={t} at={taxAt} x={200} topY={BRICK_BOT - 620 * (1 - choppedFrac * (1 / 0.38) * 0.45)} scale={1.55} label="INCOME TAX" red
        bounce bounceAt={bounceAt} />
      {ladderAts.map((a, i) => (
        <Cleaver key={i} t={t} at={a} x={230 + (i % 2) * 60} topY={BRICK_BOT - 620 * (1 - choppedFrac * (1 / 0.38) * 0.45)}
          scale={0.8 + i * 0.06} label={`TAX ${TAX_STEPS[i].pct}`} red />
      ))}
    </>
  );

  return (
    <FilmT.Provider value={t}>
      <AbsoluteFill style={{ width, height }}>
        <AbsoluteFill style={{
          background: `radial-gradient(120% 85% at 50% 40%, ${W3.ground2} 0%, ${W3.ground} 60%, #D5C9B2 100%)`,
          transform: `translate(${shake * 0.7}px, ${shake}px)`,
        }}>
          {/* the desk world */}
          <Img src={P("desk_scene.png")} style={{
            position: "absolute", left: -60, top: 980, width: 1200, height: 750,
            objectFit: "cover", opacity: 0.9, borderRadius: 24,
            filter: `brightness(${t >= giveAt ? 0.5 : t >= brickAt ? 0.92 : 1})`,
            transform: `scale(${1.02 + Math.sin(t * 0.7) * 0.008})`,
          }} />
          <ExposureScore keys={expo}>
            {brick}
            {brickTag}
            {cleavers}
            {cart}
            {offer}
            {confetti}
          </ExposureScore>
          {chat}
          {sms}
          {creditMath}
          {wafer}
          {shield}
          {taxablePanel}
          {slivers}
          {ladder}
          {brand}
          {give}
        </AbsoluteFill>
        <FlashCut at={[varpayAt + 0.65, bounceAt, creditAt]} color="#FFE9C4" opacity={0.3} />
        <svg style={{ position: "absolute", inset: 0, opacity: 0.05, mixBlendMode: "overlay", pointerEvents: "none" }}>
          <filter id="sb-grain"><feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" seed={9} /></filter>
          <rect width="100%" height="100%" filter="url(#sb-grain)" />
        </svg>
        <div style={{ position: "absolute", inset: 0, pointerEvents: "none",
          background: `radial-gradient(130% 95% at 50% 42%, transparent 55%, ${rgba("#4A3B26", 0.26)} 100%)` }} />
        {chipEl}
        {pings.map((pg, i) => <EngagePing key={i} t={t} ping={pg} />)}
      </AbsoluteFill>
    </FilmT.Provider>
  );
};

/* ---- canonical demo (planned clock) -------------------------------------- */
export const salaryBrickDemo: SalaryBrickProps = {
  pings: [
    { at: 17.6, kind: "like", tip: "worth a like? hit it ✨" },
    { at: 27.8, kind: "comment", tip: "drop your gap 👇" },
    { at: 30.9, kind: "subscribe", tip: "more of this 🔔" },
  ],
  chips: [
    { t: 0.3, end: 1.6, text: "34 LAKH? 🎉", hot: true },
    { t: 1.7, end: 3.3, text: "WHY SO SMALL?" },
    { t: 3.4, end: 4.5, text: "CTC = BRICK" },
    { t: 4.6, end: 6.0, text: "FIRST CUT", hot: true },
    { t: 6.1, end: 8.4, text: "VARIABLE −₹5,10,000", hot: true, big: true },
    { t: 8.5, end: 10.8, text: "ON HOLD" },
    { t: 10.9, end: 11.6, text: "EMPLOYER PF ✂" },
    { t: 11.7, end: 12.3, text: "GRATUITY ✂" },
    { t: 12.4, end: 12.9, text: "INSURANCE ✂" },
    { t: 13.0, end: 13.5, text: "EMPLOYEE PF ✂" },
    { t: 13.6, end: 14.9, text: "PROF TAX ✂" },
    { t: 15.0, end: 15.9, text: "NOW: TAX", hot: true },
    { t: 16.0, end: 17.4, text: "FIRST ₹4L FREE" },
    { t: 17.5, end: 18.8, text: "SLAB BY SLAB" },
    { t: 18.9, end: 20.1, text: "30% + CESS", hot: true },
    { t: 20.2, end: 22.0, text: "TAX −₹3,62,352", hot: true, big: true },
    { t: 22.1, end: 24.5, text: "TAX ON TAX" },
    { t: 24.6, end: 25.9, text: "WHAT'S LEFT?" },
    { t: 26.0, end: 27.5, text: "₹1,75,702 CREDITED", hot: true },
    { t: 27.6, end: 28.7, text: "GAP: ₹12,91,568" },
    { t: 28.8, end: 30.6, text: "PROMPT PINNED", hot: true },
    { t: 30.7, end: 33.1, text: "RUN YOUR NUMBERS" },
  ],
};
