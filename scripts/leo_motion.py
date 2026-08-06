#!/usr/bin/env python3
"""
Leonardo Motion 2.0 image-to-video. Animates a still into a short motion clip.

Usage:
  python3 scripts/leo_motion.py --gen-id <generationId> --idx 0 \
      --prompt "gentle lively animation, the parrot sways to music" \
      --resolution RESOLUTION_720 --out out.mp4
  # or from a local file (uploaded as init):
  python3 scripts/leo_motion.py --upload scene.jpg --prompt "..." --out out.mp4

Prints the raw response (incl. any apiCreditCost) so you know the cost before scaling.
"""
import requests, sys, time, json, os, re, argparse
BASE = "https://cloud.leonardo.ai/api/rest/v1"

def load_key():
    here = os.path.dirname(os.path.abspath(__file__))
    for line in open(os.path.join(here, "..", ".env")):
        if line.strip().startswith("LEONARDO_API_KEY="):
            return line.strip().split("=", 1)[1]
    sys.exit("LEONARDO_API_KEY not found")

H = {"Authorization": f"Bearer {load_key()}", "Accept": "application/json", "Content-Type": "application/json"}

def find_key(d, key):
    if isinstance(d, dict):
        for k, v in d.items():
            if k == key:
                return v
            r = find_key(v, key)
            if r is not None:
                return r
    elif isinstance(d, list):
        for it in d:
            r = find_key(it, key)
            if r is not None:
                return r
    return None

def get_image_id(gen_id, idx):
    r = requests.get(f"{BASE}/generations/{gen_id}", headers=H).json()
    imgs = r["generations_by_pk"]["generated_images"]
    return imgs[idx]["id"], imgs[idx]["url"]

def upload_init(path):
    ext = path.rsplit(".", 1)[-1].lower()
    r = requests.post(f"{BASE}/init-image", headers=H, json={"extension": ext}); r.raise_for_status()
    d = r.json()["uploadInitImage"]; fields = json.loads(d["fields"])
    with open(path, "rb") as fh:
        up = requests.post(d["url"], data=fields, files={"file": (os.path.basename(path), fh)})
    up.raise_for_status()
    return d["id"]

def motion(image_id, is_init, prompt, resolution, enhance):
    body = {
        "imageType": "UPLOADED" if is_init else "GENERATED",
        "isPublic": False,
        "resolution": resolution,
        "imageId": image_id,
        "prompt": prompt,
        "frameInterpolation": True,
        "promptEnhance": enhance,
    }
    r = requests.post(f"{BASE}/generations-image-to-video", headers=H, json=body)
    if r.status_code >= 400:
        sys.exit(f"!! POST {r.status_code}: {r.text[:600]}")
    data = r.json()
    print(">> raw response:", json.dumps(data)[:500])
    return find_key(data, "generationId"), find_key(data, "apiCreditCost")

def poll(gen_id, out):
    for i in range(90):
        time.sleep(6)
        s = requests.get(f"{BASE}/generations/{gen_id}", headers=H).json()
        pk = s.get("generations_by_pk", {}); st = pk.get("status")
        print(f">> poll {i}: {st}")
        if st == "COMPLETE":
            gi = pk.get("generated_images", [])
            url = None
            if gi:
                url = gi[0].get("motionMP4URL") or gi[0].get("videoUrl") or gi[0].get("url")
            if not url or not str(url).endswith(".mp4"):
                m = re.findall(r'https?://[^"\\ ]+?\.mp4', json.dumps(s))
                if m:
                    url = m[0]
            print(">> video url:", url)
            if url:
                open(out, "wb").write(requests.get(url).content)
                print(">> saved", out)
            else:
                print(">> NO MP4. pk keys:", list(pk.keys()), "img0 keys:", list(gi[0].keys()) if gi else None)
            return url
        if st == "FAILED":
            sys.exit("!! FAILED " + json.dumps(pk)[:400])
    sys.exit("!! timeout")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen-id"); ap.add_argument("--idx", type=int, default=0)
    ap.add_argument("--upload")
    ap.add_argument("--prompt", default="gentle lively animation, cheerful smooth motion")
    ap.add_argument("--resolution", default="RESOLUTION_720")
    ap.add_argument("--no-enhance", action="store_true", help="disable promptEnhance to preserve composition")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.upload:
        iid = upload_init(a.upload); is_init = True; print(">> init id", iid)
    else:
        iid, url = get_image_id(a.gen_id, a.idx); is_init = False; print(">> image id", iid, url[:60])
    mg, cost = motion(iid, is_init, a.prompt, a.resolution, not a.no_enhance)
    print(f">> motion genId={mg}  apiCreditCost={cost}")
    if not mg:
        sys.exit("!! no generationId in response")
    poll(mg, a.out)
