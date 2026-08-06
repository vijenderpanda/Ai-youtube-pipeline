#!/usr/bin/env python3
"""
Backfill already-shipped YouTube videos onto the factory calendar (+ posts).

For each factory channel, pulls the real uploads list from the YouTube Data
API (snippet.publishedAt is the ground truth for public videos — a public
video has no status.publishAt, playbook §9) and, for every PUBLIC video that
went live inside the date window (local IST dates), writes the pair the
dashboard joins on:

  factory_calendar  (status 'produced', origin 'backfill')
  factory_posts     (status 'published', video_id + real publish_at)

linked by a shared synthetic job_id — there is no factory_jobs row; the
calendar->post join is job_id-based and the job itself is optional (the UI
tolerates a missing job, and CalendarDrawer hides "View job" for backfill).

Idempotent: a video_id already present in factory_posts is skipped (covers
worker-scheduled posts), and a calendar item whose title matches the video
in the same window is skipped too (covers hand-planned items). Never touches
factory_jobs, so it is safe to run while the worker daemon is live.

Usage:
  python3 scripts/backfill_calendar_published.py --dry-run
  python3 scripts/backfill_calendar_published.py                     # 2026-08-01..2026-08-04
  python3 scripts/backfill_calendar_published.py --since 2026-08-01 --until 2026-08-04
"""
import argparse
import re
import sys
import uuid
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from factory_worker import UPLOAD_DEFAULTS, Supa, load_env, now_iso  # noqa: E402

IST = ZoneInfo("Asia/Kolkata")


def creds_key(token_file):
    """UPLOAD_DEFAULTS token_file -> the yt_upload.get_creds channel key
    (token.json belongs to lulla; token_<key>.json -> <key>)."""
    if token_file == "token.json":
        return "lulla"
    return token_file[len("token_"):-len(".json")]


def norm_title(t):
    """Loose title key: lowercase alphanumerics + collapsed spaces (emojis,
    punctuation and episode suffixes must not defeat the duplicate check)."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (t or "").lower())).strip()


def fetch_public_in_window(key, since, until):
    """All PUBLIC uploads of the channel whose IST publish date is in
    [since, until]. Returns [{video_id, title, published_utc, ist_date}]."""
    from googleapiclient.discovery import build
    from yt_upload import get_creds
    creds = get_creds(creds_key(UPLOAD_DEFAULTS[key]["token_file"]), False)
    yt = build("youtube", "v3", credentials=creds)
    ch = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, page = [], None
    while True:
        pl = yt.playlistItems().list(part="contentDetails", playlistId=uploads,
                                     maxResults=50, pageToken=page).execute()
        ids += [i["contentDetails"]["videoId"] for i in pl.get("items", [])]
        page = pl.get("nextPageToken")
        if not page or len(ids) >= 200:
            break
    out = []
    for chunk in (ids[i:i + 50] for i in range(0, len(ids), 50)):
        vr = yt.videos().list(part="snippet,status", id=",".join(chunk)).execute()
        for v in vr.get("items", []):
            if v["status"].get("privacyStatus") != "public":
                continue
            pub = v["snippet"].get("publishedAt")
            if not pub:
                continue
            ist_day = datetime.fromisoformat(pub.replace("Z", "+00:00")).astimezone(IST).date()
            if since <= ist_day <= until:
                out.append({"video_id": v["id"], "title": v["snippet"]["title"],
                            "published_utc": pub, "ist_date": ist_day})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=date.fromisoformat, default=date(2026, 8, 1))
    ap.add_argument("--until", type=date.fromisoformat, default=date(2026, 8, 4))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    env = load_env()
    supa = Supa(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
    added = 0

    for key, defaults in UPLOAD_DEFAULTS.items():
        try:
            vids = fetch_public_in_window(key, a.since, a.until)
        except Exception as e:  # per-channel auth/API issues must not kill the rest
            print(f"[{key}] SKIPPED channel — YouTube fetch failed: {e}")
            continue

        known_ids = {p["video_id"] for p in supa.select(
            "factory_posts", f"channel_key=eq.{key}&select=video_id") if p.get("video_id")}
        cal_rows = supa.select(
            "factory_calendar",
            f"channel_key=eq.{key}&planned_date=gte.{a.since}&planned_date=lte.{a.until}"
            "&select=title,planned_date")
        cal_titles = {norm_title(r["title"]) for r in cal_rows}

        for v in vids:
            if v["video_id"] in known_ids:
                print(f"[{key}] skip (post exists)      {v['ist_date']}  {v['title'][:60]}")
                continue
            nt = norm_title(v["title"])
            if any(ct and (ct in nt or nt in ct) for ct in cal_titles):
                print(f"[{key}] skip (calendar match)   {v['ist_date']}  {v['title'][:60]}")
                continue
            print(f"[{key}] ADD  {v['ist_date']}  {v['title'][:70]}")
            added += 1
            if a.dry_run:
                continue
            job_id = str(uuid.uuid4())
            supa.insert("factory_calendar", [{
                "channel_key": key,
                "planned_date": v["ist_date"].isoformat(),
                "title": v["title"],
                "brief": f"Backfilled from YouTube — published {v['published_utc']} "
                         f"(https://youtu.be/{v['video_id']})",
                "type": "produce_short",
                "status": "produced",
                "origin": "backfill",
                "kind": "content",
                "job_id": job_id,
            }])
            supa.insert("factory_posts", [{
                "channel_key": key,
                "job_id": job_id,
                "yt_title": v["title"][:100],
                "video_id": v["video_id"],
                "publish_at": v["published_utc"],
                "status": "published",
                "audience": defaults.get("audience"),
                "synthetic": bool(defaults.get("synthetic")),
                "updated_at": now_iso(),
            }])

    print(f"\n{'would add' if a.dry_run else 'added'} {added} calendar+post pair(s) "
          f"for {a.since}..{a.until}")


if __name__ == "__main__":
    main()
