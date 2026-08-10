#!/usr/bin/env python3
"""push_asset — publish one produce_preview-generated asset to the factory DB
so Studio's board can render it in real time (v16).

Called by Claude inside a produce_preview session after each asset is written
to disk. Wraps the factory-api `add_asset` action. Zero-op if the asset was
already pushed (dedup by calendar_id + asset_key).

Usage (inside produce_preview's Claude Bash tool):

  python3 scripts/push_asset.py \\
    --calendar-id <uuid> \\
    --asset-key hook_frame_zero \\
    --file channels/claude-tricks/assets/ep9/hook_frame_zero.jpg \\
    --kind image \\
    --group thumbnail

Exit codes:
  0 — pushed (or already recorded — dedup)
  1 — bad args or file missing
  2 — API error (network / auth / server)
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
API_BASE = "https://xfqyovimnqdghiekicqr.supabase.co/functions/v1/factory-api"
ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhmcXlvdmltbnFkZ2hpZWtpY3FyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExMTIyMzksImV4cCI6MjA5NjY4ODIzOX0."
    "CA_znXaUlgmChBLFSE_eRZ4X-xg2WhwIiZmxwXrZRlM"
)

VALID_KINDS = ("image", "video", "audio", "text", "other")
VALID_GROUPS = ("thumbnail", "scene", "clip", "audio", "bookend", "overlay", "other")


def load_factory_token():
    """Read FACTORY_TOKEN from secrets/factory.env. Same source the webapp uses."""
    env_path = os.path.join(REPO, "secrets", "factory.env")
    if not os.path.exists(env_path):
        sys.exit(f"!! secrets/factory.env not found at {env_path}")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("FACTORY_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("!! FACTORY_TOKEN not present in secrets/factory.env")


def probe_duration(path):
    """seconds via ffprobe, or None. Only used for video/audio."""
    try:
        import subprocess
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=15)
        return round(float(r.stdout.strip()), 2) if r.returncode == 0 else None
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(
        description="Publish one asset from a produce_preview session to factory-api")
    ap.add_argument("--calendar-id", required=True,
                    help="factory_calendar row uuid (from job.meta.calendar_id)")
    ap.add_argument("--asset-key", required=True,
                    help="stable slug: hook_frame_zero, scene_02_still, vo_master, thumbnail, etc.")
    ap.add_argument("--file", required=True,
                    help="path to the generated file (absolute or repo-relative)")
    ap.add_argument("--kind", required=True, choices=VALID_KINDS,
                    help="media kind")
    ap.add_argument("--group", default="other", choices=VALID_GROUPS,
                    help="board grouping (default: other)")
    ap.add_argument("--title", default=None,
                    help="human title for the Studio filmstrip (default: asset_key)")
    a = ap.parse_args()

    # resolve local_path
    fpath = a.file
    if not os.path.isabs(fpath):
        fpath = os.path.join(REPO, fpath)
    if not os.path.exists(fpath):
        sys.exit(f"!! file missing: {fpath}")

    size = os.path.getsize(fpath)
    dur = probe_duration(fpath) if a.kind in ("video", "audio") else None

    payload = {
        "action": "add_asset",
        "calendar_id": a.calendar_id,
        "asset_key": a.asset_key,
        "group_key": a.group,
        "kind": a.kind,
        "filename": os.path.basename(fpath),
        "local_path": fpath,
        "size_bytes": size,
        "duration_s": dur,
        "title": a.title or a.asset_key,
    }

    token = load_factory_token()
    req = urllib.request.Request(
        API_BASE,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": "Bearer " + ANON_KEY,
            "x-factory-token": token,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"!! HTTP {e.code}: {e.read().decode()[:400]}", file=sys.stderr)
        sys.exit(2)
    except urllib.error.URLError as e:
        print(f"!! network error: {e}", file=sys.stderr)
        sys.exit(2)

    asset = resp.get("asset") or {}
    note = resp.get("note") or ""
    print(f">> pushed asset '{a.asset_key}' -> id={asset.get('id')}"
          + (f"  ({note})" if note else ""))


if __name__ == "__main__":
    main()
