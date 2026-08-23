import React from "react";
import { staticFile } from "remotion";

/* =============================================================================
   COOKBOOK KIT — shared tokens + tiny utils for the visual-component cookbook.
   (docs/REMOTION-DESIGNER-VISION.md — the "graphical b-roll" library.)

   Every cookbook component is a self-contained, parameterized Remotion element
   that draws animated on-brand "screens" (fake app UIs, dataviz, invented UI/UX
   flexes) to fill the b-roll/visual section WITHOUT capturing a real app. This
   file is the only shared dependency: brand color tokens (mirrored from
   Short.tsx so a component gets brand defaults without importing the 1300-line
   composition), font stacks, a <Fonts/> loader, and rgba/clamp helpers.

   Contract every cookbook file follows — see docs/COOKBOOK.md:
     export type <Name>Props    // documented props contract (JSON-serialisable —
                                //   NO function props: build_ep_v2 feeds --props
                                //   as JSON, so use prefix/suffix/enums instead)
     export const <Name>        // React.FC, self-animating off useCurrentFrame,
                                //   draws at a 1080x1920 design box, brand default
     export const <name>Demo    // canonical demo payload (the QC harness props)
   ...then a <Composition id="<Name>Demo"> in Root.tsx for Studio + still QC.
   ========================================================================== */

/* brand tokens — verbatim from Short.tsx MAG/YELLOW/INK/ACCENT so the cookbook
   shares the Sol/AI-Unpacked identity by default (every component still takes an
   `accent` prop to retint per channel). */
export const BRAND = {
  mag: "#E0218A", // primary — Sol identity, hot accent
  yellow: "#FFD60A", // secondary — pills, highlights
  ink: "#0E0E14", // base fill
  cyan: "#22D3EE", // callout / info accent
  paper: "#F2F2F8", // near-white text
  mute: "#9A9AAE", // muted grey text
} as const;

/* font stacks. Body/UI text uses the system sans so headless Chromium never
   blocks on a web font; DISPLAY (Anton) + SERIF (Playfair) load via <Fonts/>. */
export const SANS =
  'ui-sans-serif, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';
export const MONO =
  'ui-monospace, "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace';
export const DISPLAY = 'Anton, "Arial Black", sans-serif';
export const SERIF = '"Playfair Display", Georgia, serif';

