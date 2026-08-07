#!/usr/bin/env python3
"""Pick the couple_library couple whose vibe/mood tags best match a song's mood.

The staged Aashiqana planner casts a song by MOOD, not by re-generating a couple
(BRAND-BIBLE §4, COUPLE-LIBRARY §5). This scans every
channels/aashiqana/couple_library/couple_*/couple.meta.json 'tags' block and ranks
by keyword overlap with --mood, returning the folder + face refs + shots dir.

Usage:
  python scripts/pick_couple.py --mood "situationship neon night desire"
  python scripts/pick_couple.py --mood "rain heartbreak longing" --json
  python scripts/pick_couple.py --list
"""
import argparse, json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBRARY = os.path.join(REPO, "channels", "aashiqana", "couple_library")


def _tokens(s):
    return set(re.findall(r"[a-z0-9]+", str(s).lower()))


def load_couples():
    out = []
    if not os.path.isdir(LIBRARY):
        return out
    for name in sorted(os.listdir(LIBRARY)):
        d = os.path.join(LIBRARY, name)
        meta_p = os.path.join(d, "couple.meta.json")
        if not (name.startswith("couple_") and os.path.isfile(meta_p)):
            continue
        try:
            meta = json.load(open(meta_p))
        except Exception:
            continue
        tags = meta.get("tags", {}) or {}
        bag = set()                     # flatten every tag value into a token bag
        for v in tags.values():
            for x in (v if isinstance(v, list) else [v]):
                bag |= _tokens(x)
        bag |= _tokens(meta.get("codename", ""))
        refs = meta.get("refs", {}) or {}
        out.append({
            "id": meta.get("id", name),
            "codename": meta.get("codename", name),
            "dir": d,
            "shots": os.path.join(d, "shots"),
            "refs": {k: (os.path.join(d, v) if v else None) for k, v in refs.items()},
            "best_for": tags.get("best_for", []),
            "vibe": tags.get("vibe", []),
            "_bag": bag,
        })
    return out


def rank(couples, mood):
    q = _tokens(mood)
    scored = [(len(q & c["_bag"]), c) for c in couples]
    scored.sort(key=lambda t: (-t[0], t[1]["id"]))   # deterministic tie-break by id
    return scored


def main():
    ap = argparse.ArgumentParser(description="pick an Aashiqana couple by mood tags")
    ap.add_argument("--mood", help="song mood + keywords, e.g. 'situationship neon night'")
    ap.add_argument("--json", action="store_true", help="emit the chosen couple as JSON")
    ap.add_argument("--list", action="store_true", help="list all couples + their best_for tags")
    a = ap.parse_args()

    couples = load_couples()
    if not couples:
        sys.exit(f"no couples under {LIBRARY}")

    if a.list:
        for c in couples:
            print(f"{c['id']:12} {c['codename']:13} best_for: {', '.join(c['best_for'])}")
        return
    if not a.mood:
        ap.error("--mood is required (or use --list)")

    scored = rank(couples, a.mood)
    top_score, top = scored[0]
    if top_score == 0:
        print(f"(no tag match for '{a.mood}' — defaulting to {top['codename']})", file=sys.stderr)
    chosen = {k: v for k, v in top.items() if k != "_bag"}

    if a.json:
        print(json.dumps(chosen, indent=2))
    else:
        print(f"{top['id']}  {top['codename']}  (match {top_score})")
        print(f"  dir:   {top['dir']}")
        print(f"  shots: {top['shots']}")
        for k, v in chosen["refs"].items():
            print(f"  ref {k:13} {v}")
        rus = ", ".join(f"{c['codename']}({s})" for s, c in scored[1:3])
        if rus:
            print(f"  runner-up: {rus}")


if __name__ == "__main__":
    main()
