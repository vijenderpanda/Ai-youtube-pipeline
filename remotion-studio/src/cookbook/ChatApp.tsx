import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BRAND, SANS, rgba, clamp, coverBg, Fonts } from "./kit";

/* =============================================================================
   ChatApp — an animated, believable-but-invented AI chat app screen.
   Cookbook role: the "fake app UI". Messages arrive on a schedule; the user's
   bubbles slide in from the right, each AI reply shows a typing indicator then
   springs in, and the thread bottom-anchors so the newest message is always in
   view (free auto-scroll). Drop it on a beat that talks about *using* an AI app
   without having to screen-record a real one.
   ========================================================================== */

export type ChatMessage = {
  from: "user" | "ai";
  text: string;
};

export type ChatAppProps = {
  /** message thread, in order. */
  messages: ChatMessage[];
  appName?: string; // header title, default "Prompt Deck"
  status?: string; // header subline, default "online"
  accent?: string; // user bubble + send button fill (brand magenta)
  ink?: string; // base fill
  perMsg?: number; // seconds a message dwells before the next starts (1.15)
  typing?: number; // seconds of typing dots before each AI reply (0.6)
  start?: number; // seconds before the first message appears
  width?: number;
  height?: number;
  transparent?: boolean; // skip the backdrop (overlay use)
};

const AI_BUBBLE = "#191922";
const DEVICE = "#101017";

type Scheduled = ChatMessage & { appear: number; typeStart: number };

