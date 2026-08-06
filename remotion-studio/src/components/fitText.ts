/* Shared text-fitting math for locked premium components (Cover, StatBars).
   Rule (AI Unpacked Ep23, 2026-08-05): type must NEVER clip the frame, even on a
   lazy props payload — components autoshrink and auto-split instead of trusting
   the caller to size copy. */

/* Approximate advance width of a string set in Anton (condensed display face),
   in em units. Per-glyph weights measured against real renders; the 1.06 factor
   absorbs letter-spacing, the poster slant and the extrude shadow. */
export const emWidth = (text: string): number => {
  let w = 0;
  for (const ch of text.toUpperCase()) {
    if ("IJ1!.,:;'|() ".includes(ch)) w += 0.27;
    else if ("MW@%&".includes(ch)) w += 0.62;
    else w += 0.5;
  }
  return w * 1.06;
};

/* Largest font size <= base at which `text` fits inside maxW pixels.
   No lower floor — a guaranteed fit beats a pretty minimum that clips. */
export const fitFont = (text: string, base: number, maxW: number): number =>
  Math.min(base, Math.floor(maxW / Math.max(emWidth(text), 0.1)));

/* Split a single long hook line at the word break that best balances the two
   lines (minimise the longer line). Tie → longer TOP line, shorter punch line —
   the known-good "Poster Duotone" stack shape (title1 wide, title2 = the chip). */
export const splitHook = (s: string): [string, string] => {
  const t = s.trim().replace(/\s+/g, " ");
  const words = t.split(" ");
  if (words.length < 2) return [t, ""];
  let best: [string, string] = [t, ""];
  let bestScore = Infinity;
  for (let i = 1; i < words.length; i++) {
    const a = words.slice(0, i).join(" ");
    const b = words.slice(i).join(" ");
    const score = Math.max(emWidth(a), emWidth(b));
    if (score < bestScore - 1e-6 || (Math.abs(score - bestScore) <= 1e-6 && a.length > best[0].length)) {
      best = [a, b];
      bestScore = score;
    }
  }
  return best;
};
