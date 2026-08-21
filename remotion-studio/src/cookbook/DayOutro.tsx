import React from "react";
import { AbsoluteFill, useVideoConfig } from "remotion";
import { rgba } from "./kit";
import { clamp01, OUT_E, settle, idle } from "./motion";
import { useFilmT } from "./filmclock";

/* =============================================================================
   DayOutro — the outro sting in ep2's daylight world (per-content outro
   doctrine: the outro is designed in the film's own world). Warm daylight
   ground, the DARK question card as the value anchor, the coral bill lying
   settled, the STILL ₹0 chip carried over from the dock — same room the film
   happened in, one beat calmer.
   ========================================================================== */

const DAY = {
  ground: "#EFE7D8", ground2: "#F7F1E4", ink: "#2B241D", paper: "#F2E8D8",
  mute: "#8A7D6A", coral: "#E8603C", green: "#2E8B57", greenHot: "#4ADE80",
} as const;
const MONO = '"IBM Plex Mono", monospace';
const DISP = '"Fraunces", Georgia, serif';
const cardShadow = `0 6px 10px ${rgba("#000", 0.35)}, 0 36px 80px ${rgba("#000", 0.22)}`;

export type DayOutroProps = {
  question: string;           // lines split by "|"
  accentWord?: string;
  promptText?: string;
  promptDur?: number;
  commentLine?: string;
  subscribeLine?: string;
  width?: number; height?: number;
};

