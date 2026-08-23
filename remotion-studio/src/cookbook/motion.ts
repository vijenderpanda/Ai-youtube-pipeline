import { Easing, interpolate } from "remotion";

/* =============================================================================
   motion.ts — the movement vocabulary of the motion-graphics lane.

   WHY THIS FILE EXISTS. The reference study (docs/MOTION-PIPELINE.md) found that
   the clearest cheap-vs-premium tell is not palette or shape — it is MASS and
   OPTICS. Reference motion overshoots its target and settles (C3), deforms into
   a boundary instead of stopping (U5), blurs when it moves fast (N5), and idles
   when it "holds" (U1). Our motion tweened symmetrically at uniform weight, and
   that difference read instantly at feed size.

   The doctrine: archetypes may only move things THROUGH these primitives. A
   component that calls enter()/settle()/smearFrames()/idle() passes laws U1, U5
   and C3 BY CONSTRUCTION — the gate suite then merely confirms what the type
   system already made likely.

   Everything is a pure function of (t, params) — frame-deterministic, no state,
   no randomness that could differ across a distributed render.
   ========================================================================== */

export const OUT_E = Easing.bezier(0.16, 1, 0.3, 1);
export const IN_E = Easing.bezier(0.7, 0, 0.84, 0);
export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));

/* deterministic hash noise — shared convention with the cookbook components */
export const mhash = (i: number) => {
  const s = Math.sin(i * 127.1 + 311.7) * 43758.5453;
  return s - Math.floor(s);
};
const smooth = (a: number) => a * a * (3 - 2 * a);
export const vnoise1 = (u: number) => {
  const i = Math.floor(u), f = u - i;
  return mhash(i) * (1 - smooth(f)) + mhash(i + 1) * smooth(f);
};

/* ---- ENTER: arrival with mass --------------------------------------------
   Progress 0..1 that OVERSHOOTS its target by `over` (default 6%) and returns.
   C3's test is "≥3% past target on ≥50% of arrivals" — the default clears it.
   Use for position/scale of anything that lands. */
export const enter = (t: number, at: number, dur = 0.38, over = 0.06): number => {
  const p = clamp01((t - at) / dur);
  if (p <= 0) return 0;
  // two-phase: fast approach past 1, then settle back
  const approach = OUT_E(Math.min(p / 0.72, 1)) * (1 + over);
  const settle = p <= 0.72 ? 0 : smooth((p - 0.72) / 0.28) * over;
  return approach - settle;
};

/* ---- SETTLE: the landing tail alone --------------------------------------
   1 at rest; ripples briefly after `at`. Multiply into scale (1 + settle*amt)
   or rotation for the stamp-then-settle grammar smartwater uses. */
export const settle = (t: number, at: number, dur = 0.5): number => {
  const d = t - at;
  if (d < 0 || d > dur) return 0;
  return Math.exp(-d * 9) * Math.sin(d * 34);
};

/* ---- EXIT: acceleration INTO a boundary (U5's first half) -----------------
   Progress 0..1 that starts slow and leaves fast — a scene must never just
   stop. Pair with smearStretch for the deform. */
export const exit = (t: number, at: number, dur = 0.3): number =>
  IN_E(clamp01((t - at) / dur));

/* ---- SMEAR: the 2-4 frame deformation on fast travel ----------------------
   Returns {stretch, blurPx} from a velocity in px/s. Apply stretch along the
   travel axis (scaleX or scaleY) and blurPx as a CSS filter blur. N5's gate
   wants fast frames measurably softer than holds; this is what makes that
   true. Velocities under `calm` px/s produce nothing. */
export const smear = (velPxPerSec: number, calm = 700): { stretch: number; blurPx: number } => {
  const v = Math.max(0, Math.abs(velPxPerSec) - calm) / 2400;
  return { stretch: 1 + Math.min(v * 0.35, 0.22), blurPx: Math.min(v * 14, 9) };
};

/* finite-difference velocity of any scalar track, for feeding smear() */
export const velocity = (
  f: (tt: number) => number, t: number, dt = 1 / 30
): number => (f(t + dt) - f(t - dt)) / (2 * dt);

/* ---- IDLE: what a "hold" does instead of freezing (U1) --------------------
   A tiny compound drift, ±amp px, three incommensurate frequencies so it never
   visibly loops. Add to any object that must survive on screen unchanged for
   more than ~1s. This is the ONLY sanctioned always-on wobble — it must stay
   subtle enough that G1 sees life and a viewer sees stillness. */
export const idle = (t: number, seed = 0, amp = 2.2): { x: number; y: number; r: number } => ({
  x: (Math.sin(t * 0.9 + seed * 7.3) * 0.6 + Math.sin(t * 2.3 + seed) * 0.4) * amp,
  y: (Math.cos(t * 1.15 + seed * 3.1) * 0.6 + Math.sin(t * 1.9 + seed * 5.7) * 0.4) * amp,
  r: Math.sin(t * 0.7 + seed * 11.2) * 0.35,
});

/* ---- CAMERA DRIFT: the global handheld life (N5) --------------------------
   Perlin-ish drift for the whole frame: slow translate + slower scale breathe.
   Mounted once per film in the Canvas layer, never per component. */
export const cameraDrift = (t: number, amp = 7): { x: number; y: number; s: number } => ({
  x: (vnoise1(t * 0.21) - 0.5) * 2 * amp,
  y: (vnoise1(t * 0.17 + 40) - 0.5) * 2 * amp * 0.8,
  s: 1 + (vnoise1(t * 0.09 + 80) - 0.5) * 0.012,
});

/* ---- typeOn: character-count reveal for A2 (N2 wants a real typing event) */
export const typeOn = (t: number, at: number, chars: number, cps = 28): number => {
  if (t < at) return 0;
  return Math.min(chars, Math.floor((t - at) * cps));
};
