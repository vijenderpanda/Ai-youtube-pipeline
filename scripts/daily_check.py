#!/usr/bin/env python3
"""
Network-wide daily publish-slot guard (06:37 IST via launchd, com.aiunpacked.dailycheck).

Was single-channel (claude-tricks only). Now walks every `channels/*/channel.json`
so no channel's hard date goes unwatched: for each channel it

  1. reads the next N days of CONTENT-CALENDAR.csv slots (N = guard_days),
  2. runs `scripts/verify_uploads.py --channel <key> --expected <slots> --json`,
     which pulls the live public+scheduled list and matches slots on
     `publishAt or publishedAt` (playbook §9: a PUBLIC video has no
     status.publishAt, so matching on publishAt alone reads every shipped slot
     as EMPTY),
  3. writes channels/<dir>/NEEDS-ATTENTION.md for any empty guarded slot, and
  4. surfaces verify_uploads' own findings — duplicate titles, stale
     '🗑️ DELETE —' videos still public, double-booked days, compliance — in the
     same morning report.

Channel differences come from the config, never from assumption:
  - `made_for_kids: true`  -> comment check skipped entirely (YouTube disables
    comments on MFK videos; playbook §9b — the guard holds by construction).
  - `cadence_days`         -> how many slots the window SHOULD hold; a thinner
    calendar is an advisory, not a failure. Lulla is every-3-days, not daily.

🔴 READ-AND-REPORT ONLY. This script performs no writes against YouTube — no
upload, retitle, retire, reschedule or unschedule, ever (playbook §9). The only
files it touches are its own reports. verify_uploads.py is invoked in its
default read-only mode (no --fix-titles / --assert-disclosure / --yes).

Usage:
    python3 scripts/daily_check.py                      # the launchd run
    python3 scripts/daily_check.py --days 11 --no-notify   # dry run, wider window
    python3 scripts/daily_check.py --channel aashiqana
    python3 scripts/daily_check.py --channels-root /tmp/testchannels   # test slots
"""
import argparse, csv, glob, json, os, re, subprocess, sys, tempfile, time
from datetime import datetime, timedelta, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
os.chdir(REPO)

REPORT = os.path.join(REPO, "docs", "NETWORK-ATTENTION.md")
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
# A calendar row is CLOSED once it carries a real video: claude-tricks records
# the outcome in planned_date itself ("SHIPPED 2026-08-05 · youtu.be/BpDhMfhfOoI"),
# so the bare date is the only thing still asking to be produced. A bare
# "SCHEDULED <date>" with no link is deliberately NOT closed — the whole point of
# the guard is that the API, not the spreadsheet, confirms a slot is armed.
# RETIRED/CANCELLED rows keep their old date for history ("RETIRED (was
# 2026-08-19)") — without them here, DATE_RE below still reads that date and
# the checker keeps guarding a slot the decision already freed (the 2026-08-18
# Build Club pivot: bc06/bcs1f).
CLOSED_RE = re.compile(r"youtu\.be/|^\s*(SHIPPED|RETIRED|CANCELLED|KILLED)\b", re.I)


def notify(msg):
    # osascript chokes on embedded double quotes in the literal.
    subprocess.run(["osascript", "-e",
                    'display notification "%s" with title "YT Network — Production" '
                    'sound name "Glass"' % msg.replace('"', "'")])


# ------------------------------------------------------------------ config

def load_channels(root, only=None):
    """Every channels/*/channel.json, merged with factory_worker.UPLOAD_DEFAULTS
    (the single source of truth for audience/token, playbook §14) — the config
    file never re-declares what UPLOAD_DEFAULTS already owns."""
    from factory_worker import UPLOAD_DEFAULTS
    out = []
    for path in sorted(glob.glob(os.path.join(root, "*", "channel.json"))):
        with open(path) as f:
            cfg = json.load(f)
        cfg["dir"] = os.path.dirname(path)
        cfg["config_path"] = path
        key = cfg.get("key")
        if not key:
            print(f"!! {path}: no 'key' — skipped (never guessed)")
            continue
        if only and key != only:
            continue
        defaults = UPLOAD_DEFAULTS.get(key)
        if not defaults:
            print(f"!! {key}: not in factory_worker.UPLOAD_DEFAULTS — skipped")
            continue
        cfg["audience"] = defaults["audience"]
        # config may say made_for_kids, but UPLOAD_DEFAULTS is authoritative
        cfg["made_for_kids"] = (defaults["audience"] == "kids")
        cfg.setdefault("cadence_days", 1)
        cfg.setdefault("guard_days", 7)
        cfg.setdefault("calendar", "CONTENT-CALENDAR.csv")
        out.append(cfg)
    return out


