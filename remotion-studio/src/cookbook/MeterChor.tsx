import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { rgba } from "./kit";
import { clamp01, OUT_E, IN_E, settle } from "./motion";
import { FilmT } from "./filmclock";
import { SplitFlapMeter } from "./SplitFlapMeter";
import { ExposureScore, FlashCut } from "./craft";

/* =============================================================================
   METER-CHOR — "AC Ka Taxi-Meter". Ep2 rebuild after the audition diagnosis.

   Spine, per the judged treatment:
   0.0  ECU: a split-flap taxi meter bolted on an old window AC, total rolling,
        RATE window BLURRED — the secret the film pays at 75%.
   1.6  yank-back: the daylight cutaway house, five meters ticking in
        polyrhythm — AC's fastest. Suspicion = tempo.
   4.0  the bill becomes a meter: odometer rolls APR->MAY->JUN, final digit
        SLAMS at 6.00s absolute, and the +Rs3,400 chunk SHEARS off (the film's
        loudest event, inside the knee). The chunk then pulses as an animating
        shelf — never a freeze.
   8.0  three bills whoosh into the Claude dock; the AI's own meter refuses to
        tick (Rs0.00, dead needle).
   11.5 the meter-walk: fridge/TV/geyser/machine cleared by their usage
        patterns, cadence accelerating; flags flip UP, housings grey.
   16.3 SIRF AC: the film's only push-in. Amber, hostile, nameplate.
   18.0 the division as machinery: the chunk slides into a slot, sliced into
        30 slivers, regrouped over a 6-notch night arc into 6 chips.
   24.0 RATE LOCK (75%): the blurred window slams Rs18/HR at ~40% width.
        Chai anchor: one cutting chai every hour.
   26.5 WAHI JUMP: slivers fly back, the chunk snaps into the bill.
   28.5 the give: prompt COMPLETE AND STATIC >=2.5s, PINNED tick, loop-out to
        the meter — last frame adjacent to first.

   All timing props are film-clock anchors resolved by the build from measured
   VO (@beatN+x). This component computes its own film time from `start` (it IS
   the spine) and provides FilmT to children.
   ========================================================================== */

const DAY = {
  ground: "#EFE7D8", ground2: "#F7F1E4", ink: "#2B241D",
  coral: "#E8603C", amber: "#C77F14", green: "#4ADE80", paper: "#F2E8D8",
};
const MONO = "'JetBrains Mono', 'Courier New', monospace";
const DISP = "'Archivo Black', 'Arial Black', sans-serif";
const cardShadow = `0 6px 10px ${rgba("#000", 0.5)}, 0 36px 80px ${rgba("#000", 0.3)}`;

const P = (f: string) => staticFile(`assets/meterchor/${f}`);

/* appliance anchor points inside the cutaway plate (fractions of the plate) —
   calibrated against assets/meterchor/house_cutaway.png after generation. */
export type Chip = { t: number; end?: number; text: string; hot?: boolean; big?: boolean };

export type MeterChorProps = {
  start?: number; width?: number; height?: number;
  yankAt?: number;      // ECU -> house
  billAt?: number;      // bill slides in, odometer mounts
  slamAt?: number;      // JUN digit slam — 6.00s ABSOLUTE by law
  shearAt?: number;     // +3,400 chunk breaks off
  feedAt?: number;      // bills -> Claude dock
  aiMeterAt?: number;   // the dead Rs0 meter gag
  walkAts?: number[];   // fridge, tv, geyser, machine eliminations
  acAt?: number;        // SIRF AC push-in
  sliceAt?: number;     // ÷30
  regroupAt?: number;   // ÷6 + night arc
  lockAt?: number;      // RATE LOCK Rs18/HR (75%)
  circleAt?: number;    // WAHI JUMP snap-back
  giveAt?: number;      // console
  endAt?: number;
  cutawayAnchors?: { x: number; y: number }[]; // fridge,tv,geyser,machine,ac in plate fractions
  chips?: Chip[];
};

const SUS = [
  { key: "FRIDGE", room: "day/room_kitchen.png", pattern: "flat", note: "HAR MAHINA SAME" },
  { key: "TV", room: "day/room_tv.png", pattern: "flat", note: "HAR MAHINA SAME" },
  { key: "GEYSER", room: "day/room_geyser.png", pattern: "winter", note: "SIRF SARDI" },
  { key: "MACHINE", room: "day/room_washing.png", pattern: "weekly", note: "HAFTE MEIN 2" },
];
const R = (f: string) => staticFile(`assets/${f}`);

/* tiny 12-month usage sparkline — the HONEST elimination logic made visual:
   innocent = nothing changed with summer. */
