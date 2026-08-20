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
    ap.add_argument("--format", dest="fmt", default="short", choices=["short", "longform"],
                    help="delivery format for app categorization (default short)")
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
            "origin": "local-session", "kind": "content", "format": a.fmt,
            # direct mode is what makes the row surface on the Studio board
            # (?r=staged filters to production_mode in staged|direct)
            "production_mode": "direct",
        }])
        cal_id = created[0]["id"]
        print(f">> created factory_calendar row {cal_id} (format={a.fmt})")

    name = os.path.basename(path)
    storage = f"{a.channel}/assets/{cal_id}/_preview/{uuid.uuid4().hex[:8]}_{name}"
    with open(path, "rb") as f:
        supa.upload(storage, f.read(), mimetypes.guess_type(name)[0] or "video/mp4")
    # `title` MUST be patched too. Re-syncing an existing --calendar-id updated the
    # preview file but left the row's original title in place, so a title correction
    # made after the first sync never reached the board the reviewer actually reads —
    # and a title is the one thing they approve as much as the cut. (Hit for real on
    # _game: the title was fixed to add the "game" keyword, re-synced, and the board
    # still showed the old one.) Same for the brief, when one is supplied.
    patch = {"preview_path": storage, "preview_at": fw.now_iso(),
             "status": "produced", "format": a.fmt,
             "production_mode": "direct", "title": a.title}
    if a.brief:
        patch["brief"] = a.brief
    supa.patch("factory_calendar", f"id=eq.{cal_id}", patch)

    # Register the preview as factory_assets rows. WITHOUT THIS the Studio board hides
    # the row: ?r=staged drops direct-mode items that have no assets AND no in-flight
    # preview job ("plain unstarted rows, not production"). A stamped preview_path alone
    # is not enough. Also push a cover frame so the card has a thumbnail.
    # RE-SYNC MUST BUMP THE VERSION. factory_assets has a unique constraint on
    # (calendar_id, asset_key, version), so a hardcoded version=1 made every
    # re-sync to the same calendar row fail with a 409 — and the failure was
    # SILENT in the way that matters: calendar.preview_path advanced to the new
    # file while factory_assets still pointed at the old one, so the Studio board
    # kept serving a SUPERSEDED cut. That is worse than a hidden row: "I re-synced
    # the fix" reads as true while the reviewer is still watching the broken take.
    def _next_version(asset_key):
        try:
            rows = supa.select(
                "factory_assets",
                f"calendar_id=eq.{cal_id}&asset_key=eq.{asset_key}"
                "&select=version&order=version.desc&limit=1")
            return (rows[0]["version"] + 1) if rows else 1
        except Exception:
            return 1

    try:
        assets = [{
            "calendar_id": cal_id, "channel_key": a.channel, "asset_key": "preview_master",
            "kind": "video", "group_key": "clip", "status": "review",
            "version": _next_version("preview_master"),
            "storage_path": storage, "filename": name, "title": a.title[:80],
        }]
        cover_store = None
        try:
            import subprocess, tempfile
            with tempfile.TemporaryDirectory() as td:
                cov = os.path.join(td, "cover.jpg")
                subprocess.run(["ffmpeg", "-y", "-ss", "2.5", "-i", path,
                                "-frames:v", "1", cov],
                               check=True, capture_output=True)
                cover_store = f"{a.channel}/assets/{cal_id}/_preview/cover_{uuid.uuid4().hex[:8]}.jpg"
                with open(cov, "rb") as f:
                    supa.upload(cover_store, f.read(), "image/jpeg")
            assets.append({
                "calendar_id": cal_id, "channel_key": a.channel, "asset_key": "cover",
                "kind": "image", "group_key": "thumbnail", "status": "review",
                "version": _next_version("cover"),
                "storage_path": cover_store, "filename": "cover.jpg", "title": "cover",
            })
        except Exception as e:
            print(f"!! cover frame skipped (non-fatal): {e}")
        supa.insert("factory_assets", assets)
        print(f">> registered {len(assets)} asset(s) so the Studio board shows this row")
    except Exception as e:
        # Loud, because the failure mode is a STALE preview, not just a hidden row.
        print(f"!! ASSET REGISTRATION FAILED — the Studio board may still be serving a "
              f"PREVIOUS cut for this row; verify factory_assets.preview_master before "
              f"asking anyone to review: {e}")

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
