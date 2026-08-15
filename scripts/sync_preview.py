#!/usr/bin/env python3
"""sync_preview — push a locally-rendered master/preview to the factory app.

VJ directive 2026-08-15: every produced master gets synced to the factory app
(StudioBoard program monitor) so approval happens THERE, not over chat files.
This wraps the exact mechanism the worker's finish_preview_episode uses:
upload to <channel>/assets/<calendar_id>/_preview/ in the factory-renders
bucket, stamp factory_calendar.preview_path/preview_at, log a preview_ready
event. It never publishes or arms anything.

If no matching factory_calendar row exists (repo-CSV-planned episodes like
Build Club chapters), one is created (status 'produced') so the board has a
card to hang the preview on.

Usage:
  python3 scripts/sync_preview.py --channel claude-tricks \
      --file channels/claude-tricks/renders/epbc01_v2_outro.mp4 \
      --title "I Shipped a Website in 4 Minutes — Your Turn ⏱️" \
      --date 2026-08-17 [--calendar-id UUID] [--brief "..."]
"""
import argparse, mimetypes, os, sys, uuid

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
import factory_worker as fw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True)
    ap.add_argument("--file", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--date", required=True, help="planned_date YYYY-MM-DD")
    ap.add_argument("--calendar-id", default=None)
    ap.add_argument("--brief", default="")
    a = ap.parse_args()

    path = a.file if os.path.isabs(a.file) else os.path.join(REPO, a.file)
    if not os.path.exists(path):
        sys.exit(f"!! file not found: {path}")

    env = fw.load_env()
    supa = fw.Supa(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])

    cal_id = a.calendar_id
    if not cal_id:
        rows = supa.select(
            "factory_calendar",
            f"select=id,title&channel_key=eq.{a.channel}"
            f"&planned_date=eq.{a.date}&title=eq.{fw.requests.utils.quote(a.title)}")
        if rows:
            cal_id = rows[0]["id"]
    if not cal_id:
        created = supa.insert_returning("factory_calendar", [{
            "channel_key": a.channel, "planned_date": a.date, "title": a.title,
            "brief": a.brief, "type": "video", "status": "produced",
            "origin": "local-session", "kind": "content",
        }])
        cal_id = created[0]["id"]
        print(f">> created factory_calendar row {cal_id}")

    name = os.path.basename(path)
    storage = f"{a.channel}/assets/{cal_id}/_preview/{uuid.uuid4().hex[:8]}_{name}"
    with open(path, "rb") as f:
        supa.upload(storage, f.read(), mimetypes.guess_type(name)[0] or "video/mp4")
    supa.patch("factory_calendar", f"id=eq.{cal_id}",
               {"preview_path": storage, "preview_at": fw.now_iso(),
                "status": "produced"})
    try:
        supa.insert("factory_events", [{
            "kind": "preview_ready",
            "message": f"preview synced from local session ({name})",
            "meta": {"calendar_id": cal_id, "channel_key": a.channel},
        }])
    except Exception as e:  # best-effort, same as the worker
        print(f"!! event log failed (non-fatal): {e}")
    print(f">> preview -> {storage}\n>> calendar {cal_id} stamped — review it on the factory app")


if __name__ == "__main__":
    main()