def read_slots(cfg, today, days):
    """Open calendar rows whose planned_date falls in (today, today+days].

    Today itself is excluded: at 06:37 IST a 16:00 IST slot is still hours from
    needing a scheduled video, and flagging it every morning trains the operator
    to ignore the alert.
    """
    path = os.path.join(cfg["dir"], cfg["calendar"])
    if not os.path.exists(path):
        return None, []
    window = {str(today + timedelta(days=i)) for i in range(1, days + 1)}
    slots = []
    with open(path) as f:
        for row in csv.DictReader(f):
            raw = (row.get("planned_date") or "").strip()
            if CLOSED_RE.search(raw):
                continue
            m = DATE_RE.search(raw)
            if not m or m.group(1) not in window:
                continue
            slots.append({
                "date": m.group(1),
                "title": (row.get("working_title") or row.get("title") or "").strip(),
                "_row": row,
            })
    slots.sort(key=lambda s: s["date"])
    return path, slots


# ------------------------------------------------------------------ checks

def run_verify(key, slots, days):
    """scripts/verify_uploads.py in its default READ-ONLY mode. Returns
    (exit_code, parsed_json_or_None, stdout). Its --expected matcher is the
    playbook-blessed one (publishAt OR publishedAt) — don't re-implement it."""
    with tempfile.TemporaryDirectory() as td:
        exp = os.path.join(td, "expected.json")
        out = os.path.join(td, "result.json")
        with open(exp, "w") as f:
            json.dump([{"date": s["date"], "title": s["title"]} for s in slots], f)
        cmd = [sys.executable, "scripts/verify_uploads.py", "--channel", key, "--json", out]
        if slots:
            cmd += ["--expected", exp]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        data = None
        if os.path.exists(out):
            with open(out) as f:
                data = json.load(f)
    return p.returncode, data, (p.stdout or "") + (p.stderr or "")


def check_comments(key):
    """Videos with unread-able-but-present comments, for NON-MFK channels only.

    Uses the uploads playlist (1 quota unit) + videos.list statistics — never
    search.list (100 units) and never commentThreads, which needs the
    force-ssl scope most tokens haven't re-consented to yet (playbook §9b).
    So this reports 'there are N comments here', not 'N are unanswered'.
    """
    from yt_upload import get_creds, token_path
    from googleapiclient.discovery import build
    if not os.path.exists(token_path(key)):
        return None, f"no token at {token_path(key)}"
    yt = build("youtube", "v3", credentials=get_creds(key, False))
    ch = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0]
    pl = yt.playlistItems().list(part="contentDetails", maxResults=50,
                                 playlistId=ch["contentDetails"]["relatedPlaylists"]["uploads"]).execute()
    ids = [i["contentDetails"]["videoId"] for i in pl.get("items", [])]
    hot = []
    for chunk in (ids[i:i + 50] for i in range(0, len(ids), 50)):
        vr = yt.videos().list(part="snippet,statistics,status", id=",".join(chunk)).execute()
        for v in vr.get("items", []):
            if v["status"].get("privacyStatus") != "public":
                continue
            n = int(v.get("statistics", {}).get("commentCount", 0) or 0)
            if n:
                hot.append((v["id"], v["snippet"]["title"], n))
    return hot, None


# ------------------------------------------------------------------ reporting

