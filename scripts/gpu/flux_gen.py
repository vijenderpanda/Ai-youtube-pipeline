#!/usr/bin/env python3
"""Headless FLUX.1-schnell text-to-image via the ComfyUI HTTP API. POSTs the
workflow, polls /history, fetches the image, saves it. Stdlib only (no deps).
schnell = 4 steps, cfg 1, euler/simple, NO FluxGuidance."""
import argparse
import json
import time
import urllib.parse
import urllib.request
import uuid

WORKFLOW = {
    "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "flux1-schnell-Q5_K_S.gguf"}},
    "2": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "t5xxl_fp8_e4m3fn.safetensors",
          "clip_name2": "clip_l.safetensors", "type": "flux"}},
    "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
    "4": {"class_type": "EmptySD3LatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
    "5": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["2", 0]}},
    "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["2", 0]}},
    "7": {"class_type": "KSampler", "inputs": {"seed": 0, "steps": 4, "cfg": 1.0,
          "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0,
          "model": ["1", 0], "positive": ["5", 0], "negative": ["6", 0], "latent_image": ["4", 0]}},
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
    "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "flux_schnell", "images": ["8", 0]}},
}


def gen(server, prompt, seed, width, height, out):
    g = json.loads(json.dumps(WORKFLOW))
    g["5"]["inputs"]["text"] = prompt
    g["7"]["inputs"]["seed"] = int(seed)
    g["4"]["inputs"]["width"] = int(width)
    g["4"]["inputs"]["height"] = int(height)
    body = json.dumps({"prompt": g, "client_id": str(uuid.uuid4())}).encode()
    req = urllib.request.Request(server + "/prompt", data=body,
                                 headers={"Content-Type": "application/json"})
    pid = json.load(urllib.request.urlopen(req, timeout=60))["prompt_id"]
    print("prompt_id", pid)
    deadline = time.time() + 300
    while time.time() < deadline:
        time.sleep(2)
        h = json.load(urllib.request.urlopen(server + "/history/" + pid, timeout=30))
        if pid in h and h[pid].get("outputs"):
            imgs = (h[pid]["outputs"].get("9") or {}).get("images") or []
            if not imgs:
                raise SystemExit("FLUX_GEN_FAIL no image in outputs")
            img = imgs[0]
            q = urllib.parse.urlencode({"filename": img["filename"],
                                        "subfolder": img.get("subfolder", ""),
                                        "type": img.get("type", "output")})
            data = urllib.request.urlopen(server + "/view?" + q, timeout=60).read()
            with open(out, "wb") as f:
                f.write(data)
            print("FLUX_GEN_OK", out, len(data), "bytes")
            return
    raise SystemExit("FLUX_GEN_TIMEOUT")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="http://127.0.0.1:8188")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--width", type=int, default=1024)
    ap.add_argument("--height", type=int, default=1024)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    gen(a.server, a.prompt, a.seed, a.width, a.height, a.out)
