#!/usr/bin/env python3
"""
Post-publish ENGAGEMENT CLI for the whole channel network.

Automates the two manual post-publish steps that calendar briefs keep asking for
and no generator implements:
  1. post the pin comment on our own freshly-published video
  2. count keyword comments (a comment-CTA's go/no-go signal)

--- Post the pin comment -------------------------------------------------------
    python3 scripts/yt_engage.py --channel aashiqana --video VIDEO_ID \
        --pin "Team 1 ya Team 2?"

*** THE PIN ITSELF IS NOT AUTOMATED — AND THIS TOOL NEVER CLAIMS IT WAS. ***
The YouTube Data API v3 has NO endpoint for pinning a comment (pinning is a
Studio/web-UI-only action; `comments`/`commentThreads` expose insert/list/update
/markAsSpam/setModerationStatus/delete, and nothing that sets the pinned flag).
So this tool does the 95% that IS automatable: it POSTS the comment as the
channel, logs the comment id, and prints the exact Studio deep-link where the
human clicks "Pin" once. The forgotten-TODO becomes a 5-second click.

--- Count keyword comments (the demand signal) ---------------------------------
    python3 scripts/yt_engage.py --channel claude-tricks --video VIDEO_ID \
        --count-keyword FACTORY --days 7 --json renders_out/factory_count.json

Case-insensitive SUBSTRING match, over top-level comments and replies. Emits
{video_id, keyword, total, unique_authors, sample: [first 10 texts]} — the
go/no-go input for a "comment KEYWORD for the long-form" CTA episode.

--- Rules baked in -------------------------------------------------------------
MFK GUARD: comments are disabled on Made-for-Kids videos (COPPA). The tool reads
  status.madeForKids FIRST and exits 0 with a clear message instead of erroring.
  Kids channels (Lulla, Poly, Rumble Trucks) can therefore never use this tool —
  the kids/adult cross-cluster separation stays intact by construction.
SAFETY: this tool NEVER deletes, hides, moderates or marks-as-spam anyone's
  comments. It only calls commentThreads.insert (our own comment) and
  commentThreads.list (read). Same doctrine as "never hard-delete via
  automation" — destructive moderation stays a human action in Studio.

--- Auth / one-time scope upgrade ----------------------------------------------
Auth reuses the per-channel OAuth tokens + flow from scripts/yt_upload.py
(secrets/token_<key>.json; lulla/pip = secrets/token.json).

commentThreads.insert/list require the `youtube.force-ssl` scope, which the
upload-era tokens do NOT have (they carry youtube.upload + youtube). force-ssl
was therefore added to yt_upload.SCOPES; each channel picks it up on its next
consent. Uploads are unaffected. One-time per channel, sign into that channel's
Google account in your default browser first:

    python3 scripts/yt_engage.py --channel aashiqana --auth

Any 403 "insufficient authentication scopes" from this tool prints that exact
command instead of a traceback. (force-ssl is a broad scope that *could* delete
comments — this tool never calls those endpoints; see SAFETY above.)

Every run appends a receipt to channels/<key>/engagement_log.json.
"""
import argparse, json, os, sys
from datetime import datetime, timedelta, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
os.chdir(REPO)

# channel key -> channels/<dir>/ (keys whose folder name differs from the key)
CHANNEL_DIR = {
    "poly": "language-abc",
    "lulla": "pip-moonlit-garden",
    "pip": "pip-moonlit-garden",
}


def log_path(key):
    d = os.path.join(REPO, "channels", CHANNEL_DIR.get(key, key))
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "engagement_log.json")


def append_log(key, entry):
    p = log_path(key)
    try:
        rows = json.load(open(p))
        if not isinstance(rows, list):
            rows = []
    except Exception:
        rows = []
    rows.append(entry)
    with open(p, "w") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    print(f">> logged -> {os.path.relpath(p, REPO)}")


def scope_hint(key):
    return (f"!! this channel's token lacks the youtube.force-ssl scope that "
            f"commentThreads requires.\n"
            f"   Fix once (opens a browser — sign into the {key} Google account first):\n"
            f"       python3 scripts/yt_engage.py --channel {key} --auth")


def get_video(yt, vid):
    r = yt.videos().list(part="snippet,status", id=vid).execute().get("items", [])
    if not r:
        sys.exit(f"!! video {vid} not found (or not visible to this channel's token)")
    return r[0]


def do_pin(yt, key, vid, text, title):
    """Post the comment. NOTE: does NOT pin it — see module docstring."""
    from googleapiclient.errors import HttpError
    body = {"snippet": {"videoId": vid,
                        "topLevelComment": {"snippet": {"textOriginal": text}}}}
    try:
        thread = yt.commentThreads().insert(part="snippet", body=body).execute()
    except HttpError as e:
        if e.resp.status in (401, 403) and "insufficient" in str(e).lower():
            sys.exit(scope_hint(key))
        raise
    cid = thread["snippet"]["topLevelComment"]["id"]
    studio = f"https://studio.youtube.com/video/{vid}/comments"
    print(f">> COMMENT POSTED (not pinned): {text!r}")
    print(f"   comment id : {cid}")
    print(f"   public url : https://www.youtube.com/watch?v={vid}&lc={cid}")
    print(f">> PIN IT (5 seconds, human step — API has no pin endpoint):")
    print(f"   {studio}")
    print(f"   -> find this comment -> ⋮ -> Pin")
    append_log(key, {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "action": "pin_comment_posted",
        "video_id": vid, "video_title": title,
        "comment_id": cid, "text": text,
        "pinned": False, "pin_url": studio,
        "note": "posted via commentThreads.insert; PIN IS A MANUAL STUDIO CLICK "
                "(Data API v3 has no pin endpoint)",
    })


