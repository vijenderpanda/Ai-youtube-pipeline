#!/usr/bin/env python3
"""ingest_asset_library — register EVERY real revision of every brand-asset slot.

    python3 scripts/ingest_asset_library.py --channel claude-tricks \\
            [--tier preview|full] [--dry-run] [--rebuild-manifest]

The Assets board used to show 9 hand-registered rows all at version=1 (see
scripts/backfill_asset_versions.py). This walks the actual disk and registers each real
revision as a VERSION of its slot (scripts/asset_catalog.py), with a deterministic version
number, lineage, honest status, and a preview thumbnail the browser can decode.

SOURCE RESOLUTION
  LOCAL = channels/<ch>/assets/            (repo working tree)
  T5    = /Volumes/Samsung_T5/Ai-youtube-pipeline-media-backup/channels/<ch>/assets/
Most of the media was offloaded to the T5 (see the media-offload policy), so a run without
T5 mounted would register a third of the library as missing -> we ABORT instead.
`--dry-run` prints the plan and is allowed without T5.

READ-ONLY ON DISK. This script never deletes, moves or rewrites a source file. It only
reads bytes, writes derived thumbnails into a scratch dir, uploads to the factory-renders
bucket, and writes the manifest.

MANIFEST PINNING (the single biggest correctness risk)
  channels/<ch>/assets/ASSET-MANIFEST.json pins identity -> version. On every run, keys
  already in the manifest KEEP their version; only new keys get new numbers. Without it, a
  re-run with T5 unmounted (or one touched file) renumbers the whole board and orphans
  every downstream reference. `--rebuild-manifest` is the explicit, destructive escape.
  Identity key is the sha1 of the bytes for file-unit slots, "dir:<relpath>" for
  directory-unit slots (a host outfit is a directory of shots), "code:<build_ref>" for the
  id/rule/code slots that have no bytes at all.

LOCKS ARE SACRED
  build_ep_v2.py:1294 `_lock_lookup()` resolves `meta.build_ref` of the LOCKED version at
  every build. Renumbering moves content between version numbers, so after the upsert this
  script RE-POINTS each factory_asset_locks row at whichever new row carries the SAME
  build_ref it resolved to before, verifies it, and prints the before/after. If any locked
  build_ref cannot be found in the new rows, the lock is left untouched and the run is
  reported as needing attention.
"""
import argparse
import fnmatch
import glob
import hashlib
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
import asset_catalog as cat  # noqa: E402
import factory_worker as fw  # noqa: E402

T5_ROOT = "/Volumes/Samsung_T5/Ai-youtube-pipeline-media-backup"
THUMB_W = 640
OPTIONAL_COLS = ("retired_at", "generator", "job_id", "storage_state")


# =======================================================================================
# small utilities
# =======================================================================================
def sha1_file(path):
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def iso(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")


def hidden(rel):
    return any(seg.startswith(".") for seg in rel.split(os.sep))


def run_ffmpeg(args):
    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + args,
                       check=True, capture_output=True)
        return True
    except Exception as e:
        print(f"   !! ffmpeg failed: {e}")
        return False


# =======================================================================================
# discovery
# =======================================================================================
class Rev:
    """One revision of one slot — the thing that becomes a factory_asset_versions row."""

    def __init__(self, asset_type, key, rel_path, root_kind):
        self.asset_type = asset_type
        self.key = key                 # manifest identity (stable across runs)
        self.rel_path = rel_path       # path under the slot's root
        self.root_kind = root_kind     # "assets" | "channel"
        self.src_local = None
        self.src_t5 = None
        self.sha1 = None
        self.bytes = 0
        self.mtime = 0.0
        self.variants = []
        self.extra = {}
        self.version = None
        self.storage_path = None
        self.thumb_path = None
        self.status = "candidate"
        self.retired_reason = None
        self.parent_key = None
        self.canon_disks = None        # dir-unit: where the CANONICAL still actually is

    @property
    def src(self):
        return self.src_local or self.src_t5

    @property
    def source_disk(self):
        """Where the REVISION'S BYTES are — not merely where a folder exists. An outfit
        directory can be present in the repo while every shot in it is T5-only."""
        if self.canon_disks is not None:
            return list(self.canon_disks)
        return [d for d, p in (("local", self.src_local), ("t5", self.src_t5)) if p]

    @property
    def storage_state(self):
        ds = self.source_disk
        if not ds:
            return None
        return "both" if len(ds) == 2 else ds[0]

    @property
    def build_ref(self):
        return self.rel_path


