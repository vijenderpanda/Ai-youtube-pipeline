import React from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  spring,
} from "remotion";

/* CodeDemo — a faithful VS Code recreation for the pipCallout top-zone b-roll
   (Ep 11 "6 Claude commands"). Editor pane (top) shows the real .claude/commands
   /<key>.md file; terminal pane (bottom) shows the command being invoked and the
   REAL captured Claude response streaming in. Custom slash commands run in the
   terminal/IDE, not claude.ai web (verified), so this recreation IS the honest
   surface — real command definition + real model output, rendered clean.

   Rendered at 1080x1200 to map 1:1 into the pipCallout's 62%-tall top zone. */

const BG = "#1e1e1e";        // VS Code editor bg
const TERM_BG = "#181818";   // integrated terminal bg
const TITLE_BG = "#323233";  // title/tab bar
const GUTTER = "#858585";    // line numbers
const FG = "#d4d4d4";        // default text
// markdown/yaml token colors (VS Code Dark+)
const C_KEY = "#9cdcfe";     // frontmatter keys
const C_STR = "#ce9178";     // strings / values
const C_HR = "#569cd6";      // --- rule / headings
const C_VAR = "#4ec9b0";     // $ARGUMENTS
const C_COMMENT = "#6a9955";
const PROMPT_G = "#22D3EE";  // terminal accent = channel cyan
const CURSOR = "#e8e8e8";

export type CodeDemoProps = {
  commandKey: string;        // e.g. "premortem"
  fileLines: string[];       // the .md file content, line by line
  termArg: string;           // the argument typed after /command
  responseLines: string[];   // the REAL captured response, line by line
  typeStart?: number;        // s — when the command finishes typing (default 1.0)
  lineStagger?: number;      // s — gap between response lines appearing (default 0.5)
};

// naive markdown/yaml highlighter for the editor pane
const hl = (line: string, inFrontmatter: boolean): React.ReactNode => {
  if (line === "---") return <span style={{ color: C_HR }}>{line}</span>;
  if (inFrontmatter) {
    const m = line.match(/^(\s*[\w-]+):(.*)$/);
    if (m) {
      return (
        <>
          <span style={{ color: C_KEY }}>{m[1]}</span>
          <span style={{ color: FG }}>:</span>
          <span style={{ color: C_STR }}>{m[2]}</span>
        </>
      );
    }
  }
  // body: highlight $ARGUMENTS / $N tokens + numbered list markers
  const parts = line.split(/(\$ARGUMENTS|\$\d+|\$[A-Za-z_]+)/g);
  return parts.map((p, i) =>
    /^\$/.test(p) ? (
      <span key={i} style={{ color: C_VAR }}>{p}</span>
    ) : (
      <span key={i} style={{ color: /^\s*\d+\./.test(line) ? FG : FG }}>{p}</span>
    )
  );
};

export const CodeDemo: React.FC<CodeDemoProps> = ({
  commandKey,
  fileLines,
  termArg,
  responseLines,
  typeStart = 1.0,
  lineStagger = 0.5,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  // command typing animation
  const fullCmd = `/${commandKey} ${termArg}`;
  const typeChars = Math.max(
    0,
    Math.min(fullCmd.length, Math.floor((t / typeStart) * fullCmd.length))
  );
  const typed = fullCmd.slice(0, typeChars);
  const doneTyping = t >= typeStart;
  const cursorOn = Math.floor(t * 2) % 2 === 0;

  // response reveal: line by line after typing completes
  const respStart = typeStart + 0.35;
  let inFront = false;
  let frontCount = 0;

  return (
    <AbsoluteFill style={{ background: BG, fontFamily: "'SF Mono', 'JetBrains Mono', Menlo, monospace" }}>
      {/* title bar */}
      <div style={{ height: 64, background: TITLE_BG, display: "flex", alignItems: "center", paddingLeft: 26, gap: 12 }}>
        <span style={{ width: 17, height: 17, borderRadius: "50%", background: "#ff5f56" }} />
        <span style={{ width: 17, height: 17, borderRadius: "50%", background: "#ffbd2e" }} />
        <span style={{ width: 17, height: 17, borderRadius: "50%", background: "#27c93f" }} />
        <span style={{ marginLeft: 24, color: "#cfcfcf", fontSize: 29, opacity: 0.9 }}>
          {commandKey}.md — claude-tricks
        </span>
      </div>

      {/* editor pane */}
      <div style={{ height: 690, overflow: "hidden", padding: "16px 0", position: "relative" }}>
        {/* file tab */}
        <div style={{ position: "absolute", top: -16, left: 0, height: 50, background: BG, display: "flex", alignItems: "center", paddingLeft: 26, borderBottom: `2px solid ${PROMPT_G}` }}>
          <span style={{ color: C_HR, fontSize: 27 }}>◆ </span>
          <span style={{ color: FG, fontSize: 27, marginLeft: 8 }}>{commandKey}.md</span>
        </div>
        <div style={{ marginTop: 50 }}>
          {fileLines.map((ln, i) => {
            if (ln === "---") { inFront = !inFront; frontCount++; }
            const showFront = frontCount >= 1 && (inFront || (frontCount >= 2 && i <= fileLines.indexOf("---", fileLines.indexOf("---") + 1)));
            return (
              <div key={i} style={{ display: "flex", fontSize: 32, lineHeight: "50px" }}>
                <span style={{ width: 78, textAlign: "right", paddingRight: 24, color: GUTTER, flexShrink: 0 }}>{i + 1}</span>
                <span style={{ whiteSpace: "pre-wrap", color: FG }}>{hl(ln, inFront && ln !== "---")}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* terminal pane (bottom) */}
      <div style={{ flex: 1, background: TERM_BG, borderTop: "1px solid #333", padding: "22px 26px" }}>
        <div style={{ color: "#888", fontSize: 26, marginBottom: 14, letterSpacing: 1 }}>TERMINAL</div>
        {/* command line */}
        <div style={{ fontSize: 35, lineHeight: "52px" }}>
          <span style={{ color: PROMPT_G }}>❯ </span>
          <span style={{ color: "#fff" }}>{typed}</span>
          {!doneTyping && cursorOn ? (
            <span style={{ background: CURSOR, color: TERM_BG }}>▏</span>
          ) : null}
        </div>
        {/* response */}
        <div style={{ marginTop: 18 }}>
          {responseLines.map((ln, i) => {
            const appearAt = respStart + i * lineStagger;
            const s = spring({ frame: frame - appearAt * fps, fps, config: { damping: 20, mass: 0.5 } });
            if (t < appearAt) return null;
            return (
              <div
                key={i}
                style={{
                  fontSize: 34,
                  lineHeight: "52px",
                  color: FG,
                  opacity: interpolate(s, [0, 1], [0, 1]),
                  transform: `translateY(${interpolate(s, [0, 1], [6, 0])}px)`,
                  whiteSpace: "pre-wrap",
                }}
              >
                {ln}
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
