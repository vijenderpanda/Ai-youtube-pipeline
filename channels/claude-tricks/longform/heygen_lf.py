#!/usr/bin/env python3
"""
heygen_lf.py — Avatar IV batch for ep1 refine pass (VJ artifact notes 2026-08-26):
animate the two monitor-stage plate hosts per VO slot (lip-synced explaining), and
generate the missing host_ch4 chapter clip. Requires HeyGen API wallet funded.

Slot audio = the section VO sliced to that line's bounds (VIDEO-side driver only;
the master's continuous VO take is untouched — audio law preserved).
"""
import json, os, subprocess, sys, time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CH = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(CH))
sys.path.insert(0, os.path.join(REPO, "scripts"))
import heygen_avatar as hg

A = os.path.join(CH, "assets", "longform_ep1")
VO = os.path.join(A, "vo")
L = os.path.join(CH, "assets", "character", "host_library", "longform_champagne_v1")
PLATE0 = os.path.join(A, "stage_plates", "using-the-reference-image-keep-the-e_1f1a0a5d_1.jpg")
PLATE1 = os.path.join(L, "using-the-reference-image-keep-the-e_1f1a0757_1.jpg")
HOST_MED = os.path.join(L, "using-the-reference-image-keep-the-e_1f19f905_1.jpg")

MOTION_PLATE = ("The person sits at the desk explaining toward the monitor, natural "
                "hand gestures, subtle head movement. Camera completely locked, no "
                "zoom, no pan. The monitor and room stay perfectly still.")
MOTION_HOST = ("Natural presenter energy, talking to camera with hand gestures, "
               "subtle head motion. Camera locked, background still.")

# (tag, image, section, line_index or None=whole section, motion)
SLOTS = [
    ("plate_rel0", PLATE0, "relate", 0, MOTION_PLATE),
    ("plate_rel2", PLATE0, "relate", 2, MOTION_PLATE),
    ("plate_rel3", PLATE1, "relate", 3, MOTION_PLATE),
    ("plate_ch1s0", PLATE0, "ch1", 0, MOTION_PLATE),
    ("plate_ch3s0", PLATE1, "ch3", 0, MOTION_PLATE),
    ("host_ch4", HOST_MED, "ch4", None, MOTION_HOST),
    ("host_appfeat", HOST_MED, "appfeat", None, MOTION_HOST),
]


def line_bounds(section, idx):
    m = json.load(open(os.path.join(VO, "sections.json")))[section]
    if idx is None:
        return 0.0, m["duration"]
    b = m["bounds"][idx]
    return b["start"], b["end"]


def slice_audio(section, idx, out):
    t0, t1 = line_bounds(section, idx)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i",
                    os.path.join(VO, f"{section}.mp3"),
                    "-ss", str(t0), "-to", str(t1),
                    "-ar", "48000", "-ac", "2", out], check=True)
    return out


def gen_iv(image_asset, audio_asset, motion, out):
    body = {"type": "image",
            "image": {"type": "asset_id", "asset_id": image_asset},
            "audio_asset_id": audio_asset,
            "aspect_ratio": "16:9", "resolution": "1080p",
            "motion_prompt": motion}
    r = requests.post("https://api.heygen.com/v3/videos",
                      headers={"x-api-key": hg.KEY, "Content-Type": "application/json"},
                      json=body)
    print("generate:", r.status_code, r.text[:300])
    r.raise_for_status()
    d = r.json()["data"]
    vid = d.get("video_id") or d["id"]
    for i in range(200):
        time.sleep(8)
        s = requests.get(f"https://api.heygen.com/v3/videos/{vid}",
                         headers={"x-api-key": hg.KEY}).json()
        st = s.get("data", {}).get("status")
        print(f"  poll {i}: {st}", flush=True)
        if st == "completed":
            open(out, "wb").write(requests.get(s["data"]["video_url"]).content)
            print(">> saved", out)
            return out
        if st == "failed":
            raise RuntimeError("failed: " + json.dumps(s)[:400])
    raise RuntimeError("timeout")


def main():
    img_cache = {}
    for tag, img, section, idx, motion in SLOTS:
        out = os.path.join(A, f"{tag}.mp4")
        if os.path.exists(out):
            print("skip (exists):", out); continue
        if img not in img_cache:
            img_cache[img] = hg.upload_image(img)
        wav = os.path.join(A, f"_slot_{tag}.wav")
        slice_audio(section, idx, wav)
        aud = hg.upload_audio(wav)
        gen_iv(img_cache[img], aud, motion, out)
        os.remove(wav)


if __name__ == "__main__":
    main()
