#!/usr/bin/env python3
"""
vo_breathe.py — splice real silence into a synthesized read, and keep the word
timings honest.

Why this exists. `docs`/`SANJI-STYLE-GUIDE.md` §5.5 measured the problem: a flat
read with no silence is the single loudest "this is marketing" signal, and it is
in the audio file, not the script. Loudness RANGE is the measurable symptom —
his masters sit at LRA 1.5–2.1 and ours was landing at 2.6 with **zero** inter-word
gaps over 0.60s. No filter can manufacture range; silence IS range.

ElevenLabs will not reliably honour punctuation as a pause at the style settings
this channel uses (tested 2026-09-02: adding full stops made the read 15% FASTER
and produced no gap over 0.28s). So we insert the pauses deterministically after
synthesis, and shift every downstream word timestamp by the same amount — which
matters because the SEAM beat map is anchored to those timestamps.

    python3 scripts/vo_breathe.py VO.wav --after "mine" 0.7 --after "line" 0.8

Rewrites VO.wav in place (keeping VO.raw.wav) and VO.words.json alongside it.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument(
        "--after",
        nargs=2,
        action="append",
        metavar=("WORD", "SECONDS"),
        required=True,
        help="insert SECONDS of silence after WORD; use WORD#N for the Nth occurrence "
             "(1-based). Targeting the right occurrence matters: a repeated word can put the "
             "pause inside the 4-8s retention cliff, which the hook gate forbids.",
    )
    ap.add_argument("--sr", type=int, default=44100)
    a = ap.parse_args()

    wav = Path(a.wav)
    words_p = wav.with_suffix("").with_suffix(".words.json") if wav.suffixes[-2:] else None
    words_p = wav.parent / (wav.stem + ".words.json")
    if not words_p.exists():
        sys.exit(f"no timings at {words_p}")
    words = json.load(open(words_p))

    # resolve each requested pause to a word index; first unused match wins, so a
    # repeated word can be targeted more than once in order
    used, plan = set(), []
    for w_txt, secs in a.after:
        secs = float(secs)
        want, _, nth = w_txt.partition("#")
        nth = int(nth) if nth else 1
        hit, seen_n = None, 0
        for i, w in enumerate(words):
            if w["w"].strip().upper().strip(".,\u2014-") != want.strip().upper():
                continue
            seen_n += 1
            if seen_n == nth and i not in used:
                hit = i
                break
        if hit is None:
            sys.exit(f"word not found in timings: {w_txt!r}")
        used.add(hit)
        plan.append((hit, secs))
    plan.sort()

    raw = wav.parent / (wav.stem + ".raw.wav")
    if not raw.exists():
        shutil.copy2(wav, raw)

    # cut the source at each insertion point, concatenating silence between parts
    parts, filt, n = [], [], 0
    prev_end = 0.0
    for idx, secs in plan:
        cut = words[idx]["end"]
        filt.append(f"[0:a]atrim=start={prev_end}:end={cut},asetpts=N/SR/TB[p{n}]")
        parts.append(f"[p{n}]")
        n += 1
        filt.append(f"anullsrc=r={a.sr}:cl=mono,atrim=duration={secs},asetpts=N/SR/TB[s{n}]")
        parts.append(f"[s{n}]")
        n += 1
        prev_end = cut
    filt.append(f"[0:a]atrim=start={prev_end},asetpts=N/SR/TB[p{n}]")
    parts.append(f"[p{n}]")

    graph = ";".join(filt) + ";" + "".join(parts) + f"concat=n={len(parts)}:v=0:a=1[out]"
    out = wav.parent / (wav.stem + ".breathed.wav")
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(raw), "-filter_complex", graph,
         "-map", "[out]", "-ar", str(a.sr), "-y", str(out)],
        capture_output=True, text=True,
    )
    if r.returncode:
        sys.exit(r.stderr[-1500:])
    shutil.move(str(out), str(wav))

    # shift every timestamp at or after each insertion point
    for idx, secs in plan:
        cut = words[idx]["end"]
        for w in words:
            if w["start"] >= cut - 1e-6:
                w["start"] += secs
            if w["end"] > cut - 1e-6 and w is not words[idx]:
                w["end"] += secs
    json.dump(words, open(words_p, "w"))

    gaps = [words[i + 1]["start"] - words[i]["end"] for i in range(len(words) - 1)]
    big = sum(1 for g in gaps if g > 0.60)
    print(f"ok  +{sum(s for _, s in plan):.1f}s silence in {len(plan)} places")
    print(f"ok  {len(words)} words, {words[-1]['end']:.2f}s, "
          f"{len(words)/words[-1]['end']:.2f} w/s, {big} gaps > 0.60s")


if __name__ == "__main__":
    main()
