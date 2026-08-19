/* =============================================================================
   COOKBOOK REGISTRY — the machine-readable catalog that lets a content planner
   pick the best-suited visual component for a beat.

   Every cookbook component draws a specific SHAPE of information well (a trend,
   a single big number, a before/after, a set of options, a spoken line…). When
   the plan for a beat is known — what it's trying to say and what data it has —
   `pickCookbook()` scores the catalog and returns the strongest matches. This
   is the selection layer the designer/build_ep_v2 will call to auto-assign a
   graphical b-roll component to a beat (docs/REMOTION-DESIGNER-VISION.md).

   Keep ONE entry per registered component; `demoId` is its Root.tsx <Composition
   id>. Adding a component = add its file (see COOKBOOK.md) + an entry here.
   ========================================================================== */

/** Visual family — the kind of surface the component draws. */
export type CookbookRole =
  | "app-ui" // a believable invented application screen
  | "device-ui" // an iOS/phone surface (lock screen, island, orb…)
  | "dataviz" // a chart/graph that teaches a number
  | "interaction" // a UI gesture/micro-interaction flex
  | "layout" // an arrangement of several facts at once
  | "typography" // kinetic/large type as the hero
  | "transformation"; // an input visibly becoming an output

/** Where in a short the component tends to earn its place. */
export type BeatKind =
  | "hook" // 0-3s attention grab
  | "context" // set up the idea
  | "stat" // land a number / proof point
  | "process" // show a sequence of steps happening
  | "comparison" // A vs B / before vs after / pick best
  | "demo" // show a capability being used
  | "punchline" // the payoff line
  | "cta" // call to action
  | "social-proof"; // results / traction / counts

/** The SHAPE of content the component needs — the planner must be able to
    supply data in this shape for the component to fit. */
export type DataShape =
  | "series" // ordered numbers (+optional labels) — a trend over time
  | "metrics" // a few labeled percentages / progress values
  | "single-number" // one big value (+ optional label / delta)
  | "facts" // 3-6 short labeled facts
  | "before-after" // paired old -> new lines / states
  | "steps" // an ordered list of phases / actions
  | "options" // a set of choices, one is the winner
  | "dialogue" // a chat / turn-by-turn exchange
  | "phrase" // a sentence with words to emphasize
  | "query-results" // a search query + result rows
  | "hub-spokes" // one center + N related items
  | "alerts" // a set of short notifications
  | "utterance"; // a spoken line -> live transcript

export type CookbookEntry = {
  id: string; // component export name (also the file basename)
  demoId: string; // Root.tsx composition id for preview / still QC
  title: string;
  role: CookbookRole;
  beats: BeatKind[]; // beats this component serves well
  needs: DataShape; // the data shape the planner must supply
  keywords: string[]; // content-fit tags used for fuzzy matching
  transparentCapable: boolean; // supports `transparent` -> can overlay a host/b-roll
  wow: 1 | 2 | 3 | 4 | 5; // taste-flex impact (5 = showstopper)
  density: "low" | "med" | "high"; // how much info it carries at once
  useWhen: string; // one-line selection guidance
};

