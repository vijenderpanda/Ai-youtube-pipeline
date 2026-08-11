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
// v16 Vaibhav-DNA: neon lime as the numeric-callout + CTA accent (competitor
// teardown 2026-08-11 — every #NN hashtag callout and the community CTA pill
// in his 360K Short is this color). Magenta stays the Sol/brand primary; lime
// is reserved for the numbered-list callout system and CTA emphasis so the two
// never fight for the same job.
const LIME = "#B4FF00";

/* ---------- caption: small, bottom-third, spring pop, 1-3 words ---------- */
const Caption: React.FC<{ word: Word; fps: number; y?: string }> = ({ word, fps, y }) => {
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
          fontSize: 78,
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
        <span style={{ color: LIME }}>{numRaw}</span>
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

/* ---------- pipCallout (v16 Vaibhav-DNA numbered-list layout) ----------
   Top zone: product screencap b-roll (video/image), cover-fit, anchored top,
   fading into INK at the bottom so the callout row pops on dark (our brand
   fades to ink, not Vaibhav's light grey — keeps Sol's magenta/dark identity).
   Bottom-left: rounded-square host PIP. Right of it: giant lime "#NN" in
   Playfair italic + up to 3 description lines. PIP + callout spring up together
   on beat entry. The competitor's #NN callout is the attention anchor of every
   numbered point; this is the single most-copied move from the 360K teardown. */
const PIP_SIZE = 380;        // rounded-square host PIP edge (px)
const PIP_LEFT = 48;
const PIP_BOTTOM = 330;      // lower-third, with breathing room below (Vaibhav's row sits ~65-83%, not jammed at the frame bottom)
const PipCallout: React.FC<{ seg: Seg; fps: number }> = ({ seg, fps }) => {
  const frame = useCurrentFrame();
  const s = spring({ frame, fps, config: { damping: 18, mass: 0.8 } });
  const rise = interpolate(s, [0, 1], [70, 0]);
  const fade = interpolate(s, [0, 1], [0, 1]);
  const numRaw = (seg.num ?? "").replace(/^#/, "");
  const lines = seg.lines ?? [];
  const isVid = (seg.src ?? "").match(/\.(mp4|mov|webm|mkv)$/i);
  return (
    <AbsoluteFill style={{ background: INK }}>
      {/* top zone — product screencap */}
      <div style={{ position: "absolute", inset: 0, overflow: "hidden" }}>
        {isVid ? (
          <OffthreadVideo
            src={res(seg.src!)}
            startFrom={Math.round((seg.from ?? 0) * fps)}
            muted
            style={{ width: "100%", height: "62%", objectFit: "cover", objectPosition: "center top" }}
          />
        ) : (
          <Img
            src={res(seg.src!)}
            style={{ width: "100%", height: "62%", objectFit: "cover", objectPosition: "center top" }}
          />
        )}
        {/* fade the screencap bottom into INK so the callout row reads clean */}
        <div
          style={{
            position: "absolute",
            top: "40%",
            left: 0,
            width: "100%",
            height: "60%",
            background: `linear-gradient(180deg, rgba(14,14,20,0) 0%, ${INK} 40%)`,
          }}
        />
      </div>
      {/* PIP + callout row */}
      <div
        style={{
          position: "absolute",
          left: PIP_LEFT,
          bottom: PIP_BOTTOM,
          right: 40,
          display: "flex",
          alignItems: "center",
          gap: 40,
          transform: `translateY(${rise}px)`,
          opacity: fade,
        }}
      >
        {/* rounded-square host PIP */}
        <div
          style={{
            width: PIP_SIZE,
            height: PIP_SIZE,
            flexShrink: 0,
            borderRadius: 30,
            overflow: "hidden",
            border: "2px solid rgba(255,255,255,0.14)",
            boxShadow: "0 24px 60px rgba(0,0,0,0.55)",
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
                objectPosition: "center top",
                // v16: the HeyGen render is a chest-up talking-head (720x1280)
                // framed for full-frame, not a 380px square. Without a zoom the
                // face renders at ~75px physical and Sol's warm-eyes signal — the
                // whole point of the host — dies. A fixed scale pulls the
                // head-and-shoulders up to ~70% fill (matching Vaibhav's PIP).
                // One zoom works across the whole wardrobe (all outfits share the
                // same 2:3 recipe/seed/framing). Parent has overflow:hidden.
                transform: `scale(${seg.pipZoom ?? 1.32})`,
                transformOrigin: "50% 30%",
              }}
            />
          ) : null}
        </div>
        {/* callout number + lines */}
        <div style={{ minWidth: 0, flex: 1 }}>
          <div
            style={{
              fontFamily: "'Playfair Display', Georgia, serif",
              fontStyle: "italic",
              fontWeight: 900,
              fontSize: 200,
              lineHeight: 0.9,
              letterSpacing: -4,
              textShadow: "0 6px 26px rgba(0,0,0,0.6)",
            }}
          >
            <span style={{ color: "white" }}>#</span>
            <span style={{ color: LIME }}>{numRaw}</span>
          </div>
          <div
            style={{
              marginTop: 14,
              fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif',
              fontWeight: 600,
              fontSize: 38,
              lineHeight: 1.18,
              color: "#F3F4F8",
              textShadow: "0 2px 10px rgba(0,0,0,0.7)",
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
      {activeCaption && !activeIsPip ? (
        <Caption word={activeCaption} fps={fps} y={activeMode === "split" ? "47%" : undefined} />
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
