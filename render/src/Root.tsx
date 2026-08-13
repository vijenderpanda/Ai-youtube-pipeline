import React from "react";
import { Composition } from "remotion";
import { ShortVideo, shortSchema } from "./ShortVideo";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Short"
    component={ShortVideo}
    schema={shortSchema}
    fps={30}
    width={1080}
    height={1920}
    durationInFrames={300}
    defaultProps={{
      videoSrc: "input.mp4",
      captions: [],
      style: "tier2" as const,
      handle: "@yourchannel",
      durationInFrames: 300,
    }}
    calculateMetadata={({ props }) => ({
      durationInFrames: props.durationInFrames,
    })}
  />
);
