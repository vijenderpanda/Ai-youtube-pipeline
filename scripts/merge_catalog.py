#!/usr/bin/env python3
"""Merge the historical catalog (contributors, tags, local paths, upload defaults)
into the factory Supabase (v4 schema). Idempotent / re-runnable:

  1. contributors_tags.json contributors[] -> factory_render_contributors
     (resolved via factory_renders.storage_path; existing render+generator pairs
     are skipped; high AND medium confidence entries are included)
  2. contributors_tags.json generator_tags -> factory_generators.tags/scope
     (PATCH by name; generators missing from the table are inserted first so
     contributor rows never dangle)
  3. render_inventory.json finals[].path -> factory_renders.local_path
     (storage_path is reconstructed as <channel_key>/historical/<safe filename>)
  4. contributors_tags.json upload_defaults -> factory_channels.brand
     (merged under brand['upload_defaults'], other brand keys preserved)
     + ensure factory_settings auto_sync rows exist (insert-if-missing only)
  5. one factory_events row (kind='catalog') summarizing what changed

Usage:
  python3 scripts/merge_catalog.py --contributors <contributors_tags.json> \
      --inventory <render_inventory.json> [--dry-run]
"""
import argparse
import json
import os
import re
import sys

import requests

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(REPO_ROOT, "secrets", "factory.env")

AUTO_SYNC_DEFAULTS = {
    "auto_sync_hour": "07:30",
    "auto_sync_tz": "Asia/Kolkata",
}

