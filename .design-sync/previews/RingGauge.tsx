// The simple case: one measured number, one arc.
import React from "react";
import { MotionStage, RingGauge, ringGaugeDemo } from "remotion-studio";

/** The canonical reading, arc drawn and value settled. */
export const Canonical = () => (
  <MotionStage component={RingGauge} componentProps={ringGaugeDemo}
               autoPlay={false} initialFrame={80} />
);

/** Mid-draw — the arc sweeping is the whole point of using this over text. */
export const MidSweep = () => (
  <MotionStage component={RingGauge} componentProps={ringGaugeDemo}
               autoPlay={false} initialFrame={26} />
);

export const Playing = () => (
  <MotionStage component={RingGauge} componentProps={ringGaugeDemo}
               durationInSeconds={4} initialFrame={80} />
);
