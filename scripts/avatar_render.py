#!/usr/bin/env python3
"""Avatar-track router: the single entrypoint for host talking-head generation.
Routes by the channel's `avatar_track`:

  * `echomimic_local` (FREE) — EchoMimic V1 on the RTX 3060 worker: whole-face
    diffusion driven by the audio, natural head/eye motion, no mouth-inpaint seam.
    ALWAYS dispatched to DESKTOP-DEIR7RS (pinned shell_script). On ANY failure it
    FALLS BACK to heygen, so production never breaks on a worker hiccup.
  * `heygen` (paid, cloud) — the existing talking-photo flow (scripts/heygen_avatar.py).

Mirror of scripts/vo_render.py + scripts/img_render.py. See docs/VOICE-TRACKS.md.

  python scripts/avatar_render.py --channel claude-tricks --audio vo.wav --out host.mp4
  python scripts/avatar_render.py --channel claude-tricks --audio vo.wav --out host.mp4 --track heygen
  python scripts/avatar_render.py --channel claude-tricks --audio vo.wav --image frame.png --out host.mp4
"""
import argparse
import os
import re
import sys
import time

import requests

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
WORKER = "DESKTOP-DEIR7RS"

# Per-channel avatar config for BOTH tracks — switch `track` with no other change.
AVATAR_TRACKS = {
    "_default": {"track": "heygen"},
    "claude-tricks": {
        "track": "echomimic_local",  # FREE default (VJ 2026-08-19); heygen = fallback
        # EchoMimic reference portrait already in the bucket (locked outfit-11 host):
        "host_image": "gpu-refs/sol_host_outfit11.jpg",
        # HeyGen fallback avatar — outfit-11 pip talking_photo_id:
        "heygen_photo_id": "dc9533a1e07944a1ad32e6dcb19b678f",
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


def _storage_put(url, key, dest, data, content_type):
    """Upload bytes to factory-renders/<dest> (upsert) → the public URL."""
    r = requests.put(
        f"{url}/storage/v1/object/factory-renders/{dest}",
        headers={"apikey": key, "Authorization": f"Bearer {key}",
                 "x-upsert": "true", "Content-Type": content_type},
        data=data, timeout=180)
    r.raise_for_status()
    return f"{url}/storage/v1/object/public/factory-renders/{dest}"


def render_echomimic_local(cfg, image, audio, out, poll_s=10, timeout_s=1500):
    """Upload the host image (if a local path) + the audio, dispatch a pinned
    EchoMimic job to the worker, poll to terminal, download the talking-head mp4."""
    s = _secrets()
    url, key = s.get("SUPABASE_URL"), s.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY missing in secrets/factory.env")

    # unique per-call token so parallel avatar jobs never clobber each other's inputs
    # (the worker runs shell_script 2-up).
    tok = f"{int(time.time())}_{os.getpid()}"

    # host image: a given local file is uploaded; a URL is passed through; else the
    # channel's stored host portrait.
    if image and image.startswith("http"):
        img_url = image
    elif image and os.path.exists(image):
        ext = "png" if image.lower().endswith(".png") else "jpg"
        ctype = "image/png" if ext == "png" else "image/jpeg"
        img_url = _storage_put(url, key, f"gpu-inputs/avatar_src_{tok}.{ext}",
                               open(image, "rb").read(), ctype)
    else:
        img_url = f"{url}/storage/v1/object/public/factory-renders/{cfg['host_image']}"

    if not audio or not os.path.exists(audio):
        raise RuntimeError(f"audio not found: {audio!r}")
    aud_url = _storage_put(url, key, f"gpu-inputs/avatar_audio_{tok}.wav",
                           open(audio, "rb").read(), "audio/wav")

    hdr = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    job = {"type": "shell_script", "target_worker": WORKER, "status": "queued",
           "title": "avatar_render echomimic", "prompt": "avatar",
           "meta": {"script_path": "deploy/gpu/echomimic_gen.ps1",
                    "script_args": ["-SrcUrl", img_url, "-AudioUrl", aud_url, "-Tag", "avatar"]}}
    r = requests.post(f"{url}/rest/v1/factory_jobs",
                      headers={**hdr, "Prefer": "return=representation"}, json=job, timeout=30)
    r.raise_for_status()
    jid = r.json()[0]["id"]
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(poll_s)
        q = requests.get(f"{url}/rest/v1/factory_jobs?id=eq.{jid}&select=status,result",
                         headers=hdr, timeout=30).json()[0]
        if q["status"] in ("done", "failed", "cancelled"):
            so = (q.get("result") or {}).get("script_output") or ""
            m = re.search(r"PUBLIC_URL=(\S+)", so)
            if q["status"] != "done" or not m or not m.group(1):
                raise RuntimeError(f"echomimic job {q['status']}: {so[-400:]}")
            with requests.get(m.group(1), timeout=180, stream=True) as dl:
                dl.raise_for_status()
                with open(out, "wb") as f:
                    for chunk in dl.iter_content(8192):
                        f.write(chunk)
            return out
    raise RuntimeError("echomimic job timed out")


def render_heygen(cfg, image, audio, out, aspect="9:16"):
    """Paid fallback: the existing HeyGen talking-photo flow. Uses the channel's
    configured outfit talking_photo_id (identity-stable; avoids burning a photo-avatar
    slot per render). `image` is ignored here — HeyGen identity comes from the id."""
    import heygen_avatar as hg
    tid = cfg.get("heygen_photo_id")
    if not tid:
        raise RuntimeError("no heygen_photo_id configured for fallback")
    if not audio or not os.path.exists(audio):
        raise RuntimeError(f"audio not found: {audio!r}")
    aid = hg.upload_audio(audio)
    return hg.generate(tid, aid, out, aspect=aspect)


def render_avatar(channel, audio, out, image=None, track=None, allow_fallback=True):
    """Returns (track_used, out_path). echomimic_local falls back to heygen on any
    failure unless allow_fallback=False."""
    cfg = AVATAR_TRACKS.get(channel, AVATAR_TRACKS["_default"])
    track = track or cfg.get("track", "heygen")
    if track == "echomimic_local":
        try:
            return ("echomimic_local", render_echomimic_local(cfg, image, audio, out))
        except Exception as e:  # noqa: BLE001 -- any failure must fall through to paid
            if not allow_fallback:
                raise
            sys.stderr.write(f"[avatar_render] echomimic_local failed ({e}); "
                             "falling back to heygen\n")
            return ("heygen(fallback)", render_heygen(cfg, image, audio, out))
    if track == "heygen":
        return ("heygen", render_heygen(cfg, image, audio, out))
    raise SystemExit(f"unknown avatar_track {track!r}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True)
    ap.add_argument("--audio", required=True, help="voiceover wav that drives the lips")
    ap.add_argument("--out", required=True)
    ap.add_argument("--image", default=None,
                    help="host portrait (local path or URL); default = channel host")
    ap.add_argument("--track", choices=["echomimic_local", "heygen"], default=None,
                    help="override the channel's default avatar_track")
    ap.add_argument("--no-fallback", action="store_true",
                    help="fail hard instead of falling back to heygen")
    a = ap.parse_args()
    used, path = render_avatar(a.channel, a.audio, a.out, image=a.image,
                               track=a.track, allow_fallback=not a.no_fallback)
    print(f"AVATAR_OK track={used} -> {path}")


if __name__ == "__main__":
    main()
