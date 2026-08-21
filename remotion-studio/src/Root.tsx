import React from "react";
import { AbsoluteFill, Composition, getInputProps, staticFile, useVideoConfig } from "remotion";
import { Short, ShortProps, totalDuration, Cover, Watermark } from "./Short";
import { StatBars, StatBarsProps } from "./components/StatBars";
import { CodeDemo, CodeDemoProps } from "./components/CodeDemo";
import { OutroCard, OutroCardProps } from "./components/OutroCard";
// visual cookbook (docs/COOKBOOK.md) — graphical b-roll components, each with a
// self-contained demo payload registered as a "<Name>Demo" composition below.
import { ChatApp, chatAppDemo } from "./cookbook/ChatApp";
import { LineReveal, lineRevealDemo } from "./cookbook/LineReveal";
import { CommandPalette, commandPaletteDemo } from "./cookbook/CommandPalette";
import { BentoGrid, bentoGridDemo } from "./cookbook/BentoGrid";
import { DiffReveal, diffRevealDemo } from "./cookbook/DiffReveal";
import { RingGauge, ringGaugeDemo } from "./cookbook/RingGauge";
import { Odometer, odometerDemo } from "./cookbook/Odometer";
import { OrbitNodes, orbitNodesDemo } from "./cookbook/OrbitNodes";
import { KineticQuote, kineticQuoteDemo } from "./cookbook/KineticQuote";
import { NotificationStack, notificationStackDemo } from "./cookbook/NotificationStack";
import { DynamicIsland, dynamicIslandDemo } from "./cookbook/DynamicIsland";
import { VoiceOrb, voiceOrbDemo } from "./cookbook/VoiceOrb";
import { SwipeDeck, swipeDeckDemo } from "./cookbook/SwipeDeck";
import { Fogline, foglineDemo } from "./cookbook/Fogline";
import { HoloCard, holoCardDemo } from "./cookbook/HoloCard";
import { GlassPanel, glassPanelDemo } from "./cookbook/GlassPanel";
import { MorphField, morphFieldDemo } from "./cookbook/MorphField";
import { ReactionMeter, reactionMeterDemo } from "./cookbook/ReactionMeter";
import { SpinWheel, spinWheelDemo } from "./cookbook/SpinWheel";
import { LedgerFlow, ledgerFlowDemo } from "./cookbook/LedgerFlow";
import { ShareSplit, shareSplitDemo } from "./cookbook/ShareSplit";
import { TapStack, tapStackDemo } from "./cookbook/TapStack";
import { CareerArc, careerArcDemo } from "./cookbook/CareerArc";
import { ProofTrace, proofTraceDemo } from "./cookbook/ProofTrace";
import { ContextTube, contextTubeDemo, ContextTubeProps } from "./cookbook/ContextTube";
import { FilmCanvas, CameraRig } from "./cookbook/FilmLayers";
import { WorldCamera, Parallax } from "./cookbook/WorldCamera";
import { ForgetsClay, forgetsClayDemo } from "./cookbook/ForgetsClay";
import { ClayOutro, clayOutroDemo } from "./cookbook/ClayOutro";
import { TravelSprite, MorphSwap, ExposureScore, FlashCut } from "./cookbook/craft";
import { ToyStage } from "./cookbook/Claylight";
import { PaperStage, OctoPuppet, PaperWord, PAPER } from "./cookbook/Kaagaz";
import { ZeroStackPaper, zeroStackPaperDemo } from "./cookbook/ZeroStackPaper";
import { BillDay, billDayDemo } from "./cookbook/BillDay";
import { DayOutro, dayOutroDemo } from "./cookbook/DayOutro";
import { CaseBullets, caseBulletsDemo } from "./cookbook/CaseBullets";
import { OutroGlass, outroGlassDemo } from "./cookbook/OutroGlass";
import { ScreenStage, screenStageDemo } from "./cookbook/ScreenStage";
import { GenerativeUI, generativeUIDemo } from "./cookbook/GenerativeUI";

const FPS = 30;

const fallback: ShortProps = {
  segments: [],
  captions: [],
  vo: "",
};

