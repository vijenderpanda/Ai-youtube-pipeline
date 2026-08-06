#!/usr/bin/env python3
"""
Grid hygiene, network-scope: retire the superseded uploads the insight cycles
keep flagging, without waiting for a manual Studio session.

PRIVATIZE, NEVER DELETE (playbook §9 "never hard-delete via automation").
`private` is reversible from Studio in two clicks; a delete is not, and no
automation on this machine is allowed to make an irreversible call about a
video. This script therefore only ever writes privacyStatus=private.

Selection is DELIBERATELY DUMB and that is the safety property: a video is a
candidate only if the operator's own marker string is literally in its title
(default '🗑️ DELETE', the playbook §9 retire prefix). Exact substring, no
fuzzy match, no "(superseded)" heuristics, no keep-set guessing -- an unmarked
video can never be touched, whatever it is called. Marking is a human act
(Studio rename, or `verify_uploads.py --fix-titles`); this script is only the
janitor that acts on the marks.

Usage:
    python3 scripts/yt_cleanup.py --channel aashiqana                 # dry run (default)
    python3 scripts/yt_cleanup.py --channel aashiqana --apply         # writes
    python3 scripts/yt_cleanup.py --channel vehicles --marker '[RETIRE]'
    python3 scripts/yt_cleanup.py --channel aashiqana --apply --unschedule
    python3 scripts/yt_cleanup.py --channel aashiqana --json out.json

Dry run prints every candidate (id / title / views / privacyStatus) and exits 0
having changed nothing. --apply flips each candidate to private, re-reads it to
confirm, and appends channels/<key>/cleanup_log.json so every change is
auditable and reversible.

Exit codes: 0 = nothing to do / every marked video is private.
            1 = a marked video could not be retired, or the run was invalid
                (missing token, empty marker) -- either way daily_check should
                surface it rather than silently pass.
"""
import argparse, json, os, sys, time
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
os.chdir(REPO)

DEFAULT_MARKER = "🗑️ DELETE"

# The status fields that must be echoed back on videos.update, imported rather
# than re-declared: videos.update REPLACES the whole `status` part, so anything
# omitted is wiped (a missing publishAt unschedules, a missing
# selfDeclaredMadeForKids silently flips the COPPA flag). Single source of
# truth lives in verify_uploads.py.
from verify_uploads import STATUS_ROUNDTRIP  # noqa: E402


def log_path(channel):
    return os.path.join(REPO, "channels", channel, "cleanup_log.json")


def load_log(channel):
    """Never raises: a corrupt log must not lose the record of a write that
    already happened on YouTube (playbook §9 -- a crash in the bookkeeping
    step after a successful API call reads as "the action failed")."""
    p = log_path(channel)
    if not os.path.exists(p):
        return []
    try:
        with open(p) as f:
            entries = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f">> WARNING: {os.path.relpath(p, REPO)} unreadable ({e}); starting a fresh log "
              f"— the old file is about to be overwritten, copy it first if you need it")
        return []
    return entries if isinstance(entries, list) else []