def write_needs_attention(cfg, calendar_path, empty, stamp):
    """channels/<dir>/NEEDS-ATTENTION.md — same shape the claude-tricks guard
    has always written, now with every non-empty calendar column preserved so
    channels can keep their own schema."""
    path = os.path.join(cfg["dir"], "NEEDS-ATTENTION.md")
    with open(path, "w") as f:
        f.write(f"# Needs attention — {cfg['name']} (`{cfg['key']}`) — {stamp}\n\n")
        f.write(f"Empty guarded publish slots: **{', '.join(s['date'] for s in empty)}**\n\n")
        f.write(f"Calendar: `{os.path.relpath(calendar_path, REPO)}` · "
                f"cadence: {cfg.get('cadence_label', cfg['cadence_days'])} · "
                f"slot time: {cfg.get('slot_time_ist', '16:00')} IST\n\n")
        for s in empty:
            row = s["_row"]
            f.write(f"## {s['date']} — {s['title'] or '(untitled row)'}\n")
            for col, val in row.items():
                if col in ("planned_date", "working_title", "title") or not (val or "").strip():
                    continue
                f.write(f"- **{col}**: {val.strip()}\n")
            f.write("\n")
        f.write(f"Produce with: {cfg.get('produce_hint', 'open a Claude session and produce the calendar row')}\n")
    return path


