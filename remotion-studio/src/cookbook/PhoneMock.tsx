import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { Fonts, SANS, SERIF, rgba, themeTokens, type CookTheme } from "./kit";
import { enter, idle, settle } from "./motion";

/* =============================================================================
   PhoneMock — a believable phone frame (9:19.5, dynamic island, status bar)
   holding an in-app messaging thread: grey incoming / accent outgoing bubbles,
   contact header, typing dots, messages arriving on a schedule, bottom-anchored.
   Clones comp-dna: DirGcMXm4zw "iMessage phone mockup", VSC5E0okvD4
   "app/phone mockup frame", cUG0TGwE9-4 "phone-mock frame". Distinct from
   NotificationStack / DynamicIsland (lock-screen surfaces) — this is the thread.
   Cream-first (theme:"cream" default), retintable via accent/bg.
   HONESTY: a generic, invented thread. Never present it as a screenshot of a
   real shipped app, a real person's messages, or a real product's UI.
   ========================================================================== */

export type PhoneMsg = {
  /** seconds (relative to `start`) the bubble lands. */
  t: number;
  from: "me" | "them";
  text: string;
};

export type PhoneMockProps = {
  messages: PhoneMsg[];
  /** header name shown above the thread. */
  contact?: string;
  /** tiny app label shown in the status bar / header (generic, e.g. "Messages"). */
  appName?: string;
  /** subtle 3D tilt in degrees (rotateY). 0 = flat. */
  tilt?: number;
  /** overall scale of the device (1 ≈ 640px wide). */
  scale?: number;
  /** show typing dots for this many seconds before each "them" bubble. */
  typingLead?: number;
  theme?: CookTheme;
  accent?: string;
  bg?: string;
  transparent?: boolean;
  start?: number;
};

const DEV_W = 640;
const DEV_H = Math.round(DEV_W * (19.5 / 9)); // 1387
const CX = 540;
const CY = 770; // device centre — keeps the bottom edge ≈ y=1553, above caption zone

