import React from "react";
import { AbsoluteFill, Easing, useCurrentFrame, useVideoConfig } from "remotion";
import { BRAND, MONO, rgba, clamp, Fonts } from "./kit";
import { enter, settle, idle, clamp01, mhash, OUT_E, IN_E } from "./motion";

/* =============================================================================
   ContextTube — the pilot film: "Why Claude Forgets Long Chats".

   THE WORLD. One glass tube, centre frame, for the whole film: the context
   window as a physical container. Messages are blocks that drop in at the top;
   when the tube is full, every arrival pushes the oldest block out of the open
   bottom, where it falls into the dark below the glass. One block is YOURS —
   the hot magenta one, the important thing you told it — and the film is its
   journey: in, down, OUT, and honestly back.

   THE HONEST MECHANIC. There is no "pin" in claude.ai, so no pin is shown.
   The fix demonstrated is the real one: the chat SUMMARIZES itself into one
   bright block, the summary is carried into a FRESH tube, and the scan that
   failed in the full tube succeeds there. The GIVE (the description's prompt)
   is exactly the summary ask — the payoff object and the artifact the viewer
   takes away are the same thing.

   MECHANISM CLASS, DECLARED. The tube is an illustration of a mechanism, not
   a screenshot of a product. No numbers anywhere: capacity is shown as a full
   tube, never as a token count we would have to source.

   GRAMMAR THIS SCENE OWNS (the global layers own the rest):
   - U3  carry: the tube never leaves; the hot block crosses every phase.
   - U8  payoff: the ANSWER first exists at scan2 (~78% of runtime); its
         absence is planted by the failed scan at 40%.
   - U9  knee: the overflow — first block ejected — lands in the 4-8s window.
   - U1  no dead frames: arrivals, falls, scans or absorbs run continuously;
         every hold idles.
   - C4  one subject, one verb: blocks drop. Everything is that verb.

   Times arrive film-absolute via props (the build resolves "@beatN+x" from the
   measured VO clock). The arrival schedule is derived deterministically from
   those anchors — nothing here is random.
   ========================================================================== */

const TUBE_W = 560;
const TUBE_X = 540;              // centre
const TUBE_TOP = 292;
const TUBE_BOT = 1108;           // open bottom
const BLOCK_W = 470;
const BLOCK_H = 96;
const PITCH = 106;               // block height + gap
const K = 7;                     // capacity in slots
const SLOT0_Y = TUBE_TOP + 30;   // top slot's y

const G = 3400;                  // gravity px/s^2 for ejected blocks

export type ContextTubeProps = {
  /** film-absolute anchors. Defaults sketch the 34.5s plan. */
  hotAt?: number;        // the hot block arrives
  overflowAt?: number;   // tube full — first ejection (THE KNEE)
  hotFallAt?: number;    // the hot block is ejected
  askAt?: number;        // the "?" block arrives
  scanAt?: number;       // failed scan sweep starts
  summaryAt?: number;    // the absorb begins
  freshAt?: number;      // fresh tube replaces the full one
  scan2At?: number;      // the mirrored scan starts
  answerAt?: number;     // THE PAYOFF: the answer flares
  endAt?: number;        // scene dives into the whiteout
  hotLines?: string[];   // greeked label on the hot block (2 short lines max)
  accent?: string;
  ink?: string;
  start?: number;
  width?: number;
  height?: number;
};

type Block = {
  t: number;             // arrival time
  hot?: boolean;
  q?: boolean;           // the question block
  seed: number;
};

