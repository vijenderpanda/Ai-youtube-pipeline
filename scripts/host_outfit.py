#!/usr/bin/env python3
"""
Dynamic host wardrobe for AI Unpacked (claude-tricks).

Picks ONE outfit folder from assets/character/host_library/ per episode and
returns its HeyGen talking_photo_id, so every host cutaway in a single video
wears the SAME outfit while different videos rotate through the wardrobe.

Each outfit folder holds: center.jpg + three_quarter.jpg (2:3 talking-head
sources) and left_corner.jpg / right_corner.jpg (16:9 wide). `center.jpg` is the
HeyGen talking-photo source (front-facing head-and-shoulders, warm).

Selection is DETERMINISTIC and IDEMPOTENT per episode key: the first build of an
episode picks an outfit (hash-ordered by the key, skipping the last few used so
consecutive videos don't repeat) and records it; every rebuild of that episode
returns the same outfit. Each outfit's HeyGen id is uploaded once on first use
and cached in the outfit folder's `.heygen_photo_id` (uploading is a free API
call; only rendering costs credits).

API:
    outfit       = pick(episode_key)              # -> Outfit dict (idempotent)
    tid          = heygen_id(outfit)              # -> talking_photo_id (uploads+caches on 1st use)
    outfit, tid  = pick_and_register(episode_key) # both, + append to USED-OUTFITS.csv

CLI (smoke test — --list/--pick make no network calls, --register only uploads):
    python3 scripts/host_outfit.py --list
    python3 scripts/host_outfit.py --pick 27         # which outfit ep27 gets
    python3 scripts/host_outfit.py --register 27     # pick + upload its center to HeyGen (free)
"""
import argparse, csv, hashlib, json, os, random, time

HERE = os.path.dirname(os.path.abspath(__file__))
LIBRARY = os.path.abspath(os.path.join(
    HERE, "..", "channels", "claude-tricks", "assets", "character", "host_library"))
USED_LOG = os.path.join(LIBRARY, "USED-OUTFITS.csv")
# Ephemeral HeyGen photo-avatar pool: outfit avatars WE created, so we can
# recycle them within HeyGen's 3-group cap without ever touching the current
# host or the aashiqana avatar (which are NOT in this file).
POOL = os.path.join(LIBRARY, ".heygen_pool.json")
CAP_CODE = "401028"   # HeyGen "exceeded your limit of 3 photo avatars"

SHOTS = ("center", "three_quarter", "left_corner", "right_corner")


def _outfit(name, d):
    o = {"name": name, "dir": d,
         "heygen_cache": os.path.join(d, ".heygen_photo_id"),
         # v16: 3/4 yaw as a SECOND animatable source per outfit — closes ~30%
         # of the "no variety" tell within a single episode's cutaways
         "heygen_cache_3q": os.path.join(d, ".heygen_photo_id_3q")}
    for s in SHOTS:
        p = os.path.join(d, s + ".jpg")
        o[s] = p if os.path.exists(p) else None
    o["face"] = o["center"]           # HeyGen talking-photo source (primary)
    o["face_3q"] = o["three_quarter"]  # HeyGen talking-photo source (yaw variant)
    return o


def list_outfits():
    """All outfit dirs (name starts 'outfit_' and holds center.jpg), sorted."""
    out = []
    if not os.path.isdir(LIBRARY):
        return out
    for name in sorted(os.listdir(LIBRARY)):
        d = os.path.join(LIBRARY, name)
        if name.startswith("outfit_") and os.path.isdir(d) \
                and os.path.exists(os.path.join(d, "center.jpg")):
            out.append(_outfit(name, d))
    return out


def _log_rows():
    if not os.path.exists(USED_LOG):
        return []
    with open(USED_LOG, newline="") as f:
        return [r for r in csv.reader(f) if r][1:]   # skip header


def assigned(episode_key):
    """Outfit name previously logged for this episode key (idempotency), else None."""
    key = str(episode_key)
    name = None
    for r in _log_rows():
        if len(r) > 1 and r[0] == key:
            name = r[1]                              # most-recent assignment wins
    return name


