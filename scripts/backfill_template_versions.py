#!/usr/bin/env python3
"""backfill_template_versions — give every live template a composed CAST that is
identical to what it already renders (Phase 4, docs/STUDIO-ASSET-VERSIONING.md).

For each factory_channels row with a `template`, create ONE
factory_template_versions row seeded from that channel's current
factory_asset_locks, freeze it (status='locked' + composition jsonb with each
pick's build_ref COPIED), and point factory_templates.active_version_id at it.

Nothing changes behaviorally — the composition EQUALS the locks — which is the
safest possible way to prove the new resolution layer in build_ep_v2
(_bind_template_version / _tpl_lookup) before anyone swaps a slot. Verify with:

    python3 channels/claude-tricks/build_ep_v2.py --ep 13 --dry
    # ">> template version: <key> v1 -> [...]" and the same refs as
    # ">> asset locks resolved: {...}"

Idempotent: a template that already has any version is SKIPPED (never fork on
top of an operator's work). --dry-run prints the plan and writes nothing.
"""
import os
import sys
import argparse
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
import factory_worker as fw  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
    ap.add_argument("--channel", help="limit to one channel key")
    a = ap.parse_args()

    env = fw.load_env()
    supa = fw.Supa(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])

    channels = supa.select("factory_channels", "select=key,template")
    if a.channel:
        channels = [c for c in channels if c.get("key") == a.channel]
    made = 0

    for ch in channels:
        ckey, tkey = ch.get("key"), ch.get("template")
        if not tkey:
            continue
        tpl = supa.select("factory_templates", f"key=eq.{tkey}&select=key,active_version_id")
        if not tpl:
            print(f"-- {ckey}: template {tkey!r} not in factory_templates; skip")
            continue
        existing = supa.select("factory_template_versions",
                               f"template_key=eq.{tkey}&select=id,version,status")
        if existing:
            print(f"-- {tkey}: already has {len(existing)} version(s); skip")
            continue

        locks = supa.select("factory_asset_locks",
                            f"channel_key=eq.{ckey}&select=asset_type,locked_version_id")
        ids = [l["locked_version_id"] for l in locks if l.get("locked_version_id")]
        if not ids:
            print(f"-- {ckey}/{tkey}: no locked assets; skip")
            continue
        vers = supa.select("factory_asset_versions",
                           f"id=in.({','.join(ids)})"
                           "&select=id,asset_type,version,label,status,storage_path,thumb_path,meta")
        by_id = {v["id"]: v for v in vers}

        composition, slots, bad = {}, [], []
        for l in locks:
            v = by_id.get(l.get("locked_version_id"))
            if not v:
                continue
            build_ref = (v.get("meta") or {}).get("build_ref")
            if not build_ref:
                bad.append(f"{v['asset_type']} v{v['version']} (no meta.build_ref)")
                continue
            composition[v["asset_type"]] = {
                "version_id": v["id"], "version": v["version"], "build_ref": build_ref,
                "label": v.get("label") or "", "storage_path": v.get("storage_path"),
                "thumb_path": v.get("thumb_path"),
            }
            slots.append({"asset_type": v["asset_type"], "asset_version_id": v["id"],
                          "position": 0, "note": "backfilled from the channel lock"})
        if bad:
            print(f"!! {tkey}: skipping unresolvable slots — {', '.join(bad)}")
        if not composition:
            print(f"-- {ckey}/{tkey}: nothing resolvable; skip")
            continue

        print(f">> {tkey} v1 ({ckey}): {len(composition)} slots — "
              f"{', '.join(sorted(composition))}")
        if a.dry_run:
            continue

        now = datetime.now(timezone.utc).isoformat()
        created = supa.insert_returning("factory_template_versions", [{
            "template_key": tkey, "channel_key": ckey, "version": 1,
            "label": "Baseline — the channel locks as of backfill",
            "notes": "Composition EQUALS factory_asset_locks; renders identically to before Phase 4.",
            "status": "locked", "composition": composition, "locked_at": now,
            "meta": {"source": "backfill_template_versions"},
        }])
        tv_id = created[0]["id"]
        supa.insert("factory_template_assets",
                    [dict(s, template_version_id=tv_id) for s in slots])
        supa.patch("factory_templates", f"key=eq.{tkey}", {"active_version_id": tv_id})
        print(f"   locked + active: {tv_id}")
        made += 1

    print(f">> DONE — {made} template version(s) created"
          + (" (dry run: nothing written)" if a.dry_run else ""))


if __name__ == "__main__":
    main()
