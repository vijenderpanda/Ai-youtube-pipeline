#!/usr/bin/env python3
"""Voice-track router: the single entrypoint for VO generation. Routes by the
channel's `voice_track` (ElevenLabs paid, or CosyVoice 2 free on the RTX 3060
worker) so switching tracks needs no other pipeline change. See docs/VOICE-TRACKS.md.

  python scripts/vo_render.py --channel claude-tricks --text "..." --out vo.wav
  python scripts/vo_render.py --channel claude-tricks --text "..." --out vo.wav --track cosyvoice2
"""
import argparse
import os
import sys
import time

import requests

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

WORKER = "DESKTOP-DEIR7RS"

# Per-channel voice config for BOTH tracks — switch `track` with no other change.
VOICE_TRACKS = {
    "claude-tricks": {
        "track": "elevenlabs",  # default; app/template overrides via factory_channels.meta.voice_track
        "eleven_voice": "ZZ5OIPIzxVJswEhc0UXt",  # Hrithik / Sol (locked)
        "eleven_style": 0.4,
        "cv2_ref": "gpu-refs/sol_ref_energetic.wav",   # in the factory-renders bucket
        "cv2_ref_text": "Stop typing prompts like it's twenty twenty-three. "
                        "This one tweak makes any A I ten times smarter.",
    },
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


def render_elevenlabs(cfg, text, out, speed=1.0):
    from eleven_vo import synth, load_key
    synth(load_key(), cfg["eleven_voice"], text, out,
          speed=speed, style=cfg.get("eleven_style", 0.4))
    return out


def render_cosyvoice2(cfg, text, out, poll_s=8, timeout_s=600):
    """Dispatch a pinned CosyVoice 2 clone job to the worker, then download the wav."""
    s = _secrets()
    url, key = s.get("SUPABASE_URL"), s.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY missing in secrets/factory.env")
    hdr = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    ref_url = f"{url}/storage/v1/object/public/factory-renders/{cfg['cv2_ref']}"
    job = {
        "type": "shell_script", "target_worker": WORKER, "status": "queued",
        "title": "vo_render cosyvoice2", "prompt": "vo",
        "meta": {"script_path": "deploy/gpu/cv2_clone.ps1", "script_args": [
            "-RefUrl", ref_url, "-RefText", cfg["cv2_ref_text"], "-Text", text, "-Tag", "vo"]},
    }
    r = requests.post(f"{url}/rest/v1/factory_jobs", headers={**hdr, "Prefer": "return=representation"},
                      json=job, timeout=30)
    r.raise_for_status()
    jid = r.json()[0]["id"]
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(poll_s)
        q = requests.get(f"{url}/rest/v1/factory_jobs?id=eq.{jid}&select=status,result",
                         headers=hdr, timeout=30).json()[0]
        if q["status"] in ("done", "failed"):
            so = (q.get("result") or {}).get("script_output") or ""
            import re
            m = re.search(r"PUBLIC_URL=(\S+)", so)
            if q["status"] == "failed" or not m or not m.group(1):
                raise RuntimeError(f"cosyvoice2 job {q['status']}: {so[-400:]}")
            pub = m.group(1)
            with requests.get(pub, timeout=60, stream=True) as dl:
                dl.raise_for_status()
                with open(out, "wb") as f:
                    for chunk in dl.iter_content(8192):
                        f.write(chunk)
            return out
    raise RuntimeError("cosyvoice2 job timed out")


def render(channel, text, out, track=None, speed=1.0):
    cfg = VOICE_TRACKS.get(channel)
    if not cfg:
        raise SystemExit(f"no voice config for channel {channel!r} (add it to VOICE_TRACKS)")
    track = track or cfg.get("track", "elevenlabs")
    if track == "cosyvoice2":
        return render_cosyvoice2(cfg, text, out)
    if track == "elevenlabs":
        return render_elevenlabs(cfg, text, out, speed=speed)
    raise SystemExit(f"unknown track {track!r}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--track", choices=["elevenlabs", "cosyvoice2"], default=None,
                    help="override the channel's default voice_track")
    ap.add_argument("--speed", type=float, default=1.0)
    a = ap.parse_args()
    path = render(a.channel, a.text, a.out, track=a.track, speed=a.speed)
    print(f"VO_OK track={a.track or VOICE_TRACKS[a.channel].get('track')} -> {path}")


if __name__ == "__main__":
    main()
