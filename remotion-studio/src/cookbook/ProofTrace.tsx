import React from "react";
import { AbsoluteFill, Easing, spring, useCurrentFrame, useVideoConfig } from "remotion";
import {
  BRAND, SANS, MONO, DISPLAY, rgba, clamp, Fonts, AuroraBed, SAFE, glassChrome, GlassInner,
} from "./kit";

/* =============================================================================
   ProofTrace — one trace that never stops moving and never leaves its band.

   THE FILM. A person cannot remember their own last five years. An instrument is
   searching that span and finding nothing on the record. A prompt starts asking
   questions; the answers land as entries; and on one un-eased frame the whole
   line rises into the shape it always had. The work was there. It was never
   written down.

   WHY THIS REPLACED CareerArc. Three complaints and two measurements:

   - THE LINE MOVED HOUSE. CareerArc's plot slid downward out of its own band and
     flattened at y~1000 by t=1.25, then never returned. Worse, a `breathe` term
     drifted the entire graphic +-3.2px on a sine independent of any content. The
     band here is y640..1120 and it is CONSTANT: there is no transform on the
     group at all. Every motion lives inside y(x, t).
   - 747px OF NOTHING. A frame audit of the previous cut measured the top region
     99.0% empty from 1.1s to 3.58s -- 2.5 seconds of held frame sitting on the
     measured 4-7s knee, where 64% of this channel's total retention loss occurs
     and the worst single second (5->6s, -8.1pp median) lives. The ledger strip
     and the scan hairline fill it, and they are not decoration: the strip is the
     CAUSE of the trace's height.
   - TWO WORDS SAT STILL FOR 6.87s. "FLAT." asserted, in the largest type in the
     film, muted, the exact falsehood the film exists to refute -- and the
     correction did not arrive until 8.70s, by which point a quarter of the
     audience has left. The verdict line replaces it: five short claims, longest
     hold 2.82s, never the only moving thing on screen.

   THE HONESTY BAR. There is no axis, no counter, no part-of-whole bar and no
   figure anywhere in this component. Time is the only thing the horizontal
   claims, and time is the one axis that is not a claim about the viewer. The
   vertical is the DENSITY OF YOUR RECORD, and it is declared in mechanism -- a
   ledger rule fills, a thread drops, the line rises there -- never in a label.
   The trend deliberately DIPS at span 3 and runs near-flat through span 4;
   growth and compensation charts never do, and that dip is a permanent on-screen
   disproof of the measurement reading. This is emphatically NOT a salary graph:
   a rising money line with no axis, at 2x on mute, IS a promise of a raise, and
   the film's closing beat exists to refuse exactly that promise.

   Authored 1080x1920. SAFE.headerFloor (132) owns the top; the verdict line ends
   at y1312, clearing the caption band at 1380 by 68px.
   ========================================================================== */

/* ---- the band. These are literals and they never interpolate. ------------ */
const PLOT_L = 84;
const PLOT_R = 996;
const TOP_Y = 640;      // ceiling: topmost ink ever is 665
const FLOOR_Y = 1120;   // floor: the fill dies to alpha 0 well before reaching it
const REST_Y = 1016;    // the unrecorded resting height
const SPAN = 340;       // trend travel, so the right-hand peak is y676
const STEP = 6;         // sample pitch -> 153 samples

/* the four ledger columns ARE CaseBullets' nodeX(i) at n=4, and the lifts the
   trend lands on ARE the lifts CaseBullets draws. Not approximations — these
   exact values are what make the hand-off at 11.30 invisible. */
const CB_X = [214.286, 431.429, 648.571, 865.714];
const CB_Y = [429.2, 391.8, 354.4, 313.6];        // 470 - 170*lift, lifts .24/.46/.68/.92

const OUT_E = Easing.bezier(0.16, 1, 0.3, 1);
const smooth = (a: number) => a * a * (3 - 2 * a);

/* THE TREND — non-monotone on purpose. The dip at TX[2] (-0.12) and the
   near-flat stretch TX[2]->TX[3] (+0.02) are not decoration and are not
   negotiable: they are what stops this reading as a growth chart. */
