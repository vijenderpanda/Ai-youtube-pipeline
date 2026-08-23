import React, { createContext, useContext } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";

/* =============================================================================
   filmclock — ONE clock for a film that renders across many <Sequence>s.

   Every beat of a build_ep_v2 episode mounts inside its own <Sequence>, where
   useCurrentFrame() restarts at zero. A component that reads the frame raw
   therefore REPLAYS ITS OPENING on every cut — the draft build showed the
   film's first second at 5.25s, empty box and all, because chips, sprites and
   the camera each kept their own beat-local time while only the spine
   component knew the film time.

   The spine component computes film time once (its `start` prop) and provides
   it here; every Claylight primitive and the WorldCamera read useFilmT() and
   get film-absolute seconds whether they are mounted in a Sequence, in the
   studio demo composition, or on a bare page.
   ========================================================================== */

export const FilmT = createContext<number | null>(null);

export const useFilmT = (): number => {
  const ctx = useContext(FilmT);
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return ctx ?? frame / fps;
};
