import React from "react";
import {
  AbsoluteFill,
  OffthreadVideo,
  staticFile,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {
  BRAND,
  SANS,
  MONO,
  DISPLAY,
  rgba,
  clamp,
  Fonts,
  AuroraBed,
  glassChrome,
  glassLite,
  GlassInner,
  SAFE,
} from "./kit";

/* =============================================================================
   ShareSplit — one total, decomposed into its share of a larger whole.

   Cookbook role: the PAYOFF form. RingGauge draws up to three INDEPENDENT
   percentages as radial rings, each conjured from nothing and unrelated to the
   others. Odometer rolls one number with no relationship to any whole.
   LineReveal is a trend. GlassPanel presents a figure with supporting rows but
   never decomposes it. Nothing in the catalog draws PART-OF-WHOLE as a single
   object splitting — and, the part that actually matters, nothing REBUILDS the
   part out of the countable atoms that produced it, which is the only way a
   share feels earned instead of asserted. New DataShape: "part-whole".

   It is also the only component designed to open PIXEL-CONTINUOUS with another
   component's closing rectangle (`openFrost`), which is what lets a preceding
   beat hand a number across without a cut. LedgerFlow#grow collapses its ticks
   into a slab of exactly `handoff.w x handoff.h`; ShareSplit opens on the same
   rectangle and lifts the total out of it.

   THE ONE HARD FRAME: the bar splits with NO easing. Everything else in this
   file breathes, drifts and settles; the cut is instantaneous. That contrast is
   the whole point — a payoff that eases in has no moment, and this component
   exists to produce exactly one.

   THE `>=` TWIST: optionally, late, the number slides right to accept a
   relational operator and a word types in underneath, while blurred ghost bars
   fade up behind to stand for everything that was never counted. This is the
   honesty beat as a craft beat: the film's last move is to tell you the number
   is still too low.

   JSON-safe: data only, no function props. Math.random is banned pipeline-wide.
   Geometry constants are MIRRORED from LedgerFlow.tsx — change one, change both.
   ========================================================================== */

/* ---- shared geometry — MIRRORED IN LedgerFlow.tsx. Keep in lockstep. ------ */
const COL_W = 872;
const COL_X = 104;
const SAFE_BOTTOM = 1460;

/* ---- easings ------------------------------------------------------------- */
const eoq = (u: number) => 1 - Math.pow(1 - clamp(u), 5); // the settle
const eset = (u: number) => 1 - Math.pow(1 - clamp(u), 3.2); // glyph arrival
const eio = (u: number) => {
  const c = clamp(u);
  return c < 0.5 ? 4 * c * c * c : 1 - Math.pow(-2 * c + 2, 3) / 2;
};

export type ShareSplitProps = {
  /** the hero figure — the PART. */
  total: { value: number; label: string; prefix?: string; sub?: string };
  /** what it is a share OF. */
  whole: { value: number; label: string };
  /** how many countable atoms rebuild the part (0 = solid fill). */
  atoms?: number;
  /** a WORD fraction — "ONE THIRD OF THESE SCREENSHOTS", never "33%". A word
   *  fraction is honest about precision the source cannot support. */
  shareLabel?: string;
  /** open pixel-continuous with the previous component's closing rectangle. */
  openFrost?: { w: number; h: number; dur?: number };
  /** beat-local seconds of the one un-eased cut. */
  splitAt?: number;
  /** the late relational twist: the number was always a floor. */
  atLeast?: { at: number; word: string; note?: string };
  /** blurred bars behind, standing for what was never counted. */
  ghostBars?: number;
  /** Nothing is drawn below this y. A karaoke line can run to FOUR rows on a
   *  long sentence, which reaches up to y=1212 — far above the 1580 caption
   *  ceiling this component was built against. Pass the real floor. */
  capSafe?: number;
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
  /** What the REMAINDER is made of. Without this the grey side is an anonymous
   *  block and the viewer learns only "the part is big"; with it they learn
   *  what it beat. Segments are drawn proportionally inside the remainder and
   *  settle after the cut, so the split still reads as one hard frame. */
  wholeParts?: { label: string; value: number; tint?: string }[];
  /** Fogline-style run header — the dot + label that names what produced this. */
  runLabel?: string;
  /** Fogline-style labelled micro-columns. This is the library's fine-detail
   *  idiom: small MONO labels over tabular values, carrying the provenance of
   *  the hero number so the payoff is auditable at a glance rather than asserted. */
  meta?: { k: string; v: string }[];
  accent?: string;
  ink?: string;
  transparent?: boolean;
  start?: number;
  width?: number;
  height?: number;
};

const money = (n: number, prefix = "₹") =>
  prefix + n.toLocaleString("en-IN", { maximumFractionDigits: 0 });

/** deterministic jitter, seeded off index. */
const jit = (i: number) => Math.sin(i * 12.9898 + 4.1414);


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

export const ShareSplit: React.FC<ShareSplitProps> = ({
  total,
  whole,
  atoms = 0,
  shareLabel,
  openFrost,
  splitAt = 1.15,
  atLeast,
  ghostBars = 0,
  capSafe = 1580,
  host,
  hostSize = 300,
  hostFrom = 0,
  hostAnchor = "bl",
  wholeParts,
  runLabel,
  meta,
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

  // survive missing props rather than crashing the render
  const TOT = total ?? { value: 0, label: "" };
  const WHOLE = whole ?? { value: 1, label: "" };
  const share = clamp(TOT.value / Math.max(1, WHOLE.value), 0.04, 1);

  /* -- the frosted handoff rectangle the total lifts out of ---------------- */
  const openDur = openFrost?.dur ?? 0.5;
  const open = openFrost ? clamp(t / openDur) : 1;

  /* -- the hero number ----------------------------------------------------- */
  const lift = spring({
    frame: frame - Math.round((start + openDur * 0.55) * fps),
    fps,
    config: { damping: 17, mass: 0.9, stiffness: 95 },
  });
  const rollU = eoq(clamp((t - openDur * 0.55) / 1.0));
  const shown = Math.round(TOT.value * rollU);

  /* -- THE ONE HARD FRAME -------------------------------------------------- */
  // deliberately NOT eased and NOT sprung: the cut is a step function.
  const cut = t >= splitAt ? 1 : 0;
  const sinceCut = t - splitAt;
  // after the cut the two sides separate, and THAT settles.
  const part = eio(clamp(sinceCut / 0.42));
  const GAP = 26;

  /* -- atoms rebuilding the part ------------------------------------------ */
  const atomsIn = clamp((sinceCut - 0.18) / 0.75);

  /* -- the >= twist -------------------------------------------------------- */
  const alU = atLeast ? clamp((t - atLeast.at) / 0.5) : 0;
  const alType = atLeast ? clamp((t - atLeast.at - 0.28) / 0.6) : 0;
  const ghostU = atLeast ? clamp((t - atLeast.at - 0.15) / 0.9) : 0;

  /* -- bar geometry -------------------------------------------------------- */
  const BAR_Y = Math.min(1052, capSafe - 300);
  const BAR_H = 132;
  const partW = COL_W * share;
  const restW = COL_W - partW;
  const partX = COL_X - part * (GAP * 0.5);
  const restX = COL_X + partW + part * (GAP * 0.5);

  const heroY = Math.min(700, capSafe - 640) - (1 - lift) * 40;
  const heroSlide = alU * 78; // the number slides right to accept the operator

  return (
    <AbsoluteFill style={{ width, height, background: transparent ? undefined : ink }}>
      <Fonts />
      {transparent ? null : <AuroraBed t={t} accent={accent} ink={ink} opacity={0.32} />}

      {/* ---- ghost bars: everything that was never counted ----------------- */}
      {ghostBars > 0 && ghostU > 0
        ? Array.from({ length: Math.min(6, ghostBars) }).map((_, i) => {
            const w = COL_W * (0.42 + Math.abs(jit(i)) * 0.5);
            return (
              <div
                key={i}
                style={{
                  position: "absolute",
                  left: COL_X,
                  top: BAR_Y - 150 - i * 26,
                  width: w,
                  height: 18,
                  borderRadius: 9,
                  background: rgba(BRAND.paper, 0.3),
                  filter: `blur(${5 + i * 1.6}px)`,
                  opacity: ghostU * (0.62 - i * 0.07),
                  transform: `translateY(${(1 - ghostU) * 22}px)`,
                }}
              />
            );
          })
        : null}

      {/* ---- run header + labelled micro-columns (Fogline's detail idiom) --- */}
      {runLabel ? (
        <div
          style={{
            position: "absolute",
            left: COL_X,
            top: SAFE.headerFloor + 18,
            display: "flex",
            alignItems: "center",
            gap: 14,
            opacity: clamp(lift * 1.4),
          }}
        >
          <div
            style={{
              width: 14,
              height: 14,
              borderRadius: 7,
              background: accent,
              boxShadow: `0 0 18px ${rgba(accent, 0.9)}`,
            }}
          />
          <div
            style={{
              fontFamily: MONO,
              fontSize: 26,
              letterSpacing: 4,
              color: BRAND.paper,
            }}
          >
            {runLabel}
          </div>
        </div>
      ) : null}
      {meta?.length ? (
        <div
          style={{
            position: "absolute",
            left: COL_X,
            right: COL_X,
            top: SAFE.headerFloor + 64,
            display: "flex",
            gap: 40,
            fontFamily: MONO,
            fontVariantNumeric: "tabular-nums",
            opacity: clamp(lift * 1.4),
          }}
        >
          {meta.slice(0, 4).map((m, i) => (
            <div key={m.k}>
              <div
                style={{ fontSize: 16, letterSpacing: 2, color: rgba(BRAND.paper, 0.36) }}
              >
                {m.k}
              </div>
              <div
                style={{
                  fontSize: 30,
                  fontWeight: 700,
                  marginTop: 3,
                  color: i === meta.length - 1 ? accent : BRAND.paper,
                }}
              >
                {m.v}
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {/* ---- the handoff frost, which the total lifts out of ---------------- */}
      {openFrost && open < 1 ? (
        <div
          style={{
            position: "absolute",
            left: 540 - openFrost.w / 2,
            top: 960 - openFrost.h / 2,
            width: openFrost.w,
            height: openFrost.h,
            ...glassChrome(40, 1.2),
            opacity: 1 - eoq(open),
            transform: `scale(${1 + eoq(open) * 0.06})`,
          }}
        >
          <GlassInner
            t={t}
            x={540 - openFrost.w / 2}
            y={960 - openFrost.h / 2}
            w={openFrost.w}
            h={openFrost.h}
            accent={accent}
            ink={ink}
          />
        </div>
      ) : null}

      {/* ---- hero number ---------------------------------------------------- */}
      <div
        style={{
          position: "absolute",
          left: COL_X,
          top: heroY,
          opacity: clamp(lift * 1.3),
          transform: `translateY(${(1 - lift) * 46}px)`,
        }}
      >
        <div
          style={{
            fontFamily: MONO,
            fontSize: 24,
            letterSpacing: 6,
            color: rgba(BRAND.paper, 0.55),
            marginBottom: 8,
          }}
        >
          {TOT.label}
        </div>
        <div style={{ display: "flex", alignItems: "flex-end", gap: 10 }}>
          {/* the operator that arrives late and re-frames everything above it */}
          {atLeast ? (
            <span
              style={{
                // Anton carries no U+2265 — it rendered as a clipped shape.
                // MONO has it, and the weight difference reads as intentional.
                fontFamily: MONO,
                fontWeight: 700,
                fontSize: 96,
                lineHeight: "104px",
                color: accent,
                opacity: alU,
                transform: `translateX(${(1 - eset(alU)) * -30}px) scale(${
                  0.7 + eset(alU) * 0.3
                })`,
                transformOrigin: "100% 100%",
              }}
            >
              ≥
            </span>
          ) : null}
          <span
            style={{
              fontFamily: DISPLAY,
              fontSize: 168,
              lineHeight: "150px",
              color: BRAND.paper,
              fontVariantNumeric: "tabular-nums",
              transform: `translateX(${atLeast ? 0 : heroSlide}px)`,
              textShadow: `0 10px 60px ${rgba(accent, 0.35)}`,
            }}
          >
            {money(shown, TOT.prefix ?? "₹")}
          </span>
        </div>
        {TOT.sub ? (
          <div
            style={{
              fontFamily: SANS,
              fontSize: 34,
              color: rgba(BRAND.paper, 0.7),
              marginTop: 10,
            }}
          >
            {TOT.sub}
          </div>
        ) : null}
      </div>

      {/* ---- THE BAR ------------------------------------------------------- */}
      {/* before the cut: one object. after: two, and they never rejoin. */}
      <div
        style={{
          position: "absolute",
          left: partX,
          top: BAR_Y,
          width: partW,
          height: BAR_H,
          ...glassChrome(cut ? 20 : 22, 1),
          opacity: clamp(lift * 1.4),
        }}
      >
        <GlassInner
          t={t}
          x={partX}
          y={BAR_Y}
          w={partW}
          h={BAR_H}
          accent={accent}
          ink={ink}
          frost={0.55}
          sheen={(t * 0.3) % 1}
        />
        {/* the part is filled with the ATOMS that produced it */}
        <div style={{ position: "absolute", inset: 0, background: rgba(accent, 0.42) }} />
        {atoms > 0 ? (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              gap: 3,
              padding: "0 10px",
            }}
          >
            {Array.from({ length: Math.min(60, atoms) }).map((_, i) => {
              const u = clamp((atomsIn - i / Math.max(1, atoms) * 0.55) * 3);
              return (
                <div
                  key={i}
                  style={{
                    flex: 1,
                    height: BAR_H - 30,
                    borderRadius: 4,
                    background: rgba("#ffffff", 0.16 + (i % 2) * 0.08),
                    boxShadow: `inset 0 1px 0 ${rgba("#fff", 0.3)}`,
                    opacity: u,
                    transform: `scaleY(${0.35 + eset(u) * 0.65})`,
                  }}
                />
              );
            })}
          </div>
        ) : null}
      </div>

      {/* the remainder: jumps aside on the cut, then greys out — but keeps its
          own composition visible, so you can see what the part beat */}
      <div
        style={{
          position: "absolute",
          left: restX,
          top: BAR_Y,
          width: restW,
          height: BAR_H,
          // greyed, NOT erased — the remainder has to stay legible or the
          // fraction loses the thing it is a fraction OF.
          ...glassLite(cut ? 20 : 22, undefined, 1 - part * 0.25),
          opacity: clamp(lift * 1.4) * (1 - part * 0.18),
          overflow: "hidden",
          display: "flex",
          alignItems: "stretch",
          gap: 2,
          padding: 5,
        }}
      >
        {(wholeParts ?? []).map((wp, i) => {
          const sum = (wholeParts ?? []).reduce((a, b) => a + b.value, 0) || 1;
          const u = clamp((sinceCut - 0.24 - i * 0.09) / 0.5);
          const tint = wp.tint ?? BRAND.mute;
          return (
            <div
              key={wp.label}
              style={{
                flex: wp.value / sum,
                borderRadius: 8,
                background: `linear-gradient(158deg, ${rgba(tint, 0.5)} 0%, ${rgba(
                  tint,
                  0.22
                )} 100%)`,
                boxShadow: `inset 0 1px 0 ${rgba("#fff", 0.34)}`,
                transform: `scaleY(${0.25 + eset(u) * 0.75})`,
                transformOrigin: "50% 100%",
                opacity: 0.35 + u * 0.65,
              }}
            />
          );
        })}
      </div>
      {/* remainder legend — named groups, in dead space under the bar */}
      {cut && wholeParts?.length ? (
        <div
          style={{
            position: "absolute",
            left: restX,
            top: BAR_Y + BAR_H + 52,
            width: restW,
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "flex-end",
            gap: "6px 14px",
            opacity: part * 0.85,
          }}
        >
          {wholeParts.map((wp) => (
            <span
              key={wp.label}
              style={{
                fontFamily: MONO,
                fontSize: 19,
                letterSpacing: 1,
                color: rgba(BRAND.paper, 0.72),
                whiteSpace: "nowrap",
              }}
            >
              <span
                style={{
                  display: "inline-block",
                  width: 10,
                  height: 10,
                  borderRadius: 3,
                  background: wp.tint ?? BRAND.mute,
                  marginRight: 7,
                }}
              />
              {wp.label} {money(wp.value, TOT.prefix ?? "\u20b9")}
            </span>
          ))}
        </div>
      ) : null}

      {/* ---- labels either side of the cut --------------------------------- */}
      {cut ? (
        <>
          <div
            style={{
              position: "absolute",
              left: partX,
              top: BAR_Y + BAR_H + 22,
              width: partW,
              opacity: part,
              transform: `translateY(${(1 - part) * 14}px)`,
            }}
          >
            <div
              style={{
                fontFamily: MONO,
                fontSize: 22,
                letterSpacing: 4,
                color: accent,
              }}
            >
              {shareLabel ?? TOT.label}
            </div>
          </div>
          <div
            style={{
              position: "absolute",
              left: restX,
              top: BAR_Y + BAR_H + 22,
              width: restW,
              textAlign: "right",
              opacity: part * 0.7,
              transform: `translateY(${(1 - part) * 14}px)`,
            }}
          >
            <div
              style={{
                fontFamily: MONO,
                fontSize: 22,
                letterSpacing: 4,
                color: rgba(BRAND.paper, 0.5),
              }}
            >
              {WHOLE.label} {money(WHOLE.value, TOT.prefix ?? "₹")}
            </div>
          </div>
        </>
      ) : null}

      {/* ---- the twist line, typed ----------------------------------------- */}
      {atLeast ? (
        <div
          style={{
            position: "absolute",
            left: COL_X,
            top: SAFE_BOTTOM - 96,
            maxWidth: COL_W,
            opacity: clamp(alType * 1.4),
          }}
        >
          {atLeast.word ? (
            <div
              style={{
                fontFamily: DISPLAY,
                fontSize: 66,
                lineHeight: "64px",
                color: BRAND.paper,
              }}
            >
              {atLeast.word.slice(0, Math.ceil(atLeast.word.length * alType))}
              <span style={{ opacity: alType < 1 ? 1 : 0, color: accent }}>▌</span>
            </div>
          ) : null}
          {atLeast.note ? (
            <div
              style={{
                fontFamily: MONO,
                fontSize: 22,
                letterSpacing: 3,
                color: rgba(BRAND.paper, 0.5),
                marginTop: 12,
              }}
            >
              {atLeast.note}
            </div>
          ) : null}
        </div>
      ) : null}
      {host ? (
        <HostPip host={host} hostSize={hostSize} hostFrom={hostFrom}
                 height={height} fps={fps} anchor={hostAnchor} width={width} />
      ) : null}
    </AbsoluteFill>
  );
};

/* ---- canonical demo payload (the QC harness props) ----------------------- */
export const shareSplitDemo: ShareSplitProps = {
  runLabel: "FROM 3 SCREENSHOTS \u00b7 ONE MONTH",
  meta: [
    { k: "ROWS READ", v: "61" },
    { k: "DUPES CUT", v: "5" },
    { k: "MERCHANTS", v: "12" },
    { k: "SPEND", v: "\u20b90" },
  ],
  total: { value: 4212, label: "FOOD DELIVERY", sub: "41 orders in one month" },
  whole: { value: 12640, label: "FOUND IN THESE SCREENSHOTS" },
  atoms: 41,
  shareLabel: "ONE THIRD OF EVERYTHING",
  openFrost: { w: 750, h: 930, dur: 0.5 },
  splitAt: 1.15,
  atLeast: {
    at: 2.6,
    word: "And that's only what I showed it.",
    note: "A FLOOR — NOT A BANK STATEMENT",
  },
  ghostBars: 5,
  wholeParts: [
    { label: "SHOPPING", value: 7345, tint: "#FF9900" },
    { label: "OTHER APPS", value: 5164, tint: "#5FA82C" },
    { label: "FOOD", value: 2728, tint: "#E23744" },
    { label: "REST", value: 2560, tint: "#7A6B76" },
  ],
};
