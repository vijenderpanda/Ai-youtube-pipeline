import React from "react";
import {
  AbsoluteFill,
  staticFile,
  Audio,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { fitFont, splitHook } from "./components/fitText";
import { StatBars, StatBarsProps } from "./components/StatBars";

/* ---------- types (props come from a per-episode JSON) ---------- */
export type Word = { w: string; start: number; end: number; hot?: boolean };
export type Seg = {
  /* src omitted for kind "statBars" (chart is drawn in-comp, never pre-baked) */
  src?: string;
  dur: number;
  kind?: "video" | "image" | "statBars" | "pipCallout";
  from?: number;
  /* per-beat pane mode (newsSplit only): "split" b-roll top + host bottom,
     "full" b-roll full-frame, "host" host full-frame */
  mode?: "split" | "full" | "host";
  /* kind "statBars": props for the LOCKED StatBars chart (playbook §4 — data
     beats render the native 1080x1920 component, never a cover-fit image).
     stat.start is relative to THIS beat (Sequence-local frames). */
  stat?: StatBarsProps;
  /* kind "pipCallout" (v16 Vaibhav-DNA): the flagship numbered-list layout.
     `src` = the b-roll top zone (product screencap, video or image, cover-fit).
     `pip` = the host talking-head clip shown as a rounded-square PIP bottom-left.
     `num` = the callout number ("02") rendered huge in lime Playfair italic.
     `lines` = 1-3 description lines beside the number.
     `pipFrom` = start-from for the pip clip; `from` = start-from for the b-roll. */
  pip?: string;
  pipFrom?: number;
  pipZoom?: number;   // v16: scale the PIP video to fill the square (~70% face fill); default 1.55
  num?: string;
  lines?: string[];
  framed?: boolean;   // v16.2: render a host clip as a contained rounded card on the gradient bg (not full-bleed giant face)
  hostZoom?: number;  // v16.2: scale inside the framed host card (default 1.0)
};
/* pos: which corner the chip lives in — pick the one with dead space so the
   chip NEVER covers the content the beat is teaching (default tl).
   style "hashtag" (v16): render a lime Playfair "#NN" badge instead of the
   glass "STEP 1/3" chip — keeps the numbered-list count alive over host-hero
   beats between pipCallout beats (Vaibhav-DNA). `label` carries the number. */
export type Step = {
  label: string;
  start: number;
  end: number;
  pos?: "tl" | "tr" | "bl" | "br";
  style?: "chip" | "hashtag";
};
export type Emphasis = { text: string; start: number; end: number };
export type ShortProps = {
  segments: Seg[];
  captions: Word[];
  steps?: Step[];
  vo: string;
  music?: string;
  musicGain?: number;
  /* title2 optional: a lazy payload may send the whole hook as one long title1 —
     Cover auto-splits it into the mandatory two-line stack (see Cover below). */
  cover?: {
    title1: string;
    title2?: string;
    sub?: string;
    emojis?: string;
    until: number;
    /* v16 premium cover: opt-in overrides for bigger, centered title */
    bigTitle?: number;      // absolute font-size override for title1
    centerTitle?: boolean;  // horizontally center the type stack instead of left-anchoring
  };
  watermark?: boolean;
  fps?: number;
  /* news-split: persistent host pinned bottom, segments play in the top pane */
  layout?: "cut" | "newsSplit";
  host?: string;
  emphasis?: Emphasis[];
};

const res = (p: string) => (p.startsWith("http") ? p : staticFile(p));

const MAG = "#E0218A";     // brand primary — Sol identity, active caption word
const YELLOW = "#FFD60A";  // brand secondary — hot-word alternate, chip fills
const INK = "#0E0E14";
// v16: the numbered-callout + CTA accent. Vaibhav uses neon lime; we deliberately
// do NOT copy his color (the LAYOUT is the borrowed idea, the color stays ours) —
// electric cyan #22D3EE is distinct from our magenta+yellow AND from his lime,
// reads premium/tech on dark ink. One constant so it's a one-line change.
// Reserved for the #NN callout system + CTA emphasis; magenta stays brand primary.
const ACCENT = "#22D3EE";

/* ---------- caption: bottom, spring pop, 1-3 words. size for small pip-beat
   captions in the bottom space (v16.2). ---------- */
const Caption: React.FC<{ word: Word; fps: number; y?: string | number; size?: number }> = ({ word, fps, y, size }) => {
  const frame = useCurrentFrame();
  const startF = word.start * fps;
  const s = spring({ frame: frame - startF, fps, config: { damping: 12, mass: 0.4 } });
  const scale = interpolate(s, [0, 1], [0.86, 1]);
  return (
    <div
      style={{
        position: "absolute",
        bottom: y ?? "21%",
        width: "100%",
        display: "flex",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          transform: `scale(${scale})`,
          fontFamily: "Anton, Arial Black, sans-serif",
          fontWeight: 900,
          fontSize: size ?? 78,
          letterSpacing: 1,
          color: word.hot ? MAG : "white",
          textShadow:
            "0 3px 0 #000, 0 -3px 0 #000, 3px 0 0 #000, -3px 0 0 #000, 0 6px 18px rgba(0,0,0,0.85)",
          textTransform: "uppercase",
        }}
      >
        {word.w}
      </div>
    </div>
  );
};

/* ---------- step marker: “STEP 1/3” chip, top-left, slides in ---------- */
// Modern status-chip: dark glass, hairline border, a magenta accent dot and a
// medium tracked sans label — no fat Anton block or thick brand border. Shared
// design language with the outro CTAs (gen_outro.py).
const StepChip: React.FC<{ step: Step; fps: number }> = ({ step, fps }) => {
  const frame = useCurrentFrame();
  const s = spring({ frame: frame - step.start * fps, fps, config: { damping: 16, mass: 0.7 } });
  const pos = step.pos ?? "tl";
  const enterX = interpolate(s, [0, 1], [pos.endsWith("l") ? -44 : 44, 0]);
  const opacity = interpolate(s, [0, 1], [0, 1]);
  const vert: React.CSSProperties = pos.startsWith("t") ? { top: 172 } : { bottom: 566 };
  const horiz: React.CSSProperties = pos.endsWith("l") ? { left: 40 } : { right: 40 };

  // v16 Vaibhav-DNA: hashtag variant — a lime Playfair "#NN" badge (no glass
  // chrome). label carries the number ("02" or "#02"); the # is forced white,
  // the number lime. Used to keep the running count alive over host-hero beats.
  if (step.style === "hashtag") {
    const numRaw = step.label.replace(/^#/, "");
    return (
      <div
        style={{
          position: "absolute",
          ...vert,
          ...horiz,
          transform: `translateY(${interpolate(s, [0, 1], [40, 0])}px)`,
          opacity,
          fontFamily: "'Playfair Display', Georgia, serif",
          fontStyle: "italic",
          fontWeight: 900,
          fontSize: 130,
          lineHeight: 0.9,
          letterSpacing: -3,
          textShadow: "0 5px 22px rgba(0,0,0,0.6)",
        }}
      >
        <span style={{ color: "white" }}>#</span>
        <span style={{ color: ACCENT }}>{numRaw}</span>
      </div>
    );
  }

  return (
    <div
      style={{
        position: "absolute",
        ...vert,
        ...horiz,
        transform: `translateX(${enterX}px)`,
        opacity,
        display: "flex",
        alignItems: "center",
        gap: 11,
        padding: "11px 20px 11px 16px",
        background: "rgba(16,16,22,0.56)",
        border: "1.5px solid rgba(255,255,255,0.16)",
        borderRadius: 14,
        boxShadow: "0 10px 30px rgba(0,0,0,0.38)",
        backdropFilter: "blur(14px)",
        WebkitBackdropFilter: "blur(14px)",
        fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif',
        fontWeight: 600,
        fontSize: 28,
        letterSpacing: 0.4,
        color: "#F3F4F8",
        whiteSpace: "nowrap",
      }}
    >
      <span
        style={{
          width: 9,
          height: 9,
          borderRadius: "50%",
          background: MAG,
          boxShadow: `0 0 12px ${MAG}`,
          flexShrink: 0,
        }}
      />
      {step.label}
    </div>
  );
};

/* ---------- cover: FROZEN "Poster Duotone" template (user-approved 2026-08-02) ----------
   LOCKED RULE (Ep23 QC, 2026-08-05): the hook is ALWAYS the two-line stack.
   - A lazy payload sending one long title1 (no/empty title2) is auto-split at the
     most balanced word break: title1 = wide extruded line, title2 = punch chip.
   - Both lines hard-cap their width via font autoshrink (fitFont) so type can
     NEVER clip the 1080 frame (Ep23's "AI JUST GOT" at fixed 225px ran off the
     right edge). If a supplied title1 would need a sub-premium size, the whole
     hook is re-balanced across both lines first, then shrunk only as needed. */
const extrude = (depth: number, color: string): string =>
  Array.from({ length: depth }, (_, i) => `${i + 1}px ${i + 1}px 0 ${color}`).join(",") +
  ", 16px 22px 28px rgba(0,0,0,0.55)";

const COVER_BOX_W = 990; // type-stack box (left 44 → safe right edge)
const T1_BASE = 225;     // frozen title1 size — used only when it actually fits
const T1_MIN = 120;      // below this, re-balance the split before shrinking
const T2_BASE = 118;     // frozen chip size
const CHIP_PAD_X = 68;   // chip horizontal padding total

export const Cover: React.FC<{ c: NonNullable<ShortProps["cover"]>; fps: number }> = ({ c, fps }) => {
  const frame = useCurrentFrame();
  const untilF = c.until * fps;
  // Frame 0 is the Shorts feed thumbnail, so it must stay fully opaque. Clamp the
  // fade-in start to >=0: an `until` shorter than the 0.7s dissolve then compresses
  // the dissolve into [0, until] instead of opening it BEFORE frame 0 (which left
  // the thumbnail ~14% transparent when a no-host episode derived until=0.60).
  // Playbook §5 (frame-zero QC) / §13 (Ep25).
  const fadeOut = interpolate(frame, [Math.max(0, untilF - 0.7 * fps), untilF], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // v13 PROOF-FLASH: brief opacity dip at ~0.5s lets the first segment peek through
  // the cover, signalling "real content is coming" and reducing swipe-aways.
  // The dip is subtle (to 0.7) and lasts 0.25s so frame-0 thumbnail stays clean.
  // Only fires when cover holds long enough (>= 1.2s) to have room for the peek.
  const peekDip = c.until >= 1.2
    ? interpolate(frame, [0.4 * fps, 0.5 * fps, 0.65 * fps, 0.75 * fps], [1, 0.7, 0.7, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 1;
  const opacity = fadeOut * peekDip;
  const intro = spring({ frame, fps, config: { damping: 14, mass: 0.6 } });
  const slide = interpolate(intro, [0, 1], [70, 0]);
  const slant = "perspective(900px) rotateY(-4deg) rotateZ(-3deg) skewY(-1deg)";

  /* enforce the two-line stack */
  const raw1 = (c.title1 ?? "").trim();
  const raw2 = (c.title2 ?? "").trim();
  let [line1, line2] = raw2 ? [raw1, raw2] : splitHook(raw1);
  if (fitFont(line1 || " ", T1_BASE, COVER_BOX_W) < T1_MIN) {
    [line1, line2] = splitHook(`${line1} ${line2}`.trim());
  }
  // v16: premium cover opts — bigTitle overrides the frozen 225 base (Ep 10 v3
  // ships bigTitle=300 for shorts-feed reach). centerTitle horizontally
  // centers the type-stack box instead of left-anchoring at 44px.
  const t1Base = c.bigTitle ?? T1_BASE;
  const f1 = fitFont(line1 || " ", t1Base, COVER_BOX_W);
  const f2 = fitFont(line2 || " ", T2_BASE, COVER_BOX_W - CHIP_PAD_X);
  const extrudeDepth = Math.max(6, Math.round(f1 / 20)); // scale extrude with type
  // type-on reveal — keeps the angled/extruded poster style, adds a hook/edited feel
  const CHAR_F = 1.7;                       // frames per character
  const t1Start = 5;
  const t1End = t1Start + line1.length * CHAR_F;
  const shown1 = line1.slice(0, Math.max(0, Math.min(line1.length, Math.floor((frame - t1Start) / CHAR_F))));
  const caretOn = frame < t1End && Math.floor(frame / 6) % 2 === 0;
  const t2Start = t1End + 4;
  const chipSpring = spring({ frame: frame - t2Start, fps, config: { damping: 13, mass: 0.5 } });
  const chipScale = interpolate(chipSpring, [0, 1], [0.7, 1]);
  const chipOpacity = interpolate(frame, [t2Start, t2Start + 3], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const subStart = t2Start + 10;
  const subOpacity = interpolate(frame, [subStart, subStart + 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ opacity }}>
      <Img
        src={staticFile("cover_bg_duotone.jpg")}
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
      />
      <AbsoluteFill style={{ background: "rgba(10,10,14,0.38)" }} />
      {/* type stack — extruded + slanted, poster style */}
      <div
        style={{
          position: "absolute",
          top: 150,
          left: c.centerTitle ? 0 : 44,
          right: c.centerTitle ? 0 : undefined,
          width: c.centerTitle ? undefined : 990,
          margin: c.centerTitle ? "0 auto" : undefined,
          textAlign: c.centerTitle ? "center" : undefined,
          transform: `translateY(${slide}px)`,
          fontFamily: "Anton, Arial Black, sans-serif",
          textTransform: "uppercase",
        }}
      >
        <div
          style={{
            fontSize: f1,
            lineHeight: 0.98,
            color: "#F7F8FC",
            transform: slant,
            transformOrigin: "left center",
            textShadow: extrude(extrudeDepth, "#3C0A28"),
            letterSpacing: 1,
          }}
        >
          {shown1}
          {caretOn ? (
            <span
              style={{
                display: "inline-block",
                width: Math.round(f1 * 0.06),
                height: Math.round(f1 * 0.72),
                background: MAG,
                marginLeft: 10,
                borderRadius: 3,
                verticalAlign: "-0.08em",
              }}
            />
          ) : null}
        </div>
        {line2 ? (
          <div
            style={{
              display: "inline-block",
              marginTop: 34,
              padding: "10px 34px 16px",
              background: "#FFD60A",
              color: "#100C16",
              fontSize: f2,
              lineHeight: 1.0,
              borderRadius: 20,
              transform: `${slant} scale(${chipScale})`,
              transformOrigin: "left center",
              opacity: chipOpacity,
              boxShadow: "14px 18px 30px rgba(0,0,0,0.5)",
            }}
          >
            {line2}
          </div>
        ) : null}
        {c.sub ? (
          <div
            style={{
              marginTop: 44,
              opacity: subOpacity,
              fontSize: fitFont(c.sub, 52, COVER_BOX_W - 90),
              color: "#E8E8F2",
              letterSpacing: 1,
            }}
          >
            {c.emojis ? <span style={{ fontSize: 58, marginRight: 22 }}>{c.emojis.slice(0, 2)}</span> : null}
            {c.sub}
          </div>
        ) : c.emojis ? (
          <div style={{ marginTop: 40, fontSize: 72, letterSpacing: 14 }}>{c.emojis}</div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

/* ---------- emphasis: serif italic key-phrase, upper-middle, gentle rise ---------- */
const EmphasisText: React.FC<{ e: Emphasis; fps: number }> = ({ e, fps }) => {
  const frame = useCurrentFrame();
  const startF = e.start * fps;
  const endF = e.end * fps;
  const s = spring({ frame: frame - startF, fps, config: { damping: 16, mass: 0.5 } });
  const rise = interpolate(s, [0, 1], [26, 0]);
  const fade = interpolate(frame, [endF - 0.4 * fps, endF], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        position: "absolute",
        top: "38%",
        width: "100%",
        display: "flex",
        justifyContent: "center",
        opacity: Math.min(s, fade),
        transform: `translateY(${rise}px)`,
      }}
    >
      <div
        style={{
          fontFamily: "Georgia, 'Times New Roman', serif",
          fontStyle: "italic",
          fontWeight: 600,
          fontSize: 64,
          color: "#F5F0E8",
          textAlign: "center",
          maxWidth: 880,
          lineHeight: 1.18,
          textShadow: "0 2px 6px rgba(0,0,0,0.9), 0 8px 30px rgba(0,0,0,0.7)",
        }}
      >
        {e.text}
      </div>
    </div>
  );
};

/* v16.2: gentle continuous float — a slow sine on translateY. The subtle
   "alive" drift on every card/PIP/callout in the competitor's shorts (confirmed
   frame-to-frame). Phase-offset per element so they don't bob in lockstep. */
const floatY = (frame: number, fps: number, amp: number, periodS: number, phaseS = 0) =>
  amp * Math.sin(((frame / fps) + phaseS) * ((2 * Math.PI) / periodS));

/* v16.2: shared premium gradient backdrop for the card-based beats (pipCallout +
   framed host) — magenta top glow + cyan bottom-right accent + deep violet-ink
   base + a vignette. One look across the episode so beats feel like one system. */
const GRAD_BG =
  "radial-gradient(140% 88% at 50% 6%, rgba(224,33,138,0.30) 0%, rgba(150,28,116,0.12) 26%, rgba(14,14,20,0) 56%)," +
  "radial-gradient(85% 55% at 84% 94%, rgba(34,211,238,0.12) 0%, rgba(14,14,20,0) 52%)," +
  "linear-gradient(178deg, #1c1122 0%, #130d17 42%, #0E0E14 80%)";
const Vignette: React.FC = () => (
  <AbsoluteFill
    style={{
      background: "radial-gradient(120% 80% at 50% 42%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.45) 100%)",
      pointerEvents: "none",
    }}
  />
);

/* ---------- framed host (v16.2) — a full-shot host beat rendered as a large
   CONTAINED rounded card on the gradient (not a full-bleed giant face). Fixes
   VJ's note that the tight outfit_11 crop filled the whole phone screen. */
const FramedHost: React.FC<{ seg: Seg; fps: number }> = ({ seg, fps }) => {
  const frame = useCurrentFrame();
  const f = floatY(frame, fps, 7, 3.8, 0);
  return (
    <AbsoluteFill style={{ background: GRAD_BG }}>
      <Vignette />
      <div
        style={{
          position: "absolute",
          left: 116,
          right: 116,
          top: 214,
          height: 1180,
          transform: `translateY(${f}px)`,
          borderRadius: 32,
          overflow: "hidden",
          border: "1.5px solid rgba(255,255,255,0.12)",
          boxShadow: "0 44px 100px rgba(0,0,0,0.6), 0 8px 44px rgba(224,33,138,0.12)",
          background: INK,
        }}
      >
        <OffthreadVideo
          src={res(seg.src!)}
          startFrom={Math.round((seg.from ?? 0) * fps)}
          muted
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            objectPosition: "57% 14%",
            transform: `scale(${seg.hostZoom ?? 1.0})`,
            transformOrigin: "57% 16%",
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

/* ---------- pipCallout v2 (Vaibhav-DNA numbered-list layout) ----------
   Redesign per VJ feedback (2026-08-11): the b-roll is no longer a hard
   full-bleed section cropped-and-pasted. It's a ROUNDED-CORNER CARD inset from
   the edges, floating on a dark magenta-tinted GRADIENT, with a soft shadow.
   The host PIP is a rounded RECTANGLE (portrait), not a square (which was
   half-cutting the face). Everything drifts with a gentle float. #NN stays big
   cyan Playfair (our distinctive accent), description beside it. */
const CARD_X = 44;
const CARD_TOP = 70;
const CARD_W = 1080 - 2 * CARD_X;        // 992
const CARD_H = Math.round(CARD_W / 0.9); // ~1102 — matches the 1080x1200 CodeDemo aspect (no crop)
const PIP_W = 360;
const PIP_H = 464;                        // rounded RECTANGLE (portrait ~3:4), not a square
const PIP_LEFT = 48;
const PIP_BOTTOM = 240;
const PipCallout: React.FC<{ seg: Seg; fps: number }> = ({ seg, fps }) => {
  const frame = useCurrentFrame();
  const s = spring({ frame, fps, config: { damping: 18, mass: 0.8 } });
  const rise = interpolate(s, [0, 1], [70, 0]);
  const fade = interpolate(s, [0, 1], [0, 1]);
  const numRaw = (seg.num ?? "").replace(/^#/, "");
  const lines = seg.lines ?? [];
  const isVid = (seg.src ?? "").match(/\.(mp4|mov|webm|mkv)$/i);

  // float offsets (phase-staggered)
  const cardF = floatY(frame, fps, 7, 3.6, 0);
  const pipF = floatY(frame, fps, 6, 4.0, 1.3);
  const numF = floatY(frame, fps, 5, 4.4, 2.5);

  const media = { width: "100%", height: "100%", objectFit: "cover" as const, objectPosition: "center top" as const };

  return (
    <AbsoluteFill style={{ background: GRAD_BG }}>
      <Vignette />
      {/* b-roll — a floating rounded card, inset from the edges */}
      <div
        style={{
          position: "absolute",
          left: CARD_X,
          top: CARD_TOP,
          width: CARD_W,
          height: CARD_H,
          transform: `translateY(${cardF}px)`,
          borderRadius: 26,
          overflow: "hidden",
          border: "1.5px solid rgba(255,255,255,0.10)",
          boxShadow:
            "0 40px 90px rgba(0,0,0,0.55), 0 0 0 1px rgba(0,0,0,0.4), 0 8px 40px rgba(34,211,238,0.10)",
          background: INK,
        }}
      >
        {isVid ? (
          <OffthreadVideo src={res(seg.src!)} startFrom={Math.round((seg.from ?? 0) * fps)} muted style={media} />
        ) : (
          <Img src={res(seg.src!)} style={media} />
        )}
      </div>

      {/* PIP + callout row (spring-rise on entry, then gentle float) */}
      <div
        style={{
          position: "absolute",
          left: PIP_LEFT,
          bottom: PIP_BOTTOM,
          right: 40,
          display: "flex",
          alignItems: "center",
          gap: 38,
          transform: `translateY(${rise}px)`,
          opacity: fade,
        }}
      >
        {/* host PIP — rounded RECTANGLE (portrait), fixed scale so the face isn't cut */}
        <div
          style={{
            width: PIP_W,
            height: PIP_H,
            flexShrink: 0,
            transform: `translateY(${pipF}px)`,
            borderRadius: 26,
            overflow: "hidden",
            border: "1.5px solid rgba(255,255,255,0.12)",
            boxShadow: "0 28px 64px rgba(0,0,0,0.55)",
            background: INK,
          }}
        >
          {seg.pip ? (
            <OffthreadVideo
              src={res(seg.pip)}
              startFrom={Math.round((seg.pipFrom ?? 0) * fps)}
              muted
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                // v16.2: HeyGen framed outfit_11's face slightly RIGHT of center;
                // objectPosition "57%" recenters it and the modest zoom fills the
                // rounded rectangle without clipping the right cheek (the earlier
                // 1.06 + center-crop was cutting it). Per-beat seg.pipZoom overrides.
                objectPosition: "57% 16%",
                transform: `scale(${seg.pipZoom ?? 1.08})`,
                transformOrigin: "57% 18%",
              }}
            />
          ) : null}
        </div>

        {/* callout number + description */}
        <div style={{ minWidth: 0, flex: 1, transform: `translateY(${numF}px)` }}>
          <div
            style={{
              fontFamily: "'Playfair Display', Georgia, serif",
              fontStyle: "italic",
              fontWeight: 900,
              fontSize: 190,
              lineHeight: 0.9,
              letterSpacing: -4,
              textShadow: "0 6px 26px rgba(0,0,0,0.6)",
            }}
          >
            <span style={{ color: "white" }}>#</span>
            <span style={{ color: ACCENT }}>{numRaw}</span>
          </div>
          <div
            style={{
              marginTop: 12,
              fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif',
              fontWeight: 600,
              fontSize: 37,
              lineHeight: 1.2,
              color: "#F3F4F8",
              textShadow: "0 2px 12px rgba(0,0,0,0.85)",
            }}
          >
            {lines.map((ln, i) => (
              <div key={i}>{ln}</div>
            ))}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ---------- watermark ----------
   v16: fade in only AFTER cover clears (frame > coverUntil + 0.3s) so the
   frame-zero + hook window stays visually clean. When there's no cover, fades
   in at t=0.3s. Vaibhav-DNA covers have no watermark in the hook — the
   watermark's job is on-scroll brand recall in the second half, not shouting
   during the hook. */
export const Watermark: React.FC<{ startF?: number }> = ({ startF = 0 }) => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(
    frame,
    [startF, startF + 8],
    [0, 0.7],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  return (
  <div
    style={{
      position: "absolute",
      top: 34,
      right: 30,
      fontFamily: "Anton, Arial Black",
      fontSize: 34,
      opacity: fadeIn,
      background: "rgba(10,10,16,0.5)",
      padding: "6px 16px",
      borderRadius: 14,
    }}
  >
    <span style={{ color: "white" }}>AI </span>
    <span style={{ color: MAG }}>UNPACKED</span>
    <span style={{ color: YELLOW }}> VJ</span>
  </div>
  );
};

/* ---------- main composition ---------- */
export const Short: React.FC<ShortProps> = (props) => {
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();
  const t = frame / fps;
  let acc = 0;
  const segStarts = props.segments.map((s) => {
    const st = acc;
    acc += s.dur;
    return st;
  });
  const total = acc;
  const activeCaption = props.captions.find((w) => t >= w.start && t <= w.end);
  const musicVol = (f: number) =>
    interpolate(f, [0, 1.2 * fps], [0, props.musicGain ?? 0.13], {
      extrapolateRight: "clamp",
    });

  const news = props.layout === "newsSplit" && props.host;
  // active segment's pane mode drives host placement + caption position
  const activeIdx = props.segments.findIndex(
    (s, i) => t >= segStarts[i] && t < segStarts[i] + s.dur
  );
  const activeMode: NonNullable<Seg["mode"]> = news
    ? props.segments[Math.max(activeIdx, 0)]?.mode ?? "split"
    : "full";
  // v16: pipCallout beats carry their own description lines, so the word-by-word
  // caption is suppressed there (it would collide with the callout row). The
  // step chip is suppressed too — the #NN callout IS the step marker.
  const activeIsPip = props.segments[Math.max(activeIdx, 0)]?.kind === "pipCallout";
  const paneFor = (mode: NonNullable<Seg["mode"]>): React.CSSProperties =>
    mode === "split"
      ? { position: "absolute", top: 0, left: 0, width: "100%", height: "55%", overflow: "hidden" }
      : { position: "absolute", inset: 0 };

  return (
    <AbsoluteFill style={{ background: INK }}>
      <style>{`
        @font-face { font-family: 'Anton'; src: url('${staticFile("fonts/Anton.ttf")}'); }
        @font-face { font-family: 'Playfair Display'; font-style: italic; font-weight: 400 900; src: url('${staticFile("fonts/PlayfairDisplay-Italic.ttf")}'); }
      `}</style>
      {props.segments.map((seg, i) => {
        const mode = news ? seg.mode ?? "split" : "full";
        if (news && mode === "host") return null; // host layer covers this beat
        return (
          <Sequence
            key={i}
            from={Math.round(segStarts[i] * fps)}
            durationInFrames={Math.round(seg.dur * fps)}
          >
            <div style={paneFor(mode)}>
              {seg.kind === "pipCallout" ? (
                <PipCallout seg={seg} fps={fps} />
              ) : seg.framed && !news ? (
                <FramedHost seg={seg} fps={fps} />
              ) : seg.kind === "statBars" && seg.stat ? (
                <StatBars {...seg.stat} />
              ) : seg.kind === "image" ? (
                <Img src={res(seg.src!)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              ) : (
                <OffthreadVideo
                  src={res(seg.src!)}
                  startFrom={Math.round((seg.from ?? 0) * fps)}
                  muted
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: news ? "cover" : "contain",
                    background: INK,
                  }}
                />
              )}
            </div>
          </Sequence>
        );
      })}
      {news && activeMode !== "full" ? (
        <div
          style={
            activeMode === "host"
              ? { position: "absolute", inset: 0, overflow: "hidden" }
              : {
                  position: "absolute",
                  bottom: 0,
                  left: 0,
                  width: "100%",
                  height: "45%",
                  overflow: "hidden",
                  borderTop: `6px solid ${MAG}`,
                }
          }
        >
          <OffthreadVideo
            src={res(props.host!)}
            muted
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              // 45%-tall split pane center-crops a 9:16 talking-photo and
              // guillotines the top of the head; anchor to the top so the
              // head+shoulders stay in frame (full-host mode is exact, so
              // this is a no-op there).
              objectPosition: "center top",
            }}
          />
        </div>
      ) : null}

      {(props.steps ?? [])
        .filter((s) => t >= s.start && t <= s.end && !activeIsPip)
        .map((s, i) => (
          <StepChip key={i} step={s} fps={fps} />
        ))}

      {(props.emphasis ?? [])
        .filter((e) => t >= e.start && t <= e.end)
        .map((e, i) => (
          <EmphasisText key={i} e={e} fps={fps} />
        ))}
      {activeCaption ? (
        activeIsPip ? (
          // v16.2: small running captions with hot-word highlight in the bottom
          // space below the pipCallout row (VJ feedback — use the blank space)
          <Caption word={activeCaption} fps={fps} y={96} size={46} />
        ) : (
          <Caption word={activeCaption} fps={fps} y={activeMode === "split" ? "47%" : undefined} />
        )
      ) : null}
      {props.cover && t <= props.cover.until ? <Cover c={props.cover} fps={fps} /> : null}
      {props.watermark !== false ? (
        <Watermark
          // v16: fade in after cover clears + a 0.3s grace so the hook window
          // stays visually clean. With no cover, still delay 0.3s so a
          // full-frame value pane at frame 0 isn't crowded.
          startF={Math.round(((props.cover?.until ?? 0) + 0.3) * fps)}
        />
      ) : null}

      <Audio src={res(props.vo)} />
      {props.music ? <Audio src={res(props.music)} volume={musicVol} loop /> : null}
    </AbsoluteFill>
  );
};

export const totalDuration = (p: ShortProps): number =>
  p.segments.reduce((a, s) => a + s.dur, 0);
