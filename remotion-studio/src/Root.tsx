import React from "react";
import { AbsoluteFill, Composition, getInputProps, staticFile, useVideoConfig } from "remotion";
import { Short, ShortProps, totalDuration, Cover, Watermark } from "./Short";
import { StatBars, StatBarsProps } from "./components/StatBars";
import { CodeDemo, CodeDemoProps } from "./components/CodeDemo";
import { OutroCard, OutroCardProps } from "./components/OutroCard";

const FPS = 30;

const fallback: ShortProps = {
  segments: [],
  captions: [],
  vo: "",
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
    </>
  );
};
