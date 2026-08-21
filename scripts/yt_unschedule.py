#!/usr/bin/env python3
"""
yt_unschedule.py — HOLD a scheduled-but-not-yet-public YouTube video by removing its
auto-publish time and leaving it plain `private`. Fully reversible (reschedule any time
with yt_upload's --publish-at flow, or in Studio).

Safety: it REFUSES to touch a video that is already `public`, and only acts when the
video is currently private with a publishAt set (i.e. a genuinely scheduled draft).

    python scripts/yt_unschedule.py --channel claude-tricks --video VIDEO_ID [--apply]

Without --apply it only PRINTS the current state (dry run).
"""
import argparse, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--apply", action="store_true", help="actually write; default is dry-run")
    a = ap.parse_args()

    from yt_upload import get_creds
    from googleapiclient.discovery import build
    yt = build("youtube", "v3", credentials=get_creds(a.channel, False))

    r = yt.videos().list(part="snippet,status", id=a.video).execute()
    items = r.get("items", [])
    if not items:
        sys.exit(f"video {a.video} not found on channel {a.channel}")
    v = items[0]
    st = v["status"]
    title = v["snippet"]["title"]
    print(f"video   : {a.video}")
    print(f"title   : {title}")
    print(f"privacy : {st.get('privacyStatus')}")
    print(f"publishAt: {st.get('publishAt', '(none)')}")

    if st.get("privacyStatus") == "public":
        sys.exit("REFUSING: video is already public — nothing to hold.")
    if not st.get("publishAt"):
        print("nothing to do: no publishAt set (already unscheduled).")
        return
    if not a.apply:
        print("\nDRY RUN — rerun with --apply to remove the schedule and hold it private.")
        return

    # Send back only the status part, privacy=private, publishAt cleared.
    new_status = {"privacyStatus": "private", "selfDeclaredMadeForKids": st.get("madeForKids", False)}
    # preserve synthetic-media disclosure if present
    if "containsSyntheticMedia" in st:
        new_status["containsSyntheticMedia"] = st["containsSyntheticMedia"]
    yt.videos().update(part="status", body={"id": a.video, "status": new_status}).execute()

    chk = yt.videos().list(part="status", id=a.video).execute()["items"][0]["status"]
    print(f"\n✅ HELD. privacy now: {chk.get('privacyStatus')}  publishAt: {chk.get('publishAt', '(none)')}")

if __name__ == "__main__":
    main()
