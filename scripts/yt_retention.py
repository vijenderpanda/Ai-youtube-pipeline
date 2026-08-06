#!/usr/bin/env python3
"""
yt_retention.py — per-video AUDIENCE RETENTION CURVES from the YouTube Analytics API.

Why this exists: hook and format decisions were resting on a single avg_view_pct number.
This pulls the actual watch curve (dimension=elapsedVideoTimeRatio) so we can SEE where a
video bleeds viewers — the ~3s hook gate and the ~15s sustained-distribution gate that the
2026 Shorts research treats as the two distribution levers, plus the steepest mid-video
drop points. One avg % hides all of that; the curve is the diagnosis.

Usage:
    python scripts/yt_retention.py --channel claude-tricks [--video ID ...] [--days 30]
                                   [--out retention.json] [--summary] [--md docs/stats/RETENTION.md]

Auth: reuses scripts/yt_upload.get_creds (secrets/token_<key>.json) — the SAME OAuth grant
network_stats.py already uses for the Analytics API. 🔴 We only READ. Never pass the module
SCOPES and never write the token back here: get_creds already loads each token with its own
granted scopes, and a write-back that stamps the aspirational scope list bricks every channel
(see the get_creds docstring — measured 6 Aug 2026).

Data notes:
  - YouTube Analytics finalizes with a ~48h lag; today's / yesterday's numbers are provisional.
  - Small channels: YouTube WITHHOLDS retention below a privacy sample threshold. Those videos
    are marked status="insufficient_data" — never fabricated as zeros.
  - audienceWatchRatio is ~1.0 at the start and decays; relativeRetentionPerformance compares to
    similar YouTube videos (0.5 = median) and can be unavailable per-video → we degrade to the
    watch ratio alone rather than failing the whole video.

Consumers (keep these in sync when the output shape changes):
  - Aashiqana hook-bar A/B loop (which bar of song #01's Short retains → seeds song #03's hook)
  - AI Unpacked secondary-hook-at-15s placement checks + the QUALITY-LEDGER retention axis
  - Lulla compilation experiment (does a 30-min binder hold watch time vs 3-min singles — the
    go / no-go for a 60-90-min v2)
"""
import argparse, json, os, re, sys
from datetime import datetime, timedelta, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
os.chdir(REPO)  # token paths in yt_upload are relative to the repo root

ANALYTICS_LAG_H = 48


def iso_dur_to_s(iso):
    """ISO-8601 PT#H#M#S (YouTube contentDetails.duration) -> seconds, or None."""
    if not iso:
        return None
    m = re.match(r"P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?$", iso)
    if not m:
        return None
    d, h, mi, s = (float(x) if x else 0.0 for x in m.groups())
    return int(d * 86400 + h * 3600 + mi * 60 + s)


def yt_services(key):
    from yt_upload import get_creds
    from googleapiclient.discovery import build
    creds = get_creds(key, False)  # do_auth=False: load existing token, refresh if stale
    return (build("youtube", "v3", credentials=creds),
            build("youtubeAnalytics", "v2", credentials=creds))


def list_videos(yt, days):
    """Recent uploads (uploads playlist + forMine search, deduped) published within `days`."""
    ch = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids = []
    try:
        pl = yt.playlistItems().list(part="contentDetails", playlistId=uploads,
                                     maxResults=50).execute()
        ids = [i["contentDetails"]["videoId"] for i in pl.get("items", [])]
    except Exception:
        pass
    try:
        sr = yt.search().list(part="id", forMine=True, type="video",
                              maxResults=50, order="date").execute()
        for i in sr.get("items", []):
            v = i["id"]["videoId"]
            if v not in ids:
                ids.append(v)
    except Exception:
        pass
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    keep = []
    for m in fetch_meta(yt, ids).values():
        pub = m["snippet"].get("publishedAt", "")
        try:
            pubdt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
        except Exception:
            pubdt = None
        if pubdt and pubdt < cutoff:
            continue
        keep.append(m)
    keep.sort(key=lambda v: v["snippet"].get("publishedAt", ""), reverse=True)
    return keep


def fetch_meta(yt, video_ids):
    """id -> full videos().list item (snippet+contentDetails+statistics)."""
    out = {}
    for chunk in (video_ids[i:i + 50] for i in range(0, len(video_ids), 50)):
        if not chunk:
            continue
        vr = yt.videos().list(part="snippet,contentDetails,statistics",
                              id=",".join(chunk)).execute()
        for v in vr.get("items", []):
            out[v["id"]] = v
    return out


def retention_curve(yta, video_id, start_date, end_date):
    """(rows, relative_ok) where rows = [[ratio, watch_ratio, relative_or_None], ...].

    relativeRetentionPerformance can 400 on individual videos → fall back to the watch
    ratio alone so one unavailable metric never blanks the whole curve.
    """
    base = dict(ids="channel==MINE", startDate=start_date, endDate=end_date,
                dimensions="elapsedVideoTimeRatio", filters=f"video=={video_id}",
                sort="elapsedVideoTimeRatio")
    last = None
    for metrics in ("audienceWatchRatio,relativeRetentionPerformance", "audienceWatchRatio"):
        try:
            r = yta.reports().query(metrics=metrics, **base).execute()
            rows = r.get("rows", [])
            rel_ok = "relativeRetentionPerformance" in metrics
            norm = [[float(x[0]), float(x[1]),
                     (float(x[2]) if rel_ok and len(x) > 2 else None)] for x in rows]
            return norm, rel_ok
        except Exception as e:
            last = e
    raise last