/* ---- LedgerFlow QC harness: one composition per phase, so each of the four
   re-layouts can be fixed in isolation before any beat authoring. The four
   share ONE row set on purpose — that is the component's whole thesis. */

/* ---- Fogline as the UPI SCAN (VJ 2026-08-20: "use the fogline component you
   invented"). Right call: Fogline's mechanic is blur = confidence, and "which
   rows did Claude actually read" IS a confidence statement. It also puts the
   DEDUPE on screen as a numbered result — the single best piece of teaching in
   the whole episode, which was otherwise buried in a reference file. Every
   `result` here is a real measured number from the 2026-08-20 legibility test. */
const FOGLINE_UPI = {
  runLabel: "READING 3 SCREENSHOTS · UPI HISTORY",
  currency: "\u20b9",
  spendDecimals: 0,
  lift: 0.62,
  doneTone: "#0E2A26",
  perStep: 0.85,
  horizon: 3,
  startAt: 1.15,
  steps: [
    { verb: "Read screenshot 1", detail: "18 Aug \u2192 15 Aug", params: "vision only \u00b7 nothing connected", result: "23 rows", dur: 1, cost: "" },
    { verb: "Read screenshot 2", detail: "15 Aug \u2192 11 Aug", params: "overlap with #1 detected", result: "24 rows", dur: 1, cost: "" },
    { verb: "Read screenshot 3", detail: "11 Aug \u2192 06 Aug", params: "", result: "19 rows", dur: 1, cost: "" },
    { verb: "Drop the sliced rows", detail: "cut in half at the crop edge", params: "never guessed", result: "2 skipped", dur: 1, cost: "" },
    { verb: "Remove the duplicates", detail: "same day \u00b7 same payee \u00b7 same amount", params: "the overlap counted them twice", result: "5 removed", dur: 3, cost: "" },
    { verb: "Hide the people", detail: "person-to-person transfers", params: "no names, ever", result: "1 line", dur: 1, cost: "" },
    { verb: "Group by merchant", detail: "food \u00b7 groceries \u00b7 shopping \u00b7 travel", params: "", result: "8 groups", dur: 2, cost: "" },
    { verb: "Total what was visible", detail: "a floor \u2014 not a bank statement", params: "", result: "\u20b912,640", dur: 2, cost: "" },
  ],
};


/* ---- EPISODE _upi — LOCKED 2026-08-20 -------------------------------------
   Every row below is a transaction that ACTUALLY APPEARS in VJ's own PhonePe
   history recording. Nothing here is invented: brandmarks.ts:17-19 — "Usage is
   nominative... Never imply endorsement. Never invent a transaction."
   Person-to-person rows carry merchant:"" and masked:true — the identity is
   absent from the PROPS, not hidden at render, so no name ever enters the repo.
   Source of truth: channels/claude-tricks/assets/ep_upi/locked_numbers.json */
