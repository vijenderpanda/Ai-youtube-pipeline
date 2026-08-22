import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig, Video } from "remotion";
import { rgba } from "./kit";
import { clamp01, OUT_E, settle } from "./motion";

/* =============================================================================
   LpaOutro — ep3's outro sting, in the film's own desk world (per-episode
   outro doctrine), with THE HOST BACK as a circle pip (VJ's call):

   Phase A (0 -> promptDur): the CTC-decoder prompt types on the dark console
     — PAUSE TO COPY.
   Phase B: the question card CTC MINUS IN-HAND / TUMHARA GAP / KITNA? with
     the coral accent + comment/subscribe pills — and SOL in a circular pip,
     ring animated (rotating dash + breathing glow), talking the CTA.

   hostSrc: a HeyGen talking-head clip at build; falls back to the pinned
   outfit_11 still so the storyboard gate can see the layout without a
   HeyGen spend.
   ========================================================================== */

const W3 = {
  ground: "#F1EADB", ground2: "#F8F3E7", ink: "#2C261C",
  coral: "#E8603C", green: "#4ADE80",
};
const MONO = "'JetBrains Mono', 'Courier New', monospace";
const DISP = "'Playfair Display', Georgia, serif";
const BOLD = "'Archivo Black', 'Arial Black', sans-serif";
const cardShadow = `0 6px 10px ${rgba("#000", 0.5)}, 0 36px 80px ${rgba("#000", 0.3)}`;

export type LpaOutroProps = {
  q?: string;                 // "LINE1|LINE2|LINE3"
  accentWord?: string;
  promptText?: string;
  promptDur?: number;
  hostSrc?: string;           // heygen mp4 (staticFile path) — still fallback if absent
  width?: number; height?: number;
};

