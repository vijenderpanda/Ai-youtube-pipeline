/* =============================================================================
   COOKBOOK_DEMOS — id -> the component's exported demo props.

   Single source for placeholder content: the auto-compose button (webapp
   SequenceEditor) seeds each picked block with its component's demo props so the
   composed sequence is immediately renderable/previewable, then the operator
   refines. Kept beside components.tsx (the id -> component map); one entry per
   registered component. This file imports the component modules (remotion), so
   the webapp lazy-imports it (dynamic import) to keep it out of the main bundle.
   ========================================================================== */
import { chatAppDemo } from "./ChatApp";
import { lineRevealDemo } from "./LineReveal";
import { commandPaletteDemo } from "./CommandPalette";
import { bentoGridDemo } from "./BentoGrid";
import { diffRevealDemo } from "./DiffReveal";
import { ringGaugeDemo } from "./RingGauge";
import { odometerDemo } from "./Odometer";
import { orbitNodesDemo } from "./OrbitNodes";
import { kineticQuoteDemo } from "./KineticQuote";
import { notificationStackDemo } from "./NotificationStack";
import { dynamicIslandDemo } from "./DynamicIsland";
import { voiceOrbDemo } from "./VoiceOrb";
import { swipeDeckDemo } from "./SwipeDeck";
import { foglineDemo } from "./Fogline";
import { holoCardDemo } from "./HoloCard";
import { glassPanelDemo } from "./GlassPanel";
import { morphFieldDemo } from "./MorphField";

// deno-lint-ignore no-explicit-any
export const COOKBOOK_DEMOS: Record<string, any> = {
  ChatApp: chatAppDemo,
  LineReveal: lineRevealDemo,
  CommandPalette: commandPaletteDemo,
  BentoGrid: bentoGridDemo,
  DiffReveal: diffRevealDemo,
  RingGauge: ringGaugeDemo,
  Odometer: odometerDemo,
  OrbitNodes: orbitNodesDemo,
  KineticQuote: kineticQuoteDemo,
  NotificationStack: notificationStackDemo,
  DynamicIsland: dynamicIslandDemo,
  VoiceOrb: voiceOrbDemo,
  SwipeDeck: swipeDeckDemo,
  Fogline: foglineDemo,
  HoloCard: holoCardDemo,
  GlassPanel: glassPanelDemo,
  MorphField: morphFieldDemo,
};
