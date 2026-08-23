import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { Fonts, SANS, SERIF, rgba, themeTokens, type CookTheme } from "./kit";
import { enter, settle, clamp01 } from "./motion";

/* =============================================================================
   FlowTree — a node-tree / flowchart step card. Root at the top (or left),
   children branch below (or right), 1-3 levels, <=7 nodes. Each connector DRAWS
   itself (stroke-dashoffset) and THEN its child node pops in; the active path
   (active node + its ancestors) lights in accent, everything else stays
   ink/mute with dashed connectors.
   Clones: zB5mUHSYjXA "node tree diagram" (dark pills, dashed connectors),
   dLS-6jn9xxc "flowchart/tree diagram" (right-angle lines), ovLAIhbk3ek
   "flowchart step card" (title + steps), VE2Uxb9Fz7I "branching decision path".
   Distinct from OrbitNodes (radial) and Fogline (linear road).
   HONESTY: a diagram of a plan/structure. Never dress it as a live product UI
   or imply an agent actually executed the branch shown.
   ========================================================================== */

export type FlowNode = {
  id: string;
  label: string;
  /** id of the parent; omit for the root (first parentless node is the root). */
  parent?: string;
  /** optional emoji drawn before the label. */
  icon?: string;
  state?: "done" | "active" | "todo";
};

export type FlowTreeProps = {
  nodes: FlowNode[];
  direction?: "down" | "right";
  title?: string;
  theme?: CookTheme;
  accent?: string;
  bg?: string;
  transparent?: boolean;
  /** seconds offset — the reveal starts at film second `start`. */
  start?: number;
};

type Laid = FlowNode & { x: number; y: number; w: number; h: number; depth: number; order: number };

/* tidy layout: every subtree gets width = sum of its leaves; nodes centre over
   their subtree; levels stack along the main axis. Pure function of the list. */
const layout = (nodes: FlowNode[], dir: "down" | "right"): Laid[] => {
  const list = nodes.slice(0, 7);
  const ids = new Set(list.map((n) => n.id));
  const root = list.find((n) => !n.parent || !ids.has(n.parent)) ?? list[0];
  const kids = (id: string) => list.filter((n) => n.parent === id && n.id !== root.id);
  const leaves = (n: FlowNode): number => {
    const k = kids(n.id);
    return k.length === 0 ? 1 : k.reduce((s, c) => s + leaves(c), 0);
  };
  const depthOf = (n: FlowNode, d = 0): number => {
    const k = kids(n.id);
    return k.length === 0 ? d : Math.max(...k.map((c) => depthOf(c, d + 1)));
  };
  const levels = depthOf(root) + 1;
  const L = leaves(root);
  // cross axis = the axis siblings spread along; main axis = the depth axis
  const crossSpan = dir === "down" ? 920 : 1120; // x∈[80,1000] | y∈[300,1420]
  const cross0 = dir === "down" ? 80 : 300;
  const slot = crossSpan / L;
  const gap = 18;
  const nodeCross = Math.min(dir === "down" ? 300 : 150, slot - gap);
  const nodeMain = dir === "down" ? 120 : 300;
  const mainSpan = dir === "down" ? 1060 : 920; // y∈[330,1390] | x∈[80,1000]
  const main0 = dir === "down" ? 330 : 80;
  const step = levels > 1 ? (mainSpan - nodeMain) / (levels - 1) : 0;

  const out: Laid[] = [];
  let order = 0;
  const place = (n: FlowNode, depth: number, leafStart: number) => {
    const ln = leaves(n);
    const c = cross0 + (leafStart + ln / 2) * slot; // subtree centre on cross axis
    const m = main0 + depth * step;
    const w = dir === "down" ? nodeCross : nodeMain;
    const h = dir === "down" ? nodeMain : nodeCross;
    out.push({ ...n, depth, order: order++,
      x: dir === "down" ? c - w / 2 : m,
      y: dir === "down" ? m : c - h / 2, w, h });
    let acc = leafStart;
    for (const k of kids(n.id)) { place(k, depth + 1, acc); acc += leaves(k); }
  };
  place(root, 0, 0);
  return out;
};

const elbow = (p: Laid, c: Laid, dir: "down" | "right"): string => {
  if (dir === "down") {
    const x1 = p.x + p.w / 2, y1 = p.y + p.h, x2 = c.x + c.w / 2, y2 = c.y;
    const ym = (y1 + y2) / 2;
    return `M${x1},${y1} L${x1},${ym} L${x2},${ym} L${x2},${y2}`;
  }
  const x1 = p.x + p.w, y1 = p.y + p.h / 2, x2 = c.x, y2 = c.y + c.h / 2;
  const xm = (x1 + x2) / 2;
  return `M${x1},${y1} L${xm},${y1} L${xm},${y2} L${x2},${y2}`;
};
const pathLen = (p: Laid, c: Laid, dir: "down" | "right"): number =>
  dir === "down"
    ? Math.abs(c.y - (p.y + p.h)) + Math.abs(c.x + c.w / 2 - (p.x + p.w / 2))
    : Math.abs(c.x - (p.x + p.w)) + Math.abs(c.y + c.h / 2 - (p.y + p.h / 2));

