import React from "react";
import { AbsoluteFill, useVideoConfig } from "remotion";
import { rgba } from "./kit";
import { enter, settle, clamp01, idle } from "./motion";
import { CLAY, BALOO, PLEX, ToyStage, SpriteLayer } from "./Claylight";
import { useFilmT } from "./filmclock";

/* =============================================================================
   ClayOutro — the outro sting designed in the film's own world.

   VJ's note, and it generalises: "as per the content theme outro gets
   designed." The previous card was gen_outro_glass — aurora bed, glass, the
   magenta system — which read as a different channel bolted onto the tail of
   a CLAYLIGHT film. This card is the same room the film happened in: espresso
   ground, lamplight, Baloo, one coral. And where the old card carried Sol's
   face, this lane is zero-human by decision — the CORAL BRICK sits in the
   avatar's place, because the carry element IS the channel mark here.

   Two phases, same contract the build's retime path expects:
     A  THE PROMPT — the give, on a clay chat-card, mono label + pause hint
     B  the question + comment + subscribe rows, tagline
   ========================================================================== */

const LIB = "assets/claylight/library";

export type ClayOutroProps = {
  question: string;          // lines split by "|"
  promptText?: string;
  promptLabel?: string;
  promptHint?: string;
  promptDur?: number;        // seconds phase A owns
  commentLine?: string;
  subscribeLine?: string;
  tagline?: string;
  accentWord?: string;       // the ONE coral word inside the question
  width?: number;
  height?: number;
};

