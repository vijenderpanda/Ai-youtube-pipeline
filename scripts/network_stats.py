#!/usr/bin/env python3
"""
Daily network stats check (runs 07:00 IST via launchd on the Mac).

Pulls live stats for every channel in the network (Data API) + traffic-source
breakdown (Analytics API), appends a per-video snapshot to docs/stats/history.csv,
and rewrites docs/stats/DAILY-STATS.md with day-over-day deltas. Headline movers
go to a macOS notification on the Mac, stdout everywhere else.

Run manually any time:  python3 scripts/network_stats.py

Runs on the Windows worker too (analytics_sync shells it out). Requires
secrets/token_<key>.json for each channel — with no token file, get_creds()
falls through to an interactive browser consent that will HANG a headless job,
so auth each channel once on the box before scheduling a sync there.
"""
import csv, os, subprocess, sys
from datetime import datetime, timedelta, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
os.chdir(REPO)

CHANNELS = [
    ("lulla", "Lulla's Moonlit Garden", "UCKBJGCpvHAYbtUTBWOcmpLQ"),
    ("poly", "Learn with Poly", "UCNUgG5rRDQ42QFcNLjZQJnQ"),
    ("vehicles", "Rumble Trucks", "UCy8VHZoeP07NokvLJxXKoCQ"),
    ("claude-tricks", "AI Unpacked", "UCn0Mta19_rTBtdyHoggM7HA"),
    ("aashiqana", "Aashiqana", "UCPqDIZt1YCm7awEBztW6Yzg"),
]
STATS_DIR = os.path.join(REPO, "docs", "stats")
HISTORY = os.path.join(STATS_DIR, "history.csv")
REPORT = os.path.join(STATS_DIR, "DAILY-STATS.md")
FIELDS = ["date", "channel", "video_id", "title", "privacy", "publish_at",
          "views", "likes", "comments", "subs", "channel_views"]


def notify(msg):
    """Headline line for the human. macOS gets a real notification; every other
    host just prints it.

    🔴 osascript is macOS-only. Calling it unguarded raises FileNotFoundError on
    the Windows worker — and notify() is the LAST thing main() does, so the
    traceback lands AFTER history.csv + DAILY-STATS.md are already written: the
    data is fine, but the process exits non-zero and analytics_sync logs
    "WARNING: network_stats.py exited 1" on every single Windows run, which
    masks the real fetch errors this warning exists to surface."""
    print(f"[stats] {msg}")
    if sys.platform == "darwin":
        subprocess.run(["osascript", "-e",
                        f'display notification "{msg}" with title "YT Network — Daily Stats" sound name "Glass"'])


def fetch_channel(key, cid):
    from yt_upload import get_creds
    from googleapiclient.discovery import build
    creds = get_creds(key, False)
    yt = build("youtube", "v3", credentials=creds)
    ch = yt.channels().list(part="snippet,statistics,contentDetails", mine=True).execute()["items"][0]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids = []
    try:
        pl = yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50).execute()
        ids = [i["contentDetails"]["videoId"] for i in pl.get("items", [])]
    except Exception:
        pass
    try:
        sr = yt.search().list(part="id", forMine=True, type="video", maxResults=50, order="date").execute()
        for i in sr.get("items", []):
            v = i["id"]["videoId"]
            if v not in ids:
                ids.append(v)
    except Exception:
        pass
    videos = []
    for chunk in (ids[i:i + 50] for i in range(0, len(ids), 50)):
        vr = yt.videos().list(part="snippet,statistics,status", id=",".join(chunk)).execute()
        for v in vr.get("items", []):
            st = v.get("statistics", {})
            videos.append({
                "id": v["id"],
                "title": v["snippet"]["title"],
                "published": v["snippet"].get("publishedAt", ""),
                "publish_at": v["status"].get("publishAt", "") or "",
                "privacy": v["status"].get("privacyStatus", ""),
                "views": int(st.get("viewCount", 0) or 0),
                "likes": int(st.get("likeCount", 0) or 0),
                "comments": int(st.get("commentCount", 0) or 0),
            })
    videos.sort(key=lambda x: x["published"], reverse=True)
    # traffic sources, finalized data lags ~48h so use a 7-day window
    traffic = []
    try:
        yta = build("youtubeAnalytics", "v2", credentials=creds)
        end = datetime.now(timezone.utc).date()
        r = yta.reports().query(
            ids=f"channel=={cid}",
            startDate=str(end - timedelta(days=7)), endDate=str(end),
            metrics="views", dimensions="insightTrafficSourceType", sort="-views").execute()
        traffic = [(row[0], int(row[1])) for row in r.get("rows", [])]
    except Exception:
        pass
    return {
        "subs": int(ch["statistics"].get("subscriberCount", 0) or 0),
        "channel_views": int(ch["statistics"].get("viewCount", 0) or 0),
        "videos": videos,
        "traffic": traffic,
    }


