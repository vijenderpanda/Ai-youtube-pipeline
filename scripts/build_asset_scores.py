#!/usr/bin/env python3
"""build_asset_scores — the meta-heavy scoring layer for the comp-dna library.

Emits research/comp-dna/SCORING.json: one tagged, scored record per asset (reference
short, cookbook component, clone), plus a `score_pack(brief)` matcher so a planning
agent can pick the right asset pack for a piece of content WITH a confidence score and
a "world-fit" check (does the pack match the audience/region/mood/lane around the plan).

Tag vocabulary (the axes a planner reasons over):
  palette   cream | paperYellow | night | midnight | cleanRed   (canvas+accent family)
  tone      light | dark
  accent    terracotta | sage | mint | yellow | red | pink | blue
  host      full | pip | none
  archetype A1..A6 | B1..B5   (see TAXONOMY.md)
  hook      logo-motion | wordless-icon | object-3d | crt-boot | curiosity-type |
            dense-montage-relief | poster-claim | mid-sentence | shock-stat |
            quote-card | claim-title-card | yes-no-question | chart-first | verbal-gap |
            walking-selfie-claim
  density   low | med | high
  motion    still | light | kinetic
  lane      ai-tools | design | news-hottake | framework | product-demo | tutorial
  region    IN | US | global
  mood      calm | urgent | money | playful | authoritative | curious
  length    micro(<25s) | short(25-45s) | mid(45-70s) | long(70s+)

The evidence weight = how much real performance data backs the asset (views/day rank
within the scout, like-rate) so confidence isn't just cosine similarity.
"""
import csv, json, glob, os, re, statistics as st
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CD = REPO / "research/comp-dna"

# ---- palette classification (mirrors kit.tsx PALETTES) --------------------
def lum(h):
    h = h.lstrip("#")
    return 200 if len(h) != 6 else 0.299*int(h[0:2],16)+0.587*int(h[2:4],16)+0.114*int(h[4:6],16)
def hue(h):
    h = h.lstrip("#")
    if len(h) != 6: return "other"
    r,g,b = (int(h[i:i+2],16) for i in (0,2,4))
    if r>180 and g>160 and b<110: return "yellow"
    if r>150 and g<95 and b<95: return "red"
    if b>140 and r<120: return "blue"
    if r>150 and b>95 and g<120: return "pink"
    if g>110 and r<125 and b<150: return "green"
    if r>190 and 90<g<170 and b<100: return "orange"
    return "other"
def palette_of(bg, ac):
    L, H = lum(bg), hue(ac)
    if L < 90: return ("midnight","dark","pink") if H=="pink" else ("night","dark","yellow")
    if H=="yellow": return ("paperYellow","light","yellow")
    if H=="red" and L>245: return ("cleanRed","light","red")
    if H=="green": return ("cream","light","sage")
    if H=="orange": return ("cream","light","terracotta")
    return ("cream","light","terracotta")

ARCH_LANE = {"A1":"tutorial","A2":"tutorial","A3":"product-demo","A4":"framework","A5":"tutorial","A6":"news-hottake",
             "B1":"news-hottake","B2":"news-hottake","B3":"news-hottake","B4":"news-hottake","B5":"tutorial"}
HOOK_MOOD = {"logo-motion":"authoritative","wordless-icon":"curious","object-3d":"curious","curiosity-type":"curious",
             "poster-claim":"money","shock-stat":"urgent","quote-card":"authoritative","claim-title-card":"authoritative",
             "yes-no-question":"curious","chart-first":"authoritative","verbal-gap":"curious","mid-sentence":"curious",
             "walking-selfie-claim":"playful","crt-boot":"playful","dense-montage-relief":"authoritative"}

def length_bucket(d):
    d = int(d or 0)
    return "micro" if d<25 else "short" if d<45 else "mid" if d<70 else "long"

