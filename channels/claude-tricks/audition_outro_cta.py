#!/usr/bin/env python3
"""Audition the SPOKEN outro CTA against an already-shipped mastered body,
without a full rebuild — the VJ-review piece for the 2026-08-13 subscriber-
conversion experiment (text-only card -> Sol speaks a series CTA + tease).

Honesty guarantee: this does NOT re-implement the mix. It calls the exact
pieces the ship path uses — outro_cta.prepare_cta (compose/synth/level) and
build_ep_v2.outro_fc (the concat filtergraph) — so what VJ approves here is
what finalize renders later. QC prints integrated LUFS vs the finalize gate
(-14.0 ±0.5).

  python3 channels/claude-tricks/audition_outro_cta.py \
      --body renders/ep32_v2.mp4 --card assets/ep11/outro_card.mp4 \
      --slug promise                     # auto-compose (calendar/fallback)
  python3 channels/claude-tricks/audition_outro_cta.py \
      --body renders/ep32_v2.mp4 --card assets/ep11/outro_card.mp4 \
      --slug tease --text "Tomorrow: the command that makes Claude remember \
your style — follow so it finds you."
"""
import argparse, os, sys

CH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CH)
from build_ep_v2 import ELEVEN_VOICE, STYLE, outro_fc, run, venc
from outro_cta import measure_lufs, prepare_cta, probe_dur

LUFS_TARGET, LUFS_TOL = -14.0, 0.5   # finalize_episode.py QC gate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--body", required=True, help="mastered body mp4 (rel to channel dir ok)")
    ap.add_argument("--card", default="assets/ep11/outro_card.mp4")
    ap.add_argument("--music", default="assets/music/bed_active.mp3")
    ap.add_argument("--text", help="verbatim CTA line; omit to auto-compose")
    ap.add_argument("--slug", default="audition",
                    help="variant name -> assets/outro_cta_<slug>/ + renders/outro_cta_<slug>.mp4")
    a = ap.parse_args()

    p = lambda x: x if os.path.isabs(x) else os.path.join(CH, x)
    body, card, music = p(a.body), p(a.card), p(a.music)
    for f in (body, card, music):
        assert os.path.exists(f), f"missing: {f}"
    A = os.path.join(CH, "assets", f"outro_cta_{a.slug}")
    os.makedirs(A, exist_ok=True)
    out = os.path.join(CH, "renders", f"outro_cta_{a.slug}.mp4")

    cfg = {"outro_cta": a.text or "auto", "title": ""}
    cta = prepare_cta(cfg, A, ELEVEN_VOICE, style=STYLE)

    # identical arithmetic to build_ep_v2's outro block (odur=0 template case)
    base = probe_dur(card)
    T = round(max(base, 0.45 + cta["dur_s"] + 0.8), 3)
    fst = round(max(T - 1.6, 0.3), 3)
    fc = outro_fc("", fst, ratio=T / base, gain_db=cta["gain_db"])
    run(["ffmpeg", "-y", "-i", body, "-i", card,
         "-stream_loop", "-1", "-i", music, "-i", cta["wav"],
         "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
         *venc("18", "veryfast"),
         "-c:a", "aac", "-b:a", "192k", "-shortest", out])

    lufs = measure_lufs(out)
    drift = None if lufs is None else lufs - LUFS_TARGET
    verdict = ("UNMEASURABLE" if lufs is None else
               "PASS" if abs(drift) <= LUFS_TOL else "FAIL")
    print(f">> AUDITION {out}")
    print(f">> outro {T}s (card {base}s retimed x{T / base:.2f}), line [{cta['note']}]: "
          f"{cta['text']!r}")
    print(f">> LUFS integrated: {'n/a' if lufs is None else f'{lufs:.2f}'} "
          f"vs gate {LUFS_TARGET}±{LUFS_TOL} -> {verdict}")
    return 0 if verdict == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