const UPI_LANES = [
  { key: "blinkit", label: "BLINKIT", emoji: "\u{1F6F5}", tint: "#F8CB46" },
  { key: "other", label: "OTHER APPS", emoji: "\u{1F4F1}", tint: "#5FA82C" },
  { key: "food", label: "FOOD", emoji: "\u{1F37D}", tint: "#E23744" },
  { key: "shop", label: "SHOPPING", emoji: "\u{1F6CD}", tint: "#FF9900" },
];
const UPI_ROWS = [
  { id: "u01", merchant: "Blinkit", amount: 560, day: "18 AUG", cat: "blinkit", counted: true },
  { id: "u02", merchant: "Zomato", amount: 1072, day: "18 AUG", cat: "food", counted: true },
  { id: "u03", merchant: "Zomato", amount: 897, day: "18 AUG", cat: "food", counted: true },
  { id: "u04", merchant: "Amazon", amount: 1414, day: "18 AUG", cat: "shop", counted: true },
  { id: "u05", merchant: "", amount: 100, day: "18 AUG", masked: true },
  { id: "u06", merchant: "Blinkit", amount: 710, day: "17 AUG", cat: "blinkit", counted: true },
  { id: "u07", merchant: "Blinkit", amount: 649, day: "17 AUG", cat: "blinkit", counted: true },
  { id: "u08", merchant: "Snabbit", amount: 399, day: "17 AUG", cat: "other", counted: true },
  { id: "u09", merchant: "DMart", amount: 5931, day: "17 AUG", cat: "shop", counted: true },
  { id: "u10", merchant: "Blinkit", amount: 1843, day: "16 AUG", cat: "blinkit", counted: true },
  { id: "u11", merchant: "", amount: 2800, day: "16 AUG", masked: true },
  { id: "u12", merchant: "Maestro", amount: 199, day: "15 AUG", cat: "other", counted: true },
  { id: "u13", merchant: "Gas Bill", amount: 1500, day: "14 AUG", cat: "other", counted: true },
  { id: "u14", merchant: "Box8", amount: 372, day: "12 AUG", cat: "food", counted: true },
  { id: "u15", merchant: "Snabbit", amount: 248, day: "12 AUG", cat: "other", counted: true },
  { id: "u16", merchant: "", amount: 250, day: "12 AUG", masked: true },
  { id: "u17", merchant: "Snabbit", amount: 323, day: "09 AUG", cat: "other", counted: true },
  { id: "u18", merchant: "Blinkit", amount: 923, day: "03 AUG", cat: "blinkit", counted: true },
  { id: "u19", merchant: "Blinkit", amount: 1215, day: "03 AUG", cat: "blinkit", counted: true },
  { id: "u20", merchant: "Blinkit", amount: 841, day: "02 AUG", cat: "blinkit", counted: true },
  { id: "u21", merchant: "Blinkit", amount: 598, day: "02 AUG", cat: "blinkit", counted: true },
  { id: "u22", merchant: "Zepto", amount: 1560, day: "02 AUG", cat: "other", counted: true },
];
/* the four digits of 7339, one per beat — see locked_numbers.json digit_schedule */
const UPI_HUD = { label: "BLINKIT SO FAR", value: 7339, prefix: "\u20b9 " };
const UPI_BASE = {
  rows: UPI_ROWS, lanes: UPI_LANES, scrollFrom: 0, scrollTo: 0,
};
const UPI_RUSH = {
  ...UPI_BASE, phase: "rush" as const, ingest: { count: 3, at: 0 },
  scrollTo: 14, hud: { ...UPI_HUD, revealed: 0, revealAt: 0.79 },
  tally: { label: "ROWS READ", from: 0, to: 22 },
  claimLines: ["I SCREENSHOTTED", "MY UPI HISTORY"], claimHot: "UPI",
  contentStart: 0.37, claimHold: 2.15,
};
const UPI_FLOOR = {
  ...UPI_BASE, phase: "floor" as const, scrollFrom: 8, scrollTo: 8,
  hud: { ...UPI_HUD, revealed: 1, revealAt: 1.83 },
  bracket: { from: 2, to: 12, label: "WHAT THE SHOTS SHOWED", ghostLabel: "NOT IN THE PICTURES" },
  skipLabel: "DUPLICATE \u2014 SKIPPED",
  footNote: "FREE CHATS TRAIN THE MODEL \u2014 TURN IT OFF IN SETTINGS",
};
const UPI_SORT = {
  ...UPI_BASE, phase: "sort" as const, scrollFrom: 6, scrollTo: 6,
  hud: { ...UPI_HUD, revealed: 2, revealAt: 1.61 },
  host: "mock/host_wide.mp4", hostSize: 470, hostAnchor: "ml" as const,
  /* NOT a remembered guess — VJ never gave one, and inventing it after seeing
     the answer would fabricate the beat. This is the biggest SINGLE purchase in
     the same data (DMart, 17 Aug, Rs 5,931), which the eight small taps beat.
     True, already on screen elsewhere in the film, and a stronger reversal. */
  ghostGuess: { value: 5931, label: "ONE SUPERMARKET TRIP", killAt: 2.21, prefix: "\u20b9" },
};
const UPI_GROW = {
  ...UPI_BASE, phase: "grow" as const, scrollFrom: 6, scrollTo: 6,
  focusLane: "blinkit", hud: { ...UPI_HUD, revealed: 3, revealAt: 1.94 },
  spill: { atPct: 0.78, releaseAt: 1.4 },
  counter: { label: "BLINKIT ORDERS", to: 8, at: 0, roll: 0.7 },
  handoff: { w: 750, h: 930, at: 0.6 },
};
const UPI_SPLIT = {
  runLabel: "FROM MY OWN SCREENSHOTS",
  meta: [
    { k: "ROWS READ", v: "22" },
    { k: "SKIPPED", v: "3" },
    { k: "ORDERS", v: "8" },
    { k: "COST", v: "FREE" },
  ],
  total: { value: 7339, label: "BLINKIT", sub: "8 orders \u00b7 \u20b9917 a tap" },
  whole: { value: 25136, label: "SHOPS & APPS IN THESE SHOTS" },
  atoms: 8,
  shareLabel: "NEARLY A THIRD",
  openFrost: { w: 750, h: 930, dur: 0.5 },
  splitAt: 1.15,
  capSafe: 1200,
  atLeast: { at: 3.5, word: "", note: "A FLOOR \u2014 NOT A STATEMENT" },
  ghostBars: 5,
  /* host goes RIGHT here — the twist line starts at x=104 in the same y-band */
  host: "mock/host_wide.mp4", hostSize: 420, hostAnchor: "tr" as const,
  /* the remainder, by group — Blinkit Rs 7,339 lands almost exactly level with
     ALL shopping (Rs 7,345), which the eye catches before any label does */
  wholeParts: [
    { label: "SHOPPING", value: 7345, tint: "#FF9900" },
    { label: "OTHER APPS", value: 5164, tint: "#5FA82C" },
    { label: "FOOD", value: 2728, tint: "#E23744" },
    { label: "REST", value: 2560, tint: "#7A6B76" },
  ],
};

