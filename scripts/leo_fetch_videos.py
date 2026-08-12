#!/usr/bin/env python3
"""Fetch recent Leonardo VIDEO (motion/Hailuo) generations via the API GET endpoint.
GET calls are free (no generation tokens). Downloads the .mp4 for each completed
video generation into <outdir>. Usage: leo_fetch_videos.py <outdir> [limit]
"""
import json, os, re, subprocess, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
env = open(os.path.join(HERE, "..", ".env")).read()
KEY = re.search(r"LEONARDO_API_KEY=(\S+)", env).group(1)
outdir = sys.argv[1] if len(sys.argv) > 1 else "."
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 15
os.makedirs(outdir, exist_ok=True)
H = {"Authorization": f"Bearer {KEY}", "Accept": "application/json"}

def get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=H)))

uid = get("https://cloud.leonardo.ai/api/rest/v1/me")["user_details"][0]["user"]["id"]
gens = get(f"https://cloud.leonardo.ai/api/rest/v1/generations/user/{uid}?offset=0&limit={limit}")["generations"]

for g in gens:
    blob = json.dumps(g)
    mp4s = re.findall(r'https?://[^"\\ ]+?\.mp4', blob)
    if not mp4s:
        continue  # not a video generation (or not ready)
    pid = g["id"][:8]
    head = re.sub(r"[^a-z0-9]+", "-", (g.get("prompt") or "vid")[:36].lower()).strip("-")
    url = mp4s[0]
    path = os.path.join(outdir, f"{head[:32]}_{pid}.mp4")
    print(f"{g['id']} | {g.get('status')} | {g.get('imageWidth')}x{g.get('imageHeight')} | {g.get('prompt','')[:55]}")
    if not os.path.exists(path):
        subprocess.run(["curl", "-sL", url, "-o", path], check=False)
        print(f"   saved {path}")
    else:
        print(f"   exists {path}")
