#!/usr/bin/env python3
"""heygen_pool_sync — make the LIVE HeyGen account the source of truth for which
photo-avatar ids still render.

Why this exists: `.heygen_pool.json` is written by hand at registration time and
goes stale the moment an avatar is added or freed elsewhere. On 2026-08-18 that
staleness made the asset library mark outfit_12 (registered 2026-08-16, very much
alive) as "freed — won't render", which blocked the newest host in the composer.
A cache that silently disagrees with the server is worse than no cache.

Run it before composing/producing, or any time the host list looks wrong:
    python3 scripts/heygen_pool_sync.py            # report + refresh pool + DB
    python3 scripts/heygen_pool_sync.py --dry-run  # report only
"""
import argparse, json, os, sys, urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
CH = os.path.join(REPO, "channels", "claude-tricks")
LIB = os.path.join(CH, "assets", "character", "host_library")
POOL = os.path.join(LIB, ".heygen_pool.json")


def api_key():
    for p in (os.path.join(REPO, ".env"), os.path.join(CH, ".env")):
        if os.path.exists(p):
            for line in open(p):
                if line.strip().startswith("HEYGEN_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("HEYGEN_API_KEY not found in .env")


def live_avatars(key):
    req = urllib.request.Request("https://api.heygen.com/v2/avatar_group.list",
                                 headers={"x-api-key": key})
    d = json.loads(urllib.request.urlopen(req, timeout=30).read())
    return (d.get("data") or {}).get("avatar_group_list") or []


def ids_on_disk():
    """{outfit_dir: {role: id}} from .heygen_photo_id_* files and shot_map.json."""
    out = {}
    if not os.path.isdir(LIB):
        return out
    for d in sorted(os.listdir(LIB)):
        p = os.path.join(LIB, d)
        if not os.path.isdir(p):
            continue
        roles = {}
        for fn in os.listdir(p):
            if fn.startswith(".heygen_photo_id"):
                role = fn.replace(".heygen_photo_id", "").lstrip("_") or "default"
                try:
                    roles[role] = open(os.path.join(p, fn)).read().strip()
                except OSError:
                    pass
        sm = os.path.join(p, "shot_map.json")
        if os.path.exists(sm):
            try:
                for shot, cfg in (json.load(open(sm)).get("shots") or {}).items():
                    tid = (cfg or {}).get("heygen_talking_photo_id")
                    if tid:
                        roles[shot] = tid
            except Exception:
                pass
        if roles:
            out[d] = roles
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    groups = live_avatars(api_key())
    live_ids = {g["id"]: g for g in groups}
    print(f">> LIVE on HeyGen: {len(live_ids)} avatar(s)")
    for gid, g in live_ids.items():
        print(f"   {gid}  {g.get('name','')!r:32s} {g.get('group_type','')}")

    disk = ids_on_disk()
    print(f"\n>> outfits declaring ids on disk: {len(disk)}")
    alive_rows, report = [], []
    for outfit, roles in disk.items():
        states = {r: ("live" if i in live_ids else "freed") for r, i in roles.items()}
        n_live = sum(1 for s in states.values() if s == "live")
        verdict = "RENDERS" if n_live else "DEAD"
        report.append((outfit, verdict, states))
        print(f"   {outfit:32s} {verdict:8s} " +
              " ".join(f"{r}={s}" for r, s in sorted(states.items())))
        for r, i in roles.items():
            if i in live_ids:
                alive_rows.append({"heygen_id": i, "outfit": outfit, "role": r, "ts": 0})

    # avatars on the server that no outfit on disk claims
    claimed = {i for roles in disk.values() for i in roles.values()}
    orphans = [g for gid, g in live_ids.items() if gid not in claimed]
    if orphans:
        print("\n>> LIVE but not claimed by any outfit on disk:")
        for g in orphans:
            print(f"   {g['id']}  {g.get('name','')!r} ({g.get('group_type','')})")

    if a.dry_run:
        print("\n>> dry-run — nothing written")
        return

    with open(POOL, "w") as f:
        json.dump(alive_rows, f, indent=1)
    print(f"\n>> pool refreshed from the server: {POOL} ({len(alive_rows)} live id(s))")

    # push the same truth into the asset rows the composer reads
    try:
        import factory_worker as fw
        env = fw.load_env()
        supa = fw.Supa(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
        rows = supa.select("factory_asset_versions",
                           "channel_key=eq.claude-tricks&asset_type=eq.host_outfit"
                           "&select=id,version,meta")
        pool_live = sorted(live_ids.keys())
        n = 0
        for row in rows:
            meta = row.get("meta") or {}
            ref = (meta.get("build_ref") or "")
            outfit = ref.rsplit("/", 1)[-1]
            roles = disk.get(outfit)
            if not roles:
                continue
            hg = {r: i for r, i in roles.items()}
            for r, i in roles.items():
                hg[f"{r}_state"] = "live" if i in live_ids else "freed"
            hg["pool_live"] = pool_live
            meta["heygen"] = hg
            supa.patch("factory_asset_versions", f"id=eq.{row['id']}", {"meta": meta})
            n += 1
        print(f">> updated meta.heygen on {n} host_outfit revision(s) from live truth")
    except Exception as e:
        print(f"!! DB not updated ({e}) — pool file is still refreshed")


if __name__ == "__main__":
    main()