const LEDGER_RUSH = { ...ledgerFlowDemo, phase: "rush" as const };
const LEDGER_FLOOR = {
  ...ledgerFlowDemo,
  phase: "floor" as const,
  ingest: undefined,
  claimLines: undefined,
  scrollFrom: 8,
  scrollTo: 8,
  bracket: { from: 2, to: 15, label: "WHAT MY SCREENSHOTS SHOWED", ghostLabel: "NOT IN THE PICTURES" },
  hud: { label: "FOOD SO FAR", value: 4212, revealed: 0, revealAt: 1.6, prefix: "₹ " },
  tally: { label: "ROWS READ", from: 61, to: 61 },
  footNote: "FREE CHATS TRAIN THE MODEL — TURN IT OFF IN SETTINGS",
};
const LEDGER_SORT = {
  ...ledgerFlowDemo,
  phase: "sort" as const,
  ingest: undefined,
  claimLines: undefined,
  scrollFrom: 8,
  scrollTo: 8,
  hud: { label: "FOOD SO FAR", value: 4212, revealed: 1, revealAt: 1.8, prefix: "₹ " },
  tally: undefined,
  ghostGuess: { value: 900, label: "MY GUESS", killAt: 0.9, prefix: "₹" },
};
const LEDGER_GROW = {
  ...ledgerFlowDemo,
  phase: "grow" as const,
  ingest: undefined,
  claimLines: undefined,
  scrollFrom: 8,
  scrollTo: 8,
  focusLane: "food",
  hud: { label: "FOOD SO FAR", value: 4212, revealed: 2, revealAt: 1.5, prefix: "₹ " },
  tally: undefined,
  spill: { atPct: 0.78, releaseAt: 1.4 },
  counter: { label: "ORDERS", to: 41, at: 0.4 },
};

/* ---- StatBarsDemo: reference usage + QC harness for the locked chart spec.
   Deliberately stresses the edge cases: 6 bars (max density), a full-height bar
   (value label must flip inside-top), near-zero bars (labels ride the baseline),
   a delta pill, long-ish labels. Render 4s and eyeball: nothing may clip. */
const statBarsDemoProps: StatBarsProps = {
  title: "AI PRICE INDEX",
  subtitle: "$ PER 1M TOKENS · ILLUSTRATIVE",
  footer: "SAME QUESTIONS. LESS MONEY.",
  bars: [
    { label: "TOP TIER", value: 30, display: "$30", hot: true },
    { label: "FLAGSHIP", value: 25, display: "$25" },
    { label: "MID TIER", value: 14, display: "$14" },
    { label: "SMALL", value: 6, display: "$6" },
    { label: "FAST TIER", value: 1.4, display: "$1.40", delta: "-80%" },
    { label: "FREE", value: 0.4, display: "$0" },
  ],
  start: 0.3,
};

