import React from "react";
import { AbsoluteFill } from "remotion";
import { ChatApp } from "./ChatApp";
import { LineReveal } from "./LineReveal";
import { CommandPalette } from "./CommandPalette";
import { BentoGrid } from "./BentoGrid";
import { DiffReveal } from "./DiffReveal";
import { RingGauge } from "./RingGauge";
import { Odometer } from "./Odometer";
import { OrbitNodes } from "./OrbitNodes";
import { KineticQuote } from "./KineticQuote";
import { NotificationStack } from "./NotificationStack";
import { DynamicIsland } from "./DynamicIsland";
import { VoiceOrb } from "./VoiceOrb";
import { SwipeDeck } from "./SwipeDeck";
import { Fogline } from "./Fogline";
import { HoloCard } from "./HoloCard";
import { GlassPanel } from "./GlassPanel";
import { MorphField } from "./MorphField";
import { ReactionMeter } from "./ReactionMeter";
import { LedgerFlow } from "./LedgerFlow";
import { ShareSplit } from "./ShareSplit";
import { SpinWheel } from "./SpinWheel";
import { OutroGlass } from "./OutroGlass";
import { ScreenStage } from "./ScreenStage";
import { TapStack } from "./TapStack";
import { CareerArc } from "./CareerArc";
import { GenerativeUI } from "./GenerativeUI";

/* =============================================================================
   COOKBOOK render dispatch — the id -> component map.

   registry.ts is METADATA ONLY (role/beats/needs/keywords, for pickCookbook).
   This is the render-time lookup that turns a locked cookbook block's `id`
   string (e.g. "LineReveal") into the actual React component, so a composition
   segment `{ kind:"cookbook", cookbook:{ id, props } }` can render inside Short.
   Keep this map in sync with registry.ts / COOKBOOK.md — one entry per component.
   ========================================================================== */
export const COOKBOOK_COMPONENTS: Record<string, React.FC<any>> = {
  ChatApp,
  LineReveal,
  CommandPalette,
  BentoGrid,
  DiffReveal,
  RingGauge,
  Odometer,
  OrbitNodes,
  KineticQuote,
  NotificationStack,
  DynamicIsland,
  VoiceOrb,
  SwipeDeck,
  Fogline,
  HoloCard,
  GlassPanel,
  MorphField,
  ReactionMeter,
  LedgerFlow,
  ShareSplit,
  SpinWheel,
  OutroGlass,
  ScreenStage,
  GenerativeUI,
  TapStack,
  CareerArc,
};

export type CookbookBlockProps = {
  id: string;
  props?: Record<string, unknown>;
  transparent?: boolean;
};

/* Render a cookbook component by id inside a composition beat. An unknown id
   renders a LOUD placeholder (never a silent blank), so a bad locked block is
   caught the moment it's previewed/rendered rather than shipping empty. */
export const CookbookBlock: React.FC<CookbookBlockProps> = ({ id, props, transparent }) => {
  const Comp = COOKBOOK_COMPONENTS[id];
  if (!Comp) {
    return (
      <AbsoluteFill
        style={{
          background: "#1a0b12",
          color: "#E0218A",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "ui-monospace, monospace",
          fontSize: 40,
          textAlign: "center",
          padding: 80,
          whiteSpace: "pre-line",
        }}
      >
        {`cookbook block\nunknown component "${id}"`}
      </AbsoluteFill>
    );
  }
  return <Comp transparent={transparent} {...(props ?? {})} />;
};
