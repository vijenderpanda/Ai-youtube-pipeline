import React from "react";
import { AbsoluteFill, useVideoConfig } from "remotion";
import { interpolatePath } from "@remotion/paths";
import { rgba } from "./kit";
import { clamp01, mhash, OUT_E, IN_E, settle, smear, idle } from "./motion";
import { useFilmT, FilmT } from "./filmclock";
import { PAPER, PaperStage, PaperFonts, FRAUNCES, FRAUNCES_IT } from "./Kaagaz";
import { WorldCamera, Parallax } from "./WorldCamera";
import { ExposureScore, FlashCut } from "./craft";

/* =============================================================================
   ZeroStackPaper — ep2: "The ₹0 Stack", in the paper world.

   Bills ARE paper, so the world is paper: a vertical cut-paper machine, four
   floors, one coral crumpled bill-ball falling through it. Three free AIs
   each do ONE visible transformation, and a ₹0 paper tag rides the HUD the
   whole film — unproven at frame 1, stamped TRUE in the brightest frame.

   THE LEVEL-UP, delivered with the new toolchain:
   - TRUE MORPHS via @remotion/paths interpolatePath: six bill sheets fold
     into the crumpled ball at the open, and the ball is rolled FLAT into a
     clean sheet at the payoff. Real path interpolation, not a crossfade.
   - The droplets DRAW the chart (the judge's pick for the one Ravie-grade
     morph): coral drops leak from the hot table row, fall with gravity, and
     the spike polyline exists only where they have landed.
   - GLOBAL physics: one gravity constant for all four floor-drops; squash on
     every landing; smear above the velocity threshold; anticipation wobble
     before every hatch.
   - EXPOSURE SCORE designed in: the 4s near-black breath before the verdict
     (only the spike ember + the ₹0 tag alive), peaks PLACED at the knee, the
     stamp, and the payoff. C1 passes by design, not by luck.

   Numbers (manifest-sourced): "UP TO ₹18/HR" (1.5T non-inverter ~1.9 u/hr ×
   Mumbai ₹9.5/kWh), "UP TO ₹900/MO" (derived on screen), ₹0 (the premise,
   free tiers verified). No personal bills anywhere; bill sheets are greeked.
   ========================================================================== */

const G = 6000;                       // px/s^2 — the one gravity constant
const FLOORS = { f0: 1150, f1: 1810, f2: 2570, f3: 3330, f4: 3760 };
const CX = 540;

/* the hero's two true shapes: a bill sheet and the crumpled ball, path-morphable
   (same command count, both closed). Authored in a -100..100 box. */
const SHEET_PATH =
  "M -70 -92 L 70 -92 L 72 -60 L 70 -20 L 72 20 L 70 60 L 68 92 L -68 92 L -72 60 L -70 20 L -72 -20 L -70 -60 Z";
const BALL_PATH =
  "M -18 -88 L 42 -74 L 84 -30 L 88 12 L 62 58 L 30 88 L -26 84 L -70 52 L -88 6 L -76 -40 L -52 -72 L -18 -88 Z";

export type ZeroStackPaperProps = {
  crumpleAt?: number;
  drop1At?: number;
  kneeAt?: number;
  spikeAt?: number;
  drop2At?: number;
  chartAt?: number;
  breathAt?: number;
  drop3At?: number;
  stampAt?: number;
  drop4At?: number;
  smoothAt?: number;
  payoffAt?: number;
  loopAt?: number;
  endAt?: number;
  chips?: { t: number; end?: number; text: string; hot?: boolean }[];
  start?: number;
  width?: number;
  height?: number;
};

/* one drop: from yA (standing) through a hatch to yB, gravity-true */
const dropY = (t: number, at: number, yA: number, yB: number) => {
  if (t < at) return { y: yA, v: 0, landed: false };
  const dur = Math.sqrt((2 * (yB - yA)) / G);
  const d = Math.min(t - at, dur);
  const y = yA + 0.5 * G * d * d;
  return { y: Math.min(y, yB), v: G * d, landed: t - at >= dur, landAt: at + dur } as any;
};