def _roots(channel, dry):
    """[(disk, assets_root, channel_root)] — LOCAL first so its bytes win ties."""
    out = [("local", os.path.join(REPO, "channels", channel, "assets"),
            os.path.join(REPO, "channels", channel))]
    t5_ch = os.path.join(T5_ROOT, "channels", channel)
    if os.path.isdir(t5_ch):
        out.append(("t5", os.path.join(t5_ch, "assets"), t5_ch))
    elif not dry:
        sys.exit(f"!! ABORT — T5 not mounted at {T5_ROOT}. Most of this channel's media "
                 f"lives ONLY there; a run without it would register the library as "
                 f"missing. Mount the drive, or use --dry-run.")
    else:
        print(f"!! T5 not mounted ({T5_ROOT}) — dry-run plan will be LOCAL-only.")
    return out


def _matches(rel, pats):
    return any(fnmatch.fnmatch(rel, p) for p in (pats or []))


def discover(channel, dry):
    """-> {asset_type: [Rev]}  (unordered; versions assigned later)"""
    roots = _roots(channel, dry)
    found = {}

    for atype in cat.ordered_slots():
        spec = cat.discover_of(atype)
        slot = cat.SLOTS[atype]
        revs = {}

        if spec is None:  # id / rule / code slots — no bytes on disk
            for s in slot.get("static", []):
                r = Rev(atype, "code:" + s["build_ref"], s["build_ref"], "static")
                r.rel_path = s["build_ref"]
                r.extra = {k: v for k, v in s.items() if k not in ("build_ref", "label")}
                r.extra["label"] = s["label"]
                r.mtime = 0.0
                revs[r.key] = r
            found[atype] = list(revs.values())
            continue

        for disk, aroot, croot in roots:
            base = aroot if spec["root"] == "assets" else croot
            if not os.path.isdir(base):
                continue
            for pat in spec["globs"]:
                for hit in glob.glob(os.path.join(base, pat)):
                    rel = os.path.relpath(hit, base)
                    if hidden(rel) or _matches(rel, spec.get("exclude")):
                        continue

                    if spec["unit"] == "dir":
                        if not os.path.isdir(hit):
                            continue
                        _merge_dir_rev(revs, atype, rel, hit, disk, spec)
                    else:
                        if not os.path.isfile(hit):
                            continue
                        exts = spec.get("exts")
                        if exts and not hit.lower().endswith(tuple(exts)):
                            continue
                        _merge_file_rev(revs, atype, rel, hit, disk, spec)

        found[atype] = list(revs.values())
    return found


def _merge_file_rev(revs, atype, rel, abs_path, disk, spec):
    sha = sha1_file(abs_path)
    st = os.stat(abs_path)
    r = revs.get(sha)
    if r is None:
        r = Rev(atype, sha, rel.replace(os.sep, "/"), spec["root"])
        r.sha1 = sha
        r.bytes = st.st_size
        r.mtime = st.st_mtime
        revs[sha] = r
    # earliest mtime across copies = when the bytes were actually made (a restore from T5
    # does not preserve mtime, so LOCAL can look "newer" than the original)
    r.mtime = min(r.mtime, st.st_mtime)
    setattr(r, "src_" + disk, abs_path)
    if rel.replace(os.sep, "/") != r.rel_path:
        r.extra.setdefault("also_at", []).append(rel.replace(os.sep, "/"))


