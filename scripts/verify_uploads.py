#!/usr/bin/env python3
"""
Playbook §9 "verify after every upload/swap" discipline, automated.

Pulls a channel's full public+scheduled video list (search.list forMine +
videos.list status), then detects the failure modes that have repeatedly
slipped through manual swaps:
  - duplicate / near-duplicate titles live in public+scheduled state
  - videos still PUBLIC that carry the '🗑️ DELETE — ' retire prefix
    (i.e. someone renamed for cleanup but forgot to actually retire it)
  - a scheduled slot (same publishAt day) holding two videos
  - (with --expected) calendar slots with no video, and videos matching
    no expected slot
  - per-channel-type compliance, read from scripts/factory_worker.py's
    UPLOAD_DEFAULTS (never guessed)

⚠️ containsSyntheticMedia is WRITE-ONLY (playbook §8/§9)
The YouTube Data API accepts status.containsSyntheticMedia on videos.insert /
videos.update but NEVER returns it on videos.list -- verified against the live
claude-tricks + aashiqana lists (field absent from every status resource, even
on videos this repo uploaded with `yt_upload.py --synthetic`). So disclosure
CANNOT be audited by reading. Treating an absent field as "not disclosed" is a
false positive on every single video, which is exactly what an earlier build of
this script did. Instead:
  - synthetic disclosure is reported as ADVISORY (never a discrepancy) unless
    --strict-disclosure is passed;
  - it becomes verifiable only by (re-)asserting it: --assert-disclosure writes
    containsSyntheticMedia=true and records the video in a local ledger at
    channels/<key>/disclosure_ledger.json. Ledger entries are only ever written
    for videos we actually asserted -- never inferred, never backfilled.
madeForKids IS readable, so the kids / notForKids audience checks are real.

NEVER deletes or unschedules anything. --fix-titles only ADDS the
'🗑️ DELETE — ' prefix, and only to videos the operator explicitly lists on
stdin (one video ID per line) -- guarded against the live/scheduled keep-set.
--assert-disclosure round-trips the full status resource and re-reads each
video afterwards, aborting if privacyStatus/publishAt moved by a hair.

Usage:
    python3 scripts/verify_uploads.py --channel claude-tricks
    python3 scripts/verify_uploads.py --channel aashiqana --expected slots.json --json out.json
    echo VIDEO_ID_TO_RETIRE | python3 scripts/verify_uploads.py --channel vehicles --fix-titles
    python3 scripts/verify_uploads.py --channel claude-tricks --assert-disclosure          # dry run
    python3 scripts/verify_uploads.py --channel claude-tricks --assert-disclosure --yes    # writes

Exit code is non-zero whenever discrepancies are found (so this can be the
mandatory last step of scripts/factory_worker.py and the daily launchd checks).
"""
import argparse, difflib, json, os, sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
os.chdir(REPO)

DELETE_PREFIX = "🗑️ DELETE — "
TITLE_SIM_THRESHOLD = 0.88  # near-duplicate cutoff (difflib ratio)

# status fields we must echo back on videos.update so a partial body can never
# unschedule / re-privatise a video (videos.update REPLACES the whole part).
STATUS_ROUNDTRIP = ("privacyStatus", "publishAt", "license", "embeddable",
                    "publicStatsViewable", "selfDeclaredMadeForKids")


def ledger_path(channel):
    return os.path.join(REPO, "channels", channel, "disclosure_ledger.json")


def load_ledger(channel):
    """{video_id: {"asserted_at": iso, "containsSyntheticMedia": true}}.
    Only ever contains videos this script actually wrote the flag to."""
    p = ledger_path(channel)
    if not os.path.exists(p):
        return {}
    with open(p) as f:
        return json.load(f)