export const ChatApp: React.FC<ChatAppProps> = ({
  messages,
  appName = "Prompt Deck",
  status = "online",
  accent = BRAND.mag,
  ink = BRAND.ink,
  perMsg = 1.15,
  typing = 0.6,
  start = 0.2,
  width = 1080,
  height = 1920,
  transparent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  /* build the timeline: each AI reply is preceded by `typing` seconds of dots. */
  const sched: Scheduled[] = [];
  let t = start;
  for (const m of messages) {
    const typeStart = t;
    const appear = m.from === "ai" ? t + typing : t;
    sched.push({ ...m, appear, typeStart });
    t = appear + perMsg;
  }

  // device geometry — a phone surface floated in the 9:16 frame
  const DW = Math.min(width - 180, 900);
  const DH = Math.min(height - 320, 1580);
  const dx = (width - DW) / 2;
  const dy = (height - DH) / 2;
  const HEAD = 176;
  const INPUT = 128;
  const PAD = 34;

  // typing indicator: active only in the gap before an AI reply that is next up
  const activeTyping = sched.find(
    (s) => s.from === "ai" && frame >= s.typeStart * fps && frame < s.appear * fps
  );

  return (
    <AbsoluteFill
      style={{
        background: transparent ? undefined : coverBg(accent, ink),
        fontFamily: SANS,
      }}
    >
      <Fonts />
      {/* device frame */}
      <div
        style={{
          position: "absolute",
          left: dx,
          top: dy,
          width: DW,
          height: DH,
          borderRadius: 60,
          background: DEVICE,
          border: `1.5px solid ${rgba("#ffffff", 0.08)}`,
          boxShadow: `0 40px 120px ${rgba("#000000", 0.6)}, inset 0 1px 0 ${rgba(
            "#ffffff",
            0.06
          )}`,
          overflow: "hidden",
        }}
      >
        {/* header */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: HEAD,
            display: "flex",
            alignItems: "center",
            gap: 22,
            padding: "0 40px",
            background: rgba("#000000", 0.25),
            borderBottom: `1px solid ${rgba("#ffffff", 0.06)}`,
            boxSizing: "border-box",
          }}
        >
          <div
            style={{
              width: 84,
              height: 84,
              borderRadius: 24,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 44,
              color: ink,
              background: `linear-gradient(140deg, ${accent}, ${BRAND.cyan})`,
              boxShadow: `0 8px 26px ${rgba(accent, 0.4)}`,
            }}
          >
            {"✦"}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 42, fontWeight: 800, color: BRAND.paper, letterSpacing: 0.3 }}>
              {appName}
            </div>
            <div style={{ marginTop: 6, fontSize: 26, color: rgba(BRAND.cyan, 0.9), display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ width: 14, height: 14, borderRadius: 999, background: "#33D67B", boxShadow: "0 0 12px #33D67B" }} />
              {status}
            </div>
          </div>
          <div style={{ fontSize: 40, color: BRAND.mute, letterSpacing: 3 }}>{"⋯"}</div>
        </div>

        {/* message viewport — bottom-anchored so newest stays visible */}
        <div
          style={{
            position: "absolute",
            top: HEAD,
            left: 0,
            width: "100%",
            height: DH - HEAD - INPUT,
            padding: `28px ${PAD}px`,
            boxSizing: "border-box",
            display: "flex",
            flexDirection: "column",
            justifyContent: "flex-end",
            gap: 24,
            overflow: "hidden",
          }}
        >
          {sched.map((m, i) => {
            const af = m.appear * fps;
            if (frame < af) return null;
            const s = spring({ frame: frame - af, fps, config: { damping: 16, mass: 0.6 } });
            const isUser = m.from === "user";
            const dx2 = interpolate(s, [0, 1], [isUser ? 60 : -60, 0]);
            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  justifyContent: isUser ? "flex-end" : "flex-start",
                  opacity: clamp(s * 1.4),
                  transform: `translateX(${dx2}px) scale(${interpolate(s, [0, 1], [0.94, 1])})`,
                }}
              >
                <div
                  style={{
                    maxWidth: "78%",
                    padding: "26px 32px",
                    fontSize: 38,
                    lineHeight: 1.34,
                    color: isUser ? ink : BRAND.paper,
                    background: isUser
                      ? `linear-gradient(160deg, ${accent}, ${rgba(accent, 0.82)})`
                      : AI_BUBBLE,
                    border: isUser ? "none" : `1px solid ${rgba("#ffffff", 0.07)}`,
                    borderRadius: 34,
                    borderBottomRightRadius: isUser ? 10 : 34,
                    borderBottomLeftRadius: isUser ? 34 : 10,
                    boxShadow: isUser ? `0 12px 34px ${rgba(accent, 0.34)}` : `0 12px 30px ${rgba("#000000", 0.4)}`,
                    fontWeight: isUser ? 600 : 500,
                  }}
                >
                  {m.text}
                </div>
              </div>
            );
          })}

          {/* typing indicator */}
          {activeTyping ? (
            <div style={{ display: "flex", justifyContent: "flex-start" }}>
              <div
                style={{
                  display: "flex",
                  gap: 14,
                  alignItems: "center",
                  padding: "30px 34px",
                  background: AI_BUBBLE,
                  border: `1px solid ${rgba("#ffffff", 0.07)}`,
                  borderRadius: 34,
                  borderBottomLeftRadius: 10,
                }}
              >
                {[0, 1, 2].map((d) => {
                  const bob = Math.sin((frame / fps) * 9 - d * 0.9);
                  return (
                    <span
                      key={d}
                      style={{
                        width: 20,
                        height: 20,
                        borderRadius: 999,
                        background: rgba(BRAND.paper, 0.5 + 0.5 * clamp((bob + 1) / 2)),
                        transform: `translateY(${-8 * clamp((bob + 1) / 2)}px)`,
                      }}
                    />
                  );
                })}
              </div>
            </div>
          ) : null}
        </div>

        {/* input bar */}
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            width: "100%",
            height: INPUT,
            display: "flex",
            alignItems: "center",
            gap: 20,
            padding: `0 ${PAD}px`,
            boxSizing: "border-box",
            background: rgba("#000000", 0.28),
            borderTop: `1px solid ${rgba("#ffffff", 0.06)}`,
          }}
        >
          <div
            style={{
              flex: 1,
              height: 76,
              borderRadius: 999,
              background: rgba("#ffffff", 0.05),
              border: `1px solid ${rgba("#ffffff", 0.08)}`,
              display: "flex",
              alignItems: "center",
              padding: "0 32px",
              fontSize: 32,
              color: BRAND.mute,
            }}
          >
            Message{"…"}
          </div>
          <div
            style={{
              width: 76,
              height: 76,
              borderRadius: 999,
              background: `linear-gradient(140deg, ${accent}, ${BRAND.cyan})`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 38,
              color: ink,
              boxShadow: `0 8px 24px ${rgba(accent, 0.4)}`,
            }}
          >
            {"↑"}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const chatAppDemo: ChatAppProps = {
  appName: "Prompt Deck",
  status: "online",
  messages: [
    { from: "user", text: "turn my messy notes into a 3-step plan" },
    { from: "ai", text: "Done. 1) Draft the outline  2) Cut to 3 beats  3) Write the last line first." },
    { from: "user", text: "make step 3 a hook" },
    { from: "ai", text: "“You’re writing the ending before the start — here’s why that wins.”" },
  ],
};
