import React from "react";
import { useCurrentFrame, useVideoConfig, AbsoluteFill, spring } from "remotion";
import { createTikTokStyleCaptions, type Caption } from "@remotion/captions";
import { loadFont } from "@remotion/google-fonts/Inter";

const { fontFamily } = loadFont("normal", { weights: ["800", "900"] });

type Word = { text: string; startMs: number; endMs: number };

export const Captions: React.FC<{
  captions: Word[];
  style: "tier1" | "tier2";
}> = ({ captions, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ms = (frame / fps) * 1000;

  const asCaptions: Caption[] = captions.map((w) => ({
    text: w.text + " ",
    startMs: w.startMs,
    endMs: w.endMs,
    timestampMs: (w.startMs + w.endMs) / 2,
    confidence: 1,
  }));

  const { pages } = createTikTokStyleCaptions({
    captions: asCaptions,
    combineTokensWithinMilliseconds: 1200,
  });

  const page = pages.find((p) => ms >= p.startMs && ms < p.startMs + p.durationMs);
  if (!page) return null;

  const pop = spring({
    frame: frame - Math.round((page.startMs / 1000) * fps),
    fps,
    config: { damping: 12 },
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 380,
      }}
    >
      <div
        style={{
          maxWidth: 900,
          textAlign: "center",
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: 10,
          transform: `scale(${0.9 + pop * 0.1})`,
        }}
      >
        {page.tokens.map((t, i) => {
          const active = ms >= t.fromMs && ms < t.toMs;
          const base: React.CSSProperties = {
            fontFamily,
            fontWeight: 900,
            fontSize: 68,
            lineHeight: 1.1,
            color: "#fff",
            textTransform: "uppercase",
            padding: "2px 14px",
            borderRadius: 14,
            textShadow: "0 4px 18px rgba(0,0,0,0.6)",
          };
          const hi =
            style === "tier2"
              ? {
                  background: "linear-gradient(90deg,#A855F7,#EC4899)",
                  transform: "scale(1.08)",
                }
              : { background: "#3B82F6" };
          return (
            <span key={i} style={{ ...base, ...(active ? hi : {}) }}>
              {t.text.trim()}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