export const ZeroStackPaper: React.FC<ZeroStackPaperProps> = ({
  crumpleAt = 1.4,
  drop1At = 6.2,
  kneeAt = 6.5,
  spikeAt = 9.9,
  drop2At = 12.8,
  chartAt = 13.3,
  breathAt = 17.2,
  drop3At = 20.7,
  stampAt = 21.5,
  drop4At = 25.9,
  smoothAt = 26.7,
  payoffAt = 27.8,
  loopAt = 31.2,
  endAt = 34.3,
  chips = [],
  start = 0,
  width = 1080,
  height = 1920,
}) => {
  const t = useFilmT();
  const { fps } = useVideoConfig();

  /* ---- the hero's vertical life ------------------------------------------ */
  const standH = 170;                            // the ball's rest height
  const d1 = dropY(t, drop1At, FLOORS.f0, FLOORS.f1);
  const d2 = dropY(t, drop2At, FLOORS.f1, FLOORS.f2);
  const d3 = dropY(t, drop3At, FLOORS.f2, FLOORS.f3);
  const d4 = dropY(t, drop4At, FLOORS.f3, FLOORS.f4);
  let heroY = FLOORS.f0;
  let heroV = 0;
  if (t >= drop4At) { heroY = d4.y; heroV = d4.landed ? 0 : d4.v; }
  else if (t >= drop3At) { heroY = d3.y; heroV = d3.landed ? 0 : d3.v; }
  else if (t >= drop2At) { heroY = d2.y; heroV = d2.landed ? 0 : d2.v; }
  else if (t >= drop1At) { heroY = d1.y; heroV = d1.landed ? 0 : d1.v; }
  const sm = smear(heroV, 900);
  let squash = 0;
  for (const dd of [d1, d2, d3, d4]) {
    if ((dd as any).landed && (dd as any).landAt) squash += settle(t, (dd as any).landAt, 0.42);
  }
  // anticipation wobble before every hatch
  let wobble = 0;
  for (const at of [drop1At, drop2At, drop3At, drop4At]) {
    const d = t - (at - 0.5);
    if (d >= 0 && t < at) wobble += Math.sin(d * 22) * 4 * (d / 0.5);
  }

  /* the hero's SHAPE: sheets -> ball at the open, ball -> sheet at the smooth */
  const crumple = OUT_E(clamp01((t - crumpleAt) / 0.5));
  const smooth = OUT_E(clamp01((t - smoothAt) / 0.6));
  const heroPath = interpolatePath(clamp01(crumple - smooth), SHEET_PATH, BALL_PATH);
  const heroScale = 0.84 + crumple * 0.06 - smooth * 0.05;

  /* ---- camera: chase every drop, come home for the loop ------------------- */
  const track = [
    { t: 0, x: CX, y: 900, z: 1.24 },
    { t: crumpleAt + 0.7, x: CX, y: 930, z: 1.38 },
    { t: drop1At - 0.3, x: CX, y: 980, z: 1.26 },
    { t: drop1At + 0.55, x: CX, y: 1560, z: 1.18, dur: 0.55 },
    { t: kneeAt + 1.6, x: CX, y: 1580, z: 1.42 },
    { t: spikeAt + 1.2, x: CX, y: 1600, z: 1.34 },
    { t: drop2At + 0.6, x: CX, y: 2300, z: 1.2, dur: 0.6 },
    { t: chartAt + 2.2, x: CX, y: 2330, z: 1.36 },
    { t: breathAt + 1.0, x: CX, y: 2340, z: 1.28 },
    { t: drop3At + 0.6, x: CX, y: 3090, z: 1.2, dur: 0.6 },
    { t: stampAt + 1.6, x: CX, y: 3130, z: 1.4 },
    { t: drop4At + 0.55, x: CX, y: 3570, z: 1.24, dur: 0.55 },
    { t: payoffAt + 1.0, x: CX, y: 3590, z: 1.36 },
    { t: loopAt + 1.2, x: CX, y: 900, z: 1.24, dur: 1.2 },     // home
  ];

  /* ---- exposure score (C1 designed in) ------------------------------------ */
  const expo: [number, number][] = [
    [0, 0.62], [1.2, 0.72], [crumpleAt + 0.3, 0.66],
    [drop1At, 0.8], [kneeAt, 1.0], [kneeAt + 0.5, 0.78],
    [spikeAt, 0.7], [drop2At, 0.75], [chartAt + 1.5, 0.68],
    [breathAt - 0.4, 0.5], [breathAt + 0.4, 0.14], [breathAt + 2.6, 0.1], [drop3At - 0.4, 0.3],
    [drop3At + 0.3, 0.7], [stampAt, 0.88], [stampAt + 0.6, 0.74],
    [drop4At, 0.66], [payoffAt, 0.98], [payoffAt + 1.4, 0.86], [loopAt + 1.2, 0.66],
  ];

  const breathP = clamp01((t - breathAt) / 0.6) * (1 - clamp01((t - (drop3At - 0.4)) / 0.4));

  /* ---- shared paper bits --------------------------------------------------- */
  const inkCard = (x: number, y: number, w: number, h: number, r = 18): React.CSSProperties => ({
    position: "absolute", left: x, top: y, width: w, height: h,
    background: "#FBF6EC", borderRadius: r,
    boxShadow: `4px 7px 0 ${PAPER.shadow}, 0 2px 0 ${rgba("#fff", 0.6)} inset`,
    border: `2px solid ${rgba(PAPER.ink, 0.14)}`,
  });

  /* droplets that draw the chart */
  const DROPS = 7;
  const chartPts: [number, number][] = [];
  for (let i = 0; i < DROPS; i++) {
    const at = chartAt + i * 0.28;
    const x = 452 + i * 56;
    const spike = i === 4;
    const yTarget = FLOORS.f2 - 120 - (spike ? 270 : 50 + mhash(i * 3) * 60);
    if (t >= at + 0.34) chartPts.push([x, yTarget]);
  }

  /* the press head */
  const pressD = t - stampAt;
  const pressY = pressD < -0.3 ? -210
    : pressD < 0 ? -210 - 34 * Math.sin(clamp01((pressD + 0.3) / 0.3) * Math.PI * 0.5)   // wind up
    : pressD < 0.1 ? -244 + 244 * IN_E(clamp01(pressD / 0.1))                              // the slam
    : 0;
  const pressDown = pressD >= 0.1;

  return (
    <FilmT.Provider value={t}>
    <AbsoluteFill style={{ width, height, background: PAPER.ground }}>
      <PaperFonts />
      <ExposureScore keys={expo}>
        <WorldCamera track={track} punches={[kneeAt, stampAt, payoffAt]} punchScale={1.1} breath={4}>

          {/* ---- the world: floors + walls ---- */}
          <Parallax depth={0.4}>
            {[420, 1180, 1940, 2700, 3440].map((y, i) => (
              <div key={i} style={{ position: "absolute", left: -200, top: y, width: 1480, height: 3,
                                    background: rgba(PAPER.ink, 0.05) }} />
            ))}
          </Parallax>

          {Object.values(FLOORS).map((fy, i) => (
            <React.Fragment key={i}>
              {/* floor slab with the hatch gap */}
              <div style={{ position: "absolute", left: -60, top: fy, width: 400 + 60, height: 26,
                            background: "#D9CCB2", boxShadow: `0 7px 0 ${PAPER.shadow}` }} />
              <div style={{ position: "absolute", left: 740, top: fy, width: 400, height: 26,
                            background: "#D9CCB2", boxShadow: `0 7px 0 ${PAPER.shadow}` }} />
              {/* hatch doors — swing open just before each drop */}
              {(() => {
                const at = [drop1At, drop2At, drop3At, drop4At, 1e9][i];
                const open = OUT_E(clamp01((t - (at - 0.12)) / 0.3));
                return (
                  <>
                    <div style={{ position: "absolute", left: 340, top: fy, width: 200, height: 22,
                                  background: "#D8CBB4", transformOrigin: "0 50%",
                                  transform: `rotate(${open * 78}deg)`,
                                  boxShadow: `0 5px 0 ${PAPER.shadow}` }} />
                    <div style={{ position: "absolute", left: 540, top: fy, width: 200, height: 22,
                                  background: "#D8CBB4", transformOrigin: "100% 50%",
                                  transform: `rotate(${-open * 78}deg)`,
                                  boxShadow: `0 5px 0 ${PAPER.shadow}` }} />
                  </>
                );
              })()}
            </React.Fragment>
          ))}

          {/* ---- F0: the pile ---- */}
          {Array.from({ length: 6 }, (_, i) => {
            // six greeked bills folding INTO the hero: they fly to centre and die
            // as the morph takes over
            const gone = clamp01((t - crumpleAt) / 0.45);
            const fan = (i - 2.5) * 26;
            const fx = 320 + i * 82 + (CX - (320 + i * 82)) * OUT_E(gone);
            const fy = FLOORS.f0 - 120 + Math.abs(i - 2.5) * 8 + (FLOORS.f0 - 150 - (FLOORS.f0 - 120)) * OUT_E(gone);
            if (gone >= 0.96) return null;
            return (
              <div key={i} style={{
                ...inkCard(fx - 74, fy - 100, 148, 200, 10),
                opacity: 1 - gone * 0.85,
                transform: `rotate(${fan * (1 - gone) + gone * 160 * (i % 2 ? 1 : -1)}deg) scale(${1 - gone * 0.4})`,
              }}>
                {[0, 1, 2, 3].map((k) => (
                  <div key={k} style={{ position: "absolute", left: 14, top: 20 + k * 26,
                                        width: 60 + mhash(i * 7 + k) * 34, height: 7, borderRadius: 3,
                                        background: rgba(PAPER.ink, 0.22) }} />
                ))}
                <div style={{ position: "absolute", right: 10, bottom: 10, fontFamily: FRAUNCES,
                              fontWeight: 800, fontSize: 20, color: PAPER.coralDeep, opacity: 0.7,
                              transform: "rotate(-12deg)" }}>DUE</div>
              </div>
            );
          })}

          {/* the desk lamp, F0 + F4 */}
          {[[210, FLOORS.f0], [240, FLOORS.f4]].map(([lx, ly], i) => (
            <svg key={i} width={260} height={300} style={{ position: "absolute", left: lx - 60, top: ly - 268 }}>
              <g fill="#D8CBB4" stroke={rgba(PAPER.ink, 0.2)} strokeWidth={2}>
                <rect x={20} y={252} width={110} height={16} rx={8} />
                <rect x={64} y={130} width={14} height={130} rx={7} transform="rotate(14 71 195)" />
                <path d="M 96 96 L 196 128 L 168 178 L 78 140 Z" fill="#E8DCC6" />
              </g>
              <ellipse cx={150} cy={150} rx={26} ry={16} fill={rgba("#FFE9B0", 0.9)} />
            </svg>
          ))}

          {/* ---- F1: the scanner arch + the table card ---- */}
          <svg width={520} height={360} style={{ position: "absolute", left: CX - 260, top: FLOORS.f1 - 350 }}>
            <g fill="#CDBFA5" stroke={rgba(PAPER.ink, 0.2)} strokeWidth={3}>
              <rect x={60} y={40} width={64} height={310} rx={22} />
              <rect x={396} y={40} width={64} height={310} rx={22} />
              <rect x={40} y={10} width={440} height={64} rx={26} />
            </g>
            {/* the scan beam lights as the hero passes */}
            {(() => {
              const passing = t >= drop1At && t < drop1At + 0.5;
              return <rect x={128} y={70} width={264} height={6}
                           fill={passing ? PAPER.coral : rgba(PAPER.ink, 0.1)}
                           opacity={passing ? 0.9 : 0.5} />;
            })()}
          </svg>

          {/* the TABLE card snaps out at the knee */}
          {t >= kneeAt ? (() => {
            const on = OUT_E(clamp01((t - kneeAt) / 0.3));
            const rows = 5;
            return (
              <div style={{
                ...inkCard(CX - 190, FLOORS.f1 - 300, 380, 250),
                opacity: Math.min(1, on * 1.5),
                transform: `translateX(${(1 - on) * -60}px) rotate(${(1 - on) * -6}deg) scale(${0.8 + on * 0.2 + settle(t, kneeAt + 0.3, 0.4) * 0.04})`,
              }}>
                {Array.from({ length: rows }, (_, r) => {
                  const hot = r === 3 && t >= spikeAt;
                  const glow = hot ? 0.5 + Math.sin(t * 5) * 0.2 : 0;
                  return (
                    <div key={r} style={{
                      position: "absolute", left: 18, top: 20 + r * 44, width: 344, height: 32,
                      borderRadius: 8,
                      background: hot ? rgba(PAPER.coral, 0.25 + glow * 0.3) : rgba(PAPER.ink, 0.06),
                      border: hot ? `2px solid ${PAPER.coralDeep}` : undefined,
                      display: "flex", alignItems: "center", gap: 10, padding: "0 12px",
                    }}>
                      <div style={{ width: 60 + mhash(r * 5) * 40, height: 8, borderRadius: 4,
                                    background: rgba(PAPER.ink, hot ? 0.55 : 0.3) }} />
                      <div style={{ marginLeft: "auto", width: 46 + mhash(r * 9) * 30, height: 8,
                                    borderRadius: 4, background: rgba(PAPER.ink, hot ? 0.55 : 0.3) }} />
                    </div>
                  );
                })}
              </div>
            );
          })() : null}

          {/* ---- F2: the plotter + droplets drawing the chart ---- */}
          <svg width={620} height={420} style={{ position: "absolute", left: CX - 310, top: FLOORS.f2 - 410 }}>
            <g fill="#CDBFA5" stroke={rgba(PAPER.ink, 0.2)} strokeWidth={3}>
              <rect x={30} y={330} width={180} height={18} rx={9} transform="rotate(-18 120 339)" />
              <rect x={60} y={80} width={16} height={280} rx={8} />
              <circle cx={68} cy={70} r={22} />
            </g>
            {/* the chart frame */}
            <rect x={180} y={40} width={420} height={330} rx={16} fill="#FBF6EC"
                  stroke={rgba(PAPER.ink, 0.14)} strokeWidth={2} />
          </svg>
          {/* droplets: leak from the hot row above, fall, and DRAW the line */}
          {Array.from({ length: DROPS }, (_, i) => {
            const at = chartAt + i * 0.28;
            if (t < at) return null;
            const x = 452 + i * 56;
            const spike = i === 4;
            const yTarget = FLOORS.f2 - 120 - (spike ? 270 : 50 + mhash(i * 3) * 60);
            const y0 = FLOORS.f1 - 160;                 // from the table's hot row
            const p = clamp01((t - at) / 0.34);
            const y = y0 + (yTarget - y0) * p * p;      // gravity-ish
            if (p >= 1) return null;
            return <div key={i} style={{
              position: "absolute", left: x - 9, top: y - 9, width: 18, height: 18,
              borderRadius: 9, background: PAPER.coral,
              boxShadow: `2px 4px 0 ${PAPER.shadow}`,
            }} />;
          })}
          {chartPts.length >= 2 ? (
            <svg width={1080} height={4300} style={{ position: "absolute", left: 0, top: 0 }}>
              <path d={chartPts.map((p, i) => `${i ? "L" : "M"}${p[0]} ${p[1]}`).join(" ")}
                    stroke={PAPER.coralDeep} strokeWidth={7} fill="none"
                    strokeLinecap="round" strokeLinejoin="round" />
              {chartPts.map((p, i) => (
                <circle key={i} cx={p[0]} cy={p[1]} r={8} fill={PAPER.coral} />
              ))}
              {/* the spike, circled when complete */}
              {chartPts.length >= 5 ? (
                <circle cx={452 + 4 * 56} cy={FLOORS.f2 - 390}
                        r={34 + settle(t, chartAt + 4 * 0.28 + 0.4, 0.5) * 8}
                        fill="none" stroke={PAPER.green} strokeWidth={5} strokeDasharray="10 7" />
              ) : null}
            </svg>
          ) : null}

          {/* the ember: the spike glows through the breath */}
          {t >= breathAt ? (
            <div style={{
              position: "absolute", left: 300 + 4 * 78 - 20, top: FLOORS.f2 - 470, width: 40, height: 40,
              borderRadius: 20, background: PAPER.coral,
              boxShadow: `0 0 ${30 + Math.sin(t * 3.4) * 12}px ${rgba(PAPER.coral, 0.8)}`,
              opacity: breathP,
            }} />
          ) : null}
          {/* the suspect silhouette: an AC unit fading in during the dark */}
          <svg width={300} height={180} style={{
            position: "absolute", left: 700, top: FLOORS.f2 - 240,
            opacity: breathP * 0.85,
          }}>
            <rect x={10} y={30} width={270} height={120} rx={18} fill="#4A4038" />
            {[0, 1, 2, 3, 4].map((k) => (
              <rect key={k} x={30} y={96 + k * 11} width={230} height={5} rx={2.5} fill="#372F29" />
            ))}
            <rect x={30} y={48} width={140} height={26} rx={8} fill="#372F29" />
            <circle cx={236} cy={61} r={9} fill="#5C5148" />
            <rect x={40} y={152} width={8} height={20} rx={4} fill="#372F29" />
          </svg>

          {/* ---- F3: the press ---- */}
          <svg width={560} height={420} style={{ position: "absolute", left: CX - 280, top: FLOORS.f3 - 410 }}>
            <g fill="#CDBFA5" stroke={rgba(PAPER.ink, 0.2)} strokeWidth={3}>
              <rect x={40} y={0} width={480} height={54} rx={20} />
              <rect x={70} y={40} width={30} height={120} rx={12} />
              <rect x={460} y={40} width={30} height={120} rx={12} />
            </g>
            <rect x={150} y={60 + pressY + 260} width={260} height={70} rx={16}
                  fill="#C4B499" stroke={rgba(PAPER.ink, 0.24)} strokeWidth={3} />
          </svg>
          {/* the verdict card under the press */}
          {t >= drop3At + 0.3 ? (
            <div style={{
              ...inkCard(CX - 170, FLOORS.f3 - 110, 340, 86),
              display: "flex", alignItems: "center", justifyContent: "center",
              transform: `scale(${1 + settle(t, stampAt + 0.09, 0.5) * 0.08})`,
            }}>
              <span style={{
                fontFamily: FRAUNCES, fontWeight: 800, fontSize: 44, color: PAPER.ink,
                opacity: pressDown ? 1 : 0,
              }}>UP TO <span style={{ color: PAPER.coralDeep }}>₹18/HR</span></span>
            </div>
          ) : null}
          {/* impact specks */}
          {pressDown && pressD < 0.5 ? Array.from({ length: 8 }, (_, i) => {
            const p = clamp01((pressD - 0.09) / 0.4);
            const a = (i / 8) * Math.PI * 2;
            return <div key={i} style={{
              position: "absolute",
              left: CX + Math.cos(a) * (40 + p * 130) - 5,
              top: FLOORS.f3 - 70 + Math.sin(a) * (16 + p * 40) - 5,
              width: 10, height: 10, borderRadius: 3, background: "#E2D7C3",
              opacity: (1 - p) * 0.9, transform: `rotate(${p * 200}deg)`,
            }} />;
          }) : null}

          {/* ---- F4: rollers + the verdict phone-card ---- */}
          <svg width={420} height={200} style={{ position: "absolute", left: CX - 210, top: FLOORS.f4 - 240 }}>
            {[0, 1].map((i) => (
              <g key={i} transform={`translate(${110 + i * 200} 100) rotate(${t * 140 * (i ? -1 : 1)})`}>
                <circle r={54} fill="#C4B499" stroke={rgba(PAPER.ink, 0.24)} strokeWidth={3} />
                <line x1={-54} y1={0} x2={54} y2={0} stroke={rgba(PAPER.ink, 0.16)} strokeWidth={4} />
              </g>
            ))}
          </svg>
          {t >= payoffAt - 0.3 ? (() => {
            const on = OUT_E(clamp01((t - (payoffAt - 0.3)) / 0.45));
            return (
              <div style={{
                ...inkCard(CX + 90, FLOORS.f4 - 330, 300, 300, 26),
                opacity: Math.min(1, on * 1.4),
                transform: `translateY(${(1 - on) * 40}px) scale(${0.9 + on * 0.1})`,
                display: "flex", flexDirection: "column", alignItems: "center",
                justifyContent: "center", gap: 12,
              }}>
                <span style={{ fontFamily: FRAUNCES, fontWeight: 800, fontSize: 40,
                               color: PAPER.green }}>UP TO</span>
                <span style={{ fontFamily: FRAUNCES, fontWeight: 800, fontSize: 62,
                               color: PAPER.ink }}>₹900<span style={{ fontSize: 34 }}>/MO</span></span>
                <span style={{ fontFamily: FRAUNCES_IT, fontStyle: "italic", fontSize: 30,
                               color: PAPER.coralDeep }}>back.</span>
              </div>
            );
          })() : null}

          {/* ---- THE HERO ---- */}
          {(() => {
            const w = 200 * heroScale, h = 200 * heroScale;
            const grounded = heroV === 0;
            const sx = grounded ? 1 + squash * 0.1 : 1 / sm.stretch;
            const sy = grounded ? 1 - squash * 0.1 : sm.stretch;
            const wob = idle(t, 3, grounded ? 1.6 : 0);
            return (
              <svg width={240} height={240} viewBox="-120 -120 240 240" style={{
                position: "absolute", left: CX - 120 + wobble + wob.x, top: heroY - 200 + wob.y,
                transform: `scale(${sx.toFixed(3)}, ${sy.toFixed(3)})`,
                transformOrigin: "50% 100%",
                filter: sm.blurPx > 0.4 && !grounded ? `blur(${sm.blurPx.toFixed(1)}px)` : undefined,
              }}>
                <g transform="translate(5 9)"><path d={heroPath} fill={PAPER.shadow} transform="scale(0.86)" /></g>
                <path d={heroPath} fill={PAPER.coral} transform="scale(0.86)" />
                <path d={heroPath} fill="none" stroke={PAPER.coralDeep} strokeWidth={4}
                      transform="scale(0.86)" opacity={0.5} />
              </svg>
            );
          })()}

          {/* the smoothed sheet's clean lines appear as the rollers finish */}
          {smooth > 0.6 ? (
            <div style={{ position: "absolute", left: CX - 62, top: FLOORS.f4 - 176, width: 124,
                          opacity: clamp01((smooth - 0.6) / 0.4) }}>
              {[0, 1, 2].map((k) => (
                <div key={k} style={{ width: 90 - k * 16, height: 7, borderRadius: 3, margin: "10px auto",
                                      background: rgba(PAPER.ink, 0.3) }} />
              ))}
            </div>
          ) : null}
        </WorldCamera>

        {/* the breath's darkness needs the world dark but the HUD alive — the
            ExposureScore handles the world; the ember + tag render above */}
      </ExposureScore>

      {/* ---- HUD: the ₹0 paper tag on its string, all film ---- */}
      {(() => {
        const sway = Math.sin(t * 1.4) * 3.5 + Math.sin(t * 0.7) * 2;
        const stamped = t >= payoffAt;
        const pop = 1 + settle(t, payoffAt, 0.5) * 0.16;
        return (
          <div style={{ position: "absolute", right: 74, top: 96, zIndex: 30,
                        transform: `rotate(${sway.toFixed(1)}deg)`, transformOrigin: "50% 0" }}>
            <div style={{ width: 2.5, height: 54, background: rgba(PAPER.ink, 0.4), margin: "0 auto" }} />
            <div style={{
              background: stamped ? PAPER.green : "#FBF6EC",
              border: `2.5px solid ${stamped ? PAPER.green : rgba(PAPER.ink, 0.3)}`,
              borderRadius: 14, padding: "10px 22px",
              boxShadow: `3px 5px 0 ${PAPER.shadow}`,
              transform: `scale(${pop.toFixed(3)})`,
              fontFamily: FRAUNCES, fontWeight: 800, fontSize: 44,
              color: stamped ? "#F6EFE3" : PAPER.ink,
            }}>₹0</div>
          </div>
        );
      })()}
      {/* ghost paid-tier tags sucked into the ₹0 (generic — no price claims) */}
      {[3.2, 11.4, 23.4].map((at, i) => {
        const p = clamp01((t - at) / 0.8);
        if (p <= 0 || p >= 1) return null;
        const e = IN_E(p);
        return (
          <div key={i} style={{
            position: "absolute",
            right: 74 + (1 - e) * (240 + i * 60),
            top: 130 + (1 - e) * (260 + i * 90),
            zIndex: 29, opacity: (1 - p * 0.7),
            transform: `scale(${1 - e * 0.6}) rotate(${e * 30}deg)`,
            fontFamily: FRAUNCES_IT, fontStyle: "italic", fontWeight: 700, fontSize: 34,
            color: rgba(PAPER.ink, 0.55),
            border: `2px dashed ${rgba(PAPER.ink, 0.4)}`, borderRadius: 12, padding: "6px 16px",
            background: rgba("#FBF6EC", 0.8),
          }}>PRO ——/mo</div>
        );
      })}

      <FlashCut at={[kneeAt, stampAt + 0.1]} color="#FFF3D8" opacity={0.3} />

      {/* ---- chips, paper-styled ---- */}
      {(() => {
        let cur: any = null;
        for (let i = 0; i < chips.length; i++) {
          const c = chips[i];
          const end = c.end ?? chips[i + 1]?.t ?? c.t + 1.9;
          if (t >= c.t && t < end) { cur = c; break; }
        }
        if (!cur) return null;
        const pop = Math.min(1, (t - cur.t) * fps / 2);
        return (
          <div style={{
            position: "absolute", left: 0, right: 0, top: 1306, zIndex: 40,
            display: "flex", justifyContent: "center",
            transform: `translateY(-50%) scale(${(0.94 + 0.06 * pop) * (1 + settle(t, cur.t, 0.4) * 0.05)})`,
            opacity: pop,
          }}>
            <div style={{
              fontFamily: FRAUNCES, fontWeight: 800, fontSize: 66,
              textTransform: "uppercase" as const, whiteSpace: "nowrap" as const,
              color: cur.hot ? "#F6EFE3" : PAPER.ink,
              background: cur.hot ? PAPER.coralDeep : rgba("#FBF6EC", 0.92),
              padding: "8px 30px", borderRadius: 18,
              boxShadow: `4px 7px 0 ${PAPER.shadow}`,
            }}>{cur.text}</div>
          </div>
        );
      })()}
    </AbsoluteFill>
    </FilmT.Provider>
  );
};