def append_log(channel, entries):
    """Append-only audit trail. Each entry is enough to undo the change by
    hand: {video_id, title, old_status, new_status, ts}.

    Read the whole log BEFORE opening for write -- open(p, "w") truncates, so
    loading inside the write block silently ate the history (caught on the
    first live --apply run, 6 Aug 2026)."""
    if not entries:
        return None
    history = load_log(channel)
    p = log_path(channel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(history + entries, f, indent=2, ensure_ascii=False)
    return p


def get_youtube(channel):
    """Reuse yt_upload.py's OAuth plumbing -- one GCP client, one token per
    channel. get_creds() falls back to an INTERACTIVE browser consent when the
    token is missing, which hangs forever under launchd, so a missing token is
    a loud failure here instead."""
    from yt_upload import get_creds, token_path
    from googleapiclient.discovery import build
    tp = token_path(channel)
    if not os.path.exists(tp):
        sys.exit(f"!! no token for channel {channel!r} at {tp} — authorize once with: "
                 f"python3 scripts/yt_upload.py --channel {channel} --auth")
    return build("youtube", "v3", credentials=get_creds(channel, False)), tp


def list_uploads(yt):
    """Every video on the channel, private ones included.

    The uploads playlist is the authoritative list for the owner; search.list
    forMine is unioned in because it surfaces very recent uploads the playlist
    index can lag on (same belt-and-braces pair network_stats.py uses). Both
    are paginated -- a truncated list would silently under-report candidates,
    which for a cleanup tool reads as "nothing to clean".
    """
    ch = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0]
    uploads_pl = ch["contentDetails"]["relatedPlaylists"]["uploads"]

    ids, page = [], None
    while True:
        kw = dict(part="contentDetails", playlistId=uploads_pl, maxResults=50)
        if page:
            kw["pageToken"] = page
        resp = yt.playlistItems().list(**kw).execute()
        ids.extend(i["contentDetails"]["videoId"] for i in resp.get("items", []))
        page = resp.get("nextPageToken")
        if not page:
            break

    page = None
    while True:
        kw = dict(part="id", forMine=True, type="video", maxResults=50, order="date")
        if page:
            kw["pageToken"] = page
        resp = yt.search().list(**kw).execute()
        ids.extend(i["id"]["videoId"] for i in resp.get("items", []))
        page = resp.get("nextPageToken")
        if not page:
            break

    seen, ordered = set(), []
    for v in ids:
        if v not in seen:
            seen.add(v)
            ordered.append(v)

    videos = []
    for chunk in (ordered[i:i + 50] for i in range(0, len(ordered), 50)):
        vr = yt.videos().list(part="snippet,status,statistics", id=",".join(chunk)).execute()
        for v in vr.get("items", []):
            st = v.get("status", {})
            videos.append({
                "id": v["id"],
                "title": v["snippet"]["title"],
                "privacyStatus": st.get("privacyStatus", ""),
                "publishAt": st.get("publishAt", "") or "",
                "publishedAt": v["snippet"].get("publishedAt", "") or "",
                "views": int(v.get("statistics", {}).get("viewCount", 0) or 0),
                "status": st,
            })
    return videos


def select_marked(videos, marker):
    """Exact substring match on the operator's marker. Nothing else, ever."""
    return [v for v in videos if marker in v["title"]]


def retire(yt, video, unschedule):
    """Flip one marked video to private, echoing its whole status back.

    Returns (ok, note). `note` on success is a non-fatal warning or None.
    Never deletes; never touches snippet (title, tags, description and
    categoryId stay exactly as the operator left them).

    🔴 videos.list is READ-AFTER-WRITE STALE (measured 6 Aug 2026 on
    4EgwUVBN7Ng: update to unlisted acked, the very next videos.list still
    said 'private', a later list said 'unlisted'). So the authority for "did
    the write land" is the videos.update RESPONSE, which echoes the stored
    resource; the re-read is a confirmation with a short retry. Treating the
    first stale read as failure would report a false FAILED on a write that
    actually succeeded -- and daily_check would cry wolf every run.
    """
    body = {k: video["status"][k] for k in STATUS_ROUNDTRIP if k in video["status"]}
    body["privacyStatus"] = "private"
    if unschedule:
        body.pop("publishAt", None)
    try:
        resp = yt.videos().update(part="status", body={"id": video["id"], "status": body}).execute()
    except Exception as e:  # HttpError and transport errors alike
        return False, f"videos.update failed: {e}"

    acked = (resp.get("status") or {}).get("privacyStatus", "")
    if acked != "private":
        return False, f"videos.update acked privacyStatus={acked!r}, expected 'private'"
    if not unschedule:
        # a dropped publishAt here would mean the round-trip lost the schedule
        was, now = video["publishAt"], (resp.get("status") or {}).get("publishAt", "") or ""
        if was and now != was:
            return False, f"publishAt drifted {was!r} -> {now!r} — video may have been unscheduled"

    for attempt in range(3):
        if attempt:
            time.sleep(2)
        items = yt.videos().list(part="status", id=video["id"]).execute().get("items", [])
        if not items:
            return False, "video vanished from videos.list after update"
        got = items[0]["status"].get("privacyStatus", "")
        if got == "private":
            return True, None
    return True, (f"write acked but read-back still shows {got!r} (known videos.list lag) — "
                  f"confirm with: python3 scripts/verify_uploads.py --channel <key>")


