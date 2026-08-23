import React from "react";
import {
  AbsoluteFill,
  Easing,
  OffthreadVideo,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { AuroraBed, BRAND, Fonts, MONO, SAFE, clamp, glassChrome, rgba } from "./kit";

/* =============================================================================
   WebTour — a REAL recorded web page, toured by a scripted camera.

   The tape (a rec_web_tour.py capture of a live site) is staged as a glass
   card and a camera pans/zooms INTO it: punch to the repo title, drift across
   the README, sweep a browser-style text selection over the line the VO is
   reading. ScreenStage frames a recording; WebTour additionally FILMS inside
   one.

   HONESTY CONTRACT (deliberate policy difference from ScreenStage:40-43):
     · Camera pan/zoom INTO the tape is ALLOWED — it is framing for
       readability, the same crop + slow pan/drift-zoom over real UI captures
       the hit-corpus endorses (MOTION-PIPELINE.md:373). The pixels shown are
       always the tape's own pixels, only magnified.
     · NEVER retime the tape — no playbackRate, ever. Tape seconds are wall
       seconds.
     · NEVER alter, relabel or fake the vendor's pixels, and never crop so as
       to mislead about what the page says.
     · Selection sweeps are an ADDITIVE translucent overlay, exactly like a
       real browser selection: the fill sits over the glyphs at low alpha,
       the glyphs stay legible, the tape pixels underneath are untouched.
     · The provenance strip (MONO, "REAL SCREEN RECORDING · <host>") is ON by
       default; pass label:"" to remove it only when another beat carries the
       disclosure.

   TWO COORDINATE SYSTEMS — the math this component lives on:

     1. TAPE SPACE — the recording's own pixel grid, tourW x tourH (default
        1920x1080). The capture manifest normalizes everything to this frame:
        a camera center or selection corner (nx, ny) in 0..1 is tape pixel
        (nx*tourW, ny*tourH). tourW/tourH MUST match the tape's true aspect —
        the video is drawn object-fit:fill into a wrapper laid out at exactly
        tourW x tourH, so a wrong aspect here shears the picture AND every
        rect with it.

     2. CARD SPACE — the glass card's inner viewport (viewW x viewH px) on
        the 1080x1920 design box, i.e. the card minus its browser bar.

     The camera maps tape -> card with one transform:

        s  = zoom * viewW / tourW        zoom 1 = fit-width: the tape spans
                                         the viewport edge-to-edge
        tx = viewW/2 - s * cx * tourW    pan: the chosen normalized tape
        ty = viewH/2 - s * cy * tourH    point lands at the viewport center

     applied as `translate(tx,ty) scale(s)` with transform-origin 0 0 (CSS
     composes right-to-left, so a tape point p renders at s*p + (tx,ty)).
     tx/ty are clamped so a tape edge never enters the viewport — the render-
     time version of the manifest's "cap zoom so the box never clips" rule.
     If zoom < fit (scaled tape smaller than the viewport on an axis) the
     tape is centered on that axis instead.

     THE GLUE: the <OffthreadVideo> AND the selection highlights are children
     of that ONE transformed wrapper, each positioned in raw tape pixels. One
     transform moves both identically, so highlights are glued to page pixels
     by construction — when the camera punches, they travel with the page.
     There is no second mapping to drift out of register.

     Selection rects come from Range.getClientRects() over the LIVE page, so
     they are viewport-relative at one scroll position — valid only while the
     tape sits at the scrollTop they were captured at. `scrollTop` is carried
     as authoring metadata (the component cannot see inside the pixels); the
     author schedules `at` inside that window, and the highlight auto-releases
     after its hold instead of lingering over content that may scroll away.
   ========================================================================== */

type WebTourCameraKey = {
  at: number; // seconds (component clock) the punch BEGINS
  dur?: number; // travel time, default 0.8; settle bezier
  center: [number, number]; // normalized tape point that lands at viewport center
  zoom: number; // 1 = fit-width
  hold?: number; // seconds the pose holds exactly before idle drift resumes (default 0.9)
};

type WebTourSelection = {
  at: number; // seconds (component clock) the sweep begins
  dur?: number; // total sweep travel time, default 0.35s per line
  rects: Array<[number, number, number, number]>; // per-LINE [x0,y0,x1,y1], normalized to the tape frame
  scrollTop?: number; // capture metadata only — the page scrollTop these rects are valid at
  hold?: number; // seconds the finished selection stays before releasing (default 1.6)
  color?: string; // hex tint; default browser-white rgba(255,255,255,0.28)
  sweep?: "ltr" | "instant"; // caret-led left-to-right per line, or appear-at-once
};

export type WebTourProps = {
  src: string; // tape path — staticFile() unless it is an http(s) URL
  from?: number; // seconds INTO THE TAPE (tape clock) to start playing
  url?: string; // the page's address — shown in the chrome bar + provenance host
  tourW?: number; // tape native size — the tape-space grid (default 1920x1080)
  tourH?: number;
  /* the glass card on the 1080x1920 design box. h is the FULL card box
     (browser bar included). Defaults: w=1016 centered, h grown from the tape
     aspect (capped to the safe band), vertically centered in the safe band. */
  card?: { x?: number; y?: number; w?: number; h?: number; radius?: number };
  camera?: WebTourCameraKey[]; // punches, sorted by `at`, non-overlapping; between them: RecFull drift-zoom 1.0->1.035
  selections?: WebTourSelection[];
  chrome?: "bar" | "none"; // minimal dark browser top-bar with the url (default "bar")
  label?: string; // provenance strip; default "REAL SCREEN RECORDING · <host>"; "" hides it
  start?: number; // seconds before the component clock begins
  /* Host PIP — a HeyGen clip cut from THIS beat's own VO slice, so the lipsync
     matches the words being spoken over the tour. build_ep_v2 generates it and
     swaps the real path in when the episode spec sets `host: true` on the beat
     (build_ep_v2.py:3367, same contract as ScreenStage). */
  host?: string;
  hostSize?: number; // pip WIDTH in px (16:9 card), default 360
  hostFrom?: number; // seconds into the host clip
  accent?: string;
  ink?: string;
  width?: number;
  height?: number;
  transparent?: boolean; // drop the ground so the stage floats over the comp
};

const SETTLE = Easing.bezier(0.2, 0.9, 0.25, 1); // Plate 06 settle
const BAR_H = 64; // browser chrome bar height
const DRIFT_PX = 12; // ScreenStage parallax layer travel
const PER_LINE = 0.35; // default selection sweep time per line
const DRIFT_MAX = 1.035; // RecFull idle drift-zoom ceiling (Short.tsx:1154)
const LAST_IDLE = 4; // s — drift ramp length after the final punch
const MIN_IDLE = 0.6; // idle windows shorter than this skip drift (a 3.5% zoom
//                       crammed into a sub-0.6s gap reads as a pop, not a drift)

type Pose = { cx: number; cy: number; z: number };

/* Idle drift: the zoom multiplies up to DRIFT_MAX across the WHOLE idle window
   [idle0, idle1], reaching the ceiling exactly as the next punch begins — so a
   punch's from-zoom (pose.z * DRIFT_MAX) is continuous with the drift and the
   camera never pops between phases. */
const driftedZ = (z: number, t: number, idle0: number, idle1: number): number => {
  const span = idle1 - idle0;
  if (span < MIN_IDLE) return z;
  return z * (1 + (DRIFT_MAX - 1) * clamp((t - idle0) / span));
};

/* Piecewise camera: base pose (full fit-width) -> settle-eased travel to each
   key over [at, at+dur] -> exact hold -> idle drift-zoom until the next key.
   Continuous at every boundary by construction (see driftedZ). */
const cameraAt = (t: number, keys: WebTourCameraKey[]): Pose => {
  let cx = 0.5;
  let cy = 0.5;
  let z = 1; // settled pose of the previous segment
  let settleEnd = 0;
  let hold = 0; // base pose has no hold — drift may start at t=0 (never static)
  for (const k of keys) {
    const d = Math.max(0.15, k.dur ?? 0.8);
    const idle0 = settleEnd + hold;
    if (t < k.at) return { cx, cy, z: driftedZ(z, t, idle0, k.at) };
    const zFrom = driftedZ(z, k.at, idle0, k.at); // drift attained as the punch begins
    if (t < k.at + d) {
      const e = SETTLE(clamp((t - k.at) / d));
      return {
        cx: cx + (k.center[0] - cx) * e,
        cy: cy + (k.center[1] - cy) * e,
        z: zFrom + (k.zoom - zFrom) * e,
      };
    }
    cx = k.center[0];
    cy = k.center[1];
    z = k.zoom;
    settleEnd = k.at + d;
    hold = k.hold ?? 0.9;
  }
  const idle0 = settleEnd + hold;
  return { cx, cy, z: driftedZ(z, t, idle0, idle0 + LAST_IDLE) };
};

/** hostname of a URL without the URL constructor (never throws). */
const hostOf = (u?: string): string | undefined => {
  if (!u) return undefined;
  const m = u.match(/^[a-z][a-z0-9+.-]*:\/\/([^/?#]+)/i) ?? u.match(/^([^/?#]+)/);
  return m ? m[1].replace(/^www\./, "") : undefined;
};

export const WebTour: React.FC<WebTourProps> = ({
  src,
  from = 0,
  url,
  tourW = 1920,
  tourH = 1080,
  card,
  camera,
  selections,
  chrome = "bar",
  label,
  start = 0,
  host,
  hostSize = 360,
  hostFrom = 0,
  accent = BRAND.mag,
  ink = BRAND.ink,
  width = 1080,
  height = 1920,
  transparent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = (frame - start * fps) / fps; // seconds since this component began
  const tc = Math.max(0, t); // animation clock never runs backwards past 0

  // ---- card geometry: live inside the safe band (kit SAFE, measured) ----
  const bandTop = SAFE.headerFloor;
  const bandH = SAFE.captionCeil - SAFE.headerFloor;
  const barH = chrome === "bar" ? BAR_H : 0;
  const cw = card?.w ?? 1016;
  const naturalH = barH + Math.round(cw * (tourH / tourW)); // card grown to the tape aspect
  const ch = card?.h ?? Math.min(naturalH, bandH - 40); // 20px breathing top+bottom
  const cx0 = card?.x ?? (width - cw) / 2;
  const cy0 = card?.y ?? bandTop + (bandH - ch) / 2;
  const radius = card?.radius ?? 40;
  const viewW = cw; // tape viewport = card minus the browser bar
  const viewH = ch - barH;

  // ---- the camera transform (see header: tape space -> card space) ----
  const keys = [...(camera ?? [])].sort((a, b) => a.at - b.at);
  const cam = cameraAt(tc, keys);
  const s = (cam.z * viewW) / tourW; // zoom 1 = fit-width
  const sw = s * tourW;
  const sh = s * tourH;
  let tx = viewW / 2 - s * cam.cx * tourW;
  let ty = viewH / 2 - s * cam.cy * tourH;
  // never show past a tape edge; if there is slack on an axis, center it
  tx = sw <= viewW ? (viewW - sw) / 2 : clamp(tx, viewW - sw, 0);
  ty = sh <= viewH ? (viewH - sh) / 2 : clamp(ty, viewH - sh, 0);

  // ---- Plate 07 parallax: four flat layers at four speeds (ScreenStage) ----
  const pxc = Math.sin(tc * 0.38) * 1 + Math.sin(tc * 0.17 + 1) * 0.4;
  const pyc = Math.cos(tc * 0.31) * 0.9;
  const layer = (k: number) =>
    `translate3d(${pxc * DRIFT_PX * k}px, ${pyc * DRIFT_PX * 0.8 * k}px, 0)`;

  // sheen repeats on ScreenStage's 3.2s cycle so still evidence keeps breathing
  const sheenT = tc - 0.25;
  const sheenP = sheenT < 1.5 ? clamp(sheenT / 1.5) : ((sheenT - 1.5) % 3.2) / 3.2;

  const hostName = hostOf(url) ?? (src.startsWith("http") ? hostOf(src) : undefined);
  const labelText =
    label === ""
      ? undefined
      : label ?? (hostName ? `REAL SCREEN RECORDING · ${hostName}` : "REAL SCREEN RECORDING");
  const urlText = url ? url.replace(/^[a-z][a-z0-9+.-]*:\/\//i, "").replace(/\/$/, "") : undefined;

  /* startFrom is source frames shown AT MOUNT. The tape must read `from` when
     the component clock hits 0, i.e. from - start seconds at mount. With
     start > from the tape clamps to its head — author beats with start=0 and
     slice via <Sequence> instead. NO playbackRate anywhere (honesty). */
  const startFrom = Math.max(0, Math.round((from - start) * fps));

  return (
    <AbsoluteFill style={{ background: transparent ? undefined : ink, overflow: "hidden" }}>
      <Fonts />
      {/* one shared material across the whole cut (VJ: unify on aurora + glass) */}
      {!transparent && <AuroraBed t={tc} accent={accent} ink={ink} opacity={0.34} />}

      {/* accent bloom behind the card — deepest layer (0.2) */}
      {!transparent && (
        <div
          style={{
            position: "absolute",
            left: cx0 - cw * 0.18,
            top: cy0 - ch * 0.08,
            width: cw * 1.36,
            height: ch * 1.16,
            borderRadius: "50%",
            background: `radial-gradient(closest-side, ${rgba(accent, 0.26)}, transparent 70%)`,
            filter: "blur(60px)",
            transform: layer(0.2),
          }}
        />
      )}

      {/* shadow plane — layer 0.5, behind and below the card */}
      <div
        style={{
          position: "absolute",
          left: cx0,
          top: cy0 + 26,
          width: cw,
          height: ch,
          borderRadius: radius,
          background: rgba("#000000", 0.55),
          filter: "blur(38px)",
          transform: layer(0.5),
          opacity: 0.8,
        }}
      />

      {/* the card — layer 0.9 (front). OPAQUE background: OffthreadVideo can
          miss its very first frame after a startFrom seek, and a transparent
          card becomes a HOLE for one frame at every hard cut into a recording
          (ScreenStage:195-199, caught on _game at 16.03s). */}
      <div
        style={{
          position: "absolute",
          left: cx0,
          top: cy0,
          width: cw,
          height: ch,
          ...glassChrome(radius, 1.2),
          background: ink,
          transform: layer(0.9),
        }}
      >
        {/* minimal dark browser bar — the url is part of the provenance */}
        {chrome === "bar" && (
          <div
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              top: 0,
              height: BAR_H,
              background: `linear-gradient(180deg, ${rgba("#ffffff", 0.07)}, ${rgba(
                "#ffffff",
                0.03
              )})`,
              borderBottom: `1px solid ${rgba("#ffffff", 0.08)}`,
              display: "flex",
              alignItems: "center",
            }}
          >
            <div style={{ display: "flex", gap: 10, paddingLeft: 26 }}>
              {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => (
                <div
                  key={c}
                  style={{ width: 14, height: 14, borderRadius: 7, background: c, opacity: 0.8 }}
                />
              ))}
            </div>
            {urlText && (
              <div
                style={{
                  position: "absolute",
                  left: "50%",
                  transform: "translateX(-50%)",
                  maxWidth: cw - 260,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  fontFamily: MONO,
                  fontSize: 21,
                  letterSpacing: 0.5,
                  lineHeight: 1,
                  color: rgba(BRAND.paper, 0.66),
                  background: rgba("#ffffff", 0.07),
                  border: `1px solid ${rgba("#ffffff", 0.1)}`,
                  borderRadius: 999,
                  padding: "9px 26px",
                }}
              >
                {urlText}
              </div>
            )}
          </div>
        )}

        {/* the tape viewport — everything below is in TAPE SPACE under ONE
            transform (see header math). Opaque again for the same hole fix. */}
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: barH,
            bottom: 0,
            overflow: "hidden",
            background: ink,
          }}
        >
          <div
            style={{
              position: "absolute",
              left: 0,
              top: 0,
              width: tourW,
              height: tourH,
              transform: `translate(${tx}px, ${ty}px) scale(${s})`,
              transformOrigin: "0 0",
            }}
          >
            {/* THE EVIDENCE — untouched, unretimed pixels. object-fit:fill is
                deliberate: the wrapper IS the tape-space grid, so the video
                must fill it exactly (a tourW/tourH mismatch is an authoring
                error, not something to letterbox away). */}
            <OffthreadVideo
              src={src.startsWith("http") ? src : staticFile(src)}
              startFrom={startFrom}
              muted
              style={{ width: "100%", height: "100%", objectFit: "fill" }}
            />

            {/* browser-style selection sweeps — ADDITIVE overlay in tape px,
                glued to the page by the shared transform */}
            {selections?.map((sel, i) => {
              const rects = sel.rects ?? [];
              const n = rects.length;
              if (!n) return null;
              const instant = sel.sweep === "instant";
              const sweepDur = instant ? 0.08 : Math.max(0.12, sel.dur ?? PER_LINE * n);
              const holdDur = sel.hold ?? 1.6;
              const tEnd = sel.at + sweepDur + holdDur;
              const FADE = 0.15; // quick release — a rect must never outlive its scrollTop
              if (tc < sel.at || tc > tEnd + FADE) return null;
              const master = tc > tEnd ? 1 - (tc - tEnd) / FADE : 1;
              const per = sweepDur / n;
              const fill = sel.color ? rgba(sel.color, 0.3) : "rgba(255,255,255,0.28)";

              // caret-led: a glowing text cursor rides the leading edge,
              // hopping line to line like a real drag-select
              let caret: { x: number; y: number; h: number } | null = null;
              if (!instant && master === 1 && tc <= sel.at + sweepDur + 0.1) {
                const j = Math.min(n - 1, Math.floor((tc - sel.at) / per));
                const r = rects[j];
                const p = clamp((tc - (sel.at + j * per)) / per);
                caret = {
                  x: (r[0] + (r[2] - r[0]) * p) * tourW,
                  y: r[1] * tourH,
                  h: (r[3] - r[1]) * tourH,
                };
              }

              return (
                <React.Fragment key={i}>
                  {rects.map((r, j) => {
                    const x = r[0] * tourW;
                    const y = r[1] * tourH;
                    const w = (r[2] - r[0]) * tourW;
                    const h = (r[3] - r[1]) * tourH;
                    const p = instant
                      ? clamp((tc - sel.at) / 0.08)
                      : clamp((tc - (sel.at + j * per)) / per);
                    if (p <= 0) return null;
                    return (
                      <div
                        key={j}
                        style={{
                          position: "absolute",
                          left: x,
                          top: y,
                          width: instant ? w : w * p,
                          height: h,
                          background: fill,
                          borderRadius: 3,
                          opacity: instant ? p * master : master,
                        }}
                      />
                    );
                  })}
                  {caret && (
                    <div
                      style={{
                        position: "absolute",
                        left: caret.x - 1.5,
                        top: caret.y - caret.h * 0.08,
                        width: 3,
                        height: caret.h * 1.16,
                        background: "rgba(255,255,255,0.95)",
                        borderRadius: 2,
                        boxShadow: "0 0 14px rgba(255,255,255,0.8)",
                      }}
                    />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>

        {/* 3px caustic top edge (Plate 01) */}
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: 0,
            height: 3,
            background: `linear-gradient(90deg, ${rgba("#fff", 0)} 0%, ${rgba(
              "#fff",
              0.62
            )} 50%, ${rgba("#fff", 0)} 100%)`,
          }}
        />

        {/* repeating specular pass — genuinely-still evidence keeps breathing */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: `linear-gradient(100deg, transparent 36%, ${rgba(
              "#ffffff",
              0.13
            )} 50%, transparent 64%)`,
            transform: `translateX(${-130 + sheenP * 260}%)`,
            pointerEvents: "none",
          }}
        />
      </div>

      {/* host PIP — bottom-left, clear of the caption band (ScreenStage placement) */}
      {host && (
        <div
          style={{
            position: "absolute",
            left: 56,
            top: height - Math.round(hostSize * 0.5625) - 320,
            width: hostSize,
            height: Math.round(hostSize * 0.5625), // 16:9 — matches the wide avatar
            borderRadius: 24,
            overflow: "hidden",
            border: `2px solid ${rgba("#ffffff", 0.5)}`,
            boxShadow: `0 26px 60px -18px ${rgba("#000", 0.85)}`,
            transform: layer(0.9),
          }}
        >
          <OffthreadVideo
            src={host.startsWith("http") ? host : staticFile(host)}
            startFrom={Math.round(hostFrom * fps)}
            muted
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </div>
      )}

      {/* grain over everything (Plate 07) */}
      <svg style={{ position: "absolute", inset: 0, opacity: 0.12, mixBlendMode: "overlay" }}>
        <filter id="wt-grain">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" />
        </filter>
        <rect width="100%" height="100%" filter="url(#wt-grain)" />
      </svg>

      {/* provenance strip — says plainly that the pixels are real. Clamped to
          the header floor if an author pushes the card to the very top. */}
      {labelText && (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: Math.max(SAFE.headerFloor, cy0 - 58),
            textAlign: "center",
            fontFamily: MONO,
            fontSize: 24,
            letterSpacing: 6,
            color: rgba(BRAND.paper, 0.72),
            opacity: clamp(tc / 0.5),
          }}
        >
          {labelText}
        </div>
      )}
    </AbsoluteFill>
  );
};

/* Demo tour of the claude-code repo tape, TRUED against the real capture
   manifest public/tapes/webtour_demo.tour.json (2026-08-23 recording of
   github.com/anthropics/claude-code). The 25.4s tape is entered at from=3 so
   the 12s WebTourDemo window covers title punch → stars punch → README scroll
   → the real selection; every focus center/zoom and the selection rect +
   scrollTop are the manifest's own values (component `at` = manifest t − 3). */
export const webTourDemo: WebTourProps = {
  src: "tapes/webtour_demo.mp4",
  url: "https://github.com/anthropics/claude-code",
  tourW: 1920,
  tourH: 1080,
  from: 3,
  camera: [
    // manifest focus "repo-title" t=4.004 · box [.1266,.1264,.2172,.1583]
    { at: 1.0, dur: 0.7, center: [0.172, 0.142], zoom: 1.9, hold: 2.0 },
    // manifest focus "stars" t=7.537 · box [.9319,.1278,.9648,.1556]
    { at: 4.54, dur: 0.65, center: [0.948, 0.142], zoom: 2.2, hold: 1.9 },
    // pull back to full-fit while the tape scrolls 0→1012 (manifest 10.37–12.17)
    { at: 7.3, dur: 0.6, center: [0.5, 0.5], zoom: 1.0, hold: 1.2 },
    // punch to the README tagline before the sweep (rect center of the selection)
    { at: 9.3, dur: 0.6, center: [0.275, 0.29], zoom: 1.9, hold: 1.9 },
  ],
  selections: [
    // manifest selection t=13.081 "an agentic coding tool that lives in your
    // terminal" — real Range.getClientRects line, valid at scroll_top 1012
    // (the tape sits there from 12.17 to 15.80)
    {
      at: 10.08,
      rects: [[0.1396, 0.2772, 0.4096, 0.3022]],
      scrollTop: 1012,
      hold: 1.4,
      sweep: "ltr",
    },
  ],
};