/* ---- CoverDemo: QC harness for the two-line hook stack. Renders Cover exactly
   as frame zero of a real episode does — same Anton face, same watermark on top
   — so a still of this comp IS the Shorts thumbnail preview (playbook §5).
   Pass a real episode's cover block via --props to QC that episode's frame zero;
   with no props it falls back to the LAZY payload shape (whole hook as one long
   title1, no title2) so the auto-split + autoshrink path stays covered. */
type CoverDemoProps = { c: NonNullable<ShortProps["cover"]> };

const coverDemoLazyProps: CoverDemoProps = {
  c: {
    title1: "THE BEST AI JUST GOT CHEAPER",
    sub: "pick right, pay less",
    emojis: "\u{1F4B8}\u{1F916}",
    until: 9999,
  },
};

const CoverDemoComp: React.FC<CoverDemoProps> = ({ c }) => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill>
      <style>{`
        @font-face { font-family: 'Anton'; src: url('${staticFile("fonts/Anton.ttf")}'); }
        @font-face { font-family: 'Playfair Display'; font-style: italic; font-weight: 400 900; src: url('${staticFile("fonts/PlayfairDisplay-Italic.ttf")}'); }
      `}</style>
      <Cover c={c} fps={fps} />
      <Watermark />
    </AbsoluteFill>
  );
};

// CodeDemo smoke-test default props — the real /premortem command + captured response
const codeDemoProps: CodeDemoProps = {
  commandKey: "premortem",
  fileLines: [
    "---",
    "description: Imagine the plan already",
    "  failed — work backward to find why",
    "argument-hint: [the plan or decision]",
    "---",
    "",
    "It is six months from now and this",
    "has failed badly: $ARGUMENTS",
    "",
    "Write the post-mortem from that future.",
  ],
  termArg: "launching my SaaS side project next month",
  responseLines: [
    "Dead by month 4 — 11 paying users, killed Stripe.",
    "Cause: Gmail ships free summaries the week you launch.",
    "Warning we ignore: 300 upvotes, only 4 convert to paid.",
    "2k followers ≠ buyers — peers, not inbox-drowning execs.",
    "Fix today: presell 15 annual seats before Product Hunt.",
  ],
};

/* the pilot's film view: the spine component ON its canvas, under the drift —
   what the storyboard stills and the studio preview should show, because the
   component alone on black is not the film. */
/* WorldCamera smoke test: five stations on a 3000x2400 world, three depths.
   Not a product composition — it exists so the camera can be SEEN working. */
const CamTestComp: React.FC = () => (
  <FilmCanvas>
    <WorldCamera
      track={[
        { t: 0, x: 540, y: 960, z: 1 },
        { t: 2.2, x: 1600, y: 700, z: 1.5 },
        { t: 4.2, x: 2400, y: 1500, z: 1.0 },
        { t: 6.0, x: 1200, y: 1800, z: 2.1, dur: 1.2 },
        { t: 8.0, x: 540, y: 960, z: 1 },
      ]}
      punches={[3.0, 7.0]}
    >
      <Parallax depth={0.35}>
        {[...Array(24)].map((_, i) => (
          <div key={i} style={{ position: "absolute", left: (i % 6) * 560 - 200, top: Math.floor(i / 6) * 700 - 200,
            width: 90, height: 90, borderRadius: 45, background: "rgba(45,224,245,0.12)" }} />
        ))}
      </Parallax>
      {[...Array(9)].map((_, i) => (
        <div key={i} style={{ position: "absolute", left: (i % 3) * 1000 + 140, top: Math.floor(i / 3) * 760 + 200,
          width: 760, height: 560, borderRadius: 28, background: "rgba(255,255,255,0.07)",
          border: "2px solid rgba(255,255,255,0.25)", display: "flex", alignItems: "center",
          justifyContent: "center", fontFamily: "Anton", fontSize: 220, color: "#F4F4FA" }}>{i + 1}</div>
      ))}
      <Parallax depth={1.5}>
        {[...Array(12)].map((_, i) => (
          <div key={i} style={{ position: "absolute", left: (i % 4) * 800 + 60, top: Math.floor(i / 4) * 900 + 60,
            width: 34, height: 34, borderRadius: 17, background: "rgba(255,46,154,0.65)" }} />
        ))}
      </Parallax>
    </WorldCamera>
  </FilmCanvas>
);