def main():
    ap = argparse.ArgumentParser(
        description="Privatize (never delete) videos the operator marked for cleanup.")
    ap.add_argument("--channel", required=True,
                    help="channel key -> secrets/token_<key>.json (lulla/pip = token.json)")
    ap.add_argument("--marker", default=DEFAULT_MARKER,
                    help=f"exact substring that marks a video for retirement (default: {DEFAULT_MARKER!r})")
    ap.add_argument("--apply", action="store_true",
                    help="actually write privacyStatus=private (default is a dry run)")
    ap.add_argument("--unschedule", action="store_true",
                    help="also clear publishAt on marked videos that are still SCHEDULED "
                         "(refused without this flag -- retiring a scheduled video means "
                         "unscheduling it, which is never automatic)")
    ap.add_argument("--json", dest="json_out", help="write the candidate report to this path too")
    a = ap.parse_args()

    marker = a.marker
    if not marker.strip():
        sys.exit("!! --marker cannot be empty: that would select every video on the channel")

    yt, tp = get_youtube(a.channel)
    who = yt.channels().list(part="snippet", mine=True).execute()["items"][0]["snippet"]["title"]
    print(f">> channel: {who}  (key={a.channel}, token={tp})")
    print(f">> marker: {marker!r}   mode: {'APPLY (writes)' if a.apply else 'DRY RUN (no changes)'}")

    videos = list_uploads(yt)
    marked = select_marked(videos, marker)
    print(f">> {len(videos)} uploads scanned, {len(marked)} marked\n")

    if not marked:
        print("no marked videos")
        if a.json_out:
            with open(a.json_out, "w") as f:
                json.dump({"channel": a.channel, "marker": marker, "scanned": len(videos),
                           "candidates": []}, f, indent=2, ensure_ascii=False)
        return 0

    report = []
    for v in marked:
        state = v["privacyStatus"]
        if v["privacyStatus"] == "private" and v["publishAt"]:
            state = f"scheduled {v['publishAt'][:16]}"
        report.append({"video_id": v["id"], "title": v["title"], "views": v["views"],
                       "privacyStatus": v["privacyStatus"], "publishAt": v["publishAt"],
                       "state": state})
        print(f"  {v['id']}  {v['views']:>6} views  {state:<24}  {v['title']}")
    print()

    if a.json_out:
        with open(a.json_out, "w") as f:
            json.dump({"channel": a.channel, "marker": marker, "scanned": len(videos),
                       "candidates": report}, f, indent=2, ensure_ascii=False)
        print(f">> report: {a.json_out}")

    if not a.apply:
        todo = [v for v in marked if v["privacyStatus"] != "private"]
        print(f">> DRY RUN — nothing changed. {len(todo)} of {len(marked)} marked video(s) "
              f"would be set private.")
        print(f">> re-run with --apply to retire them "
              f"(privatize only — deletion stays a manual Studio action).")
        return 0

    entries, failures, skipped = [], [], []
    for v in marked:
        if v["privacyStatus"] == "private" and not v["publishAt"]:
            skipped.append((v, "already private"))
            print(f"  = {v['id']}  already private — no change")
            continue
        if v["publishAt"] and not a.unschedule:
            # Marked AND scheduled: privatizing while leaving publishAt would
            # let it auto-publish later anyway, and clearing publishAt is an
            # unschedule -- never implicit. Loud failure, so daily_check sees it.
            failures.append((v, "marked but SCHEDULED — refusing to unschedule implicitly; "
                                "re-run with --unschedule (or clear the schedule in Studio)"))
            print(f"  ! {v['id']}  SCHEDULED {v['publishAt'][:16]} — refused "
                  f"(re-run with --unschedule to retire it)")
            continue
        old, old_publish = v["privacyStatus"], v["publishAt"]
        ok, note = retire(yt, v, a.unschedule)
        if not ok:
            failures.append((v, note))
            print(f"  ! {v['id']}  FAILED — {note}")
            continue
        entry = {"video_id": v["id"], "title": v["title"], "old_status": old,
                 "new_status": "private", "ts": datetime.now(timezone.utc).isoformat()}
        if old_publish:
            # the cleared schedule has to live in the log too, or "reversible"
            # only gets you back to private-with-no-date
            entry["old_publish_at"] = old_publish
        entries.append(entry)
        was = f"scheduled {old_publish[:16]}" if old_publish else old
        print(f"  ✓ {v['id']}  {was} -> private{' (unscheduled)' if old_publish else ''}")
        if note:
            print(f"    (warning: {note})")

    try:
        p = append_log(a.channel, entries)
    except OSError as e:
        p = None
        print(f"\n>> WARNING: could not write the cleanup log ({e}). The videos ARE retired; "
              f"this is the record — paste it into the log by hand:")
        print(json.dumps(entries, indent=2, ensure_ascii=False))
    print()
    print(f">> retired {len(entries)}, already-private {len(skipped)}, failed {len(failures)}")
    if p:
        print(f">> logged to {os.path.relpath(p, REPO)} (undo: set these ids back in Studio)")
    if failures:
        print("\n!! marked videos still not retired:")
        for v, note in failures:
            print(f"   {v['id']}  {v['title'][:60]}  — {note}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
