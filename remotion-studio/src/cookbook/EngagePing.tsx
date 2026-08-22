import React from "react";
import { rgba } from "./kit";
import { clamp01, OUT_E, settle } from "./motion";
import { useFilmT } from "./filmclock";

/* =============================================================================
   EngagePing — VJ's engagement-glow experiment (ep3 first run).

   YouTube's Shorts UI paints its buttons OVER the video at fixed positions:
   the action rail (like/comment/share) down the right edge, the subscribe
   pill bottom-left by the handle. This component puts a pulsing glow halo in
   the frame at EXACTLY those positions plus a tiny tooltip — so the real
   button appears to light up, and the ask lands without covering content.

   Rules baked in: pings fire ON SCRIPT BEATS, never together; tooltip <= a
   few words, Gen Z-natural, never a lecture; ~2s and gone. Positions were
   mapped from VJ's annotated screenshot (1080x1920 frame space).
   ========================================================================== */

const MONO = "'JetBrains Mono', 'Courier New', monospace";
const DISP = "'Archivo Black', 'Arial Black', sans-serif";

const POS: Record<string, { x: number; y: number; side: "left" | "right" | "top" }> = {
  like: { x: 1002, y: 1218, side: "left" },
  comment: { x: 1002, y: 1372, side: "left" },
  share: { x: 1002, y: 1516, side: "left" },
  subscribe: { x: 566, y: 1618, side: "top" },
};

export type Ping = {
  at: number; kind: "like" | "comment" | "share" | "subscribe";
  tip: string; dur?: number;
};

export const EngagePing: React.FC<{ t?: number; ping: Ping; accent?: string }> = ({
  t: tProp, ping, accent = "#E8603C",
}) => {
  const filmT = useFilmT();
  const t = tProp ?? filmT;
  const { at, dur = 2.2 } = ping;
  if (t < at || t > at + dur) return null;
  const local = t - at;
  const on = OUT_E(clamp01(local / 0.35));
  const off = clamp01((local - (dur - 0.4)) / 0.4);
  const o = on * (1 - off);
  const p = POS[ping.kind];
  /* two expanding rings on a loop + a soft steady halo */
  const ring = (phase: number) => {
    const rp = ((local * 0.9 + phase) % 1);
    return (
      <div key={phase} style={{
        position: "absolute", left: p.x - 60 * rp - 30, top: p.y - 60 * rp - 30,
        width: 60 + 120 * rp, height: 60 + 120 * rp, borderRadius: "50%",
        border: `3px solid ${rgba(accent, (1 - rp) * 0.85)}`,
        pointerEvents: "none",
      }} />
    );
  };
  const tipW = 30 + ping.tip.length * 15;
  const tipX = p.side === "left" ? p.x - tipW - 74 : p.x - tipW / 2;
  const tipY = p.side === "top" ? p.y - 96 : p.y - 24;
  return (
    <div style={{ position: "absolute", inset: 0, zIndex: 44, opacity: o, pointerEvents: "none" }}>
      {/* the halo behind the real button */}
      <div style={{
        position: "absolute", left: p.x - 56, top: p.y - 56, width: 112, height: 112,
        borderRadius: "50%",
        background: `radial-gradient(circle, ${rgba(accent, 0.5)} 0%, ${rgba(accent, 0.18)} 45%, transparent 70%)`,
        transform: `scale(${1 + Math.sin(local * 6) * 0.08})`,
      }} />
      {ring(0)}
      {ring(0.5)}
      {/* the tooltip */}
      <div style={{
        position: "absolute", left: tipX, top: tipY,
        transform: `scale(${0.9 + on * 0.1 + settle(t, at, 0.4) * 0.06})`,
        transformOrigin: p.side === "left" ? "right center" : "center bottom",
        background: rgba("#211A12", 0.94), borderRadius: 12,
        padding: "7px 14px", boxShadow: `0 5px 14px ${rgba("#000", 0.4)}`,
        border: `1.5px solid ${rgba(accent, 0.6)}`,
      }}>
        <span style={{ fontFamily: DISP, fontSize: 26, color: "#FFF6EC", whiteSpace: "nowrap" as const }}>
          {ping.tip}
        </span>
        {/* pointer nub toward the button */}
        <div style={{
          position: "absolute",
          ...(p.side === "left"
            ? { right: -7, top: "50%", transform: "translateY(-50%) rotate(45deg)" }
            : { left: "50%", bottom: -7, transform: "translateX(-50%) rotate(45deg)" }),
          width: 14, height: 14, background: rgba("#211A12", 0.94),
          borderRight: `1.5px solid ${rgba(accent, 0.6)}`,
          borderTop: p.side === "left" ? `1.5px solid ${rgba(accent, 0.6)}` : undefined,
          borderBottom: p.side === "top" ? `1.5px solid ${rgba(accent, 0.6)}` : undefined,
        }} />
      </div>
    </div>
  );
};
