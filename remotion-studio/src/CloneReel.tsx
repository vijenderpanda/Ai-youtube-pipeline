import React from "react";
import { AbsoluteFill, Img, OffthreadVideo, Sequence, staticFile, useVideoConfig } from "remotion";
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
  host?: "full" | "pip" | "none" | "split"; // host presence on this beat (overrides reel default)
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
  hostDefault?: "full" | "pip" | "none" | "split"; // presence when a block doesn't set its own (default "pip")
  hostPos?: "bl" | "br"; // pip corner (default "bl")
  /** Tight head-and-shoulders host close-up, used for the `split` layout's bottom band
   *  (Vaibhav split-screen grammar: graphic top ~62%, host close-up bottom ~38%). */
  hostCloseupSrc?: string; // e.g. "hosts/sol_closeup.jpg"
  /** Global yellow word-highlight karaoke, on the film clock (from VO word timings). */
  karaoke?: Chip[];
};

/* Host render per the cutaway grammar (research/comp-dna/HOST-PLACEMENT.md):
   - "full" = the dominant talking-head shot (host fills the lower frame, text overlays above);
     stands in for the real HeyGen Sol clip that composites at full render.
   - "pip"  = a small corner window (dev-tips variant only).
   The graphic beats pass host:"none" → nothing renders (hard cutaway to graphic-full). */
const isVideo = (s: string) => /\.(mp4|webm|mov)$/i.test(s);
const HostMedia: React.FC<{ src: string; startSec?: number; style: React.CSSProperties }> = ({ src, startSec = 0, style }) => {
  const { fps } = useVideoConfig();
  return isVideo(src)
    ? <OffthreadVideo src={staticFile(src)} startFrom={Math.round(startSec * fps)} muted style={style} />
    : <Img src={staticFile(src)} style={style} />;
};
const HostShot: React.FC<{ src: string; mode: "full" | "pip"; pos: "bl" | "br"; accent: string; bg: string; startSec?: number }> = ({ src, mode, pos, accent, bg, startSec }) => {
  const mediaStyle = (extra: React.CSSProperties): React.CSSProperties => ({ objectFit: "cover", objectPosition: "top center", ...extra });
  if (mode === "full") {
    // A full 9:16 studio host scene fills the whole frame (Vaibhav grammar: desk + studio +
    // dark headroom for the title). Slow Ken-Burns so a still reads as alive.
    return (
      <AbsoluteFill style={{ overflow: "hidden" }}>
        <div style={{ position: "absolute", inset: 0, transform: "scale(1.06)", transformOrigin: "50% 42%",
          animation: undefined }}>
          <HostMedia src={src} startSec={startSec} style={mediaStyle({ width: 1080, height: 1920 })} />
        </div>
        {/* darken the top headroom a touch so the claim/title always reads */}
        <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0) 34%)" }} />
      </AbsoluteFill>
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

export const CloneReel: React.FC<CloneReelProps> = ({ title, theme = "cream", accent, bg, blocks, hostSrc, hostDefault = "pip", hostPos = "bl", hostCloseupSrc, karaoke }) => {
  const { fps } = useVideoConfig();
  const T = themeTokens(theme, accent, bg);
  let at = 0;
  return (
    <AbsoluteFill style={{ background: T.bg, fontFamily: SANS }}>
      <Fonts />
      {blocks.map((b, i) => {
        const beatStart = at;
        const from = Math.round(at * fps);
        const dur = Math.max(1, Math.round(b.seconds * fps));
        at += b.seconds;
        const props = { theme, accent, bg, ...(b.props ?? {}) };
        const hostMode = b.host ?? hostDefault;
        // Vaibhav split layout: graphic clipped to the top ~60%, host MEDIUM shot in the bottom ~40%.
        // Use the wide studio scene (hostCloseupSrc override wins) so the host reads as a
        // pulled-back medium shot (head + shoulders + chest + desk), NOT a tight face.
        const splitHostSrc = hostCloseupSrc ?? hostSrc ?? "hosts/sol_studio.jpg";
        if (hostMode === "split") {
          const TOP = 1150; // ~60% of 1920 — host band a touch taller for the medium shot
          return (
            <Sequence key={i} from={from} durationInFrames={dur} layout="none">
              <AbsoluteFill style={{ background: T.bg }}>
                <div style={{ position: "absolute", top: 0, left: 0, width: 1080, height: TOP, overflow: "hidden" }}>
                  <CookbookBlock id={b.id} props={props} transparent={b.transparent ?? true} />
                </div>
                <div style={{ position: "absolute", top: TOP, left: 0, width: 1080, height: 1920 - TOP,
                  overflow: "hidden", borderTop: `2px solid ${rgba(T.accent, 0.5)}` }}>
                  {/* Zoom OUT: scale the wide studio scene down so the head→desk (hands) region fills
                      the band — Vaibhav's pulled-back medium shot, not a tight face. */}
                  {(() => {
                    const BH = 1920 - TOP;            // band height (~770)
                    const REGION = 0.60;              // show 60% of the source height (head→desk)
                    const S = BH / (1920 * REGION);   // scale so that region fills the band height
                    const W = Math.round(1080 * S);
                    return (
                      <HostMedia src={splitHostSrc} startSec={beatStart}
                        style={{ position: "absolute", width: W, height: Math.round(1920 * S),
                          left: (1080 - W) / 2, top: -Math.round(0.22 * 1920 * S), objectFit: "cover" }} />
                    );
                  })()}
                  <div style={{ position: "absolute", inset: 0, background: `linear-gradient(180deg, ${rgba(T.bg, 0.9)} 0%, rgba(0,0,0,0) 16%)` }} />
                </div>
              </AbsoluteFill>
            </Sequence>
          );
        }
        return (
          <Sequence key={i} from={from} durationInFrames={dur} layout="none">
            <AbsoluteFill>
              {hostSrc && hostMode === "full" ? (
                <HostShot src={hostSrc} mode="full" pos={hostPos} accent={T.accent} bg={T.bg} startSec={beatStart} />
              ) : null}
              <CookbookBlock id={b.id} props={props} transparent={b.transparent ?? true} />
              {hostSrc && hostMode === "pip" ? (
                <HostShot src={hostSrc} mode="pip" pos={hostPos} accent={T.accent} bg={T.bg} startSec={beatStart} />
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
