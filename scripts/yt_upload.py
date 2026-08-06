#!/usr/bin/env python3
"""
YouTube uploader / scheduler for the whole channel network.
ONE GCP project (lulla-pipeline) + ONE client_secret + ONE token file PER channel.

--- Authorize a channel (once) ---
Sign into that channel's Google account in your default browser, then:
    python3 scripts/yt_upload.py --channel poly --auth
A browser opens -> pick the target channel -> Allow. Token saved to secrets/token_<channel>.json.
(Existing "Lulla's Moonlit Garden" already lives in secrets/token.json as --channel lulla.)

--- Upload immediately as a private draft ---
    python3 scripts/yt_upload.py --channel poly --audience kids \
      --video channels/language-abc/renders/ep01_final.mp4 \
      --title "Say Hello in 5 Languages! ..." \
      --desc-file channels/language-abc/docs/ep01_description.txt \
      --tags "hello song,spanish for kids,poly the parrot" --category 27 \
      --thumbnail channels/language-abc/assets/thumbnail/thumb_A.jpg

--- Schedule (auto-publish at a UTC time) ---  add:
      --publish-at 2026-08-05T15:00:00Z
"""
import argparse, os, sys

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube",
          # force-ssl is required by commentThreads.insert/list (scripts/yt_engage.py).
          # A channel only gains it on its next `--auth` re-consent. This list is
          # what we ASK FOR at consent time -- it is never what an existing token
          # HAS. See get_creds(): loading a token with this list attached and
          # writing it back is what bricked every channel on 6 Aug 2026.
          "https://www.googleapis.com/auth/youtube.force-ssl"]
CLIENT = "secrets/client_secret.json"

# Channel keys whose token file is NOT secrets/token_<key>.json.
# `language-abc` is the key UPLOAD_DEFAULTS / channels/ use for Poly, but the
# token was authorized under "poly" -- without this alias every network-wide
# tool (verify_uploads.py, daily_check.py) dies on "no token for 'language-abc'".
TOKEN_ALIASES = {"lulla": "token.json", "pip": "token.json",
                 "language-abc": "token_poly.json"}

def token_path(ch):
    return "secrets/" + TOKEN_ALIASES.get(ch, f"token_{ch}.json")

def get_creds(channel, do_auth):
    """Load (or mint) this channel's credentials.

    🔴 Load with the token's OWN scopes, never the module-level SCOPES, and only
    write the file back when the credentials actually changed. Doing otherwise
    silently bricks every channel (measured 6 Aug 2026): passing SCOPES to
    from_authorized_user_file() stamps the *aspirational* list onto the object,
    and the unconditional to_json() write-back then persists it -- so the first
    run after force-ssl joined SCOPES rewrote three token files claiming a scope
    the user had never consented to. The next refresh asks Google for that scope
    against a grant that lacks it and dies `invalid_scope: Bad Request`, taking
    down uploads, network_stats, verify_uploads and daily_check at once.
    A channel gains a new scope ONLY through an interactive `--auth` consent.
    """
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    tp = token_path(channel); creds = None; dirty = False
    if os.path.exists(tp):
        creds = Credentials.from_authorized_user_file(tp)  # scopes come from the file
    if do_auth or not creds:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT, SCOPES)
        creds = flow.run_local_server(port=0, prompt="consent")
        dirty = True
    elif not creds.valid and creds.refresh_token:
        creds.refresh(Request())
        dirty = True
    if dirty:
        os.makedirs("secrets", exist_ok=True)
        with open(tp, "w") as f:
            f.write(creds.to_json())
    return creds

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True, help="channel key -> secrets/token_<key>.json (lulla=token.json)")
    ap.add_argument("--auth", action="store_true", help="(re)run OAuth consent for this channel and exit")
    ap.add_argument("--video")
    ap.add_argument("--title")
    ap.add_argument("--desc-file")
    ap.add_argument("--tags", default="")
    ap.add_argument("--category", default="27", help="27=Education 10=Music 24=Entertainment")
    ap.add_argument("--audience", choices=["kids", "general"], help="kids => selfDeclaredMadeForKids=true (COPPA)")
    ap.add_argument("--synthetic", action="store_true",
                    help="disclose realistic AI/altered content (status.containsSyntheticMedia=true). "
                         "REQUIRED for AI Unpacked (photoreal AI host).")
    ap.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    ap.add_argument("--publish-at", help="RFC3339 UTC e.g. 2026-08-05T15:00:00Z (schedules; forces private until then)")
    ap.add_argument("--thumbnail")
    ap.add_argument("--playlist", help="playlistId to append to")
    ap.add_argument("--video-id", help="recovery mode: skip upload, just set "
                    "--thumbnail / --playlist on this existing video id")
    a = ap.parse_args()

    creds = get_creds(a.channel, a.auth)
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    yt = build("youtube", "v3", credentials=creds)
    who = yt.channels().list(part="snippet", mine=True).execute()["items"][0]["snippet"]["title"]
    print(f">> authorized channel: {who}  (token: {token_path(a.channel)})")

    # Post-upload extras must NEVER fail the run: once the video is up, a crash
    # here reads as "upload failed" upstream and invites a duplicate upload
    # (learned 2026-08-05: thumbnails.set 403 'forbidden' -- channel not
    # phone-verified -- marked an uploaded+scheduled post as FAILED).
    def set_extras(vid):
        if a.thumbnail:
            try:
                yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(a.thumbnail)).execute()
                print(">> thumbnail set")
            except HttpError as e:
                hint = ""
                if e.resp.status == 403:
                    hint = (" -- custom thumbnails need one-time PHONE VERIFICATION "
                            "for this channel: youtube.com/features (then re-run with "
                            f"--video-id {vid} --thumbnail ...)")
                print(f">> WARNING: thumbnail not set ({e.resp.status}){hint}")
        if a.playlist:
            try:
                yt.playlistItems().insert(part="snippet", body={"snippet": {"playlistId": a.playlist,
                    "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
                print(">> added to playlist")
            except HttpError as e:
                print(f">> WARNING: playlist add failed ({e.resp.status})")

    if a.video_id:
        set_extras(a.video_id)
        print(f">> DONE (recovery mode) https://youtu.be/{a.video_id}")
        return
    if a.auth or not a.video:
        print(">> auth OK. re-run with --video ... to upload." if a.auth else ">> nothing to upload.")
        return
    if not a.title or a.audience is None:
        sys.exit("!! --title and --audience are required to upload")

    desc = open(a.desc_file).read() if a.desc_file else ""
    body = {
        "snippet": {"title": a.title, "description": desc,
                    "tags": [t.strip() for t in a.tags.split(",") if t.strip()],
                    "categoryId": a.category},
        "status": {"privacyStatus": "private" if a.publish_at else a.privacy,
                   "selfDeclaredMadeForKids": (a.audience == "kids")},
    }
    if a.synthetic:
        body["status"]["containsSyntheticMedia"] = True
    if a.publish_at:
        body["status"]["publishAt"] = a.publish_at
    media = MediaFileUpload(a.video, chunksize=-1, resumable=True, mimetype="video/*")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        st, resp = req.next_chunk()
        if st:
            print(f"   uploading {int(st.progress()*100)}%")
    vid = resp["id"]
    print(f">> UPLOADED: https://youtu.be/{vid}  (madeForKids={a.audience=='kids'}, "
          f"{'scheduled '+a.publish_at if a.publish_at else a.privacy})", flush=True)
    set_extras(vid)

if __name__ == "__main__":
    main()