/* ---- canonical demo (planned clock) -------------------------------------- */
export const zeroStackPaperDemo: ZeroStackPaperProps = {
  crumpleAt: 1.4, drop1At: 6.2, kneeAt: 6.5, spikeAt: 9.9,
  drop2At: 12.8, chartAt: 13.3, breathAt: 17.2, drop3At: 20.7, stampAt: 21.5,
  drop4At: 25.9, smoothAt: 26.7, payoffAt: 27.8, loopAt: 31.2, endAt: 34.3,
  chips: [
    { t: 0.3, end: 1.4, text: "BIJLI SHOCK?", hot: true },
    { t: 1.6, end: 3.0, text: "6 BILLS" },
    { t: 4.9, end: 6.4, text: "GEMINI · FREE", hot: true },
    { t: 6.6, end: 8.0, text: "ONE TABLE" },
    { t: 9.9, end: 11.4, text: "THE SPIKE" },
    { t: 12.6, end: 14.2, text: "CLAUDE · FREE", hot: true },
    { t: 17.4, end: 19.4, text: "ONE SUSPECT" },
    { t: 20.6, end: 22.2, text: "CHATGPT · FREE", hot: true },
    { t: 22.4, end: 24.4, text: "₹18 / HOUR", hot: true },
    { t: 25.8, end: 27.6, text: "ONE HABIT" },
    { t: 27.8, end: 29.6, text: "₹900 BACK", hot: true },
    { t: 31.4, end: 33.8, text: "PROMPT BELOW" },
  ],
};
