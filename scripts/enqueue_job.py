#!/usr/bin/env python3
"""enqueue_job.py — queue a single factory_jobs row from the command line.

The dashboard is the normal way to create jobs; this is the scriptable path for
when you're already in a terminal (or driving from another script). It reuses
factory_worker's env loader + Supa client, so it reads the same
secrets/factory.env (SUPABASE_URL + SUPABASE_SERVICE_KEY) the worker does.

A queued row is picked up by any live, un-paused worker on its next poll (~10s);
there is no separate "run" step. Model/effort map exactly as the worker maps
them (fable -> claude-fable-5; opus/sonnet/haiku pass straight to `claude
--model`; effort = low|medium|high|xhigh|max).

Examples:
  # produce the Aug 17 short (tips lane) on sonnet/low -- resolves the
  # factory_calendar UUID from the planned date so you don't paste it by hand
  python3 scripts/enqueue_job.py produce_short \
      --channel claude-tricks --model sonnet --effort low \
      --calendar-date 2026-08-17 \
      --title "Stop Trusting The First AI Answer — Ask This 🧠" \
      --prompt "TIPS LANE single-tape fail->fix->proof (record_demo --followup + --fix-seed-terms)."

  # a free-form analysis job (no calendar item)
  python3 scripts/enqueue_job.py custom \
      --channel claude-tricks --model sonnet --effort low \
      --title "BC01 retention read" \
      --prompt "Run scripts/yt_retention.py ... and read the curve vs the Aug 21 thresholds."
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from factory_worker import load_env, Supa, now_iso  # noqa: E402


def resolve_calendar_id(supa, channel, date):
    """factory_calendar UUID for (channel, planned_date). Prints nearby rows and
    exits non-zero if there's no match, so a typo'd date fails loud, not silent."""
    rows = supa.select(
        "factory_calendar",
        f"channel_key=eq.{channel}&planned_date=eq.{date}&select=id,title,status")
    if rows:
        r = rows[0]
        print(f"resolved calendar item {r['id']}  {r['title']!r} ({r['status']})")
        return r["id"]
    print(f"!! no factory_calendar row for {channel} on {date}. Nearby rows:", file=sys.stderr)
    for r in supa.select(
            "factory_calendar",
            f"channel_key=eq.{channel}&planned_date=gte.{date}"
            "&select=planned_date,id,title,status&order=planned_date&limit=8"):
        print(f"   {r['planned_date']}  {r['id']}  {r['title']!r} ({r['status']})", file=sys.stderr)
    sys.exit(2)


def main():
    ap = argparse.ArgumentParser(description="Queue one factory_jobs row.")
    ap.add_argument("job_type", help="produce_short | custom | analyze_and_suggest | ...")
    ap.add_argument("--channel", required=True, help="channel_key, e.g. claude-tricks")
    ap.add_argument("--prompt", required=True, help="the job brief / instruction")
    ap.add_argument("--title", default="", help="job title (dashboard label)")
    ap.add_argument("--model", default="", help="fable|opus|sonnet|haiku (blank = queue default)")
    ap.add_argument("--effort", default="", help="low|medium|high|xhigh|max (blank = worker default)")
    ap.add_argument("--meta", default="",
                    help='extra meta JSON, e.g. \'{"script_path": "deploy/restart_worker.sh"}\'')
    ap.add_argument("--calendar-id", default="", help="factory_calendar UUID (meta.calendar_id)")
    ap.add_argument("--calendar-date", default="",
                    help="resolve meta.calendar_id from this planned_date instead of pasting a UUID")
    ap.add_argument("--dry-run", action="store_true", help="print the row; don't insert")
    a = ap.parse_args()

    # Supa is only built when we actually touch the DB -- a pure --dry-run
    # (no calendar-date to resolve) works without secrets/factory.env present.
    supa = None

    def _supa():
        nonlocal supa
        if supa is None:
            env = load_env()
            supa = Supa(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
        return supa

    cal_id = a.calendar_id
    if a.calendar_date and not cal_id:
        cal_id = resolve_calendar_id(_supa(), a.channel, a.calendar_date)

    job = {
        "type": a.job_type,
        "channel_key": a.channel,
        "prompt": a.prompt,
        "status": "queued",
        "created_at": now_iso(),
    }
    if a.title:
        job["title"] = a.title
    if a.model:
        job["model"] = a.model
    if a.effort:
        job["effort"] = a.effort
    meta = {}
    if a.meta:
        import json as _json
        try:
            meta = _json.loads(a.meta)
            assert isinstance(meta, dict)
        except (ValueError, AssertionError):
            sys.exit(f"--meta must be a JSON object, got: {a.meta!r}")
    if cal_id:
        meta["calendar_id"] = cal_id
    if meta:
        job["meta"] = meta

    if a.dry_run:
        import json
        print(json.dumps(job, indent=2, ensure_ascii=False))
        return

    row = _supa().insert_returning("factory_jobs", [job])
    jid = row[0]["id"] if isinstance(row, list) and row else "?"
    print(f"queued {a.job_type} on {a.model or 'default'}/{a.effort or 'default'}  id={jid}")
    print("a live worker will claim it on its next poll (~10s).")


if __name__ == "__main__":
    main()
