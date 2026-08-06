#!/usr/bin/env python3
"""Scaffold a new channel directory in the network.

Usage:
  python3 scripts/new_channel.py <key> "Display Name" [kids|general]
Example:
  python3 scripts/new_channel.py vehicles "Rev & Roll (wk)" kids
"""
import os, sys

def main():
    if len(sys.argv) < 2:
        sys.exit("usage: new_channel.py <key> \"Display Name\" [kids|general]")
    key = sys.argv[1]
    name = sys.argv[2] if len(sys.argv) > 2 else key
    aud = sys.argv[3] if len(sys.argv) > 3 else "kids"
    base = f"channels/{key}"
    for d in ["songs", "assets/character", "assets/scenes", "assets/thumbnail", "renders", "docs"]:
        os.makedirs(f"{base}/{d}", exist_ok=True)
    bb = f"{base}/BRAND-BIBLE.md"
    if not os.path.exists(bb):
        open(bb, "w").write(
            f"# Brand Bible — {name}\n\n> Working name (confirm handle + light trademark check). "
            f"Audience: **{aud}**.\n\n## Wedge / positioning\nTODO\n\n## Mascot\nTODO — strong silhouette, "
            f"simple shapes (AI-consistency friendly).\n\n## World · palette (hex) · typography\nTODO\n\n"
            f"## Song / motion style\nTODO\n\n## Locked recipe\n- Image model + seed: TODO\n- Style tokens "
            f"(lead with FLAT): TODO\n- Negative: TODO\n\n## QC gate additions\nTODO\n")
    bp = f"{base}/BUILD-PLAN.md"
    if not os.path.exists(bp):
        pipe = "A (kids music video)" if aud == "kids" else "B (avatar explainer)"
        mfk = "Made-for-Kids = YES" if aud == "kids" else "Made-for-Kids = NO (higher RPM)"
        open(bp, "w").write(
            f"# Build Plan — {name}\n\nPipeline **{pipe}**. {mfk}.\n"
            f"Uploader key: `{key}` → token `secrets/token_{key}.json` "
            f"(`python3 scripts/yt_upload.py --channel {key} --auth`).\n\n"
            f"## Content pillars\nTODO\n\n## Motion budget\nHybrid: 2-3 Motion 2.0 heroes + Ken Burns (~$1.35/video).\n\n"
            f"## SEO\nTODO\n\n## First 30 days\nTODO\n")
    print(f"scaffolded {base}  ({name}, {aud})")

if __name__ == "__main__":
    main()
