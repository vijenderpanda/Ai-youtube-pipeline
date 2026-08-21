/* =============================================================================
   AI Unpacked — Motion Cookbook: the design-system entry.

   WHY THIS FILE EXISTS. Every component in src/cookbook is a REMOTION component:
   it reads `useCurrentFrame()` and `useVideoConfig()`, which only resolve inside
   a Remotion timeline. Imported into a plain React page they throw, so a design
   tool that renders live React cannot mount them directly — and a design system
   whose parts do not run is a picture book, not a library.

   `MotionStage` is the missing runtime. It mounts any cookbook component inside
   @remotion/player, which supplies the frame clock, so the component ANIMATES in
   the design surface exactly as it does in a render. That is not a workaround
   bolted on for the export: it is genuinely how you embed one of these on a web
   page, which makes it the honest thing for the design agent to build with.

   Nothing here reimplements a component. This file re-exports the real ones and
   adds the one wrapper they need to live outside a video.
   ========================================================================== */
import React from "react";
import { Player } from "@remotion/player";

/* ---- the shelf, re-exported verbatim ------------------------------------ */
export { BentoGrid } from "./cookbook/BentoGrid";
export { ChatApp } from "./cookbook/ChatApp";
export { CommandPalette } from "./cookbook/CommandPalette";
export { DiffReveal } from "./cookbook/DiffReveal";
export { DynamicIsland } from "./cookbook/DynamicIsland";
export { Fogline } from "./cookbook/Fogline";
export { GenerativeUI } from "./cookbook/GenerativeUI";
export { GlassPanel } from "./cookbook/GlassPanel";
export { HoloCard } from "./cookbook/HoloCard";
export { KineticQuote } from "./cookbook/KineticQuote";
export { LedgerFlow } from "./cookbook/LedgerFlow";
export { LineReveal } from "./cookbook/LineReveal";
export { MorphField } from "./cookbook/MorphField";
export { NotificationStack } from "./cookbook/NotificationStack";
export { Odometer } from "./cookbook/Odometer";
export { OrbitNodes } from "./cookbook/OrbitNodes";
export { OutroGlass } from "./cookbook/OutroGlass";
export { ReactionMeter } from "./cookbook/ReactionMeter";
export { RingGauge } from "./cookbook/RingGauge";
export { ScreenStage } from "./cookbook/ScreenStage";
export { ShareSplit } from "./cookbook/ShareSplit";
export { SpinWheel } from "./cookbook/SpinWheel";
export { SwipeDeck } from "./cookbook/SwipeDeck";
export { TapStack } from "./cookbook/TapStack";
export { VoiceOrb } from "./cookbook/VoiceOrb";


/* ---- the repo's own canonical props ------------------------------------
   Every component already ships a demo object that production beats were
   authored against. Re-exporting them means a preview card shows the REAL
   composition this library uses, not one invented for the export — and the
   design agent gets a working starting point per component instead of having
   to guess a prop shape from the type alone. */
export { bentoGridDemo } from "./cookbook/BentoGrid";
export { chatAppDemo } from "./cookbook/ChatApp";
export { commandPaletteDemo } from "./cookbook/CommandPalette";
export { diffRevealDemo } from "./cookbook/DiffReveal";
export { dynamicIslandDemo } from "./cookbook/DynamicIsland";
export { foglineDemo } from "./cookbook/Fogline";
export { generativeUIDemo } from "./cookbook/GenerativeUI";
export { glassPanelDemo } from "./cookbook/GlassPanel";
export { holoCardDemo } from "./cookbook/HoloCard";
export { kineticQuoteDemo } from "./cookbook/KineticQuote";
export { ledgerFlowDemo } from "./cookbook/LedgerFlow";
export { lineRevealDemo } from "./cookbook/LineReveal";
export { morphFieldDemo } from "./cookbook/MorphField";
export { notificationStackDemo } from "./cookbook/NotificationStack";
export { odometerDemo } from "./cookbook/Odometer";
export { orbitNodesDemo } from "./cookbook/OrbitNodes";
export { outroGlassDemo } from "./cookbook/OutroGlass";
export { reactionMeterDemo } from "./cookbook/ReactionMeter";
export { ringGaugeDemo } from "./cookbook/RingGauge";
export { screenStageDemo } from "./cookbook/ScreenStage";
export { shareSplitDemo } from "./cookbook/ShareSplit";
export { spinWheelDemo } from "./cookbook/SpinWheel";
export { swipeDeckDemo } from "./cookbook/SwipeDeck";
export { tapStackDemo } from "./cookbook/TapStack";
export { voiceOrbDemo } from "./cookbook/VoiceOrb";

/* ---- the tokens, so the design agent styles its own glue on-brand ------- */
export { BRAND, SANS, MONO, DISPLAY, SERIF, rgba, clamp, SAFE } from "./cookbook/kit";

export type MotionStageProps = {
  /** The cookbook component to run. Pass the component itself, not an element. */
  component: React.ComponentType<any>;
  /** Props handed to that component, exactly as a production beat would. */
  componentProps?: Record<string, unknown>;
  /** Beat length in seconds. Cookbook beats run 2-7s; 5 is a fair default. */
  durationInSeconds?: number;
  /** Rendered size in the page. The composition is always authored 1080x1920 —
   *  a vertical Short — and is scaled to fit this box. */
  width?: number;
  height?: number;
  fps?: number;
  loop?: boolean;
  autoPlay?: boolean;
  /** Frame to park on when `autoPlay` is false. Most components animate IN, so
   *  frame 0 is deliberately empty — a still of frame 0 shows nothing and reads
   *  as a broken component. Pick a frame where the beat has resolved. */
  initialFrame?: number;
};

/**
 * Mount a cookbook component so it runs on a web page.
 *
 * The composition is fixed at 1080x1920 because that is what every component in
 * this library is authored against — the safe zones (`SAFE.headerFloor` 132,
 * `SAFE.captionCeil` 1580) are absolute pixel values in that frame, so scaling
 * the BOX is correct and changing the composition size is not.
 *
 * ```tsx
 * <MotionStage component={SpinWheel} componentProps={{ options: [...] }} />
 * ```
 */
export const MotionStage: React.FC<MotionStageProps> = ({
  component,
  componentProps = {},
  durationInSeconds = 5,
  width = 270,
  height = 480,
  fps = 30,
  loop = true,
  autoPlay = true,
  initialFrame = 0,
}) => (
  <Player
    component={component as React.ComponentType<Record<string, unknown>>}
    inputProps={componentProps}
    durationInFrames={Math.max(1, Math.round(durationInSeconds * fps))}
    compositionWidth={1080}
    compositionHeight={1920}
    fps={fps}
    style={{ width, height, borderRadius: 14, overflow: "hidden" }}
    loop={loop}
    autoPlay={autoPlay}
    initialFrame={initialFrame}
    controls={false}
    showVolumeControls={false}
    clickToPlay={false}
    doubleClickToFullscreen={false}
    acknowledgeRemotionLicense
  />
);
