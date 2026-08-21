import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { rgba, clamp } from "./kit";
import { clamp01, mhash, OUT_E, IN_E } from "./motion";
import {
  CLAY, ToyStage, SpriteLayer, SlabScreen, ChipClay, CounterClay, ClayChip,
} from "./Claylight";
import { WorldCamera, Parallax } from "./WorldCamera";

/* =============================================================================
   ForgetsClay — the pilot film in the CLAYLIGHT world.

   "Why Claude Forgets Long Chats", re-skinned per the fresh-start verdict
   (docs/MOTION-PIPELINE.md PART III). Toy box = the context window; clay
   message-bubble bricks = your messages; the CORAL brick = the first thing you
   told it (the one coral object of the episode — the carry element); the slab
   = real captures, witnessed; the jar of notes = the payoff, and the GIVE.

   THE ONE MEASURED NUMBER: the counter fills toward 200,000 — Claude's
   documented context window (Anthropic docs). Declared in the manifest's
   numbers[] with that source; Plex Mono renders nothing else in this film.

   The world plane is 1080x1920 at author scale; WorldCamera dollies it. All
   times arrive film-absolute via props resolved from the VO clock.
   ========================================================================== */

const LIB = "assets/claylight/library";
const BOX = { x: 400, y: 1250, h: 600, aspect: 0.828 };
/* the sprite's mouth: the body's opening sits at ~0.68h of the image, so with
   the box 600 tall its rim is at boxTop + 408. Bricks live BETWEEN the full
   box sprite (back, z4) and the front-wall crop (z12): they drop into the
   mouth, their torsos hidden by the front wall, tops peeking above the rim —
   the fill is told by a rising skyline. */
const BOX_TOP = BOX.y - BOX.h;
const RIM_Y = BOX_TOP + BOX.h * 0.68;      // 1058
const MOUTH = { x: BOX.x, y: RIM_Y + 10 };

export type ForgetsClayProps = {
  hookCapture?: string;        // the long-chat auto-scroll on the slab
  proofCapture?: string;       // the first-message miss, full frame
  payoffCapture?: string;      // the summary prompt working
  captureVideo?: boolean;
  staged?: boolean;            // true until the final claude.ai captures land
  provenance?: string;
  coralAt?: number;            // the coral brick lands
  kneeAt?: number;             // counter digit-roll + knee snap (U9, ~6.00s)
  fullAt?: number;             // the box reads FULL (amber state)
  coralOutAt?: number;         // the loss: coral tips over the back rim
  diveAt?: number;             // zoom-through into the box mouth
  proofAt?: number;            // full-frame proof capture
  pullAt?: number;             // reverse dolly: the jar revealed
  payoffAt?: number;           // mint moment on the payoff capture
  loopAt?: number;             // composition returns to frame 1
  endAt?: number;
  chips?: ClayChip[];
  /** [t, tokens] — measured fill keys; 200,000 is the documented limit. */
  counterKeys?: [number, number][];
  start?: number;
  width?: number;
  height?: number;
};

