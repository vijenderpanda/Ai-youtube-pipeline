#!/usr/bin/env python3
"""Set a channel banner via the YouTube Data API (no phone verification needed).
Usage: python3 scripts/set_banner.py <channel> <banner.jpg>
Example: python3 scripts/set_banner.py vehicles channels/vehicles/assets/channel/banner_final.jpg
"""
import sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ch, banner = sys.argv[1], sys.argv[2]
tp = "secrets/token.json" if ch in ("lulla", "pip") else f"secrets/token_{ch}.json"
yt = build("youtube", "v3", credentials=Credentials.from_authorized_user_file(tp))

me = yt.channels().list(part="id,brandingSettings", mine=True).execute()["items"][0]
cid, bs = me["id"], me.get("brandingSettings", {})
up = yt.channelBanners().insert(media_body=MediaFileUpload(banner)).execute()
bs.setdefault("image", {})["bannerExternalUrl"] = up["url"]
yt.channels().update(part="brandingSettings", body={"id": cid, "brandingSettings": bs}).execute()
print(f">> banner set on channel {cid}\n   bannerExternalUrl: {up['url']}")
