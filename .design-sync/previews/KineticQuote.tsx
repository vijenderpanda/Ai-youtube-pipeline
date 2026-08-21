// Text-heavy on purpose: if Anton or Playfair failed to load, it shows HERE
// first — a button-only solo would have passed and invalidated the whole wave.
import React from "react";
import { MotionStage, KineticQuote, kineticQuoteDemo } from "remotion-studio";

/** The composition production beats are authored against. */
export const Canonical = () => (
  <MotionStage component={KineticQuote} componentProps={kineticQuoteDemo}
               autoPlay={false} initialFrame={70} />
);

/** The line fully landed — every word set, nothing still animating in. */
export const Resolved = () => (
  <MotionStage component={KineticQuote} componentProps={kineticQuoteDemo}
               autoPlay={false} initialFrame={110} />
);

/** Running — parked on a resolved frame so the still is representative
 *  and the card still animates in the design pane. */
export const Playing = () => (
  <MotionStage component={KineticQuote} componentProps={kineticQuoteDemo}
               durationInSeconds={5} initialFrame={70} />
);
