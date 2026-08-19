import React from "react";
import { AbsoluteFill, Img, OffthreadVideo, staticFile } from "remotion";
import { layoutById, Rect } from "./layouts";
import { CookbookBlock } from "./cookbook/components";
import { BRAND, rgba, coverBg, SANS } from "./cookbook/kit";

/* =============================================================================
   SlotScene — renders a scene from a LAYOUT id + its slot fills.

   The generic, slot-composed layouts (host-top / host-bottom / split / host-pip
   / full-broll) place two kinds of content — a host clip and a b-roll — into the
   regions the layout defines (layouts.ts). "Which layout" (geometry) is fully
   decoupled from "what fills it" (content): the same LineReveal can sit full-
   frame in `full-broll` or in the lower band of `host-top`.

   A cookbook fill is designed at 1080x1920, so it's scaled to fit its region
   (FitBox, letterboxed); media (image/video) cover-fits. The global karaoke
   caption is still drawn by Short over the whole frame — the layout's
   `captionZone` says where it belongs (wired further in a later sprint).
   ========================================================================== */

const res = (p: string) => (p.startsWith("http") ? p : staticFile(p));

export type SlotBroll = {
  kind: "cookbook" | "image" | "video";
  id?: string; // cookbook component id
  props?: Record<string, unknown>; // cookbook props
  src?: string; // image/video src
  from?: number; // video start (seconds)
  transparent?: boolean;
};
export type SlotHost = {
  src?: string; // host clip (HeyGen/EchoMimic); placeholder card if absent
  label?: string; // shown on the placeholder
};
export type SlotSceneProps = {
  layout: string;
  broll?: SlotBroll;
  host?: SlotHost;
  tag?: string;
  accent?: string;
  ink?: string;
  width?: number;
  height?: number;
};

/* absolutely-position + scale a 1080x1920 child to fit `rect`, letterboxed. */
const FitBox: React.FC<{ rect: Rect; W: number; H: number; radius?: number; children: React.ReactNode }> = ({
  rect,
  W,
  H,
  radius = 26,
  children,
}) => {
  const rw = rect.w * W;
  const rh = rect.h * H;
  const scale = Math.min(rw / 1080, rh / 1920);
  return (
    <div style={{ position: "absolute", left: rect.x * W, top: rect.y * H, width: rw, height: rh, overflow: "hidden", borderRadius: radius }}>
      <div style={{ position: "absolute", left: rw / 2, top: rh / 2, width: 1080, height: 1920, transform: `translate(-50%,-50%) scale(${scale})` }}>
        {children}
      </div>
    </div>
  );
};

const CoverBox: React.FC<{ rect: Rect; W: number; H: number; radius?: number; children: React.ReactNode }> = ({
  rect,
  W,
  H,
  radius = 26,
  children,
}) => (
  <div style={{ position: "absolute", left: rect.x * W, top: rect.y * H, width: rect.w * W, height: rect.h * H, overflow: "hidden", borderRadius: radius }}>
    {children}
  </div>
);

export const SlotScene: React.FC<SlotSceneProps> = ({
  layout,
  broll,
  host,
  tag,
  accent = BRAND.mag,
  ink = BRAND.ink,
  width = 1080,
  height = 1920,
}) => {
  const def = layoutById(layout);
  if (!def) {
    return (
      <AbsoluteFill style={{ background: "#1a0b12", color: BRAND.mag, alignItems: "center", justifyContent: "center", fontFamily: "monospace", fontSize: 40 }}>
        {`unknown layout "${layout}"`}
      </AbsoluteFill>
    );
  }
  const W = width;
  const H = height;
  const cover = { width: "100%", height: "100%", objectFit: "cover" as const };

  return (
    <AbsoluteFill style={{ background: coverBg(accent, ink), fontFamily: SANS }}>
      {/* b-roll slot */}
      {def.slots.broll && broll
        ? broll.kind === "cookbook" && broll.id
          ? (
            <FitBox rect={def.slots.broll} W={W} H={H}>
              <CookbookBlock id={broll.id} props={broll.props} transparent={broll.transparent} />
            </FitBox>
          )
          : (
            <CoverBox rect={def.slots.broll} W={W} H={H}>
              {broll.kind === "video" && broll.src ? (
                <OffthreadVideo src={res(broll.src)} startFrom={Math.round((broll.from ?? 0) * 30)} muted style={cover} />
              ) : broll.src ? (
                <Img src={res(broll.src)} style={cover} />
              ) : null}
            </CoverBox>
          )
        : null}

      {/* host slot — clip if present, else a labeled placeholder card */}
      {def.slots.host ? (
        <CoverBox rect={def.slots.host} W={W} H={H} radius={30}>
          {host && host.src ? (
            <OffthreadVideo src={res(host.src)} muted style={cover} />
          ) : (
            <div
              style={{
                width: "100%",
                height: "100%",
                background: `linear-gradient(160deg, ${rgba(accent, 0.5)}, ${rgba("#12060c", 0.9)})`,
                border: `1.5px solid ${rgba("#ffffff", 0.12)}`,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: 14,
                color: BRAND.paper,
              }}
            >
              <div style={{ fontSize: 64 }}>{"🧑🏻‍🦰"}</div>
              <div style={{ fontSize: 26, letterSpacing: 1, color: rgba(BRAND.paper, 0.85) }}>HOST</div>
              {host?.label ? (
                <div style={{ fontFamily: "monospace", fontSize: 20, color: rgba(BRAND.paper, 0.6) }}>{host.label}</div>
              ) : null}
            </div>
          )}
        </CoverBox>
      ) : null}

      {/* #tag slot */}
      {def.slots.tag && tag ? (
        <div
          style={{
            position: "absolute",
            left: def.slots.tag.x * W,
            top: def.slots.tag.y * H,
            padding: "10px 22px",
            borderRadius: 999,
            background: rgba("#10101a", 0.6),
            border: `1.5px solid ${rgba(accent, 0.5)}`,
            color: BRAND.paper,
            fontSize: 30,
            fontWeight: 700,
          }}
        >
          {tag}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