const TX = [84, 266.4, 448.8, 631.2, 813.6, 996];
const TL = [0.10, 0.36, 0.24, 0.26, 0.64, 1.0];
const trendLift = (x: number) => {
  let i = 0;
  while (i < 4 && x > TX[i + 1]) i++;
  const u = clamp((x - TX[i]) / (TX[i + 1] - TX[i]));
  return TL[i] + (TL[i + 1] - TL[i]) * smooth(u);
};
const trendY = (x: number) => REST_Y - SPAN * trendLift(x);

/* deterministic noise — never Math.random, which would differ per frame in a
   distributed render and strobe. */
const hash = (i: number) => {
  const s = Math.sin(i * 127.1 + 311.7) * 43758.5453;
  return s - Math.floor(s);
};
const vnoise = (u: number) => {
  const i = Math.floor(u), f = u - i, s = smooth(f);
  return hash(i) * (1 - s) + hash(i + 1) * s;
};

/* THE SIGNAL. Coefficients sum to exactly 1.00 so |wave| <= 1 and `amp` is in
   pixels, verbatim — which is what makes the excursion budget below provable.
   Three incommensurate temporal terms plus value noise never repeat. */
const wave = (x: number, t: number) =>
  0.34 * Math.sin(x * 0.0091 + t * 1.31) +
  0.24 * Math.sin(x * 0.0223 - t * 2.07) +
  0.22 * Math.sin(x * 0.0041 + t * 0.77) +
  0.20 * (vnoise(x * 0.017 + t * 1.9) - 0.5) * 2;

const AMP_LOOSE = 34;
const AMP_LOCKED = 11;

/* excursion budget, verified:
     lowest  = 1016 + 34(amp) + 42(sag) + 14.4(flinch peak) = 1106.4 < 1120  OK
     highest = 676 - 11 = 665 > 640                                          OK
   (dents finish at 5.09 and sag ramps from 5.40, so they never sum) */

export type ProofAnswer = {
  /** short label for the ledger entry this answer fills. Never rendered large. */
  label?: string;
  /** beat-local second the answer lands. Accepts "@beatN+x" via build_ep_v2. */
  at: number;
};

export type ProofVerdict = {
  at: number;
  /** <= 15 characters. Anton caps advance ~0.50em, so 16+ overflows the 912px
   *  field even at the 0.82 scale clamp. Shorten the string; never raise the size. */
  text: string;
};

export type ProofTraceProps = {
  runLabel?: string;
  searchLabel?: string;
  spanLabelL?: string;
  spanLabelR?: string;
  reviewLabel?: string;
  /** 0..1 along the span where "the form's window" begins. The picture dims left
   *  of this on `panicAt` and re-widens when the head returns. */
  reviewFrom?: number;
  /** the head snaps back and the picture narrows to the review window. */
  panicAt?: number;
  /** the search is struck through and the head begins its return sweep. */
  stopAt?: number;
  /** the prompt card lands; the trace physically flinches from the impact. */
  pasteAt?: number;
  pasteText?: string[];
  /** four answers. Each fills a ledger rule, drops a thread, steps the frontier. */
  answers?: ProofAnswer[];
  /** THE FRAME. trendLock 0->1 un-eased, dash->solid, the ledger densifies. */
  revealAt?: number;
  /** the scanner reaches NOW and merges with it. */
  mergeAt?: number;
  /** geometry lerp onto CaseBullets' own arc. */
  demoteAt?: number;
  demoteDur?: number;
  verdicts?: ProofVerdict[];
  accent?: string;
  ink?: string;
  transparent?: boolean;
  start?: number;
  width?: number;
  height?: number;
};

