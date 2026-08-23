import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { BRAND, DISPLAY, rgba } from "./kit";
import { settle } from "./motion";

/* =============================================================================
   ChipCaption — the transcript as 1-3 word chips at one fixed anchor.

   THE GAP THIS CLOSES (Gap 2 of the reference study). KaraokeLine painted a
   full sentence and highlighted through it: a muted viewer had to read a
   paragraph while the graphics moved elsewhere. Every niche reference instead
   hard-swaps ONE chip of 1-3 words every 0.4-0.7s at a locked anchor, with one
   colour-flagged word that rhymes with an object in frame. Reading burden is
   near zero and the words land on VO stress like drum hits.

   LAWS THIS LAYER OWNS:
   - N1: the chips ARE the transcript, advancing 0.4-1.0s while VO is active.
   - U7: never more than 3 words on screen, y-anchor fixed for the whole film
     (the gate convicts >3% y-variance), nothing in the bottom 25%.
   - The CodeHype trick, free by construction: this layer is GLOBAL — mounted
     once above every scene, on the film clock — so a chip survives a hard cut
     and visibly bridges it, which is carry-grammar the viewer feels.

   The chip list is authored by the build (grouped from the measured VO word
   timings, 1-3 words, breaks on punctuation and >=0.25s pauses); this component
   only renders it. Hard swap: the outgoing chip simply stops existing — no
   crossfade, which would put six words on screen — and the incoming chip lands
   with a 4-frame scale-pop + settle.

   ANCHOR: chip baseline centred at y=1306 (68% of 1920) — the reference locus,
   well above both caption ceilings. Chips render in Anton caps at 64px, one
   accent word per chip, black under-glow for contrast on any canvas.
   ========================================================================== */

export type Chip = {
  /** film-absolute second the chip lands. */
  t: number;
  /** film-absolute second it clears; defaults to the next chip's t. */
  end?: number;
  /** 1-3 words. The build enforces the budget; this renders what it is given. */
  text: string;
  /** index of the accent word within text (space-split), or -1 for none. */
  hot?: number;
};

export type ChipCaptionProps = {
  chips: Chip[];
  /** y centre of the chip line. LOCKED per film — never vary it per beat. */
  anchorY?: number;
  size?: number;
  accent?: string;
};

export const ChipCaption: React.FC<ChipCaptionProps> = ({
  chips = [],
  anchorY = 1306,
  size = 64,
  accent = BRAND.mag,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  let cur: Chip | null = null;
  for (let i = 0; i < chips.length; i++) {
    const c = chips[i];
    const end = c.end ?? chips[i + 1]?.t ?? c.t + 1.4;
    if (t >= c.t && t < end) { cur = c; break; }
  }
  if (!cur) return null;

  // the landing: 2-frame pop-in, then the stamp settles. No fade — a chip is
  // either on screen or it is not, which is what keeps the word count at 3.
  const age = t - cur.t;
  const pop = Math.min(1, age * fps / 2);
  const sc = (0.94 + 0.06 * pop) * (1 + settle(t, cur.t, 0.4) * 0.045);
  const words = cur.text.split(" ").slice(0, 3);

  return (
    <div style={{
      position: "absolute", left: 0, right: 0, top: anchorY,
      display: "flex", justifyContent: "center",
      transform: `translateY(-50%) scale(${sc})`,
      opacity: pop,
      pointerEvents: "none",
      zIndex: 40,
    }}>
      <div style={{
        fontFamily: DISPLAY,
        fontSize: size,
        lineHeight: `${Math.round(size * 1.08)}px`,
        letterSpacing: 0.5,
        textTransform: "uppercase" as const,
        whiteSpace: "nowrap" as const,
        color: BRAND.paper,
        textShadow: `0 3px 22px ${rgba("#000", 0.85)}, 0 1px 4px ${rgba("#000", 0.9)}`,
      }}>
        {words.map((w, i) => (
          <span key={i} style={{ color: i === cur!.hot ? accent : undefined }}>
            {w}{i < words.length - 1 ? " " : ""}
          </span>
        ))}
      </div>
    </div>
  );
};

/* ---- the grouper's contract, documented for the build side -----------------
   build_ep_v2 turns vo_v2.words.json into chips:
   - break on sentence punctuation, on any inter-word gap >= 0.25s, and at 3 words
   - a chip's `t` is its first word's start; `end` is its last word's end + 0.12s
   - hot = index of the first word present in cfg["hot_words"], else -1
   - chips shorter than 0.34s merge forward (a 1-frame chip is a strobe)      */
