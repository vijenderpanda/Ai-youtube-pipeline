#!/usr/bin/env python3
"""Image-track router: the single entrypoint for image generation. Routes by the
channel's `image_track` — `leonardo` (paid/cloud, existing flow) or `flux_local`
(free, FLUX.1-schnell on the RTX 3060 worker). Mirror of scripts/vo_render.py.
See docs/VOICE-TRACKS.md.

  python scripts/img_render.py --channel claude-tricks --prompt "..." --out img.png --track flux_local
"""
import argparse
import os
import re
import time

import requests

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKER = "DESKTOP-DEIR7RS"

IMAGE_TRACKS = {
    "_default": {"track": "leonardo"},  # per-channel override via factory_channels.meta.image_track
    "claude-tricks": {"track": "leonardo"},
}


def _secrets():
    path = os.path.join(REPO, "secrets", "factory.env")
    env = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def render_flux_local(prompt, out, seed=0, width=1024, height=1024, poll_s=8, timeout_s=600):
    """Dispatch a pinned FLUX-schnell job to the worker, then download the PNG."""
    s = _secrets()
    url, key = s.get("SUPABASE_URL"), s.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY missing in secrets/factory.env")
    hdr = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    args = ["-Prompt", prompt, "-Seed", str(seed), "-Width", str(width), "-Height", str(height), "-Tag", "img"]
    job = {"type": "shell_script", "target_worker": WORKER, "status": "queued",
           "title": "img_render flux", "prompt": "img",
           "meta": {"script_path": "deploy/gpu/flux_gen.ps1", "script_args": args}}
    r = requests.post(f"{url}/rest/v1/factory_jobs",
                      headers={**hdr, "Prefer": "return=representation"}, json=job, timeout=30)
    r.raise_for_status()
    jid = r.json()[0]["id"]
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(poll_s)
        q = requests.get(f"{url}/rest/v1/factory_jobs?id=eq.{jid}&select=status,result",
                         headers=hdr, timeout=30).json()[0]
        if q["status"] in ("done", "failed"):
            so = (q.get("result") or {}).get("script_output") or ""
            m = re.search(r"PUBLIC_URL=(\S+)", so)
            if q["status"] == "failed" or not m or not m.group(1):
                raise RuntimeError(f"flux job {q['status']}: {so[-400:]}")
            with requests.get(m.group(1), timeout=120, stream=True) as dl:
                dl.raise_for_status()
                with open(out, "wb") as f:
                    for chunk in dl.iter_content(8192):
                        f.write(chunk)
            return out
    raise RuntimeError("flux job timed out")


def render_image(channel, prompt, out, track=None, seed=0, width=1024, height=1024):
    cfg = IMAGE_TRACKS.get(channel, IMAGE_TRACKS["_default"])
    track = track or cfg.get("track", "leonardo")
    if track == "flux_local":
        return render_flux_local(prompt, out, seed=seed, width=width, height=height)
    if track == "leonardo":
        raise SystemExit("image_track=leonardo → use the existing Leonardo flow "
                         "(leo_chrome.py / generation MCP); this router handles flux_local")
    raise SystemExit(f"unknown image_track {track!r}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--track", choices=["leonardo", "flux_local"], default=None)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--width", type=int, default=1024)
    ap.add_argument("--height", type=int, default=1024)
    a = ap.parse_args()
    path = render_image(a.channel, a.prompt, a.out, track=a.track,
                        seed=a.seed, width=a.width, height=a.height)
    print(f"IMG_OK track={a.track or IMAGE_TRACKS.get(a.channel, IMAGE_TRACKS['_default'])['track']} -> {path}")


if __name__ == "__main__":
    main()
