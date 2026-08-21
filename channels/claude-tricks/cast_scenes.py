#!/usr/bin/env python3
"""cast_scenes.py — the FILM MANIFEST compiler (docs/MOTION-PIPELINE.md, stage 4).

The manifest is ONE artifact that is simultaneously the storyboard VJ approves,
the build input, and the spec every QC gate tests against. This compiler is the
gate between writing and building: it VALIDATES the story's grammar while it is
still cheap to fix, then emits the episode spec build_ep_v2 consumes
(episodes/<ep>.v2.json — the existing JSON fallback path, no code changes).

WHAT GETS REJECTED, AND WHY IT IS REJECTED HERE:
  - a VO line with no {subject, from, to}, or a vague direction ("graphics
    animate") — U2 says every phrase needs a visual twin; a line that cannot
    name its twin is an unfinished LINE, and the script is where it gets fixed.
  - a spoken number with no entry in manifest.numbers[].source — the honesty
    bar as a type check. Illustration numbers are declared, never smuggled.
  - a knee event outside the 4.0-8.0s window on the PLANNED clock — the
    measured worst second is 5-6s; an event scheduled at 10s is a script bug.
  - a payoff before min_frac of the planned runtime — U8.
  - a missing carry/plant declaration — U3 needs something to test.

The planned clock estimates each line at the measured ElevenLabs rate
(2.67 words/s + the 0.4s break). The BUILD re-resolves every "@beatN+x" from
the real synthesized clock, so passing here does not depend on the estimate
being perfect — it depends on the story being schedulable at all.

Usage:
  python3 channels/claude-tricks/cast_scenes.py films/forgets.manifest.json
  python3 channels/claude-tricks/cast_scenes.py films/forgets.manifest.json --emit
"""
import argparse
import json
import os
import re
import sys

CH = os.path.dirname(os.path.abspath(__file__))
WPS = 2.67          # measured ElevenLabs words/sec for the locked voice
BREAK = 0.4         # the inter-line <break>

VAGUE = re.compile(r"\b(animates?|graphics?|motion|moves?|transitions?)\b", re.I)
NUM_WORDS = re.compile(
    r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"twenty|thirty|forty|fifty|hundred|thousand|lakh|crore|percent|\d+)\b", re.I)
# words that read as numbers but are prose, not figures (U10 is about FIGURES)
NUM_PROSE_OK = {"one"}


def planned_clock(lines):
    """[line...] -> beat boundary times on the planned clock, [0, t1, ..., tN]."""
    t, bounds = 0.0, [0.0]
    for ln in lines:
        t += len(ln["vo"].split()) / WPS + BREAK
        bounds.append(round(t, 2))
    return bounds


def resolve(anchor, bounds):
    """'@beatN' / '@beatN+x' / '@beatN-x' -> planned seconds."""
    m = re.match(r"^@beat(\d+)([+-][\d.]+)?$", str(anchor))
    if not m:
        return float(anchor)
    n = min(int(m.group(1)), len(bounds) - 1)
    return bounds[n] + (float(m.group(2)) if m.group(2) else 0.0)


