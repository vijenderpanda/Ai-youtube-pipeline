#!/usr/bin/env python3
"""capture_demo — register a REAL screen recording as a reusable demo_clip asset.

The owner's ask: "add a real recording asset where it can ask for full screen or
mobile view, light or dark mode." This is the worker side of that flow. It drives
the existing scripts/record_demo.py with a chosen VIEW (mobile 9:16 / desktop
16:9) and THEME (light / dark), uploads the resulting mp4, cuts a poster frame,
and registers a CANDIDATE `demo_clip` revision — the same lineage/versioning the
rest of the Assets board uses. Nothing is locked; the candidate simply appears in
Demo footage to be chosen deliberately.

Designed to run as an existing `shell_script` worker job (meta.script_path =
'scripts/capture_demo.py'), exactly like regen_asset.py — no new job type, no
worker restart, no `claude -p`.

  python3 scripts/capture_demo.py --channel claude-tricks \\
      --site duckai --view desktop --theme dark \\
      --prompt "Explain RAG in one line" --label "RAG one-liner (fullscreen)"

  python3 scripts/capture_demo.py --channel claude-tricks \\
      --url https://example.com --selector "textarea" --view mobile --theme light \\
      --prompt "..."

LOGIN LIMITATION
----------------
record_demo.py uses a persistent browser profile for the sites that need an
account (chatgpt / claude / gemini). The worker runs HEADLESS and cannot do the
interactive `--setup-profile` login, so a capture of one of those sites only
works if that profile was logged in beforehand on this machine
(.browser-profiles/<site>). Public sites (duckai, perplexity) and arbitrary
public --url pages need no login. This script does NOT silently paper over that:
it warns up-front when the target needs a profile, and if record_demo aborts on a
login wall it fails with that reason surfaced in the job result.
"""
import argparse, json, os, subprocess, sys, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ASSET_TYPE = "demo_clip"
RECORD_DEMO = os.path.join(REPO, "scripts", "record_demo.py")

# Sites whose recording needs a logged-in persistent profile (mirror of the
# `"profile": True` rows in record_demo.SITES). Kept here as a fallback so the
# login warning still fires even if record_demo can't be imported; the live
# import below overrides it so the two never drift.
PROFILE_SITES = {"chatgpt", "claude", "gemini"}
PROFILES_DIR = os.path.join(REPO, ".browser-profiles")


def die(msg):
    print(f"!! {msg}", file=sys.stderr)
    sys.exit(2)


