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
         "heygen_cache": os.path.join(d, ".heygen_photo_id")}
    for s in SHOTS:
        p = os.path.join(d, s + ".jpg")
        o[s] = p if os.path.exists(p) else None
    o["face"] = o["center"]           # HeyGen talking-photo source
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


def heygen_id(outfit, force=False):
    """talking_photo_id (== avatar_group id) for this outfit, managed as an
    ephemeral pool under HeyGen's 3-photo-avatar cap.

    - If the outfit already holds a live avatar (in the pool) -> reuse it.
    - Otherwise upload center.jpg. If HeyGen rejects it at the cap, delete the
      least-recently-used avatar THIS POOL created (never the host or aashiqana),
      then retry. Uploading/deleting are free; only rendering costs credits.
    """
    import requests
    import heygen_avatar                            # scripts/ is on sys.path

    cache = outfit["heygen_cache"]
    pool = _pool_load()

    if not force and os.path.exists(cache):
        tid = open(cache).read().strip()
        if tid and any(e["heygen_id"] == tid for e in pool):
            for e in pool:                          # touch LRU timestamp
                if e["heygen_id"] == tid:
                    e["ts"] = int(time.time())
            _pool_save(pool)
            return tid

    if not outfit.get("face"):
        raise RuntimeError(f"{outfit['name']} has no center.jpg to use as the HeyGen source")

    for _ in range(len(pool) + 2):
        try:
            tid = heygen_avatar.upload_photo(outfit["face"], cache=cache)
            pool = [e for e in pool if e["heygen_id"] != tid]
            pool.append({"heygen_id": tid, "outfit": outfit["name"], "ts": int(time.time())})
            _pool_save(pool)
            return tid
        except requests.HTTPError as ex:
            body = ex.response.text if ex.response is not None else ""
            if CAP_CODE not in body or not pool:
                raise                                # not a cap error, or nothing of ours to free
            pool.sort(key=lambda e: e["ts"])         # evict OUR least-recently-used outfit avatar
            victim = pool.pop(0)
            heygen_avatar.delete_group(victim["heygen_id"])
            vcache = os.path.join(LIBRARY, victim["outfit"], ".heygen_photo_id")
            if os.path.exists(vcache):
                os.remove(vcache)
            _pool_save(pool)
            print(f"   (evicted {victim['outfit']} to stay under HeyGen's cap)")
    raise RuntimeError("could not register outfit within HeyGen's 3-avatar cap "
                       "(free a slot or upgrade)")


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
    outfit and does not duplicate the log row."""
    o = pick(episode_key, avoid_recent)
    tid = heygen_id(o)
    if assigned(episode_key) != o["name"]:
        log_use(episode_key, o)
    return o, tid


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="dynamic host wardrobe picker")
    ap.add_argument("--list", action="store_true", help="list outfits + registration state")
    ap.add_argument("--pick", metavar="EP", help="show which outfit an episode key gets (no network)")
    ap.add_argument("--register", metavar="EP", help="pick + upload its center to HeyGen (free API call)")
    a = ap.parse_args()
    did = False
    if a.list:
        did = True
        for o in list_outfits():
            reg = "registered" if os.path.exists(o["heygen_cache"]) else "-"
            print(f"{o['name']:34} {reg}")
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
    if not did:
        ap.print_help()