export const ContextTube: React.FC<ContextTubeProps> = ({
  hotAt = 1.2,
  overflowAt = 5.5,
  hotFallAt = 10.2,
  askAt = 13.2,
  scanAt = 14.2,
  summaryAt = 18.8,
  freshAt = 22.8,
  scan2At = 26.0,
  answerAt = 27.2,
  endAt = 29.4,
  hotLines = ["flight — FRI 6 AM", "gate closes 5:30"],
  accent = BRAND.mag,
  ink = BRAND.ink,
  start = 0,
  width = 1080,
  height = 1920,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - start;

  /* ---- the deterministic schedule ---------------------------------------
     Derived from the anchors so the choreography retimes with the VO. The
     rule K blocks fill the tube gives closed-form ejections: block j is
     ejected exactly when block j+K arrives. */
  const HOT = 4;                                   // the hot block's index
  const blocks: Block[] = [];
  {
    // 8 pre-overflow arrivals ending just before overflowAt; hot is the 5th
    for (let i = 0; i < K; i++) {
      const p = i / (K - 1);
      const tt = 0.02 + (overflowAt - 0.55 - 0.02) * p;
      blocks.push({ t: i === HOT ? Math.min(hotAt, tt) : tt, hot: i === HOT, seed: i });
    }
    blocks.sort((a, b) => a.t - b.t);
    // post-overflow arrivals: each one ejects a block; the (HOT+K)th arrival
    // is scheduled AT hotFallAt so the loss lands on its VO line
    const postN = HOT + 1;                          // enough to eject up to hot
    for (let i = 0; i < postN; i++) {
      const p = postN === 1 ? 1 : i / (postN - 1);
      blocks.push({ t: overflowAt + (hotFallAt - overflowAt) * p, seed: 20 + i });
    }
    // the question block, then quiet until the summary
    blocks.push({ t: askAt, q: true, seed: 40 });
  }
  const ejectTimeOf = (j: number) => (j + K < blocks.length ? blocks[j + K].t : Infinity);

  /* fresh-tube world shift */
  const fresh = OUT_E(clamp01((t - freshAt) / 0.7));
  const oldX = -640 * fresh;                        // old tube exits left
  const oldDim = 1 - 0.75 * fresh;

  /* ---- per-block state ---------------------------------------------------- */
  const renderBlock = (b: Block, j: number) => {
    if (t < b.t - 0.35) return null;
    const ej = ejectTimeOf(j);

    // slot index: one eased step down per later arrival, capped at K-1
    let s = 0;
    for (let k = j + 1; k < blocks.length; k++) {
      if (blocks[k].t > t) break;
      s += enter(t, blocks[k].t, 0.4, 0.03);
    }
    s = Math.min(s, K - 1 + (t >= ej ? 1 : 0));

    // entry: drops from above the tube into slot 0 (then shifts)
    const drop = enter(t, b.t - 0.32, 0.42, 0.05);
    const entryY = -180 + (SLOT0_Y + 180) * drop;
    let y = Math.max(entryY, SLOT0_Y) + Math.max(0, s) * PITCH - (1 - drop) * 60;
    let x = TUBE_X - BLOCK_W / 2;
    let opacity = Math.min(1, drop * 1.6);
    let rot = 0;

    // ejection: gravity out of the open bottom
    if (t >= ej) {
      const d = t - ej;
      y = SLOT0_Y + (K - 1) * PITCH + PITCH * 0.4 + 0.5 * G * d * d;
      rot = (mhash(b.seed) - 0.5) * 34 * d;
      if (b.hot) {
        // yours does not vanish — it RESTS in the dark, visibly outside the glass
        const restY = 1136;
        y = Math.min(y, restY);
        opacity = y >= restY - 1 ? 0.42 : 1;
      } else {
        opacity = Math.max(0, 1 - d * 1.4);
      }
    }
    // the question dissolves with its failed reply — it has been answered by
    // nothing, and leaving it in the tube collided with the summary forming
    if (b.q) opacity *= 1 - clamp01((t - (scanAt + 3.0)) / 0.7);
    if (opacity <= 0.01) return null;

    const wob = idle(t, b.seed, 1.4);
    const lit = b.hot ? 1 : 0;
    // the failed scan brushes each block it passes
    const sweep1 = t >= scanAt && t < scanAt + 1.4
      ? clamp01(1 - Math.abs((SLOT0_Y + ((t - scanAt) / 1.4) * (TUBE_BOT - SLOT0_Y)) - y) / 90) : 0;

    return (
      <div key={j} style={{
        position: "absolute", left: x + wob.x + oldX, top: y + wob.y,
        width: BLOCK_W, height: BLOCK_H, borderRadius: 16,
        opacity: opacity * oldDim,
        transform: `rotate(${rot.toFixed(1)}deg)`,
        background: b.hot
          ? `linear-gradient(135deg, ${rgba(accent, 0.32)}, ${rgba(accent, 0.14)})`
          : b.q
            ? `linear-gradient(135deg, ${rgba(BRAND.cyan, 0.22)}, ${rgba(BRAND.cyan, 0.08)})`
            : `linear-gradient(135deg, ${rgba("#ffffff", 0.1 + sweep1 * 0.1)}, ${rgba("#ffffff", 0.04)})`,
        border: `1.5px solid ${b.hot ? rgba(accent, 0.9) : b.q ? rgba(BRAND.cyan, 0.75) : rgba("#ffffff", 0.2 + sweep1 * 0.3)}`,
        boxShadow: b.hot
          ? `0 0 ${26 + Math.sin(t * 2.4) * 8}px ${rgba(accent, 0.5)}, 0 14px 30px -14px ${rgba("#000", 0.8)}`
          : `0 14px 30px -14px ${rgba("#000", 0.8)}`,
        padding: "16px 20px",
        display: "flex", flexDirection: "column", justifyContent: "center", gap: 9,
      }}>
        {b.hot ? hotLines.slice(0, 2).map((ln, i) => (
          <div key={i} style={{ fontFamily: MONO, fontSize: 25, letterSpacing: 1,
                                color: rgba("#fff", 0.95), whiteSpace: "nowrap" }}>{ln}</div>
        )) : b.q ? (
          <div style={{ fontFamily: MONO, fontSize: 34, color: rgba("#fff", 0.9) }}>
            which day was it… ?
          </div>
        ) : (
          // greeked lines — a message, unreadable on purpose (it is not the story)
          [0, 1].map((i) => (
            <div key={i} style={{
              height: 9, width: 90 + mhash(b.seed * 13 + i) * 220, borderRadius: 5,
              background: rgba("#ffffff", 0.34 - i * 0.1),
            }} />
          ))
        )}
      </div>
    );
  };

  /* ---- the tube itself ----------------------------------------------------- */
  const overflowFlash = t >= overflowAt && t < overflowAt + 0.2
    ? 1 - (t - overflowAt) / 0.2 : 0;
  const tube = (x0: number, dim: number, key: string, born: number) => {
    const up = enter(t, born, 0.6, 0.04);
    if (up <= 0) return null;
    return (
      <div key={key} style={{
        position: "absolute", left: x0 - TUBE_W / 2, top: TUBE_TOP - 40,
        width: TUBE_W, height: TUBE_BOT - TUBE_TOP + 40,
        opacity: dim * up,
        transform: `translateY(${(1 - up) * 80}px)`,
        borderLeft: `3px solid ${rgba("#fff", 0.44 + overflowFlash * 0.5)}`,
        borderRight: `3px solid ${rgba("#fff", 0.44 + overflowFlash * 0.5)}`,
        borderTop: `2.5px solid ${rgba("#fff", 0.22)}`,
        borderRadius: "34px 34px 8px 8px",
        background: `linear-gradient(180deg, ${rgba("#ffffff", 0.05)}, ${rgba("#ffffff", 0.012)} 60%, ${rgba("#ffffff", 0)})`,
        boxShadow: `inset 0 2px 0 ${rgba("#fff", 0.3)}, 0 40px 90px -50px ${rgba("#000", 0.9)}`,
      }}>
        {/* the open bottom: two small feet, a gap between — things can LEAVE */}
        <div style={{ position: "absolute", left: -2.5, bottom: -12, width: 54, height: 12,
                      borderLeft: `2.5px solid ${rgba("#fff", 0.34)}`,
                      borderBottom: `2.5px solid ${rgba("#fff", 0.2)}` }} />
        <div style={{ position: "absolute", right: -2.5, bottom: -12, width: 54, height: 12,
                      borderRight: `2.5px solid ${rgba("#fff", 0.34)}`,
                      borderBottom: `2.5px solid ${rgba("#fff", 0.2)}` }} />
      </div>
    );
  };

  /* ---- scans: the same beam, failing then succeeding ------------------------ */
  const beam = (from: number, dur: number, x0: number, hit: boolean) => {
    if (t < from || t > from + dur + 0.3) return null;
    const p = clamp01((t - from) / dur);
    const by = SLOT0_Y + p * (TUBE_BOT - 60 - SLOT0_Y);
    const fade = t > from + dur ? 1 - (t - from - dur) / 0.3 : 1;
    return (
      <div style={{
        position: "absolute", left: x0 - TUBE_W / 2 + 8, top: by,
        width: TUBE_W - 16, height: 4, opacity: fade,
        background: `linear-gradient(90deg, ${rgba(BRAND.cyan, 0)}, ${hit ? BRAND.cyan : rgba(BRAND.cyan, 0.8)}, ${rgba(BRAND.cyan, 0)})`,
        boxShadow: `0 0 18px ${rgba(BRAND.cyan, 0.7)}`,
      }} />
    );
  };

  /* the fog reply after the failed scan */
  const fogP = clamp01((t - (scanAt + 1.5)) / 0.5);
  const fogGone = clamp01((t - (scanAt + 3.0)) / 0.8);

  /* the absorb: sparks from the tube converge into the summary block */
  const sumP = clamp01((t - summaryAt) / 1.2);
  const sumLand = enter(t, summaryAt + 1.15, 0.4);
  // summary block: forms above the old tube, then arcs into the FRESH tube's top slot
  const sumFormX = TUBE_X - BLOCK_W / 2;
  const sumFormY = TUBE_TOP - 156;
  const intoFresh = OUT_E(clamp01((t - (freshAt + 0.55)) / 0.6));
  const sumHomeX = sumFormX;
  const sumY = sumFormY + (SLOT0_Y - sumFormY) * intoFresh;
  const answerP = enter(t, answerAt, 0.45, 0.08);
  const flare = t >= answerAt && t < answerAt + 0.25 ? 1 - (t - answerAt) / 0.25 : 0;

  /* fresh arrivals under the summary */
  const freshArr = [freshAt + 1.3, freshAt + 2.1];

  return (
    <AbsoluteFill style={{ width, height }}>
      <Fonts />

      {/* the dark below the glass — where ejected things live */}
      <div style={{
        position: "absolute", left: 0, top: TUBE_BOT + 6, width, height: 260,
        background: `linear-gradient(180deg, ${rgba("#000", 0)}, ${rgba("#000", 0.55)})`,
        pointerEvents: "none",
      }} />

      {tube(TUBE_X + oldX, oldDim, "old", 0)}
      {blocks.map(renderBlock)}

      {/* overflow flash ring at the tube mouth — THE KNEE EVENT */}
      {overflowFlash > 0 ? (
        <div style={{
          position: "absolute", left: TUBE_X - TUBE_W / 2 - 80, top: TUBE_TOP - 130,
          width: TUBE_W + 160, height: 220, borderRadius: "50%",
          background: `radial-gradient(50% 50% at 50% 55%, ${rgba("#fff", overflowFlash * 0.55)} 0%, ${rgba(accent, overflowFlash * 0.3)} 45%, ${rgba(accent, 0)} 75%)`,
          filter: "blur(2px)",
        }} />
      ) : null}

      {beam(scanAt, 1.4, TUBE_X + oldX, false)}

      {/* the failed reply: a fog block that never resolves, then dissolves */}
      {fogP > 0 && fogGone < 1 ? (
        <div style={{
          position: "absolute", left: TUBE_X - BLOCK_W / 2 + oldX, top: TUBE_TOP - 130,
          width: BLOCK_W, height: BLOCK_H, borderRadius: 16,
          opacity: fogP * (1 - fogGone) * 0.8,
          background: rgba("#9aa", 0.12),
          border: `1.5px dashed ${rgba("#fff", 0.3)}`,
          filter: `blur(${3 + fogGone * 6}px)`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontFamily: MONO, fontSize: 30, color: rgba("#fff", 0.55),
        }}>· · ·</div>
      ) : null}

      {/* the absorb sparks */}
      {sumP > 0 && sumP < 1 ? [0, 1, 2, 3].map((i) => {
        const p = clamp01(sumP * 1.5 - i * 0.16);
        if (p <= 0) return null;
        const sy = SLOT0_Y + (i + 1.5) * PITCH;
        const yy = sy + (sumFormY + 30 - sy) * OUT_E(p);
        const xx = TUBE_X + (mhash(i * 7) - 0.5) * 200 * (1 - p) + oldX;
        return <div key={i} style={{
          position: "absolute", left: xx, top: yy, width: 14, height: 14, borderRadius: 7,
          background: accent, opacity: (1 - p * 0.7),
          boxShadow: `0 0 16px ${rgba(accent, 0.8)}`,
        }} />;
      }) : null}

      {/* THE SUMMARY BLOCK — the payoff object, and the GIVE, as one thing */}
      {sumLand > 0 ? (
        <div style={{
          position: "absolute", left: sumHomeX, top: sumY,
          width: BLOCK_W, height: BLOCK_H, borderRadius: 16,
          opacity: Math.min(1, sumLand * 1.5),
          transform: `scale(${(0.9 + 0.1 * sumLand + answerP * 0.06).toFixed(3)})`,
          background: `linear-gradient(135deg, ${rgba(accent, 0.4)}, ${rgba(accent, 0.16)})`,
          border: `2px solid ${rgba(accent, 1)}`,
          boxShadow: `0 0 ${30 + answerP * 40}px ${rgba(accent, 0.55 + flare * 0.45)}, 0 14px 30px -14px ${rgba("#000", 0.8)}`,
          padding: "13px 20px",
          display: "flex", flexDirection: "column", justifyContent: "center", gap: 7,
        }}>
          <div style={{ fontFamily: MONO, fontSize: 21, letterSpacing: 3, color: rgba("#fff", 0.8) }}>
            SUMMARY — WHAT MATTERS
          </div>
          <div style={{ fontFamily: MONO, fontSize: 24, color: "#fff", whiteSpace: "nowrap" }}>
            {hotLines[0]} · + 3 more
          </div>
        </div>
      ) : null}

      {/* fresh tube + its young arrivals */}
      {t >= freshAt ? tube(TUBE_X + (1 - fresh) * 700, 1, "fresh", freshAt) : null}
      {t >= freshAt ? freshArr.map((fa, i) => {
        const dp = enter(t, fa, 0.45, 0.05);
        if (dp <= 0) return null;
        return (
          <div key={`f${i}`} style={{
            position: "absolute", left: TUBE_X - BLOCK_W / 2,
            top: -160 + (SLOT0_Y + (i + 1) * PITCH + 160) * dp,
            width: BLOCK_W, height: BLOCK_H, borderRadius: 16,
            opacity: Math.min(1, dp * 1.5),
            background: `linear-gradient(135deg, ${rgba("#ffffff", 0.1)}, ${rgba("#ffffff", 0.04)})`,
            border: `1.5px solid ${rgba("#ffffff", 0.2)}`,
            padding: "16px 20px", display: "flex", flexDirection: "column",
            justifyContent: "center", gap: 9,
          }}>
            {[0, 1].map((k) => (
              <div key={k} style={{ height: 9, width: 100 + mhash(i * 31 + k) * 180,
                                    borderRadius: 5, background: rgba("#fff", 0.3 - k * 0.08) }} />
            ))}
          </div>
        );
      }) : null}

      {beam(scan2At, 1.0, TUBE_X, true)}

      {/* THE ANSWER — first exists here, ~78% of runtime */}
      {answerP > 0 ? (
        <div style={{
          position: "absolute", left: TUBE_X - 150, top: TUBE_TOP - 136,
          width: 300, height: 84, borderRadius: 42,
          opacity: Math.min(1, answerP * 1.4),
          transform: `scale(${answerP.toFixed(3)})`,
          background: `linear-gradient(135deg, ${rgba(BRAND.cyan, 0.3)}, ${rgba(BRAND.cyan, 0.1)})`,
          border: `2px solid ${BRAND.cyan}`,
          boxShadow: `0 0 ${34 + flare * 60}px ${rgba(BRAND.cyan, 0.6 + flare * 0.4)}`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontFamily: MONO, fontSize: 30, letterSpacing: 1, color: "#fff",
          whiteSpace: "nowrap",
        }}>FRI · 6 AM ✓</div>
      ) : null}

      {/* flare ring on the hit */}
      {flare > 0 ? (
        <div style={{
          position: "absolute", left: TUBE_X - BLOCK_W / 2 - 40, top: sumY - 40,
          width: BLOCK_W + 80, height: BLOCK_H + 80, borderRadius: 40,
          border: `4px solid ${rgba("#fff", flare)}`,
          boxShadow: `0 0 80px ${rgba(BRAND.cyan, flare * 0.9)}`,
        }} />
      ) : null}
    </AbsoluteFill>
  );
};

/* ---- canonical demo ------------------------------------------------------ */
export const contextTubeDemo: ContextTubeProps = {
  hotAt: 1.2,
  overflowAt: 5.5,
  hotFallAt: 10.2,
  askAt: 13.2,
  scanAt: 14.2,
  summaryAt: 18.8,
  freshAt: 22.8,
  scan2At: 26.0,
  answerAt: 27.2,
  endAt: 29.4,
  hotLines: ["flight — FRI 6 AM", "gate closes 5:30"],
};
