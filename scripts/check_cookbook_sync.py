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

    print(f"registry {len(reg_s)} · render map {len(map_s)} · edge catalog {len(edge_s)}")
    if problems:
        print("\n✖ the cookbook's three lists disagree:\n")
        for p in problems:
            print("  " + p)
        print("\nA component missing from the edge catalog renders and ranks fine "
              "but cannot be chosen by anyone.")
        sys.exit(1)
    print("✓ all three lists agree")


if __name__ == "__main__":
    main()
