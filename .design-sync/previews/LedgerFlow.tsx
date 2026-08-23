// The compound case: a conserved row set moving through four phases. Props come
// straight from the component's own demo, which is the real _upi data.
import React from "react";
import { MotionStage, LedgerFlow, ledgerFlowDemo } from "remotion-studio";

/** Phase 1 — rows streaming past faster than they can be read. */
export const Rush = () => (
  <MotionStage component={LedgerFlow}
               componentProps={{ ...ledgerFlowDemo, phase: "rush" }}
               autoPlay={false} initialFrame={40} />
);

/** Phase 3 — the same rows re-laying into category lanes. */
export const Sort = () => (
  <MotionStage component={LedgerFlow}
               componentProps={{ ...ledgerFlowDemo, phase: "sort" }}
               autoPlay={false} initialFrame={60} />
);

/** Phase 4 — one lane outgrowing the rest. */
export const Grow = () => (
  <MotionStage component={LedgerFlow}
               componentProps={{ ...ledgerFlowDemo, phase: "grow" }}
               autoPlay={false} initialFrame={100} />
);

export const Playing = () => (
  <MotionStage component={LedgerFlow}
               componentProps={{ ...ledgerFlowDemo, phase: "sort" }}
               durationInSeconds={5} initialFrame={70} />
);
