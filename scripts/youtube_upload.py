#!/usr/bin/env python3
"""
Upload + schedule a video to YouTube via the Data API v3 (the automated path).

One-time setup: see docs/OAUTH-SETUP.md (Google Cloud project + OAuth client).
Put the OAuth client JSON at secrets/client_secret.json. First run opens a browser
to authorize the LULLA brand account; the token is cached at secrets/token.json.

Examples:
  # schedule for the launch slot with thumbnail
  python3 scripts/youtube_upload.py \
    --file renders/song01_full_v2.mp4 \
    --title "Little Light, Goodnight 🌙 Calm Bedtime Songs for Babies | Lulla's Moonlit Garden" \
    --desc-file songs/desc_01.txt \
    --tags "bedtime songs,lullaby,baby sleep music,calm songs for toddlers,nursery rhymes" \
    --thumbnail assets/thumbnail/thumb01_final_A.jpg \
    --publish-at "2026-08-04T16:00:00+05:30"

  # publish now (public) instead of scheduling: omit --publish-at and pass --privacy public
"""
import argparse, os, sys, time

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
except ImportError:
    sys.exit("Missing deps. Run: pip install -r requirements.txt")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CLIENT_SECRET = os.path.join(ROOT, "secrets", "client_secret.json")
TOKEN = os.path.join(ROOT, "secrets", "token.json")

def get_service():
    creds = None
    if os.path.exists(TOKEN):
        creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET):
                sys.exit(f"Missing {CLIENT_SECRET} — see docs/OAUTH-SETUP.md")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
            print(">> A browser will open — sign in and CHOOSE 'Lulla's Moonlit Garden' (the brand account).")
            creds = flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(TOKEN), exist_ok=True)
        open(TOKEN, "w").write(creds.to_json())
    return build("youtube", "v3", credentials=creds)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auth-only", action="store_true", help="just authorize + cache the token, no upload")
    ap.add_argument("--file")
    ap.add_argument("--title")
    ap.add_argument("--description", default="")
    ap.add_argument("--desc-file", default="", help="read description from a text file (overrides --description)")
    ap.add_argument("--tags", default="", help="comma-separated")
    ap.add_argument("--category", default="10", help="10=Music, 27=Education")
    ap.add_argument("--thumbnail", default="")
    ap.add_argument("--playlist-id", default="")
    ap.add_argument("--publish-at", default="", help="RFC3339, e.g. 2026-08-04T16:00:00+05:30 (schedules; privacy forced to private)")
    ap.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    args = ap.parse_args()

    if args.auth_only:
        get_service()
        print(">> Authorized ✓  token cached at secrets/token.json")
        return
    if not args.file or not args.title:
        sys.exit("--file and --title are required (or use --auth-only)")

    description = open(args.desc_file, encoding="utf-8").read() if args.desc_file else args.description
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    status = {"selfDeclaredMadeForKids": True}
    if args.publish_at:
        status["privacyStatus"] = "private"
        status["publishAt"] = args.publish_at
    else:
        status["privacyStatus"] = args.privacy

    body = {
        "snippet": {"title": args.title, "description": description, "tags": tags, "categoryId": args.category},
        "status": status,
    }

    yt = get_service()
    print(f">> Uploading {args.file} ...")
    media = MediaFileUpload(args.file, chunksize=1024 * 1024 * 8, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        s, resp = req.next_chunk()
        if s:
            print(f"   {int(s.progress() * 100)}%")
    vid = resp["id"]
    print(f">> DONE video: https://youtu.be/{vid}  (status: {status['privacyStatus']}"
          + (f", publishAt {args.publish_at}" if args.publish_at else "") + ")")

    if args.thumbnail:
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(args.thumbnail)).execute()
            print("   thumbnail set ✓")
        except HttpError as e:
            print(f"   !! thumbnail failed (channel likely needs phone verification): {e}")

    if args.playlist_id:
        yt.playlistItems().insert(part="snippet", body={
            "snippet": {"playlistId": args.playlist_id,
                        "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
        print("   added to playlist ✓")

if __name__ == "__main__":
    main()
