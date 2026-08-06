#!/usr/bin/env python3
"""Backfill historical renders + generator catalog metadata into the factory (Supabase).

Idempotent / re-runnable:
  - uploads each FINAL from the render inventory to the factory-renders bucket at
    <channel_key>/historical/<safe filename> (x-upsert), skipping any file whose
    storage_path already has a factory_renders row
  - inserts a factory_renders row per uploaded file (origin='historical')
  - merges gen_meta_*.json into factory_generators (PATCH on name): category,
    what_it_does, inputs, outputs, channels, and samples[] built from the uploaded
    renders (sample_globs + inventory generator attribution, max 4, videos first)
  - logs one factory_events row (kind='backfill') per run

'unsure' inventory entries are never uploaded. Never deletes local files.

Usage:
  python3 scripts/backfill_renders.py --inventory <render_inventory.json> \
      --gen-meta '<glob for gen_meta_*.json>' [--dry-run]
"""
import argparse
import fnmatch
import glob
import json
import mimetypes
import os
import re
import subprocess
import sys

import requests

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(REPO_ROOT, "secrets", "factory.env")
BUCKET = "factory-renders"
# Supabase free-plan hard cap: 50 MiB per object. Videos over this are uploaded
# as a re-encoded preview (originals on disk are never touched).
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

MIME_BY_EXT = {
    ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".gif": "image/gif", ".webp": "image/webp",
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4",
    ".flac": "audio/flac", ".ogg": "audio/ogg",
}


def load_env(path):
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def safe_filename(name):
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name.strip("._") or "file"


def guess_mime(path):
    ext = os.path.splitext(path)[1].lower()
    return MIME_BY_EXT.get(ext) or mimetypes.guess_type(path)[0] or "application/octet-stream"


def make_preview(src, work_dir):
    """Re-encode src (video) into work_dir until it fits MAX_UPLOAD_BYTES.

    Returns the preview path, or None if even the smallest attempt is too big.
    Never modifies src.
    """
    os.makedirs(work_dir, exist_ok=True)
    base = safe_filename(os.path.basename(src))
    for crf, height in ((26, 720), (30, 720), (34, 540)):
        out = os.path.join(work_dir, f"crf{crf}_h{height}_{base}")
        if not (os.path.exists(out) and os.path.getsize(out) > 0):
            cmd = [
                "ffmpeg", "-y", "-v", "error", "-i", src,
                "-vf", f"scale=-2:'min({height},ih)'",
                "-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart", out,
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"  WARN ffmpeg failed on {src}: {res.stderr[-300:]}")
                continue
        if os.path.getsize(out) < MAX_UPLOAD_BYTES:
            return out
    return None


def ffprobe_duration(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=60,
        )
        val = out.stdout.strip()
        return round(float(val), 2) if val else None
    except Exception:
        return None


