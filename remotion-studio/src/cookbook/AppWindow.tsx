import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { Fonts, MONO, SANS, SERIF, rgba, themeTokens, type CookTheme } from "./kit";
import { enter, idle, settle, typeOn } from "./motion";

/* =============================================================================
   AppWindow — a generic desktop app-window frame for INVENTED content.
   Title bar (traffic lights + title), optional address bar, optional sidebar
   list, body = typed lines / code / staggered table rows, optional caret.
   Clones comp-dna: zB5mUHSYjXA "fake app window" + "code editor screenshot",
   VE2Uxb9Fz7I "mini app-window mockup", yJK5GueSHmU "vault/note-list mockup"
   + "terminal command card". Distinct from ScreenStage/WebTour (real footage)
   and TermRun (terminal only). Window drops in with mass, content types/lands,
   then HOLDS (idle drift only).
   HONESTY: this frames MOCK content — never present it as a real product
   screenshot or a real app's real output.
   ========================================================================== */

export type AppWindowBody = {
  kind: "lines" | "code" | "table";
  /** for "lines" / "code": each string types on in order. */
  lines?: string[];
  /** for "table": rows land staggered; first row is the header. */
  rows?: string[][];
  /** cosmetic tag shown in the tab strip for code ("py", "ts", "md"). */
  lang?: string;
};

export type AppWindowProps = {
  theme?: CookTheme;
  accent?: string;
  bg?: string;
  transparent?: boolean;
  /** seconds offset — animation clock is t = frame/fps - start. */
  start?: number;
  /** window title in the title bar. */
  title?: string;
  /** optional address bar text (renders a URL pill under the title bar). */
  url?: string;
  /** optional left sidebar items; `activeIndex` highlights one. */
  sidebar?: string[];
  activeIndex?: number;
  body: AppWindowBody;
  /** blinking caret after the last typed line (lines/code only). */
  cursor?: boolean;
  /** big soft drop under the window. */
  shadow?: boolean;
  /** slight 3D tilt for the "screenshot-of-software" feel. */
  tilt?: boolean;
  /** dark chrome (editor/terminal look) vs light chrome (note app). */
  dark?: boolean;
  /** chars per second for typed lines. */
  cps?: number;
  /** y of the window's top edge in the 1080×1920 box. */
  top?: number;
};

const LIGHTS = ["#FF5F57", "#FEBC2E", "#28C840"];

