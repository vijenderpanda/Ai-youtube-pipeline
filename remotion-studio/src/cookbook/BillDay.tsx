import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { rgba, clamp } from "./kit";
import { clamp01, mhash, OUT_E, IN_E, settle, idle } from "./motion";
import { useFilmT, FilmT } from "./filmclock";
import { WorldCamera } from "./WorldCamera";
import { ExposureScore, FlashCut } from "./craft";

/* =============================================================================
   BillDay — ep2 "GHAR MEIN CHOR": a whodunit in a sunlit house, daytime cut.

   VJ's call on the noir cut: "storyboards promising but instead of dark
   environment create day time environment." Same story, same treatment
   physics, daylight world: every environment is a BAKED-SUNLIGHT FLUX plate
   (assets/day/*), the ground is graded warm daylight, and the DARK cards —
   the bill bars and the terminal dock — are the value anchors the forensics
   demanded (dark-on-cream, the Isenberg move exactly). Cleared rooms don't
   go black; they GREY-WASH like evidence photos being filed away, so the
   countdown survives the daylight.

   THE STORY LOGIC, on screen (VJ's demand): three DEMO bill bars step up
   8,577 / 9,940 / 11,990 -> the AI overlays where SUMMER starts -> the
   Rs3,400 seasonal delta is boxed -> divided on screen by 30 days x 6 hrs ->
   the needle locks Rs18/HOUR (public cross-check in small print) -> and the
   payoff is the CIRCLE CLOSING: Rs18 x 6h x 30d lands back on the June bar.
   No number before its referent. Figures are DECLARED DEMO; the method
   (seasonal delta) is the real, teachable content.

   The five suspects are ROOMS. Verdicts visibly launch FROM the chat dock —
   the AI is the detective, never an anonymous stamp.
   ========================================================================== */

const DAY = {
  ground: "#EFE7D8",       // warm daylight wall
  ground2: "#F7F1E4",      // the sunlit center
  card: "#141110",
  ink: "#2B241D",          // dark ink on daylight
  paper: "#F2E8D8",        // light text on the DARK anchor cards
  mute: "#8A7D6A",
  coral: "#E8603C",
  amber: "#C77F14",        // amber deepened for a light ground
  green: "#4ADE80",        // terminal green, lives on the dark dock
  cleared: "#6E7D6E",
} as const;

const SANS = '"Inter", -apple-system, sans-serif';
const MONO = '"IBM Plex Mono", monospace';
const DISP = '"Fraunces", Georgia, serif';

/* the measured treatment: every floating card carries BOTH shadows + a rim */
const cardShadow = `0 6px 10px ${rgba("#000", 0.5)}, 0 36px 80px ${rgba("#000", 0.3)}`;
const cardRim = `inset 0 1.5px 0 ${rgba("#FFF6E8", 0.22)}`;

const ROOMS = [
  { id: "kitchen", plate: "assets/day/room_kitchen.png", label: "KITCHEN · FRIDGE" },
  { id: "tv", plate: "assets/day/room_tv.png", label: "LIVING · TV" },
  { id: "geyser", plate: "assets/day/room_geyser.png", label: "BATH · GEYSER" },
  { id: "washing", plate: "assets/day/room_washing.png", label: "UTILITY · WASHING" },
  { id: "study", plate: "assets/day/room_study.png", label: "STUDY · OLD AC" },
];
const STACK_TOP = 300;
const CARD_H = 200;
const CARD_GAP = 16;
const CARD_W = 900;
const STUDY = 4;
const studyCenterY = STACK_TOP + STUDY * (CARD_H + CARD_GAP) + CARD_H / 2;

export type BillDayProps = {
  bar2At?: number; bar3At?: number;
  lineupAt?: number; kneeAt?: number; caseAt?: number;
  clueAt?: number; deltaAt?: number;
  clearAts?: number[];
  pushAt?: number; plateAt?: number;
  mathAt?: number; lockAt?: number;
  circleAt?: number;
  stillAt?: number; promptAt?: number; endAt?: number;
  chips?: { t: number; end?: number; text: string; hot?: boolean }[];
  start?: number; width?: number; height?: number;
};