def _merge_dir_rev(revs, atype, rel, abs_dir, disk, spec):
    """A directory-unit revision (a host outfit): one row per DIRECTORY, its canonical
    still is the bytes, every other shot in it becomes meta.variants[]."""
    rel = rel.replace(os.sep, "/")
    key = "dir:" + rel
    r = revs.get(key)
    if r is None:
        r = Rev(atype, key, rel, spec["root"])
        revs[key] = r
    setattr(r, "src_" + disk, abs_dir)

    name = os.path.basename(rel)
    pref = list(spec.get("canonical", []))
    ov = (spec.get("canonical_override") or {}).get(name)
    if ov:
        pref = [ov] + [p for p in pref if p != ov]

    by_rel = {v["rel"]: v for v in r.variants}
    for fn in sorted(os.listdir(abs_dir)):
        p = os.path.join(abs_dir, fn)
        if fn.startswith(".") or not os.path.isfile(p):
            continue
        if cat.media_kind(fn) != "image":
            continue
        st = os.stat(p)
        by_rel[f"{rel}/{fn}"] = {"role": cat.role_for(fn), "rel": f"{rel}/{fn}",
                                 "bytes": st.st_size}
        r.mtime = min(r.mtime or st.st_mtime, st.st_mtime)

    r.variants = sorted(by_rel.values(), key=lambda v: v["rel"])

    # candidate / upscale side-car counts (they are NOT versions — spec vocabulary #2)
    for meta_key, sub in (spec.get("count_dirs") or {}).items():
        d = os.path.join(abs_dir, sub)
        if os.path.isdir(d):
            n = len([f for f in os.listdir(d) if not f.startswith(".")])
            r.extra[meta_key] = max(r.extra.get(meta_key, 0), n)

    # canonical still -> the revision's bytes (LOCAL copy preferred, else T5)
    dirs = [(d, p) for d, p in (("local", r.src_local), ("t5", r.src_t5)) if p]
    r.extra["dir_on"] = [d for d, _ in dirs]
    for fn in pref:
        on = [d for d, p in dirs if os.path.isfile(os.path.join(p, fn))]
        if not on:
            continue
        pick = dict(dirs)["local" if "local" in on else "t5"]
        src = os.path.join(pick, fn)
        r.sha1 = sha1_file(src)
        r.bytes = os.path.getsize(src)
        r.canon_disks = on
        r.extra["canonical"] = f"{rel}/{fn}"
        r.extra["canonical_abs"] = src
        return


# =======================================================================================
# per-channel enrichment (claude-tricks host facts; harmless no-ops elsewhere)
# =======================================================================================
def enrich_host(channel, revs, roots_assets):
    """meta.heygen + meta.used_by_eps for host_outfit rows, read from disk truth."""
    used = {}
    pool_ids = []
    freed_prefixes = []
    for aroot in roots_assets:
        lib = os.path.join(aroot, "character", "host_library")
        csv = os.path.join(lib, "USED-OUTFITS.csv")
        if os.path.isfile(csv):
            for line in open(csv).read().splitlines()[1:]:
                parts = line.split(",")
                if len(parts) >= 2:
                    used.setdefault(parts[1].strip(), set()).add("ep" + parts[0].strip())
        pool = os.path.join(lib, ".heygen_pool.json")
        if os.path.isfile(pool):
            try:
                pool_ids = [e.get("heygen_id") for e in json.load(open(pool))]
            except Exception:
                pass
        # outfit_12's shot_map records WHICH pool slots were freed to make room for it —
        # the only disk evidence that an avatar was deleted server-side.
        sm12 = os.path.join(lib, "outfit_12_longform_olive", "shot_map.json")
        if os.path.isfile(sm12):
            try:
                reason = json.load(open(sm12)).get("heygen_registration", {}).get("reason", "")
                freed_prefixes += re.findall(r"[0-9a-f]{6,}", reason)
            except Exception:
                pass
        # per-episode pins
        if os.path.isdir(aroot):
            for ep in sorted(os.listdir(aroot)):
                f = os.path.join(aroot, ep, "host_outfit.txt")
                if os.path.isfile(f):
                    val = open(f).read().strip().split(" ")[0]
                    used.setdefault(val, set()).add(ep)

    for r in revs:
        name = os.path.basename(r.rel_path)
        hey = {}
        for d in (r.src_local, r.src_t5):
            if not d or not os.path.isdir(d):
                continue
            for fn in os.listdir(d):
                if fn.startswith(".heygen"):
                    role = fn.replace(".heygen_photo_id", "").replace(".heygen_", "") or "photo"
                    role = role.lstrip("_") or "photo"
                    try:
                        hey[role] = open(os.path.join(d, fn)).read().strip()
                    except Exception:
                        pass
            sm = os.path.join(d, "shot_map.json")
            if os.path.isfile(sm):
                try:
                    r.extra["shot_map"] = json.load(open(sm)).get("shots", {})
                except Exception:
                    pass
        if hey:
            hey["pool_live"] = [i for i in pool_ids if i]
            # integrity: ids named in outfit_12/shot_map's "freed" reason are gone
            # server-side; other ids merely absent from the pool are just not rotating.
            for role, hid in list(hey.items()):
                if role == "pool_live" or not isinstance(hid, str):
                    continue
                if any(hid.startswith(p) for p in freed_prefixes):
                    hey[role + "_state"] = "freed"
                elif pool_ids and hid not in pool_ids:
                    hey[role + "_state"] = "not_in_pool"
            r.extra["heygen"] = hey
        if name in used:
            r.extra["used_by_eps"] = sorted(used[name])