/* naive, deterministic code tinting — keywords / strings / numbers only */
const KW = /^(import|from|def|return|const|let|function|export|async|await|if|else|for|in|class|new|type)$/;
const tintToken = (tok: string, accent: string, ink: string, mute: string): string => {
  if (KW.test(tok)) return accent;
  if (/^["'`].*["'`]$/.test(tok)) return "#3E8C74";
  if (/^\d+(\.\d+)?$/.test(tok)) return "#C2783A";
  if (/^#|^\/\//.test(tok)) return mute;
  return ink;
};

export const AppWindow: React.FC<AppWindowProps> = ({
  theme = "cream",
  accent,
  bg,
  transparent = false,
  start = 0,
  title = "Untitled",
  url,
  sidebar,
  activeIndex = 0,
  body,
  cursor = true,
  shadow = true,
  tilt = false,
  dark,
  cps = 30,
  top = 420,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = Math.max(0, frame / fps - start);
  const T = themeTokens(theme, accent, bg);
  const isDark = dark ?? body.kind === "code";

  // chrome palette: light note-app vs dark editor/terminal (on either canvas)
  const chrome = isDark
    ? { frame: "#1C1C1A", bar: "#26262A", line: rgba("#fff", 0.08), text: "#ECEAE4", mute: "#8B8A84", side: "#202022" }
    : { frame: T.card, bar: theme === "cream" ? "#ECE9E2" : "#1E1E28", line: T.line, text: T.ink, mute: T.mute, side: theme === "cream" ? "#F0EEE8" : "#1A1A24" };

  // window drop-in: mass + settle, then idle so the hold never freezes
  const e = enter(t, 0.05, 0.5, 0.04);
  const dropY = (1 - e) * -90;
  const sc = 0.94 + 0.06 * e + settle(t, 0.55, 0.5) * 0.012;
  const id = idle(t, 3, 1.6);
  const X = 80, W = 920;
  const sideW = sidebar && sidebar.length ? 230 : 0;
  const bodyH = 620;
  const barH = 64;
  const urlH = url ? 56 : 0;

  // content schedule
  const contentAt = 0.55;
  const lines = body.lines ?? [];
  const rows = body.rows ?? [];
  const bodyFont = body.kind === "code" ? MONO : SANS;
  const lineH = body.kind === "code" ? 40 : 46;
  const fontSize = body.kind === "code" ? 26 : 30;

  // typed lines: sequential; each starts when the previous finished
  const lineStarts: number[] = [];
  let acc = contentAt;
  for (const l of lines) { lineStarts.push(acc); acc += Math.max(0.25, l.length / cps) + 0.18; }
  const typingDone = t >= acc;
  const blink = Math.floor(t * 2.2) % 2 === 0;

  const renderLine = (l: string, i: number) => {
    const n = typeOn(t, lineStarts[i], l.length, cps);
    if (n <= 0) return null;
    const shown = l.slice(0, n);
    const isLast = i === lines.length - 1 || typeOn(t, lineStarts[i + 1] ?? 1e9, 1, cps) === 0;
    const caret = cursor && isLast && (!typingDone || blink) ? (
      <span style={{ display: "inline-block", width: 3, height: fontSize * 1.05, background: T.accent, marginLeft: 3, verticalAlign: "text-bottom" }} />
    ) : null;
    if (body.kind === "code") {
      const indent = l.match(/^\s*/)?.[0].length ?? 0;
      const toks = shown.slice(indent).split(/(\s+)/);
      return (
        <div key={i} style={{ height: lineH, display: "flex", whiteSpace: "pre" }}>
          <span style={{ width: 44, color: chrome.mute, fontSize: fontSize - 6, textAlign: "right", marginRight: 22, lineHeight: `${lineH}px` }}>{i + 1}</span>
          <span style={{ lineHeight: `${lineH}px` }}>
            {" ".repeat(indent)}
            {toks.map((tk, k) => <span key={k} style={{ color: tintToken(tk, T.accent, chrome.text, chrome.mute) }}>{tk}</span>)}
            {caret}
          </span>
        </div>
      );
    }
    return (
      <div key={i} style={{ height: lineH, lineHeight: `${lineH}px`, whiteSpace: "pre-wrap", fontWeight: i === 0 ? 700 : 500, fontSize: i === 0 ? fontSize + 6 : fontSize, color: chrome.text }}>
        {shown}{caret}
      </div>
    );
  };

  const renderTable = () => {
    const cols = rows[0]?.length ?? 1;
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {rows.map((r, i) => {
          const p = enter(t, contentAt + i * 0.14, 0.42, 0.05);
          if (p <= 0) return null;
          const hdr = i === 0;
          return (
            <div key={i} style={{
              display: "grid", gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: 12,
              padding: "10px 14px", borderRadius: 10,
              background: hdr ? "transparent" : rgba(isDark ? "#fff" : "#000", 0.035),
              borderBottom: hdr ? `1px solid ${chrome.line}` : "none",
              opacity: Math.min(1, p), transform: `translateY(${(1 - p) * 18}px)`,
              fontSize: hdr ? 22 : 27, fontWeight: hdr ? 700 : 500, letterSpacing: hdr ? 1 : 0,
              textTransform: hdr ? "uppercase" : "none", color: hdr ? chrome.mute : chrome.text,
            }}>
              {r.map((c, k) => <span key={k} style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: !hdr && k === 0 ? T.accent : undefined, fontFamily: !hdr && k === 0 ? SERIF : SANS, fontStyle: !hdr && k === 0 ? "italic" : "normal" }}>{c}</span>)}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div style={{ position: "absolute", inset: 0, background: transparent ? "transparent" : T.bg, fontFamily: SANS, overflow: "hidden" }}>
      <Fonts />
      <div style={{
        position: "absolute", left: X, top, width: W,
        transform: `translate(${id.x}px, ${dropY + id.y}px) scale(${sc}) ${tilt ? "perspective(1800px) rotateX(4deg) rotateY(-6deg)" : ""}`,
        transformOrigin: "50% 40%",
        opacity: Math.min(1, e * 1.4),
        borderRadius: 22, overflow: "hidden",
        background: chrome.frame,
        border: `1px solid ${isDark ? rgba("#fff", 0.1) : chrome.line}`,
        boxShadow: shadow ? `0 50px 110px -40px ${rgba("#000", isDark ? 0.7 : 0.45)}, 0 2px 0 ${rgba("#fff", isDark ? 0.05 : 0.6)} inset` : "none",
      }}>
        {/* title bar */}
        <div style={{ height: barH, background: chrome.bar, display: "flex", alignItems: "center", padding: "0 22px", borderBottom: `1px solid ${chrome.line}` }}>
          <div style={{ display: "flex", gap: 10 }}>
            {LIGHTS.map((c) => <span key={c} style={{ width: 16, height: 16, borderRadius: 8, background: c }} />)}
          </div>
          <div style={{ flex: 1, textAlign: "center", fontSize: 24, fontWeight: 600, color: chrome.mute, paddingRight: 68 }}>
            {title}{body.kind === "code" && body.lang ? <span style={{ marginLeft: 10, fontSize: 18, padding: "2px 8px", borderRadius: 6, background: rgba(T.accent, 0.18), color: T.accent, fontFamily: MONO }}>.{body.lang}</span> : null}
          </div>
        </div>
        {/* address bar */}
        {url ? (
          <div style={{ height: urlH, display: "flex", alignItems: "center", padding: "0 18px", borderBottom: `1px solid ${chrome.line}` }}>
            <div style={{ flex: 1, height: 36, borderRadius: 10, background: rgba(isDark ? "#fff" : "#000", 0.06), display: "flex", alignItems: "center", padding: "0 14px", fontSize: 21, color: chrome.mute, fontFamily: MONO }}>
              <span style={{ width: 10, height: 10, borderRadius: 5, background: "#3E8C74", marginRight: 10 }} />{url}
            </div>
          </div>
        ) : null}
        {/* body row */}
        <div style={{ display: "flex", height: bodyH }}>
          {sideW ? (
            <div style={{ width: sideW, background: chrome.side, borderRight: `1px solid ${chrome.line}`, padding: "16px 12px", display: "flex", flexDirection: "column", gap: 6 }}>
              {sidebar!.map((s, i) => {
                const p = enter(t, 0.35 + i * 0.06, 0.35, 0.03);
                const on = i === activeIndex;
                return (
                  <div key={i} style={{ padding: "10px 12px", borderRadius: 10, fontSize: 22, fontWeight: on ? 700 : 500, color: on ? T.accent : chrome.mute, background: on ? rgba(T.accent, 0.14) : "transparent", opacity: p, transform: `translateX(${(1 - p) * -14}px)`, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {s}
                  </div>
                );
              })}
            </div>
          ) : null}
          <div style={{ flex: 1, padding: body.kind === "table" ? "18px 18px" : "26px 30px", fontFamily: bodyFont, color: chrome.text, overflow: "hidden" }}>
            {body.kind === "table" ? renderTable() : lines.map(renderLine)}
          </div>
        </div>
        {/* bottom status strip */}
        <div style={{ height: 34, background: chrome.bar, borderTop: `1px solid ${chrome.line}`, display: "flex", alignItems: "center", padding: "0 18px", fontSize: 17, color: chrome.mute, fontFamily: MONO, letterSpacing: 1 }}>
          MOCKUP
        </div>
      </div>
    </div>
  );
};

export const appWindowDemo: AppWindowProps = {
  theme: "cream",
  title: "Simple Note Editor",
  sidebar: ["Inbox", "Ideas", "Today", "Archive"],
  activeIndex: 2,
  body: {
    kind: "lines",
    lines: [
      "Plan for Tuesday",
      "- Ship the notes app",
      "- Call the plumber at 4",
      "- Read 20 pages",
    ],
  },
  cursor: true,
  shadow: true,
  tilt: true,
};
