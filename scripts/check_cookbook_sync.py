#!/usr/bin/env python3
"""Fail when the cookbook's three lists disagree.

A component has to exist in THREE places to be usable:
  1. remotion-studio/src/cookbook/registry.ts    metadata + pickCookbook ranking
  2. remotion-studio/src/cookbook/components.tsx the id -> component render map
  3. supabase/functions/factory-api/index.ts     COOKBOOK_CATALOG, the validator
                                                 AND what the designer can offer

Miss (3) and the component is invisible: it renders fine, ranks fine, and simply
cannot be chosen. That is how OutroGlass -- written specifically to replace the
flat PIL outro sting -- sat unusable while the outro it was built to fix kept
shipping. Miss (2) and a locked block renders a loud placeholder. Miss (1) and
pickCookbook never proposes it.

This has now drifted twice. Run it in CI or before touching the cookbook:
    python3 scripts/check_cookbook_sync.py
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REG = REPO / "remotion-studio/src/cookbook/registry.ts"
MAP = REPO / "remotion-studio/src/cookbook/components.tsx"
EDGE = REPO / "supabase/functions/factory-api/index.ts"


def main():
    reg = re.findall(r'\bid:\s*"([A-Za-z0-9_]+)",\s*demoId', REG.read_text())
    mp = re.findall(r'^import\s*\{\s*([A-Za-z0-9_]+)\s*\}\s*from\s*"\./', MAP.read_text(), re.M)
    edge_block = re.search(r"const COOKBOOK_CATALOG[^=]*=\s*\[(.*?)\n\];", EDGE.read_text(), re.S)
    edge = re.findall(r'\bid:\s*"([A-Za-z0-9_]+)"', edge_block.group(1)) if edge_block else []

    reg_s, map_s, edge_s = set(reg), set(mp), set(edge)
    problems = []
    for name, other in (("the render map (components.tsx)", map_s),
                        ("the edge catalog (COOKBOOK_CATALOG)", edge_s)):
        missing = sorted(reg_s - other)
        if missing:
            problems.append(f"in registry.ts but NOT in {name}: {', '.join(missing)}")
    orphan = sorted((map_s | edge_s) - reg_s)
    if orphan:
        problems.append(f"offered or renderable but NOT in registry.ts: {', '.join(orphan)}")

    # The CLOSED VOCABULARIES drift too, and more quietly. registry.ts owns
    # BeatKind and DataShape; the planner prompt and the build validator each
    # carry a hand-copied list. When registry gains a shape (it gained "ledger"
    # and "part-whole" within a day), the planner cannot emit it and the build
    # action REJECTS it as invalid -- a valid beat refused by a stale copy.
    #
    # These are parsed from the SPECIFIC list, not searched for anywhere in the
    # file: the first version of this check looked for the value anywhere in
    # index.ts and passed happily while the validator was broken, because the
    # same string also appears in a catalog entry.
    reg_txt = REG.read_text()

    def type_values(name):
        m = re.search(rf"export type {name} =(.*?);", reg_txt, re.S)
        return set(re.findall(r'\|\s*"([a-z0-9-]+)"', m.group(1))) if m else set()

    edge_txt = EDGE.read_text()
    worker_txt = (REPO / "scripts/factory_worker.py").read_text()

    def edge_set(const_name):
        m = re.search(rf"const {const_name} = new Set\(\[(.*?)\]\)", edge_txt, re.S)
        return set(re.findall(r'"([a-z0-9-]+)"', m.group(1))) if m else None

    # The prompt is built from ADJACENT Python string literals, so the option
    # list spans several source lines with quotes and newlines between them.
    # Reading only the first literal made this report eight valid shapes as
    # missing. Slice from the field to the NEXT field and collect everything.
    PROMPT_BOUNDS = {"needs": '"keywords"', "beat": '"shows"'}

    def planner_set(field):
        i = worker_txt.find(f'"{field}": ')
        if i < 0:
            return None
        j = worker_txt.find(PROMPT_BOUNDS[field], i)
        window = worker_txt[i:j if j > i else i + 900]
        return set(re.findall(r'"([a-z0-9-]+)"', window))

    for tname, edge_const, prompt_field in (("DataShape", "DATA_SHAPES", "needs"),
                                            ("BeatKind", "BEAT_KINDS", "beat")):
        want = type_values(tname)
        if not want:
            continue
        for got, label in ((edge_set(edge_const), f"the edge validator ({edge_const})"),
                           (planner_set(prompt_field), f"the planner prompt (\"{prompt_field}\")")):
            if got is None:
                problems.append(f"could not find {label} to check {tname} against")
                continue
            missing = sorted(want - got)
            if missing:
                problems.append(f"{tname} value(s) in registry.ts but missing from {label}: {', '.join(missing)}")

    print(f"registry {len(reg_s)} · render map {len(map_s)} · edge catalog {len(edge_s)}")
    if problems:
        print("\n✖ the cookbook's three lists disagree:\n")
        for p in problems:
            print("  " + p)
        print("\nA component missing from the edge catalog renders and ranks fine "
              "but cannot be chosen by anyone; a vocabulary value missing from the "
              "planner or the validator makes a legitimate beat unplannable.")
        sys.exit(1)
    print("✓ all three lists agree")


if __name__ == "__main__":
    main()
