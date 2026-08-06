#!/usr/bin/env python3
"""
Character-consistent Leonardo generator for the Lulla pipeline.

Uploads a reference image (the canonical Lulla) and generates new images that
keep the same character, using either:
  - image-to-image  (--mode img2img,  --strength 0.1..0.9  higher = closer to ref)
  - Character Reference controlnet (--mode charref, --strengthType Low|Mid|High)

Usage:
  python3 scripts/leo_ref_gen.py \
    --ref assets/character/canonical/lulla_master.jpg \
    --prompt "..." --negative "..." \
    --model 7b592283-e8a7-4c5a-9ba6-d18c31f258b9 \
    --num 4 --mode img2img --strength 0.45 \
    --out assets/character --label lulla_sleepy

Reference-image IDs are cached in <out>/.initid_<basename>.txt to avoid re-uploading.
"""
import argparse, json, os, sys, time
import requests

BASE = "https://cloud.leonardo.ai/api/rest/v1"

def load_key():
    # read LEONARDO_API_KEY from ../.env relative to this script
    here = os.path.dirname(os.path.abspath(__file__))
    env = os.path.join(here, "..", ".env")
    with open(env) as f:
        for line in f:
            if line.strip().startswith("LEONARDO_API_KEY="):
                return line.strip().split("=", 1)[1]
    sys.exit("LEONARDO_API_KEY not found in .env")

KEY = load_key()
H = {"Authorization": f"Bearer {KEY}", "Accept": "application/json", "Content-Type": "application/json"}

def upload_ref(path, out):
    cache = os.path.join(out, ".initid_" + os.path.basename(path) + ".txt")
    if os.path.exists(cache):
        return open(cache).read().strip()
    ext = path.rsplit(".", 1)[-1].lower().replace("jpg", "jpeg") if False else path.rsplit(".", 1)[-1].lower()
    r = requests.post(f"{BASE}/init-image", headers=H, json={"extension": ext})
    r.raise_for_status()
    d = r.json()["uploadInitImage"]
    image_id = d["id"]
    fields = json.loads(d["fields"])
    url = d["url"]
    with open(path, "rb") as fh:
        up = requests.post(url, data=fields, files={"file": (os.path.basename(path), fh)})
    if up.status_code not in (200, 201, 204):
        sys.exit(f"S3 upload failed {up.status_code}: {up.text[:300]}")
    os.makedirs(out, exist_ok=True)
    open(cache, "w").write(image_id)
    print(f">> uploaded ref, init_image_id={image_id}")
    return image_id

def generate(args, init_id):
    body = {
        "prompt": args.prompt,
        "modelId": args.model,
        "num_images": args.num,
        "width": args.width,
        "height": args.height,
    }
    if args.negative:
        body["negative_prompt"] = args.negative
    if args.mode == "img2img":
        body["init_image_id"] = init_id
        body["init_strength"] = args.strength
    elif args.mode == "charref":
        body["controlnets"] = [{
            "initImageId": init_id,
            "initImageType": "UPLOADED",
            "preprocessorId": 133,          # Character Reference
            "strengthType": args.strengthType,
        }]
    r = requests.post(f"{BASE}/generations", headers=H, json=body)
    if r.status_code >= 400:
        sys.exit(f"!! generation POST {r.status_code}: {r.text[:500]}")
    gid = r.json().get("sdGenerationJob", {}).get("generationId")
    if not gid:
        sys.exit(f"!! no generationId: {r.text[:500]}")
    print(f">> generationId={gid}")
    return gid

def poll_download(gid, out, label):
    os.makedirs(out, exist_ok=True)
    for i in range(1, 41):
        time.sleep(5)
        s = requests.get(f"{BASE}/generations/{gid}", headers=H).json()
        pk = s.get("generations_by_pk", {})
        st = pk.get("status")
        print(f">> poll {i}: {st}")
        if st == "COMPLETE":
            imgs = pk.get("generated_images", [])
            for j, im in enumerate(imgs):
                u = im["url"]
                fn = os.path.join(out, f"{label}_{j}.jpg")
                open(fn, "wb").write(requests.get(u).content)
                print(f"   saved {fn}")
            print(f">> DONE: {len(imgs)} images (label={label})")
            return
        if st == "FAILED":
            sys.exit(f"!! generation FAILED: {json.dumps(pk)[:300]}")
    sys.exit("!! timeout")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--negative", default="")
    ap.add_argument("--model", required=True)
    ap.add_argument("--num", type=int, default=4)
    ap.add_argument("--width", type=int, default=1024)
    ap.add_argument("--height", type=int, default=1024)
    ap.add_argument("--mode", choices=["img2img", "charref"], default="img2img")
    ap.add_argument("--strength", type=float, default=0.45)      # img2img
    ap.add_argument("--strengthType", default="High")            # charref
    ap.add_argument("--out", default="assets")
    ap.add_argument("--label", default="ref_gen")
    args = ap.parse_args()

    init_id = upload_ref(args.ref, args.out)
    gid = generate(args, init_id)
    poll_download(gid, args.out, args.label)

if __name__ == "__main__":
    main()
