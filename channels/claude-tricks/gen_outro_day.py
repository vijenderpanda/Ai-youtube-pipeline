#!/usr/bin/env python3
"""Render the DayOutro sting (ep2's daylight world) for build_ep_v2's outro_src.
Per-content outro doctrine — same CLI shape as gen_outro_clay.py."""
import argparse, json, os, subprocess
CH = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.join(os.path.dirname(os.path.dirname(CH)), "remotion-studio")
FPS = 30
ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--q", required=True)
ap.add_argument("--accent-word", default=None)
ap.add_argument("--prompt-text", default=None)
ap.add_argument("--prompt-dur", type=float, default=2.6)
ap.add_argument("--comment-line", default=None)
ap.add_argument("--dur", type=float, default=6.8)
ap.add_argument("--scale", type=float, default=1.0)
a = ap.parse_args()
props = {"question": a.q, "accentWord": a.accent_word, "promptText": a.prompt_text,
         "promptDur": a.prompt_dur, "commentLine": a.comment_line}
props = {k: v for k, v in props.items() if v is not None}
pj = os.path.join(CH, ".outro_day_props.json")
json.dump(props, open(pj, "w"))
out = a.out if os.path.isabs(a.out) else os.path.join(CH, a.out)
subprocess.run(["npx", "remotion", "render", "DayOutroDemo", out, f"--props={pj}",
                f"--frames=0-{int(a.dur * FPS) - 1}", f"--scale={a.scale}", "--crf=17",
                "--log=error"], cwd=STUDIO, check=True)
os.remove(pj)
print(f">> day outro: {out}")
