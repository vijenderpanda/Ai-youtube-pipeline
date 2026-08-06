#!/usr/bin/env python3
"""
HeyGen talking-photo pipeline for AI Unpacked.

Turns a real photo + a voiceover WAV into a lip-synced talking-head clip.
Renders via POST /v3/videos (avatar mode); the legacy /v2/video/generate is removed 2026-10-31.

Usage:
  # one-time: upload the host photo -> prints talking_photo_id (cached in .heygen_photo_id)
  python3 scripts/heygen_avatar.py --photo channels/claude-tricks/assets/character/ref_images/38.JPEG

  # generate a talking clip from audio (uses cached talking_photo_id)
  python3 scripts/heygen_avatar.py --audio channels/claude-tricks/renders/voicetest.wav \
      --out channels/claude-tricks/renders/talking_test.mp4 [--bg "#0E0E14"]
"""
import argparse, json, os, sys, time
import requests

def load_key():
    here = os.path.dirname(os.path.abspath(__file__))
    for line in open(os.path.join(here, "..", ".env")):
        if line.strip().startswith("HEYGEN_API_KEY="):
            return line.strip().split("=", 1)[1].strip()
    sys.exit("HEYGEN_API_KEY not found in .env")

KEY = load_key()
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                     "channels", "claude-tricks", "assets", "character", ".heygen_photo_id")

def upload_photo(path, cache=CACHE):
    """Upload a host photo -> talking_photo_id, cached at `cache`.
    Pass a per-outfit cache path (see host_outfit.py) to register wardrobe
    variants without clobbering the global .heygen_photo_id."""
    ext = path.rsplit(".", 1)[-1].lower().replace("jpeg", "jpg")
    ctype = {"jpg": "image/jpeg", "png": "image/png"}[ext]
    r = requests.post("https://upload.heygen.com/v1/talking_photo",
                      headers={"x-api-key": KEY, "Content-Type": ctype},
                      data=open(path, "rb").read())
    print("upload:", r.status_code, r.text[:300])
    r.raise_for_status()
    tid = r.json()["data"]["talking_photo_id"]
    open(cache, "w").write(tid)
    print(">> talking_photo_id:", tid, "(cached ->", os.path.basename(os.path.dirname(cache)) + "/" + os.path.basename(cache) + ")")
    return tid

def delete_group(tid):
    """Delete a talking-photo avatar GROUP (id == talking_photo_id), freeing one
    of the 3 HeyGen photo-avatar slots. Used by host_outfit's ephemeral pool to
    recycle outfit avatars it created. NOTE: /v2 avatar_group is Legacy (HeyGen
    sunsets it 2026-10-31 — swap to the replacement endpoint before then)."""
    r = requests.delete("https://api.heygen.com/v2/avatar_group/" + tid,
                        headers={"x-api-key": KEY})
    print(f"delete_group {tid[:8]}...: {r.status_code}")
    return r.status_code < 300


def group_count():
    """How many photo-avatar groups the account holds (cap is 3)."""
    r = requests.get("https://api.heygen.com/v2/avatar_group.list",
                     headers={"x-api-key": KEY})
    return r.json().get("data", {}).get("total_count")


def upload_audio(path):
    if not path.endswith(".mp3"):
        import subprocess
        mp3 = path.rsplit(".", 1)[0] + ".mp3"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path,
                        "-b:a", "192k", mp3], check=True)
        path = mp3
    r = requests.post("https://upload.heygen.com/v1/asset",
                      headers={"x-api-key": KEY, "Content-Type": "audio/mpeg"},
                      data=open(path, "rb").read())
    if r.status_code >= 400:
        print("audio upload error:", r.status_code, r.text[:300])
    r.raise_for_status()
    aid = r.json()["data"]["id"]
    print(">> audio asset:", aid)
    return aid

def upload_image(path):
    ext = path.rsplit(".", 1)[-1].lower().replace("jpeg", "jpg")
    ctype = {"jpg": "image/jpeg", "png": "image/png"}[ext]
    r = requests.post("https://upload.heygen.com/v1/asset",
                      headers={"x-api-key": KEY, "Content-Type": ctype},
                      data=open(path, "rb").read())
    r.raise_for_status()
    aid = r.json()["data"]["id"]
    print(">> image asset:", aid)
    return aid

def generate(tid, audio_id, out, bg="#0E0E14", bg_image_asset=None, matting=None):
    """matting: None = auto (matte only when a replacement bg is requested);
    with matting off the talking photo keeps its own background."""
    background = ({"type": "image", "asset_id": bg_image_asset}
                  if bg_image_asset else {"type": "color", "value": bg})
    do_matte = matting if matting is not None else bool(bg_image_asset)
    body = {
        "type": "avatar",
        "avatar_id": tid,  # photo-avatar (talking photo) ids are valid here
        "audio_asset_id": audio_id,
        "background": background,
        "resolution": "720p",
        "aspect_ratio": "9:16",
        "expressiveness": "high",
    }
    if do_matte:
        body["remove_background"] = True
    r = requests.post("https://api.heygen.com/v3/videos",
                      headers={"x-api-key": KEY, "Content-Type": "application/json"},
                      json=body)
    print("generate:", r.status_code, r.text[:400])
    r.raise_for_status()
    d = r.json()["data"]
    vid = d.get("video_id") or d["id"]
    print(">> video_id:", vid)
    for i in range(120):
        time.sleep(6)
        s = requests.get(f"https://api.heygen.com/v3/videos/{vid}",
                         headers={"x-api-key": KEY}).json()
        st = s.get("data", {}).get("status")
        print(f"   poll {i}: {st}")
        if st == "completed":
            url = s["data"]["video_url"]
            open(out, "wb").write(requests.get(url).content)
            print(">> saved", out)
            return out
        if st == "failed":
            sys.exit("!! failed: " + json.dumps(s)[:400])
    sys.exit("!! timeout")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--photo")
    ap.add_argument("--audio")
    ap.add_argument("--out")
    ap.add_argument("--bg", default="#0E0E14")
    ap.add_argument("--bg-image", help="background image file (uploaded + composited behind the cutout host)")
    a = ap.parse_args()
    if a.photo:
        upload_photo(a.photo)
    if a.audio:
        tid = open(CACHE).read().strip() if os.path.exists(CACHE) else sys.exit("upload --photo first")
        if not a.out:
            sys.exit("need --out")
        bg_asset = upload_image(a.bg_image) if a.bg_image else None
        generate(tid, upload_audio(a.audio), a.out, a.bg, bg_asset)
