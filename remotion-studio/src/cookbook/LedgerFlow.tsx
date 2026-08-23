import React from "react";
import {
  AbsoluteFill,
  OffthreadVideo,
  staticFile,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {
  BRAND, SANS, MONO, DISPLAY, rgba, clamp, Fonts, AuroraBed,
  glassChrome, glassLite, GlassInner, SAFE,
} from "./kit";
import { resolveBrand } from "./brandmarks";

/* =============================================================================
   LedgerFlow — a CONSERVED column of transaction rows that re-lays itself.

   Cookbook role: the missing "raw personal data arrives and gets organised"
   form. Everything else in the catalog either shows a FEW records inside device
   chrome (NotificationStack), CONSUMES records as it sifts (SwipeDeck), places
   unrelated facts in fixed tiles (BentoGrid), or frames real tape (ScreenStage).
   Nothing could draw 40-60 homogeneous ledger rows streaming with velocity
   smear, mask individual rows for PII, fog the rows outside an evidence
   bracket, and then flip the survivors into grouped lanes while CONSERVING row
   identity. New DataShape: "ledger".

   Why it exists (2026-08-20): the post-pivot franchise is "point Claude at your
   own mess". Every episode's payoff is therefore the same shape — a pile of the
   viewer's real records becoming a grouping. Four `phase` values are four
   re-layouts of ONE row set, so consecutive beats hand off with no visual cut:

     rush   the screenshots shatter into rows and stream past too fast to read,
            decelerating until merchant names resolve. The hook.
     floor  the column stops; a bracket is DRAWN around what was actually read
            and everything outside it fogs to placeholder bars. The honesty beat
            — the frame that admits the blind spot is the best-looking frame in
            the film, and it is also the frame that pays the first digit.
     sort   rows peel off, shrink to ticks and arc into category lanes. Masked
            rows never enter a lane; they exit through a gate. The mechanism.
     grow   one lane keeps receiving past its own rim and spills. The build.

   THE MASKED HUD is the spine across all four: a figure whose digits are
   plates that break open one at a time, so every beat pays the viewer something
   while the total stays withheld. `revealed` is the count of digits already
   shown at beat start; `revealAt` breaks exactly one more.

   HONESTY: this component is a DESIGNED RESTATEMENT of real data. Every row it
   draws must be a record that actually exists in the source. It never invents a
   transaction, and `masked` rows carry no merchant string at all — the identity
   is absent from the props, not merely hidden at render.

   Geometry constants below are duplicated verbatim in ShareSplit.tsx so the two
   can hand a rectangle to each other pixel-continuous. Change one, change both.

   JSON-safe: data only, no function props (build_ep_v2 feeds --props as JSON).
   Math.random is banned pipeline-wide (breaks resumability) — every "random"
   here is seeded off the row index via sin().
   ========================================================================== */

/* ---- shared geometry — MIRRORED IN ShareSplit.tsx. Keep in lockstep. ------ */
const COL_W = 872;
const COL_X = 104;
const ROW_H = 96;
const ROW_GAP = 12;
const PITCH = ROW_H + ROW_GAP; // 108
const ROW_R = 22;
const HUD_Y = 176;
const LANE_TOP = 1180;
const SAFE_BOTTOM = 1460; // karaoke caption band starts 1517 — never cross this
const CENTRE_Y = 960;
const WINDOW = 1200; // render only rows within this of centre (<=22 live nodes)

/* ---- easings, each named for its feel ------------------------------------ */
const easeOutQuint = (u: number) => 1 - Math.pow(clamp(u), 5) * 0; // placeholder guard
const eoq = (u: number) => 1 - Math.pow(1 - clamp(u), 5); // the decelerating rush
const eic = (u: number) => {
  const c = clamp(u);
  return c < 0.5 ? 4 * c * c * c : 1 - Math.pow(-2 * c + 2, 3) / 2; // the FLIP
};
const eiq = (u: number) => clamp(u) * clamp(u); // the shove-off
const eset = (u: number) => 1 - Math.pow(1 - clamp(u), 3.2); // glyph arrival
const SETTLE = Easing.bezier(0.2, 0.9, 0.25, 1);
void easeOutQuint;

/* ---- data ---------------------------------------------------------------- */
export type LedgerRow = {
  id: string;
  /** merchant as printed in the source. EMPTY STRING for masked rows — a
   *  person's name must never enter the props, let alone the repo. */
  merchant: string;
  amount: number;
  day?: string; // "14 AUG"
  cat?: string; // lane key
  masked?: boolean; // person-to-person: identity plated, amount visible
  counted?: boolean; // inside the evidence bracket -> may enter a lane
};

export type LedgerLane = {
  key: string;
  label: string;
  emoji?: string;
  tint?: string;
};

export type MaskedHud = {
  label: string; // "FOOD SO FAR" — a STATUS, never a taunt
  value: number; // the true figure
  revealed: number; // digits shown at beat start (0..len)
  revealAt?: number; // beat-local seconds at which ONE more digit breaks
  prefix?: string; // "₹ "
};

export type LedgerFlowProps = {
  rows: LedgerRow[]; // capped 60
  phase: "rush" | "floor" | "sort" | "grow";
  lanes?: LedgerLane[]; // capped 4
  /** drawn glass tiles the rows ingest out of — NOT photographs. */
  ingest?: { count: number; at?: number };
  scrollFrom?: number; // row-units — the continuity handoff between beats
  scrollTo?: number;
  focusLane?: string;
  bracket?: { from: number; to: number; label: string; ghostLabel: string };
  maskLabel?: string; // "PERSONAL — HIDDEN"
  skipLabel?: string; // "PERSONAL — SKIPPED"
  hud?: MaskedHud;
  tally?: { label: string; from: number; to: number }; // never resets across beats
  ghostGuess?: { value: number; label: string; killAt: number; prefix?: string };
  spill?: { atPct: number; releaseAt: number };
  counter?: { label: string; to: number; at?: number; roll?: number };
  handoff?: { w: number; h: number; at: number };
  footNote?: string;
  /** Sol's wide clip as a bottom-left PIP. Without this the designed beats
   *  cannot carry the host at all, and a 34s film ends up showing a face for
   *  two seconds — a graphics reel with a cameo. */
  host?: string;
  hostSize?: number;
  hostFrom?: number;
  /** Where the host sits. A bottom corner is the safe default, but these
   *  beats leave a large VOID in the upper frame once the rows depart — a
   *  small card in a busy corner while half the screen is empty is the worst
   *  of both. Anchor it into the dead space and size it up instead.
   *  bl/br = bottom, ml/mr = middle, tl/tr = top. */
  hostAnchor?: "bl" | "br" | "ml" | "mr" | "tl" | "tr";
  claimLines?: string[]; // capped 2 — the burned hook claim, riding over motion
  claimHot?: string;
  claimHold?: number;
  contentStart?: number;
  start?: number;
  accent?: string;
  ink?: string;
  transparent?: boolean;
  width?: number;
  height?: number;
};

/* ---- helpers ------------------------------------------------------------- */
const money = (n: number, prefix = "₹") =>
  prefix + n.toLocaleString("en-IN", { maximumFractionDigits: 0 });

/** deterministic pseudo-jitter — seeded off index, never Math.random. */
const jit = (i: number, k = 1) => Math.sin(i * 12.9898 + k * 4.1414);

/** the frosted identity plate. Never backdrop-filter: unreliable headless. */
const MaskPlate: React.FC<{ label: string; accent: string }> = ({
  label,
  accent,
}) => (
  <div style={{ display: "flex", alignItems: "center", gap: 16, flex: 1 }}>
    <div
      style={{
        width: 26,
        height: 26,
        borderRadius: 7,
        border: `2.5px solid ${rgba(BRAND.paper, 0.5)}`,
        borderBottomWidth: 13,
        boxSizing: "border-box",
      }}
    />
    <div style={{ display: "flex", flexDirection: "column", gap: 7, flex: 1 }}>
      {[196, 128, 84].map((w, k) => (
        <div
          key={k}
          style={{
            width: w,
            height: k === 0 ? 15 : 10,
            borderRadius: 6,
            background: rgba(BRAND.paper, 0.16 - k * 0.03),
          }}
        />
      ))}
    </div>
    <div
      style={{
        fontFamily: MONO,
        fontSize: 18,
        letterSpacing: 2,
        color: rgba(accent, 0.85),
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </div>
  </div>
);

/** One HUD digit: either the glyph, or a churning plate that can break open. */
const HudDigit: React.FC<{
  ch: string;
  shown: boolean;
  breaking: number; // 0 = closed plate, 1 = fully broken to glyph
  i: number;
  t: number;
  accent: string;
}> = ({ ch, shown, breaking, i, t, accent }) => {
  if (ch === ",") {
    return (
      <span style={{ fontFamily: DISPLAY, fontSize: 52, opacity: 0.6 }}>,</span>
    );
  }
  const open = shown || breaking >= 1;
  if (open) {
    // arrival: rotateX + horizontal squash settling out
    const u = breaking > 0 && breaking < 1 ? eset(breaking) : 1;
    return (
      <span
        style={{
          display: "inline-block",
          fontFamily: DISPLAY,
          fontSize: 52,
          lineHeight: "46px",
          fontVariantNumeric: "tabular-nums",
          transform: `perspective(420px) rotateX(${(1 - u) * -78}deg) scaleX(${
            1 + (1 - u) * 0.55
          })`,
          transformOrigin: "50% 100%",
        }}
      >
        {ch}
      </span>
    );
  }
  // closed plate: a strip of block glyphs scrolling behind a window
  const CELL = 46;
  const off = -(((t * 11 + i * 3.7) % 4) * CELL);
  const scan = ((t + i * 0.27) % 1.1) / 1.1;
  const squash = breaking > 0 ? 1 - clamp(breaking / 0.35) * 0.22 : 1;
  return (
    <span
      style={{
        position: "relative",
        display: "inline-block",
        width: 28,
        height: 46,
        borderRadius: 6,
        overflow: "hidden",
        background: rgba(accent, 0.14),
        border: `1.5px solid ${rgba(accent, 0.55)}`,
        boxSizing: "border-box",
        transform: `scaleY(${squash})`,
        verticalAlign: "top",
      }}
    >
      <span
        style={{
          position: "absolute",
          left: 0,
          top: off,
          fontFamily: MONO,
          fontSize: 30,
          lineHeight: `${CELL}px`,
          color: rgba(accent, 0.9),
          whiteSpace: "pre",
        }}
      >
        {"▮\n▨\n▤\n▥\n▮\n▨\n▤\n▥"}
      </span>
      <span
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: scan * 46,
          height: 2,
          background: rgba(accent, 0.8),
        }}
      />
    </span>
  );
};

/* ---- component ----------------------------------------------------------- */

/* ---- host PIP — geometry MIRRORED from ScreenStage.tsx so the host does not
   jump between a tape beat and a designed beat. Bottom-left, anchored at
   height-320 so its bottom sits at y=1600 regardless of size, which clears the
   Anton-54 caption band (~1650). Keep in lockstep with ScreenStage. ---------- */
const HostPip: React.FC<{
  host: string; hostSize: number; hostFrom: number; height: number;
  fps: number; anchor: string; width: number;
}> = ({ host, hostSize, hostFrom, height, fps, anchor, width }) => {
  const h = Math.round(hostSize * 0.5625);
  const right = anchor.endsWith("r");
  const band = anchor[0]; // b | m | t
  const top =
    band === "t" ? 300 : band === "m" ? Math.round(height * 0.32) : height - h - 320;
  return (
  <div
    style={{
      position: "absolute",
      left: right ? width - hostSize - 56 : 56,
      top,
      width: hostSize,
      height: h,
      borderRadius: 24,
      overflow: "hidden",
      border: `2px solid ${rgba("#ffffff", 0.5)}`,
      boxShadow: `0 26px 60px -18px ${rgba("#000", 0.85)}`,
    }}
  >
    <OffthreadVideo
      src={host.startsWith("http") ? host : staticFile(host)}
      startFrom={Math.round(hostFrom * fps)}
      muted
      style={{ width: "100%", height: "100%", objectFit: "cover" }}
    />
  </div>
  );
};

export const LedgerFlow: React.FC<LedgerFlowProps> = ({
  rows = [],
  phase = "rush",
  lanes = [],
  ingest,
  scrollFrom = 0,
  scrollTo = 0,
  focusLane,
  bracket,
  maskLabel = "PERSONAL — HIDDEN",
  skipLabel = "PERSONAL — SKIPPED",
  hud,
  tally,
  ghostGuess,
  spill,
  counter,
  handoff,
  footNote,
  host,
  hostSize = 300,
  hostFrom = 0,
  hostAnchor = "bl",
  claimLines,
  claimHot,
  claimHold = 2.2,
  contentStart = 0,
  start = 0,
  accent = BRAND.mag,
  ink = BRAND.ink,
  transparent,
  width = 1080,
  height = 1920,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = frame / fps - start;
  const dur = durationInFrames / fps - start;

  // survive empty/garbage props rather than crashing the whole render
  const R = (rows || []).slice(0, 60);
  const LN = (lanes || []).slice(0, 4);

  /* -- column scroll offset, per phase ------------------------------------ */
  let scroll = scrollFrom;
  let speed = 0;
  if (phase === "rush") {
    const u = clamp((t - 0.6) / Math.max(0.3, dur - 0.9));
    const uPrev = clamp((t - 1 / fps - 0.6) / Math.max(0.3, dur - 0.9));
    scroll = scrollFrom + (scrollTo - scrollFrom) * eoq(u);
    const prev = scrollFrom + (scrollTo - scrollFrom) * eoq(uPrev);
    speed = clamp(Math.abs(scroll - prev) * fps / 34);
  } else if (phase === "floor") {
    const u = clamp(t / 0.55);
    scroll = scrollFrom + (scrollTo - scrollFrom) * eoq(u);
  } else {
    // sort/grow: the column is being CONSUMED, so it must pull up as rows leave
    // or the top two thirds of the frame go empty and the beat reads dead.
    const nC = R.filter((r) => r.counted && !r.masked).length || 1;
    const fl = Math.max(0.9, dur - 1.35);
    const st = clamp(fl / nC, 0.03, 0.11);
    const departed = clamp((t - 0.22) / Math.max(0.3, nC * st)) * nC;
    scroll = (scrollTo || scrollFrom) + departed * 0.55;
  }
  // residual drift — nothing in this component is ever fully static
  const drift = PITCH * 0.06 * Math.sin(t * 0.9);

  /* -- ingest: drawn glass tiles shattering into rows --------------------- */
  const ingestAt = ingest?.at ?? 0;
  const shatter = clamp((t - ingestAt - 0.28) / 0.32); // 0..1 across the slice
  const showTiles = phase === "rush" && !!ingest && t < ingestAt + 0.62;

  /* -- HUD ---------------------------------------------------------------- */
  const hudDigits = hud ? String(hud.value).split("") : [];
  const revealAt = hud?.revealAt;
  const breaking =
    revealAt != null ? clamp((t - revealAt) / 0.42) : 0;
  const breakIdx = hud ? hud.revealed : -1;

  /* -- bracket (floor) ---------------------------------------------------- */
  const bDraw = clamp((t - 0.3) / 0.75);
  const bFrom = bracket?.from ?? 0;
  const bTo = bracket?.to ?? R.length;
  const bCentre = (bFrom + bTo) / 2;
  const bHalf = (bTo - bFrom) / 2;

  /* -- lanes -------------------------------------------------------------- */
  const laneX = (k: number) => COL_X + 26 + k * ((COL_W - 52) / Math.max(1, LN.length));
  const laneW = (COL_W - 52) / Math.max(1, LN.length) - 18;
  const counted = R.filter((r) => r.counted && !r.masked);
  const laneCount: Record<string, number> = {};
  LN.forEach((l) => (laneCount[l.key] = 0));
  // Departure cadence is derived from the beat, never fixed: with a fixed 38ms
  // stagger a 16-row set finished at 1.25s and left two thirds of a 3.7s beat
  // frozen — the exact failure that cost _style its QC pass.
  const nCounted = R.filter((r) => r.counted && !r.masked).length || 1;
  const flurry = Math.max(0.9, (phase === "sort" ? dur : 3.4) - 1.35);
  const step = clamp(flurry / nCounted, 0.03, 0.11);
  const sortDepart = (i: number) => 0.22 + i * step;
  counted.forEach((r, i) => {
    if (phase === "sort") {
      const arrived = t > sortDepart(i) + 0.42;
      if (arrived && r.cat && laneCount[r.cat] != null) laneCount[r.cat] += 1;
    } else if (phase === "grow") {
      // grow OPENS with the sort already complete — it is the build beat, not a
      // replay of the mechanism beat.
      if (r.cat && laneCount[r.cat] != null) laneCount[r.cat] += 1;
    }
  });

  /* -- ghost guess kill --------------------------------------------------- */
  const gk = ghostGuess ? clamp((t - ghostGuess.killAt) / 0.22) : 0;
  const gShove = ghostGuess ? clamp((t - ghostGuess.killAt - 0.22) / 0.5) : 0;

  /* -- claim -------------------------------------------------------------- */
  const cs = contentStart;
  const claimOp = claimLines?.length
    ? interpolate(t, [cs, cs + 0.18, cs + claimHold, cs + claimHold + 0.4], [0, 1, 1, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 0;

  /* -- handoff slab ------------------------------------------------------- */
  const hoU = handoff ? clamp((t - (dur - handoff.at)) / Math.max(0.2, handoff.at)) : 0;

  /* ---- row renderer ----------------------------------------------------- */
  const renderRow = (r: LedgerRow, i: number) => {
    const baseY = CENTRE_Y - ROW_H / 2 + (i - scroll) * PITCH + drift;

    // --- sort/grow: fly to a lane -------------------------------------
    let x = COL_X;
    let y = baseY;
    let w = COL_W;
    let h = ROW_H;
    let rot = 0;
    let tint = 0;
    let gone = false;

    if (phase === "sort" || phase === "grow") {
      const ci = counted.indexOf(r);
      if (r.masked) {
        // masked rows exit right through the gate, never entering a lane
        const mi = R.filter((q) => q.masked).indexOf(r);
        const dep = 0.22 + (R.indexOf(r)) * 0.038;
        const u = clamp((t - dep) / 0.5);
        x = COL_X + u * 1010;
        y = baseY;
        if (u >= 1) gone = true;
        void mi;
      } else if (ci >= 0) {
        const dep = sortDepart(ci);
        // in grow the flight is already over: u is pinned to 1 so every tick
        // starts where sort left it
        const u = phase === "grow" ? 1 : clamp((t - dep) / 0.42);
        const li = LN.findIndex((l) => l.key === r.cat);
        if (u > 0 && li >= 0) {
          const e = eic(u);
          const tickW = laneW - 24;
          const tx = laneX(li) + 12;
          const inLane = laneCount[r.cat!] ?? 0;
          const slotIdx = counted
            .slice(0, ci)
            .filter((q) => q.cat === r.cat).length;
          const isFocus = phase === "grow" && focusLane === r.cat;
          const COURSE = 15;
          const stackH = (slotIdx + 1) * COURSE;
          const ty = LANE_TOP - 26 - stackH;
          void isFocus;
          // quadratic bezier with a lateral control point
          const cx = (COL_X + tx) / 2 + (tx > COL_X ? 180 : -180);
          const cy = (baseY + ty) / 2 - 120;
          const mt = e;
          x =
            (1 - mt) * (1 - mt) * COL_X + 2 * (1 - mt) * mt * cx + mt * mt * tx;
          y =
            (1 - mt) * (1 - mt) * baseY + 2 * (1 - mt) * mt * cy + mt * mt * ty;
          w = COL_W + (tickW - COL_W) * e;
          h = ROW_H + (13 - ROW_H) * e;
          rot = jit(ci, 2) * 1.6 * e;
          tint = e;
          void inLane;
        }
      }
    }

    if (gone) return null;
    if (Math.abs(y - CENTRE_Y) > WINDOW && phase !== "sort" && phase !== "grow")
      return null;

    // --- floor fog ------------------------------------------------------
    let fog = 0;
    if (phase === "floor" && bracket) {
      const d = Math.abs(i - bCentre) - bHalf;
      const c = clamp(1 - d / 6);
      fog = 1 - c;
    }
    const bars = fog > 0.66;

    // --- rush velocity smear -------------------------------------------
    const useFilter = phase === "rush" && speed > 0.06;
    const lane = LN.find((l) => l.key === r.cat);

    return (
      <div
        key={r.id}
        style={{
          position: "absolute",
          left: x,
          top: y,
          width: w,
          height: h,
          // real glass, not a flat wash — glassLite because up to 22 rows are
          // live at once and a per-row refraction sample would crawl
          ...glassLite(
            tint > 0.5 ? 7 : ROW_R,
            tint > 0 ? lane?.tint : undefined,
            tint > 0.5 ? 2.1 : 1 - fog * 0.8
          ),
          // a lit rim on the settled ticks — without it a stack of slabs reads
          // as muddy olive rather than as coins catching light
          ...(tint > 0.5 && lane?.tint
            ? { boxShadow: `0 2px 10px -2px ${rgba("#000", 0.7)}, inset 0 1px 0 ${rgba("#fff", 0.55)}, 0 0 14px ${rgba(lane.tint, 0.45)}` }
            : {}),
          boxSizing: "border-box",
          display: "flex",
          alignItems: "center",
          gap: 22,
          padding: h > 40 ? "0 26px" : 0,
          overflow: "hidden",
          opacity: phase === "floor" ? 0.1 + (1 - fog) * 0.75 : 1,
          transform: `rotate(${rot}deg)${
            useFilter ? ` scaleY(${1 + speed * 0.14})` : ""
          }`,
          filter: useFilter
            ? `blur(${speed * 4.5}px)`
            : fog > 0.02
            ? `blur(${fog * 7}px) saturate(${1 - fog * 0.9})`
            : undefined,
        }}
      >
        {h < 40 ? null : bars ? (
          <>
            <div
              style={{
                width: 300,
                height: 16,
                borderRadius: 8,
                background: rgba(BRAND.paper, 0.13),
              }}
            />
            <div style={{ flex: 1 }} />
            <div
              style={{
                width: 120,
                height: 16,
                borderRadius: 8,
                background: rgba(BRAND.paper, 0.13),
              }}
            />
          </>
        ) : r.masked ? (
          <>
            <MaskPlate label={maskLabel} accent={accent} />
            <div
              style={{
                fontFamily: DISPLAY,
                fontSize: 38,
                fontVariantNumeric: "tabular-nums",
                color: BRAND.paper,
              }}
            >
              {money(r.amount)}
            </div>
          </>
        ) : (
          <>
            {(() => {
              // brandmarks.ts: licence-clean glyph where one exists, otherwise a
              // brand-coloured wordmark chip with NO logo reproduced.
              const b = resolveBrand(r.merchant);
              return (
                <div
                  style={{
                    width: 52,
                    height: 52,
                    borderRadius: 26,
                    flex: "none",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    background: rgba(b.hex, 0.2),
                    border: `1px solid ${rgba(b.hex, 0.55)}`,
                    boxShadow: `inset 0 1px 0 ${rgba("#fff", 0.28)}`,
                  }}
                >
                  {b.kind === "glyph" && b.d ? (
                    <svg viewBox="0 0 24 24" width={28} height={28} fill={b.hex}>
                      <path d={b.d} />
                    </svg>
                  ) : (
                    <span style={{ fontFamily: SANS, fontSize: 26, fontWeight: 800, color: b.hex }}>
                      {(r.merchant || "?").charAt(0).toUpperCase()}
                    </span>
                  )}
                </div>
              );
            })()}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontFamily: SANS,
                  fontSize: 34,
                  fontWeight: 600,
                  color: BRAND.paper,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {r.merchant}
              </div>
              {r.day ? (
                <div
                  style={{
                    fontFamily: MONO,
                    fontSize: 20,
                    color: rgba(BRAND.paper, 0.45),
                    marginTop: 3,
                  }}
                >
                  {r.day}
                </div>
              ) : null}
            </div>
            <div
              style={{
                fontFamily: DISPLAY,
                fontSize: 40,
                fontVariantNumeric: "tabular-nums",
                color: BRAND.paper,
              }}
            >
              {money(r.amount)}
            </div>
          </>
        )}
      </div>
    );
  };

  /* ---- draw ------------------------------------------------------------- */
  return (
    <AbsoluteFill style={{ width, height, background: transparent ? undefined : ink }}>
      <Fonts />
      {transparent ? null : <AuroraBed t={t} accent={accent} ink={ink} opacity={0.32} />}

      {/* ---- the column -------------------------------------------------- */}
      <AbsoluteFill style={{ opacity: hoU > 0 ? 1 - hoU : 1 }}>
        {R.map(renderRow)}
      </AbsoluteFill>

      {/* ---- bottom fade: the karaoke caption owns everything below
          SAFE.captionCeil, so rows dissolve INTO it rather than fighting it.
          Without this the column runs straight through the caption band and
          both become unreadable — visible only once composited. */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: SAFE.captionCeil - 260,
          height: 1920 - (SAFE.captionCeil - 260),
          background: `linear-gradient(180deg, ${rgba(ink, 0)} 0%, ${rgba(
            ink,
            0.9
          )} 30%, ${rgba(ink, 0.99)} 55%, ${rgba(ink, 1)} 100%)`,
          pointerEvents: "none",
        }}
      />

      {/* ---- ingest tiles (rush only) ------------------------------------ */}
      {showTiles
        ? Array.from({ length: Math.min(4, ingest!.count) }).map((_, k) => {
            const sp = spring({
              frame: frame - Math.round((ingestAt + k * 0.06) * fps),
              fps,
              config: { damping: 14, stiffness: 150 },
            });
            const ang = (k - (ingest!.count - 1) / 2) * 7;
            return (
              <div
                key={k}
                style={{
                  position: "absolute",
                  left: 540 - 120 + (k - (ingest!.count - 1) / 2) * 150,
                  top: 760 - 215,
                  width: 240,
                  height: 430,
                  ...glassLite(28, undefined, 1.15),
                  padding: 16,
                  display: "flex",
                  flexDirection: "column",
                  gap: 9,
                  transform: `rotate(${ang}deg) scale(${sp}) translateY(${
                    (1 - sp) * 60
                  }px)`,
                  opacity: sp * (1 - shatter),
                }}
              >
                {/* a screenshot's SHAPE, not its content — a title bar and rows */}
                <div
                  style={{
                    height: 20,
                    width: "58%",
                    borderRadius: 5,
                    background: rgba(BRAND.paper, 0.4),
                    marginBottom: 6,
                  }}
                />
                {Array.from({ length: 7 }).map((_, r) => (
                  <div
                    key={r}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      opacity: 0.9 - r * 0.07,
                    }}
                  >
                    <div style={{ width: 22, height: 22, borderRadius: 11, background: rgba(accent, 0.5) }} />
                    <div style={{ flex: 1, height: 11, borderRadius: 5, background: rgba(BRAND.paper, 0.26) }} />
                    <div
                      style={{
                        width: 34 + ((r * 13) % 22),
                        height: 11,
                        borderRadius: 5,
                        background: rgba(BRAND.paper, 0.42),
                      }}
                    />
                  </div>
                ))}
              </div>
            );
          })
        : null}

      {/* ---- evidence bracket (floor) ------------------------------------ */}
      {phase === "floor" && bracket ? (
        <>
          {(() => {
            const top = CENTRE_Y - ROW_H / 2 + (bFrom - scroll) * PITCH + drift - 14;
            const bot = CENTRE_Y - ROW_H / 2 + (bTo - scroll) * PITCH + drift + 14;
            const armT = clamp((bDraw - 0.0) / 0.33);
            const armL = clamp((bDraw - 0.33) / 0.33);
            const armB = clamp((bDraw - 0.66) / 0.34);
            return (
              <>
                <div
                  style={{
                    position: "absolute",
                    left: COL_X - 18,
                    top,
                    width: (COL_W + 36) * armT,
                    height: 4,
                    background: BRAND.cyan,
                    boxShadow: `0 0 18px ${rgba(BRAND.cyan, 0.9)}`,
                    borderRadius: 2,
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    left: COL_X - 18,
                    top,
                    width: 4,
                    height: (bot - top) * armL,
                    background: BRAND.cyan,
                    boxShadow: `0 0 18px ${rgba(BRAND.cyan, 0.9)}`,
                    borderRadius: 2,
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    left: COL_X - 18,
                    top: bot,
                    width: (COL_W + 36) * armB,
                    height: 4,
                    background: BRAND.cyan,
                    boxShadow: `0 0 18px ${rgba(BRAND.cyan, 0.9)}`,
                    borderRadius: 2,
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    left: COL_X - 18,
                    top: top - 46,
                    fontFamily: MONO,
                    fontSize: 24,
                    letterSpacing: 6,
                    color: BRAND.cyan,
                    textShadow: `0 0 20px ${rgba(BRAND.cyan, 0.8)}`,
                    opacity: clamp((bDraw - 0.4) / 0.3),
                  }}
                >
                  {bracket.label}
                </div>
                <div
                  style={{
                    position: "absolute",
                    left: COL_X,
                    width: COL_W,
                    textAlign: "right",
                    top: bot + 40,
                    fontFamily: MONO,
                    fontSize: 22,
                    color: rgba(BRAND.paper, 0.4),
                    opacity: clamp((bDraw - 0.6) / 0.3),
                  }}
                >
                  {bracket.ghostLabel}
                </div>
              </>
            );
          })()}
        </>
      ) : null}

      {/* ---- lanes (sort / grow) ----------------------------------------- */}
      {(phase === "sort" || phase === "grow") && LN.length
        ? LN.map((l, k) => {
            const sp = spring({
              frame: frame - Math.round(k * 0.05 * fps),
              fps,
              config: { damping: 16, stiffness: 120 },
            });
            const isFocus = phase === "grow" && focusLane === l.key;
            const dim = phase === "grow" && !isFocus;
            const n = laneCount[l.key] ?? 0;
            const stackH = n * (isFocus ? 12 : 10);
            const rimY = LANE_TOP - 80;
            const capY = rimY - (spill ? (SAFE_BOTTOM - LANE_TOP) * 0 : 0);
            void capY;
            const breathe = 1 + Math.sin(t * 3.4 + k) * 0.0035;
            return (
              <div key={l.key}>
                {/* the stack */}
                <div
                  style={{
                    position: "absolute",
                    left: laneX(k),
                    top: rimY + 44,
                    width: laneW,
                    height: 6,
                    borderRadius: 10,
                    background: rgba(l.tint ?? accent, isFocus ? 0.55 : 0.3),
                    boxShadow: isFocus
                      ? `0 0 ${40 + n}px ${rgba(l.tint ?? accent, 0.5)}`
                      : undefined,
                    opacity: dim ? 0.28 : 1,
                  }}
                />
                {/* capacity rule */}
                {spill ? (
                  <div
                    style={{
                      position: "absolute",
                      left: laneX(k) - 6,
                      top: rimY - (SAFE_BOTTOM - LANE_TOP) * spill.atPct,
                      width: laneW + 12,
                      height: 0,
                      borderTop: `2px dashed ${rgba(accent, 0.75)}`,
                      opacity: dim ? 0.25 : 1,
                    }}
                  />
                ) : null}
                {/* chip */}
                <div
                  style={{
                    position: "absolute",
                    left: laneX(k),
                    top: LANE_TOP - (isFocus ? 18 : 0),
                    width: laneW,
                    height: 72,
                    ...glassLite(18, isFocus ? l.tint ?? accent : undefined, isFocus ? 1.25 : 0.9),
                    boxSizing: "border-box",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 10,
                    transform: `scale(${sp * breathe})`,
                    opacity: dim ? 0.28 : sp,
                  }}
                >
                  <span style={{ fontSize: 26 }}>{l.emoji}</span>
                  <span
                    style={{
                      fontFamily: MONO,
                      fontSize: 20,
                      letterSpacing: 2,
                      color: BRAND.paper,
                    }}
                  >
                    {l.label}
                  </span>
                  <span
                    style={{
                      fontFamily: DISPLAY,
                      fontSize: 28,
                      fontVariantNumeric: "tabular-nums",
                      color: isFocus ? l.tint ?? accent : BRAND.paper,
                    }}
                  >
                    {n}
                  </span>
                </div>
              </div>
            );
          })
        : null}

      {/* ---- exit gate for masked rows ----------------------------------- */}
      {phase === "sort" ? (
        <div
          style={{
            position: "absolute",
            left: 1010,
            top: 300,
            width: 3,
            height: 1000,
            background: rgba(accent, 0.5),
          }}
        />
      ) : null}

      {/* ---- ghost guess -------------------------------------------------- */}
      {ghostGuess && phase === "sort" ? (
        <div
          style={{
            position: "absolute",
            left: 60 - gShove * 620,
            top: 620,
            opacity: 0.3 * (1 - gShove),
            transform: `rotate(-4deg)`,
          }}
        >
          <div
            style={{
              position: "relative",
              fontFamily: DISPLAY,
              fontSize: 120,
              color: BRAND.paper,
              lineHeight: "110px",
            }}
          >
            {money(ghostGuess.value, ghostGuess.prefix ?? "₹")}
            <div
              style={{
                position: "absolute",
                left: 0,
                top: "52%",
                height: 4,
                width: `${gk * 100}%`,
                background: accent,
              }}
            />
          </div>
          <div
            style={{
              fontFamily: MONO,
              fontSize: 24,
              letterSpacing: 5,
              color: rgba(BRAND.paper, 0.7),
              marginTop: 6,
            }}
          >
            {ghostGuess.label}
          </div>
        </div>
      ) : null}

      {/* ---- HUD ----------------------------------------------------------
          The column is full-width, so without a ground of its own the masked
          readout lands directly on row amounts — two tabular numbers fighting
          in the same 200px. The scrim is the fix, and it doubles as the top
          vignette that keeps rows from colliding with the safe-area edge. */}
      {hud ? (
        <>
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: 0,
            height: 300,
            background: `linear-gradient(180deg, ${rgba(ink, 0.85)} 0%, ${rgba(
              ink,
              0.45
            )} 62%, ${rgba(ink, 0)} 100%)`,
          }}
        />
        <div
          style={{
            position: "absolute",
            right: 76,
            top: HUD_Y - 26,
            textAlign: "right",
            padding: "18px 26px 20px",
            ...glassChrome(26, 1.1),
            transform: `scale(${
              1 + (breaking > 0 && breaking < 1 ? Math.sin(breaking * Math.PI) * 0.04 : 0)
            })`,
          }}
        >
          <GlassInner
            t={t}
            x={width - 76 - 300}
            y={HUD_Y - 26}
            w={300}
            h={170}
            accent={accent}
            ink={ink}
            sheen={((t * 0.32) % 1)}
          />
          <div
            style={{
              position: "relative",
              fontFamily: MONO,
              fontSize: 20,
              letterSpacing: 5,
              color: rgba(BRAND.paper, 0.55),
            }}
          >
            {hud.label}
          </div>
          <div
            style={{
              position: "relative",
              display: "flex",
              gap: 4,
              alignItems: "flex-end",
              justifyContent: "flex-end",
              marginTop: 6,
              color: BRAND.paper,
            }}
          >
            <span style={{ fontFamily: DISPLAY, fontSize: 52, opacity: 0.8 }}>
              {hud.prefix ?? "₹"}
            </span>
            {hudDigits.map((ch, i) => (
              <HudDigit
                key={i}
                ch={ch}
                i={i}
                t={t}
                accent={accent}
                shown={i < breakIdx}
                breaking={i === breakIdx ? breaking : 0}
              />
            ))}
          </div>
          {tally ? (
            <div style={{ position: "relative", marginTop: 14 }}>
              <span
                style={{
                  fontFamily: MONO,
                  fontSize: 20,
                  letterSpacing: 4,
                  color: rgba(BRAND.paper, 0.45),
                  marginRight: 10,
                }}
              >
                {tally.label}
              </span>
              <span
                style={{
                  fontFamily: DISPLAY,
                  fontSize: 34,
                  fontVariantNumeric: "tabular-nums",
                  color: BRAND.paper,
                }}
              >
                {Math.round(
                  tally.from + (tally.to - tally.from) * eoq(clamp(t / Math.min(dur, 2.4)))
                )}
              </span>
            </div>
          ) : null}
        </div>
        </>
      ) : null}

      {/* ---- big counter (grow) ------------------------------------------- */}
      {counter && phase === "grow" ? (
        <div
          style={{
            position: "absolute",
            left: COL_X,
            top: 700,
            display: "flex",
            alignItems: "baseline",
            gap: 18,
            opacity: clamp((t - (counter.at ?? 0)) / 0.3),
          }}
        >
          <span
            style={{
              fontFamily: DISPLAY,
              fontSize: 128,
              fontVariantNumeric: "tabular-nums",
              color: BRAND.paper,
              lineHeight: "112px",
            }}
          >
            {Math.round(counter.to * eoq(clamp((t - (counter.at ?? 0)) / (counter.roll ?? 1.6))))}
          </span>
          <span
            style={{
              fontFamily: MONO,
              fontSize: 30,
              letterSpacing: 6,
              color: accent,
            }}
          >
            {counter.label}
          </span>
        </div>
      ) : null}

      {/* ---- footnote (dead space, never over content) --------------------- */}
      {footNote ? (
        <div
          style={{
            position: "absolute",
            left: COL_X,
            top: SAFE.captionCeil - 96,
            padding: "13px 24px",
            ...glassChrome(14, 0.8),
            background: rgba(ink, 0.96),
            fontFamily: MONO,
            fontSize: 22,
            letterSpacing: 2,
            color: rgba(BRAND.paper, 0.62),
            opacity: clamp((t - 1.2) / 0.4),
          }}
        >
          {footNote}
        </div>
      ) : null}

      {/* ---- burned claim, riding over the motion --------------------------
          The claim shares the top band with the HUD, so it is width-capped to
          the left 58% and sits on its own scrim. Without both, the headline
          crosses the masked readout and the first rows — the exact "chip over
          taught content" failure the channel banned. */}
      {claimLines?.length ? (
        <>
          <div
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              top: 0,
              height: 470,
              background: `linear-gradient(180deg, ${rgba(ink, 0.92)} 0%, ${rgba(
                ink,
                0.72
              )} 58%, ${rgba(ink, 0)} 100%)`,
              opacity: claimOp,
            }}
          />
        <div
          style={{
            position: "absolute",
            left: COL_X,
            width: 600,
            top: SAFE.headerFloor + 26,
            opacity: claimOp,
          }}
        >
          {claimLines.slice(0, 2).map((ln, i) => (
            <div
              key={i}
              style={{
                fontFamily: DISPLAY,
                fontSize: 88,
                lineHeight: "86px",
                color: BRAND.paper,
                textShadow: `0 6px 40px ${rgba(ink, 0.9)}`,
              }}
            >
              {ln.split(" ").map((wd, k) => (
                <span
                  key={k}
                  style={{
                    color:
                      claimHot && wd.replace(/[^A-Za-z]/g, "").toUpperCase() ===
                      claimHot.toUpperCase()
                        ? accent
                        : undefined,
                  }}
                >
                  {wd}{" "}
                </span>
              ))}
            </div>
          ))}
        </div>
        </>
      ) : null}

      {/* ---- handoff slab: collapse to the rectangle ShareSplit reopens ---- */}
      {handoff && hoU > 0 ? (
        <div
          style={{
            position: "absolute",
            left: 540 - handoff.w / 2,
            top: 960 - handoff.h / 2,
            width: handoff.w,
            height: handoff.h,
            borderRadius: 40,
            background: `linear-gradient(160deg, ${rgba(accent, 0.3)}, ${rgba(
              accent,
              0.12
            )})`,
            border: `1px solid ${rgba(BRAND.paper, 0.25)}`,
            opacity: hoU,
            transform: `scale(${0.94 + hoU * 0.06})`,
          }}
        />
      ) : null}
      {host ? (
        <HostPip host={host} hostSize={hostSize} hostFrom={hostFrom}
                 height={height} fps={fps} anchor={hostAnchor} width={width} />
      ) : null}
    </AbsoluteFill>
  );
};

