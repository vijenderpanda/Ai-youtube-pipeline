#!/usr/bin/env python3
"""
Link already-shipped YouTube videos back to the calendar rows that made them.

WHY THIS EXISTS. A piece that is live on YouTube kept showing up in the app as
"a cut is waiting". The app decides a piece has shipped by finding its post --
factory_posts.calendar_id, which finalize_episode.py:490 writes -- but that
backlink was only added recently, so every older post carries neither
calendar_id nor job_id. Meanwhile finalize's terminal write to the calendar is
status='produced' (finalize_episode.py:503), which is exactly the status the
triage feed selects for. So those pieces sat in "needs you" forever with no way
out.

WHY NOT MATCH ON TITLE. The YouTube title is frequently rewritten at upload:
calendar "Your Claude Code Usage Boost Disappears Aug 19" shipped as "You Have
50% More Claude Code Right Now", and "The FDA Just Let AI Diagnose You" shipped
as "An AI Can Legally Diagnose You". Title matching would miss exactly the rows
that need fixing and, worse, could confidently mismatch.

WHAT IT MATCHES ON. The pipeline arms a piece for its planned day: every
already-linked pair in the database has planned_date == the post's IST publish
date. So a calendar row and a post are paired when they share a channel AND a
day AND each is the ONLY unmatched candidate on that day. A day with two
unmatched pieces is reported, never guessed -- that is the case where a wrong
link would silently attribute one video's numbers to another piece.

SECOND MODE: --from-youtube. Some pieces are live on YouTube with no post row at
all -- Thehar Ja, Chalo Na and Tu Meri Jaan were all public on 2026-08-19 and the
app had no record of any of them, because they were armed outside the app. That
mode reads the channel's real uploads (public AND scheduled-private) and writes
the missing post, so the piece leaves "needs you" for the reason it should: the
video exists.

Within a day, titles disambiguate. Three Aashiqana pieces and three Aashiqana
videos shared 2026-08-19, so counting alone could not pair them -- but "Thehar
Ja" against "Thehar Ja (cafe) | New Hindi Love Song 2026" is unambiguous.
Title matching is used ONLY to separate candidates that already share a channel
and a day; it is never used to find a match across the whole set, which is how
it would go wrong.

Usage:
  python3 scripts/reconcile_posts.py                     # dry run: post <-> calendar
  python3 scripts/reconcile_posts.py --apply
  python3 scripts/reconcile_posts.py --from-youtube      # dry run: youtube -> missing posts
  python3 scripts/reconcile_posts.py --from-youtube --apply
  python3 scripts/reconcile_posts.py --pair <calendar_id> <video_id> --apply
  python3 scripts/reconcile_posts.py --unlink <video_id> --apply
"""
import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from factory_worker import Supa, load_env  # noqa: E402

IST = ZoneInfo("Asia/Kolkata")
# A post in any of these states proves the video reached YouTube.
SHIPPED = ("published", "armed", "scheduled", "uploading")
# The statuses the triage feed selects for -- the rows that get stuck.
STUCK = ("queued", "produced")