def _nearest(rows, target_ratio):
    return min(rows, key=lambda p: abs(p[0] - target_ratio)) if rows else None


def analyze_video(yta, meta, days):
    vid = meta["id"]
    title = meta["snippet"]["title"]
    dur = iso_dur_to_s(meta.get("contentDetails", {}).get("duration", ""))
    pub = meta["snippet"].get("publishedAt", "")[:10]
    end = datetime.now(timezone.utc).date()
    start = pub or str(end - timedelta(days=days))
    rec = {"video_id": vid, "title": title, "duration_s": dur, "published": pub}
    try:
        rows, rel_ok = retention_curve(yta, vid, start, str(end))
    except Exception as e:
        rec["status"] = "error"
        rec["error"] = str(e)[:220]
        return rec
    if not rows:
        rec["status"] = "insufficient_data"
        rec["note"] = ("YouTube withheld retention (sample below privacy threshold) or "
                       f"data not finalized yet (~{ANALYTICS_LAG_H}h lag).")
        return rec
    rows.sort(key=lambda p: p[0])
    curve = [{"pct_elapsed": round(p[0], 4),
              "sec": round(p[0] * dur, 1) if dur else None,
              "watch_ratio": round(p[1], 4),
              "relative": (round(p[2], 4) if p[2] is not None else None)} for p in rows]
    # steepest drops = most negative consecutive delta in watch_ratio
    deltas = [(b[1] - a[1], a[0], b[0]) for a, b in zip(rows, rows[1:])]
    deltas.sort(key=lambda d: d[0])
    drop_points = [{"from_pct": round(f, 4), "to_pct": round(t, 4),
                    "at_sec": round(t * dur, 1) if dur else None,
                    "watch_ratio_drop": round(-dv, 4)} for dv, f, t in deltas[:3] if dv < 0]

    def hold_at(sec):
        if not dur:
            return None
        p = _nearest(rows, sec / dur)
        return round(p[1], 4) if p else None

    rec.update({
        "status": "ok",
        "relative_available": rel_ok,
        "start_watch_ratio": round(rows[0][1], 4),
        "end_watch_ratio": round(rows[-1][1], 4),
        "hook_hold": {"at_3s": hold_at(3), "at_15s": hold_at(15)},
        "drop_points": drop_points,
        "curve": curve,
    })
    return rec


def _pct(x):
    return f"{x * 100:.0f}%" if isinstance(x, (int, float)) else "n/a"


def summarize(channel, results):
    lines = [f"### Retention — {channel} ({datetime.now():%Y-%m-%d %H:%M} IST)",
             f"_Analytics lag ~{ANALYTICS_LAG_H}h; low-sample videos are withheld by YouTube._", ""]
    for r in results:
        if r.get("status") != "ok":
            lines.append(f"- **{r['title'][:60]}** — _{r.get('status', '?')}_")
            continue
        h = r["hook_hold"]
        dp = ", ".join(f"{x['at_sec']}s (−{int(round(x['watch_ratio_drop'] * 100))}pp)"
                       for x in r["drop_points"]) or "—"
        lines.append(
            f"- **{r['title'][:60]}** ({r['duration_s']}s) — "
            f"3s hold {_pct(h['at_3s'])}, 15s hold {_pct(h['at_15s'])}, ends {_pct(r['end_watch_ratio'])}. "
            f"steepest drops: {dp}")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Per-video YouTube audience-retention curves.")
    ap.add_argument("--channel", required=True, help="channel key -> secrets/token_<key>.json")
    ap.add_argument("--video", action="append", default=[],
                    help="video id (repeatable); default = recent uploads in the window")
    ap.add_argument("--days", type=int, default=30,
                    help="lookback window for auto-listing videos + analytics start (default 30)")
    ap.add_argument("--out", default="retention.json", help="output JSON path")
    ap.add_argument("--summary", action="store_true", help="also print a human-readable block")
    ap.add_argument("--md", default=None,
                    help="append the human-readable summary block to this markdown file "
                         "(so the daily launchd flow can adopt it later)")
    a = ap.parse_args()

    yt, yta = yt_services(a.channel)
    if a.video:
        meta = fetch_meta(yt, a.video)
        metas = [meta[v] for v in a.video if v in meta]
        for v in [v for v in a.video if v not in meta]:
            print(f"  ! {v}: not found / not on this channel", file=sys.stderr)
    else:
        metas = list_videos(yt, a.days)

    print(f"analyzing {len(metas)} video(s) on {a.channel} …", file=sys.stderr)
    results = []
    for m in metas:
        r = analyze_video(yta, m, a.days)
        results.append(r)
        print(f"  {r.get('status', '?'):>17}  {r['title'][:55]}", file=sys.stderr)

    payload = {"channel": a.channel,
               "generated_at": datetime.now(timezone.utc).isoformat(),
               "analytics_lag_hours": ANALYTICS_LAG_H,
               "window_days": a.days,
               "videos": results}
    with open(a.out, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"wrote {a.out} ({len(results)} videos)", file=sys.stderr)

    block = summarize(a.channel, results)
    if a.summary:
        print("\n" + block)
    if a.md:
        os.makedirs(os.path.dirname(a.md) or ".", exist_ok=True)
        with open(a.md, "a") as f:
            f.write("\n" + block)
        print(f"appended summary to {a.md}", file=sys.stderr)


if __name__ == "__main__":
    main()
