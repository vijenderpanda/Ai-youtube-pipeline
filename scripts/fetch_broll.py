#!/usr/bin/env python3
"""
Licensed stock b-roll fetcher for the AI Unpacked news-split format.

Sources (all free for commercial use, no attribution required):
  - Pexels Videos  (PEXELS_API_KEY in .env  — free key: https://www.pexels.com/api/)
  - Pixabay Videos (PIXABAY_API_KEY in .env — free key: https://pixabay.com/api/docs/)

Usage:
  # search + download top portrait-friendly clips for a query
  python3 scripts/fetch_broll.py --q "humanoid robot" --n 3 \
      --out channels/claude-tricks/assets/ep13/broll

  # preview only (no download)
  python3 scripts/fetch_broll.py --q "data center" --list

Picks HD clips, prefers portrait/tall or croppable landscape, writes
<out>/<source>_<id>.mp4 plus a manifest.json with source URLs for the
episode credits/records.
"""
import argparse, json, os, sys
import requests

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def env_key(name):
    p = os.path.join(REPO, ".env")
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"')
    return os.environ.get(name)

def pexels(query, n, key):
    r = requests.get("https://api.pexels.com/videos/search",
                     headers={"Authorization": key},
                     params={"query": query, "per_page": n * 2, "orientation": "portrait"},
                     timeout=30)
    r.raise_for_status()
    out = []
    for v in r.json().get("videos", []):
        files = sorted(v.get("video_files", []),
                       key=lambda f: (f.get("height") or 0), reverse=True)
        best = next((f for f in files if (f.get("height") or 0) >= 1080), files[0] if files else None)
        if best:
            out.append({"source": "pexels", "id": v["id"], "dur": v.get("duration"),
                        "w": best.get("width"), "h": best.get("height"),
                        "url": best["link"], "page": v.get("url")})
    return out[:n]

def pixabay(query, n, key):
    r = requests.get("https://pixabay.com/api/videos/",
                     params={"key": key, "q": query, "per_page": n * 2, "safesearch": "true"},
                     timeout=30)
    r.raise_for_status()
    out = []
    for v in r.json().get("hits", []):
        f = v["videos"].get("large") or v["videos"].get("medium")
        if f:
            out.append({"source": "pixabay", "id": v["id"], "dur": v.get("duration"),
                        "w": f.get("width"), "h": f.get("height"),
                        "url": f["url"], "page": v.get("pageURL")})
    return out[:n]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--q", required=True, help="search query, e.g. 'humanoid robot'")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--out", help="download dir (required unless --list)")
    ap.add_argument("--list", action="store_true", help="preview matches, no download")
    a = ap.parse_args()

    pex, pix = env_key("PEXELS_API_KEY"), env_key("PIXABAY_API_KEY")
    if not pex and not pix:
        sys.exit("No PEXELS_API_KEY or PIXABAY_API_KEY in .env — both are free:\n"
                 "  Pexels:  https://www.pexels.com/api/\n"
                 "  Pixabay: https://pixabay.com/api/docs/")

    hits = []
    if pex:
        try: hits += pexels(a.q, a.n, pex)
        except Exception as e: print(f"!! pexels: {e}")
    if pix and len(hits) < a.n:
        try: hits += pixabay(a.q, a.n - len(hits), pix)
        except Exception as e: print(f"!! pixabay: {e}")

    if not hits:
        sys.exit(f"no results for '{a.q}'")
    for h in hits:
        print(f"  {h['source']}:{h['id']}  {h['w']}x{h['h']}  {h['dur']}s  {h['page']}")
    if a.list:
        return

    if not a.out:
        sys.exit("--out required to download")
    os.makedirs(a.out, exist_ok=True)
    manifest = []
    for h in hits:
        dst = os.path.join(a.out, f"{h['source']}_{h['id']}.mp4")
        if not os.path.exists(dst):
            print(f">> downloading {h['source']}:{h['id']} ...")
            with requests.get(h["url"], stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(dst, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
        manifest.append({**h, "file": os.path.basename(dst)})
    mp = os.path.join(a.out, "manifest.json")
    json.dump(manifest, open(mp, "w"), indent=1)
    print(f">> {len(manifest)} clips -> {a.out}  (manifest.json records source pages)")

if __name__ == "__main__":
    main()