/* craft smoke test: a brick travels with physics, morphs into the jar, under
   an exposure score with a near-black breath. Not a product composition. */
/* the character test VJ asked for: the paper octopus, alive. ~9s. */
const OctoTestComp: React.FC = () => (
  <PaperStage>
    <OctoPuppet
      enterAt={0.2}
      poses={[
        { t: 0.2, x: 540, y: 980, s: 0.9, all: { curl: 0.9, reach: 0.5 } },
        { t: 0.9, s: 1, all: { curl: 0.1, reach: 1 } },
        { t: 2.2, lookX: -1, tilt: -4 },
        { t: 3.0, lookX: 1, tilt: 4 },
        { t: 3.9, mood: "glare", all: { curl: 0.75, reach: 0.85 }, tilt: 0, s: 0.96, lookX: 0 },
        { t: 5.0, mood: "wide", all: { curl: -0.35, reach: 1.18 }, s: 1.06 },
        { t: 6.4, mood: "calm", all: { curl: 0.12, reach: 1 }, s: 1,
          arms: { 2: { curl: -0.15, reach: 1.85, swing: -18 } } },
        { t: 8.2, all: { curl: 0.15, reach: 1 } },
      ]}
    />
    <div style={{
      position: "absolute", left: 700, top: 490, zIndex: 6,
      background: PAPER.green, color: "#F6EFE3",
      fontFamily: '"Fraunces", Georgia, serif', fontWeight: 700, fontSize: 40,
      padding: "18px 40px", borderRadius: 60,
      boxShadow: "0 8px 0 #2C4C41, 4px 12px 18px rgba(60,45,30,0.35)",
    }}>{"\u20B90 \u00B7 free"}</div>
    <PaperWord at={5.1} until={8.6} y={300} size={92} parts={[
      { text: "TEN" }, { text: "arms.", italic: true, color: PAPER.green },
      { text: "ZERO" }, { text: "rupees.", italic: true, color: PAPER.coralDeep },
    ]} />
  </PaperStage>
);

const CraftTestComp: React.FC = () => (
  <ToyStage>
    <ExposureScore keys={[[0, 1], [1.6, 1], [2.4, 0.18], [3.2, 1], [5.2, 0.9], [6.0, 1]]}>
      <TravelSprite src="assets/claylight/library/brick_cream.png" aspect={1.093} h={170}
        groundY={1100} seed={2}
        path={[
          { t: 0.3, x: 200, y: 1100, mode: "hold" },
          { t: 1.3, x: 540, y: 1100, mode: "ballistic" },
          { t: 2.6, x: 900, y: 1100, mode: "ballistic" },
          { t: 3.4, x: 900, y: 1100, mode: "hold" },
        ]}
        visibleTo={4.1} />
      <MorphSwap from={{ src: "assets/claylight/library/brick_cream.png", aspect: 1.093 }}
                 to={{ src: "assets/claylight/library/jar.png", aspect: 0.69 }}
                 at={4.4} x={900} y={1100} h={240} />
      <FlashCut at={[2.4]} opacity={0.35} />
    </ExposureScore>
  </ToyStage>
);

const ContextTubeFilmComp: React.FC<ContextTubeProps> = (p) => (
  <FilmCanvas>
    <CameraRig>
      <ContextTube {...p} />
    </CameraRig>
  </FilmCanvas>
);

