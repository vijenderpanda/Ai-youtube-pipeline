#!/usr/bin/env python3
"""regen_asset — make a NEW asset revision derived from an existing one.

The composer's swap drawer is where you notice "this is close, but the question
should be different" — so that is where generating the next revision belongs.
This runs the slot's real generator, uploads the result, and registers it as a
CANDIDATE whose parent_version_id is the revision you started from, so the
lineage rail shows where it came from. It never locks anything: a candidate has
to be chosen deliberately.

Designed to run as an existing `shell_script` worker job (meta.script_path =
'scripts/regen_asset.py'), so no new job type and no worker restart.

  python3 scripts/regen_asset.py --asset-type outro_card_gen \\
      --from-version <uuid> --params '{"q":"What would you build first?","pill":"Comment it below"}'
"""
import argparse, json, os, subprocess, sys, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
import factory_worker as fw

CH_DIR = os.path.join(REPO, "channels", "claude-tricks")

# Which slots can actually be regenerated today, and by what. Being explicit
# beats a generic "generate" button that fails for two thirds of the library.
GENERATORS = {
    "outro_card_gen": {
        "script": os.path.join(CH_DIR, "gen_outro_card.py"),
        "params": ["q", "pill"],          # --q "line one|line two"  --pill "Comment it below"
        "ext": "mp4",
        "free": True,                      # PIL + ffmpeg, no API spend
    },
}


def die(msg):
    print(f"!! {msg}", file=sys.stderr)
    sys.exit(2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", default="claude-tricks")
    ap.add_argument("--asset-type", required=True)
    ap.add_argument("--from-version", help="factory_asset_versions.id to derive from")
    ap.add_argument("--params", default="{}", help="JSON of generator params")
    ap.add_argument("--label", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    gen = GENERATORS.get(a.asset_type)
    if not gen:
        die(f"'{a.asset_type}' has no wired generator. Generatable today: "
            f"{', '.join(sorted(GENERATORS)) or 'none'}")
    try:
        params = json.loads(a.params or "{}")
    except json.JSONDecodeError as e:
        die(f"--params is not valid JSON: {e}")

    env = fw.load_env()
    supa = fw.Supa(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])

    rows = supa.select("factory_asset_versions",
                       f"channel_key=eq.{a.channel}&asset_type=eq.{a.asset_type}"
                       f"&select=id,version,label,meta&order=version.desc")
    if not rows:
        die(f"no existing {a.asset_type} revisions for {a.channel}")
    parent = next((r for r in rows if r["id"] == a.from_version), None) if a.from_version else None
    nxt = max(r["version"] for r in rows) + 1

    # inherit the parent's params so "change one thing" really is one thing
    inherited = dict(((parent or {}).get("meta") or {}).get("gen_params") or {})
    inherited.update({k: v for k, v in params.items() if v not in (None, "")})
    missing = [p for p in gen["params"] if not inherited.get(p)]
    if missing:
        die(f"missing generator param(s): {', '.join(missing)}")

    rel = f"_regen/{a.asset_type}_v{nxt}_{int(time.time())}.{gen['ext']}"
    out = os.path.join(CH_DIR, "assets", rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cmd = ["python3", gen["script"], "--out", os.path.join("assets", rel)]
    for p in gen["params"]:
        cmd += [f"--{p}", str(inherited[p])]
    print(">> " + " ".join(cmd), flush=True)
    if a.dry_run:
        print(">> dry-run — generator not executed"); return

    r = subprocess.run(cmd, cwd=CH_DIR)
    if r.returncode != 0 or not os.path.exists(out):
        die(f"generator failed (exit {r.returncode}) — nothing registered")

    store = f"{a.channel}/assets/{rel}"
    supa.upload(store, open(out, "rb").read(), "video/mp4")
    thumb = None
    pj = out.rsplit(".", 1)[0] + ".jpg"
    subprocess.run(["ffmpeg", "-v", "error", "-ss", "0.4", "-i", out, "-frames:v", "1",
                    "-q:v", "4", "-vf", "scale=640:-2", pj, "-y"], check=False)
    if os.path.exists(pj):
        thumb = f"{a.channel}/assets/_thumbs/{a.asset_type}/regen_v{nxt}.jpg"
        supa.upload(thumb, open(pj, "rb").read(), "image/jpeg")

    row = {
        "channel_key": a.channel, "asset_type": a.asset_type, "version": nxt,
        "label": a.label or f"regenerated from v{(parent or {}).get('version', '?')}",
        "storage_path": store, "thumb_path": thumb,
        "status": "candidate",              # never auto-locked — you choose it
        "source": "regeneration",
        "parent_version_id": (parent or {}).get("id"),
        "meta": {"build_ref": rel, "gen_params": inherited,
                 "derived_from_version": (parent or {}).get("version")},
    }
    supa.insert("factory_asset_versions", [row],
                on_conflict="channel_key,asset_type,version", resolution="merge-duplicates")
    print(f">> registered {a.asset_type} v{nxt} (candidate, from v{(parent or {}).get('version','?')})")
    print(f">> {store}")


if __name__ == "__main__":
    main()