def save_ledger(channel, ledger):
    p = ledger_path(channel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(ledger, f, indent=2, sort_keys=True)
    return p


def load_upload_defaults():
    """Reuse factory_worker.py's UPLOAD_DEFAULTS -- the single source of
    truth for per-channel audience/synthetic/token_file. Don't re-declare it."""
    import factory_worker
    return factory_worker.UPLOAD_DEFAULTS


def fetch_channel_videos(channel):
    """Full public+scheduled list via search.list forMine + videos.list status.
    Reuses the OAuth plumbing in yt_upload.py -- no reimplementation."""
    from yt_upload import get_creds, token_path
    from googleapiclient.discovery import build
    # get_creds() falls back to an INTERACTIVE browser consent flow when the
    # token is missing -- which hangs forever under launchd. This script is a
    # non-interactive checker, so fail loudly instead.
    tp = token_path(channel)
    if not os.path.exists(tp):
        sys.exit(f"!! no token for channel {channel!r} at {tp} — "
                 f"authorize once with: python3 scripts/yt_upload.py --channel {channel} --auth")
    creds = get_creds(channel, False)
    yt = build("youtube", "v3", credentials=creds)

    ids, page_token = [], None
    while True:
        kw = dict(part="id", forMine=True, type="video", maxResults=50, order="date")
        if page_token:
            kw["pageToken"] = page_token
        resp = yt.search().list(**kw).execute()
        ids.extend(i["id"]["videoId"] for i in resp.get("items", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    videos = []
    for chunk in (ids[i:i + 50] for i in range(0, len(ids), 50)):
        vr = yt.videos().list(part="snippet,status", id=",".join(chunk)).execute()
        for v in vr.get("items", []):
            st = v.get("status", {})
            videos.append({
                "id": v["id"],
                "title": v["snippet"]["title"],
                "privacyStatus": st.get("privacyStatus", ""),
                # scheduled videos carry status.publishAt; already-public ones
                # carry only snippet.publishedAt -- keep both, the calendar
                # matcher needs the union or every published slot reads EMPTY.
                "publishAt": st.get("publishAt", "") or "",
                "publishedAt": v["snippet"].get("publishedAt", "") or "",
                "madeForKids": st.get("madeForKids", None),
                "selfDeclaredMadeForKids": st.get("selfDeclaredMadeForKids", None),
                # NOTE: containsSyntheticMedia is write-only and is never present
                # here. Kept only so the raw status/snippet round-trip honestly
                # -- videos.update REPLACES a whole part, so anything we don't
                # echo back gets wiped.
                "_status": st,
                "_snippet": v["snippet"],
            })
    return yt, videos


def effective_day(v):
    """The day this video occupies on the calendar: its scheduled publishAt if
    still pending, else the day it actually went public."""
    stamp = v["publishAt"] or v["publishedAt"]
    return stamp[:10] if stamp else None


def public_or_scheduled(videos):
    """The set the playbook cares about: live now, or waiting to go live."""
    return [v for v in videos
            if v["privacyStatus"] == "public"
            or (v["privacyStatus"] == "private" and v["publishAt"])]


def norm_title(t):
    return t.strip().lower()


def detect_duplicates(videos):
    """Exact + near-duplicate titles among public+scheduled videos."""
    live = public_or_scheduled(videos)
    exact, seen = [], {}
    for v in live:
        key = norm_title(v["title"])
        seen.setdefault(key, []).append(v)
    for key, group in seen.items():
        if len(group) > 1:
            exact.append(group)

    near = []
    checked = set()
    for i, a in enumerate(live):
        for b in live[i + 1:]:
            if norm_title(a["title"]) == norm_title(b["title"]):
                continue  # already reported as exact
            pair = frozenset((a["id"], b["id"]))
            if pair in checked:
                continue
            checked.add(pair)
            ratio = difflib.SequenceMatcher(None, norm_title(a["title"]), norm_title(b["title"])).ratio()
            if ratio >= TITLE_SIM_THRESHOLD:
                near.append((a, b, ratio))
    return exact, near


def detect_stale_public_deletes(videos):
    """Videos PUBLIC that carry the retire prefix -- renamed but not retired."""
    return [v for v in videos if v["privacyStatus"] == "public" and v["title"].startswith(DELETE_PREFIX)]


def detect_double_booked_slots(videos):
    """Two scheduled (private + publishAt) videos landing on the same day."""
    by_day = {}
    for v in videos:
        if v["privacyStatus"] == "private" and v["publishAt"]:
            day = v["publishAt"][:10]
            by_day.setdefault(day, []).append(v)
    return {day: group for day, group in by_day.items() if len(group) > 1}


def detect_slot_mismatches(videos, expected):
    """expected: list of {"date": "YYYY-MM-DD", "title": "..."} calendar slots.
    Matches by publishAt day (public videos use publishedAt-less heuristic:
    any public/scheduled video whose day matches). Reports empty slots and
    unmatched (orphan) videos."""
    live = public_or_scheduled(videos)
    video_days = {}
    for v in live:
        video_days.setdefault(effective_day(v), []).append(v)

    empty_slots, matched_ids = [], set()
    for slot in expected:
        day = slot.get("date")
        candidates = video_days.get(day, [])
        if not candidates:
            empty_slots.append(slot)
        else:
            for c in candidates:
                matched_ids.add(c["id"])

    orphans = [v for v in live if v["id"] not in matched_ids and effective_day(v)]
    return empty_slots, orphans


def detect_compliance(channel, videos, defaults, ledger, strict_disclosure=False):
    """Per-channel-type flags per playbook §8/§9 / COPPA / synthetic disclosure.

    Returns (issues, advisories). Only `issues` count as discrepancies.

    madeForKids round-trips through the API, so audience mismatches are hard
    findings. containsSyntheticMedia does NOT round-trip (write-only), so an
    unasserted video is an ADVISORY -- "we cannot confirm this by reading" --
    not a violation. --strict-disclosure promotes advisories to issues for
    operators who have adopted the ledger and want CI to enforce it.
    """
    cfg = defaults.get(channel)
    issues, advisories = [], []
    if not cfg:
        return issues, advisories  # unknown channel key -> skip, don't guess
    live = public_or_scheduled(videos)

    if cfg.get("synthetic"):
        unasserted = [v for v in live if ledger.get(v["id"], {}).get("containsSyntheticMedia") is not True]
        if unasserted:
            advisories.append(
                f"synthetic-host channel: containsSyntheticMedia is write-only, so the API cannot "
                f"confirm disclosure for {len(unasserted)}/{len(live)} public+scheduled video(s). "
                f"Videos uploaded via `yt_upload.py --synthetic` DID set it at insert. "
                f"Run `--assert-disclosure --yes` to re-assert and record it in "
                f"channels/{channel}/disclosure_ledger.json.")
            for v in unasserted:
                advisories.append(f"    {v['id']}  not in disclosure ledger  — {v['title'][:60]}")
            if strict_disclosure:
                issues.extend(f"{v['id']}  synthetic disclosure unasserted (--strict-disclosure)  — {v['title'][:60]}"
                              for v in unasserted)

    if cfg.get("audience") == "kids":
        for v in live:
            if v["selfDeclaredMadeForKids"] is not True and v["madeForKids"] is not True:
                issues.append(f"{v['id']}  kids channel but madeForKids != true  — {v['title'][:60]}")
    elif cfg.get("audience") == "notForKids":
        # the inverse mistake is just as costly: a made-for-kids flag on an
        # adult channel silently kills comments, end screens and monetisation.
        for v in live:
            if v["madeForKids"] is True or v["selfDeclaredMadeForKids"] is True:
                issues.append(f"{v['id']}  notForKids channel but madeForKids == true  — {v['title'][:60]}")
    return issues, advisories


def assert_disclosure(yt, channel, videos, ledger, apply):
    """Re-assert status.containsSyntheticMedia=true on every public+scheduled
    video of a synthetic-host channel, then record it in the local ledger.

    Safety (playbook: never delete, never unschedule):
      - videos.update REPLACES the whole `status` part, so the current status
        is echoed back field-for-field; a missing publishAt would unschedule
        the video, which is exactly the failure this script exists to catch.
      - after each write the video is re-read and privacyStatus/publishAt are
        compared; the first drift aborts the run before touching anything else.
      - dry run by default; writes only with --yes.
    """
    live = public_or_scheduled(videos)
    planned, written = [], []
    for v in live:
        body_status = {k: v["_status"][k] for k in STATUS_ROUNDTRIP if k in v["_status"]}
        body_status["containsSyntheticMedia"] = True
        planned.append((v, body_status))

    if not apply:
        return planned, written, None

    for v, body_status in planned:
        yt.videos().update(part="status", body={"id": v["id"], "status": body_status}).execute()
        after = yt.videos().list(part="status", id=v["id"]).execute()["items"][0]["status"]
        drift = [k for k in ("privacyStatus", "publishAt")
                 if (after.get(k, "") or "") != (v["_status"].get(k, "") or "")]
        if drift:
            return planned, written, (
                f"ABORTED after {v['id']}: {', '.join(drift)} changed "
                f"({', '.join(f'{k}: {v['_status'].get(k)!r} -> {after.get(k)!r}' for k in drift)}). "
                f"No further videos touched -- fix this video in Studio first.")
        ledger[v["id"]] = {
            "asserted_at": datetime.now(timezone.utc).isoformat(),
            "containsSyntheticMedia": True,
            "title": v["title"][:100],
        }
        written.append(v)
    return planned, written, None


def fix_titles(yt, videos, ids_to_retire):
    """Prefix titles with the retire marker for operator-listed IDs only.
    Guard keep-set: refuse anything not currently public or scheduled (i.e.
    already private/unlisted with no publishAt needs no marker -- and refuse
    unknown IDs outright)."""
    by_id = {v["id"]: v for v in videos}
    done, refused = [], []
    for vid in ids_to_retire:
        vid = vid.strip()
        if not vid:
            continue
        v = by_id.get(vid)
        if not v:
            refused.append((vid, "not found in this channel's list"))
            continue
        if v["title"].startswith(DELETE_PREFIX):
            refused.append((vid, "already prefixed"))
            continue
        if v["privacyStatus"] not in ("public",) and not (v["privacyStatus"] == "private" and v["publishAt"]):
            refused.append((vid, f"not public/scheduled (privacyStatus={v['privacyStatus']}) -- nothing to retire"))
            continue
        new_title = (DELETE_PREFIX + v["title"])[:100]
        # videos.update REPLACES the whole snippet part: sending only
        # title+categoryId wipes the description and tags and force-recategorises
        # the video (e.g. a music channel's 10 -> 27). Echo the real snippet back
        # and change nothing but the title.
        sn = v["_snippet"]
        body_snippet = {"title": new_title,
                        "description": sn.get("description", ""),
                        "categoryId": sn.get("categoryId", "27")}
        for k in ("tags", "defaultLanguage", "defaultAudioLanguage"):
            if sn.get(k):
                body_snippet[k] = sn[k]
        yt.videos().update(part="snippet", body={"id": vid, "snippet": body_snippet}).execute()
        done.append((vid, v["title"], new_title))
    return done, refused


def render_report(channel, videos, exact_dupes, near_dupes, stale_deletes,
                   double_booked, empty_slots, orphans, compliance_issues, advisories):
    lines = [f"# verify_uploads — {channel}  ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)",
             f"public+scheduled videos: {len(public_or_scheduled(videos))} / total fetched: {len(videos)}", ""]

    def section(title, rows_fn):
        rows = rows_fn()
        lines.append(f"## {title}: {'OK' if not rows else f'{len(rows)} issue(s)'}")
        return rows

    for group in exact_dupes:
        lines.append(f"- DUPLICATE TITLE: {group[0]['title'][:70]!r}")
        for v in group:
            lines.append(f"    {v['id']}  {v['privacyStatus']}  publishAt={v['publishAt'] or '-'}")
    if exact_dupes:
        lines.append("")

    for a, b, ratio in near_dupes:
        lines.append(f"- NEAR-DUPLICATE TITLE ({ratio:.2f}): {a['title'][:60]!r}  vs  {b['title'][:60]!r}")
        lines.append(f"    {a['id']} ({a['privacyStatus']})  /  {b['id']} ({b['privacyStatus']})")
    if near_dupes:
        lines.append("")

    for v in stale_deletes:
        lines.append(f"- STALE PUBLIC + DELETE-PREFIXED: {v['id']}  {v['title'][:70]!r}  (renamed but never retired -- privacy still public)")
    if stale_deletes:
        lines.append("")

    for day, group in double_booked.items():
        lines.append(f"- DOUBLE-BOOKED SLOT {day}:")
        for v in group:
            lines.append(f"    {v['id']}  {v['title'][:60]!r}")
    if double_booked:
        lines.append("")

    for slot in empty_slots:
        lines.append(f"- EMPTY CALENDAR SLOT: {slot.get('date')}  expected {slot.get('title', '(untitled)')!r}")
    if empty_slots:
        lines.append("")

    for v in orphans:
        lines.append(f"- VIDEO MATCHES NO EXPECTED SLOT: {v['id']}  {effective_day(v)}  "
                      f"({'scheduled' if v['publishAt'] else 'published'})  {v['title'][:60]!r}")
    if orphans:
        lines.append("")

    for issue in compliance_issues:
        lines.append(f"- COMPLIANCE: {issue}")
    if compliance_issues:
        lines.append("")

    total = len(exact_dupes) + len(near_dupes) + len(stale_deletes) + len(double_booked) + \
        len(empty_slots) + len(orphans) + len(compliance_issues)
    lines.append(f"TOTAL DISCREPANCIES: {total}")

    # advisories deliberately sit BELOW the total: they are not discrepancies
    # and must never flip the exit code (see the write-only note at the top).
    if advisories:
        lines.append("")
        lines.append("## ADVISORY (not counted -- unverifiable via API)")
        lines.extend(f"- {a}" if not a.startswith("    ") else a for a in advisories)
    return "\n".join(lines), total


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--channel", required=True, help="channel key -> secrets/token_<key>.json")
    ap.add_argument("--expected", help="path to slots.json: [{\"date\": \"YYYY-MM-DD\", \"title\": \"...\"}, ...]")
    ap.add_argument("--fix-titles", action="store_true",
                     help="read video IDs (one per line) from stdin and prefix them with '🗑️ DELETE — '. "
                          "Never deletes/unschedules; guarded by keep-set.")
    ap.add_argument("--assert-disclosure", action="store_true",
                     help="re-assert status.containsSyntheticMedia=true on this synthetic-host channel's "
                          "public+scheduled videos and record them in channels/<key>/disclosure_ledger.json "
                          "(the field is write-only, so this is the ONLY way to make disclosure auditable). "
                          "Dry run unless --yes.")
    ap.add_argument("--yes", action="store_true", help="actually perform --assert-disclosure writes")
    ap.add_argument("--strict-disclosure", action="store_true",
                     help="promote unasserted-disclosure advisories to hard discrepancies (non-zero exit)")
    ap.add_argument("--json", help="also write the full result to this path")
    a = ap.parse_args()

    defaults = load_upload_defaults()
    ledger = load_ledger(a.channel)
    yt, videos = fetch_channel_videos(a.channel)

    if a.assert_disclosure:
        if not defaults.get(a.channel, {}).get("synthetic"):
            sys.exit(f"!! --assert-disclosure refused: {a.channel} is not a synthetic-host channel "
                     f"in UPLOAD_DEFAULTS -- disclosing AI content that isn't AI is its own violation")
        planned, written, abort = assert_disclosure(yt, a.channel, videos, ledger, apply=a.yes)
        if not a.yes:
            print(f">> DRY RUN — would set containsSyntheticMedia=true on {len(planned)} video(s); "
                  f"re-run with --yes to write")
            for v, body in planned:
                print(f"   {v['id']}  {v['privacyStatus']:8}  publishAt={v['publishAt'] or '-'}  "
                      f"{v['title'][:50]!r}")
                print(f"      status round-trip: {json.dumps(body, sort_keys=True)}")
        else:
            for v in written:
                print(f">> disclosed: {v['id']}  {v['title'][:60]!r}")
            if written:
                print(f">> ledger: {save_ledger(a.channel, ledger)}")
            if abort:
                sys.exit(f"!! {abort}")
            yt, videos = fetch_channel_videos(a.channel)

    if a.fix_titles:
        ids_to_retire = [line for line in sys.stdin.read().splitlines() if line.strip()]
        if not ids_to_retire:
            sys.exit("!! --fix-titles requires video IDs on stdin (one per line)")
        done, refused = fix_titles(yt, videos, ids_to_retire)
        for vid, old, new in done:
            print(f">> retired: {vid}  {old[:60]!r} -> {new[:60]!r}")
        for vid, why in refused:
            print(f"!! refused {vid}: {why}")
        # refresh after mutation for the report below
        yt, videos = fetch_channel_videos(a.channel)

    exact_dupes, near_dupes = detect_duplicates(videos)
    stale_deletes = detect_stale_public_deletes(videos)
    double_booked = detect_double_booked_slots(videos)
    compliance_issues, advisories = detect_compliance(
        a.channel, videos, defaults, ledger, strict_disclosure=a.strict_disclosure)

    empty_slots, orphans = [], []
    if a.expected:
        with open(a.expected) as f:
            expected = json.load(f)
        empty_slots, orphans = detect_slot_mismatches(videos, expected)

    report, total = render_report(a.channel, videos, exact_dupes, near_dupes, stale_deletes,
                                   double_booked, empty_slots, orphans, compliance_issues, advisories)
    print(report)

    if a.json:
        result = {
            "channel": a.channel,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "video_count": len(videos),
            "public_or_scheduled_count": len(public_or_scheduled(videos)),
            "duplicate_title_groups": [[v["id"] for v in g] for g in exact_dupes],
            "near_duplicate_pairs": [{"a": a_["id"], "b": b_["id"], "ratio": r} for a_, b_, r in near_dupes],
            "stale_public_delete_prefixed": [v["id"] for v in stale_deletes],
            "double_booked_slots": {day: [v["id"] for v in g] for day, g in double_booked.items()},
            "empty_slots": empty_slots,
            "orphan_videos": [v["id"] for v in orphans],
            "compliance_issues": compliance_issues,
            "advisories": advisories,
            "disclosure_ledger_size": len(ledger),
            "total_discrepancies": total,
        }
        with open(a.json, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n>> wrote {a.json}")

    sys.exit(1 if total > 0 else 0)


if __name__ == "__main__":
    main()
