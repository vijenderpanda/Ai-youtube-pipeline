import React from "react";
import {
  AbsoluteFill,
  Img,
  staticFile,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

/* OutroCard (v16.2) — a stronger Vaibhav-style outro: a question-CTA wrapped in
   containers on the brand gradient, with the Sol avatar, a comment prompt, a
   subscribe pill, and gentle float. Replaces the shared subscribe/comment sting
   for premium episodes. Rendered silent (music is added by build_ep_v2's concat). */

const MAG = "#E0218A";
const ACCENT = "#22D3EE";
const INK = "#0E0E14";
const GRAD_BG =
  "radial-gradient(140% 88% at 50% 6%, rgba(224,33,138,0.30) 0%, rgba(150,28,116,0.12) 26%, rgba(14,14,20,0) 56%)," +
  "radial-gradient(85% 55% at 84% 94%, rgba(34,211,238,0.12) 0%, rgba(14,14,20,0) 52%)," +
  "linear-gradient(178deg, #1c1122 0%, #130d17 42%, #0E0E14 80%)";

const floatY = (frame: number, fps: number, amp: number, periodS: number, phaseS = 0) =>
  amp * Math.sin(((frame / fps) + phaseS) * ((2 * Math.PI) / periodS));

export type OutroCardProps = {
  avatar: string;      // path (under assets/) to the Sol still
  question: string;    // big question, e.g. "WHICH COMMAND FIRST?"
  commentCta: string;  // e.g. "Comment your #1 👇"
  tagline?: string;    // e.g. "one AI trick, every single day"
};

export const OutroCard: React.FC<OutroCardProps> = ({ avatar, question, commentCta, tagline }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = (delay: number) =>
    spring({ frame: frame - delay, fps, config: { damping: 15, mass: 0.6 } });

  const avF = floatY(frame, fps, 8, 3.6, 0);
  const qF = floatY(frame, fps, 6, 4.0, 1.0);
  const ctaF = floatY(frame, fps, 5, 4.4, 2.0);

  const a = pop(2);
  const q = pop(8);
  const c = pop(16);
  const s = pop(24);

  return (
    <AbsoluteFill style={{ background: GRAD_BG, fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif' }}>
      <AbsoluteFill
        style={{ background: "radial-gradient(120% 80% at 50% 42%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.45) 100%)" }}
      />

      {/* Sol avatar — rounded circle */}
      <div
        style={{
          position: "absolute",
          top: 300,
          left: "50%",
          width: 300,
          height: 300,
          marginLeft: -150,
          transform: `translateY(${avF}px) scale(${interpolate(a, [0, 1], [0.8, 1])})`,
          opacity: a,
          borderRadius: "50%",
          overflow: "hidden",
          border: `4px solid ${MAG}`,
          boxShadow: `0 20px 60px rgba(0,0,0,0.5), 0 0 40px rgba(224,33,138,0.35)`,
          background: INK,
        }}
      >
        <Img
          src={avatar.startsWith("http") ? avatar : staticFile(avatar)}
          style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "57% 14%", transform: "scale(1.05)" }}
        />
      </div>

      {/* Question */}
      <div
        style={{
          position: "absolute",
          top: 660,
          left: 60,
          right: 60,
          textAlign: "center",
          transform: `translateY(${qF}px)`,
          opacity: q,
          fontFamily: "'Playfair Display', Georgia, serif",
          fontStyle: "italic",
          fontWeight: 900,
          fontSize: 92,
          lineHeight: 1.02,
          color: "white",
          textShadow: "0 6px 26px rgba(0,0,0,0.6)",
        }}
      >
        {question}
      </div>

      {/* Comment CTA pill (cyan) */}
      <div
        style={{
          position: "absolute",
          top: 986,
          left: "50%",
          transform: `translateX(-50%) translateY(${ctaF}px) scale(${interpolate(c, [0, 1], [0.85, 1])})`,
          opacity: c,
          display: "flex",
          alignItems: "center",
          gap: 14,
          padding: "22px 44px",
          borderRadius: 999,
          border: `2.5px solid ${ACCENT}`,
          background: "rgba(34,211,238,0.10)",
          color: ACCENT,
          fontWeight: 800,
          fontSize: 44,
          whiteSpace: "nowrap",
          boxShadow: `0 0 30px rgba(34,211,238,0.25)`,
        }}
      >
        {commentCta}
      </div>

      {/* Subscribe pill (magenta) */}
      <div
        style={{
          position: "absolute",
          top: 1176,
          left: "50%",
          transform: `translateX(-50%) scale(${interpolate(s, [0, 1], [0.85, 1])})`,
          opacity: s,
          padding: "26px 70px",
          borderRadius: 999,
          background: MAG,
          color: "white",
          fontWeight: 900,
          fontSize: 52,
          letterSpacing: 1,
          boxShadow: `0 16px 44px rgba(224,33,138,0.45), 0 0 40px rgba(224,33,138,0.3)`,
        }}
      >
        SUBSCRIBE
      </div>

      {tagline ? (
        <div
          style={{
            position: "absolute",
            top: 1316,
            left: 0,
            right: 0,
            textAlign: "center",
            opacity: s * 0.8,
            color: "#c9c4d0",
            fontSize: 34,
            fontWeight: 600,
          }}
        >
          {tagline}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