export const COOKBOOK: CookbookEntry[] = [
  {
    id: "ChatApp", demoId: "ChatAppDemo", title: "AI chat app",
    role: "app-ui", beats: ["demo", "context"], needs: "dialogue",
    keywords: ["ai chat", "assistant", "prompt", "conversation", "messaging", "app", "reply"],
    transparentCapable: true, wow: 4, density: "med",
    useWhen: "Show using an AI assistant conversationally without recording a real app.",
  },
  {
    id: "LineReveal", demoId: "LineRevealDemo", title: "Line/area trend reveal",
    role: "dataviz", beats: ["stat", "context", "social-proof"], needs: "series",
    keywords: ["growth", "trend", "over time", "curve", "views", "revenue", "compounding", "decline"],
    transparentCapable: true, wow: 4, density: "med",
    useWhen: "A number that moved over time — the line draws while the value counts up.",
  },
  {
    id: "CommandPalette", demoId: "CommandPaletteDemo", title: "Command palette (⌘K)",
    role: "interaction", beats: ["demo", "hook"], needs: "query-results",
    keywords: ["command", "search", "shortcut", "cmdk", "actions", "quick pick", "power user"],
    transparentCapable: true, wow: 5, density: "med",
    useWhen: "Show invoking a command / searching and picking an action.",
  },
  {
    id: "BentoGrid", demoId: "BentoGridDemo", title: "Bento fact grid",
    role: "layout", beats: ["stat", "context", "social-proof"], needs: "facts",
    keywords: ["dashboard", "metrics", "summary", "at a glance", "results", "multiple facts", "recap"],
    transparentCapable: true, wow: 3, density: "high",
    useWhen: "Show 3-6 facts / metrics at once, each landing on its own micro-beat.",
  },
  {
    id: "DiffReveal", demoId: "DiffRevealDemo", title: "Before → after rewrite",
    role: "transformation", beats: ["demo", "comparison", "punchline"], needs: "before-after",
    keywords: ["rewrite", "before after", "edit", "improve", "prompt", "refactor", "fix", "clean up"],
    transparentCapable: true, wow: 4, density: "med",
    useWhen: "Show a messy input being rewritten into a clean output.",
  },
  {
    id: "RingGauge", demoId: "RingGaugeDemo", title: "Concentric ring gauge",
    role: "dataviz", beats: ["stat"], needs: "metrics",
    keywords: ["percent", "progress", "completion", "share", "rings", "breakdown", "time saved", "utilization"],
    transparentCapable: true, wow: 4, density: "med",
    useWhen: "Show a few percentages / progress values as radial rings + a headline figure.",
  },
  {
    id: "Odometer", demoId: "OdometerDemo", title: "Rolling number",
    role: "interaction", beats: ["stat", "hook", "social-proof"], needs: "single-number",
    keywords: ["count", "subscribers", "revenue", "milestone", "big number", "total", "downloads"],
    transparentCapable: true, wow: 4, density: "low",
    useWhen: "Reveal a single big number with a satisfying slot-machine roll (milestones, totals).",
  },
  {
    id: "OrbitNodes", demoId: "OrbitNodesDemo", title: "Hub + orbit constellation",
    role: "interaction", beats: ["context", "demo"], needs: "hub-spokes",
    keywords: ["ecosystem", "one to many", "capabilities", "features", "use cases", "map", "connections", "versatile"],
    transparentCapable: true, wow: 4, density: "med",
    useWhen: "Show one thing branching into many related capabilities / use-cases.",
  },
  {
    id: "KineticQuote", demoId: "KineticQuoteDemo", title: "Kinetic punchline",
    role: "typography", beats: ["hook", "punchline", "cta"], needs: "phrase",
    keywords: ["quote", "statement", "hook", "punchline", "big text", "mantra", "truth", "one-liner"],
    transparentCapable: true, wow: 4, density: "low",
    useWhen: "Land a punchy statement / hook with emphasis on the words that matter.",
  },
  {
    id: "NotificationStack", demoId: "NotificationStackDemo", title: "Phone alert pile",
    role: "device-ui", beats: ["demo", "social-proof", "context"], needs: "alerts",
    keywords: ["notifications", "alerts", "phone", "lock screen", "results", "pile up", "updates", "outputs"],
    transparentCapable: true, wow: 5, density: "med",
    useWhen: "Show a pile of results / alerts stacking up on a phone lock screen.",
  },
  {
    id: "DynamicIsland", demoId: "DynamicIslandDemo", title: "Live-activity island",
    role: "device-ui", beats: ["process", "demo"], needs: "steps",
    keywords: ["live activity", "progress", "background task", "running", "dynamic island", "generating", "status", "working"],
    transparentCapable: true, wow: 5, density: "low",
    useWhen: "Show an AI task running through phases to completion as a live-activity pill.",
  },
  {
    id: "VoiceOrb", demoId: "VoiceOrbDemo", title: "Voice assistant orb",
    role: "device-ui", beats: ["demo", "hook"], needs: "utterance",
    keywords: ["voice", "speak", "assistant", "transcribe", "listening", "siri", "hands-free", "dictation"],
    transparentCapable: true, wow: 5, density: "low",
    useWhen: "Show speaking to an AI and the words transcribing live.",
  },
  {
    id: "SwipeDeck", demoId: "SwipeDeckDemo", title: "Decision swipe deck",
    role: "interaction", beats: ["comparison", "demo", "process"], needs: "options",
    keywords: ["choose", "pick best", "options", "compare", "filter", "decision", "shortlist", "swipe", "evaluate"],
    transparentCapable: true, wow: 4, density: "med",
    useWhen: "Show AI sifting a set of options and picking the best one.",
  },
];

