import React from "react";
import { AbsoluteFill, Sequence, useVideoConfig } from "remotion";
import { CookbookBlock } from "./cookbook/components";
import { CREAM, Fonts, SANS, SERIF, themeTokens, CookTheme } from "./cookbook/kit";

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
};

export type CloneReelProps = {
  title?: string; // tiny provenance tag, top-left
  theme?: CookTheme;
  accent?: string;
  bg?: string;
  blocks: CloneBlock[];
};

export const cloneReelDuration = (p: CloneReelProps, fps: number): number =>
  Math.max(1, Math.round(p.blocks.reduce((a, b) => a + b.seconds, 0) * fps));

export const CloneReel: React.FC<CloneReelProps> = ({ title, theme = "cream", accent, bg, blocks }) => {
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
              <CookbookBlock id={b.id} props={props} transparent={b.transparent ?? true} />
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