export const LpaOutro: React.FC<LpaOutroProps> = ({
  q = "CTC − IN-HAND|TUMHARA GAP|KITNA?",
  accentWord = "KITNA?",
  promptText = "Break my CTC of ₹____ into real monthly in-hand (new regime FY25-26). List every deduction step by step, which lines come back, and the ONE line to negotiate.",
  promptDur = 3.4,
  hostSrc,
  width = 1080, height = 1920,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const phaseB = t >= promptDur;
  const bT = t - promptDur;

  const typed = Math.floor(clamp01((t - 0.15) / (promptDur * 0.55)) * promptText.length);
  const qOn = OUT_E(clamp01(bT / 0.5));
  const pipOn = OUT_E(clamp01((bT - 0.3) / 0.5));
  const lines = q.split("|");

  return (
    <AbsoluteFill style={{ width, height }}>
      <AbsoluteFill style={{
        background: `radial-gradient(120% 85% at 50% 40%, ${W3.ground2} 0%, ${W3.ground} 60%, #D5C9B2 100%)`,
      }} />
      <Img src={staticFile("assets/lpa/desk_scene.png")} style={{
        position: "absolute", left: -60, top: 980, width: 1200, height: 750,
        objectFit: "cover", opacity: 0.55, borderRadius: 24,
        filter: "brightness(0.8)",
        transform: `scale(${1.02 + Math.sin(t * 0.6) * 0.008})`,
      }} />

      {/* phase A: the console — PAUSE TO COPY */}
      {!phaseB || bT < 0.5 ? (
        <div style={{ position: "absolute", left: 70, top: 430, width: 940,
          opacity: phaseB ? 1 - bT / 0.5 : 1 }}>
          <div style={{ background: "linear-gradient(180deg, #14231A, #0D1811)", borderRadius: 20,
            padding: "26px 30px", boxShadow: cardShadow, border: `1.5px solid ${rgba(W3.green, 0.35)}` }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontFamily: MONO, fontSize: 23, color: W3.green, letterSpacing: 2 }}>✳ CTC DECODER</span>
              <span style={{ fontFamily: MONO, fontSize: 21, color: "#0D1811", background: W3.green,
                borderRadius: 8, padding: "4px 12px", fontWeight: 700,
                opacity: typed >= promptText.length ? 1 : 0.25 }}>PINNED ✓ COPY KARO</span>
            </div>
            <div style={{ marginTop: 14, fontFamily: MONO, fontSize: 28, lineHeight: 1.55,
              color: "#D9F2E2", minHeight: 250 }}>
              {"> "}{promptText.slice(0, typed)}
              {typed < promptText.length ? <span style={{ opacity: Math.sin(t * 9) > 0 ? 1 : 0 }}>▌</span> : null}
            </div>
            <div style={{ marginTop: 12, textAlign: "center", fontFamily: MONO, fontSize: 22,
              letterSpacing: 4, color: rgba("#D9F2E2", 0.55),
              opacity: typed >= promptText.length ? 1 : 0 }}>PAUSE · COPY KARO</div>
          </div>
        </div>
      ) : null}

      {/* phase B: the question card + the host pip */}
      {phaseB ? (
        <>
          <div style={{ position: "absolute", left: 70, top: 480, width: 940, opacity: qOn,
            transform: `translateY(${(1 - qOn) * 60}px) scale(${0.96 + qOn * 0.04})` }}>
            <div style={{ background: "linear-gradient(180deg, #2B241C, #1C160F)", borderRadius: 26,
              padding: "60px 50px", boxShadow: cardShadow, textAlign: "center",
              border: `1px solid ${rgba("#FFF", 0.08)}` }}>
              {lines.map((ln, i) => (
                <div key={i} style={{ fontFamily: DISP, fontWeight: 800, fontSize: 88, lineHeight: 1.16,
                  color: ln.trim() === accentWord ? W3.coral : "#F2E8D8" }}>{ln}</div>
              ))}
              <div style={{ marginTop: 26, display: "inline-block", fontFamily: MONO, fontSize: 24,
                color: W3.green, border: `1.5px solid ${rgba(W3.green, 0.5)}`, borderRadius: 10,
                padding: "6px 18px", background: rgba("#0D1811", 0.6) }}>AI COST: STILL ₹0</div>
            </div>
          </div>

          {/* comment + subscribe pills */}
          <div style={{ position: "absolute", left: 0, right: 0, top: 1560, display: "flex",
            justifyContent: "center", gap: 20, opacity: OUT_E(clamp01((bT - 0.7) / 0.5)) }}>
            <div style={{ fontFamily: BOLD, fontSize: 34, color: "#FFF6EC", background: W3.coral,
              borderRadius: 30, padding: "10px 30px", boxShadow: cardShadow }}>
              Comment: tumhara gap? 👇
            </div>
          </div>

          {/* THE HOST PIP — circular, ring animated, talking head */}
          <div style={{ position: "absolute", right: 64, top: 190, width: 300, height: 300,
            opacity: pipOn, transform: `scale(${0.8 + pipOn * 0.2 + settle(t, promptDur + 0.3, 0.5) * 0.06})
              translateY(${Math.sin(t * 1.4) * 5}px)` }}>
            {/* rotating dashed ring */}
            <svg width={300} height={300} viewBox="0 0 300 300" style={{ position: "absolute", inset: 0 }}>
              <circle cx={150} cy={150} r={143} fill="none" stroke={W3.coral} strokeWidth={5}
                strokeDasharray="34 18" strokeLinecap="round"
                transform={`rotate(${t * 40} 150 150)`} />
              <circle cx={150} cy={150} r={132} fill="none" stroke={rgba("#FFF", 0.5)} strokeWidth={2} />
            </svg>
            {/* breathing glow */}
            <div style={{ position: "absolute", inset: -22, borderRadius: "50%",
              background: `radial-gradient(circle, transparent 55%, ${rgba(W3.coral, 0.24 + Math.sin(t * 3) * 0.1)} 72%, transparent 82%)` }} />
            <div style={{ position: "absolute", inset: 14, borderRadius: "50%", overflow: "hidden",
              boxShadow: cardShadow, background: "#1C160F" }}>
              {hostSrc ? (
                <Video src={staticFile(hostSrc)} style={{ width: "100%", height: "100%", objectFit: "cover" }} muted={false} />
              ) : (
                <Img src={staticFile("assets/character/host_library/outfit_11_sol_magenta/center.jpg")}
                  style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "center 12%" }} />
              )}
            </div>
            {/* name tag */}
            <div style={{ position: "absolute", left: "50%", bottom: -14, transform: "translateX(-50%)",
              fontFamily: MONO, fontSize: 20, letterSpacing: 2, color: "#FFF6EC",
              background: rgba("#211A12", 0.94), borderRadius: 9, padding: "3px 14px",
              boxShadow: cardShadow, whiteSpace: "nowrap" as const }}>SOL · AI UNPACKED</div>
          </div>
        </>
      ) : null}

      {/* grain + vignette to match the film */}
      <svg style={{ position: "absolute", inset: 0, opacity: 0.05, mixBlendMode: "overlay", pointerEvents: "none" }}>
        <filter id="lo-grain"><feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" seed={11} /></filter>
        <rect width="100%" height="100%" filter="url(#lo-grain)" />
      </svg>
      <div style={{ position: "absolute", inset: 0, pointerEvents: "none",
        background: `radial-gradient(130% 95% at 50% 42%, transparent 55%, ${rgba("#4A3B26", 0.28)} 100%)` }} />
    </AbsoluteFill>
  );
};

export const lpaOutroDemo: LpaOutroProps = {};