/* ------------------------------------------------------------------------- */

/** A beat's intent, as much of it as the planner knows. Any field may be
    omitted; more fields => sharper ranking. */
export type BeatIntent = {
  beat?: BeatKind; // where this sits in the short
  needs?: DataShape; // the shape of data the beat has to show
  keywords?: string[]; // free words from the script / plan
  role?: CookbookRole; // force a family, if the plan already decided
  minWow?: number; // floor the taste-flex impact
  transparent?: boolean; // require overlay-capable (over a host/b-roll)
};

export type Scored = { entry: CookbookEntry; score: number; why: string[] };

const norm = (s: string): string => s.toLowerCase().trim();

/** Score every catalog entry against a beat intent and return the best `n`,
    highest score first. Scoring (additive, transparent + role/wow are gates):
      +5 data-shape (`needs`) exact match — the strongest signal
      +3 beat is in the component's beats
      +1 per overlapping keyword (either direction, substring-aware)
      +wow/10 tie-breaker so the flashier option wins an otherwise even race
    A `role` in the intent hard-filters to that family; `minWow` and
    `transparent` hard-filter too. Entries scoring 0 are dropped. */
export function pickCookbook(intent: BeatIntent, n = 3): Scored[] {
  const kw = (intent.keywords ?? []).map(norm).filter(Boolean);
  const ranked: Scored[] = [];

  for (const entry of COOKBOOK) {
    if (intent.role && entry.role !== intent.role) continue;
    if (intent.transparent && !entry.transparentCapable) continue;
    if (typeof intent.minWow === "number" && entry.wow < intent.minWow) continue;

    let score = 0;
    const why: string[] = [];

    if (intent.needs && entry.needs === intent.needs) {
      score += 5;
      why.push(`needs:${entry.needs}`);
    }
    if (intent.beat && entry.beats.includes(intent.beat)) {
      score += 3;
      why.push(`beat:${intent.beat}`);
    }
    if (kw.length) {
      const hay = [...entry.keywords.map(norm), norm(entry.title), norm(entry.useWhen)];
      let hits = 0;
      for (const k of kw) {
        if (hay.some((h) => h.includes(k) || k.includes(h))) {
          hits += 1;
          why.push(`kw:${k}`);
        }
      }
      score += hits;
    }

    if (score <= 0) continue;
    score += entry.wow / 10; // tie-breaker toward higher wow
    ranked.push({ entry, score: Math.round(score * 100) / 100, why });
  }

  ranked.sort((a, b) => b.score - a.score);
  return ranked.slice(0, n);
}

/** Convenience lookups. */
export const byId = (id: string): CookbookEntry | undefined =>
  COOKBOOK.find((e) => e.id === id);
export const byRole = (role: CookbookRole): CookbookEntry[] =>
  COOKBOOK.filter((e) => e.role === role);
export const byNeeds = (needs: DataShape): CookbookEntry[] =>
  COOKBOOK.filter((e) => e.needs === needs);
