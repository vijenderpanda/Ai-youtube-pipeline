#!/usr/bin/env python3
"""Set a custom thumbnail on an existing video (retry once the channel's custom-thumbnail feature is enabled).
Usage: python3 scripts/set_thumbnail.py <channel> <videoId> <thumbnail.jpg>
Example: python3 scripts/set_thumbnail.py poly 6tqf75hpXJg channels/language-abc/assets/thumbnail/thumb_A.jpg
"""
import sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ch, vid, thumb = sys.argv[1], sys.argv[2], sys.argv[3]
tp = "secrets/token.json" if ch in ("lulla", "pip") else f"secrets/token_{ch}.json"
yt = build("youtube", "v3", credentials=Credentials.from_authorized_user_file(tp))
yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(thumb)).execute()
print(f">> thumbnail set on https://youtu.be/{vid}")
