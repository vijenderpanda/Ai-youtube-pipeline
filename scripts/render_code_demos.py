#!/usr/bin/env python3
"""Render the 6 CodeDemo b-roll clips for a command-list episode (Ep 11).

Reads channels/claude-tricks/assets/ep11/command_demos.json + the real
.claude/commands/<key>.md files, builds per-command Remotion props, and
renders each CodeDemo composition to broll_<key>.mp4. These feed the
pipCallout top-zones in build_ep_v2.py (pip:<key> beats).

Usage: python3 scripts/render_code_demos.py
"""
import json
import os
import subprocess
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
CH = os.path.join(REPO, "channels", "claude-tricks")
DATA = os.path.join(CH, "assets", "ep11", "command_demos.json")
CMD_DIR = os.path.join(REPO, ".claude", "commands")
OUT_DIR = os.path.join(CH, "assets", "ep11")
REMOTION = os.path.join(REPO, "remotion-studio")

EDITOR_WRAP = 40    # chars per editor line
EDITOR_MAX = 11     # lines shown in the editor pane


def editor_lines(md_path):
    """The .md file formatted for the editor pane: frontmatter + opening body,
    soft-wrapped, capped so the pane stays clean."""
    raw = open(md_path).read().splitlines()
    out = []
    for ln in raw:
        if ln == "---" or ln.strip() == "":
            out.append(ln)
            continue
        # wrap long lines with a 2-space continuation indent
        wrapped = textwrap.wrap(ln, EDITOR_WRAP, subsequent_indent="  ") or [ln]
        out.extend(wrapped)
        if len(out) >= EDITOR_MAX:
            break
    return out[:EDITOR_MAX]


def short_arg(arg):
    """Trim the terminal argument so the command line doesn't overflow."""
    return arg if len(arg) <= 52 else arg[:49].rstrip() + "..."


def main():
    data = json.load(open(DATA))
    cmds = data["commands"]
    rendered = []
    for c in cmds:
        key = c["key"]
        md = os.path.join(CMD_DIR, f"{key}.md")
        if not os.path.exists(md):
            print(f"!! missing {md} — skipping /{key}")
            continue
        props = {
            "commandKey": key,
            "fileLines": editor_lines(md),
            "termArg": short_arg(c["arg"]),
            "responseLines": c["response"],
            "typeStart": 1.0,
            "lineStagger": 0.45,
        }
        pf = os.path.join(OUT_DIR, f".props_broll_{key}.json")
        json.dump(props, open(pf, "w"), indent=1)
        out = os.path.join(OUT_DIR, f"broll_{key}.mp4")
        print(f">> rendering /{key} -> {os.path.relpath(out, REPO)}")
        r = subprocess.run(
            ["npx", "remotion", "render", "CodeDemo", out, f"--props={pf}"],
            cwd=REMOTION)
        if r.returncode != 0:
            print(f"!! render failed for /{key}")
            sys.exit(1)
        rendered.append(out)
    print(f"\n>> done — {len(rendered)} b-roll clips in {os.path.relpath(OUT_DIR, REPO)}")
    for r in rendered:
        print(f"   {os.path.relpath(r, REPO)}")


if __name__ == "__main__":
    main()