def _recent(n):
    """Names of the last n DISTINCT outfits used (newest first)."""
    seen, out = set(), []
    for r in reversed(_log_rows()):
        if len(r) > 1 and r[1] not in seen:
            seen.add(r[1]); out.append(r[1])
            if len(out) >= n:
                break
    return out


def pick(episode_key, avoid_recent=2):
    """Deterministic, idempotent outfit for an episode.

    If the key was already assigned (and that outfit still exists) -> return it.
    Otherwise order the library by a hash of the key and take the first outfit
    that isn't among the last `avoid_recent` used.
    """
    outfits = list_outfits()
    if not outfits:
        raise RuntimeError(f"no outfit folders under {LIBRARY}")
    by_name = {o["name"]: o for o in outfits}

    prev = assigned(episode_key)
    if prev and prev in by_name:
        return by_name[prev]

    seed = int(hashlib.sha256(str(episode_key).encode()).hexdigest(), 16)
    order = outfits[:]
    random.Random(seed).shuffle(order)
    recent = set(_recent(avoid_recent))
    for o in order:
        if o["name"] not in recent:
            return o
    return order[0]                                 # all used recently -> key's top pick


def _pool_load():
    try:
        return json.load(open(POOL)) if os.path.exists(POOL) else []
    except Exception:
        return []


def _pool_save(p):
    os.makedirs(os.path.dirname(POOL), exist_ok=True)
    json.dump(p, open(POOL, "w"), indent=2)


def _heygen_id_for(outfit, source_key, cache_key, force=False):
    """Shared upload+pool logic for either the primary (center) or the yaw
    variant (three_quarter) HeyGen avatar of an outfit. source_key is the
    outfit dict key holding the .jpg path ("face" or "face_3q"); cache_key
    is the outfit dict key holding the .heygen_photo_id cache path.
    Pool entries carry a "role" so eviction can prefer other-outfit victims
    over the currently-registering outfit's other avatar."""
    import requests
    import heygen_avatar                            # scripts/ is on sys.path

    cache = outfit[cache_key]
    role = "3q" if cache_key == "heygen_cache_3q" else "center"
    pool = _pool_load()

    if not force and os.path.exists(cache):
        tid = open(cache).read().strip()
        if tid and any(e["heygen_id"] == tid for e in pool):
            for e in pool:                          # touch LRU timestamp
                if e["heygen_id"] == tid:
                    e["ts"] = int(time.time())
            _pool_save(pool)
            return tid

    src = outfit.get(source_key)
    if not src:
        raise RuntimeError(f"{outfit['name']} has no {source_key} source ({cache_key})")

    for _ in range(len(pool) + 2):
        try:
            tid = heygen_avatar.upload_photo(src, cache=cache)
            pool = [e for e in pool if e["heygen_id"] != tid]
            pool.append({"heygen_id": tid, "outfit": outfit["name"], "role": role,
                         "ts": int(time.time())})
            _pool_save(pool)
            return tid
        except requests.HTTPError as ex:
            body = ex.response.text if ex.response is not None else ""
            if CAP_CODE not in body or not pool:
                raise                                # not a cap error, or nothing of ours to free
            # v16: prefer evicting a DIFFERENT outfit's avatar; only fall back
            # to same-outfit siblings when nothing else is on the pool
            pool.sort(key=lambda e: (e["outfit"] == outfit["name"], e["ts"]))
            victim = pool.pop(0)
            heygen_avatar.delete_group(victim["heygen_id"])
            vcache_name = ".heygen_photo_id_3q" if victim.get("role") == "3q" else ".heygen_photo_id"
            vcache = os.path.join(LIBRARY, victim["outfit"], vcache_name)
            if os.path.exists(vcache):
                os.remove(vcache)
            _pool_save(pool)
            print(f"   (evicted {victim['outfit']}/{victim.get('role','center')} "
                  f"to stay under HeyGen's cap)")
    raise RuntimeError("could not register outfit within HeyGen's 3-avatar cap "
                       "(free a slot or upgrade)")


def heygen_id(outfit, force=False):
    """talking_photo_id for the outfit's PRIMARY (center) avatar. Legacy API
    — preserved for callers that only need one talking-photo per outfit."""
    return _heygen_id_for(outfit, "face", "heygen_cache", force=force)