export const PhoneMock: React.FC<PhoneMockProps> = ({
  messages = [],
  contact = "Assistant",
  appName = "Messages",
  tilt = 6,
  scale = 1,
  typingLead = 0.9,
  theme = "cream",
  accent,
  bg,
  transparent = false,
  start = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - start;
  const tok = themeTokens(theme, accent, bg);
  const cream = theme === "cream";

  // device arrival: scale-up with mass, then a very faint idle so a hold breathes
  const arrive = enter(t, 0, 0.55, 0.04);
  const drift = idle(t, 3, 1.6);
  const sc = scale * (0.9 + 0.1 * arrive);

  // screen palette — the thread itself is a dark/light "app", independent of canvas
  const screenBg = cream ? "#F7F6F2" : "#0B0B10";
  const screenInk = cream ? "#141414" : "#F2F2F8";
  const inBubble = cream ? "#E5E4E0" : "#26262F";
  const inInk = cream ? "#141414" : "#F2F2F8";
  const bezel = cream ? "#1C1C1A" : "#08080C";

  const visible = messages.filter((m) => t >= m.t);
  // typing indicator: next "them" message within typingLead seconds
  const next = messages.find((m) => t < m.t);
  const typing = next && next.from === "them" && t >= next.t - typingLead;

  const W = DEV_W, H = DEV_H;
  const screenInset = 14;
  const headerH = 150;
  const composerH = 86;

  return (
    <div style={{ position: "absolute", inset: 0, background: transparent ? "transparent" : tok.bg, fontFamily: SANS }}>
      <Fonts />
      {/* soft ground shadow under the device */}
      <div style={{
        position: "absolute", left: CX - 260, top: CY + H / 2 - 40, width: 520, height: 90,
        borderRadius: "50%", background: rgba("#000", 0.28), filter: "blur(40px)",
        opacity: arrive, transform: `scaleX(${sc})`,
      }} />
      <div style={{
        position: "absolute", left: CX - W / 2, top: CY - H / 2, width: W, height: H,
        transform: `perspective(2200px) translate(${drift.x}px, ${drift.y}px) rotateY(${tilt}deg) rotateX(${-tilt * 0.35}deg) scale(${sc})`,
        transformOrigin: "50% 50%",
        opacity: Math.min(1, arrive * 1.4),
      }}>
        {/* bezel */}
        <div style={{
          position: "absolute", inset: 0, borderRadius: 96, background: bezel,
          boxShadow: `0 50px 120px -40px ${rgba("#000", 0.7)}, inset 0 0 0 2px ${rgba("#fff", 0.16)}, inset 0 0 0 6px ${rgba("#fff", 0.04)}`,
        }} />
        {/* side buttons */}
        <div style={{ position: "absolute", left: -5, top: 260, width: 5, height: 58, borderRadius: 3, background: bezel }} />
        <div style={{ position: "absolute", left: -5, top: 340, width: 5, height: 110, borderRadius: 3, background: bezel }} />
        <div style={{ position: "absolute", right: -5, top: 380, width: 5, height: 160, borderRadius: 3, background: bezel }} />
        {/* screen */}
        <div style={{
          position: "absolute", left: screenInset, top: screenInset, right: screenInset, bottom: screenInset,
          borderRadius: 84, background: screenBg, overflow: "hidden", color: screenInk,
        }}>
          {/* status bar */}
          <div style={{ position: "absolute", top: 26, left: 44, fontSize: 26, fontWeight: 700, letterSpacing: -0.3 }}>9:41</div>
          <div style={{ position: "absolute", top: 30, right: 44, display: "flex", gap: 8, alignItems: "center" }}>
            {[10, 14, 18, 22].map((h, i) => (
              <div key={i} style={{ width: 6, height: h, borderRadius: 2, background: screenInk, alignSelf: "flex-end", opacity: i < 3 ? 1 : 0.35 }} />
            ))}
            <div style={{ width: 44, height: 22, borderRadius: 7, border: `2px solid ${rgba(screenInk, 0.6)}`, marginLeft: 8, position: "relative" }}>
              <div style={{ position: "absolute", left: 3, top: 3, bottom: 3, width: 26, borderRadius: 3, background: screenInk }} />
            </div>
          </div>
          {/* dynamic island */}
          <div style={{ position: "absolute", top: 18, left: "50%", transform: "translateX(-50%)", width: 190, height: 56, borderRadius: 28, background: "#000" }} />
          {/* header */}
          <div style={{
            position: "absolute", top: 0, left: 0, right: 0, height: headerH,
            borderBottom: `1px solid ${rgba(screenInk, 0.1)}`,
            display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "flex-end", paddingBottom: 10,
            background: rgba(screenBg, 0.92),
          }}>
            <div style={{ position: "absolute", left: 22, bottom: 16, color: tok.accent, fontSize: 24, fontWeight: 600 }}>‹ {appName}</div>
            <div style={{
              width: 58, height: 58, borderRadius: 29, background: tok.accent, color: "#fff",
              display: "flex", alignItems: "center", justifyContent: "center", fontSize: 26, fontWeight: 700, marginBottom: 6,
            }}>{contact.slice(0, 1).toUpperCase()}</div>
            <div style={{ fontSize: 22, fontWeight: 600, opacity: 0.9 }}>{contact}</div>
          </div>
          {/* thread — bottom anchored */}
          <div style={{
            position: "absolute", left: 0, right: 0, top: headerH, bottom: composerH,
            display: "flex", flexDirection: "column", justifyContent: "flex-end", gap: 12,
            padding: "0 22px 18px", overflow: "hidden",
          }}>
            {visible.map((m, i) => {
              const a = enter(t, m.t, 0.36, 0.08);
              const s = settle(t, m.t, 0.4);
              const me = m.from === "me";
              return (
                <div key={i} style={{
                  alignSelf: me ? "flex-end" : "flex-start", maxWidth: "78%",
                  background: me ? tok.accent : inBubble, color: me ? "#fff" : inInk,
                  fontSize: 27, lineHeight: "34px", padding: "14px 20px",
                  borderRadius: 26,
                  borderBottomRightRadius: me ? 8 : 26, borderBottomLeftRadius: me ? 26 : 8,
                  transform: `translateY(${(1 - a) * 28}px) scale(${0.92 + 0.08 * a + s * 0.03})`,
                  transformOrigin: me ? "100% 100%" : "0% 100%",
                  opacity: Math.min(1, a * 1.5),
                }}>{m.text}</div>
              );
            })}
            {typing ? (
              <div style={{
                alignSelf: "flex-start", background: inBubble, borderRadius: 26, borderBottomLeftRadius: 8,
                padding: "16px 20px", display: "flex", gap: 7,
                opacity: Math.min(1, enter(t, next!.t - typingLead, 0.25, 0)),
              }}>
                {[0, 1, 2].map((k) => (
                  <div key={k} style={{
                    width: 12, height: 12, borderRadius: 6, background: rgba(inInk, 0.5),
                    transform: `translateY(${Math.sin(t * 9 - k * 0.9) * 3}px)`,
                  }} />
                ))}
              </div>
            ) : null}
          </div>
          {/* composer */}
          <div style={{
            position: "absolute", left: 0, right: 0, bottom: 0, height: composerH,
            display: "flex", alignItems: "center", gap: 12, padding: "0 22px 20px",
          }}>
            <div style={{ width: 40, height: 40, borderRadius: 20, background: rgba(screenInk, 0.1), display: "flex", alignItems: "center", justifyContent: "center", fontSize: 26, color: rgba(screenInk, 0.6) }}>+</div>
            <div style={{ flex: 1, height: 44, borderRadius: 22, border: `1.5px solid ${rgba(screenInk, 0.18)}`, display: "flex", alignItems: "center", padding: "0 16px", fontSize: 22, color: rgba(screenInk, 0.4) }}>{appName === "Messages" ? "iMessage" : "Message"}</div>
            <div style={{ width: 40, height: 40, borderRadius: 20, background: tok.accent, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24, fontWeight: 800 }}>↑</div>
          </div>
          {/* home indicator */}
          <div style={{ position: "absolute", bottom: 10, left: "50%", transform: "translateX(-50%)", width: 180, height: 6, borderRadius: 3, background: rgba(screenInk, 0.5) }} />
        </div>
      </div>
      {/* small serif caption under the device: the punch word, stays above caption zone */}
      <div style={{
        position: "absolute", left: 80, right: 80, top: 1462, textAlign: "center",
        fontFamily: SERIF, fontStyle: "italic", fontSize: 40, color: tok.mute, opacity: arrive,
      }}>just text it.</div>
    </div>
  );
};

export const phoneMockDemo: PhoneMockProps = {
  contact: "Claude",
  appName: "Messages",
  tilt: 6,
  theme: "cream",
  messages: [
    { t: 0.6, from: "me", text: "Remind me to call Mom at 6 tonight" },
    { t: 2.0, from: "them", text: "Done — reminder set for 6:00 PM. Want me to add it to your calendar too?" },
    { t: 3.8, from: "me", text: "Yes, and move my 5pm to tomorrow" },
    { t: 5.6, from: "them", text: "Moved. Tomorrow 5:00 PM, invite updated. Anything else?" },
    { t: 7.2, from: "me", text: "That's it 🙌" },
  ],
};