# =======================================================================================
# version assignment + manifest
# =======================================================================================
def manifest_path(channel):
    return os.path.join(REPO, "channels", channel, "assets", "ASSET-MANIFEST.json")


def load_manifest(channel, rebuild):
    p = manifest_path(channel)
    if rebuild or not os.path.isfile(p):
        return {}
    try:
        return json.load(open(p)).get("entries", {})
    except Exception:
        return {}


def assign_versions(found, manifest):
    """Chronological by mtime ASC within a slot -> highest version = newest.
    Keys already pinned in the manifest keep their number, always."""
    for atype, revs in found.items():
        pinned = {k: e["version"] for k, e in manifest.items()
                  if e.get("asset_type") == atype}
        revs.sort(key=lambda r: (r.mtime, r.rel_path))
        taken = set(pinned.get(r.key) for r in revs if r.key in pinned)
        taken.discard(None)
        nxt = 1
        for r in revs:
            if r.key in pinned:
                r.version = pinned[r.key]
                continue
            while nxt in taken:
                nxt += 1
            r.version = nxt
            taken.add(nxt)
        revs.sort(key=lambda r: r.version)
        # lineage: v(n).parent = v(n-1). host_outfit o12 -> o11 is already this chain
        # (the Nano-Banana EDIT was seeded from o11), so no override is needed today.
        prev = None
        for r in revs:
            r.parent_key = prev.key if prev else None
            prev = r


# =======================================================================================
# storage paths, thumbs, uploads
# =======================================================================================
def assign_paths(channel, found):
    for atype, revs in found.items():
        if cat.SLOTS[atype].get("upload") == "none":
            continue
        # two different sha1s at the same rel_path (LOCAL vs T5 drifted) would collide in
        # the bucket -> disambiguate ALL members of the colliding group, deterministically
        seen = {}
        for r in revs:
            # a dir-unit revision uploads its CANONICAL STILL, not the folder
            seen.setdefault(r.extra.get("canonical") or r.rel_path, []).append(r)
        for rel, group in seen.items():
            for r in group:
                base = f"{channel}/assets/{rel}" if r.root_kind == "assets" \
                    else f"{channel}/{rel}"
                if len(group) > 1 and r.sha1:
                    stem, ext = os.path.splitext(base)
                    base = f"{stem}.{r.sha1[:8]}{ext}"
                    r.extra["disambiguated"] = True
                r.storage_path = base
        for r in revs:
            if cat.SLOTS[atype].get("thumb") != "none":
                r.thumb_path = f"{channel}/assets/_thumbs/{atype}/v{r.version}.jpg"