def validate(man):
    errs, warns = [], []
    lines = man.get("lines") or []
    if not lines:
        errs.append("no lines[]")
    bounds = planned_clock(lines)
    total = bounds[-1]

    # -- the mute table: every line names its visual twin -------------------
    for i, ln in enumerate(lines):
        for k in ("subject", "from", "to"):
            v = (ln.get(k) or "").strip()
            if not v:
                errs.append(f"line {i}: missing {k!r} — the VO phrase has no visual twin (U2)")
            elif VAGUE.search(v) and len(v.split()) < 4:
                errs.append(f"line {i}: {k}={v!r} is a vague direction — name the OBJECT and its STATE")

    # -- numbers: sourced, declared, or absent ------------------------------
    declared = set()
    for n in (man.get("numbers") or []):
        declared.add(str(n.get("value")).lower())
        # a number may be SPOKEN in words ("two lakh") while declared as digits;
        # the spoken field ties them so the honesty check matches what the VO says
        for tok in str(n.get("spoken", "")).lower().split():
            declared.add(tok)
    for i, ln in enumerate(lines):
        for tok in NUM_WORDS.findall(ln["vo"]):
            if tok.lower() in NUM_PROSE_OK:
                continue
            if tok.lower() not in declared:
                errs.append(f"line {i}: spoken number {tok!r} has no numbers[] entry with a source "
                            f"(real-sourced, mechanism-illustration, or absent — no fourth option)")
    for n in (man.get("numbers") or []):
        if not (n.get("source") or "").strip():
            errs.append(f"numbers[]: {n.get('value')!r} declared without a source")

    # -- carry + plant: U3 needs something to test --------------------------
    if not (man.get("carry") or "").strip():
        errs.append("no carry declaration (U3)")
    if man.get("plant") is None:
        errs.append("no plant declaration (U8 needs the incomplete object at 0s)")

    # -- the knee: schedulable inside the measured window -------------------
    knee = man.get("knee") or {}
    if not knee:
        errs.append("no knee event (U9)")
    else:
        kt = resolve(knee.get("anchor", "@beat0"), bounds)
        lo, hi = knee.get("window", [4.0, 8.0])
        if not (lo <= kt <= hi):
            errs.append(f"knee at {kt:.2f}s on the planned clock — outside [{lo},{hi}] (U9). "
                        f"Move the anchor or reorder the script; do not ship and hope.")

    # -- the payoff: withheld -----------------------------------------------
    pay = man.get("payoff") or {}
    if not pay:
        errs.append("no payoff declaration (U8)")
    else:
        pt = resolve(pay.get("anchor", "@beat0"), bounds)
        frac = pt / total if total else 0
        if frac < pay.get("min_frac", 0.75):
            errs.append(f"payoff at {pt:.2f}s = {frac:.0%} of the planned {total:.1f}s — "
                        f"before min_frac {pay.get('min_frac', 0.75):.0%} (U8)")

    # -- structure ----------------------------------------------------------
    beats = man.get("beats") or []
    if len(beats) != len(lines):
        errs.append(f"{len(beats)} beats vs {len(lines)} lines — must be 1:1")
    if not man.get("give", {}).get("prompt"):
        errs.append("no give.prompt — the artifact the viewer takes away (admission gate 5)")
    if man.get("honesty") not in ("real-capture", "reads-as-mock", "declared-illustration"):
        errs.append("honesty class must be declared (admission gate 6)")
    if len(lines) and total > 40:
        warns.append(f"planned runtime {total:.1f}s — over the ~34s target")

    return errs, warns, bounds


def emit(man, bounds):
    """manifest -> episodes/<ep>.v2.json (the build's existing JSON path)."""
    ep = man["ep"].lstrip("_")
    out = {
        "_note": f"COMPILED from films/{man['ep'].lstrip('_')}.manifest.json by cast_scenes.py "
                 f"— edit the MANIFEST, not this file.",
        "title": man["title_candidates"][0],
        "tags": man["tags"],
        "outro": True,
        "outro_dur": 0,
        "outro_src": man["outro"]["src"],
        "outro_cta": man["outro"]["cta"],
        "lines": [ln["vo"] for ln in man["lines"]],
        "hot_words": man["hot_words"],
        "beats": man["beats"],
        "spine": man["spine"],
        "film": man["film"],
        "cookbook": man["cookbook"],
        "desc_prompt": (man.get("packaging", {}).get("desc_hook", "") + "\n\n"
                        "The fix — paste this BEFORE your chat gets long:\n\n"
                        "\"" + man["give"]["prompt"] + "\"\n\n"
                        "Then open a fresh chat, paste the notes, and continue where you left off. "
                        "Works in ChatGPT, Claude, and Gemini.").strip(),
        "desc_cta": man.get("packaging", {}).get("desc_cta",
                    "What's the one thing Claude keeps forgetting on you? Tell me below."),
        "desc_hashtags": man.get("packaging", {}).get("desc_hashtags"),
        "steps": [],
    }
    path = os.path.join(CH, "episodes", f"{man['ep']}.v2.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--emit", action="store_true",
                    help="write episodes/<ep>.v2.json after a clean validate")
    a = ap.parse_args()
    mp = a.manifest if os.path.isabs(a.manifest) else os.path.join(CH, a.manifest)
    man = json.load(open(mp))
    errs, warns, bounds = validate(man)
    total = bounds[-1]
    print(f">> {man.get('ep')}: {len(man.get('lines') or [])} lines, "
          f"planned {total:.1f}s body, beats at {[round(b,1) for b in bounds]}")
    for w in warns:
        print(f"?? {w}")
    for e in errs:
        print(f"!! {e}")
    if errs:
        sys.exit(1)
    print(">> manifest CLEAN — every line has a visual twin, the knee and payoff are schedulable")
    if a.emit:
        p = emit(man, bounds)
        print(f">> emitted {p}")


if __name__ == "__main__":
    main()