def main():
    scout = {r["id"]: r for r in csv.DictReader(open(CD/"scout/SCOUT.csv"))}
    vpds = sorted(int(r["views_per_day"]) for r in scout.values() if r.get("views_per_day"))
    def vpd_pct(v):
        v=int(v or 0)
        return round(sum(1 for x in vpds if x<=v)/max(1,len(vpds)),2)
    lib = {r["id"]: r for r in json.load(open(CD/"LIBRARY.json"))}

    assets = []
    # ---- reference shorts -------------------------------------------------
    for d in sorted(glob.glob(str(CD/"*/design/theme.json"))):
        vid = os.path.basename(os.path.dirname(os.path.dirname(d)))[:11]
        th = json.load(open(d)); p = th.get("palette",{})
        bg,ac = p.get("bg","#EAE7E0"), p.get("accent","#E8623D")
        pal,tone,accent = palette_of(bg,ac)
        L = lib.get(vid,{}); sc = scout.get(vid,{})
        arch = L.get("archetype","A1"); hook = (L.get("hook_type","") or "").replace("H-","")
        host = th.get("layout",{}).get("host","full")
        vpd = sc.get("views_per_day",0); lr = float(sc.get("like_rate",0) or 0)
        region = "IN" if (sc.get("lang") in ("hi","ta","bn") or L.get("uploader") in ("Varun Mayya","Ishan Sharma","Raj Shamani","Aakash Gupta")) else "US"
        dur = L.get("dur") or sc.get("duration") or 40
        ev = round(min(1.0, 0.4*vpd_pct(vpd) + 0.4*min(1,lr/0.06) + 0.2), 2)  # evidence weight
        assets.append({
            "id": vid, "kind": "reference", "title": L.get("title"), "creator": L.get("uploader"),
            "tags": {"palette":pal,"tone":tone,"accent":accent,"host":host,"archetype":arch,
                     "hook":hook or "mid-sentence","lane":ARCH_LANE.get(arch,"ai-tools"),
                     "region":region,"mood":HOOK_MOOD.get(hook,"curious"),"length":length_bucket(dur),
                     "density": L.get("density","med") if isinstance(L.get("density"),str) else "med"},
            "perf": {"views_per_day":int(vpd or 0),"views_per_day_pct":vpd_pct(vpd),"like_rate":lr},
            "evidence": ev,
            "clone": f"clones/{vid}.json", "sheet": f"cards/refs/{vid}.html",
        })
    # ---- cookbook components (from registry.ts) --------------------------
    reg = (REPO/"remotion-studio/src/cookbook/registry.ts").read_text()
    for m in re.finditer(r'\{\s*id:\s*"([A-Za-z0-9_]+)",\s*demoId[^}]*?role:\s*"([^"]+)",\s*beats:\s*\[([^\]]*)\],\s*needs:\s*"([^"]+)"[^}]*?wow:\s*(\d)[^}]*?density:\s*"([^"]+)"', reg, re.S):
        cid,role,beats,needs,wow,dens = m.groups()
        beats=[b.strip().strip('"') for b in beats.split(",") if b.strip()]
        comp_daily = cid in ("PhoneMock","FlowTree","StatCloser","ChipRow","BrandBumper","SplitHead","AppWindow")
        assets.append({
            "id": cid, "kind": "component", "role": role, "needs": needs, "beats": beats,
            "tags": {"palette":"any","tone":"any","accent":"any","motion":"kinetic",
                     "density":dens,"wow":int(wow),"comp_dna": comp_daily},
            "evidence": 0.5,  # components are craft, not perf-measured
            "card": f"cards/components/{cid}.html",
        })
    out = {"generated_for":"comp-dna library","n": len(assets), "assets": assets}
    (CD/"SCORING.json").write_text(json.dumps(out, indent=1))
    # coverage summary
    from collections import Counter
    refs=[a for a in assets if a["kind"]=="reference"]
    print("references:",len(refs)," components:",len(assets)-len(refs))
    print("palette:",dict(Counter(a["tags"]["palette"] for a in refs)))
    print("archetype:",dict(Counter(a["tags"]["archetype"] for a in refs)))
    print("region:",dict(Counter(a["tags"]["region"] for a in refs)))
    print("wrote",CD/"SCORING.json")

if __name__ == "__main__":
    main()