const Spark: React.FC<{ pattern: string; w: number; h: number; on: number }> = ({ pattern, w, h, on }) => {
  const pts: number[] = [];
  for (let m = 0; m < 12; m++) {
    if (pattern === "flat") pts.push(0.5 + Math.sin(m * 2.1) * 0.04);
    else if (pattern === "winter") pts.push(m < 2 || m > 9 ? 0.75 : 0.18);
    else pts.push(m % 2 ? 0.55 : 0.35);
  }
  const n = Math.max(2, Math.ceil(on * 12));
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
      <line x1={0} y1={h - 2} x2={w} y2={h - 2} stroke={rgba("#F6EEDF", 0.3)} strokeWidth={1.5} />
      <polyline fill="none" stroke="#4ADE80" strokeWidth={3} strokeLinecap="round"
        points={pts.slice(0, n).map((v, i) => `${(i / 11) * (w - 4) + 2},${h - 4 - v * (h - 10)}`).join(" ")} />
    </svg>
  );
};

export const MeterChor: React.FC<MeterChorProps> = ({
  start = 0, width = 1080, height = 1920,
  yankAt = 1.6, billAt = 4.0, slamAt = 6.0, shearAt = 6.3,
  feedAt = 8.0, aiMeterAt = 9.8,
  walkAts = [11.5, 13.0, 14.3, 15.4], acAt = 16.3,
  sliceAt = 18.0, regroupAt = 21.0, lockAt = 24.0,
  circleAt = 26.5, giveAt = 28.5, endAt = 32.0,
  cutawayAnchors = [
    { x: 0.15, y: 0.50 }, { x: 0.44, y: 0.56 }, { x: 0.61, y: 0.38 },
    { x: 0.70, y: 0.55 }, { x: 0.87, y: 0.20 },
  ],
  chips = [],
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - start;

  /* ------------------------------------------------------------ camera ---- */
  /* one world: the ECU is a zoom INTO the cutaway's study corner. The yank-
     back is the same camera pulling out — so frame 0 and frame 2.5 are one
     continuous space, and the loop-out at the end returns to it. */
  const acA = cutawayAnchors[4];
  const yank = IN_E(clamp01((t - yankAt) / 0.7));
  const pushAc = OUT_E(clamp01((t - acAt) / 0.8));
  const giveP = OUT_E(clamp01((t - giveAt) / 0.6));
  const loopP = OUT_E(clamp01((t - (endAt - 1.2)) / 0.9));
  /* camera zoom on the house layer: ECU 3.4 -> wide 1.0 -> AC push 2.4 -> wide */
  let z = 3.4, cx = acA.x, cy = acA.y;
  if (t >= yankAt) { z = 3.4 - yank * 2.4; }
  if (t >= acAt) { z = 1.0 + pushAc * 1.5; }
  if (t >= sliceAt) { z = 2.5 - OUT_E(clamp01((t - sliceAt) / 0.6)) * 1.5; cx = 0.5; cy = 0.5; }
  if (t >= endAt - 1.2) { z = 1.0 + loopP * 2.4; cx = acA.x; cy = acA.y; }
  const breathe = Math.sin(t * 0.9) * 0.006 + 1;
  z *= breathe;

  /* ----------------------------------------------------- the house layer -- */
  const plateW = 1080, plateH = plateW * (640 / 1024);
  const houseY = 480;
  const camX = 540 - (cx * plateW - plateW / 2) * (z - 1) * 0.9;
  const camY = houseY - (cy * plateH - plateH / 2) * (z - 1) * 0.9;
  const houseDim = t >= sliceAt && t < circleAt ? 0.35 : t >= giveAt ? 0.25 : t >= walkAts[0] ? 0.55 : 1;

  const house = (
    <div style={{
      position: "absolute", left: 540 - plateW / 2, top: houseY,
      width: plateW, height: plateH,
      transform: `translate(${camX - 540}px, ${camY - houseY}px) scale(${z})`,
      transformOrigin: `${cx * 100}% ${cy * 100}%`,
      filter: `brightness(${houseDim})`,
      transition: "none",
    }}>
      <Img src={P("house_cutaway.png")} style={{ width: "100%", height: "100%", objectFit: "cover", borderRadius: 20 }} />
      {/* five mini meters ticking in polyrhythm once the yank lands */}
      {t >= yankAt + 0.4 && t < sliceAt ? cutawayAnchors.map((a, i) => {
        const isAc = i === 4;
        const cleared = !isAc && i < walkAts.length && t >= walkAts[i] + 0.5;
        return (
          <div key={i} style={{ position: "absolute", left: a.x * plateW - 60, top: a.y * plateH - 40,
            transform: `scale(${0.34 / Math.max(z * 0.55, 1)})`, transformOrigin: "top left",
            filter: cleared ? "grayscale(0.9) brightness(0.8)" : undefined }}>
            <SplitFlapMeter t={t} x={0} y={0}
              schedule={isAc
                ? Array.from({ length: 40 }, (_, k) => ({ at: yankAt + k * 0.35, value: 320 + k * 18 }))
                : Array.from({ length: 12 }, (_, k) => ({ at: yankAt + k * 1.3 + i * 0.3, value: 40 + k * (3 + i) }))}
              digits={3} tone={isAc ? "hot" : "calm"}
              flagUpAt={cleared ? walkAts[i] + 0.5 : undefined}
              appear={yankAt + 0.3 + i * 0.12} />
          </div>
        );
      }) : null}
    </div>
  );

  /* -------------------------------------------------------- the ECU hook -- */
  /* frame 0: the AC hero plate full-bleed with the HERO meter mounted on it.
     No build-in: total already mid-roll, flag down, rate blurred. */
  const ecuFade = 1 - clamp01((t - yankAt) / 0.5);
  const loopIn = clamp01((t - (endAt - 0.9)) / 0.6);
  const ecuOn = Math.max(ecuFade, loopIn);
  const heroSchedule = [
    ...Array.from({ length: 24 }, (_, k) => ({ at: k * 0.32 - 0.01, value: 1284 + k * 18 })),
    ...Array.from({ length: 8 }, (_, k) => ({ at: endAt - 1.0 + k * 0.3, value: 1716 + k * 18 })),
  ];
  const ecu = ecuOn > 0.01 ? (
    <AbsoluteFill style={{ opacity: ecuOn }}>
      <Img src={P("ac_hero.png")} style={{
        position: "absolute", left: -220, top: 200, width: 1520, height: 1520,
        objectFit: "cover",
        transform: `scale(${1.06 + Math.sin(t * 0.7) * 0.012}) translateY(${t * -4}px)`,
      }} />
      {/* heat shimmer off the fins */}
      <div style={{ position: "absolute", left: 0, top: 620, width: 1080, height: 320,
        background: `linear-gradient(180deg, ${rgba("#FFF3D0", 0.10)} 0%, ${rgba("#FFF3D0", 0)} 100%)`,
        transform: `skewX(${Math.sin(t * 5) * 1.4}deg)`, mixBlendMode: "screen" }} />
      <div style={{ position: "absolute", left: 90, top: 950 }}>
        <SplitFlapMeter t={t} x={0} y={0} scale={1.9}
          schedule={heroSchedule} digits={5} label="AC · FARE METER"
          rate="₹18/HR" rateLockAt={lockAt} tone="hot" />
      </div>
      {/* the accusation — giant, frame 0, upper-middle safe zone */}
      <div style={{ position: "absolute", left: 0, right: 0, top: 360, textAlign: "center" }}>
        <div style={{ fontFamily: DISP, fontSize: 108, lineHeight: 1.02, color: DAY.ink,
          textShadow: `0 3px 0 ${rgba("#FFF", 0.7)}, 0 22px 60px ${rgba("#000", 0.25)}` }}>
          AC PE<br />
          <span style={{ color: DAY.coral, textShadow: `0 3px 0 ${rgba("#FFF", 0.55)}, 0 16px 44px ${rgba("#000", 0.3)}` }}>TAXI METER</span>
        </div>
      </div>
      {/* brand inside 1s */}
      <div style={{ position: "absolute", right: 60, top: 250, display: "flex", gap: 12, alignItems: "center",
        background: rgba("#211A12", 0.9), borderRadius: 14, padding: "10px 20px", boxShadow: cardShadow }}>
        <span style={{ fontSize: 30 }}>✳</span>
        <span style={{ fontFamily: MONO, fontSize: 26, color: "#F6EEDF", letterSpacing: 2 }}>FREE AI</span>
      </div>
      <div style={{ position: "absolute", inset: 0,
        background: `radial-gradient(120% 90% at 50% 45%, transparent 55%, ${rgba("#2A1D0E", 0.5)} 100%)` }} />
    </AbsoluteFill>
  ) : null;

  /* ------------------------------------------------- the bill-meter beat -- */
  const billOn = OUT_E(clamp01((t - billAt) / 0.5)) * (1 - clamp01((t - giveAt + 0.2) / 0.4));
  /* the bill DOCKS up-left once the AI has the bills (so the walk cards and
     their stamps own the frame), and returns center for the circle snap-back */
  const dockP = OUT_E(clamp01((t - (feedAt + 0.6)) / 0.7)) * (1 - OUT_E(clamp01((t - circleAt) / 0.6)));
  const billScale = 1 - dockP * 0.58;
  const billX = 90 - dockP * 62, billY = 300 - dockP * 196;
  const monthIdx = t >= slamAt ? 2 : t >= billAt + 1.0 ? 1 : 0;
  const MONTHS = ["APR", "MAY", "JUN"];
  const billSchedule = [
    { at: billAt, value: 8577 },
    { at: billAt + 1.0, value: 9940 },
    { at: slamAt, value: 11990 },
  ];
  const shearDrop = IN_E(clamp01((t - shearAt) / 0.45));

  const bill = billOn > 0.01 ? (
    <div style={{ position: "absolute", left: billX, top: billY, width: 900, opacity: billOn,
      transformOrigin: "top left",
      transform: `translateY(${(1 - billOn) * 60}px) scale(${billScale * (1 + settle(t, slamAt, 0.5) * 0.05)})` }}>
      <Img src={P("bill_paper.png")} style={{ width: 900, height: 620, objectFit: "cover",
        borderRadius: 22, boxShadow: cardShadow }} />
      <div style={{ position: "absolute", left: 60, top: 46, fontFamily: MONO, fontSize: 30,
        letterSpacing: 4, color: "#4A3B28" }}>BIJLI BILL · {MONTHS[monthIdx]}
        <span style={{ marginLeft: 16, fontSize: 18, border: `1.5px solid ${rgba("#4A3B28", 0.5)}`,
          borderRadius: 6, padding: "2px 8px", color: rgba("#4A3B28", 0.7) }}>DEMO</span>
      </div>
      <div style={{ position: "absolute", left: 110, top: 120 }}>
        <SplitFlapMeter t={t} x={0} y={0} scale={1.55} schedule={billSchedule} digits={6} />
      </div>
      {/* shear dust */}
      {t >= shearAt && t < shearAt + 0.7 ? (
        <svg width={900} height={620} style={{ position: "absolute", left: 0, top: 0, pointerEvents: "none" }}>
          {Array.from({ length: 9 }).map((_, i) => (
            <circle key={i} cx={280 + i * 28} cy={160 + (i % 3) * 22 + shearDrop * 120}
              r={5 - (i % 3)} fill={rgba("#E8603C", 0.5 * (1 - clamp01((t - shearAt) / 0.7)))} />
          ))}
        </svg>
      ) : null}
    </div>
  ) : null;


  /* ---- THE CHUNK: the film's carry object, top-level so the bill's dock
     scale never shrinks it. Born at the shear over the bill header, drops
     with mass, parks as the pulsing shelf, feeds the slicer, snaps back. */
  const chunk = (() => {
    if (t < shearAt) return null;
    const drop = IN_E(clamp01((t - shearAt) / 0.45));
    const park = OUT_E(clamp01((t - (feedAt + 0.6)) / 0.7));
    const toSlicer = OUT_E(clamp01((t - sliceAt) / 0.6));
    const consumed = t >= sliceAt + 0.8 && t < circleAt;
    const snap = OUT_E(clamp01((t - circleAt) / 0.55));
    const pulse = 1 + Math.sin(t * 3.2) * 0.03 * (t > shearAt + 0.6 && t < sliceAt ? 1 : 0);
    let X = 600, Y = 400 + drop * 330;                     // shear + drop below the meter
    X += park * (60 - 600); Y += park * (430 - 730);       // park under the docked bill
    X += toSlicer * 380; Y += toSlicer * 120;              // feed the slicer slot
    if (snap > 0) { X = 300 + 60 * (1 - snap); Y = 420 + 140 * (1 - snap); }  // snap into the bill
    if (consumed) return null;
    return (
      <div style={{
        position: "absolute", left: X, top: Y, zIndex: 26,
        transform: `rotate(${(1 - OUT_E(clamp01((t - shearAt) / 0.55))) * -4 + drop * 5 - snap * 5}deg) scale(${(1 - toSlicer * 0.5) * pulse * (snap > 0 ? 0.9 + snap * 0.1 : 1)})`,
        background: DAY.coral, borderRadius: 16, padding: "14px 30px",
        boxShadow: cardShadow, border: `3px solid ${rgba("#FFF", 0.25)}`,
      }}>
        <div style={{ fontFamily: DISP, fontSize: 58, color: "#FFF6EC" }}>+₹3,400</div>
        {snap > 0.5 ? (
          <div style={{ fontFamily: MONO, fontSize: 22, color: rgba("#FFF6EC", 0.9), textAlign: "center" }}>= AC ≈ ₹3,240</div>
        ) : null}
      </div>
    );
  })();

  /* ------------------------------------------------------ the Claude dock -- */
  const dockOn = OUT_E(clamp01((t - feedAt) / 0.5));
  const dock = t >= feedAt ? (
    <div style={{ position: "absolute", right: 40, top: 130, width: 460, opacity: dockOn,
      transform: `translateX(${(1 - dockOn) * 80}px)`,
      background: "linear-gradient(180deg, #14231A 0%, #0D1811 100%)",
      borderRadius: 18, padding: "16px 20px", boxShadow: cardShadow,
      border: `1.5px solid ${rgba("#4ADE80", 0.3)}` }}>
      <div style={{ fontFamily: MONO, fontSize: 22, color: "#4ADE80", letterSpacing: 2 }}>✳ FREE AI · DETECTIVE</div>
      <div style={{ fontFamily: MONO, fontSize: 19, color: rgba("#D9F2E2", 0.85), marginTop: 8 }}>
        {t < aiMeterAt ? "> 3 bills mile. scan…" :
         t < walkAts[0] ? "> pattern dhoond raha…" :
         t < acAt ? `> ${SUS.filter((_, i) => t >= walkAts[i] + 0.5).length}/4 cleared` :
         t < lockAt ? "> 1 suspect bacha" : "> case closed ✓"}
      </div>
      {/* the AI's own meter: refuses to tick */}
      {t >= aiMeterAt ? (
        <div style={{ marginTop: 10, transform: "scale(0.62)", transformOrigin: "top left", height: 130 }}>
          <SplitFlapMeter t={t} x={0} y={0} schedule={[{ at: aiMeterAt, value: 0 }]}
            digits={3} label="AI · COST" dead appear={aiMeterAt} />
        </div>
      ) : null}
    </div>
  ) : null;

  /* --------------------------------------------------- the meter-walk ----- */
  const walkCards = SUS.map((s, i) => {
    const at = walkAts[i];
    if (t < at || t >= acAt + 0.3) return null;
    const on = OUT_E(clamp01((t - at) / 0.35));
    const nextAt = i + 1 < walkAts.length ? walkAts[i + 1] : acAt;
    const off = clamp01((t - (nextAt - 0.15)) / 0.3);
    const stamped = t >= at + 0.55;
    return (
      <div key={s.key} style={{
        position: "absolute", left: 70, top: 620, width: 940, opacity: on * (1 - off),
        transform: `scale(${0.92 + on * 0.08}) translateY(${(1 - on) * 50}px)`,
      }}>
        <Img src={R(s.room)} style={{ width: 940, height: 480, objectFit: "cover", borderRadius: 20,
          boxShadow: cardShadow, filter: stamped ? "grayscale(0.85) brightness(0.82)" : undefined }} />
        {/* scan bar */}
        {!stamped ? (
          <div style={{ position: "absolute", left: 0, top: clamp01((t - at) / 0.5) * 440, width: 940, height: 5,
            background: rgba("#4ADE80", 0.85), boxShadow: `0 0 24px ${rgba("#4ADE80", 0.8)}` }} />
        ) : null}
        <div style={{ position: "absolute", left: 28, top: 24, fontFamily: MONO, fontSize: 30, letterSpacing: 3,
          color: "#FFF6EC", background: rgba("#211A12", 0.85), borderRadius: 10, padding: "6px 16px" }}>{s.key}</div>
        {/* the usage sparkline — the innocence evidence */}
        <div style={{ position: "absolute", right: 28, top: 24, background: rgba("#211A12", 0.88),
          borderRadius: 12, padding: "10px 16px" }}>
          <Spark pattern={s.pattern} w={200} h={64} on={clamp01((t - at) / 0.5)} />
          <div style={{ fontFamily: MONO, fontSize: 18, color: "#4ADE80", marginTop: 4 }}>{s.note}</div>
        </div>
        {/* the SLAM stamp — full opacity, overshoot */}
        {stamped ? (
          <div style={{ position: "absolute", left: 320, top: 170,
            transform: `rotate(-9deg) scale(${1 + (1 - OUT_E(clamp01((t - at - 0.55) / 0.3))) * 1.6})`,
            opacity: Math.min(1, (t - at - 0.55) / 0.12),
            border: `6px solid #4ADE80`, borderRadius: 14, padding: "6px 24px",
            fontFamily: DISP, fontSize: 64, color: "#4ADE80",
            textShadow: `0 2px 10px ${rgba("#000", 0.6)}`, background: rgba("#0D1811", 0.35) }}>
            BARI ✓
          </div>
        ) : null}
      </div>
    );
  });

  /* ----------------------------------------------------------- SIRF AC ---- */
  const acCard = t >= acAt && t < sliceAt + 0.4 ? (() => {
    const on = OUT_E(clamp01((t - acAt) / 0.5));
    return (
      <div style={{ position: "absolute", left: 70, top: 560, width: 940, opacity: on * (1 - clamp01((t - sliceAt) / 0.4)) }}>
        <Img src={P("ac_hero.png")} style={{ width: 940, height: 620, objectFit: "cover", borderRadius: 20,
          boxShadow: cardShadow, filter: `saturate(1.1) sepia(${0.25 * on})` }} />
        <div style={{ position: "absolute", inset: 0, borderRadius: 20,
          background: `radial-gradient(90% 70% at 50% 45%, transparent 40%, ${rgba("#7A2E12", 0.45 * on)} 100%)` }} />
        <div style={{ position: "absolute", left: 28, top: 24, fontFamily: MONO, fontSize: 30, letterSpacing: 3,
          color: "#FFB08F", background: rgba("#211A12", 0.9), borderRadius: 10, padding: "6px 16px" }}>
          {t < acAt + 1.0 ? "STUDY · AC" : "CHOR?"}
        </div>
        <div style={{ position: "absolute", right: 28, bottom: 26, fontFamily: MONO, fontSize: 24,
          color: "#3A2E1E", background: "#E8DCC2", borderRadius: 10, padding: "8px 18px",
          boxShadow: cardShadow, transform: `rotate(-2deg) translateY(${(1 - OUT_E(clamp01((t - acAt - 0.8) / 0.4))) * 40}px)`,
          opacity: clamp01((t - acAt - 0.8) / 0.4), whiteSpace: "nowrap" as const }}>
          1.5 TON · NON-INVERTER · 2016
        </div>
      </div>
    );
  })() : null;

  /* ------------------------------------------ the division as machinery --- */
  const slicerOn = OUT_E(clamp01((t - sliceAt) / 0.5)) * (1 - clamp01((t - circleAt + 0.2) / 0.4));
  const sliceP = clamp01((t - sliceAt - 0.5) / 1.6);       // 30 slivers appear
  const regroupP = clamp01((t - regroupAt) / 1.4);          // -> 6 chips
  const slicer = t >= sliceAt && t < circleAt + 0.3 ? (
    <div style={{ position: "absolute", left: 60, top: 430, width: 960, opacity: slicerOn }}>
      <div style={{ background: "linear-gradient(180deg, #33291C, #1B140C)", borderRadius: 22,
        padding: "26px 30px", boxShadow: cardShadow, border: `2px solid ${rgba("#FFD9A0", 0.25)}` }}>
        <div style={{ fontFamily: MONO, fontSize: 24, letterSpacing: 3, color: rgba("#F6EEDF", 0.6) }}>
          METER KE ANDAR · HISAAB
        </div>
        {/* slot */}
        <div style={{ margin: "14px auto 8px", width: 320, height: 14, borderRadius: 7,
          background: "#0E0A05", border: `2px solid ${rgba("#FFD9A0", 0.4)}` }} />
        {/* 30 slivers */}
        <div style={{ display: "flex", gap: 5, justifyContent: "center", marginTop: 16, flexWrap: "wrap" as const, width: 900 }}>
          {Array.from({ length: 30 }).map((_, i) => {
            const born = sliceP * 30 > i;
            const merged = regroupP > 0 ? Math.floor(i / 5) : -1;
            const gone = regroupP > 0.5 && i % 5 !== 2;
            return (
              <div key={i} style={{
                width: gone ? 0 : merged >= 0 ? 24 + regroupP * 60 * (i % 5 === 2 ? 1 : 0) : 24,
                height: 44, borderRadius: 6,
                background: DAY.coral, opacity: born ? (gone ? 0 : 1) : 0,
                transform: `translateY(${born ? 0 : -30}px) scale(${born ? 1 + settle(t, sliceAt + 0.5 + i * 0.05, 0.3) * 0.15 : 0.6})`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontFamily: MONO, fontSize: i % 5 === 2 && regroupP > 0.6 ? 22 : 0, color: "#FFF6EC",
                boxShadow: `0 3px 8px ${rgba("#000", 0.4)}`,
              }}>{i % 5 === 2 && regroupP > 0.6 ? "₹" : ""}</div>
            );
          })}
        </div>
        <div style={{ display: "flex", justifyContent: "center", gap: 26, marginTop: 14,
          fontFamily: MONO, fontSize: 30, color: "#F6EEDF" }}>
          <span style={{ opacity: sliceP > 0.2 ? 1 : 0.3 }}>÷ 30 DIN</span>
          <span style={{ opacity: regroupP > 0.2 ? 1 : 0.3 }}>÷ 6 GHANTE</span>
        </div>
        {/* the night arc justifying the 6 */}
        {regroupP > 0.1 ? (
          <svg width={340} height={80} style={{ display: "block", margin: "10px auto 0" }} viewBox="0 0 340 80">
            <path d="M 20 70 A 150 150 0 0 1 320 70" fill="none" stroke={rgba("#F6EEDF", 0.3)} strokeWidth={6} />
            <path d="M 20 70 A 150 150 0 0 1 320 70" fill="none" stroke="#FFB08F" strokeWidth={7}
              strokeDasharray={`${regroupP * 118} 500`} strokeLinecap="round" />
            <text x={170} y={44} textAnchor="middle" fontFamily={MONO} fontSize={22} fill="#FFD9A0">
              raat 6 ghante
            </text>
          </svg>
        ) : null}
      </div>
    </div>
  ) : null;

  /* -------------------------------------------------------- RATE LOCK ----- */
  const lockOn = OUT_E(clamp01((t - lockAt) / 0.35)) * (1 - clamp01((t - giveAt + 0.2) / 0.4));
  const rateLock = t >= lockAt && t < giveAt ? (
    <div style={{ position: "absolute", left: 0, right: 0, top: 1080, textAlign: "center", opacity: lockOn }}>
      <div style={{
        display: "inline-block", fontFamily: DISP, fontSize: 120, color: "#FFB08F",
        background: rgba("#211A12", 0.92), borderRadius: 26, padding: "10px 46px",
        boxShadow: cardShadow, transform: `scale(${1 + settle(t, lockAt, 0.5) * 0.12})`,
        textShadow: `0 0 44px ${rgba("#E8603C", 0.65)}`,
      }}>₹18/HR</div>
      <div style={{ marginTop: 16, display: "inline-flex", gap: 14, alignItems: "center",
        background: rgba("#211A12", 0.85), borderRadius: 14, padding: "8px 20px",
        fontFamily: MONO, fontSize: 26, color: "#F6EEDF", opacity: clamp01((t - lockAt - 0.7) / 0.4) }}>
        <Img src={P("chai_glass.png")} style={{ width: 52, height: 52, objectFit: "cover", borderRadius: 8 }} />
        = har ghante ek cutting chai
      </div>
      <div style={{ marginTop: 12, fontFamily: MONO, fontSize: 20, color: rgba("#2B241D", 0.75),
        opacity: clamp01((t - lockAt - 1.2) / 0.4) }}>
        cross-check: 1.9 units/hr × ₹9.5 ≈ ₹18 (public specs)
      </div>
    </div>
  ) : null;

  /* ------------------------------------------------------------- give ----- */
  const PROMPT = "Mere last 3 bijli bills: Apr __, May __, Jun __. Detective bano — seasonal jump nikaalo, appliance-wise hisaab do, culprit batao.";
  const typed = Math.floor(clamp01((t - giveAt - 0.2) / 0.9) * PROMPT.length);
  const give = t >= giveAt ? (
    <div style={{ position: "absolute", left: 70, top: 480, width: 940, opacity: giveP * (1 - clamp01((t - (endAt - 0.9)) / 0.5)) }}>
      <div style={{ background: "linear-gradient(180deg, #14231A, #0D1811)", borderRadius: 20,
        padding: "24px 28px", boxShadow: cardShadow, border: `1.5px solid ${rgba("#4ADE80", 0.35)}` }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontFamily: MONO, fontSize: 22, color: "#4ADE80", letterSpacing: 2 }}>✳ DETECTIVE PROMPT</span>
          <span style={{ fontFamily: MONO, fontSize: 20, color: "#0D1811", background: "#4ADE80",
            borderRadius: 8, padding: "4px 12px", fontWeight: 700,
            opacity: typed >= PROMPT.length ? 1 : 0.25 }}>PINNED ✓ COPY KARO</span>
        </div>
        <div style={{ marginTop: 14, fontFamily: MONO, fontSize: 27, lineHeight: 1.55,
          color: "#D9F2E2", minHeight: 200 }}>
          {"> "}{PROMPT.slice(0, typed)}
          {typed < PROMPT.length ? <span style={{ opacity: Math.sin(t * 9) > 0 ? 1 : 0 }}>▌</span> : null}
        </div>
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
        <div style={{ position: "absolute", left: 0, right: 0, top: 1300, textAlign: "center", zIndex: 40,
          opacity: pop, transform: `scale(${0.92 + 0.08 * pop + settle(t, cur.t, 0.4) * 0.05})` }}>
          <span style={{ fontFamily: DISP, fontSize: 84, color: cur.hot ? "#FFF6EC" : DAY.ink,
            background: cur.hot ? DAY.coral : "transparent",
            padding: cur.hot ? "6px 34px" : 0, borderRadius: 20,
            textShadow: cur.hot ? undefined : `0 3px 0 ${rgba("#FFF", 0.6)}`,
            boxShadow: cur.hot ? cardShadow : undefined }}>{cur.text}</span>
        </div>
      );
    }
    return (
      <div style={{ position: "absolute", left: 0, right: 0, top: 1445, display: "flex",
        justifyContent: "center", zIndex: 40, opacity: pop,
        transform: `translateY(-50%) scale(${(0.94 + 0.06 * pop) * (1 + settle(t, cur.t, 0.4) * 0.05)})` }}>
        <div style={{ fontFamily: DISP, fontWeight: 800, fontSize: 58, textTransform: "uppercase" as const,
          whiteSpace: "nowrap" as const, color: cur.hot ? "#FFF6EC" : DAY.paper,
          background: cur.hot ? DAY.coral : rgba("#211A12", 0.92),
          padding: "8px 28px", borderRadius: 18, boxShadow: cardShadow,
          border: cur.hot ? undefined : `1.5px solid ${rgba("#FFF6E8", 0.18)}` }}>{cur.text}</div>
      </div>
    );
  })();

  /* ---------------------------------------------------------- exposure ---- */
  const expo: [number, number][] = [
    [0, 1.0], [yankAt, 1.03], [slamAt, 1.07], [slamAt + 0.4, 0.97],
    [acAt, 0.92], [lockAt, 1.08], [lockAt + 0.5, 0.99], [endAt, 1.0],
  ];

  return (
    <FilmT.Provider value={t}>
      <AbsoluteFill style={{ width, height }}>
        <AbsoluteFill style={{
          background: `radial-gradient(120% 85% at 50% 40%, ${DAY.ground2} 0%, ${DAY.ground} 60%, #CFC3AC 100%)`,
        }} />
        <ExposureScore keys={expo}>
          {house}
          {walkCards}
          {acCard}
          {bill}
          {chunk}
          {slicer}
          {ecu}
        </ExposureScore>
        {dock}
        {rateLock}
        {give}
        <FlashCut at={[slamAt, lockAt]} color="#FFE3B8" opacity={0.32} />
        {/* grain + vignette */}
        <svg style={{ position: "absolute", inset: 0, opacity: 0.05, mixBlendMode: "overlay", pointerEvents: "none" }}>
          <filter id="mc-grain"><feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" seed={7} /></filter>
          <rect width="100%" height="100%" filter="url(#mc-grain)" />
        </svg>
        <div style={{ position: "absolute", inset: 0, pointerEvents: "none",
          background: `radial-gradient(130% 95% at 50% 42%, transparent 55%, ${rgba("#4A3B26", 0.28)} 100%)` }} />
        {chipEl}
      </AbsoluteFill>
    </FilmT.Provider>
  );
};

