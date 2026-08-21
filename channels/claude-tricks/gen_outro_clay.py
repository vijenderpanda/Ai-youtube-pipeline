#!/usr/bin/env python3
"""Render the ClayOutro sting to an mp4 for build_ep_v2's `outro_src`.

Successor to gen_outro_glass.py FOR CLAYLIGHT FILMS: the outro is designed in
the film's own world (VJ 2026-08-21 — "as per the content theme outro gets
designed"), espresso/clay/Baloo/one-coral, zero-human, the coral brick where
the avatar disc used to be. Same CLI shape so callers barely change:

  python3 channels/claude-tricks/gen_outro_clay.py \
      --out assets/ep_forgets/outro_card.mp4 \
      --q "WHAT WOULD|CLAUDE HAVE|FORGOTTEN?" --accent-word "FORGOTTEN?" \
      --prompt-text "..." --dur 6.8
"""
import argparse, json, os, subprocess

CH = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(CH))
STUDIO = os.path.join(ROOT, "remotion-studio")
FPS = 30

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--q", required=True)
ap.add_argument("--accent-word", default=None)
ap.add_argument("--prompt-text", default=None)
ap.add_argument("--prompt-label", default="THE PROMPT")
ap.add_argument("--prompt-hint", default="PAUSE TO COPY")
ap.add_argument("--prompt-dur", type=float, default=2.8)
ap.add_argument("--comment-line", default="Comment yours 👇")
ap.add_argument("--subscribe-line", default="Subscribe · one AI trick, every day")
ap.add_argument("--dur", type=float, default=6.8)
ap.add_argument("--scale", type=float, default=1.0)
a = ap.parse_args()

props = {"question": a.q, "accentWord": a.accent_word,
         "promptText": a.prompt_text, "promptLabel": a.prompt_label,
         "promptHint": a.prompt_hint, "promptDur": a.prompt_dur,
         "commentLine": a.comment_line, "subscribeLine": a.subscribe_line}
props = {k: v for k, v in props.items() if v is not None}
pj = os.path.join(CH, ".outro_clay_props.json")
json.dump(props, open(pj, "w"))
out = a.out if os.path.isabs(a.out) else os.path.join(CH, a.out)
subprocess.run(["npx", "remotion", "render", "ClayOutroDemo", out,
                f"--props={pj}", f"--frames=0-{int(a.dur * FPS) - 1}", f"--scale={a.scale}",
                "--crf=17", "--log=error"], cwd=STUDIO, check=True)
os.remove(pj)
print(f">> clay outro: {out}")