def channel_report(cfg, res):
    """Markdown block + the list of headline problems for one channel."""
    lines = [f"## {cfg['name']} (`{cfg['key']}`)"]
    lines.append(f"Cadence {cfg.get('cadence_label', cfg['cadence_days'])} · "
                 f"guard window {cfg['guard_days']}d · "
                 f"{'MFK — no comments' if cfg['made_for_kids'] else 'non-MFK'}")
    problems = []

    if res.get("error"):
        lines.append(f"\n⚠️ **CHECK FAILED — {res['error']}**\n")
        problems.append(f"{cfg['key']}: check failed")
        return lines, problems

    if res["calendar_path"] is None:
        lines.append(f"\n⚠️ **no calendar** at `{cfg['calendar']}` — nothing guarded.\n")
        problems.append(f"{cfg['key']}: no calendar")
        return lines, problems

    guarded, empty = res["slots"], res["empty"]
    filled = [s for s in guarded if s["date"] not in {e["date"] for e in empty}]
    lines.append("")
    lines.append("| Guarded slot | Title | State |")
    lines.append("|---|---|---|")
    for s in guarded:
        state = "🟥 EMPTY — needs attention" if s in empty else "🟩 filled (scheduled/public)"
        lines.append(f"| {s['date']} | {s['title'][:60] or '—'} | {state} |")
    if not guarded:
        lines.append("| — | no open calendar rows in window | — |")
    lines.append("")
    lines.append(f"Guarded **{len(guarded)}** · pending **{len(empty)}** · filled **{len(filled)}**")

    if empty:
        problems.append(f"{cfg['key']}: {len(empty)} empty slot(s) {', '.join(e['date'] for e in empty)}")
        lines.append(f"→ wrote `{os.path.relpath(res['needs_attention'], REPO)}`")

    # cadence coverage: how many slots SHOULD the window hold?
    want = max(1, cfg["guard_days"] // max(1, cfg["cadence_days"]))
    if res["calendar_rows_in_window"] < want:
        lines.append(f"- ℹ️ calendar thin: {res['calendar_rows_in_window']} row(s) in the next "
                     f"{cfg['guard_days']}d, cadence implies ~{want}")

    v = res.get("verify") or {}
    if res["verify_rc"] is None:
        lines.append("- ⚠️ verify_uploads.py did not run")
    else:
        dupes = v.get("duplicate_title_groups") or []
        near = v.get("near_duplicate_pairs") or []
        stale = v.get("stale_public_delete_prefixed") or []
        booked = v.get("double_booked_slots") or {}
        comp = v.get("compliance_issues") or []
        for label, items in (("duplicate titles live", dupes), ("near-duplicate titles", near),
                             ("stale 🗑️ DELETE still public", stale), ("compliance", comp)):
            if items:
                lines.append(f"- 🟥 verify_uploads: {len(items)} {label}")
        for day, vids in booked.items():
            lines.append(f"- 🟥 verify_uploads: {day} double-booked ({len(vids)} videos)")
        # Count only HYGIENE findings as new problems. verify_uploads' exit code
        # also fires on empty slots (already reported above) and on orphans --
        # every already-shipped video whose calendar row predates these
        # calendars is an "orphan", so folding those into the headline would
        # cry wolf every single morning.
        hygiene = len(dupes) + len(near) + len(stale) + len(booked) + len(comp)
        orphans = len(v.get("orphan_videos") or [])
        if hygiene:
            problems.append(f"{cfg['key']}: {hygiene} verify_uploads hygiene issue(s)")
            lines.append(f"- run `python3 scripts/verify_uploads.py --channel {cfg['key']}` for the detail")
        else:
            lines.append(f"- ✅ verify_uploads: no duplicates / stale deletes / double-booked days"
                         + (f" (exit {res['verify_rc']} = the empty slots above)" if res["verify_rc"] else ""))
        if orphans:
            lines.append(f"- ℹ️ {orphans} live video(s) match no guarded calendar row "
                         f"(expected for back-catalogue predating this calendar)")

    if cfg["made_for_kids"]:
        lines.append("- comments: n/a (Made-for-Kids — YouTube disables them)")
    elif res.get("comments_error"):
        lines.append(f"- ⚠️ comment check: {res['comments_error']}")
    elif res.get("comments"):
        for vid, title, n in res["comments"]:
            lines.append(f"- 💬 {n} comment(s) on “{title[:50]}” — "
                         f"studio.youtube.com/video/{vid}/comments")
    else:
        lines.append("- 💬 no comments on public videos")
    lines.append("")
    return lines, problems


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, help="override every channel's guard_days")
    ap.add_argument("--channel", help="check one channel key only")
    ap.add_argument("--channels-root", default=os.path.join(REPO, "channels"),
                    help="where to find <dir>/channel.json (for testing)")
    ap.add_argument("--no-notify", action="store_true", help="skip the macOS notification")
    ap.add_argument("--skip-comments", action="store_true", help="skip the non-MFK comment check")
    a = ap.parse_args()

    t0 = time.time()
    today = datetime.now(timezone.utc).date()
    stamp = f"{datetime.now():%Y-%m-%d %H:%M}"
    channels = load_channels(a.channels_root, a.channel)
    if not channels:
        sys.exit(f"!! no channel configs under {a.channels_root}")

    blocks, all_problems = [], []
    for cfg in channels:
        if a.days:
            cfg["guard_days"] = a.days
        res = {"calendar_path": None, "slots": [], "empty": [], "verify": None,
               "verify_rc": None, "calendar_rows_in_window": 0}
        try:
            cal, slots = read_slots(cfg, today, cfg["guard_days"])
            res["calendar_path"], res["slots"] = cal, slots
            res["calendar_rows_in_window"] = len(slots)
            if cal is not None:
                rc, data, out = run_verify(cfg["key"], slots, cfg["guard_days"])
                res["verify_rc"], res["verify"] = rc, data
                if data is None:
                    res["error"] = f"verify_uploads produced no JSON (exit {rc}): {out.strip()[-200:]}"
                else:
                    empty_dates = {s["date"] for s in (data.get("empty_slots") or [])}
                    res["empty"] = [s for s in slots if s["date"] in empty_dates]
                    if res["empty"]:
                        res["needs_attention"] = write_needs_attention(cfg, cal, res["empty"], stamp)
                if not cfg["made_for_kids"] and not a.skip_comments:
                    res["comments"], res["comments_error"] = check_comments(cfg["key"])
        except Exception as e:
            res["error"] = f"{type(e).__name__}: {e}"
        block, problems = channel_report(cfg, res)
        blocks += block
        all_problems += problems

    header = [f"# Network — publish-slot guard — {stamp}",
              "",
              "Auto-generated by `scripts/daily_check.py` (read-and-report only — this "
              "script never uploads, retitles, retires, reschedules or unschedules anything).",
              f"Guarding {len(channels)} channel(s) from {today + timedelta(days=1)}.",
              ""]
    if all_problems:
        header.append("## ⚠️ Needs attention")
        header += [f"- {p}" for p in all_problems]
    else:
        header.append("## ✅ All guarded slots filled and all channels clean")
    header.append("")
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    report = "\n".join(header + blocks) + "\n"
    with open(REPORT, "w") as f:
        f.write(report)
    print(report)
    print(f">> wrote {os.path.relpath(REPORT, REPO)} in {time.time() - t0:.1f}s")

    if not a.no_notify:
        notify(f"⚠️ {len(all_problems)} item(s): {'; '.join(all_problems)[:180]} — see NETWORK-ATTENTION.md"
               if all_problems else
               f"All {len(channels)} channels clean — slots filled")
    sys.exit(1 if all_problems else 0)


if __name__ == "__main__":
    main()
