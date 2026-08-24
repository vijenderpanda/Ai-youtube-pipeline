#!/usr/bin/env python3
"""pick_asset_pack — score the comp-dna library against a content brief.

Given what a planned piece of content IS (topic, mood, host budget, region, length,
lane, desired hook), return the best-fit ASSET PACK: a palette family + a reference
archetype to clone + the cookbook components to fill its beats — each with a
confidence score and a "world-fit" note (does the pack match the audience/region/
mood/lane around the plan, not just one axis).

    python scripts/pick_asset_pack.py --brief '{"lane":"news-hottake","mood":"urgent",
        "host":"full","region":"US","length":"short","topic":"a new Claude feature"}'
    # or --topic "..." and let it infer the rest

Confidence = weighted tag match × evidence weight (real views/day + like-rate back the
reference), so a pack backed by a proven short scores higher than a plausible-but-unproven one.
"""
import argparse, json, re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CD = REPO / "research/comp-dna"

# axis weights — how much each dimension matters for "the whole world around the content"
W = {"lane":3.0, "mood":2.0, "host":2.0, "region":1.5, "palette":1.5, "length":1.0, "archetype":1.0, "hook":1.0}

# topic keyword -> tag hints (infers the brief when only a topic is given)
KW = [
    (r"\b(news|launch|released?|just|update|breaking|scary|threat)\b", {"lane":"news-hottake","mood":"urgent","hook":"claim-title-card"}),
    (r"\b(framework|decision|mindset|principle|law|habit)\b", {"lane":"framework","mood":"authoritative","hook":"wordless-icon"}),
    (r"\b(build|built|app|one prompt|made|created)\b", {"lane":"product-demo","mood":"playful","hook":"logo-motion"}),
    (r"\b(tip|trick|feature|how to|hack|dont know|secret)\b", {"lane":"tutorial","mood":"curious","hook":"curiosity-type"}),
    (r"\b(money|cost|earn|price|crore|lakh|\$|revenue|save)\b", {"mood":"money","hook":"poster-claim"}),
    (r"\b(vs|versus|compare|better|worse)\b", {"lane":"news-hottake","hook":"yes-no-question"}),
]

def infer(topic, brief):
    t = (topic or "").lower()
    for pat, hints in KW:
        if re.search(pat, t):
            for k,v in hints.items(): brief.setdefault(k,v)
    brief.setdefault("host","full"); brief.setdefault("region","US")
    brief.setdefault("length","short"); brief.setdefault("mood","curious")
    brief.setdefault("lane","ai-tools")
    return brief

def score(brief, tags):
    got=0.0; tot=0.0; hits=[]; miss=[]
    for ax,w in W.items():
        if ax not in brief: continue
        tot += w; want=brief[ax]; have=tags.get(ax)
        if have in ("any",None): got += w*0.5; continue   # component-neutral axis
        if have==want: got += w; hits.append(ax)
        elif ax=="palette" and want in ("cream","paperYellow") and have in ("cream","paperYellow"): got += w*0.6
        elif ax=="mood" and want in ("urgent","money") and have in ("urgent","money"): got += w*0.6; hits.append(ax+"~")
        else: miss.append(f"{ax}:{have}≠{want}")
    return (got/tot if tot else 0), hits, miss

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", help="JSON brief")
    ap.add_argument("--topic", help="free-text topic (infers the rest)")
    ap.add_argument("--top", type=int, default=3)
    a = ap.parse_args()
    brief = json.loads(a.brief) if a.brief else {}
    if a.topic: brief["topic"]=a.topic
    brief = infer(brief.get("topic"), brief)

    data = json.loads((CD/"SCORING.json").read_text())
    refs = [x for x in data["assets"] if x["kind"]=="reference"]
    comps = [x for x in data["assets"] if x["kind"]=="component"]

    # score references (the archetype+palette to clone)
    ranked=[]
    for r in refs:
        fit,hits,miss = score(brief, r["tags"])
        conf = round(0.7*fit + 0.3*r["evidence"], 3)   # blend tag-fit with real evidence
        ranked.append((conf,fit,r,hits,miss))
    ranked.sort(key=lambda x:-x[0])

    # component pack: pick comp-dna components whose beats cover hook/proof/payoff/cta,
    # preferring higher wow, matching the chosen palette tone (all support "any")
    beat_need = ["hook","context","stat","demo","process","punchline","cta"]
    chosen=[]; used=set()
    for need in beat_need:
        best=None
        for c in comps:
            if c["id"] in used: continue
            if need in c.get("beats",[]):
                if best is None or c["tags"]["wow"]>best["tags"]["wow"]: best=c
        if best: chosen.append((need,best)); used.add(best["id"])

    top = ranked[:a.top]
    print("BRIEF:", json.dumps(brief, ensure_ascii=False))
    print("\n=== Best-fit asset packs ===")
    for conf,fit,r,hits,miss in top:
        t=r["tags"]
        print(f"\n▶ {conf:.0%} confidence — clone {r['id']} ({r['creator']})")
        print(f"   palette={t['palette']}/{t['tone']}+{t['accent']}  archetype={t['archetype']}  host={t['host']}  hook={t['hook']}  lane={t['lane']}  region={t['region']}  mood={t['mood']}")
        print(f"   evidence={r['evidence']:.2f} ({r['perf']['views_per_day']:,} v/day, p{int(r['perf']['views_per_day_pct']*100)}, like {r['perf']['like_rate']:.1%})")
        print(f"   world-fit: matched [{', '.join(hits) or '—'}]" + (f"  gaps [{', '.join(miss)}]" if miss else ""))
        print(f"   spec: research/comp-dna/{r['clone']}")
    best = top[0][2]
    print(f"\n=== Component pack for the winning archetype (palette: {best['tags']['palette']}) ===")
    for need,c in chosen:
        print(f"   {need:9} → {c['id']} (wow {c['tags']['wow']}, needs {c['needs']})")
    print("\nApply: copy the clone spec, set theme to the palette above, swap props to your topic, render with scripts/render_clones.py")

if __name__ == "__main__":
    main()