/* ---- canonical demo (planned clock) -------------------------------------- */
export const meterChorDemo: MeterChorProps = {
  chips: [
    { t: 0.3, end: 1.6, text: "KAUN KHA RAHA?", hot: true },
    { t: 1.7, end: 4.0, text: "HAR APPLIANCE PE METER" },
    { t: 4.1, end: 6.0, text: "APR → MAY → JUN" },
    { t: 6.1, end: 8.0, text: "+₹3,400 KISNE?", hot: true, big: true },
    { t: 8.1, end: 9.8, text: "3 BILLS → AI" },
    { t: 9.9, end: 11.5, text: "AI KA METER: ₹0", hot: true },
    { t: 11.6, end: 13.0, text: "FRIDGE ✗" },
    { t: 13.1, end: 14.3, text: "TV ✗" },
    { t: 14.4, end: 15.4, text: "GEYSER ✗" },
    { t: 15.5, end: 16.3, text: "MACHINE ✗" },
    { t: 16.4, end: 18.0, text: "SIRF AC", hot: true },
    { t: 18.1, end: 21.0, text: "÷ 30 DIN" },
    { t: 21.1, end: 24.0, text: "÷ 6 GHANTE" },
    { t: 24.1, end: 25.9, text: "₹18/GHANTA", hot: true },
    { t: 26.0, end: 26.5, text: "1 CHAI/GHANTA" },
    { t: 26.6, end: 28.5, text: "WAHI JUMP" },
    { t: 28.6, end: 30.5, text: "PROMPT PINNED", hot: true },
    { t: 30.6, end: 32.0, text: "CHOR PAKDO" },
  ],
};