def heygen_id_3q(outfit, force=False):
    """talking_photo_id for the outfit's 3/4-yaw SECONDARY avatar.
    v16: paired with heygen_id() to give a two-tid pool per episode, so a
    single Short can alternate yaw across beats and dodge the static
    talking-photo tell (~50% Vaibhav-DNA camera-angle parity — the hands
    fix still requires HeyGen Video-Avatar and real desk footage)."""
    return _heygen_id_for(outfit, "face_3q", "heygen_cache_3q", force=force)


def log_use(episode_key, outfit):
    new = not os.path.exists(USED_LOG)
    os.makedirs(os.path.dirname(USED_LOG), exist_ok=True)
    with open(USED_LOG, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["episode_key", "outfit", "ts_epoch"])
        w.writerow([str(episode_key), outfit["name"], int(time.time())])


def pick_and_register(episode_key, avoid_recent=2):
    """Pick this episode's outfit, ensure its HeyGen id exists, record the use.
    Returns (outfit, talking_photo_id). Idempotent: a rebuild reuses the same
    outfit and does not duplicate the log row.
    Only the PRIMARY (center) tid is registered — use pick_and_register_pool()
    if a build wants the 3/4 yaw variant too."""
    o = pick(episode_key, avoid_recent)
    tid = heygen_id(o)
    if assigned(episode_key) != o["name"]:
        log_use(episode_key, o)
    return o, tid


def pick_and_register_pool(episode_key, avoid_recent=2):
    """Pick + register BOTH center and 3/4-yaw talking-photos, so a single Short
    can alternate yaw across host cutaway beats. Returns (outfit, [center_tid,
    three_quarter_tid]). If three_quarter.jpg is missing (never happens on the
    current claude-tricks library — audit 2026-08-10), the pool collapses to
    [center_tid] silently rather than fail the build.
    v16: this is the entry point new plan_post / produce_preview jobs use."""
    o = pick(episode_key, avoid_recent)
    tids = [heygen_id(o)]
    if o.get("face_3q"):
        try:
            tids.append(heygen_id_3q(o))
        except Exception as e:
            # 3q registration failure never fails the whole build — the primary
            # tid is enough to render, just without yaw variety on this episode
            print(f"   (skipped 3q register for {o['name']}: {e})")
    if assigned(episode_key) != o["name"]:
        log_use(episode_key, o)
    return o, tids


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="dynamic host wardrobe picker")
    ap.add_argument("--list", action="store_true", help="list outfits + registration state")
    ap.add_argument("--pick", metavar="EP", help="show which outfit an episode key gets (no network)")
    ap.add_argument("--register", metavar="EP", help="pick + upload its center to HeyGen (free API call)")
    ap.add_argument("--register-pool", metavar="EP",
                    help="pick + upload BOTH center and 3/4-yaw to HeyGen (free API call, v16)")
    a = ap.parse_args()
    did = False
    if a.list:
        did = True
        for o in list_outfits():
            reg = "registered" if os.path.exists(o["heygen_cache"]) else "-"
            reg_3q = "reg-3q" if os.path.exists(o["heygen_cache_3q"]) else "-"
            print(f"{o['name']:34} center:{reg:14} 3q:{reg_3q}")
        print(f"\n{len(list_outfits())} outfits · library: {LIBRARY}")
    if a.pick:
        did = True
        o = pick(a.pick)
        note = "  (already assigned)" if assigned(a.pick) == o["name"] else ""
        print(f"ep {a.pick} -> {o['name']}{note}")
        for s in SHOTS:
            print(f"   {s:14} {o[s]}")
    if a.register:
        did = True
        o, tid = pick_and_register(a.register)
        print(f"ep {a.register} -> {o['name']}   talking_photo_id = {tid}")
    if a.register_pool:
        did = True
        o, tids = pick_and_register_pool(a.register_pool)
        print(f"ep {a.register_pool} -> {o['name']}   talking_photo_ids = {tids}")
        print(f"   center = {tids[0]}")
        if len(tids) > 1:
            print(f"   3q     = {tids[1]}")
    if not did:
        ap.print_help()