export const ForgetsClay: React.FC<ForgetsClayProps> = ({
  hookCapture = "assets/ep_style/demo.mp4",
  proofCapture = "assets/ep_style/demo.mp4",
  payoffCapture = "assets/ep_style/demo.mp4",
  captureVideo = true,
  staged = true,
  provenance = "STAND-IN — final: claude.ai",
  coralAt = 2.2,
  kneeAt = 6.0,
  fullAt = 8.6,
  coralOutAt = 13.9,
  diveAt = 16.9,
  proofAt = 17.5,
  pullAt = 20.6,
  payoffAt = 22.4,
  loopAt = 25.4,
  endAt = 28.2,
  chips = [],
  counterKeys = [[1.6, 31000], [5.9, 176000], [6.05, 200000]],
  start = 0,
  width = 1080,
  height = 1920,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - start;

  /* ---- brick schedule: one per VO stretch pre-full, then a dense burst ----
     Deterministic, derived from the anchors. Bricks stack BEHIND the box and
     peek above the mouth — a flat sprite cannot contain them, so the fill is
     told by the rising skyline of brick tops. */
  const bricks: { t: number; dx: number; by: number; coral?: boolean }[] = [];
  {
    // each brick lands INSIDE the mouth; later bricks land higher, so the
    // skyline of peeking tops rises as the box fills
    const n = 5;
    for (let i = 0; i < n; i++) {
      const tt = 0.15 + ((kneeAt - 1.2 - 0.15) * i) / (n - 1);
      bricks.push({ t: tt, dx: -30 + (mhash(i * 3 + 1) - 0.5) * 140, by: RIM_Y + 150 - i * 24 });
    }
    bricks.push({ t: coralAt, dx: -46, by: RIM_Y + 96, coral: true });
    // the post-knee burst: the box crowds, tops jostling above the rim
    for (let i = 0; i < 4; i++) {
      bricks.push({ t: kneeAt + 0.25 + i * 0.5, dx: -30 + (mhash(i * 7 + 11) - 0.5) * 150, by: RIM_Y + 30 - i * 18 });
    }
  }

  /* ---- camera ------------------------------------------------------------ */
  const dive = clamp01((t - diveAt - 0.12) / 0.4);
  const proofOn = clamp01((t - proofAt) / 0.3);
  const proofOff = clamp01((t - pullAt) / 0.5);
  const track = [
    { t: 0, x: 540, y: 930, z: 1 },
    { t: coralAt + 0.6, x: 470, y: 980, z: 1.14 },       // shelf dolly toward the box
    { t: kneeAt, x: 450, y: 960, z: 1.2 },
    { t: fullAt + 1.2, x: 460, y: 940, z: 1.16 },
    { t: coralOutAt - 0.3, x: 430, y: 860, z: 1.3 },     // closer for the loss
    { t: diveAt, x: 430, y: 880, z: 1.3 },
    { t: diveAt + 0.6, x: MOUTH.x, y: MOUTH.y + 60, z: 5.4, dur: 0.6 },   // THE DIVE
    { t: pullAt, x: MOUTH.x, y: MOUTH.y + 60, z: 5.4 },
    { t: pullAt + 0.9, x: 620, y: 950, z: 1.02, dur: 0.9 },               // the only reverse dolly
    { t: loopAt + 0.8, x: 540, y: 930, z: 1, dur: 0.8 },                  // home = frame 1
  ];

  const amberBox = t >= fullAt && t < diveAt;

  return (
    <AbsoluteFill style={{ width, height }}>
      <ToyStage>
        <WorldCamera track={track} punches={[kneeAt, coralOutAt]} punchScale={1.12}>
          {/* far shelf props — depth only, never story */}
          <Parallax depth={0.45}>
            <SpriteLayer src={`${LIB}/jar.png`} x={118} y={470} h={200} aspect={1}
                         opacity={0.35} seed={9} idleAmp={1} />
          </Parallax>

          {/* the box BACK — the whole sprite, behind the bricks */}
          <SpriteLayer src={`${LIB}/toybox.png`} x={BOX.x} y={BOX.y} h={BOX.h}
                       aspect={BOX.aspect} state={amberBox ? "amber" : "neutral"}
                       seed={1} zIndex={4} idleAmp={0.8} />

          {/* the bricks — INSIDE the mouth, torsos occluded by the front wall */}
          {bricks.map((b, i) => (
            <SpriteLayer key={i}
              src={b.coral ? `${LIB}/brick_coral.png` : `${LIB}/brick_cream.png`}
              x={BOX.x + b.dx} y={b.by} h={b.coral ? 195 : 170} aspect={1}
              enterAt={b.t}
              exitAt={b.coral ? coralOutAt : undefined}
              exitStyle={b.coral ? "eject" : "fall"}
              state={b.coral ? undefined : amberBox ? "amber" : "neutral"}
              seed={i + 2} zIndex={6}
            />
          ))}

          {/* the box FRONT — the wall crop that makes the fill real */}
          <SpriteLayer src={`${LIB}/toybox_front.png`} x={BOX.x} y={BOX.y} h={BOX.h}
                       aspect={BOX.aspect} state={amberBox ? "amber" : "neutral"}
                       seed={1} zIndex={12} idleAmp={0.8} />

          {/* the slab, upper right: the hook capture, then — after the pull —
              the payoff capture (the summary prompt working), re-dropped so the
              swap is an event rather than a jump */}
          {t < pullAt ? (
            <SlabScreen capture={hookCapture} video={captureVideo}
                        x={772} y={664} h={400} aspect={1} zIndex={8}
                        provenance={provenance} staged={staged} spill="#2f3540" />
          ) : (
            <SlabScreen capture={payoffCapture} video={captureVideo}
                        x={772} y={664} h={400} aspect={1} zIndex={8}
                        enterAt={pullAt + 0.25}
                        provenance={provenance} staged={staged} spill="#2f4a40" />
          )}

          {/* the mint pulse — the payoff EARNS its colour */}
          {t >= payoffAt && t < payoffAt + 0.9 ? (() => {
            const p = clamp01((t - payoffAt) / 0.9);
            return <div style={{
              position: "absolute", left: 780 - 320, top: 1265 - 660, width: 640, height: 640,
              borderRadius: "50%", zIndex: 9,
              background: `radial-gradient(50% 50% at 50% 50%, ${rgba(CLAY.mint, 0.34 * (1 - p))} 0%, ${rgba(CLAY.mint, 0)} 70%)`,
            }} />;
          })() : null}

          {/* the jar arrives for the payoff, in the lamplight */}
          {t >= pullAt ? (
            <SpriteLayer src={`${LIB}/jar.png`} x={780} y={1265} h={440} aspect={1}
                         enterAt={pullAt + 0.5} state={t >= payoffAt ? "mint" : "neutral"}
                         seed={4} zIndex={10} />
          ) : null}

          {/* the counter — the one measured number in the film */}
          <div style={{ position: "absolute", left: 640, top: 1085, whiteSpace: "nowrap", opacity: t < diveAt ? 1 : 0 }}>
            <CounterClay keys={counterKeys} label="CONTEXT · LIMIT 200K" x={0} y={0} size={46} />
          </div>
        </WorldCamera>

        {/* the mouth-dark we dive into, then the full-frame proof capture */}
        {dive > 0 && proofOff < 1 ? (
          <AbsoluteFill style={{ background: rgba("#0B0709", Math.min(dive * 1.4, 1) * (1 - proofOff)), zIndex: 18 }} />
        ) : null}
        {proofOn > 0 && proofOff < 1 ? (
          <div style={{
            position: "absolute", left: 40, top: 260, width: 1000, height: 1210, zIndex: 20,
            opacity: proofOn * (1 - proofOff),
            transform: `scale(${(0.96 + 0.04 * OUT_E(proofOn)).toFixed(3)})`,
            borderRadius: 26, overflow: "hidden",
            boxShadow: `0 60px 130px -60px ${rgba("#000", 0.95)}`,
          }}>
            <SlabProofFull capture={proofCapture} video={captureVideo} />
            <div style={{
              position: "absolute", left: 26, bottom: 18, fontFamily: '"IBM Plex Mono", monospace',
              fontSize: 21, letterSpacing: 2,
              color: staged ? rgba(CLAY.cream, 0.65) : rgba(CLAY.mint, 0.9),
            }}>{staged ? "STAGED" : "✓ REAL CAPTURE"} · {provenance}</div>
          </div>
        ) : null}

        <ChipClay chips={chips} />
      </ToyStage>
    </AbsoluteFill>
  );
};

/* the full-frame proof media, kept dumb on purpose */
const SlabProofFull: React.FC<{ capture: string; video?: boolean }> = ({ capture, video }) => {
  const { OffthreadVideo, Img, staticFile } = require("remotion");
  return video ? (
    <OffthreadVideo src={staticFile(capture)} muted startFrom={90}
                    style={{ width: "100%", height: "100%", objectFit: "cover" }} />
  ) : (
    <Img src={staticFile(capture)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
  );
};

/* ---- canonical demo (planned clock) -------------------------------------- */
export const forgetsClayDemo: ForgetsClayProps = {
  coralAt: 2.2,
  kneeAt: 6.0,
  fullAt: 8.6,
  coralOutAt: 13.9,
  diveAt: 16.9,
  proofAt: 17.5,
  pullAt: 20.6,
  payoffAt: 22.4,
  loopAt: 25.4,
  endAt: 28.2,
  chips: [
    { t: 0.2, end: 1.6, text: "IT FORGOT.", hot: true },
    { t: 1.8, end: 3.2, text: "EVERY MESSAGE" },
    { t: 3.3, end: 4.6, text: "A BLOCK" },
    { t: 4.8, end: 6.0, text: "THE LIMIT" },
    { t: 6.05, end: 7.4, text: "200K", hot: true },
    { t: 8.7, end: 10.0, text: "FULL" },
    { t: 10.2, end: 12.0, text: "NO ROOM" },
    { t: 12.6, end: 13.9, text: "THE OLDEST" },
    { t: 14.1, end: 15.6, text: "YOURS.", hot: true },
    { t: 17.6, end: 19.4, text: "IT CAN'T SEE IT" },
    { t: 21.2, end: 22.4, text: "NOTES." },
    { t: 22.6, end: 24.4, text: "IT REMEMBERS", hot: true },
    { t: 25.6, end: 27.6, text: "PROMPT BELOW" },
  ],
};
