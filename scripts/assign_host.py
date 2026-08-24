#!/usr/bin/env python3
"""assign_host — auto-place the host on a SIGNAL/CloneReel spec per the research-backed
cutaway grammar (research/comp-dna/HOST-PLACEMENT.md). No manual placement needed.

    python scripts/assign_host.py research/comp-dna/clones/signal_ep1.json [--in-place]

Rule: host="full" on spoken-card beats (SplitHead/KineticQuote/SerifCap); host="none" on
graphic-proof beats and standalone cards. Reproduces the cutaway grammar the top-5 by
views/day all use (host full on hook/turn/close, hard-cut to graphic on proof).
"""
import argparse, json, sys
from pathlib import Path

SPOKEN = {"SplitHead", "KineticQuote", "SerifCap"}   # host full-frame, text overlay
GRAPHIC = {"FlowTree", "AppWindow", "TermRun", "ChatApp", "StatCloser", "Odometer",
           "VsTable", "BentoGrid", "DiffReveal", "OrbitNodes", "RingGauge", "LineReveal",
           "PhoneMock", "SpinWheel", "ReactionMeter", "CommandPalette", "GlassPanel"}
CARD = {"BrandBumper"}   # standalone sting, no host

def assign(block):
    cid = block.get("id", "")
    beat = (block.get("beat") or "").lower()
    if cid in SPOKEN:
        return "full"
    if cid in CARD or cid in GRAPHIC:
        return "none"
    # fall back on beat role
    if any(k in beat for k in ("hook", "claim", "setup", "turn", "transition", "cta-spoken", "pivot")):
        return "full"
    return "none"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--in-place", action="store_true")
    a = ap.parse_args()
    d = json.loads(Path(a.spec).read_text())
    for b in d.get("blocks", []):
        b["host"] = assign(b)
    d.setdefault("hostSrc", "hosts/sol_center.jpg")
    d["hostGrammar"] = "cutaway"   # documented; CloneReel reads per-block host
    out = json.dumps(d, indent=1)
    if a.in_place:
        Path(a.spec).write_text(out)
        print(f"host track assigned → {a.spec}")
        for b in d["blocks"]:
            print(f"  {b['id']:12} beat={b.get('beat',''):18} host={b['host']}")
    else:
        print(out)

if __name__ == "__main__":
    main()