def norm_title(t):
    """Lowercase alphanumerics, collapsed spaces. Emojis, punctuation and the
    "| New Hindi Love Song 2026 | ..." suffixes must not defeat a comparison."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (t or "").lower())).strip()


def title_matches(a, b):
    """True when one normalised title is a prefix of the other. Deliberately
    strict: it only ever separates candidates that already share a day."""
    a, b = norm_title(a), norm_title(b)
    if not a or not b:
        return False
    n = min(len(a), len(b), 18)
    return n >= 6 and a[:n] == b[:n]


def ist_date(iso):
    if not iso:
        return None
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(IST).date().isoformat()


def yt_uploads(channel_key, limit=25):
    """Recent uploads for a channel: public ones AND scheduled-private ones,
    because a piece armed for tomorrow has shipped as far as this app cares."""
    from googleapiclient.discovery import build
    from yt_upload import get_creds
    from factory_worker import UPLOAD_DEFAULTS
    from backfill_calendar_published import creds_key

    creds = get_creds(creds_key(UPLOAD_DEFAULTS[channel_key]["token_file"]), False)
    yt = build("youtube", "v3", credentials=creds)
    ch = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0]
    up = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    pl = yt.playlistItems().list(part="contentDetails", playlistId=up,
                                 maxResults=min(limit, 50)).execute()
    ids = [i["contentDetails"]["videoId"] for i in pl.get("items", [])]
    if not ids:
        return []
    out = []
    for chunk in (ids[i:i + 50] for i in range(0, len(ids), 50)):
        vr = yt.videos().list(part="snippet,status", id=",".join(chunk)).execute()
        for v in vr.get("items", []):
            st, sn = v["status"], v["snippet"]
            privacy = st.get("privacyStatus")
            pub = st.get("publishAt") or sn.get("publishedAt")
            if not pub or privacy == "unlisted":
                continue
            out.append({
                "video_id": v["id"], "title": sn["title"], "publish_at": pub,
                "day": ist_date(pub),
                # private with a publishAt is armed and waiting; public is live
                "status": "published" if privacy == "public" else "scheduled",
            })
    return out


def from_youtube(supa, apply):
    """Write the missing post for any calendar row whose video is on YouTube."""
    cal = supa.select("factory_calendar", "select=*&limit=2000")
    posts = supa.select("factory_posts", "select=*&limit=1000")
    linked = {p["calendar_id"] for p in posts if p.get("calendar_id")}
    known_vids = {p["video_id"] for p in posts if p.get("video_id")}

    stuck = defaultdict(list)
    for it in cal:
        if it.get("id") in linked or str(it.get("status") or "") not in STUCK:
            continue
        day = str(it.get("planned_date") or "")[:10]
        if day:
            stuck[(it.get("channel_key"), day)].append(it)

    channels = sorted({ch for ch, _ in stuck if ch and not ch.startswith("_")})
    made, skipped = [], []
    for ch in channels:
        try:
            vids = yt_uploads(ch)
        except Exception as e:  # noqa: BLE001
            print(f"  {ch}: could not read YouTube — {type(e).__name__}: {str(e)[:90]}")
            continue
        by_day = defaultdict(list)
        for v in vids:
            by_day[v["day"]].append(v)
        for (c, day), rows in sorted(stuck.items()):
            if c != ch:
                continue
            cands = [v for v in by_day.get(day, []) if v["video_id"] not in known_vids]
            if not cands:
                continue
            for it in rows:
                # A title match is REQUIRED here. Unlike the linking mode, this
                # one CREATES the assertion "this piece is this video", and a
                # wrong one permanently attributes another video's analytics to
                # this piece. Counting alone proposed pairing "Your AI Forgets
                # You Every Single Chat" with "Google Just Put AI In Your Kid's
                # Classroom" purely because each was alone on its day.
                hit = [v for v in cands if title_matches(it.get("title"), v["title"])]
                if len(hit) != 1:
                    if cands:
                        skipped.append((it, cands))
                    continue
                v = hit[0]
                cands = [x for x in cands if x["video_id"] != v["video_id"]]
                known_vids.add(v["video_id"])
                made.append((it, v))

    print(f"=== {len(made)} MISSING POST(S) TO WRITE ===")
    for it, v in made:
        print(f"  {it['planned_date']} {it['channel_key']}")
        print(f"      piece : {str(it.get('title'))[:64]}")
        print(f"      video : {v['title'][:64]}  [{v['video_id']}] {v['status']}")
    if skipped:
        print(f"\n=== {len(skipped)} piece(s) a title could not separate — not touched ===")
        for it, cands in skipped:
            print(f"  {it['planned_date']} {it['channel_key']}: {str(it.get('title'))[:52]}")
            for v in cands:
                print(f"      candidate: {v['title'][:56]}  [{v['video_id']}]")
    if not apply:
        print("\nDRY RUN — nothing written. Add --apply to write these posts.")
        return
    ok = 0
    for it, v in made:
        try:
            supa.insert("factory_posts", [{
                "channel_key": it["channel_key"],
                "calendar_id": it["id"],
                "video_id": v["video_id"],
                "yt_title": v["title"][:100],
                "publish_at": v["publish_at"],
                "status": v["status"],
                "audience": "general",
                "synthetic": True,
            }])
            ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"  FAILED {v['video_id']}: {e}")
    print(f"\nwrote {ok} of {len(made)} post(s).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="write the links (default is a dry run)")
    ap.add_argument("--from-youtube", action="store_true",
                    help="create the missing post for pieces whose video is on YouTube")
    ap.add_argument("--pair", nargs=2, metavar=("CALENDAR_ID", "VIDEO_ID"),
                    help="resolve one pair by hand, for a day titles cannot separate")
    ap.add_argument("--unlink", metavar="VIDEO_ID",
                    help="clear a wrong link. Every pairing rule here is a "
                         "judgement about which video came from which piece, so "
                         "undoing one has to be as easy as making it.")
    args = ap.parse_args()

    env = load_env()
    supa = Supa(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])

    if args.unlink:
        rows = supa.select("factory_posts",
                           f"video_id=eq.{args.unlink}&select=id,video_id,yt_title,calendar_id")
        if not rows:
            sys.exit(f"no post carries video {args.unlink}")
        r = rows[0]
        if not r.get("calendar_id"):
            print(f"{args.unlink} is already unlinked."); return
        print(f"unlink {args.unlink} ({str(r.get('yt_title'))[:52]}) from {r['calendar_id']}")
        if not args.apply:
            print("DRY RUN — add --apply to write it.")
            return
        supa.patch("factory_posts", f"id=eq.{r['id']}", {"calendar_id": None})
        print("unlinked.")
        return

    if args.pair:
        cal_id, vid = args.pair
        rows = supa.select("factory_posts", f"video_id=eq.{vid}&select=id,video_id,yt_title")
        if not rows:
            sys.exit(f"no post carries video {vid}")
        print(f"pair {cal_id} <- {vid} ({str(rows[0].get('yt_title'))[:50]})")
        if not args.apply:
            print("DRY RUN — add --apply to write it.")
            return
        supa.patch("factory_posts", f"id=eq.{rows[0]['id']}", {"calendar_id": cal_id})
        print("linked.")
        return

    if args.from_youtube:
        from_youtube(supa, args.apply)
        return

    posts = supa.select("factory_posts", "select=*&limit=1000")
    cal = supa.select("factory_calendar", "select=*&limit=2000")

    linked_cal_ids = {p["calendar_id"] for p in posts if p.get("calendar_id")}
    linked_job_ids = {p["job_id"] for p in posts if p.get("job_id")}

    # Unmatched on each side, bucketed by (channel, day).
    free_posts = defaultdict(list)
    for p in posts:
        if p.get("calendar_id"):
            continue
        if str(p.get("status") or "").lower() not in SHIPPED:
            continue
        day = ist_date(p.get("publish_at"))
        if not day:
            continue
        free_posts[(p.get("channel_key"), day)].append(p)

    free_cal = defaultdict(list)
    for it in cal:
        if it.get("id") in linked_cal_ids:
            continue
        if it.get("job_id") and it["job_id"] in linked_job_ids:
            continue  # already reachable through the older job_id link
        if str(it.get("status") or "") not in STUCK:
            continue
        day = str(it.get("planned_date") or "")[:10]
        if not day:
            continue
        free_cal[(it.get("channel_key"), day)].append(it)

    pairs, ambiguous, orphan_posts, orphan_cal = [], [], [], []
    for key, cands in sorted(free_cal.items()):
        ps = free_posts.get(key, [])
        if len(cands) == 1 and len(ps) == 1:
            pairs.append((cands[0], ps[0]))
        elif cands and ps:
            ambiguous.append((key, cands, ps))
        elif cands:
            orphan_cal.append((key, cands))
    for key, ps in sorted(free_posts.items()):
        if key not in free_cal:
            orphan_posts.append((key, ps))

    print(f"posts: {len(posts)}  ·  calendar rows: {len(cal)}")
    print(f"already linked: {len(linked_cal_ids)}\n")

    print(f"=== {len(pairs)} UNAMBIGUOUS PAIR(S) ===")
    for it, p in pairs:
        print(f"  {it['planned_date']} {it['channel_key']}")
        print(f"      piece : {str(it.get('title'))[:64]}")
        print(f"      video : {str(p.get('yt_title'))[:64]}  [{p.get('video_id')}] {p.get('status')}")

    if ambiguous:
        print(f"\n=== {len(ambiguous)} AMBIGUOUS DAY(S) — not touched ===")
        for (ch, day), cands, ps in ambiguous:
            print(f"  {day} {ch}: {len(cands)} unlinked piece(s) vs {len(ps)} unlinked video(s)")
            for c in cands:
                print(f"      piece : {str(c.get('title'))[:60]}")
            for p in ps:
                print(f"      video : {str(p.get('yt_title'))[:60]}  [{p.get('video_id')}]")

    if orphan_cal:
        n = sum(len(c) for _, c in orphan_cal)
        print(f"\n=== {n} piece(s) with no video that day — nothing proves they shipped ===")
        for (ch, day), cands in orphan_cal:
            for c in cands:
                print(f"  {day} {ch}: {str(c.get('title'))[:60]}")

    if not args.apply:
        print("\nDRY RUN — nothing written. Re-run with --apply to write these links.")
        return

    ok = 0
    for it, p in pairs:
        try:
            supa.patch("factory_posts", f"id=eq.{p['id']}", {"calendar_id": it["id"]})
            ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"  FAILED {p.get('video_id')}: {e}")
    print(f"\nlinked {ok} of {len(pairs)} pair(s).")


if __name__ == "__main__":
    main()
