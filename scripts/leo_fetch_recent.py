#!/usr/bin/env python3
"""Fetch recent Leonardo generations (metadata + images) via the API GET endpoint.

Usage: leo_fetch_recent.py <outdir> [limit]
Saves each generation's images as <outdir>/<prompt-slug-or-label>_<n>.jpg and
prints a summary line per generation (id, dims, prompt head).
GET calls cost no API generation tokens.
"""
import json, os, re, subprocess, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
env = open(os.path.join(HERE, "..", ".env")).read()
KEY = re.search(r"LEONARDO_API_KEY=(\S+)", env).group(1)

outdir = sys.argv[1] if len(sys.argv) > 1 else "."
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 15
os.makedirs(outdir, exist_ok=True)

# user id lookup
req = urllib.request.Request("https://cloud.leonardo.ai/api/rest/v1/me",
                             headers={"Authorization": f"Bearer {KEY}", "Accept": "application/json"})
uid = json.load(urllib.request.urlopen(req))["user_details"][0]["user"]["id"]

req = urllib.request.Request(
    f"https://cloud.leonardo.ai/api/rest/v1/generations/user/{uid}?offset=0&limit={limit}",
    headers={"Authorization": f"Bearer {KEY}", "Accept": "application/json"})
gens = json.load(urllib.request.urlopen(req))["generations"]

for g in gens:
    pid = g["id"][:8]
    head = re.sub(r"[^a-z0-9]+", "-", g["prompt"][:40].lower()).strip("-")
    status = g.get("status")
    imgs = g.get("generated_images", [])
    print(f"{g['id']} | {status} | {g.get('imageWidth')}x{g.get('imageHeight')} | {len(imgs)} imgs | {g['prompt'][:70]}")
    for i, im in enumerate(imgs):
        path = os.path.join(outdir, f"{head[:36]}_{pid}_{i}.jpg")
        if not os.path.exists(path):
            subprocess.run(["curl", "-s", im["url"], "-o", path], check=False)
            print(f"   saved {path}")
