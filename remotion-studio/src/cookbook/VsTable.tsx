import React from "react";
import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from "remotion";
import {
  BRAND,
  DISPLAY,
  SANS,
  rgba,
  clamp,
  Fonts,
  AuroraBed,
  glassChrome,
  glassLite,
  GlassInner,
} from "./kit";

/* =============================================================================
   VsTable — the A-vs-B comparison table (the "why it matters" beat).

   Web-tour template DNA: the reference clone carried a "PLAIN AGENTS vs WITH
   RUFLO" table as its argument beat — two columns, a handful of rows, one side
   obviously winning. This is that form, drawn in the cookbook's material: a
   hero glass panel on the aurora bed, header row pinned, rows revealing
   top-down on a settle curve.

   The drama is the VERDICT, staged in two passes:
     1. per row — a beat after the row lands, the winning cell's text snaps to
        the accent with a soft one-shot pulse (scale + glow) while the losing
        cell fades down. The eye learns the pattern row by row.
     2. per column — once the last verdict has landed, the overall losing
        COLUMN (majority of verdicts) dims to 40%, header included, and the
        winning header gets an accent underline. The end state reads the
        conclusion at a glance, so a late still still carries the argument.

   Never static: the aurora drifts behind, the panel carries the repeating
   sheen cycle and a ±3px scripted drift, so the held final state breathes.

   Rows hard-cap at 5 (sliced) — six rows cannot fit the safe band at a
   legible size, and a comparison that needs six rows is a script problem.
   JSON-safe props only (build_ep_v2 feeds --props as JSON).
   ========================================================================== */

/** one comparison row — module-local so the file exports exactly the three
    cookbook symbols (the Props type inlines this shape into `rows`). */
type VsRow = {
  label: string; // what is being compared, e.g. "setup"
  a: string; // column-A value
  b: string; // column-B value
  verdict?: "b" | "a" | "none"; // which cell wins this row (default none)
};

export type VsTableProps = {
  title?: string; // display line above the panel, e.g. "THE DIFFERENCE"
  colA: string; // left column header, e.g. "BY HAND"
  colB: string; // right column header, e.g. "ONE COMMAND"
  rows: VsRow[]; // max 5 — hard-capped by slice
  rowStagger?: number; // seconds between row reveals (default 0.5)
  accent?: string; // winner tint (default brand magenta)
  ink?: string;
  start?: number; // seconds before the component begins
  width?: number;
  height?: number;
  transparent?: boolean; // skip the bed (overlay use inside a live comp)
};

/* ---- easing (local so the only imports are remotion + ./kit) ---- */
const easeOut = (x: number) => 1 - Math.pow(1 - clamp(x), 3);