/* ---- canonical demo payload (the QC harness props) ----------------------- */
const DEMO_ROWS: LedgerRow[] = [
  { id: "r1", merchant: "Swiggy", amount: 487, day: "18 AUG", cat: "food", counted: true },
  { id: "r2", merchant: "", amount: 500, day: "18 AUG", masked: true },
  { id: "r3", merchant: "Zomato", amount: 612, day: "17 AUG", cat: "food", counted: true },
  { id: "r4", merchant: "BigBasket", amount: 1240, day: "17 AUG", cat: "shop", counted: true },
  { id: "r5", merchant: "Amazon", amount: 2199, day: "16 AUG", cat: "shop", counted: true },
  { id: "r6", merchant: "Swiggy", amount: 356, day: "16 AUG", cat: "food", counted: true },
  { id: "r7", merchant: "Airtel", amount: 399, day: "15 AUG", cat: "bills", counted: true },
  { id: "r8", merchant: "Blinkit", amount: 278, day: "15 AUG", cat: "shop", counted: true },
  { id: "r9", merchant: "Swiggy", amount: 521, day: "14 AUG", cat: "food", counted: true },
  { id: "r10", merchant: "Uber", amount: 184, day: "14 AUG", cat: "rides", counted: true },
  { id: "r11", merchant: "Zomato", amount: 438, day: "13 AUG", cat: "food", counted: true },
  { id: "r12", merchant: "", amount: 1200, day: "13 AUG", masked: true },
  { id: "r13", merchant: "Swiggy", amount: 402, day: "12 AUG", cat: "food", counted: true },
  { id: "r14", merchant: "Zepto", amount: 315, day: "12 AUG", cat: "shop", counted: true },
  { id: "r15", merchant: "BookMyShow", amount: 700, day: "11 AUG", cat: "rides", counted: true },
  { id: "r16", merchant: "Swiggy", amount: 289, day: "11 AUG", cat: "food", counted: true },
  { id: "r17", merchant: "Amazon", amount: 549, day: "10 AUG", cat: "shop", counted: true },
  { id: "r18", merchant: "Zomato", amount: 526, day: "10 AUG", cat: "food", counted: true },
];

const DEMO_LANES: LedgerLane[] = [
  { key: "food", label: "FOOD", emoji: "🍽", tint: "#FC8019" },
  { key: "rides", label: "RIDES", emoji: "🛺", tint: "#2B2B2B" },
  { key: "shop", label: "SHOPPING", emoji: "🛍", tint: "#FF9900" },
  { key: "bills", label: "BILLS", emoji: "🧾", tint: "#E40000" },
];

export const ledgerFlowDemo: LedgerFlowProps = {
  rows: DEMO_ROWS,
  lanes: DEMO_LANES,
  phase: "rush",
  ingest: { count: 3, at: 0 },
  scrollFrom: 0,
  scrollTo: 14,
  hud: { label: "FOOD SO FAR", value: 4212, revealed: 0, prefix: "₹ " },
  tally: { label: "ROWS READ", from: 0, to: 61 },
  claimLines: ["I SCREENSHOTTED", "MY UPI HISTORY"],
  claimHot: "UPI",
  contentStart: 0.37,
  claimHold: 2.15,
};
