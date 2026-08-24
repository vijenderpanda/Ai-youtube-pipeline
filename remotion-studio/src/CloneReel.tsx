import React from "react";
import { AbsoluteFill, Img, Sequence, staticFile, useVideoConfig } from "remotion";
import { CookbookBlock } from "./cookbook/components";
import { ChipCaption, Chip } from "./cookbook/ChipCaption";
import { CREAM, Fonts, SANS, SERIF, rgba, themeTokens, CookTheme } from "./cookbook/kit";

/* =============================================================================
   CloneReel — a style-clone preview: an ordered list of cookbook blocks played
   back-to-back on the cream (or brand) canvas, each holding for `seconds`.
   Used to preview how a reference Short's beat-map re-renders out of OUR
   components (research/comp-dna/clones/*.json). Not a production film: no VO,
   no karaoke; an optional `caption` per block stands in for the spoken line.
   ========================================================================== */

export type CloneBlock = {
  id: string; // cookbook component id
  seconds: number;
  props?: Record<string, unknown>;
  caption?: string; // stand-in for the VO line (bottom chip)
  transparent?: boolean;
  host?: "full" | "pip" | "none"; // host presence on this beat (overrides reel default)
};

export type CloneReelProps = {
  title?: string; // tiny provenance tag, top-left
  theme?: CookTheme;
  accent?: string;
  bg?: string;
  blocks: CloneBlock[];
  /** Host still (in public/) shown as a framed PIP — stands in for the real HeyGen
   *  Sol clip that composites at full render. Lets the contact sheet show the
   *  actual host placement. */
  hostSrc?: string; // e.g. "hosts/sol_center.jpg"
  hostDefault?: "full" | "pip" | "none"; // presence when a block doesn't set its own (default "pip")
  hostPos?: "bl" | "br"; // pip corner (default "bl")
  /** Global yellow word-highlight karaoke, on the film clock (from VO word timings). */
  karaoke?: Chip[];
};

/* Host render per the cutaway grammar (research/comp-dna/HOST-PLACEMENT.md):
   - "full" = the dominant talking-head shot (host fills the lower frame, text overlays above);
     stands in for the real HeyGen Sol clip that composites at full render.
   - "pip"  = a small corner window (dev-tips variant only).
   The graphic beats pass host:"none" → nothing renders (hard cutaway to graphic-full). */
const HostShot: React.FC<{ src: string; mode: "full" | "pip"; pos: "bl" | "br"; accent: string; bg: string }> = ({ src, mode, pos, accent, bg }) => {
  if (mode === "full") {
    // talking-head fills the lower ~62% of frame, bottom-anchored, with a bg-scrim so overlay text stays legible
    return (
      <>
        <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 1200, width: 1080,
          display: "flex", justifyContent: "center", alignItems: "flex-end" }}>
          <Img src={staticFile(src)} style={{ height: 1180, objectFit: "cover", objectPosition: "top center",
            maskImage: "linear-gradient(180deg, transparent 0%, #000 16%)", WebkitMaskImage: "linear-gradient(180deg, transparent 0%, #000 16%)" }} />
        </div>
        <div style={{ position: "absolute", left: 40, bottom: 40, padding: "6px 16px", borderRadius: 999,
          background: accent, color: "#111", fontFamily: SANS, fontWeight: 800, fontSize: 26, letterSpacing: 1 }}>SOL · live</div>
      </>
    );
  }
  const w = 360, h = Math.round(w * 1.34);
  const side = pos === "bl" ? { left: 48 } : { right: 48 };
  return (
    <div style={{ position: "absolute", bottom: 300, ...side, width: w, height: h,
      borderRadius: 28, overflow: "hidden", border: `4px solid ${accent}`,
      boxShadow: `0 24px 60px -20px ${rgba("#000", 0.7)}, 0 0 0 10px ${rgba(bg, 0.6)}` }}>
      <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "top center" }} />
      <div style={{ position: "absolute", left: 12, bottom: 12, padding: "4px 12px", borderRadius: 999,
        background: accent, color: "#111", fontFamily: SANS, fontWeight: 800, fontSize: 22, letterSpacing: 1 }}>SOL</div>
    </div>
  );
};

export const cloneReelDuration = (p: CloneReelProps, fps: number): number =>
  Math.max(1, Math.round(p.blocks.reduce((a, b) => a + b.seconds, 0) * fps));

export const CloneReel: React.FC<CloneReelProps> = ({ title, theme = "cream", accent, bg, blocks, hostSrc, hostDefault = "pip", hostPos = "bl", karaoke }) => {
  const { fps } = useVideoConfig();
  const T = themeTokens(theme, accent, bg);
  let at = 0;
  return (
    <AbsoluteFill style={{ background: T.bg, fontFamily: SANS }}>
      <Fonts />
      {blocks.map((b, i) => {
        const from = Math.round(at * fps);
        const dur = Math.max(1, Math.round(b.seconds * fps));
        at += b.seconds;
        const props = { theme, accent, bg, ...(b.props ?? {}) };
        return (
          <Sequence key={i} from={from} durationInFrames={dur} layout="none">
            <AbsoluteFill>
              {hostSrc && (b.host ?? hostDefault) === "full" ? (
                <HostShot src={hostSrc} mode="full" pos={hostPos} accent={T.accent} bg={T.bg} />
              ) : null}
              <CookbookBlock id={b.id} props={props} transparent={b.transparent ?? true} />
              {hostSrc && (b.host ?? hostDefault) === "pip" ? (
                <HostShot src={hostSrc} mode="pip" pos={hostPos} accent={T.accent} bg={T.bg} />
              ) : null}
              {b.caption ? (
                <div
                  style={{
                    position: "absolute", left: 80, right: 80, bottom: 150, textAlign: "center",
                    fontFamily: SERIF, fontStyle: "italic", fontSize: 44, lineHeight: 1.2,
                    color: T.ink, textShadow: `0 2px 0 ${T.bg}`,
                  }}
                >
                  {b.caption}
                </div>
              ) : null}
            </AbsoluteFill>
          </Sequence>
        );
      })}
      {karaoke && karaoke.length ? (
        <ChipCaption chips={karaoke} accent={T.accent} />
      ) : null}
      {title ? (
        <div style={{ position: "absolute", left: 40, top: 40, fontSize: 24, letterSpacing: 2, color: T.mute, opacity: 0.8 }}>
          CLONE · {title}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

export const cloneReelDemo: CloneReelProps = {
  title: "demo",
  blocks: [
    { id: "BrandBumper", seconds: 2, props: { name: "AI UNPACKED", tagline: "one AI trick a day", glyph: "bolt" } },
    { id: "SplitHead", seconds: 3, props: { label: "HOW TO", line: "Build the whole workforce", punch: "workforce" } },
    { id: "StatCloser", seconds: 4, props: { value: 6069, prefix: "₹", label: "SPENT ON BLINKIT", sub: "in 6 orders" } },
  ],
};
export const CREAM_ACCENTS = CREAM;