export const VsTable: React.FC<VsTableProps> = ({
  title,
  colA,
  colB,
  rows,
  rowStagger = 0.5,
  accent = BRAND.mag,
  ink = BRAND.ink,
  start = 0,
  width = 1080,
  height = 1920,
  transparent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = (frame - start * fps) / fps; // seconds on this component's clock

  const list = (rows ?? []).slice(0, 5); // hard cap — safe band, not taste
  const n = Math.max(1, list.length);

  /* ---- timeline (seconds) ---- */
  const headerT = 0.3;
  const rowsT0 = 0.75;
  const rowAt = (i: number) => rowsT0 + i * rowStagger;
  const verdictAt = (i: number) => rowAt(i) + 0.4;
  const colT = verdictAt(n - 1) + 0.55; // the column-level conclusion

  /* ---- overall column verdict (majority of row verdicts) ---- */
  let aWins = 0;
  let bWins = 0;
  list.forEach((r) => {
    if (r.verdict === "a") aWins++;
    else if (r.verdict === "b") bWins++;
  });
  const loserCol: "a" | "b" | "none" =
    bWins > aWins ? "a" : aWins > bWins ? "b" : "none";
  const colP = easeOut((t - colT) / 0.5); // 0..1 conclusion progress

  /* ---- geometry — everything inside SAFE (132..1580) ---- */
  const panelX = 64;
  const panelW = width - panelX * 2; // 952
  const headerH = 116;
  const rowH = 148;
  const panelH = headerH + n * rowH;
  const titleH = title ? 150 : 0; // display line + gap
  const total = titleH + panelH;
  const bandTop = 152;
  const bandBot = 1560;
  const top = Math.max(bandTop, bandTop + (bandBot - bandTop - total) / 2);
  const panelY = top + titleH;

  const labelW = 300;
  const colW = (panelW - labelW) / 2; // 326
  const cellPad = 26;

  // auto-fit the value type so long strings can never clip sideways
  const maxValChars = Math.max(
    1,
    ...list.map((r) => Math.max(r.a.length, r.b.length))
  );
  const valSize = clamp((colW - cellPad * 2) / (maxValChars * 0.52), 26, 40);

  // same auto-fit for the headers — the B header is the payoff label and must
  // never truncate. Uppercase 800-weight glyphs run ~0.74em wide, plus the 3px
  // tracking each char carries, so solve width ≤ colW - 2*cellPad for size.
  const maxHdrChars = Math.max(1, colA.length, colB.length);
  const hdrSize = clamp(
    (colW - cellPad * 2 - maxHdrChars * 3) / (maxHdrChars * 0.74),
    18,
    32
  );

  /* ---- panel entrance + idle drift + sheen cycle ---- */
  const panelP = spring({
    frame: frame - start * fps,
    fps,
    durationInFrames: Math.round(0.55 * fps),
    config: { damping: 200, mass: 0.9 },
  });
  const driftX = Math.sin(t * 0.4) * 3;
  const driftY = Math.cos(t * 0.33) * 2.5;
  // entry pass, then repeat on a slow cycle so the held table still breathes
  const sheenT = t - 0.4;
  const sheenP = sheenT < 1.5 ? clamp(sheenT / 1.5) : ((sheenT - 1.5) % 3.2) / 3.2;

  const headerP = easeOut((t - headerT) / 0.45);

  /** opacity multiplier for a column at the conclusion (loser dims 60%). */
  const colMul = (c: "a" | "b") => (loserCol === c ? 1 - 0.6 * colP : 1);

  /* ---- one cell of one row ---- */
  const cell = (r: VsRow, i: number, c: "a" | "b") => {
    const text = c === "a" ? r.a : r.b;
    const wins = r.verdict === c;
    const loses = r.verdict === (c === "a" ? "b" : "a");
    const vp = easeOut((t - verdictAt(i)) / 0.4); // verdict progress
    const pulse = clamp((t - verdictAt(i)) / 0.55); // one-shot pulse window
    const scale = wins ? 1 + 0.06 * Math.sin(Math.PI * pulse) : 1;
    const dim = (loses ? 1 - 0.6 * vp : 1) * colMul(c);
    return (
      <div
        style={{
          width: colW,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
          borderLeft: `1px solid ${rgba("#ffffff", 0.07)}`,
        }}
      >
        {/* soft glow behind a freshly-won cell */}
        {wins && pulse > 0 ? (
          <div
            style={{
              position: "absolute",
              inset: 8,
              borderRadius: 18,
              background: `radial-gradient(closest-side, ${rgba(accent, 0.22)}, transparent 75%)`,
              opacity: Math.sin(Math.PI * pulse) * 0.9 + 0.25 * vp,
            }}
          />
        ) : null}
        <span
          style={{
            position: "relative",
            fontSize: valSize,
            fontWeight: 800,
            letterSpacing: 0.2,
            color: wins && vp > 0 ? accent : BRAND.paper,
            opacity: dim,
            transform: `scale(${scale})`,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
            maxWidth: colW - cellPad * 2,
            textShadow:
              wins && vp > 0 ? `0 0 24px ${rgba(accent, 0.45 * vp)}` : "none",
          }}
        >
          {text}
        </span>
      </div>
    );
  };

  return (
    <AbsoluteFill
      style={{
        background: transparent ? undefined : ink,
        fontFamily: SANS,
        overflow: "hidden",
      }}
    >
      <Fonts />
      {!transparent && <AuroraBed t={t} accent={accent} ink={ink} />}

      {/* display line above the panel */}
      {title ? (
        <div
          style={{
            position: "absolute",
            left: 80,
            right: 80,
            top,
            height: 110,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: DISPLAY,
            fontSize: 62,
            letterSpacing: 2,
            textTransform: "uppercase",
            color: BRAND.paper,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
            opacity: clamp(panelP * 1.3),
            transform: `translateY(${(1 - panelP) * 20}px)`,
          }}
        >
          {title}
        </div>
      ) : null}

      {/* the glass panel */}
      <div
        style={{
          position: "absolute",
          left: panelX,
          top: panelY,
          width: panelW,
          height: panelH,
          ...glassChrome(34),
          transform: `translate3d(${driftX}px, ${driftY + (1 - panelP) * 30}px, 0) scale(${0.96 + panelP * 0.04})`,
          transformOrigin: "center top",
          opacity: clamp(panelP * 1.4),
        }}
      >
        <GlassInner
          t={t}
          x={panelX}
          y={panelY}
          w={panelW}
          h={panelH}
          accent={accent}
          ink={ink}
          sheen={sheenP}
          stageW={width}
          stageH={height}
        />

        {/* header row — pinned */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: "100%",
            height: headerH,
            display: "flex",
            alignItems: "stretch",
            background: rgba("#ffffff", 0.03),
            borderBottom: `1px solid ${rgba("#ffffff", 0.1)}`,
            opacity: headerP,
            transform: `translateY(${(1 - headerP) * 14}px)`,
          }}
        >
          <div style={{ width: labelW }} />
          {(["a", "b"] as const).map((c) => {
            const winner = loserCol !== "none" && loserCol !== c;
            return (
              <div
                key={c}
                style={{
                  width: colW,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  position: "relative",
                  borderLeft: `1px solid ${rgba("#ffffff", 0.07)}`,
                  opacity: colMul(c),
                }}
              >
                <span
                  style={{
                    fontSize: hdrSize,
                    fontWeight: 800,
                    letterSpacing: 3,
                    textTransform: "uppercase",
                    color: BRAND.paper,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    maxWidth: colW - cellPad * 2,
                  }}
                >
                  {c === "a" ? colA : colB}
                </span>
                {/* accent underline wipes in under the winning header */}
                {winner ? (
                  <div
                    style={{
                      position: "absolute",
                      left: "50%",
                      bottom: 16,
                      height: 5,
                      width: Math.min(colW - cellPad * 2, 220) * colP,
                      transform: "translateX(-50%)",
                      borderRadius: 3,
                      background: accent,
                      boxShadow: `0 0 18px ${rgba(accent, 0.7)}`,
                    }}
                  />
                ) : null}
              </div>
            );
          })}
          {/* the "vs" chip riding the A|B boundary */}
          <div
            style={{
              position: "absolute",
              left: labelW + colW - 27,
              top: headerH / 2 - 27,
              width: 54,
              height: 54,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 26,
              fontWeight: 800,
              color: rgba(BRAND.paper, 0.85),
              ...glassLite(27),
            }}
          >
            vs
          </div>
        </div>

        {/* rows — reveal top-down with settle */}
        {list.map((r, i) => {
          const rp = easeOut((t - rowAt(i)) / 0.5);
          if (rp <= 0) return null;
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: 0,
                top: headerH + i * rowH,
                width: "100%",
                height: rowH,
                display: "flex",
                alignItems: "stretch",
                background: i % 2 ? rgba("#ffffff", 0.02) : "transparent",
                borderBottom:
                  i < n - 1 ? `1px solid ${rgba("#ffffff", 0.05)}` : "none",
                opacity: rp,
                transform: `translateY(${(1 - rp) * 22}px)`,
              }}
            >
              <div
                style={{
                  width: labelW,
                  display: "flex",
                  alignItems: "center",
                  paddingLeft: 34,
                }}
              >
                <span
                  style={{
                    fontSize: 28,
                    fontWeight: 700,
                    letterSpacing: 2,
                    textTransform: "uppercase",
                    color: BRAND.mute,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    maxWidth: labelW - 50,
                  }}
                >
                  {r.label}
                </span>
              </div>
              {cell(r, i, "a")}
              {cell(r, i, "b")}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const vsTableDemo: VsTableProps = {
  title: "The difference",
  colA: "By hand",
  colB: "One command",
  rows: [
    { label: "setup", a: "hours", b: "45 sec", verdict: "b" },
    { label: "context", a: "you paste it", b: "reads the repo", verdict: "b" },
    { label: "agents", a: "just you", b: "60+ on call", verdict: "b" },
    { label: "review", a: "manual", b: "auto-checked", verdict: "b" },
  ],
  rowStagger: 0.5,
};
