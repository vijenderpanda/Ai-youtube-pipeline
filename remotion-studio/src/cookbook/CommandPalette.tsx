import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BRAND, SANS, MONO, rgba, clamp, coverBg, Fonts } from "./kit";

/* =============================================================================
   CommandPalette — an invented "⌘K" palette that types a query, cascades
   results, then highlights + "launches" the chosen one.
   Cookbook role: the "invented wow / interaction" flex — the visual itself is a
   flex of UI taste ("wait, you can show a search like THIS?") while still
   teaching a concrete action. Reads as a glassy overlay floating on an app.
   The four phases are time-sliced: type → results in → select → press.
   ========================================================================== */

export type PaletteResult = {
  title: string;
  hint?: string; // right-aligned muted hint (e.g. shortcut, category)
  icon?: string; // single glyph/emoji in the leading tile
};

export type CommandPaletteProps = {
  query: string; // the text typed into the search field
  results: PaletteResult[]; // rows that cascade in
  selectedIndex?: number; // which row highlights + "launches" (default 0)
  placeholder?: string; // shown before typing starts
  caption?: string; // small label above the palette (e.g. "Press ⌘K")
  accent?: string; // caret, highlight, selected tile (brand magenta)
  ink?: string;
  cps?: number; // characters/sec typing speed (default 22)
  start?: number; // seconds before typing begins
  width?: number;
  height?: number;
  transparent?: boolean;
};

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  query,
  results,
  selectedIndex = 0,
  placeholder = "Type a command or search…",
  caption,
  accent = BRAND.mag,
  ink = BRAND.ink,
  cps = 22,
  start = 0.3,
  width = 1080,
  height = 1920,
  transparent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const t = (frame - start * fps) / fps; // seconds since palette opened
  // phase 1 — type the query
  const typedChars = clamp(t * cps, 0, query.length);
  const typed = query.slice(0, Math.floor(typedChars));
  const typingDone = typedChars >= query.length;
  const typeEndT = query.length / cps;

  // phase 2 — results cascade in after typing
  const resultsStartT = typeEndT + 0.18;
  // phase 3 — selection lands after results are in
  const selectT = resultsStartT + results.length * 0.09 + 0.35;
  // phase 4 — a quick "press" on the selected row
  const pressT = selectT + 0.5;
  const press = interpolate(t, [pressT, pressT + 0.12, pressT + 0.34], [1, 0.97, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const caret = Math.floor(t * 2) % 2 === 0 && !typingDone ? 1 : typingDone ? (Math.floor(t * 1.6) % 2 === 0 ? 0.5 : 0) : 0;

  const PW = Math.min(width - 140, 900);
  const px = (width - PW) / 2;
  const py = Math.round(height * 0.26);
  const ROW = 132;

  // palette entrance
  const open = spring({ frame: frame - start * fps, fps, config: { damping: 18, mass: 0.6 } });

  return (
    <AbsoluteFill
      style={{
        background: transparent ? undefined : coverBg(accent, ink),
        fontFamily: SANS,
      }}
    >
      <Fonts />
      {/* dim scrim to read as an overlay */}
      <AbsoluteFill style={{ background: rgba("#05050a", 0.5 * open) }} />

      {caption ? (
        <div style={{ position: "absolute", top: py - 96, width: "100%", textAlign: "center", fontSize: 40, letterSpacing: 3, textTransform: "uppercase", color: BRAND.mute, opacity: open }}>
          {caption}
        </div>
      ) : null}

      <div
        style={{
          position: "absolute",
          left: px,
          top: py,
          width: PW,
          transform: `translateY(${interpolate(open, [0, 1], [40, 0])}px) scale(${interpolate(open, [0, 1], [0.96, 1]) * press})`,
          opacity: open,
          borderRadius: 40,
          background: rgba("#14141c", 0.86),
          border: `1.5px solid ${rgba("#ffffff", 0.1)}`,
          boxShadow: `0 50px 140px ${rgba("#000000", 0.65)}, 0 0 0 1px ${rgba(accent, 0.12)}`,
          backdropFilter: "blur(24px)",
          overflow: "hidden",
        }}
      >
        {/* search row */}
        <div style={{ display: "flex", alignItems: "center", gap: 26, padding: "44px 46px", borderBottom: `1px solid ${rgba("#ffffff", 0.08)}` }}>
          <span style={{ fontSize: 52, color: accent }}>{"⌘"}</span>
          <div style={{ flex: 1, fontSize: 46, color: typed ? BRAND.paper : BRAND.mute, display: "flex", alignItems: "center", fontWeight: 500 }}>
            {typed || placeholder}
            <span style={{ display: "inline-block", width: 4, height: 52, marginLeft: 4, background: accent, opacity: caret }} />
          </div>
          <span style={{ fontFamily: MONO, fontSize: 28, color: BRAND.mute, border: `1px solid ${rgba("#ffffff", 0.16)}`, borderRadius: 10, padding: "6px 14px" }}>esc</span>
        </div>

        {/* results */}
        <div style={{ padding: "18px 18px 26px" }}>
          {results.map((r, i) => {
            const rs = spring({ frame: frame - (start + resultsStartT + i * 0.09) * fps, fps, config: { damping: 18, mass: 0.5 } });
            const isSel = i === selectedIndex && t >= selectT;
            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 26,
                  height: ROW,
                  padding: "0 28px",
                  borderRadius: 26,
                  background: isSel ? `linear-gradient(100deg, ${rgba(accent, 0.9)}, ${rgba(accent, 0.66)})` : "transparent",
                  boxShadow: isSel ? `0 16px 40px ${rgba(accent, 0.36)}` : "none",
                  opacity: clamp(rs * 1.4),
                  transform: `translateX(${interpolate(rs, [0, 1], [26, 0])}px)`,
                }}
              >
                <div
                  style={{
                    width: 74,
                    height: 74,
                    borderRadius: 20,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 38,
                    color: isSel ? ink : BRAND.paper,
                    background: isSel ? rgba("#ffffff", 0.9) : rgba("#ffffff", 0.06),
                    border: `1px solid ${rgba("#ffffff", isSel ? 0 : 0.08)}`,
                  }}
                >
                  {r.icon ?? "›"}
                </div>
                <div style={{ flex: 1, fontSize: 42, fontWeight: 600, color: isSel ? ink : BRAND.paper }}>{r.title}</div>
                {isSel ? (
                  <span style={{ fontFamily: MONO, fontSize: 30, color: ink, background: rgba("#ffffff", 0.85), borderRadius: 12, padding: "8px 18px", fontWeight: 700 }}>↵</span>
                ) : r.hint ? (
                  <span style={{ fontSize: 32, color: BRAND.mute }}>{r.hint}</span>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const commandPaletteDemo: CommandPaletteProps = {
  caption: "Press ⌘K",
  query: "summarize this thread",
  results: [
    { icon: "✦", title: "Summarize thread", hint: "AI" },
    { icon: "⇄", title: "Translate to plain English", hint: "AI" },
    { icon: "◆", title: "Extract action items", hint: "AI" },
    { icon: "↗", title: "Share as a doc", hint: "⌘S" },
  ],
  selectedIndex: 0,
};