def load_previous():
    """Latest historical snapshot per video (from before today)."""
    prev = {}
    if not os.path.exists(HISTORY):
        return prev
    today = datetime.now().strftime("%Y-%m-%d")
    with open(HISTORY) as f:
        for row in csv.DictReader(f):
            if row["date"] >= today:
                continue
            k = row["video_id"]
            if k not in prev or row["date"] > prev[k]["date"]:
                prev[k] = row
    return prev


def main():
    os.makedirs(STATS_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    prev = load_previous()
    data, errors = {}, []
    for key, label, cid in CHANNELS:
        try:
            data[key] = fetch_channel(key, cid)
        except Exception as e:
            errors.append(f"{label}: {e}")

    # append today's snapshot (drop any earlier rows from today so reruns don't duplicate)
    rows = []
    if os.path.exists(HISTORY):
        with open(HISTORY) as f:
            rows = [r for r in csv.DictReader(f) if r["date"] != today]
    for key, label, cid in CHANNELS:
        d = data.get(key)
        if not d:
            continue
        for v in d["videos"]:
            rows.append({"date": today, "channel": label, "video_id": v["id"],
                         "title": v["title"], "privacy": v["privacy"],
                         "publish_at": v["publish_at"], "views": v["views"],
                         "likes": v["likes"], "comments": v["comments"],
                         "subs": d["subs"], "channel_views": d["channel_views"]})
    with open(HISTORY, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    # build the report
    lines = [f"# Network Daily Stats — {datetime.now():%Y-%m-%d %H:%M} IST",
             "", "Auto-generated by `scripts/network_stats.py`. History: `docs/stats/history.csv`.",
             "Traffic sources = last 7 days (Analytics finalizes with ~48h lag).", ""]
    movers = []
    for key, label, cid in CHANNELS:
        d = data.get(key)
        if not d:
            lines.append(f"## {label} — ⚠️ FETCH FAILED\n")
            continue
        ch_delta = 0
        lines.append(f"## {label}")
        lines.append(f"Subs: **{d['subs']}** · Channel views: **{d['channel_views']}**")
        lines.append("")
        lines.append("| Video | State | Views | Δ day | Likes | Comments |")
        lines.append("|---|---|---|---|---|---|")
        for v in d["videos"]:
            p = prev.get(v["id"])
            delta = v["views"] - int(p["views"]) if p else v["views"]
            ch_delta += max(delta, 0)
            state = v["privacy"]
            if v["publish_at"] and v["privacy"] == "private":
                state = f"scheduled {v['publish_at'][:10]}"
            d_str = f"+{delta}" if delta > 0 else str(delta)
            lines.append(f"| {v['title'][:60]} | {state} | {v['views']} | {d_str} | {v['likes']} | {v['comments']} |")
        if d["traffic"]:
            src = " · ".join(f"{name} {n}" for name, n in d["traffic"][:4])
            lines.append(f"\nTraffic (7d): {src}")
        lines.append("")
        if ch_delta > 0:
            movers.append((ch_delta, label))
    if errors:
        lines.append("## Errors\n" + "\n".join(f"- {e}" for e in errors))
    with open(REPORT, "w") as f:
        f.write("\n".join(lines) + "\n")

    movers.sort(reverse=True)
    if movers:
        head = ", ".join(f"{l} +{n}" for n, l in movers[:3])
        notify(f"{head} views today — DAILY-STATS.md updated")
    elif errors:
        notify(f"⚠️ stats check hit {len(errors)} error(s) — see DAILY-STATS.md")
    else:
        notify("No new views since yesterday — DAILY-STATS.md updated")
    print(f"wrote {REPORT} + history ({len(rows)} rows)")


if __name__ == "__main__":
    main()
