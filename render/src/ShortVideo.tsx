import React from "react";
import { AbsoluteFill, OffthreadVideo, staticFile } from "remotion";
import { z } from "zod";
import { Captions } from "./Captions";

export const shortSchema = z.object({
  videoSrc: z.string(),
  captions: z.array(
    z.object({ text: z.string(), startMs: z.number(), endMs: z.number() })
  ),
  style: z.enum(["tier1", "tier2"]),
  handle: z.string(),
  durationInFrames: z.number(),
});

export const ShortVideo: React.FC<z.infer<typeof shortSchema>> = ({
  videoSrc,
  captions,
  style,
  handle,
}) => (
  <AbsoluteFill style={{ backgroundColor: "black" }}>
    <OffthreadVideo src={staticFile(videoSrc)} />
    {style === "tier2" && (
      <AbsoluteFill style={{ padding: 48, pointerEvents: "none" }}>
        {/* story bar */}
        <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
          {[1, 0.9, 0.35, 0.35, 0.35].map((o, i) => (
            <div
              key={i}
              style={{
                flex: 1,
                height: 5,
                borderRadius: 3,
                background: `rgba(255,255,255,${o})`,
              }}
            />
          ))}
        </div>
        {/* handle + follow */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            marginTop: 20,
          }}
        >
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 22,
              background: "#EC4899",
              border: "2px solid #fff",
            }}
          />
          <span
            style={{
              color: "#fff",
              fontWeight: 700,
              fontSize: 30,
              fontFamily: "sans-serif",
            }}
          >
            {handle}
          </span>
          <div
            style={{
              marginLeft: 8,
              padding: "6px 18px",
              borderRadius: 20,
              fontSize: 24,
              fontWeight: 700,
              color: "#fff",
              background: "linear-gradient(90deg,#A855F7,#EC4899)",
              fontFamily: "sans-serif",
            }}
          >
            Follow
          </div>
        </div>
      </AbsoluteFill>
    )}
    <Captions captions={captions} style={style} />
  </AbsoluteFill>
);