def _profile_sites():
    """The set of record_demo sites that require a login profile, read from the
    source of truth when importable, else the local fallback."""
    try:
        sys.path.insert(0, os.path.join(REPO, "scripts"))
        import record_demo  # noqa: F401 — only for its SITES table
        return {k for k, v in record_demo.SITES.items() if v.get("profile")}
    except Exception:
        return set(PROFILE_SITES)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True)
    ap.add_argument("--url", default="")
    ap.add_argument("--site", default="")
    ap.add_argument("--view", choices=("mobile", "desktop"), default="mobile")
    ap.add_argument("--theme", choices=("light", "dark"), default="light")
    ap.add_argument("--prompt", default="")
    ap.add_argument("--selector", default="")
    ap.add_argument("--label", default="")
    ap.add_argument("--stamp", default="", help="override the uniqueness stamp "
                    "(default: int(time.time()), like regen_asset.py)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    url = (a.url or "").strip()
    site = (a.site or "").strip()
    prompt = (a.prompt or "").strip()
    selector = (a.selector or "").strip()

    # ── validate (mirror the edge action so a hand-run fails the same way) ──
    if not (url or site):
        die("one of --url / --site is required")
    if url and site:
        die("--url and --site are mutually exclusive (pass one)")
    if not prompt:
        die("--prompt is required — record_demo types it into the page and films "
            "the result; there is nothing to record without it")
    if url and not selector:
        # record_demo's custom-url path needs a composer selector; catch it here
        # with a clear message rather than letting record_demo exit cryptically.
        die("--selector is required with --url (the element record_demo types "
            "into); it is optional only for a known --site")

    # ── login-profile limitation: warn loudly, never silently film a wall ──
    login_note = None
    profile_sites = _profile_sites()
    if site and site in profile_sites:
        prof = os.path.join(PROFILES_DIR, site)
        have = os.path.isdir(prof)
        login_note = (
            f"site '{site}' needs a logged-in browser profile; "
            + (f"found {prof}" if have
               else f"NO profile at {prof} — this headless worker cannot log in "
                     f"(run `python3 scripts/record_demo.py --site {site} "
                     f"--setup-profile` on a desktop first). The recording will "
                     f"abort on the login wall.")
        )
        print(f">> LOGIN: {login_note}", flush=True)

    stamp = (a.stamp or "").strip() or str(int(time.time()))

    # factory_worker (DB + storage client) is imported here, AFTER validation, so
    # --help and the arg-validation errors above never require the worker env.
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    import factory_worker as fw
    env = fw.load_env()
    supa = fw.Supa(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])

    # next version for this channel's demo_clip slot (multi-slot: candidates
    # coexist as increasing versions, same as every other asset_type)
    rows = supa.select("factory_asset_versions",
                       f"channel_key=eq.{a.channel}&asset_type=eq.{ASSET_TYPE}"
                       f"&select=version&order=version.desc")
    nxt = (max((r["version"] for r in rows), default=0) + 1)

    name = f"{ASSET_TYPE}_v{nxt}_{stamp}"
    rel = f"_recordings/{name}.mp4"
    out = os.path.join(REPO, "channels", a.channel, "assets", rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)

    # ── build the record_demo command ──
    cmd = ["python3", RECORD_DEMO, "--view", a.view, "--prompt", prompt,
           "-o", out]
    if a.theme == "dark":
        cmd += ["--dark"]                 # light is record_demo's default (no flag)
    if site:
        cmd += ["--site", site]           # selector comes from record_demo.SITES
    else:
        cmd += ["--url", url, "--selector", selector]
    print(">> " + " ".join(cmd), flush=True)
    if a.dry_run:
        print(">> dry-run — recorder not executed")
        return

    # stream record_demo's output straight through so the worker log shows the
    # capture live; a non-zero exit (incl. a login-wall abort) fails the job.
    r = subprocess.run(cmd, cwd=REPO)
    if r.returncode != 0 or not os.path.exists(out):
        extra = f"\n   (login limitation: {login_note})" if login_note else ""
        die(f"record_demo failed (exit {r.returncode}) — nothing registered{extra}")

    # ── upload the mp4 ──
    store = f"{a.channel}/assets/{rel}"
    supa.upload(store, open(out, "rb").read(), "video/mp4")

    # ── poster frame (best-effort, same recipe as regen_asset.py) ──
    thumb = None
    pj = out.rsplit(".", 1)[0] + ".jpg"
    subprocess.run(["ffmpeg", "-v", "error", "-ss", "0.4", "-i", out, "-frames:v",
                    "1", "-q:v", "4", "-vf", "scale=640:-2", pj, "-y"], check=False)
    if os.path.exists(pj):
        thumb = f"{a.channel}/assets/_thumbs/{ASSET_TYPE}/{name}.jpg"
        supa.upload(thumb, open(pj, "rb").read(), "image/jpeg")

    label = a.label.strip() or f"real recording · {a.view} · {a.theme} · {site or url}"
    row = {
        "channel_key": a.channel,
        "asset_type": ASSET_TYPE,
        "version": nxt,
        "label": label,
        "storage_path": store,
        "thumb_path": thumb,
        "status": "candidate",          # never auto-locked — you choose it
        "source": "capture",
        "meta": {
            "build_ref": rel,
            "source": "capture",
            "capture_params": {
                "view": a.view,
                "theme": a.theme,
                "url": url or None,
                "site": site or None,
                "prompt": prompt,
                "selector": selector or None,
            },
            **({"login_profile_note": login_note} if login_note else {}),
        },
    }
    supa.insert("factory_asset_versions", [row],
                on_conflict="channel_key,asset_type,version",
                resolution="merge-duplicates")
    print(f">> registered {ASSET_TYPE} v{nxt} (candidate, {a.view}/{a.theme})")
    print(f">> {store}")


if __name__ == "__main__":
    main()
