#!/usr/bin/env python3
"""Aashiqana TEST 1 read — RELATED_VIDEO repeatability check for the 3 armed romantic
long-forms (Tu Meri / Chalo Na / Thehar Ja), against pre-committed GO/KILL thresholds.

GO   = >=1 video has >=50 RELATED_VIDEO views (cumulative) AND still climbing (>5/day recent)
KILL = ALL 3 under 20 RELATED_VIDEO AND subscriber conversion < 1 per 150 test views
Writes docs/stats/TEST1-READ.md (append), fires a macOS notification with the verdict.

Usage: python3 scripts/test1_read.py [--label day-10]
Analytics API lags ~48h; schedule reads a couple days after the milestone.
"""
import os, sys, subprocess, argparse
from datetime import date, timedelta
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts")); os.chdir(REPO)

CID = "UCPqDIZt1YCm7awEBztW6Yzg"
PUB = "2026-08-19"
VIDS = [("VoOHtysP6D8", "Tu Meri Jaan (Golden-Hour)"),
        ("HMRKGT_U6o4", "Chalo Na (Seaside)"),
        ("vsyydnnnYtE", "Thehar Ja (Cafe)")]

def notify(msg):
    print(f"[test1] {msg}")
    if sys.platform == "darwin":
        subprocess.run(["osascript", "-e",
            f'display notification "{msg}" with title "Aashiqana TEST 1 read" sound name "Glass"'])

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--label", default="read"); a = ap.parse_args()
    from yt_upload import get_creds
    from googleapiclient.discovery import build
    creds = get_creds("aashiqana", False)
    yt = build("youtube", "v3", credentials=creds)
    yta = build("youtubeAnalytics", "v2", credentials=creds)
    today = str(date.today()); d3 = str(date.today() - timedelta(days=3))
    subs = int(yt.channels().list(part="statistics", mine=True).execute()["items"][0]["statistics"].get("subscriberCount", 0) or 0)

    def related(vid, start, end):
        try:
            r = yta.reports().query(ids=f"channel=={CID}", startDate=start, endDate=end,
                metrics="views", dimensions="insightTrafficSourceType", filters=f"video=={vid}").execute()
            return {row[0]: int(row[1]) for row in r.get("rows", [])}
        except Exception as e:
            return {"ERR": str(e)[:90]}

    rows = []; go = False; total_views = 0
    for vid, name in VIDS:
        cum = related(vid, PUB, today); rec = related(vid, d3, today)
        rel = cum.get("RELATED_VIDEO", 0); recrel = rec.get("RELATED_VIDEO", 0)
        tot = sum(v for k, v in cum.items() if k != "ERR"); total_views += tot
        climbing = round(recrel / 3.0, 1)
        vgo = rel >= 50 and climbing > 5
        go = go or vgo
        rows.append((name, vid, rel, tot, climbing, vgo, cum))

    had_error = any("ERR" in cum for *_, cum in rows)
    all_under20 = all(r[2] < 20 for r in rows)
    sub_conv_low = subs < total_views / 150.0
    # KILL only on REAL data — never let an API error/no-data window read as a kill
    kill = all_under20 and sub_conv_low and not had_error and total_views > 0
    if had_error or total_views == 0:
        verdict = "DATA ERROR / no data yet — RE-RUN, do not act (analytics query failed or empty)"
    elif go:
        verdict = "CONTINUE — engine reproduces, scale the recipe"
    elif kill:
        verdict = "KILL — the Aaja Ve tail was a fluke, stop investing"
    else:
        verdict = "INCONCLUSIVE — hold and re-read"

    L = [f"### Aashiqana TEST 1 — {a.label} read ({today})", "",
         "Pre-committed: GO = >=1 video >=50 RELATED_VIDEO & still >5/day; "
         "KILL = all <20 RELATED_VIDEO & subs < 1/150 views.", "",
         f"Channel subs: **{subs}** · total test views: **{total_views}**", "",
         "| Video | RELATED_VIDEO (cum) | total views | recent/day | GO? |",
         "|---|---|---|---|---|"]
    for name, vid, rel, tot, climb, vgo, cum in rows:
        L.append(f"| {name} `{vid}` | {rel} | {tot} | {climb} | {'YES' if vgo else '-'} |")
    L += ["", f"**VERDICT: {verdict}**", ""]
    for name, vid, rel, tot, climb, vgo, cum in rows:
        L.append(f"- {name}: {cum}")
    report = "\n".join(L) + "\n\n"
    with open(os.path.join(REPO, "docs", "stats", "TEST1-READ.md"), "a", encoding="utf-8") as f:
        f.write(report)
    print(report)
    best = max(r[2] for r in rows)
    notify(f"{a.label}: {verdict.split(' — ')[0]} (best RELATED_VIDEO={best})")

if __name__ == "__main__":
    main()