export const BillDay: React.FC<BillDayProps> = ({
  bar2At = 1.0, bar3At = 1.9,
  lineupAt = 4.8, kneeAt = 4.8, caseAt = 6.0,
  clueAt = 8.8, deltaAt = 10.1,
  clearAts = [12.7, 13.6, 14.5, 15.4],
  pushAt = 16.6, plateAt = 17.8,
  mathAt = 19.5, lockAt = 22.8,
  circleAt = 26.0,
  stillAt = 29.2, promptAt = 29.8, endAt = 32.8,
  chips = [],
  start = 0, width = 1080, height = 1920,
}) => {
  // BillDay IS the spine: it computes film time from its own Sequence-local
  // frame plus the build-injected `start` offset (negative = seconds already
  // elapsed), and PROVIDES FilmT below. Reading useFilmT() here would return
  // beat-local time — the draft replayed the opening bars card on every cut.
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - start;

  /* ---- camera: wide -> the stack -> INTO the study -> back out ------------ */
  const track = [
    { t: 0, x: 540, y: 900, z: 1.0 },
    { t: bar3At + 0.6, x: 540, y: 920, z: 1.08 },
    { t: lineupAt, x: 540, y: 960, z: 1.0, dur: 0.4 },
    { t: caseAt + 0.8, x: 540, y: 980, z: 1.04 },
    { t: deltaAt + 1.2, x: 540, y: 940, z: 1.1 },
    { t: clearAts[3] + 0.4, x: 540, y: 1000, z: 1.06 },
    { t: pushAt + 0.8, x: 540, y: studyCenterY, z: 2.3, dur: 0.8 },    // THE PUSH
    { t: circleAt - 0.6, x: 540, y: studyCenterY - 20, z: 2.34 },
    { t: circleAt + 0.7, x: 540, y: 930, z: 1.02, dur: 0.7 },          // the pull
    { t: endAt, x: 540, y: 920, z: 1.0 },
  ];

  /* ---- exposure: lamplight film — dips as rooms die, blooms on the lock --- */
  const expo: [number, number][] = [
    [0, 0.96], [bar3At, 1.02], [lineupAt - 0.2, 0.94], [lineupAt + 0.2, 1.04],
    [caseAt, 0.98], [deltaAt, 1.0],
    [clearAts[0], 0.96], [clearAts[3], 0.9],
    [pushAt + 0.8, 0.94], [lockAt, 1.07], [lockAt + 0.5, 0.98],
    [circleAt, 1.0], [circleAt + 1.2, 1.03], [stillAt, 1.0], [endAt, 0.97],
  ];

  /* which rooms are dark: cleared order kitchen, tv, geyser, washing */
  const clearedP = (i: number) =>
    i < 4 ? OUT_E(clamp01((t - clearAts[i]) / 0.5)) : 0;

  const pushP = OUT_E(clamp01((t - pushAt) / 0.8));
  const barsDock = OUT_E(clamp01((t - lineupAt + 0.3) / 0.5));   // bars card docks up-left
  const circleP = OUT_E(clamp01((t - circleAt) / 0.6));
  const barsBack = circleP;                                       // and returns at the circle

  /* ---- the bill bars card -------------------------------------------------- */
  const BARS = [
    { m: "APR", v: 8577, h: 150 },
    { m: "MAY", v: 9940, h: 205 },
    { m: "JUN", v: 11990, h: 285 },
  ];
  const barOn = [0.3, bar2At, bar3At];

  const barsCard = () => {
    // wide center-stage at the open; docked small top-left during the case;
    // back to center for the circle
    const dockedX = 60, dockedY = 150, dockedW = 400;
    const stageX = 90, stageY = 560, stageW = 900;
    const reDock = OUT_E(clamp01((t - (promptAt - 0.2)) / 0.5));
    const p = clamp01(Math.max(barsDock - barsBack, 0) + reDock);
    const x = stageX + (dockedX - stageX) * p;
    const y = stageY + (dockedY - stageY) * p;
    const w = stageW + (dockedW - stageW) * p;
    const h = w * 0.62;
    const s = w / stageW;
    return (
      <div style={{
        position: "absolute", left: x, top: y, width: w, height: h,
        background: `linear-gradient(180deg, ${rgba("#1E1915", 0.98)}, ${rgba("#131009", 0.98)})`,
        borderRadius: 26 * Math.max(s, 0.5), boxShadow: `${cardShadow}, ${cardRim}`,
        border: `1.5px solid ${rgba("#FFF6E8", 0.1)}`,
        overflow: "hidden", zIndex: 12,
      }}>
        <div style={{ position: "absolute", left: 34 * s, top: 24 * s, fontFamily: MONO,
                      fontSize: 26 * s, letterSpacing: 4, color: DAY.mute }}>
          ⚡ ELECTRICITY · LAST 3 MONTHS
        </div>
        <div style={{ position: "absolute", right: 30 * s, top: 22 * s, fontFamily: MONO,
                      fontSize: 22 * s, letterSpacing: 3, color: rgba(DAY.mute, 0.55),
                      border: `1.5px solid ${rgba(DAY.mute, 0.4)}`, borderRadius: 8,
                      padding: `${3 * s}px ${10 * s}px` }}>DEMO</div>
        {BARS.map((b, i) => {
          const on = OUT_E(clamp01((t - barOn[i]) / 0.45));
          if (on <= 0.001) return null;
          const bh = b.h * s * on;
          const bx = (120 + i * 260) * s;
          const isJun = i === 2;
          // the circle: June's TOP SEGMENT (the jump) lights coral
          const jump = isJun ? circleP : 0;
          const jumpH = (285 - 150) * s;   // the delta = June minus the April baseline
          return (
            <div key={i} style={{ position: "absolute", left: bx, bottom: 76 * s, width: 170 * s }}>
              <div style={{
                width: "100%", height: bh, borderRadius: 12 * s,
                background: isJun
                  ? `linear-gradient(180deg, ${rgba(DAY.coral, 0.95)}, ${rgba("#C24E2E", 0.95)})`
                  : `linear-gradient(180deg, ${rgba("#8C7A64", 0.9)}, ${rgba("#5C4F41", 0.9)})`,
                boxShadow: `0 4px 8px ${rgba("#000", 0.5)}, inset 0 2px 0 ${rgba("#FFF", 0.25)}`,
                position: "relative", overflow: "hidden",
              }}>
                {jump > 0 ? (
                  <div style={{
                    position: "absolute", left: 0, top: 0, width: "100%", height: jumpH,
                    background: rgba("#FFD9A0", 0.85 * jump),
                    boxShadow: `0 0 ${30 * jump}px ${rgba(DAY.amber, 0.9)}`,
                  }} />
                ) : null}
              </div>
              <div style={{ marginTop: 10 * s, textAlign: "center", fontFamily: MONO,
                            fontSize: 24 * s, color: DAY.mute }}>{b.m}</div>
              <div style={{ textAlign: "center", fontFamily: MONO, fontSize: 30 * s,
                            color: isJun ? DAY.coral : DAY.ink,
                            fontVariantNumeric: "tabular-nums" as const }}>
                ₹{b.v.toLocaleString("en-IN")}
              </div>
            </div>
          );
        })}
        {/* the clue overlay: SUMMER starts where the jump starts */}
        {t >= clueAt ? (() => {
          const on = OUT_E(clamp01((t - clueAt) / 0.5));
          return (
            <>
              <div style={{
                position: "absolute", left: (120 + 260) * s, bottom: 60 * s,
                width: 430 * s, height: 340 * s * on,
                borderLeft: `3px dashed ${rgba(DAY.amber, 0.75)}`,
                pointerEvents: "none",
              }} />
              <div style={{
                position: "absolute", left: (140 + 260) * s, top: 70 * s, fontFamily: MONO,
                fontSize: 25 * s, letterSpacing: 3, color: DAY.amber, opacity: on,
              }}>☀ SUMMER STARTS</div>
            </>
          );
        })() : null}
        {/* THE JUMP, measured — a dimension bracket on the June bar with a
            solid tag on a leader line. The first version was a translucent
            amber box that BLENDED with the amber bar (VJ's catch); annotation
            grammar never sits on what it annotates. */}
        {t >= deltaAt ? (() => {
          const on = OUT_E(clamp01((t - deltaAt) / 0.45));
          const draw = OUT_E(clamp01((t - deltaAt) / 0.6));
          const junTopY = (482 - 285) * s;         // June bar's top
          const segH = (285 - 150) * s;            // the delta segment
          const bx = 828 * s;                      // bracket x, clear of the bar
          return (
            <>
              <svg width={900 * s} height={558 * s}
                   style={{ position: "absolute", left: 0, top: 0, pointerEvents: "none" }}>
                {/* the bracket: ticks + spine, drawn on */}
                <g stroke="#FFD9A0" strokeWidth={3 * s} opacity={on}>
                  <line x1={bx} y1={junTopY} x2={bx} y2={junTopY + segH * draw} />
                  <line x1={bx - 12 * s} y1={junTopY} x2={bx + 12 * s} y2={junTopY} />
                  {draw > 0.95 ? (
                    <line x1={bx - 12 * s} y1={junTopY + segH} x2={bx + 12 * s} y2={junTopY + segH} />
                  ) : null}
                </g>
                {/* the leader: tag -> bracket top */}
                <polyline
                  points={`${628 * s},${218 * s} ${740 * s},${218 * s} ${bx - 14 * s},${junTopY + 6 * s}`}
                  fill="none" stroke={rgba("#FFD9A0", 0.75)} strokeWidth={2.5 * s}
                  strokeDasharray={`${6 * s} ${5 * s}`} opacity={draw} />
              </svg>
              <div style={{
                position: "absolute", left: 408 * s, top: 188 * s,
                opacity: Math.min(1, on * 1.4),
                transform: `scale(${0.9 + on * 0.1 + settle(t, deltaAt + 0.45, 0.4) * 0.05})`,
                background: rgba("#211A12", 0.94), border: `2px solid ${rgba("#FFD9A0", 0.7)}`,
                borderRadius: 12 * s, padding: `${8 * s}px ${18 * s}px`,
                fontFamily: MONO, fontSize: 36 * s, color: "#FFD9A0",
                boxShadow: cardShadow,
                fontVariantNumeric: "tabular-nums" as const,
              }}>JUMP ≈ ₹3,400</div>
            </>
          );
        })() : null}
        {/* the circle closes INSIDE the card: the multiplication sits beside
            the JUMP tag it reproduces — dark ground, no screen-space band to
            fight the docked rooms for. */}
        {circleP > 0.001 ? (
          <div style={{
            position: "absolute", left: 60 * s, top: 170 * s, width: 330 * s,
            opacity: Math.min(1, circleP * 1.4),
            transform: `translateY(${(1 - circleP) * 18 * s}px)`,
            fontFamily: MONO, fontSize: 27 * s, lineHeight: 1.45,
            color: rgba("#F6EEDF", 0.85),
            fontVariantNumeric: "tabular-nums" as const,
          }}>
            ₹18 × 6h × 30 din<br />
            ≈ <span style={{ color: "#FFD9A0" }}>₹3,240</span> →
          </div>
        ) : null}
      </div>
    );
  };

  /* ---- the room line-up ---------------------------------------------------- */
  const roomCard = (r: typeof ROOMS[number], i: number) => {
    const slam = OUT_E(clamp01((t - (lineupAt + i * 0.12)) / 0.35));
    if (slam <= 0.001) return null;
    const dark = clearedP(ROOMS.findIndex((x) => x.id === r.id) === STUDY ? 4
      : ["kitchen", "tv", "geyser", "washing"].indexOf(r.id));
    const y = STACK_TOP + i * (CARD_H + CARD_GAP);
    const isStudy = i === STUDY;
    const wob = idle(t, i * 3, 1);
    return (
      <div key={r.id} style={{
        position: "absolute", left: 540 - CARD_W / 2 + (1 - slam) * (i % 2 ? 700 : -700),
        top: y + wob.y * 0.5,
        width: CARD_W, height: CARD_H,
        borderRadius: 22, overflow: "hidden",
        boxShadow: `${cardShadow}, ${cardRim}`,
        border: `1.5px solid ${rgba("#FFF6E8", isStudy && t >= clearAts[3] ? 0.35 : 0.1)}`,
        opacity: slam, zIndex: 8,
        transform: `scale(${(0.96 + slam * 0.04 + settle(t, lineupAt + i * 0.12 + 0.35, 0.4) * 0.03).toFixed(3)})`,
      }}>
        <Img src={staticFile(r.plate)} style={{
          width: "100%", height: "100%", objectFit: "cover",
          filter: dark > 0 ? `grayscale(${dark * 0.95}) brightness(${1 - dark * 0.32}) contrast(${1 - dark * 0.15})` : undefined,
        }} />
        <div style={{
          position: "absolute", left: 18, bottom: 12, fontFamily: MONO,
          fontSize: 23, letterSpacing: 3,
          color: dark > 0.5 ? rgba("#FFF6E8", 0.45) : "#F6EEDF",
          textShadow: `0 2px 8px ${rgba("#000", 0.9)}`,
        }}>{r.label}</div>
        {/* CLEARED stamp — it stays on the dead room */}
        {dark > 0.3 ? (
          <div style={{
            position: "absolute", right: 26, top: CARD_H / 2 - 30,
            fontFamily: DISP, fontWeight: 800, fontSize: 44, letterSpacing: 2,
            color: DAY.cleared, border: `3.5px solid ${DAY.cleared}`,
            borderRadius: 12, padding: "2px 18px",
            transform: `rotate(-9deg) scale(${0.8 + Math.min(dark, 1) * 0.2})`,
            opacity: Math.min(1, dark * 1.6),
            boxShadow: `0 4px 14px ${rgba("#000", 0.6)}`,
          }}>BARI ✓</div>
        ) : null}
      </div>
    );
  };

  /* verdict bubbles: whoosh FROM the dock to each room as it clears */
  const verdicts = ["kitchen", "tv", "geyser", "washing"].map((id, i) => {
    const at = clearAts[i];
    const p = clamp01((t - (at - 0.35)) / 0.35);
    if (p <= 0 || p >= 1) return null;
    const roomI = ROOMS.findIndex((r) => r.id === id);
    const ty = STACK_TOP + roomI * (CARD_H + CARD_GAP) + CARD_H / 2;
    const e = IN_E(p);
    return (
      <div key={id} style={{
        position: "absolute",
        left: 830 + (540 - 830) * e, top: 250 + (ty - 250) * e,
        zIndex: 20, opacity: 1 - p * 0.3,
        transform: `scale(${1 - e * 0.3})`,
        background: rgba(DAY.green, 0.16), border: `2px solid ${DAY.green}`,
        borderRadius: 16, padding: "8px 18px",
        fontFamily: MONO, fontSize: 26, color: DAY.green,
        boxShadow: `0 0 24px ${rgba(DAY.green, 0.35)}`,
      }}>✓</div>
    );
  });

  /* ---- the chat dock: the detective ---------------------------------------- */
  const dockOn = OUT_E(clamp01((t - caseAt) / 0.5));
  const dock = dockOn > 0.001 ? (
    <div style={{
      position: "absolute", right: 44, top: 156, width: 360, zIndex: 22,
      opacity: Math.min(1, dockOn * 1.4),
      transform: `translateY(${(1 - dockOn) * -40}px)`,
      background: `linear-gradient(180deg, ${rgba("#101614", 0.98)}, ${rgba("#0B100E", 0.98)})`,
      border: `1.5px solid ${rgba(DAY.green, 0.4)}`,
      borderRadius: 20, boxShadow: `${cardShadow}, 0 0 34px ${rgba(DAY.green, 0.14)}`,
      padding: "14px 18px",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontFamily: MONO, fontSize: 20, letterSpacing: 3, color: DAY.green }}>
          ● FREE AI · DETECTIVE
        </span>
      </div>
      <div style={{ marginTop: 10, fontFamily: MONO, fontSize: 21, lineHeight: 1.55,
                    color: rgba(DAY.ink, 0.75) }}>
        {t < clueAt ? "reading 3 bills…" :
         t < clearAts[0] ? "> summer delta found" :
         t < pushAt ? "> eliminating suspects…" :
         t < lockAt ? "> one suspect left" : "> case closed"}
        <span style={{ opacity: Math.floor(t * 3) % 2 ? 1 : 0.2 }}>▍</span>
      </div>
      {/* the ₹0 meter — lit at the case handoff, never moves, stamped at the end */}
      <div style={{
        marginTop: 12, display: "flex", justifyContent: "space-between", alignItems: "center",
        borderTop: `1px solid ${rgba(DAY.green, 0.25)}`, paddingTop: 10,
      }}>
        <span style={{ fontFamily: MONO, fontSize: 19, letterSpacing: 3, color: DAY.mute }}>COST</span>
        <span style={{
          fontFamily: MONO, fontSize: 34, fontVariantNumeric: "tabular-nums" as const,
          color: t >= stillAt ? DAY.green : DAY.amber,
          transform: `scale(${1 + settle(t, stillAt, 0.5) * 0.18})`, display: "inline-block",
          textShadow: t >= stillAt ? `0 0 18px ${rgba(DAY.green, 0.6)}` : undefined,
        }}>{t >= stillAt ? "STILL ₹0" : "₹0"}</span>
      </div>
    </div>
  ) : null;

  /* the coral bill: the carry — flies into the dock at the case handoff */
  const billFly = clamp01((t - (caseAt - 0.5)) / 0.5);
  const billCarry = t >= caseAt - 0.6 && t < caseAt + 0.2 ? (
    <div style={{
      position: "absolute",
      left: 500 + (860 - 500) * OUT_E(billFly),
      top: 700 + (200 - 700) * OUT_E(billFly),
      zIndex: 24, opacity: (1 - clamp01((t - caseAt) / 0.25)) * clamp01((t - (caseAt - 0.6)) / 0.2),
      transform: `rotate(${billFly * 40}deg) scale(${1 - billFly * 0.5})`,
      width: 120, height: 150, borderRadius: 10,
      background: `linear-gradient(160deg, ${DAY.coral}, #C24E2E)`,
      boxShadow: cardShadow,
    }}>
      {[0, 1, 2].map((k) => (
        <div key={k} style={{ margin: "14px 12px 0", height: 7, borderRadius: 3,
                              width: 70 - k * 14, background: rgba("#FFF", 0.5) }} />
      ))}
    </div>
  ) : null;

  /* ---- the study close-up dressing (visible after the push) ---------------- */
  const plateOn = OUT_E(clamp01((t - plateAt) / 0.5));
  const bulbSwing = Math.sin(t * 2.2) * 9 * pushP;

  const dressFade = 1 - clamp01((t - (circleAt - 0.2)) / 0.4);
  const studyDressing = pushP > 0.5 && dressFade > 0.01 ? (
    <>
      {/* the sun shaft — daytime's spotlight, drifting slowly */}
      <div style={{
        position: "absolute", left: 540 - 520 + bulbSwing * 6, top: studyCenterY - 420,
        width: 1040, height: 760, zIndex: 14, pointerEvents: "none",
        opacity: (pushP - 0.5) * 2 * dressFade * 0.8,
        background: `linear-gradient(115deg, ${rgba("#FFF3D0", 0)} 34%, ${rgba("#FFF3D0", 0.30)} 46%, ${rgba("#FFF3D0", 0.06)} 58%, ${rgba("#FFF3D0", 0)} 70%)`,
        mixBlendMode: "screen",
      }} />
      {/* nameplate booking card */}
      {plateOn > 0.001 ? (
        <div style={{
          position: "absolute", left: 540 - 250, top: studyCenterY + 120, width: 500, zIndex: 16,
          opacity: Math.min(1, plateOn * 1.4) * dressFade,
          transform: `rotate(-2deg) translateY(${(1 - plateOn) * 30}px) scale(${0.9 + plateOn * 0.1})`,
          background: "#E8DCC2", borderRadius: 12, padding: "14px 22px",
          boxShadow: cardShadow, border: `2px solid ${rgba("#4A3B28", 0.4)}`,
        }}>
          <div style={{ fontFamily: MONO, fontSize: 26, letterSpacing: 2, color: "#3A2E1E",
                        textAlign: "center", whiteSpace: "nowrap" as const }}>1.5 TON · NON-INVERTER · 2016</div>
        </div>
      ) : null}
    </>
  ) : null;


  /* the give: the detective console rises */
  const promptOn = OUT_E(clamp01((t - promptAt) / 0.6));
  const consoleCard = promptOn > 0.001 ? (
    <div style={{
      position: "absolute", left: 90, top: 640, width: 900, zIndex: 26,
      opacity: Math.min(1, promptOn * 1.4),
      transform: `translateY(${(1 - promptOn) * 60}px)`,
      background: `linear-gradient(180deg, ${rgba("#0F1512", 0.98)}, ${rgba("#0A0F0C", 0.98)})`,
      border: `2px solid ${rgba(DAY.green, 0.5)}`,
      borderRadius: 24, boxShadow: `${cardShadow}, 0 0 44px ${rgba(DAY.green, 0.16)}`,
      padding: "26px 32px",
    }}>
      <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
        {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => (
          <div key={c} style={{ width: 14, height: 14, borderRadius: 7, background: c }} />
        ))}
        <span style={{ marginLeft: "auto", fontFamily: MONO, fontSize: 20, color: DAY.mute }}>
          model: <span style={{ color: DAY.green }}>fable-5 ✓</span>
        </span>
      </div>
      <div style={{ fontFamily: MONO, fontSize: 29, lineHeight: 1.6, color: DAY.green }}>
        {(() => {
          const txt = "> Mere last 3 bills: [Apr __, May __, Jun __]. Detective bano — seasonal jump nikaalo, culprit batao, maths ke saath. Free tareeke se fix bhi.";
          const chars = Math.max(0, Math.floor((t - promptAt - 0.2) * 44));
          return <>{txt.slice(0, chars)}<span style={{ opacity: Math.floor(t * 3) % 2 ? 1 : 0.15 }}>▍</span></>;
        })()}
      </div>
      <div style={{ marginTop: 16, textAlign: "center", fontFamily: MONO, fontSize: 22,
                    letterSpacing: 4, color: rgba(DAY.ink, 0.55),
                    opacity: clamp01((t - promptAt - 1.6) / 0.4) }}>PINNED · COPY KARO</div>
    </div>
  ) : null;


  /* ---- THE DIVISION, then the lock — HUD, never world space ---------------
     This is the detective's notebook, not furniture: inside WorldCamera the
     z2.3 push blew the 660px pill to ~1520px and clipped it at both edges.
     Screen space gives exact size, and the camera breath can't shake it. */
  const mathOn = OUT_E(clamp01((t - mathAt) / 0.5));
  const lockOn = t >= lockAt;
  const mathFade = 1 - clamp01((t - (circleAt - 0.2)) / 0.4);
  const mathHud = mathOn > 0.001 && mathFade > 0.01 ? (
    <div style={{
      position: "absolute", left: 60, top: 430, width: 960, zIndex: 22,
      opacity: Math.min(1, mathOn * 1.4) * mathFade, textAlign: "center",
      transform: `translateY(${(1 - mathOn) * 26}px)`,
    }}>
      <div style={{
        display: "inline-block",
        fontFamily: MONO, fontSize: 44, color: "#F6EEDF",
        background: rgba("#211A12", 0.88), borderRadius: 16,
        padding: "10px 28px", boxShadow: cardShadow,
        fontVariantNumeric: "tabular-nums" as const,
      }}>
        ₹3,400 <span style={{ color: rgba("#F6EEDF", 0.55) }}>÷ 30 din ÷ 6 ghante</span>
      </div>
      <div style={{
        marginTop: 18, display: "inline-block",
        fontFamily: DISP, fontWeight: 800, fontSize: lockOn ? 96 : 62,
        color: lockOn ? "#FFB08F" : rgba("#F6EEDF", 0.6),
        background: rgba("#211A12", lockOn ? 0.9 : 0.55),
        borderRadius: 20, padding: lockOn ? "8px 38px" : "4px 24px",
        boxShadow: cardShadow,
        transform: `scale(${1 + settle(t, lockAt, 0.5) * 0.1})`,
        textShadow: lockOn ? `0 0 34px ${rgba(DAY.coral, 0.6)}` : undefined,
      }}>
        {lockOn ? "= ₹18/HOUR" : "= ₹ __ /hour"}
      </div>
      {lockOn ? (
        <div style={{ marginTop: 14, display: "inline-block", fontFamily: MONO, fontSize: 24,
                      color: rgba("#F6EEDF", 0.8), background: rgba("#211A12", 0.78),
                      borderRadius: 10, padding: "5px 16px", boxShadow: cardShadow }}>
          cross-check: 1.9 units/hr × ₹9.5/unit ≈ ₹18 (public specs)
        </div>
      ) : null}
    </div>
  ) : null;

  return (
    <FilmT.Provider value={t}>
    <AbsoluteFill style={{ width, height }}>
      {/* the graded ground + vignette — never a flat fill */}
      <AbsoluteFill style={{
        background: `radial-gradient(120% 85% at 50% 40%, ${DAY.ground2} 0%, ${DAY.ground} 60%, #CFC3AC 100%)`,
      }} />
      <ExposureScore keys={expo}>
        <WorldCamera track={track} punches={[lineupAt, lockAt]} punchScale={1.09} breath={4}>
          {ROOMS.map(roomCard)}
          {studyDressing}
          {barsCard()}
        </WorldCamera>
      </ExposureScore>

      {verdicts}
      {dock}
      {mathHud}
      {billCarry}
      {consoleCard}

      <FlashCut at={[lineupAt, lockAt]} color="#FFE3B8" opacity={0.3} />

      {/* grain + vignette on top of everything but the chips */}
      <svg style={{ position: "absolute", inset: 0, opacity: 0.05, mixBlendMode: "overlay", pointerEvents: "none" }}>
        <filter id="day-grain"><feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" seed={6} /></filter>
        <rect width="100%" height="100%" filter="url(#day-grain)" />
      </svg>
      <div style={{
        position: "absolute", inset: 0, pointerEvents: "none",
        background: `radial-gradient(130% 95% at 50% 42%, ${rgba("#4A3B26", 0)} 55%, ${rgba("#4A3B26", 0.28)} 100%)`,
      }} />

      {/* chips — noir-styled, dead band, hot = coral pill */}
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
            position: "absolute", left: 0, right: 0, top: 1445, zIndex: 40,
            display: "flex", justifyContent: "center",
            transform: `translateY(-50%) scale(${(0.94 + 0.06 * pop) * (1 + settle(t, cur.t, 0.4) * 0.05)})`,
            opacity: pop,
          }}>
            <div style={{
              fontFamily: DISP, fontWeight: 800, fontSize: 62,
              textTransform: "uppercase" as const, whiteSpace: "nowrap" as const,
              color: cur.hot ? "#FFF6EC" : DAY.paper,
              background: cur.hot ? DAY.coral : rgba("#211A12", 0.92),
              padding: "8px 30px", borderRadius: 18,
              boxShadow: cardShadow,
              border: cur.hot ? undefined : `1.5px solid ${rgba("#FFF6E8", 0.18)}`,
            }}>{cur.text}</div>
          </div>
        );
      })()}
    </AbsoluteFill>
    </FilmT.Provider>
  );
};