# category + path hints for generators that exist as scripts but have no
# factory_generators row yet (all claude-tricks channel-local scripts).
NEW_GENERATOR_CATEGORY = {
    "build_ep.py": "assembly",
    "build_ep_v2.py": "assembly",
    "make_art.py": "art-thumbnails",
    "gen_outro.py": "art-thumbnails",
    "gen_ep09_mock.py": "art-thumbnails",
    "gen_ep11_card.py": "art-thumbnails",
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
    # must mirror backfill_renders.py so storage paths reconstruct identically
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name.strip("._") or "file"


class Api:
    def __init__(self, url, key):
        self.rest = url.rstrip("/") + "/rest/v1"
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

    def patch(self, table, params, fields):
        r = self.s.patch(
            f"{self.rest}/{table}", params=params, json=fields,
            headers={"Prefer": "return=representation"}, timeout=60,
        )
        r.raise_for_status()
        return r.json()


def resolve_generator_name(name, db_names):
    """Map a bare generator key (e.g. 'assemble_video') to its DB name."""
    if name in db_names:
        return name
    if f"{name}.py" in db_names:
        return f"{name}.py"
    return f"{name}.py"  # convention: table stores script filenames


def guess_generator_path(db_name):
    for rel in (f"scripts/{db_name}", f"channels/claude-tricks/{db_name}"):
        if os.path.exists(os.path.join(REPO_ROOT, rel)):
            return rel
    return None


def scope_channels(scope):
    if scope and scope.startswith("single:"):
        return [scope.split(":", 1)[1]]
    return ["all"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contributors", required=True, help="contributors_tags.json")
    ap.add_argument("--inventory", required=True, help="render_inventory.json")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    env = load_env(ENV_PATH)
    api = Api(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
    dry = args.dry_run

    cat = json.load(open(args.contributors))
    inv = json.load(open(args.inventory))
    contributors = cat.get("contributors", [])
    generator_tags = cat.get("generator_tags", {})
    upload_defaults = cat.get("upload_defaults", {})
    finals = inv.get("finals", [])

    renders = api.get_all(
        "factory_renders",
        {"select": "id,storage_path,local_path,channel_key"},
    )
    by_storage = {r["storage_path"]: r for r in renders}
    gen_rows = api.get_all("factory_generators", {"select": "name"})
    db_gen_names = {g["name"] for g in gen_rows}
    print(f"db: {len(renders)} renders, {len(db_gen_names)} generators")

    notes = []

    # ---- 2a. insert generators referenced by the catalog but absent in DB ----
    generators_inserted = 0
    for key in sorted(generator_tags):
        db_name = resolve_generator_name(key, db_gen_names)
        if db_name in db_gen_names:
            continue
        meta = generator_tags[key]
        row = {
            "name": db_name,
            "path": guess_generator_path(db_name),
            "category": NEW_GENERATOR_CATEGORY.get(db_name),
            "channels": scope_channels(meta.get("scope")),
            "tags": meta.get("tags", []),
            "scope": meta.get("scope"),
        }
        print(f"insert generator {db_name} (scope={row['scope']})")
        if not dry:
            api.insert("factory_generators", row)
        db_gen_names.add(db_name)
        generators_inserted += 1

    # ---- 2b. PATCH tags/scope on every generator in generator_tags ----
    generators_tagged = 0
    for key, meta in sorted(generator_tags.items()):
        db_name = resolve_generator_name(key, db_gen_names)
        fields = {"tags": meta.get("tags", []), "scope": meta.get("scope")}
        if not dry:
            out = api.patch("factory_generators", {"name": f"eq.{db_name}"}, fields)
            if not out:
                notes.append(f"generator_tags: no row matched {db_name}")
                continue
        generators_tagged += 1

    # ---- 1. contributors -> factory_render_contributors ----
    existing = api.get_all(
        "factory_render_contributors", {"select": "render_id,generator"}
    )
    existing_pairs = {(e["render_id"], e["generator"]) for e in existing}
    contributors_inserted = 0
    contributors_skipped = 0
    for c in contributors:
        if c.get("confidence") not in ("high", "medium"):
            contributors_skipped += 1
            continue
        render = by_storage.get(c["storage_path"])
        if not render:
            notes.append(f"contributor: no render for {c['storage_path']}")
            continue
        db_gen = resolve_generator_name(c["generator"], db_gen_names)
        if db_gen not in db_gen_names:
            notes.append(f"contributor: unknown generator {c['generator']}")
            continue
        pair = (render["id"], db_gen)
        if pair in existing_pairs:
            contributors_skipped += 1
            continue
        if not dry:
            api.insert(
                "factory_render_contributors",
                {"render_id": render["id"], "generator": db_gen,
                 "role": c.get("role")},
            )
        existing_pairs.add(pair)
        contributors_inserted += 1

    # ---- 3. local_path backfill on historical renders ----
    renders_localpath_set = 0
    for f in finals:
        storage = f"{f['channel_key']}/historical/{safe_filename(os.path.basename(f['path']))}"
        render = by_storage.get(storage)
        if not render:
            notes.append(f"local_path: no render for {storage}")
            continue
        if render.get("local_path") == f["path"]:
            continue
        if not dry:
            api.patch(
                "factory_renders", {"id": f"eq.{render['id']}"},
                {"local_path": f["path"]},
            )
        render["local_path"] = f["path"]
        renders_localpath_set += 1

    # ---- 4a. upload_defaults -> factory_channels.brand (merge, no clobber) ----
    channels = api.get_all("factory_channels", {"select": "key,brand"})
    brand_by_key = {c["key"]: (c.get("brand") or {}) for c in channels}
    channels_branded = 0
    for ch_key, defaults in upload_defaults.items():
        if ch_key not in brand_by_key:
            notes.append(f"upload_defaults: no factory_channels row for {ch_key}")
            continue
        brand = dict(brand_by_key[ch_key])
        if brand.get("upload_defaults") == defaults:
            continue
        brand["upload_defaults"] = defaults
        if not dry:
            api.patch("factory_channels", {"key": f"eq.{ch_key}"}, {"brand": brand})
        channels_branded += 1

    # ---- 4b. ensure factory_settings auto_sync rows exist ----
    settings = api.get_all("factory_settings", {"select": "key"})
    have = {s["key"] for s in settings}
    settings_added = 0
    for k, v in AUTO_SYNC_DEFAULTS.items():
        if k in have:
            continue
        if not dry:
            api.insert("factory_settings", {"key": k, "value": v})
        settings_added += 1

    # ---- 5. factory_events log row ----
    message = (
        f"catalog merge: {contributors_inserted} contributor links inserted "
        f"({contributors_skipped} already present/skipped), "
        f"{generators_tagged} generators tagged ({generators_inserted} new rows), "
        f"{renders_localpath_set} renders got local_path, "
        f"{channels_branded} channels got upload_defaults, "
        f"{settings_added} auto_sync settings added"
    )
    if not dry:
        api.insert("factory_events", {
            "kind": "catalog",
            "message": message,
            "meta": {
                "contributors_inserted": contributors_inserted,
                "contributors_skipped": contributors_skipped,
                "generators_tagged": generators_tagged,
                "generators_inserted": generators_inserted,
                "renders_localpath_set": renders_localpath_set,
                "channels_branded": channels_branded,
                "settings_added": settings_added,
            },
        })
    print(message)
    for n in notes:
        print("NOTE:", n)

    # ---- verify ----
    contrib_total = len(api.get_all(
        "factory_render_contributors", {"select": "render_id"}))
    gens = api.get_all("factory_generators", {"select": "name,scope"})
    gens_scoped = sum(1 for g in gens
                      if g.get("scope") and g["scope"] != "unknown")
    rends = api.get_all("factory_renders", {"select": "id,local_path"})
    rends_local = sum(1 for r in rends if r.get("local_path"))
    summary = {
        "contributors_inserted": contributors_inserted,
        "generators_tagged": generators_tagged,
        "renders_localpath": rends_local,
        "verify": {
            "contributors_total": contrib_total,
            "generators_scope_set": gens_scoped,
            "generators_total": len(gens),
            "renders_with_local_path": rends_local,
            "renders_total": len(rends),
        },
        "notes": notes,
    }
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