export const RemotionRoot: React.FC = () => {
  const input = getInputProps() as unknown as ShortProps;
  const props = input && input.segments ? input : fallback;
  const frames = Math.max(1, Math.round(totalDuration(props) * FPS));
  return (
    <>
      <Composition
        id="Short"
        component={Short}
        durationInFrames={frames}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={props}
      />
      {/* v17 STYLE PRESETS — the SAME composition + SAME episode props, rendered
          with a different `style` token so the cast's remotion_comp slot offers a
          real visual choice. build_ep_v2 renders `npx remotion render <comp>
          --props=<beat spec>`; the beat spec has no top-level `style` key, so each
          composition's defaultProps.style survives the merge. `Short` stays classic
          (unchanged above); ShortBold/ShortMinimal only add the style override. */}
      <Composition
        id="ShortBold"
        component={Short}
        durationInFrames={frames}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{ ...props, style: "bold" }}
      />
      <Composition
        id="ShortMinimal"
        component={Short}
        durationInFrames={frames}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{ ...props, style: "minimal" }}
      />
      <Composition
        id="StatBarsDemo"
        component={StatBars}
        durationInFrames={4 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={statBarsDemoProps}
      />
      <Composition
        id="CoverDemo"
        component={CoverDemoComp}
        durationInFrames={2 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={coverDemoLazyProps}
      />
      <Composition
        id="CodeDemo"
        component={CodeDemo}
        durationInFrames={7 * FPS}
        fps={FPS}
        width={1080}
        height={1500}
        defaultProps={codeDemoProps}
      />
      <Composition
        id="OutroCard"
        component={OutroCard}
        durationInFrames={Math.round(4.2 * FPS)}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          avatar: "assets/character/host_library/outfit_11_sol_magenta/cropeed_center_final.jpeg",
          question: "Which command would you build first?",
          commentCta: "Comment your #1 👇",
          tagline: "one AI trick, every single day",
        }}
      />

      {/* ---- VISUAL COOKBOOK demos (docs/COOKBOOK.md) — parameterized graphical
          b-roll components. Preview with `npx remotion studio`; each is a drop-in
          for a beat's visual slot, driven entirely by its props contract. ---- */}
      <Composition
        id="ChatAppDemo"
        component={ChatApp}
        durationInFrames={7 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={chatAppDemo}
      />
      <Composition
        id="LineRevealDemo"
        component={LineReveal}
        durationInFrames={5 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={lineRevealDemo}
      />
      <Composition
        id="CommandPaletteDemo"
        component={CommandPalette}
        durationInFrames={5 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={commandPaletteDemo}
      />
      <Composition
        id="BentoGridDemo"
        component={BentoGrid}
        durationInFrames={4 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={bentoGridDemo}
      />
      <Composition
        id="DiffRevealDemo"
        component={DiffReveal}
        durationInFrames={6 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={diffRevealDemo}
      />
      <Composition
        id="RingGaugeDemo"
        component={RingGauge}
        durationInFrames={5 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={ringGaugeDemo}
      />
      <Composition
        id="OdometerDemo"
        component={Odometer}
        durationInFrames={4 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={odometerDemo}
      />
      <Composition
        id="OrbitNodesDemo"
        component={OrbitNodes}
        durationInFrames={6 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={orbitNodesDemo}
      />
      <Composition
        id="GenerativeUIDemo"
        component={GenerativeUI}
        durationInFrames={6 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={generativeUIDemo}
      />
      <Composition
        id="ScreenStageDemo"
        component={ScreenStage}
        durationInFrames={5 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={screenStageDemo}
      />
      <Composition
        id="OutroGlassDemo"
        component={OutroGlass}
        durationInFrames={9 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={outroGlassDemo}
      />
      <Composition
        id="ReactionMeterDemo"
        component={ReactionMeter}
        durationInFrames={6 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={reactionMeterDemo}
      />
      <Composition
        id="UpiRushDemo"
        component={LedgerFlow}
        durationInFrames={74}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={UPI_RUSH}
      />
      <Composition
        id="UpiFloorDemo"
        component={LedgerFlow}
        durationInFrames={110}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={UPI_FLOOR}
      />
      <Composition
        id="UpiSortDemo"
        component={LedgerFlow}
        durationInFrames={92}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={UPI_SORT}
      />
      <Composition
        id="UpiSplitDemo"
        component={ShareSplit}
        durationInFrames={169}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={UPI_SPLIT}
      />
      <Composition
        id="UpiGrowDemo"
        component={LedgerFlow}
        durationInFrames={151}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={UPI_GROW}
      />
      <Composition
        id="FoglineUpiDemo"
        component={Fogline}
        durationInFrames={8 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={FOGLINE_UPI}
      />
      <Composition
        id="CaseBulletsDemo"
        component={CaseBullets}
        durationInFrames={16 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={caseBulletsDemo}
      />
      <Composition
        id="CareerArcDemo"
        component={CareerArc}
        durationInFrames={10 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={careerArcDemo}
      />
      <Composition
        id="DayOutroDemo"
        component={DayOutro}
        durationInFrames={Math.round(6.8 * FPS)}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={dayOutroDemo}
      />
      <Composition
        id="BillDayFilm"
        component={BillDay}
        durationInFrames={33 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={billDayDemo}
      />
      <Composition
        id="ZeroStackPaperFilm"
        component={ZeroStackPaper}
        durationInFrames={35 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={zeroStackPaperDemo}
      />
      <Composition
        id="OctoTest"
        component={OctoTestComp}
        durationInFrames={9 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
      />
      <Composition
        id="CraftTest"
        component={CraftTestComp}
        durationInFrames={7 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
      />
      <Composition
        id="ClayOutroDemo"
        component={ClayOutro}
        durationInFrames={Math.round(6.8 * FPS)}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={clayOutroDemo}
      />
      <Composition
        id="ForgetsClayFilm"
        component={ForgetsClay}
        durationInFrames={30 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={forgetsClayDemo}
      />
      <Composition
        id="CamTest"
        component={CamTestComp}
        durationInFrames={9 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
      />
      <Composition
        id="ContextTubeFilm"
        component={ContextTubeFilmComp}
        durationInFrames={36 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={contextTubeDemo}
      />
      <Composition
        id="ContextTubeDemo"
        component={ContextTube}
        durationInFrames={36 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={contextTubeDemo}
      />
      <Composition
        id="ProofTraceDemo"
        component={ProofTrace}
        durationInFrames={12 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={proofTraceDemo}
      />
      <Composition
        id="TapStackDemo"
        component={TapStack}
        durationInFrames={77}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={tapStackDemo}
      />
      <Composition
        id="ShareSplitDemo"
        component={ShareSplit}
        durationInFrames={5 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={shareSplitDemo}
      />
      <Composition
        id="LedgerFlowRushDemo"
        component={LedgerFlow}
        durationInFrames={4 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={LEDGER_RUSH}
      />
      <Composition
        id="LedgerFlowFloorDemo"
        component={LedgerFlow}
        durationInFrames={4 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={LEDGER_FLOOR}
      />
      <Composition
        id="LedgerFlowSortDemo"
        component={LedgerFlow}
        durationInFrames={4 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={LEDGER_SORT}
      />
      <Composition
        id="LedgerFlowGrowDemo"
        component={LedgerFlow}
        durationInFrames={4 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={LEDGER_GROW}
      />
      <Composition
        id="SpinWheelDemo"
        component={SpinWheel}
        durationInFrames={5 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={spinWheelDemo}
      />
      <Composition
        id="KineticQuoteDemo"
        component={KineticQuote}
        durationInFrames={5 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={kineticQuoteDemo}
      />
      <Composition
        id="NotificationStackDemo"
        component={NotificationStack}
        durationInFrames={6 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={notificationStackDemo}
      />
      <Composition
        id="DynamicIslandDemo"
        component={DynamicIsland}
        durationInFrames={6 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={dynamicIslandDemo}
      />
      <Composition
        id="VoiceOrbDemo"
        component={VoiceOrb}
        durationInFrames={6 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={voiceOrbDemo}
      />
      <Composition
        id="SwipeDeckDemo"
        component={SwipeDeck}
        durationInFrames={5 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={swipeDeckDemo}
      />
      <Composition
        id="FoglineDemo"
        component={Fogline}
        durationInFrames={10 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={foglineDemo}
      />
      <Composition
        id="HoloCardDemo"
        component={HoloCard}
        durationInFrames={6 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={holoCardDemo}
      />
      <Composition
        id="GlassPanelDemo"
        component={GlassPanel}
        durationInFrames={6 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={glassPanelDemo}
      />
      <Composition
        id="MorphFieldDemo"
        component={MorphField}
        durationInFrames={5 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={morphFieldDemo}
      />
    </>
  );
};