/* ---- canonical demo (planned clock) -------------------------------------- */
export const billDayDemo: BillDayProps = {
  bar2At: 1.0, bar3At: 1.9,
  lineupAt: 4.8, kneeAt: 4.8, caseAt: 6.0,
  clueAt: 8.8, deltaAt: 10.1,
  clearAts: [12.7, 13.6, 14.5, 15.4],
  pushAt: 16.6, plateAt: 17.8,
  mathAt: 19.5, lockAt: 22.8,
  circleAt: 26.0,
  stillAt: 29.2, promptAt: 29.8, endAt: 32.8,
  chips: [
    { t: 0.3, end: 1.8, text: "BILL BADHTA?", hot: true },
    { t: 2.0, end: 3.4, text: "HAR MAHINA" },
    { t: 4.9, end: 6.4, text: "5 SUSPECTS", hot: true },
    { t: 6.6, end: 8.2, text: "FREE DETECTIVE" },
    { t: 8.9, end: 10.0, text: "THE CLUE" },
    { t: 10.2, end: 12.0, text: "SUMMER JUMP", hot: true },
    { t: 12.8, end: 14.4, text: "BARI × 2" },
    { t: 14.6, end: 16.4, text: "BARI × 4" },
    { t: 16.8, end: 18.6, text: "EK BACHA", hot: true },
    { t: 19.6, end: 21.6, text: "PURANA AC" },
    { t: 22.9, end: 24.8, text: "₹18 / GHANTA", hot: true },
    { t: 26.1, end: 28.2, text: "WAHI JUMP" },
    { t: 29.3, end: 31.0, text: "STILL ₹0", hot: true },
    { t: 31.2, end: 32.6, text: "PROMPT PINNED" },
  ],
};
