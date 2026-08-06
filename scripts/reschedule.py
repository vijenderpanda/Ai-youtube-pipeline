#!/usr/bin/env python3
"""
Reschedule a YouTube video's publishAt (keeps it private-until-then + Made-for-Kids).

  python3 scripts/reschedule.py --video hfwxEYiVYTA --publish-at "2026-08-09T16:00:00+05:30"
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from youtube_upload import get_service

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--publish-at", required=True, help="RFC3339, e.g. 2026-08-09T16:00:00+05:30")
    a = ap.parse_args()
    yt = get_service()
    cur = yt.videos().list(part="status", id=a.video).execute()["items"][0]["status"]
    body = {"id": a.video, "status": {
        "privacyStatus": "private",
        "publishAt": a.publish_at,
        "selfDeclaredMadeForKids": cur.get("selfDeclaredMadeForKids", True),
        "license": cur.get("license", "youtube"),
    }}
    yt.videos().update(part="status", body=body).execute()
    print(f">> {a.video} rescheduled to {a.publish_at} (private until then, made-for-kids kept)")

if __name__ == "__main__":
    main()