export const FlowTree: React.FC<FlowTreeProps> = ({
  nodes = [],
  direction = "down",
  title,
  theme = "cream",
  accent,
  bg,
  transparent = false,
  start = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - start;
  const T = themeTokens(theme, accent, bg);
  const cream = theme === "cream";
  const dir = direction;

  const laid = layout(nodes, dir);
  const byId = new Map(laid.map((n) => [n.id, n]));
  // active path = every active node + its ancestors
  const lit = new Set<string>();
  for (const n of laid) if (n.state === "active") {
    let cur: Laid | undefined = n;
    while (cur) { lit.add(cur.id); cur = cur.parent ? byId.get(cur.parent) : undefined; }
  }

  // timing: title 0, root 0.35, then each node (BFS/pre-order) at a fixed pace —
  // connector draws over 0.3s, the node pops right after.
  const PACE = 0.42;
  const nodeAt = (n: Laid) => 0.35 + n.order * PACE;
  const DRAW = 0.3;

  const titleP = enter(t, 0.05, 0.5);
  const pillFill = cream ? "#1F3A34" : T.card; // comp-dna dark-green pill on cream
  const pillInk = cream ? "#F4F2EC" : T.ink;

  return (
    <div style={{ position: "absolute", inset: 0, width: 1080, height: 1920,
      background: transparent ? "transparent" : T.bg, fontFamily: SANS, overflow: "hidden" }}>
      <Fonts />
      {title ? (
        <div style={{ position: "absolute", left: 80, right: 80, top: 176,
          opacity: titleP, transform: `translateY(${(1 - titleP) * 18}px)`,
          color: T.ink, fontFamily: SERIF, fontStyle: "italic", fontSize: 60,
          lineHeight: "68px", letterSpacing: -0.5, textAlign: "center" }}>
          {title}
        </div>
      ) : null}

      {/* connectors — drawn first, under the pills */}
      <svg width={1080} height={1920} viewBox="0 0 1080 1920"
        style={{ position: "absolute", inset: 0, overflow: "visible" }}>
        {laid.filter((n) => n.parent && byId.has(n.parent)).map((c) => {
          const p = byId.get(c.parent!)!;
          const len = pathLen(p, c, dir) + 4;
          const prog = clamp01((t - (nodeAt(c) - DRAW)) / DRAW);
          const on = lit.has(c.id) && lit.has(p.id);
          const done = c.state === "done";
          return (
            <path key={c.id} d={elbow(p, c, dir)} fill="none"
              stroke={on ? T.accent : done ? T.ink : T.mute}
              strokeWidth={on ? 6 : 4} strokeLinecap="round" strokeLinejoin="round"
              strokeDasharray={on || done ? `${len}` : `12 12`}
              strokeDashoffset={on || done ? len * (1 - prog) : 0}
              /* dashed (todo) lines can't wipe via dashoffset — they ramp in */
              opacity={(on || done ? 1 : 0.75) * prog}
            />
          );
        })}
      </svg>

      {/* nodes */}
      {laid.map((n) => {
        const at = nodeAt(n);
        const p = enter(t, at, 0.4, 0.08);
        const s = 1 + settle(t, at + 0.4, 0.45) * 0.03;
        const on = lit.has(n.id);
        const active = n.state === "active";
        const done = n.state === "done";
        const todo = n.state === "todo";
        const fill = active ? T.accent : todo ? "transparent" : pillFill;
        const ink = active ? "#FFFFFF" : todo ? T.mute : pillInk;
        const border = active ? T.accent : on ? T.accent : todo ? T.mute : pillFill;
        const fs = Math.min(34, Math.max(22, (n.w - 56) / Math.max(6, n.label.length) * 1.9));
        return (
          <div key={n.id} style={{ position: "absolute", left: n.x, top: n.y, width: n.w, height: n.h,
            opacity: Math.min(1, p * 1.4),
            transform: `scale(${(0.7 + 0.3 * p) * s})`, transformOrigin: "50% 50%",
            borderRadius: 22, background: fill, color: ink,
            border: `3px ${todo ? "dashed" : "solid"} ${border}`,
            boxShadow: active ? `0 18px 40px -16px ${rgba(T.accent, 0.7)}`
              : todo ? "none" : `0 14px 30px -18px ${rgba("#000", 0.55)}`,
            display: "flex", alignItems: "center", justifyContent: "center", gap: 10,
            padding: "0 16px", boxSizing: "border-box",
            fontSize: n.label.length > 7 ? fs * 0.82 : fs, fontWeight: 700, letterSpacing: -0.2, lineHeight: 1.1,
            textAlign: "center", whiteSpace: "normal" }}>
            {n.icon ? <span style={{ fontSize: fs * 1.15 }}>{n.icon}</span> : null}
            <span style={{ overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as const }}>{n.label}</span>
            {done ? (
              <span style={{ position: "absolute", right: -12, top: -12, width: 34, height: 34,
                borderRadius: 17, background: on ? T.accent : cream ? "#3E8C74" : T.accent,
                color: "#fff", fontSize: 20, fontWeight: 900, display: "flex",
                alignItems: "center", justifyContent: "center",
                border: `3px solid ${transparent ? "transparent" : T.bg}` }}>✓</span>
            ) : null}
            {active ? (
              <span style={{ position: "absolute", inset: -3, borderRadius: 22,
                border: `3px solid ${T.accent}`,
                /* one ring on arrival, then holds invisible — no loop */
                opacity: 0.55 * (1 - clamp01((t - at - 0.3) / 0.9)),
                transform: `scale(${1 + 0.12 * clamp01((t - at - 0.3) / 0.9)})` }} />
            ) : null}
          </div>
        );
      })}
    </div>
  );
};

export const flowTreeDemo: FlowTreeProps = {
  title: "One prompt, three agents",
  direction: "down",
  nodes: [
    { id: "root", label: "Planner", icon: "🧠", state: "done" },
    { id: "a", label: "Research", parent: "root", icon: "🔍", state: "done" },
    { id: "b", label: "Write", parent: "root", icon: "✍️", state: "active" },
    { id: "c", label: "Review", parent: "root", icon: "✅", state: "todo" },
    { id: "b1", label: "Draft", parent: "b", state: "active" },
    { id: "b2", label: "Polish", parent: "b", state: "todo" },
  ],
  theme: "cream",
};