/** hex (#rgb or #rrggbb) → `rgba(r,g,b,a)`. */
export const rgba = (hex: string, a: number): string => {
  const h = hex.replace("#", "");
  const v = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
  const n = parseInt(v, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
};

/** clamp x into [lo,hi] (defaults 0..1). */
export const clamp = (x: number, lo = 0, hi = 1): number =>
  Math.max(lo, Math.min(hi, x));

/** the standard cookbook backdrop: brand radial glow over ink. Pass transparent
    to skip (overlay use inside a live composition). */
export const coverBg = (accent: string, ink: string): string =>
  `radial-gradient(120% 80% at 50% 0%, ${rgba(accent, 0.22)} 0%, ${rgba(
    accent,
    0.06
  )} 34%, ${rgba(ink, 0)} 62%),radial-gradient(90% 60% at 82% 100%, ${rgba(
    BRAND.cyan,
    0.1
  )} 0%, ${rgba(ink, 0)} 55%),linear-gradient(178deg, ${ink} 0%, #08080c 100%)`;

/** Load the repo display fonts once. Drop near the top of any cookbook tree. */
export const Fonts: React.FC = () => (
  <style>{`
    @font-face { font-family:'Anton'; src:url('${staticFile(
      "fonts/Anton.ttf"
    )}'); font-display:block; }
    @font-face { font-family:'Playfair Display'; font-style:italic; font-weight:400 900; src:url('${staticFile(
      "fonts/PlayfairDisplay-Italic.ttf"
    )}'); font-display:block; }
  `}</style>
);

/* =============================================================================
   AuroraBed — THE shared ground for every cookbook component.
   VJ 2026-08-19: "unify on aurora + glass". Components that sat on flat ink read
   cheap next to the glass ones, and a cut that changes material every beat reads
   incoherent. One bed, one language: drifting magenta / blue / purple / cyan
   blobs on ink. Drawn twice by glass components — once behind, once clipped and
   blurred inside the panel as the baked refraction sample.
   Pure function of `t` (seconds) so it stays frame-deterministic.
   ========================================================================== */
export const AuroraBed: React.FC<{
  t: number;
  accent?: string;
  ink?: string;
  opacity?: number;
}> = ({ t, accent = BRAND.mag, ink = BRAND.ink, opacity = 0.5 }) => {
  const blob = (
    xp: number,
    yp: number,
    size: number,
    color: string,
    phase: number
  ): React.CSSProperties => ({
    position: "absolute",
    left: `${xp + Math.sin(t * 0.32 + phase) * 3.5}%`,
    top: `${yp + Math.cos(t * 0.26 + phase) * 3}%`,
    width: size,
    height: size,
    marginLeft: -size / 2,
    marginTop: -size / 2,
    borderRadius: "50%",
    background: color,
    filter: "blur(96px)",   // wider + lighter (VJ: "too much aurora, lighten a lil")
    opacity,
  });
  return (
    <div style={{ position: "absolute", inset: 0, background: ink }}>
      <div style={blob(26, 28, 640, accent, 0)} />
      <div style={blob(78, 24, 540, "#2F6BFF", 1.3)} />
      <div style={blob(20, 76, 500, "#C43BFF", 2.1)} />
      <div style={blob(82, 80, 440, BRAND.cyan, 3.0)} />
    </div>
  );
};

/* =============================================================================
   GLASS — the shared material. Extracted from OutroGlass 2026-08-20 after
   LedgerFlow shipped rows as flat rgba fills and read visibly cheaper than the
   glass components beside it (VJ: "not up to the mark ... like spinner wheel
   and outro sting card").

   The recipe is five layers and the order matters:
     1. chrome     1px light border + a BIG soft drop + an INSET top highlight.
                   OutroGlass's own note: "the inset highlight is the trick, not
                   the blur." A panel with no inset edge reads as a grey box.
     2. refraction the AuroraBed drawn AGAIN inside the panel, offset by the
                   panel's own position so the bed lines up with the one behind,
                   blown up 6% and blurred. This is what makes glass look like it
                   is SAMPLING the world rather than sitting on it.
     3. frost      a LIGHT wash. Go dark here and the refraction dies.
     4. caustic    a 3px bright top edge, brightest at the centre.
     5. specular   one slow diagonal sweep.

   COST: layer 2 is a blurred full-bleed element. Fine for a handful of large
   panels, ruinous at 22 simultaneous rows. Use <GlassInner/> for hero surfaces
   and glassLite() for many-instance surfaces — glassLite keeps 1, 4 and a baked
   two-stop gradient, which carries most of the perceived depth for none of the
   fill cost.
   ========================================================================== */

/** Container chrome: border + drop + the inset edge highlights. */
export const glassChrome = (
  radius = 24,
  lift = 1
): React.CSSProperties => ({
  borderRadius: radius,
  overflow: "hidden",
  border: `1px solid ${rgba("#ffffff", 0.3)}`,
  boxShadow: `0 ${44 * lift}px ${104 * lift}px -${38 * lift}px ${rgba("#000", 0.72)}, inset 0 1px 0 ${rgba(
    "#ffffff",
    0.5
  )}, inset 0 -1px 0 ${rgba("#ffffff", 0.07)}`,
});

/** Cheap glass for many-instance surfaces (ledger rows, chips, ticks).
 *  No refraction sample — a baked gradient stands in for it. */
export const glassLite = (
  radius = 22,
  tint?: string,
  strength = 1
): React.CSSProperties => ({
  borderRadius: radius,
  border: `1px solid ${rgba("#ffffff", 0.16 * strength)}`,
  background: tint
    ? `linear-gradient(158deg, ${rgba(tint, 0.42 * strength)} 0%, ${rgba(
        tint,
        0.16 * strength
      )} 62%, ${rgba(tint, 0.28 * strength)} 100%)`
    : `linear-gradient(158deg, ${rgba("#ffffff", 0.13 * strength)} 0%, ${rgba(
        "#ffffff",
        0.04 * strength
      )} 58%, ${rgba("#ffffff", 0.08 * strength)} 100%)`,
  boxShadow: `0 18px 40px -22px ${rgba("#000", 0.75)}, inset 0 1px 0 ${rgba(
    "#ffffff",
    0.34 * strength
  )}, inset 0 -1px 0 ${rgba("#ffffff", 0.05)}`,
});

/** The inner layers of a real glass panel. Drop as the FIRST child of an
 *  element already carrying glassChrome(). `x/y/w/h` are the panel's rect in
 *  the design box — needed so the refraction sample aligns with the bed behind. */
export const GlassInner: React.FC<{
  t: number;
  x: number;
  y: number;
  w: number;
  h: number;
  accent?: string;
  ink?: string;
  /** 0..1 sweep position for the specular pass; omit for none. */
  sheen?: number;
  /** frost wash strength, 0..1. Higher = more opaque = less refraction. */
  frost?: number;
  stageW?: number;
  stageH?: number;
}> = ({
  t,
  x,
  y,
  w,
  h,
  accent = BRAND.mag,
  ink = BRAND.ink,
  sheen,
  frost = 1,
  stageW = 1080,
  stageH = 1920,
}) => (
  <>
    {/* 2 — baked refraction: the bed again, aligned, blown up and blurred */}
    <div
      style={{
        position: "absolute",
        left: -x * 1.06 - w * 0.03,
        top: -y * 1.06 - h * 0.03,
        width: stageW * 1.06,
        height: stageH * 1.06,
        filter: "blur(26px) saturate(200%) brightness(1.08)",
      }}
    >
      <AuroraBed t={t} accent={accent} ink={ink} opacity={0.38} />
    </div>
    {/* 3 — frost wash, deliberately light */}
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: `linear-gradient(160deg, ${rgba("#0a0b12", 0.34 * frost)} 0%, ${rgba(
          "#0a0b12",
          0.5 * frost
        )} 100%)`,
      }}
    />
    {/* 4 — caustic top edge: the detail that sells it */}
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        top: 0,
        height: 3,
        background: `linear-gradient(90deg, ${rgba("#fff", 0)} 0%, ${rgba(
          "#fff",
          0.7
        )} 50%, ${rgba("#fff", 0)} 100%)`,
      }}
    />
    {/* 5 — one specular pass */}
    {sheen == null ? null : (
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `linear-gradient(100deg, transparent 34%, ${rgba(
            "#ffffff",
            0.14
          )} 50%, transparent 66%)`,
          transform: `translateX(${-130 + sheen * 260}%)`,
        }}
      />
    )}
  </>
);

/* =============================================================================
   SAFE — the band a cookbook component may actually draw in.

   Measured against Short.tsx 2026-08-20, not guessed:
     GlobalHeader  renders "AI UNPACKED VJ" in Anton 46 at top:40, CENTRED, and
                   it is on for every episode (build_ep_v2 sets watermark:True).
                   Its glyphs bottom out around y=95.
     Caption       default sits at bottom:"12%" of 1920 with theme.cap.size 54,
                   so the karaoke band occupies roughly y=1600 upward.

   A component that ignores these does not fail in the Studio preview — it fails
   only once composited, which is the expensive place to find out. Fogline had
   this bug in its shipped design (runLabel at top:92, straight under the
   wordmark) and nobody hit it because the component had never been used.
   ========================================================================== */
export const SAFE = {
  /** nothing above this — the brand lockup owns the top. */
  headerFloor: 132,
  /** nothing below this — the karaoke caption owns the bottom. */
  captionCeil: 1580,
} as const;
