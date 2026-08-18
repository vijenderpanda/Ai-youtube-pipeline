#!/usr/bin/env python3
"""sync_assets_supabase — back up production media (which is gitignored per the
media-offload policy) to the `factory-renders` Supabase storage bucket, so the
exact assets persist beyond T5/YouTube and survive a move to a different Claude
account. Also seeds the Studio asset-versioning store (docs/STUDIO-ASSET-VERSIONING.md).

Uploads (x-upsert, so re-runs overwrite) each file to:
    <channel>/assets/<prefix>/<filename>

Usage:
  python3 scripts/sync_assets_supabase.py --channel claude-tricks --prefix ep_artifacts \\
      --dir channels/claude-tricks/assets/ep_artifacts \\
      --files channels/claude-tricks/renders/ep_artifacts_v2_outro.mp4 \\
              channels/claude-tricks/renders/thumb_ep_artifacts.jpg
"""
import argparse, mimetypes, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
import factory_worker as fw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True)
    ap.add_argument("--prefix", required=True, help="storage subpath under <channel>/assets/")
    ap.add_argument("--files", nargs="*", default=[], help="explicit files to upload")
    ap.add_argument("--dir", help="also upload every file directly in this dir (non-recursive)")
    a = ap.parse_args()

    env = fw.load_env()
    supa = fw.Supa(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])

    files = list(a.files)
    if a.dir:
        d = a.dir if os.path.isabs(a.dir) else os.path.join(REPO, a.dir)
        for fn in sorted(os.listdir(d)):
            p = os.path.join(d, fn)
            if os.path.isfile(p) and not fn.startswith("."):
                files.append(p)

    ok = 0
    total_kb = 0
    for f in files:
        path = f if os.path.isabs(f) else os.path.join(REPO, f)
        if not os.path.isfile(path):
            print(f"!! skip (not a file): {f}")
            continue
        name = os.path.basename(path)
        storage = f"{a.channel}/assets/{a.prefix}/{name}"
        ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
        with open(path, "rb") as fh:
            supa.upload(storage, fh.read(), ctype)
        kb = os.path.getsize(path) // 1024
        total_kb += kb
        print(f">> {storage}  ({kb} KB, {ctype})")
        ok += 1

    print(f">> DONE — {ok} file(s), {total_kb // 1024} MB synced to the factory-renders bucket "
          f"under {a.channel}/assets/{a.prefix}/")


if __name__ == "__main__":
    main()
