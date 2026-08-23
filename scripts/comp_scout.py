#!/usr/bin/env python3
"""comp_scout — rank recent Shorts across candidate channels by what the feed rewarded.

    python scripts/comp_scout.py [--channels @a,@b] [--per-channel 20] [--days 90] [--top 12]
                                 [--out research/comp-dna/scout]

Public data only: views, likes, comments, duration, upload date. Retention is NOT public;
the proxies are views/day (feed selection), like-rate, comment-rate. Writes:
  <out>/SCOUT.csv   every short scanned
  <out>/SCOUT.md    ranked table + per-channel medians + what-works notes
  <out>/top.txt     top-N URLs (feed into swipe_capture / the comp-dna pipeline)
"""
import argparse, csv, json, shutil, subprocess, sys, datetime as dt, statistics as st
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

REPO = Path(__file__).resolve().parent.parent
YTDLP = shutil.which("yt-dlp") or str(Path.home() / "miniconda3/bin/yt-dlp")
SEEDS = ["@GregIsenberg", "@anthropic-ai", "@rileybrownai", "@RubenHassid", "@rowancheung",
         "@alliekmiller", "@VarunMayya", "@IshanSharma7390", "@aakashgupta", "@mattwolfe",
         "@AIJasonZ", "@ColeMedin", "@NateBJones", "@theAIGRID", "@DavidOndrej",
         "@Skill_Leap_AI", "@Tanmay_Bhat_AI", "@RajShamani", "@WesRoth", "@AdrianTwarog"]

def run(args, timeout=120):
    try:
        return subprocess.run([YTDLP, *args], capture_output=True, text=True, timeout=timeout).stdout
    except subprocess.TimeoutExpired:
        return ""

def list_shorts(ch, n):
    out = run(["--flat-playlist", "--playlist-end", str(n), "--print", "%(id)s", f"https://www.youtube.com/{ch}/shorts"])
    return [l.strip() for l in out.splitlines() if l.strip()]

def meta(vid):
    out = run(["-j", "--no-download", f"https://www.youtube.com/shorts/{vid}"], 60)
    try:
        d = json.loads(out)
    except Exception:
        return None
    return {"id": vid, "title": d.get("title"), "channel": d.get("uploader"), "handle": d.get("uploader_id"),
            "views": d.get("view_count") or 0, "likes": d.get("like_count") or 0, "comments": d.get("comment_count") or 0,
            "duration": d.get("duration") or 0, "date": d.get("upload_date"), "lang": d.get("language")}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--channels"); ap.add_argument("--per-channel", type=int, default=20)
    ap.add_argument("--days", type=int, default=90); ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--out", default=str(REPO / "research/comp-dna/scout")); a = ap.parse_args()
    chans = a.channels.split(",") if a.channels else SEEDS
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    today = dt.date.today()
    ids = []
    with ThreadPoolExecutor(6) as ex:
        for ch, lst in zip(chans, ex.map(lambda c: list_shorts(c, a.per_channel), chans)):
            print(f"{ch}: {len(lst)} shorts", file=sys.stderr); ids += lst
    ids = list(dict.fromkeys(ids))
    with ThreadPoolExecutor(8) as ex:
        rows = [m for m in ex.map(meta, ids) if m and m["date"]]
    for r in rows:
        d = dt.date(int(r["date"][:4]), int(r["date"][4:6]), int(r["date"][6:8]))
        r["age_d"] = max(1, (today - d).days)
        r["views_per_day"] = round(r["views"] / r["age_d"])
        r["like_rate"] = round(r["likes"] / r["views"], 4) if r["views"] else 0
        r["comment_rate"] = round(r["comments"] / r["views"], 5) if r["views"] else 0
    recent = [r for r in rows if r["age_d"] <= a.days]
    recent.sort(key=lambda r: -r["views_per_day"])
    keys = ["id","channel","handle","title","views","views_per_day","like_rate","comment_rate","duration","date","age_d","lang"]
    with open(out / "SCOUT.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore"); w.writeheader(); w.writerows(recent)
    # per-channel medians
    bych = {}
    for r in recent: bych.setdefault(r["channel"], []).append(r)
    chrows = sorted(((c, len(v), st.median([x["views_per_day"] for x in v]), st.median([x["duration"] for x in v]),
                      st.median([x["like_rate"] for x in v])) for c, v in bych.items()), key=lambda t: -t[2])
    top = recent[: a.top]
    md = [f"# Comp scout — last {a.days}d · {len(recent)} shorts · {len(bych)} channels · {today}", "",
          "Public proxies only (retention not public): **views/day** = feed selection, like-rate, comment-rate.", "",
          "## Channels (median views/day)", "| channel | n | med views/day | med dur | med like-rate |", "|---|---|---|---|---|"]
    md += [f"| {c} | {n} | {vpd:,.0f} | {du:.0f}s | {lr:.3%} |" for c, n, vpd, du, lr in chrows]
    md += ["", f"## Top {a.top} shorts (views/day)", "| # | id | channel | title | views | v/day | dur | age | like |", "|---|---|---|---|---|---|---|---|---|"]
    md += [f"| {i+1} | [{r['id']}](https://youtube.com/shorts/{r['id']}) | {r['channel']} | {str(r['title'])[:55]} | {r['views']:,} | {r['views_per_day']:,} | {r['duration']}s | {r['age_d']}d | {r['like_rate']:.2%} |" for i, r in enumerate(top)]
    # what works: duration buckets + title patterns
    def bucket(d): return "<30s" if d < 30 else "30-45s" if d < 45 else "45-60s" if d < 60 else "60s+"
    bk = {}
    for r in recent: bk.setdefault(bucket(r["duration"]), []).append(r["views_per_day"])
    md += ["", "## Duration vs views/day (median)", "| bucket | n | med v/day |", "|---|---|---|"]
    md += [f"| {b} | {len(v)} | {st.median(v):,.0f} |" for b, v in sorted(bk.items())]
    bottom = recent[-a.top:] if len(recent) > a.top else []
    md += ["", "## Bottom (same window) — what the feed ignored", "| id | channel | title | v/day | dur |", "|---|---|---|---|---|"]
    md += [f"| {r['id']} | {r['channel']} | {str(r['title'])[:55]} | {r['views_per_day']:,} | {r['duration']}s |" for r in bottom]
    (out / "SCOUT.md").write_text("\n".join(md) + "\n")
    (out / "top.txt").write_text("\n".join(f"https://www.youtube.com/shorts/{r['id']}" for r in top) + "\n")
    print("\n".join(md[:8 + len(chrows) + 3 + a.top]))

if __name__ == "__main__":
    main()