class Api:
    def __init__(self, url, key):
        self.rest = url.rstrip("/") + "/rest/v1"
        self.storage = url.rstrip("/") + "/storage/v1"
        self.s = requests.Session()
        self.s.headers.update({"apikey": key, "Authorization": f"Bearer {key}"})

    def get_all(self, table, params):
        rows, offset, page = [], 0, 1000
        while True:
            p = dict(params)
            p["limit"], p["offset"] = page, offset
            r = self.s.get(f"{self.rest}/{table}", params=p, timeout=60)
            r.raise_for_status()
            chunk = r.json()
            rows.extend(chunk)
            if len(chunk) < page:
                return rows
            offset += page

    def insert(self, table, row):
        r = self.s.post(
            f"{self.rest}/{table}", json=row,
            headers={"Prefer": "return=representation"}, timeout=60,
        )
        r.raise_for_status()
        return r.json()

    def patch_generator(self, name, fields):
        r = self.s.patch(
            f"{self.rest}/factory_generators", params={"name": f"eq.{name}"},
            json=fields, headers={"Prefer": "return=representation"}, timeout=60,
        )
        r.raise_for_status()
        return r.json()

    def upload(self, storage_path, local_path, mime):
        with open(local_path, "rb") as f:
            data = f.read()
        r = self.s.post(
            f"{self.storage}/object/{BUCKET}/{storage_path}", data=data,
            headers={"Content-Type": mime, "x-upsert": "true"}, timeout=600,
        )
        r.raise_for_status()
        return r.json()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory", required=True, help="render_inventory.json path")
    ap.add_argument("--gen-meta", required=True,
                    help="glob for gen_meta_*.json files (quote it)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview-dir",
                    default=os.path.join(REPO_ROOT, "renders_out", "_backfill_previews"),
                    help="work dir for sub-50MiB re-encodes of oversized videos")
    args = ap.parse_args()

    env = load_env(ENV_PATH)
    api = Api(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])

    inv = json.load(open(args.inventory))
    finals = inv.get("finals", [])
    gen_meta = []
    meta_files = sorted(glob.glob(args.gen_meta))
    if not meta_files:
        sys.exit(f"no gen_meta files match {args.gen_meta}")
    for mf in meta_files:
        gen_meta.extend(json.load(open(mf)))
    print(f"inventory finals: {len(finals)}  generator cards: {len(gen_meta)}")

    # ---- existing rows (idempotency) ----
    existing = {
        r["storage_path"]
        for r in api.get_all("factory_renders", {"select": "storage_path"})
    }
    print(f"factory_renders rows already present: {len(existing)}")

    # ---- 1. upload finals + insert rows ----
    uploaded = 0
    previewed = []
    render_index = []  # every final with its storage_path (uploaded now or before)
    for item in finals:
        local = item["path"]
        if not os.path.exists(local):
            print(f"  SKIP (missing local file): {local}")
            continue
        fname = safe_filename(os.path.basename(local))
        storage_path = f"{item['channel_key']}/historical/{fname}"
        rel = os.path.relpath(local, REPO_ROOT)
        record = {
            "channel_key": item["channel_key"],
            "filename": fname,
            "storage_path": storage_path,
            "kind": item.get("kind"),
            "size_bytes": item.get("size_bytes") or os.path.getsize(local),
            "title": item.get("title") or fname,
            "generator": item.get("generator"),
            "origin": "historical",
        }
        if item.get("kind") in ("video", "audio"):
            record["duration_s"] = ffprobe_duration(local)
        if storage_path in existing:
            render_index.append({**record, "rel_path": rel})
            continue
        # oversized videos: upload a re-encoded preview instead (originals untouched)
        upload_src = local
        if os.path.getsize(local) > MAX_UPLOAD_BYTES:
            if item.get("kind") != "video":
                print(f"  SKIP (over {MAX_UPLOAD_BYTES // 2**20} MiB, "
                      f"not a video): {rel}")
                continue
            if args.dry_run:
                print(f"  DRY: would re-encode preview for {rel}")
            else:
                upload_src = make_preview(local, args.preview_dir)
                if not upload_src:
                    print(f"  SKIP (could not fit under cap): {rel}")
                    continue
                record["size_bytes"] = os.path.getsize(upload_src)
                previewed.append(rel)
        render_index.append({**record, "rel_path": rel})
        if args.dry_run:
            print(f"  DRY: would upload {rel} -> {storage_path}")
            uploaded += 1
            continue
        print(f"  upload {rel} -> {storage_path} "
              f"({record['size_bytes'] / 1e6:.1f} MB)")
        api.upload(storage_path, upload_src, guess_mime(local))
        api.insert("factory_renders", record)
        existing.add(storage_path)
        uploaded += 1
    print(f"uploaded (new this run): {uploaded}")
    if previewed:
        print(f"uploaded as sub-50MiB preview re-encodes ({len(previewed)}): "
              + ", ".join(previewed))

    # ---- 2. merge generator metadata + build samples ----
    def samples_for(gen):
        stem = gen["name"][:-3] if gen["name"].endswith(".py") else gen["name"]
        globs = gen.get("sample_globs") or []
        matched, seen = [], set()
        for r in render_index:
            hit = (r.get("generator") == stem) or any(
                fnmatch.fnmatch(r["rel_path"], g) for g in globs
            )
            if hit and r["storage_path"] not in seen:
                seen.add(r["storage_path"])
                matched.append(r)
        matched.sort(key=lambda r: (0 if r.get("kind") == "video" else 1,
                                    r["storage_path"]))
        return [
            {"storage_path": r["storage_path"], "title": r["title"],
             "kind": r.get("kind")}
            for r in matched[:4]
        ]

    updated = 0
    for gen in gen_meta:
        fields = {
            "category": gen.get("category") or "uncategorized",
            "what_it_does": gen.get("what_it_does") or "",
            "inputs": gen.get("inputs") or [],
            "outputs": gen.get("outputs") or [],
            "channels": gen.get("channels") or [],
            "samples": samples_for(gen),
        }
        if args.dry_run:
            print(f"  DRY: would patch {gen['name']} "
                  f"({fields['category']}, {len(fields['samples'])} samples)")
            updated += 1
            continue
        res = api.patch_generator(gen["name"], fields)
        if res:
            updated += 1
        else:
            print(f"  WARN: no factory_generators row named {gen['name']!r}; "
                  f"skipped (PATCH matched 0 rows)")
    print(f"generators updated: {updated}")

    # ---- 3. event log ----
    total_hist = len(render_index)
    msg = f"{total_hist} historical renders + {updated} generator cards imported"
    if not args.dry_run:
        api.insert("factory_events", {
            "kind": "backfill",
            "message": msg,
            "meta": {"uploaded_this_run": uploaded,
                     "historical_total": total_hist,
                     "generators_updated": updated,
                     "preview_reencodes": previewed},
        })
    print(f"event logged: {msg}")
    print(json.dumps({"uploaded": uploaded, "historical_total": total_hist,
                      "generators_updated": updated}))


if __name__ == "__main__":
    main()
