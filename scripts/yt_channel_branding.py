#!/usr/bin/env python3
"""
Set channel branding (banner, description, keywords) and/or a video thumbnail via API.
Uses the same per-channel token as yt_upload.py.

  python3 scripts/yt_channel_branding.py --channel aashiqana \
     --banner channels/aashiqana/brand/banner.jpg \
     --desc-file channels/aashiqana/brand/about.txt \
     --keywords 'hindi romantic songs,love songs,aashiqana,baarish song'
  # later, after phone verification:
  python3 scripts/yt_channel_branding.py --channel aashiqana --thumb-video XmbelUl76V8 \
     --thumb channels/aashiqana/brand/thumb_baarish.jpg
"""
import argparse, os, sys
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]
CLIENT = "secrets/client_secret.json"
def token_path(ch): return "secrets/token.json" if ch in ("lulla","pip") else f"secrets/token_{ch}.json"
def creds(ch):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    c = Credentials.from_authorized_user_file(token_path(ch), SCOPES)
    if not c.valid and c.refresh_token: c.refresh(Request())
    return c
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True)
    ap.add_argument("--banner"); ap.add_argument("--desc-file"); ap.add_argument("--keywords")
    ap.add_argument("--thumb-video"); ap.add_argument("--thumb")
    a = ap.parse_args()
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    yt = build("youtube","v3",credentials=creds(a.channel))
    ch = yt.channels().list(part="snippet,brandingSettings", mine=True).execute()["items"][0]
    cid = ch["id"]; print(f">> channel: {ch['snippet']['title']} ({cid})")
    if a.banner:
        r = yt.channelBanners().insert(media_body=MediaFileUpload(a.banner)).execute()
        url = r["url"]; print(">> banner uploaded")
        bs = ch.get("brandingSettings", {}); bs.setdefault("image", {})["bannerExternalUrl"] = url
        ch["brandingSettings"] = bs
    if a.desc_file or a.keywords:
        bs = ch.get("brandingSettings", {}); bs.setdefault("channel", {})
        if a.desc_file: bs["channel"]["description"] = open(a.desc_file).read().strip()
        if a.keywords:
            kw = " ".join(f'"{k.strip()}"' if " " in k.strip() else k.strip() for k in a.keywords.split(","))
            bs["channel"]["keywords"] = kw
        ch["brandingSettings"] = bs
    if a.banner or a.desc_file or a.keywords:
        yt.channels().update(part="brandingSettings", body={"id":cid,"brandingSettings":ch["brandingSettings"]}).execute()
        print(">> brandingSettings updated (banner/description/keywords)")
    if a.thumb_video and a.thumb:
        yt.thumbnails().set(videoId=a.thumb_video, media_body=MediaFileUpload(a.thumb)).execute()
        print(f">> thumbnail set on https://youtu.be/{a.thumb_video}")
if __name__ == "__main__": main()
