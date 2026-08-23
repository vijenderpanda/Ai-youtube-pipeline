#!/usr/bin/env python3
"""Render the OutroGlass sting to an mp4 for build_ep_v2's `outro_src`.

Drop-in successor to gen_outro_card.py. That script drew a FLAT PIL still and
faked motion with a Ken-Burns push; this one renders the real Remotion component
(remotion-studio/src/cookbook/OutroGlass.tsx), so the sting carries the same
material and motion language as the rest of the cut — refractive glass over the
aurora bed, kinetic Anton question, hairline CTA rows, scripted-camera depth.

Same CLI shape as gen_outro_card.py so callers barely change:

  python3 channels/claude-tricks/gen_outro_glass.py \
      --out assets/ep_wheel/outro_card.mp4 \
      --q "What should I build|with one line next?" \
      --dur 4.2

`--dur` sets the rendered length; build_ep_v2 can still retime it when a spoken
outro CTA needs a specific hold.
"""
import argparse
import json
import os
import subprocess
import sys

CH = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(CH))
STUDIO = os.path.join(ROOT, "remotion-studio")
FPS = 30
# public/assets is a symlink to channels/claude-tricks/assets, so staticFile()
# resolves this path inside the Remotion bundle.
DEFAULT_AVATAR = "assets/character/host_library/outfit_11_sol_magenta/cropeed_center_final.jpeg"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="output mp4 (relative to the channel dir is fine)")
    ap.add_argument("--q", required=True, help="question, lines split by '|'")
    ap.add_argument("--eyebrow", default="BEFORE YOU GO")
    ap.add_argument("--comment-label", default="Drop it in the comments")
    ap.add_argument("--comment-value", default="↳")
    ap.add_argument("--subscribe-label", default="Subscribe")
    ap.add_argument("--subscribe-value", default="ONE / DAY")
    ap.add_argument("--tagline", default="one AI trick, every single day")
    ap.add_argument("--avatar", default=DEFAULT_AVATAR)
    ap.add_argument("--accent", default=None, help="override brand magenta")
    ap.add_argument("--prompt-text", default=None,
                    help="the REAL typed line — shown chunky before the CTA card (prompt reveal)")
    ap.add_argument("--prompt-label", default="THE PROMPT")
    ap.add_argument("--prompt-hint", default="pause to copy")
    ap.add_argument("--prompt-dur", type=float, default=1.5)
    ap.add_argument("--dur", type=float, default=4.2)
    ap.add_argument("--scale", default=None,
                    help="render multiple, e.g. 2 for 2160x3840. Defaults to "
                         "$FACTORY_REMOTION_SCALE so it matches the body.")
    a = ap.parse_args()

    out = a.out if os.path.isabs(a.out) else os.path.join(CH, a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)

    props = {
        "question": a.q,
        "eyebrow": a.eyebrow,
        "commentLabel": a.comment_label,
        "commentValue": a.comment_value,
        "subscribeLabel": a.subscribe_label,
        "subscribeValue": a.subscribe_value,
        "tagline": a.tagline,
        "avatar": a.avatar,
    }
    if a.accent:
        props["accent"] = a.accent
    if a.prompt_text:
        props.update({
            "promptText": a.prompt_text,
            "promptLabel": a.prompt_label,
            "promptHint": a.prompt_hint,
            "promptDur": a.prompt_dur,
        })

    frames = max(int(round(a.dur * FPS)), FPS)
    cmd = [
        "npx", "remotion", "render", "OutroGlassDemo", out,
        f"--props={json.dumps(props)}",
        f"--frames=0-{frames - 1}",
    ]
    # RENDER THE STING AT THE BODY'S SCALE. Without this the card comes out at the
    # composition's native 1080x1920 and outro_fc upscales it into a larger body
    # with ffmpeg's default bicubic — so the last 4-7 seconds of a 4K episode, the
    # part carrying the prompt and the subscribe ask, is a soft upscale of a sharp
    # source. _upi shipped exactly that.
    _scale = a.scale or os.environ.get("FACTORY_REMOTION_SCALE")
    if _scale and float(_scale) != 1:
        cmd.append(f"--scale={_scale}")
    print("+", " ".join(cmd[:4]), "--props=<json>", cmd[-1])
    r = subprocess.run(cmd, cwd=STUDIO)
    if r.returncode != 0:
        sys.exit(f"!! remotion render failed ({r.returncode})")
    print(">> outro sting:", out)


if __name__ == "__main__":
    main()