def make_thumb(rev, mode, workdir):
    """-> local jpg path or None. Never writes next to the source."""
    src = rev.extra.get("canonical_abs") or rev.src
    if not src or not os.path.isfile(src):
        return None
    out = os.path.join(workdir, f"{rev.asset_type}_v{rev.version}.jpg")
    kind = cat.media_kind(src)
    if mode == "companion" and kind == "video":
        for ext in (".jpg", ".jpeg", ".png"):
            sib = os.path.splitext(src)[0] + ext
            if os.path.isfile(sib):
                src, kind, mode = sib, "image", "downscale"
                rev.extra["thumb_from"] = "companion"
                break
        else:
            mode = "poster"
    if kind == "image":
        mode = "downscale"
    if mode == "poster" or kind == "video":
        rev.extra.setdefault("thumb_from", "ffmpeg_poster")
        ok = run_ffmpeg(["-ss", "0.5", "-i", src, "-frames:v", "1",
                         "-vf", f"scale={THUMB_W}:-2", "-q:v", "4", out])
        if not ok:  # very short clip -> retry from frame 0
            ok = run_ffmpeg(["-i", src, "-frames:v", "1",
                             "-vf", f"scale={THUMB_W}:-2", "-q:v", "4", out])
        return out if ok and os.path.isfile(out) else None
    rev.extra.setdefault("thumb_from", "downscale")
    ok = run_ffmpeg(["-i", src, "-vf", f"scale='min({THUMB_W},iw)':-2",
                     "-q:v", "4", out])
    return out if ok and os.path.isfile(out) else None


# =======================================================================================
# DB
# =======================================================================================
def detect_columns(supa):
    have = set()
    for c in OPTIONAL_COLS:
        try:
            supa.select("factory_asset_versions", f"select={c}&limit=1")
            have.add(c)
        except Exception:
            pass
    return have


def snapshot_locks(supa, channel):
    """{asset_type: (locked_version_id, build_ref)} BEFORE we touch anything."""
    locks = supa.select("factory_asset_locks", f"channel_key=eq.{channel}&select=*")
    ids = [l["locked_version_id"] for l in locks if l.get("locked_version_id")]
    bref = {}
    if ids:
        vers = supa.select("factory_asset_versions",
                           f"id=in.({','.join(ids)})&select=id,asset_type,version,meta")
        bref = {v["id"]: v for v in vers}
    out = {}
    for l in locks:
        v = bref.get(l.get("locked_version_id")) or {}
        out[l["asset_type"]] = {
            "version_id": l.get("locked_version_id"),
            "build_ref": (v.get("meta") or {}).get("build_ref"),
            "version": v.get("version"),
        }
    return out


def row_for(channel, rev, parent_id, have_cols):
    slot = cat.SLOTS[rev.asset_type]
    meta = {"build_ref": rev.build_ref, "rel_path": rev.rel_path,
            "source_disk": rev.source_disk}
    if rev.sha1:
        meta["sha1"] = rev.sha1
    if rev.bytes:
        meta["bytes"] = rev.bytes
    if rev.mtime:
        meta["mtime"] = iso(rev.mtime)
    if rev.variants:
        meta["variants"] = rev.variants
    for k, v in rev.extra.items():
        if k in ("canonical_abs", "label"):
            continue
        meta[k] = v
    if rev.retired_reason:
        meta["retired_reason"] = rev.retired_reason

    row = {
        "channel_key": channel, "asset_type": rev.asset_type, "version": rev.version,
        "label": rev.extra.get("label") or label_for(rev),
        "storage_path": rev.storage_path, "thumb_path": rev.thumb_path,
        "parent_version_id": parent_id, "status": rev.status, "source": "import",
        "meta": meta,
    }
    if "generator" in have_cols and slot.get("generator"):
        row["generator"] = slot["generator"]
    if "storage_state" in have_cols:
        row["storage_state"] = rev.storage_state
    if "retired_at" in have_cols:
        row["retired_at"] = iso(rev.mtime) if rev.status == "retired" and rev.mtime else None
    return row


def label_for(rev):
    rel = rev.rel_path
    stem = os.path.basename(rel)
    if rev.asset_type == "host_outfit":
        parts = stem.split("_")
        return f"Outfit {parts[1]} — {' '.join(p.capitalize() for p in parts[2:])}"
    head = rel.split("/")[0]
    stem_noext = os.path.splitext(stem)[0]
    if head.startswith(("ep", "bc", "poc")) and "/" in rel:
        return f"{head} — {stem_noext.replace('_', ' ')}"
    return stem_noext.replace("_", " ")