export const ClayOutro: React.FC<ClayOutroProps> = ({
  question,
  promptText,
  promptLabel = "THE PROMPT",
  promptHint = "PAUSE TO COPY",
  promptDur = 2.8,
  commentLine = "Comment yours 👇",
  subscribeLine = "Subscribe · one AI trick, every day",
  tagline = "AI Unpacked",
  accentWord,
  width = 1080,
  height = 1920,
}) => {
  const t = useFilmT();
  const { fps } = useVideoConfig();
  const pDur = promptText ? promptDur : 0;
  const pOut = promptText ? clamp01((t - (pDur - 0.3)) / 0.3) : 1;
  const bt = t - pDur;                       // phase-B clock

  return (
    <AbsoluteFill style={{ width, height }}>
      <ToyStage poolY={900}>
        {/* the room's furniture — the jar survived the film, it survives here */}
        <SpriteLayer src={`${LIB}/jar.png`} x={952} y={1400} h={300} aspect={0.69}
                     seed={4} idleAmp={2} zIndex={4} />

        {/* ---- PHASE A: the give ---- */}
        {promptText && pOut < 1 ? (() => {
          const on = enter(t, 0.05, 0.4, 0.05);
          // words reveal fast, then hold — a reading surface, never a freeze
          const chars = Math.max(0, Math.floor((t - 0.25) * 46));
          const txt = promptText.slice(0, chars);
          return (
            <div style={{
              position: "absolute", left: 70, right: 70, top: 430,
              opacity: Math.min(1, on * 1.4) * (1 - pOut),
              transform: `translateY(${(1 - Math.min(on, 1)) * -40}px) scale(${(1 + (t * 0.004)).toFixed(4)})`,
            }}>
              <div style={{ fontFamily: PLEX, fontSize: 27, letterSpacing: 6,
                            color: rgba(CLAY.amber, 0.9), marginBottom: 20 }}>{promptLabel}</div>
              <div style={{
                background: rgba(CLAY.cream, 0.1),
                border: `2px solid ${rgba(CLAY.cream, 0.26)}`,
                borderRadius: 26, padding: "38px 42px",
                boxShadow: `0 44px 100px -44px ${rgba("#000", 0.85)}`,
              }}>
                <div style={{ fontFamily: BALOO, fontWeight: 600, fontSize: 43,
                              lineHeight: 1.42, color: CLAY.cream }}>
                  {txt}{chars < promptText.length ? <span style={{ opacity: Math.floor(t * 3) % 2 ? 1 : 0.15 }}>▍</span> : null}
                </div>
              </div>
              <div style={{ marginTop: 24, textAlign: "center", fontFamily: PLEX,
                            fontSize: 25, letterSpacing: 5,
                            color: rgba(CLAY.cream, 0.6),
                            opacity: clamp01((t - 1.3) / 0.4) }}>{promptHint}</div>
            </div>
          );
        })() : null}

        {/* ---- PHASE B: the ask ---- */}
        {bt > -0.2 ? (() => {
          const wob = idle(t, 3, 2);
          const qOn = enter(bt, 0.05, 0.45, 0.06);
          const rows = [
            { at: 0.55, text: commentLine, pill: true },
            { at: 0.85, text: subscribeLine, pill: false },
          ];
          return (
            <div style={{ position: "absolute", inset: 0, opacity: Math.min(1, (bt + 0.2) * 3) }}>
              {/* the coral brick where a face would be — the mark of this lane */}
              <SpriteLayer src={`${LIB}/brick_coral.png`} x={540} y={560} h={190}
                           aspect={1.207} enterAt={pDur + 0.1} seed={7} idleAmp={2.4} zIndex={8} />
              <div style={{
                position: "absolute", left: 80, right: 80, top: 640, textAlign: "center",
                opacity: Math.min(1, qOn * 1.3),
                transform: `translateY(${(1 - Math.min(qOn, 1)) * 40 + wob.y}px) scale(${(1 + settle(bt, 0.5, 0.5) * 0.03).toFixed(3)})`,
              }}>
                {question.split("|").map((ln, i) => (
                  <div key={i} style={{
                    fontFamily: BALOO, fontWeight: 800, fontSize: 118, lineHeight: 1.04,
                    textTransform: "uppercase" as const, color: CLAY.cream,
                    textShadow: `0 6px 40px ${rgba("#000", 0.7)}`,
                  }}>
                    {accentWord && ln.toUpperCase().includes(accentWord.toUpperCase())
                      ? ln.toUpperCase().split(accentWord.toUpperCase()).reduce<React.ReactNode[]>((acc, part, k, arr) => {
                          acc.push(<span key={`p${k}`}>{part}</span>);
                          if (k < arr.length - 1) acc.push(<span key={`a${k}`} style={{ color: CLAY.coral }}>{accentWord.toUpperCase()}</span>);
                          return acc;
                        }, [])
                      : ln}
                  </div>
                ))}
              </div>
              {rows.map((r, i) => {
                const on = enter(bt, r.at, 0.4, 0.06);
                if (on <= 0.001) return null;
                return (
                  <div key={i} style={{
                    position: "absolute", left: 0, right: 0, top: 1120 + i * 128,
                    display: "flex", justifyContent: "center",
                    opacity: Math.min(1, on * 1.4),
                    transform: `translateY(${(1 - Math.min(on, 1)) * 26}px)`,
                  }}>
                    <div style={{
                      fontFamily: BALOO, fontWeight: r.pill ? 800 : 600, fontSize: r.pill ? 52 : 40,
                      color: CLAY.cream,
                      background: r.pill ? CLAY.coral : rgba(CLAY.cream, 0.1),
                      border: r.pill ? undefined : `1.5px solid ${rgba(CLAY.cream, 0.24)}`,
                      borderRadius: 99, padding: r.pill ? "14px 44px" : "12px 38px",
                      boxShadow: `0 18px 50px -22px ${rgba("#000", 0.8)}`,
                    }}>{r.text}</div>
                  </div>
                );
              })}
              <div style={{
                position: "absolute", left: 0, right: 0, top: 1420, textAlign: "center",
                fontFamily: PLEX, fontSize: 24, letterSpacing: 6,
                color: rgba(CLAY.cream, 0.45),
                opacity: clamp01((bt - 1.1) / 0.4),
              }}>{tagline.toUpperCase()}</div>
            </div>
          );
        })() : null}
      </ToyStage>
    </AbsoluteFill>
  );
};

/* ---- canonical demo ------------------------------------------------------ */
export const clayOutroDemo: ClayOutroProps = {
  question: "WHAT WOULD|CLAUDE HAVE|FORGOTTEN?",
  accentWord: "FORGOTTEN?",
  promptText: "Before this chat gets long: summarize everything worth keeping as notes I can paste into a fresh chat.",
  promptDur: 2.8,
};