export const ProofTrace: React.FC<ProofTraceProps> = ({
  runLabel = "YOUR LAST 5 YEARS",
  searchLabel = "SEARCHING YOUR LAST 5 YEARS",
  spanLabelL = "5 YEARS AGO",
  spanLabelR = "NOW",
  reviewLabel = "THIS REVIEW",
  reviewFrom = 0.6,
  panicAt = 3.58,
  stopAt = 6.31,
  pasteAt = 6.52,
  pasteText = [],
  answers = [],
  revealAt = 8.86,
  mergeAt = 11.3,
  demoteAt = 11.3,
  demoteDur = 0.5,
  verdicts = [],
  accent = BRAND.mag,
  ink = BRAND.ink,
  transparent,
  start = 0,
  width = 1080,
  height = 1920,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - start;
  const ONE = Math.max(1, Math.round(fps / 30));   // "one frame" survives a 60fps render
  const A = answers.slice(0, 4);
  const REVIEW_X = PLOT_L + (PLOT_R - PLOT_L) * clamp(reviewFrom);

  /* ---- the scanner's pass table ------------------------------------------
     An explicit table, never frac(). frac() wraps the ghost trail backwards
     across the whole frame on every reset — eight teleport events in a film
     whose entire premise is one continuous object. */
  const passes: [number, number][] = [];
  {
    const d1 = (panicAt - 0.1) / 2;                       // 2 passes, ~524 px/s  SEARCHING
    passes.push([0.1, 0.1 + d1], [0.1 + d1, panicAt]);
    const d2 = (stopAt - panicAt) / 3;                    // 3 passes, ~1002 px/s PANIC
    for (let i = 0; i < 3; i++) passes.push([panicAt + i * d2, panicAt + (i + 1) * d2]);
  }
  const passStart = (tt: number) => {
    for (const p of passes) if (tt >= p[0] && tt < p[1]) return p[0];
    if (tt >= revealAt && tt < mergeAt) return revealAt;
    if (tt >= stopAt && tt < pasteAt) return stopAt;
    return Math.max(0, tt - 0.3);
  };

  /* THE FRONTIER. Left of it the trace is steadied, right of it agitated.
     It stops at 909.6, not 996 — the 86px gap is what keeps NOW un-reached so
     the merge is still available as an event. */
  const FRONT = [PLOT_L, 312, 540, 768, 909.6];
  const frontierX = (tt: number) => {
    let x = FRONT[0];
    for (let i = 0; i < A.length && i < 4; i++) {
      if (tt >= A[i].at) x = FRONT[i] + (FRONT[i + 1] - FRONT[i]) * OUT_E(clamp((tt - A[i].at) / 0.34));
    }
    return x;
  };

  const scanX = (tt: number) => {
    if (tt < 0.1) return PLOT_L;
    for (const p of passes) {
      if (tt >= p[0] && tt < p[1]) return PLOT_L + (PLOT_R - PLOT_L) * ((tt - p[0]) / (p[1] - p[0]));
    }
    // the RETURN: right-to-left, and it wipes the dim off behind it
    if (tt >= stopAt && tt < pasteAt) {
      return PLOT_R + (PLOT_L - PLOT_R) * clamp((tt - stopAt) / Math.max(pasteAt - stopAt, 0.01));
    }
    // between the paste and the reveal the head IS the pen: it rides the frontier
    if (tt >= pasteAt && tt < revealAt) return frontierX(tt);
    if (tt >= revealAt && tt < mergeAt) {
      return PLOT_L + (PLOT_R - PLOT_L) * clamp((tt - revealAt) / Math.max(mergeAt - revealAt, 0.01));
    }
    return PLOT_R;
  };

  /* ---- the y function. EVERYTHING moves in here, nothing moves the group. -- */
  const ampLock = (x: number, tt: number) => smooth(clamp((frontierX(tt) + 30 - x) / 60));
  const amp = (x: number, tt: number) => AMP_LOOSE + (AMP_LOCKED - AMP_LOOSE) * ampLock(x, tt);
  const trendLock = (tt: number) => (tt >= revealAt ? 1 : 0);     // UN-EASED. deliberately.
  const sag = (tt: number) => (tt >= revealAt ? 0 : 42 * OUT_E(clamp((tt - 5.4) / 0.5)));
  const DENT = [
    { x: CB_X[0], at: 4.89 }, { x: CB_X[1], at: 4.99 }, { x: CB_X[2], at: 5.09 },
  ];
  const dents = (x: number, tt: number) =>
    DENT.reduce((a, d) => (tt < d.at ? a
      : a + 18 * Math.exp(-(tt - d.at) * 2.5) * Math.exp(-((x - d.x) ** 2) / (2 * 70 * 70))), 0);
  const flinch = (tt: number) =>
    tt < pasteAt ? 0 : 20 * Math.exp(-(tt - pasteAt) * 5.5) * Math.sin((tt - pasteAt) * 26);

  const yAt = (x: number, tt: number) =>
    REST_Y + (trendY(x) - REST_Y) * trendLock(tt)
    + amp(x, tt) * wave(x, tt)
    + sag(tt) + dents(x, tt) + flinch(tt);

  /* ---- the hand-off. Parameterised by p, NOT by x — the DOMAIN itself
     contracts from [84,996] to [214.29,865.71], which is what stops the ends
     popping on the last frame before CaseBullets takes over. ---------------- */
  const d = demoteAt == null ? 0 : OUT_E(clamp((t - demoteAt) / Math.max(demoteDur, 0.01)));
  const cbYAt = (p: number) => {
    const u = clamp(p) * 3;
    const i = Math.min(2, Math.floor(u));
    return CB_Y[i] + (CB_Y[i + 1] - CB_Y[i]) * (u - i);
  };

  const pts: [number, number][] = [];
  for (let s = 0; s <= 152; s++) {
    const p = s / 152;
    const xLive = PLOT_L + (PLOT_R - PLOT_L) * p;
    const yLive = yAt(xLive, t);
    const xCB = CB_X[0] + (CB_X[3] - CB_X[0]) * p;
    const yCB = cbYAt(p);
    pts.push([xLive + (xCB - xLive) * d, yLive + (yCB - yLive) * d]);
  }
  const line = pts.map((q, i) => `${i ? "L" : "M"}${q[0].toFixed(1)} ${q[1].toFixed(1)}`).join(" ");
  const fillPath = `${line} L${pts[152][0].toFixed(1)} ${FLOOR_Y} L${pts[0][0].toFixed(1)} ${FLOOR_Y} Z`;

  const revealed = t >= revealAt;
  const dash = revealed ? undefined : "16 13";
  const flash = t >= revealAt && frame < Math.round((start + revealAt) * fps) + ONE;

  /* the dim: the picture narrows to the form's window on "Two years", and the
     RETURNING HEAD wipes it off — so a copy contradiction becomes a large-area
     luminance event that says something true: your career is longer than the form. */
  const dimOn = t >= panicAt && t < pasteAt;
  const wipeX = t >= stopAt && t < pasteAt ? scanX(t) : PLOT_L;
  const dimW = dimOn ? Math.max(0, Math.min(REVIEW_X, t < stopAt ? REVIEW_X : wipeX)) : 0;

  /* the ledger. The stack densifies on the reveal frame: the page was always
     full, and only four lines of it are yours. */
  const stripY = 360 + 88 * OUT_E(clamp((t - pasteAt) / 0.3));
  const pitch = revealed ? 17 : 26;
  const ruleA = revealed ? 0.3 : 0.06;
  const gone = clamp((t - demoteAt) / 0.4);          // everything but the trace + runLabel

  return (
    <AbsoluteFill style={{ width, height, background: transparent ? undefined : ink }}>
      <Fonts />
      {transparent ? null : <AuroraBed t={t} accent={accent} ink={ink} opacity={0.3} />}

      {/* ---- THE LEDGER STRIP — the cause of the line, not decoration ------ */}
      <svg width={width} height={height} style={{ position: "absolute", inset: 0 }}>
        <defs>
          {/* CaseBullets' cb-arc verbatim: identical gradient definitions on both
              sides of the cut removes the boundary-diff risk entirely. */}
          <linearGradient id="pt-line" x1="0" y1="1" x2="1" y2="0">
            <stop offset="0%" stopColor={accent} />
            <stop offset="100%" stopColor="#FFC2E4" />
          </linearGradient>
          <linearGradient id="pt-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={accent} stopOpacity={revealed ? 0.3 : 0.05} />
            <stop offset="78%" stopColor={accent} stopOpacity={0} />
          </linearGradient>
          {/* ONE filter, tightly regioned. feGaussianBlur over a full 1080x1920
              recomputed 356 times is the #1 render-cost risk in this file. The
              region must still contain the trace at ARC_TOP=300 during demote. */}
          <filter id="pt-soft" filterUnits="userSpaceOnUse" x="0" y="270" width="1080" height="900">
            <feGaussianBlur stdDeviation="11" />
          </filter>
          <clipPath id="pt-strip">
            <rect x="0" y={stripY - 46} width={width} height={234} />
          </clipPath>
        </defs>

        <g clipPath="url(#pt-strip)" opacity={1 - gone}>
          {CB_X.map((cx, ci) => {
            const wipe = clamp((t - ci * 0.15) / 0.45);
            if (wipe <= 0) return null;
            const dimmed = dimOn && cx < REVIEW_X && cx > wipeX ? 0.42 : 1;
            const lit = Math.abs(scanX(t) - cx) < 75 && t < pasteAt ? 0.06 : 0;
            const ans = A[ci];
            return (
              <g key={ci}>
                {Array.from({ length: 16 }, (_, k) => {
                  // one seeded rule per column detaches at 4.49 and falls 400px
                  const falls = ci < 3 && k === 3 + ci && t >= 4.49;
                  const fp = falls ? clamp((t - 4.49) / 0.45) : 0;
                  const filled = !!ans && k === 8 && t >= ans.at;
                  const y = Math.round(stripY - 40 + k * pitch + 400 * fp * fp);
                  const x0 = cx - 67 + (hash(ci * 17 + k) - 0.5) * 44;
                  const w = 40 + hash(ci * 31 + k) * 110;
                  return (
                    <rect key={k} x={x0} y={y} width={w * wipe} height={4} rx={2}
                          fill={filled ? accent : BRAND.paper}
                          opacity={(filled ? 0.9 : (ruleA + lit) * dimmed) * (1 - fp)} />
                  );
                })}
              </g>
            );
          })}
        </g>

        {/* the one interior division. ONE hairline is a boundary; four would be
            a gridline system, which is measurement grammar. Present from frame 0
            so it does not pop, brightening when the picture narrows. */}
        <line x1={REVIEW_X} y1={TOP_Y} x2={REVIEW_X} y2={FLOOR_Y}
              stroke={dimOn ? accent : BRAND.paper} strokeWidth={1}
              opacity={(dimOn ? 0.3 : 0.07) * (1 - gone)} />

        {/* ---- THE TRACE ---- */}
        <path d={fillPath} fill="url(#pt-fill)" opacity={1 - d} />
        <path d={line} stroke={rgba("#000000", 0.45)} strokeWidth={16} fill="none"
              strokeLinecap="round" strokeLinejoin="round" strokeDasharray={dash}
              opacity={0.9 * (1 - d * 0.5)} />
        <path d={line} stroke="url(#pt-line)" strokeWidth={30} fill="none"
              strokeLinecap="round" strokeLinejoin="round" strokeDasharray={dash}
              filter="url(#pt-soft)" opacity={0.16 * (1 - d)} />
        <path d={line} stroke="url(#pt-line)" strokeWidth={10 - 2 * d} fill="none"
              strokeLinecap="round" strokeLinejoin="round" strokeDasharray={dash}
              opacity={1 - 0.3 * d} />

        {/* the four nodes CaseBullets draws on its own first frame, faded in over
            the back half of the demote so the cut lands on an identical picture */}
        {d > 0.5 ? CB_X.map((cx, i) => (
          <circle key={`n${i}`} cx={cx} cy={CB_Y[i]} r={13} fill="#FFFFFF"
                  opacity={clamp((d - 0.55) / 0.45)} filter="url(#pt-soft)" />
        )) : null}

        {/* ---- PROBES (b1-b2): the line reaching up for a record that isn't
             there. The inversion of the threads in beat 3, which run DOWNWARD. */}
        {t < pasteAt ? CB_X.map((cx, ci) => {
          // WIDER and BRIGHTER than first drafted. At 2px/0.45 they were present
          // in the file and invisible in the picture, which left the 400px
          // corridor between the ledger and the trace empty -- the exact hole the
          // frame audit measured. They are the only thing crossing it in beats
          // 1-2, so they have to carry it.
          const near = Math.abs(scanX(t) - cx);
          if (near > 150) return null;
          const p = smooth(1 - near / 150);
          const y0 = yAt(cx, t);
          const tip = y0 - (y0 - (stripY + 180)) * 0.78 * p;
          return (
            <g key={`p${ci}`} opacity={p}>
              <line x1={cx} y1={y0} x2={cx} y2={tip} stroke={accent} strokeWidth={3} opacity={0.62} />
              {/* the tip is what says REACHING: it arrives, and finds nothing */}
              <circle cx={cx} cy={tip} r={5} fill={accent} opacity={0.85} />
              <circle cx={cx} cy={tip} r={13} fill="none" stroke={accent}
                      strokeWidth={2} opacity={0.28 * p} />
            </g>
          );
        }) : null}

        {/* ---- THREADS (b3): each answer drops from its ledger rule INTO the
             trace. What the interview extracted, arriving. */}
        {A.map((a, i) => {
          if (t < a.at) return null;
          const p = OUT_E(clamp((t - a.at) / 0.26));
          const f = 1 - clamp((t - a.at - 0.4) / 0.4);
          if (f <= 0) return null;
          const y0 = stripY - 40 + 8 * pitch;
          const y1 = yAt(CB_X[i], t);
          return (
            <line key={`th${i}`} x1={CB_X[i]} y1={y0} x2={CB_X[i]} y2={y0 + (y1 - y0) * p}
                  stroke={accent} strokeWidth={2} opacity={0.9 * f} />
          );
        })}

        {/* ---- THE FRONTIER. Never a track behind it and never a hue shift on
             the locked side — either would make it a progress bar, i.e. a
             percentage claim about a person. */}
        {A.length && t >= A[0].at && t < revealAt ? (() => {
          const fx = frontierX(t), fy = yAt(fx, t);
          return <line x1={fx} y1={fy - 70} x2={fx} y2={fy + 50}
                       stroke={accent} strokeWidth={2} opacity={0.55} />;
        })() : null}

        {/* ---- NOW, PINNED AT x=996. It moves only in y. NOW does not travel,
             and that is the whole answer to "position has to be consistent". */}
        {d < 0.6 ? (() => {
          // pts[152], not yAt(PLOT_R) -- once the demote starts, the live y is no
          // longer where the line IS, and NOW was left hanging 360px below it.
          const ny = pts[152][1];
          const rp = (t % 1.15) / 1.15;
          return (
            <g opacity={1 - clamp(d / 0.6)}>
              <circle cx={PLOT_R} cy={ny} r={18 + 26 * rp} fill="none"
                      stroke={accent} strokeWidth={3} opacity={0.5 * (1 - rp)} />
              <circle cx={PLOT_R} cy={ny} r={13} fill="#FFFFFF" filter="url(#pt-soft)" />
            </g>
          );
        })() : null}

        {/* ---- THE SCANNER and its comet. Each ghost sits at its TRUE past
             position, clamped to the pass start so a wrap piles them up at x=84
             instead of stringing them backwards across the frame. */}
        {t > 0.1 && t < mergeAt ? (() => {
          const sx = scanX(t), sy = yAt(sx, t), ps = passStart(t);
          return (
            <g>
              {Array.from({ length: 8 }, (_, j) => {
                const k = 8 - j;
                const tk = Math.max(t - k * 0.035, ps);
                const xk = scanX(tk);
                return (
                  <circle key={k} cx={xk} cy={yAt(xk, tk)} r={Math.max(1, 13 - k * 1.4)}
                          fill="#FFC2E4" opacity={0.5 * (1 - k / 9)} />
                );
              })}
              <circle cx={sx} cy={sy} r={30} fill={accent} opacity={0.3} />
              <circle cx={sx} cy={sy} r={14} fill="#FFF6FB" />
            </g>
          );
        })() : null}

        {/* ---- ARRIVALS. Four grey collapses to NOTHING, then one white merge.
             The contrast between them IS the resolution of the chase. */}
        {passes.map((p, i) => {
          const dt = t - p[1];
          if (dt < 0 || dt > 0.35) return null;
          const q = dt / 0.35;
          return <circle key={`a${i}`} cx={PLOT_R} cy={yAt(PLOT_R, p[1])} r={14 + 24 * q}
                         fill="none" stroke={BRAND.paper} strokeWidth={3} opacity={0.25 * (1 - q)} />;
        })}
        {t >= mergeAt && t < mergeAt + 0.24 ? (() => {
          // same reason: mergeAt and demoteAt are the same instant, so the ring
          // has to travel with the line it is merging into.
          const q = (t - mergeAt) / 0.24;
          return <circle cx={pts[152][0]} cy={pts[152][1]} r={18 + 102 * q} fill="none"
                         stroke="#FFFFFF" strokeWidth={5} opacity={0.9 * (1 - q)} />;
        })() : null}
      </svg>

      {/* the dim, as a wash over the plot band only — the picture narrows to the
          form's window, then re-widens when the head comes back */}
      {dimW > 0 ? (
        // NOT a box. A hard-edged wash reads as a UI panel dropped on the frame --
        // the render made that unmistakable. Soft on the leading edge (so the
        // returning head wipes it rather than sweeping a wall) and masked to
        // nothing top and bottom, so it reads as the picture narrowing rather
        // than as a rectangle someone left switched on.
        <div style={{
          position: "absolute", left: 0, top: 300, width: dimW + 120, height: 960,
          background: `linear-gradient(90deg, ${rgba(ink, 0.66)} 0%, ${rgba(ink, 0.66)} ${
            (dimW / (dimW + 120)) * 100 - 6}%, ${rgba(ink, 0)} 100%)`,
          WebkitMaskImage:
            "linear-gradient(180deg, rgba(0,0,0,0) 0%, #000 14%, #000 84%, rgba(0,0,0,0) 100%)",
          maskImage:
            "linear-gradient(180deg, rgba(0,0,0,0) 0%, #000 14%, #000 84%, rgba(0,0,0,0) 100%)",
          pointerEvents: "none",
        }} />
      ) : null}

      {/* ---- SEARCH BLOCK: the top zone showing the SAME event as the plot ---- */}
      {t < stopAt + 0.13 ? (() => {
        // clears in 0.13s, not 0.25 -- the prompt card occupies this exact slot and
        // the render caught them printed over each other for a quarter second.
        const f = t < stopAt ? 1 : 1 - clamp((t - stopAt) / 0.13);
        const sw = scanX(t);
        return (
          <div style={{ position: "absolute", inset: 0, opacity: f }}>
            <div style={{ position: "absolute", left: PLOT_L, top: 232, fontFamily: MONO,
                          fontSize: 28, letterSpacing: 6, color: rgba(BRAND.paper, 0.5) }}>
              {searchLabel}{".".repeat(Math.floor(t / 0.3) % 4)}
            </div>
            {/* the scan hairline — a second copy of the scanner's position at the
                top of the frame. This is what binds the top zone to the thing the
                eye is already tracking, and why the void stops being void. */}
            <div style={{ position: "absolute", left: PLOT_L, top: 300, width: PLOT_R - PLOT_L,
                          height: 3, background: rgba(BRAND.paper, 0.1) }} />
            <div style={{ position: "absolute", left: sw - 60, top: 300, width: 120, height: 3,
                          background: `linear-gradient(90deg, ${rgba(accent, 0)}, ${accent}, ${rgba(accent, 0)})` }} />
            {t >= stopAt ? (
              <div style={{ position: "absolute", left: PLOT_L, top: 252,
                            width: (PLOT_R - PLOT_L) * clamp((t - stopAt) / 0.2), height: 3,
                            background: accent }} />
            ) : null}
          </div>
        );
      })() : null}

      {/* ---- THE PROMPT CARD ---- */}
      {t >= pasteAt - 0.08 && pasteText.length ? (() => {
        const sp = spring({
          frame: frame - Math.round((start + pasteAt - 0.05) * fps),
          fps, config: { damping: 15, stiffness: 200, mass: 0.7 },
        });
        if (sp <= 0.001) return null;
        return (
          <div style={{
            position: "absolute", left: 76, top: 236, width: 928,
            opacity: sp * (1 - gone),
            transform: `translateY(${(1 - sp) * -260}px)`,
            padding: "34px 40px", ...glassChrome(24),
            // GUARD: with `transparent` there is no bed behind, so the refraction
            // sample has nothing to read and the panel renders as a grey box.
            // Fall back to a flat wash and keep only the inset highlight.
            background: transparent ? rgba("#ffffff", 0.06) : undefined,
          }}>
            {transparent ? null : (
              <GlassInner t={t} x={76} y={236} w={928} h={188} accent={accent} ink={ink} />
            )}
            <div style={{ position: "absolute", left: 0, top: 0, width: 6, height: "100%", background: accent }} />
            {pasteText.slice(0, 3).map((ln, i) => (
              <div key={i} style={{ fontFamily: MONO, fontSize: 29, lineHeight: "46px",
                                    color: rgba(BRAND.paper, 0.82), position: "relative" }}>{ln}</div>
            ))}
          </div>
        );
      })() : null}

      {/* ---- LABELS. Three strings, no digits except two durations, no interior
           ticks, no values. runLabel holds full opacity through the demote so the
           only thing that changes at the cut is the WORDS in it. ------------- */}
      <div style={{ position: "absolute", left: PLOT_L, top: SAFE.headerFloor + 46, fontFamily: MONO,
                    fontSize: 25, letterSpacing: 6, color: rgba(BRAND.paper, 0.4) }}>{runLabel}</div>
      <div style={{ position: "absolute", left: PLOT_L, top: 1124, fontFamily: MONO, fontSize: 24,
                    letterSpacing: 4, color: rgba(BRAND.paper, 0.3), opacity: 1 - gone }}>{spanLabelL}</div>
      <div style={{ position: "absolute", right: width - PLOT_R, top: 1124, fontFamily: MONO, fontSize: 24,
                    letterSpacing: 4, color: rgba(BRAND.paper, 0.45), opacity: 1 - gone }}>{spanLabelR}</div>
      {t >= panicAt + 0.04 ? (
        <div style={{ position: "absolute", left: 0, right: 0, top: 1124, textAlign: "center",
                      fontFamily: MONO, fontSize: 24, letterSpacing: 4, color: rgba(accent, 0.7),
                      opacity: clamp((t - panicAt - 0.04) / 0.4) * (1 - gone),
                      transform: `translateX(${REVIEW_X + (PLOT_R - REVIEW_X) / 2 - width / 2}px)` }}>
          {reviewLabel}
        </div>
      ) : null}

      {/* ---- THE VERDICT LINE. Replaces two wordmarks that sat still for 6.87s
           and 3.15s. Five claims, longest hold 2.82s, and never the only moving
           thing on screen. Scale is clamped from CHARACTER COUNT, never from a
           DOM measurement — measuring Anton is the silent-breakage path. ----- */}
      {(() => {
        let cur: ProofVerdict | null = null, ci = -1;
        verdicts.forEach((v, i) => { if (t >= v.at) { cur = v; ci = i; } });
        if (!cur) return null;
        const c = cur as ProofVerdict;
        const nxt = verdicts[ci + 1];
        const inP = clamp((t - c.at) / 0.24);
        const outP = nxt ? clamp((t - (nxt.at - 0.18)) / 0.18) : gone;
        if (outP >= 1) return null;
        const sc = Math.max(0.82, Math.min(1, 15 / Math.max(c.text.length, 1)));
        return (
          <div style={{
            position: "absolute", left: PLOT_L, top: 1200, width: PLOT_R - PLOT_L,
            fontFamily: DISPLAY, fontSize: Math.round(112 * sc), lineHeight: `${Math.round(112 * sc)}px`,
            color: BRAND.paper, whiteSpace: "nowrap", letterSpacing: -1,
            opacity: (1 - outP) * inP * (1 - gone),
            transform: `translateY(${(1 - OUT_E(inP)) * 40 + outP * 40}px)`,
          }}>{c.text}</div>
        );
      })()}

      {/* one un-eased frame of white. The reveal is deliberately the largest
          event in the film; an eased version of it dies at 2x playback. */}
      {flash ? <AbsoluteFill style={{ background: "rgba(255,255,255,0.14)" }} /> : null}
    </AbsoluteFill>
  );
};

/* ---- canonical demo ------------------------------------------------------ */
export const proofTraceDemo: ProofTraceProps = {
  runLabel: "YOUR LAST 5 YEARS",
  searchLabel: "SEARCHING YOUR LAST 5 YEARS",
  spanLabelL: "5 YEARS AGO",
  spanLabelR: "NOW",
  reviewLabel: "THIS REVIEW",
  reviewFrom: 0.6,
  panicAt: 3.58,
  stopAt: 6.31,
  pasteAt: 6.52,
  pasteText: ["You are my appraisal coach.", "Ask me ONE question at a time."],
  answers: [
    { label: "what broke", at: 6.98 },
    { label: "what you fixed", at: 7.42 },
    { label: "who noticed", at: 7.86 },
    { label: "what you taught", at: 8.3 },
  ],
  revealAt: 8.86,
  mergeAt: 11.3,
  demoteAt: 11.3,
  demoteDur: 0.5,
  verdicts: [
    { at: 0.62, text: "NO RECORD." },
    { at: 1.84, text: "STILL NOTHING." },
    { at: 4.66, text: "NONE OF IT KEPT" },
    { at: 6.74, text: "SO ANSWER." },
    { at: 8.86, text: "IT'S ALL THERE" },
  ],
};