def dedupe_labels(found):
    """Two revisions of a slot that render the same label are unreadable on the board
    (epbc01's two outro cards, epbc01's .jpg + .png hook art). Disambiguate by date, then
    by sha, but only where a collision actually exists."""
    for revs in found.values():
        by_label = {}
        for r in revs:
            by_label.setdefault(r.extra.get("label") or label_for(r), []).append(r)
        for base, group in by_label.items():
            if len(group) < 2:
                continue
            for r in group:
                d = iso(r.mtime)[:10] if r.mtime else "?"
                r.extra["label"] = f"{base} · {d}"
            still = {}
            for r in group:
                still.setdefault(r.extra["label"], []).append(r)
            for lbl, g2 in still.items():
                if len(g2) > 1:
                    for r in g2:
                        r.extra["label"] = f"{lbl} · {(r.sha1 or '')[:6]}"


# =======================================================================================
# main
# =======================================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True)
    ap.add_argument("--tier", choices=["preview", "full"], default="preview")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--rebuild-manifest", action="store_true")
    a = ap.parse_args()
    ch = a.channel

    print(f"== ingest_asset_library — {ch} — tier={a.tier}"
          f"{' DRY-RUN' if a.dry_run else ''}")

    found = discover(ch, a.dry_run)
    aroots = [r[1] for r in _roots(ch, True)]
    enrich_host(ch, found.get("host_outfit", []), aroots)

    manifest = load_manifest(ch, a.rebuild_manifest)
    if manifest and not a.rebuild_manifest:
        print(f">> manifest: {len(manifest)} pinned key(s) at {manifest_path(ch)}")
    assign_versions(found, manifest)
    dedupe_labels(found)

    # ---- status ------------------------------------------------------------------
    supa = None
    have_cols = set()
    pre_locks = {}
    if not a.dry_run:
        env = fw.load_env()
        supa = fw.Supa(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
        have_cols = detect_columns(supa)
        missing = [c for c in OPTIONAL_COLS if c not in have_cols]
        if missing:
            print(f"!! 019_asset_library.sql not applied yet — skipping column(s): "
                  f"{', '.join(missing)}. Re-run after applying the migration.")
        pre_locks = snapshot_locks(supa, ch)
        print(f">> locks BEFORE: " + ", ".join(
            f"{t}=v{v['version']}({v['build_ref']})" for t, v in sorted(pre_locks.items())))

    locked_brefs = {t: v["build_ref"] for t, v in pre_locks.items() if v.get("build_ref")}
    for atype, revs in found.items():
        for r in revs:
            rel_key = r.rel_path if r.root_kind == "assets" else r.rel_path
            if rel_key in cat.RETIRED:
                r.status = "retired"
                r.retired_reason = cat.RETIRED[rel_key]
            elif locked_brefs.get(atype) == r.build_ref:
                r.status = "locked"
            else:
                r.status = "candidate"

    assign_paths(ch, found)

    # ---- plan ----------------------------------------------------------------------
    total = sum(len(v) for v in found.values())
    print(f">> {total} revision(s) across {len([k for k,v in found.items() if v])} slot(s)")
    for atype in cat.ordered_slots():
        revs = found.get(atype, [])
        if not revs:
            print(f"   {atype:<20} —  (nothing on disk)")
            continue
        print(f"   {atype:<20} {len(revs):>2} rev(s)")
        for r in revs:
            mark = {"locked": "LOCK", "retired": "DEAD", "candidate": "    "}[r.status]
            print(f"      v{r.version:<3} {mark} {(r.storage_state or '—'):<5} {r.rel_path}"
                  + (f"  [{len(r.variants)} variants]" if r.variants else ""))

    if a.dry_run:
        print(">> DRY-RUN — nothing uploaded, nothing written.")
        return

    # ---- uploads + thumbs -----------------------------------------------------------
    prev_manifest = manifest
    work = tempfile.mkdtemp(prefix="asset_ingest_")
    up_n = up_kb = th_n = th_kb = 0
    try:
        for atype in cat.ordered_slots():
            slot = cat.SLOTS[atype]
            for r in found.get(atype, []):
                pin = prev_manifest.get(r.key) or {}
                want_bytes = slot["upload"] == "always" or (
                    slot["upload"] == "full" and a.tier == "full")
                if want_bytes and r.storage_path and r.src:
                    src = r.extra.get("canonical_abs") or r.src
                    if os.path.isfile(src):
                        if pin.get("uploaded_sha1") == r.sha1 and \
                                pin.get("storage_path") == r.storage_path:
                            pass  # unchanged bytes at the same path — skip re-upload
                        else:
                            ctype = mimetypes.guess_type(src)[0] or "application/octet-stream"
                            with open(src, "rb") as fh:
                                supa.upload(r.storage_path, fh.read(), ctype)
                            up_n += 1
                            up_kb += os.path.getsize(src) // 1024
                            r.extra["uploaded"] = True
                elif r.storage_path and not want_bytes:
                    r.extra["bytes_not_uploaded"] = f"tier={a.tier}"

                if r.thumb_path:
                    if pin.get("thumb_sha1") == r.sha1 and \
                            pin.get("thumb_path") == r.thumb_path:
                        continue
                    tp = make_thumb(r, slot.get("thumb", "downscale"), work)
                    if tp:
                        with open(tp, "rb") as fh:
                            supa.upload(r.thumb_path, fh.read(), "image/jpeg")
                        th_n += 1
                        th_kb += os.path.getsize(tp) // 1024
                        r.extra["thumb_ok"] = True
                    else:
                        r.thumb_path = None
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f">> uploaded {up_n} source file(s) ({up_kb//1024} MB) "
          f"+ {th_n} thumbnail(s) ({th_kb} KB)")

    # ---- upsert, in an order that never leaves a lock pointing at the wrong asset ----
    # Renumbering means the row a lock points at (e.g. host_outfit v1) gets REWRITTEN with
    # different content. So: write everything EXCEPT those rows, re-point the locks at
    # their new home, and only then overwrite the vacated rows.
    problems = []
    target = {}                       # asset_type -> the Rev carrying the locked build_ref
    for atype, pre in pre_locks.items():
        want = pre.get("build_ref")
        target[atype] = next((r for r in found.get(atype, [])
                              if r.build_ref == want), None) if want else None
        if want and target[atype] is None:
            problems.append(f"lock {atype}: build_ref '{want}' has no revision on disk — "
                            f"lock LEFT UNTOUCHED, check before the next build")
    withhold = {(atype, pre["version"]) for atype, pre in pre_locks.items()
                if target.get(atype) and target[atype].version != pre["version"]}

    def _upsert(rows):
        # PostgREST (PGRST102) rejects a batch whose objects have differing key
        # sets, and optional columns (generator/job_id/…) are only present on
        # some rows — so pad every row to the union of keys before sending.
        if not rows:
            return
        keys = set()
        for r in rows:
            keys.update(r.keys())
        rows = [{k: r.get(k) for k in keys} for r in rows]
        for i in range(0, len(rows), 50):
            supa.insert("factory_asset_versions", rows[i:i + 50],
                        on_conflict="channel_key,asset_type,version",
                        resolution="merge-duplicates")

    all_rows = [(r, row_for(ch, r, None, have_cols))
                for atype in cat.ordered_slots() for r in found.get(atype, [])]
    _upsert([row for r, row in all_rows if (r.asset_type, r.version) not in withhold])

    got = supa.select("factory_asset_versions",
                      f"channel_key=eq.{ch}&select=id,asset_type,version,meta")
    id_by = {(g["asset_type"], g["version"]): g["id"] for g in got}

    for atype, pre in sorted(pre_locks.items()):
        tv = target.get(atype)
        if tv is None:
            continue
        if tv.version == pre["version"]:
            print(f">> lock {atype:<14} unchanged  v{tv.version}  ({pre['build_ref']})")
            continue
        new_id = id_by.get((atype, tv.version))
        if not new_id:
            problems.append(f"lock {atype}: new row v{tv.version} not found after upsert "
                            f"— lock LEFT UNTOUCHED")
            continue
        supa.patch("factory_asset_locks",
                   f"channel_key=eq.{ch}&asset_type=eq.{atype}",
                   {"locked_version_id": new_id,
                    "updated_at": iso(datetime.now(timezone.utc).timestamp())})
        print(f">> lock {atype:<14} RE-POINTED v{pre['version']} -> v{tv.version}  "
              f"(same build_ref '{pre['build_ref']}' — build_ep_v2 resolves the "
              f"identical asset)")

    _upsert([row for r, row in all_rows if (r.asset_type, r.version) in withhold])
    print(f">> upserted {total} version row(s)")

    # ---- lineage (needs the ids back) -----------------------------------------------
    got = supa.select("factory_asset_versions",
                      f"channel_key=eq.{ch}&select=id,asset_type,version,meta")
    id_by = {(g["asset_type"], g["version"]): g["id"] for g in got}
    lin_rows = []
    for atype, revs in found.items():
        by_key = {r.key: r for r in revs}
        for r in revs:
            p = by_key.get(r.parent_key) if r.parent_key else None
            pid = id_by.get((atype, p.version)) if p else None
            row = dict(next(row for rr, row in all_rows if rr is r))
            row["parent_version_id"] = pid
            lin_rows.append(row)
    _upsert(lin_rows)
    print(f">> lineage: {sum(1 for r in lin_rows if r['parent_version_id'])} "
          f"parent link(s) set")

    post = snapshot_locks(supa, ch)
    for atype, pre in pre_locks.items():
        if post.get(atype, {}).get("build_ref") != pre.get("build_ref"):
            problems.append(f"!! lock {atype} build_ref CHANGED "
                            f"{pre.get('build_ref')} -> {post.get(atype, {}).get('build_ref')}")
    print(">> locks AFTER : " + ", ".join(
        f"{t}=v{v['version']}({v['build_ref']})" for t, v in sorted(post.items())))

    # ---- manifest --------------------------------------------------------------------
    entries = {}
    for atype, revs in found.items():
        by_key = {r.key: r for r in revs}
        for r in revs:
            p = by_key.get(r.parent_key) if r.parent_key else None
            entries[r.key] = {
                "asset_type": atype, "version": r.version, "sha1": r.sha1,
                "rel_path": r.rel_path, "storage_path": r.storage_path,
                "thumb_path": r.thumb_path, "status": r.status,
                "parent_key": r.parent_key, "parent_sha1": (p.sha1 if p else None),
                "uploaded_sha1": r.sha1 if r.extra.get("uploaded") else
                                 (prev_manifest.get(r.key) or {}).get("uploaded_sha1"),
                "thumb_sha1": r.sha1 if r.extra.get("thumb_ok") else
                              (prev_manifest.get(r.key) or {}).get("thumb_sha1"),
            }
    mp = manifest_path(ch)
    with open(mp, "w") as fh:
        json.dump({"_comment": "VERSION PINS — do not hand-edit. sha1 (or dir:/code: key) "
                               "-> version. Re-running the ingest keeps every pinned "
                               "number; only new keys get new versions. Deleting this "
                               "file renumbers the whole board.",
                   "channel": ch, "generated_at": iso(datetime.now(timezone.utc).timestamp()),
                   "entries": entries}, fh, indent=1, sort_keys=True)
    print(f">> manifest written: {mp} ({len(entries)} pins)")

    # ---- NEEDS-ATTENTION --------------------------------------------------------------
    notes = list(problems)
    for r in found.get("host_outfit", []):
        hey = r.extra.get("heygen") or {}
        freed = [k.replace("_state", "") for k, v in hey.items()
                 if k.endswith("_state") and v == "freed"]
        if freed:
            notes.append(f"{os.path.basename(r.rel_path)} (v{r.version}): HeyGen "
                         f"{', '.join(freed)} avatar id(s) are NOT in .heygen_pool.json — "
                         f"freed server-side to register outfit_12. The composer must not "
                         f"offer a face that no longer renders.")
    local_only = sorted({(r.rel_path if r.key.startswith("dir:")
                          else os.path.dirname(r.rel_path) or r.rel_path)
                         for revs in found.values() for r in revs
                         if r.source_disk == ["local"] and r.root_kind == "assets"})
    if local_only:
        notes.append("LOCAL-only, never rsynced to T5 (one disk failure from gone): "
                     + ", ".join(local_only))
        notes.append(f"  rsync -a --ignore-existing {REPO}/channels/{ch}/assets/ "
                     f"{T5_ROOT}/channels/{ch}/assets/")
    empty = [t for t in cat.ordered_slots() if not found.get(t)]
    if empty:
        notes.append("slots with nothing on disk: " + ", ".join(empty))
    if notes:
        print("\n== NEEDS ATTENTION")
        for n in notes:
            print("  - " + n)
    print("\n>> DONE")


if __name__ == "__main__":
    main()
