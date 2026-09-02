#!/usr/bin/env python3
"""
yt_scan.py — channel/velocity scanner over the YouTube Data API.

Why not yt-dlp: parallel yt-dlp against YouTube trips "Sign in to confirm you're
not a bot" within a few dozen calls, which silently degrades a research sweep
(2026-09-02: two of three harvest agents blocked mid-run). The Data API is
authenticated, quota'd rather than rate-limited, and returns publishedAt — which
matters because the useful ranking is VELOCITY (views per day since upload), not
lifetime views. A 1-day-old short at 90k is hotter than a 6-month-old at 200k.

    python3 scripts/yt_scan.py UCxxxx "Channel Name" [--n 60] [--days 21] [--json out.json]
    python3 scripts/yt_scan.py --search "claude code mcp" --days 14
"""
import argparse, datetime, json, re, statistics, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yt_upload import get_creds
from googleapiclient.discovery import build

ISO = re.compile(r'P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?')

def secs(d):
    m = ISO.fullmatch(d or "")
    if not m:
        return 0
    dd, h, mi, s = [float(x or 0) for x in m.groups()]
    return int(dd * 86400 + h * 3600 + mi * 60 + s)

def yt():
    return build("youtube", "v3", credentials=get_creds("claude-tricks", False))

def detail(api, ids):
    now = datetime.datetime.now(datetime.timezone.utc)
    out = []
    for k in range(0, len(ids), 50):
        r = api.videos().list(part="snippet,statistics,contentDetails",
                              id=",".join(ids[k:k + 50])).execute()
        for it in r["items"]:
            s, st = it["snippet"], it["statistics"]
            pub = datetime.datetime.fromisoformat(s["publishedAt"].replace("Z", "+00:00"))
            age = max(0.5, (now - pub).total_seconds() / 86400)
            v = int(st.get("viewCount", 0))
            out.append({"id": it["id"], "title": s["title"], "channel": s["channelTitle"],
                        "date": str(pub.date()), "age_days": round(age, 1), "views": v,
                        "likes": int(st.get("likeCount", 0)),
                        "dur": secs(it["contentDetails"]["duration"]),
                        "vel": round(v / age)})
    return out

def channel(api, cid, n):
    c = api.channels().list(part="snippet,statistics,contentDetails", id=cid).execute()["items"][0]
    up = c["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, tok = [], None
    while len(ids) < n:
        p = api.playlistItems().list(part="contentDetails", playlistId=up,
                                     maxResults=50, pageToken=tok).execute()
        ids += [i["contentDetails"]["videoId"] for i in p["items"]]
        tok = p.get("nextPageToken")
        if not tok:
            break
    return c, detail(api, ids[:n])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cid", nargs="?")
    ap.add_argument("name", nargs="?", default="")
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--days", type=int, default=0, help="only keep uploads newer than this")
    ap.add_argument("--maxdur", type=int, default=180, help="shorts filter")
    ap.add_argument("--search", help="ytsearch instead of a channel")
    ap.add_argument("--json", dest="out")
    a = ap.parse_args()
    api = yt()

    if a.search:
        r = api.search().list(part="id", q=a.search, type="video", order="date",
                              maxResults=50, videoDuration="short").execute()
        rows = detail(api, [i["id"]["videoId"] for i in r["items"]])
        head = f"SEARCH {a.search!r}"
        stats = ""
    else:
        c, rows = channel(api, a.cid, a.n)
        s = c["statistics"]
        head = f"{a.name or c['snippet']['title']}  ({a.cid})"
        stats = (f"{int(s['subscriberCount']):,} subs · {s['videoCount']} videos · "
                 f"{int(s['viewCount']):,} views")

    rows = [r for r in rows if 0 < r["dur"] <= a.maxdur]
    if a.days:
        rows = [r for r in rows if r["age_days"] <= a.days]
    rows.sort(key=lambda r: -r["vel"])

    print(f"\n### {head}")
    if stats:
        print(f"    {stats}")
    if rows:
        print(f"    n={len(rows)} · median {statistics.median([r['views'] for r in rows]):,.0f} views "
              f"· median {statistics.median([r['dur'] for r in rows]):.0f}s")
    print(f"{'vel/day':>9} {'views':>10} {'age':>5} {'dur':>5}  date        title")
    for r in rows[:25]:
        print(f"{r['vel']:>9,} {r['views']:>10,} {r['age_days']:>4.0f}d {r['dur']:>4}s  {r['date']}  {r['title'][:66]}")
    if a.out:
        json.dump(rows, open(a.out, "w"), indent=1)
        print(f">> {len(rows)} rows -> {a.out}")

if __name__ == "__main__":
    main()