def do_count(yt, key, vid, keyword, days, out_json, title):
    from googleapiclient.errors import HttpError
    cutoff = None
    if days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    kw = keyword.lower()
    total, authors, sample, scanned = 0, set(), [], 0
    page = None
    while True:
        try:
            resp = yt.commentThreads().list(
                part="snippet,replies", videoId=vid, maxResults=100,
                textFormat="plainText", order="time", pageToken=page).execute()
        except HttpError as e:
            if e.resp.status == 403 and "commentsDisabled" in str(e):
                print(">> comments are DISABLED on this video — nothing to count.")
                return
            if e.resp.status in (401, 403) and "insufficient" in str(e).lower():
                sys.exit(scope_hint(key))
            raise
        for th in resp.get("items", []):
            comments = [th["snippet"]["topLevelComment"]]
            comments += th.get("replies", {}).get("comments", [])
            for c in comments:
                s = c["snippet"]
                scanned += 1
                if cutoff:
                    pub = datetime.fromisoformat(s["publishedAt"].replace("Z", "+00:00"))
                    if pub < cutoff:
                        continue
                txt = s.get("textOriginal") or s.get("textDisplay") or ""
                if kw in txt.lower():
                    total += 1
                    authors.add(s.get("authorChannelId", {}).get("value") or
                                s.get("authorDisplayName", "?"))
                    if len(sample) < 10:
                        sample.append(txt.strip()[:300])
        page = resp.get("nextPageToken")
        if not page:
            break

    result = {"video_id": vid, "keyword": keyword, "total": total,
              "unique_authors": len(authors), "sample": sample}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f">> scanned {scanned} comment(s)"
          f"{f' — counted only the last {days}d' if days else ''}")
    if out_json:
        os.makedirs(os.path.dirname(os.path.abspath(out_json)) or ".", exist_ok=True)
        with open(out_json, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f">> wrote {out_json}")
    append_log(key, {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "action": "keyword_count",
        "video_id": vid, "video_title": title,
        "keyword": keyword, "days": days,
        "total": total, "unique_authors": len(authors), "scanned": scanned,
    })


def main():
    ap = argparse.ArgumentParser(
        description="Post-publish engagement: post the pin comment / count keyword comments. "
                    "Never deletes or moderates comments.")
    ap.add_argument("--channel", required=True,
                    help="channel key -> secrets/token_<key>.json (lulla/pip = token.json)")
    ap.add_argument("--video", help="YouTube video id (11 chars)")
    ap.add_argument("--auth", action="store_true",
                    help="(re)run OAuth consent for this channel to grant the "
                         "youtube.force-ssl scope that commentThreads needs, then exit")
    ap.add_argument("--pin", metavar="TEXT",
                    help="post this comment as the channel, then print the Studio "
                         "deep-link for the manual one-tap pin (API cannot pin)")
    ap.add_argument("--count-keyword", metavar="WORD",
                    help="count comments containing WORD (case-insensitive substring)")
    ap.add_argument("--days", type=int, default=0,
                    help="only count comments from the last N days (0 = all time)")
    ap.add_argument("--json", dest="out_json", help="write the count result to this path")
    a = ap.parse_args()

    if not a.auth and not a.pin and not a.count_keyword:
        sys.exit("!! nothing to do: pass --pin \"text\" or --count-keyword WORD")
    if not a.auth and not a.video:
        sys.exit("!! --video is required")

    from yt_upload import get_creds, token_path
    from googleapiclient.discovery import build
    if a.auth:
        print(f"!! a browser will open — pick the '{a.channel}' channel's Google account. "
              f"Choosing the WRONG account overwrites {token_path(a.channel)} and points "
              f"this key at another channel.")
    creds = get_creds(a.channel, a.auth)
    yt = build("youtube", "v3", credentials=creds)
    me = yt.channels().list(part="snippet", mine=True).execute()["items"][0]
    print(f">> authorized channel: {me['snippet']['title']}  (key: {a.channel})")
    if a.auth:
        print(">> auth OK (force-ssl granted). re-run with --video ... --pin/--count-keyword")
        return

    v = get_video(yt, a.video)
    title = v["snippet"]["title"]
    print(f">> video: {title}  https://youtu.be/{a.video}")

    # --- MFK GUARD (exit 0, not an error) -------------------------------------
    st = v.get("status", {})
    if st.get("madeForKids") or st.get("selfDeclaredMadeForKids"):
        print(">> kids channel — comments unavailable. YouTube disables comments on "
              "Made-for-Kids videos (COPPA), so there is nothing to post or count. "
              "Skipping cleanly.")
        return

    # own-video check: we can only comment-as-channel + read moderation on ours
    if v["snippet"].get("channelId") != me["id"]:
        print(f">> WARNING: {a.video} is not owned by this channel "
              f"({v['snippet'].get('channelTitle')}) — posting would comment as an "
              f"outsider. Refusing.")
        sys.exit(1)

    if a.pin:
        do_pin(yt, a.channel, a.video, a.pin, title)
    if a.count_keyword:
        do_count(yt, a.channel, a.video, a.count_keyword, a.days, a.out_json, title)


if __name__ == "__main__":
    main()
