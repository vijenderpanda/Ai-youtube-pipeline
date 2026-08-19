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
