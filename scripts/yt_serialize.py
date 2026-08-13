#!/usr/bin/env python3
"""
One-shot serialization ops for a couple-story channel (Unki Kahani — see
channels/aashiqana/SERIALIZATION-PROPOSAL.md). Two verbs, both idempotent:

    python3 scripts/yt_serialize.py --channel aashiqana --init-playlist
        Create the story playlist named in channel.json serial.story (skipped if
        serial.playlist_id is already set) and write the new id back into
        channel.json. The playlist is the "The Story So Far" binge surface.

    python3 scripts/yt_serialize.py --channel aashiqana --retrofit <VIDEO_ID> <N>
        Retro-label an already-published Short as Chapter N: append the
        ' | <story> Ch.N' title chip (100-char guard), prepend the chapter block
        to the description, and add it to the story playlist. The whole snippet
        is fetched and echoed back — videos.update REPLACES the part, so a
        partial body would silently wipe tags/categoryId (same doctrine as
        STATUS_ROUNDTRIP in verify_uploads.py, but for snippet).

Safety: this script never touches status (privacy/schedule/MFK/disclosure),
never deletes, and refuses a retrofit whose video already carries the story
name in its title. Add --dry to print planned writes without executing.

Worktree note: tokens live only in the MAIN checkout's secrets/. When run from
a git worktree the script chdirs to the main checkout for auth (secrets/* are
cwd-relative in yt_upload.py); channel.json config writes stay at this script's
own repo root so they ride the branch under review.
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)


def auth_root(channel):
    """Directory whose secrets/ holds this channel's token: REPO, else the main
    checkout this worktree belongs to."""
    from yt_upload import token_path
    if os.path.exists(os.path.join(REPO, token_path(channel))):
        return REPO
    r = subprocess.run(["git", "-C", REPO, "rev-parse", "--path-format=absolute",
                        "--git-common-dir"], capture_output=True, text=True)
    main_root = os.path.dirname(r.stdout.strip()) if r.returncode == 0 else ""
    if main_root and os.path.exists(os.path.join(main_root, token_path(channel))):
        return main_root
    sys.exit(f"!! no token for {channel!r} under {REPO}/secrets or the main checkout — "
             f"authorize once with: python3 scripts/yt_upload.py --channel {channel} --auth")


def get_youtube(channel):
    from yt_upload import get_creds
    from googleapiclient.discovery import build
    os.chdir(auth_root(channel))  # yt_upload resolves secrets/* from cwd
    return build("youtube", "v3", credentials=get_creds(channel, False))


def config_path(channel):
    return os.path.join(REPO, "channels", channel, "channel.json")


def load_serial(channel):
    cfg = json.load(open(config_path(channel)))
    ser = cfg.get("serial")
    if not ser:
        sys.exit(f"!! channels/{channel}/channel.json has no 'serial' block — nothing to serialize")
    return cfg, ser


def init_playlist(yt, channel, dry):
    cfg, ser = load_serial(channel)
    if ser.get("playlist_id"):
        print(f">> playlist already set: {ser['playlist_id']} — nothing to do")
        return ser["playlist_id"]
    title = f"{ser['story']} — The Story So Far"
    desc = (f"{ser['couple']}'s love story, one song at a time. Start at Chapter 1. "
            f"New chapter every {ser.get('chapter_day', 'Friday')}. @aashiqana.diaries")
    if dry:
        print(f">> DRY: would create public playlist {title!r} and store its id in channel.json")
        return None
    pl = yt.playlists().insert(part="snippet,status", body={
        "snippet": {"title": title, "description": desc},
        "status": {"privacyStatus": "public"}}).execute()
    ser["playlist_id"] = pl["id"]
    with open(config_path(channel), "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f">> playlist created: {pl['id']}  ({title})")
    print(f">> channel.json serial.playlist_id updated")
    return pl["id"]


# every snippet field videos.update must echo back or lose
SNIPPET_ROUNDTRIP = ("title", "description", "tags", "categoryId",
                     "defaultLanguage", "defaultAudioLanguage")


def retrofit(yt, channel, video_id, chapter, dry):
    from finalize_aashiqana import chapter_title  # single source for the chip rule
    _, ser = load_serial(channel)
    story, day = ser["story"], ser.get("chapter_day", "Friday")
    items = yt.videos().list(part="snippet", id=video_id).execute().get("items", [])
    if not items:
        sys.exit(f"!! video {video_id} not found on this channel")
    sn = items[0]["snippet"]
    if story.lower() in sn["title"].lower():
        sys.exit(f"!! {video_id} already carries {story!r} in its title — refusing a double retrofit")
    new_title = chapter_title(sn["title"], chapter, story)
    head = [f"Chapter {chapter} of {story} — {ser['couple']}'s story."]
    if int(chapter) > 1:
        head.append(f"(Chapter {int(chapter) - 1} is in the {story} playlist.)")
    head.append(f"Next chapter {day}. Follow @aashiqana.diaries")
    body = {k: sn[k] for k in SNIPPET_ROUNDTRIP if k in sn}
    body["title"] = new_title
    body["description"] = "\n".join(head) + "\n\n" + sn.get("description", "")
    print(f">> title: {sn['title']!r}\n>>     -> {new_title!r}")
    print(f">> description: prepending {len(head)}-line chapter block "
          f"(tags echoed: {len(sn.get('tags', []))})")
    if dry:
        print(">> DRY: no writes")
        return
    resp = yt.videos().update(part="snippet", body={"id": video_id, "snippet": body}).execute()
    print(f">> snippet updated (acked title: {resp['snippet']['title']!r})")
    plid = ser.get("playlist_id")
    if plid:
        yt.playlistItems().insert(part="snippet", body={"snippet": {
            "playlistId": plid,
            "resourceId": {"kind": "youtube#video", "videoId": video_id}}}).execute()
        print(f">> added to playlist {plid}")
    else:
        print(">> WARNING: no serial.playlist_id — run --init-playlist first, then re-run "
              ">> --retrofit (the title/description writes above already landed)")


def main():
    ap = argparse.ArgumentParser(description="Story-serialization ops (playlist + retro-label chapters)")
    ap.add_argument("--channel", default="aashiqana")
    ap.add_argument("--init-playlist", action="store_true")
    ap.add_argument("--retrofit", nargs=2, metavar=("VIDEO_ID", "CHAPTER"))
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    if not a.init_playlist and not a.retrofit:
        ap.error("nothing to do: pass --init-playlist and/or --retrofit VIDEO_ID N")
    yt = get_youtube(a.channel)
    if a.init_playlist:
        init_playlist(yt, a.channel, a.dry)
    if a.retrofit:
        retrofit(yt, a.channel, a.retrofit[0], int(a.retrofit[1]), a.dry)


if __name__ == "__main__":
    main()