export const DayOutro: React.FC<DayOutroProps> = ({
  question, accentWord,
  promptText, promptDur = 2.6,
  commentLine = "Comment: tumhara suspect? 👇",
  subscribeLine = "Subscribe · one AI trick, every day",
  width = 1080, height = 1920,
}) => {
  const t = useFilmT();
  const pDur = promptText ? promptDur : 0;
  const pOut = promptText ? clamp01((t - (pDur - 0.28)) / 0.28) : 1;
  const bt = t - pDur;
  const wob = idle(t, 5, 2);

  return (
    <AbsoluteFill style={{ width, height }}>
      <AbsoluteFill style={{
        background: `radial-gradient(120% 85% at 50% 40%, ${DAY.ground2} 0%, ${DAY.ground} 60%, #CFC3AC 100%)`,
      }} />
      <style>{`@font-face { font-family: 'Fraunces'; src: url('/fonts/Fraunces.ttf'); font-weight: 300 900; }
               @font-face { font-family: 'IBM Plex Mono'; src: url('/fonts/IBMPlexMono-Medium.ttf'); font-weight: 500; }`}</style>

      {/* PHASE A: the give, typed on the dark console */}
      {promptText && pOut < 1 ? (() => {
        const on = OUT_E(clamp01((t - 0.05) / 0.4));
        const chars = Math.max(0, Math.floor((t - 0.25) * 46));
        return (
          <div style={{
            position: "absolute", left: 80, right: 80, top: 480,
            opacity: Math.min(1, on * 1.4) * (1 - pOut),
            transform: `translateY(${(1 - Math.min(on, 1)) * -36}px)`,
          }}>
            <div style={{ fontFamily: MONO, fontSize: 26, letterSpacing: 5,
                          color: DAY.green, marginBottom: 18 }}>THE DETECTIVE PROMPT</div>
            <div style={{
              background: `linear-gradient(180deg, ${rgba("#0F1512", 0.98)}, ${rgba("#0A0F0C", 0.98)})`,
              border: `2px solid ${rgba(DAY.greenHot, 0.45)}`,
              borderRadius: 24, padding: "34px 38px", boxShadow: cardShadow,
            }}>
              <div style={{ fontFamily: MONO, fontSize: 31, lineHeight: 1.6, color: DAY.greenHot }}>
                {promptText.slice(0, chars)}
                {chars < promptText.length ? <span style={{ opacity: Math.floor(t * 3) % 2 ? 1 : 0.15 }}>▍</span> : null}
              </div>
            </div>
            <div style={{ marginTop: 22, textAlign: "center", fontFamily: MONO, fontSize: 24,
                          letterSpacing: 5, color: DAY.mute,
                          opacity: clamp01((t - 1.2) / 0.4) }}>PAUSE TO COPY</div>
          </div>
        );
      })() : null}

      {/* PHASE B: the ask */}
      {bt > -0.2 ? (() => {
        const qOn = OUT_E(clamp01((bt - 0.05) / 0.45));
        return (
          <div style={{ position: "absolute", inset: 0, opacity: Math.min(1, (bt + 0.2) * 3) }}>
            {/* the coral bill, settled flat — the carry retired */}
            <div style={{
              position: "absolute", left: 540 - 70, top: 430 + wob.y, width: 140, height: 176,
              borderRadius: 12, transform: `rotate(-4deg)`,
              background: `linear-gradient(160deg, ${DAY.coral}, #C24E2E)`,
              boxShadow: cardShadow,
            }}>
              {[0, 1, 2].map((k) => (
                <div key={k} style={{ margin: "18px 14px 0", height: 8, borderRadius: 4,
                                      width: 84 - k * 18, background: rgba("#FFF", 0.5) }} />
              ))}
            </div>
            <div style={{
              position: "absolute", left: 80, right: 80, top: 680, textAlign: "center",
              background: `linear-gradient(180deg, ${rgba("#1E1915", 0.97)}, ${rgba("#131009", 0.97)})`,
              borderRadius: 30, padding: "50px 30px 44px", boxShadow: cardShadow,
              border: `1.5px solid ${rgba("#FFF6E8", 0.12)}`,
              opacity: Math.min(1, qOn * 1.3),
              transform: `translateY(${(1 - Math.min(qOn, 1)) * 40}px) scale(${(1 + settle(bt, 0.5, 0.5) * 0.03).toFixed(3)})`,
            }}>
              {question.split("|").map((ln, i) => (
                <div key={i} style={{
                  fontFamily: DISP, fontWeight: 800, fontSize: 108, lineHeight: 1.06,
                  textTransform: "uppercase" as const, color: DAY.paper,
                }}>
                  {accentWord && ln.toUpperCase().includes(accentWord.toUpperCase())
                    ? ln.toUpperCase().split(accentWord.toUpperCase()).reduce<React.ReactNode[]>((acc, part, k, arr) => {
                        acc.push(<span key={`p${k}`}>{part}</span>);
                        if (k < arr.length - 1) acc.push(<span key={`a${k}`} style={{ color: DAY.coral }}>{accentWord.toUpperCase()}</span>);
                        return acc;
                      }, [])
                    : ln}
                </div>
              ))}
              <div style={{
                marginTop: 26, display: "inline-block",
                fontFamily: MONO, fontSize: 30, letterSpacing: 2, color: DAY.greenHot,
                border: `2px solid ${rgba(DAY.greenHot, 0.6)}`, borderRadius: 12,
                padding: "6px 22px",
              }}>STILL ₹0</div>
            </div>
            {[{ at: 0.55, text: commentLine, pill: true }, { at: 0.85, text: subscribeLine, pill: false }].map((r, i) => {
              const on = OUT_E(clamp01((bt - r.at) / 0.4));
              if (on <= 0.001) return null;
              return (
                <div key={i} style={{
                  position: "absolute", left: 0, right: 0, top: 1420 + i * 118,
                  display: "flex", justifyContent: "center",
                  opacity: Math.min(1, on * 1.4),
                  transform: `translateY(${(1 - Math.min(on, 1)) * 24}px)`,
                }}>
                  <div style={{
                    fontFamily: DISP, fontWeight: r.pill ? 800 : 600, fontSize: r.pill ? 46 : 34,
                    color: r.pill ? "#FFF6EC" : DAY.ink,
                    background: r.pill ? DAY.coral : rgba("#FFF", 0.55),
                    border: r.pill ? undefined : `1.5px solid ${rgba(DAY.ink, 0.25)}`,
                    borderRadius: 99, padding: r.pill ? "12px 40px" : "10px 34px",
                    boxShadow: cardShadow,
                  }}>{r.text}</div>
                </div>
              );
            })}
          </div>
        );
      })() : null}
    </AbsoluteFill>
  );
};

export const dayOutroDemo: DayOutroProps = {
  question: "KAUN KHA RAHA|TUMHARI|BIJLI?",
  accentWord: "BIJLI?",
  promptText: "> Mere last 3 bills: [Apr __, May __, Jun __]. Detective bano — seasonal jump nikaalo, culprit batao, maths ke saath.",
  promptDur: 2.6,
};
