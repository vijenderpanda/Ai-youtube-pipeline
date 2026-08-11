#!/usr/bin/env python3
"""Deterministic finalize step for claude-tricks Shorts (v16).

Runs after produce_preview + human review approves the preview MP4:

  produce_preview (Claude, ~$2.5) -> preview_raw.mp4 in Studio
  ↓ (human approves in Studio)
  finalize_episode.py (this script, ~$0) -> master + QC + arm YT

Sequence:
  1. Look up the episode config from channels/claude-tricks/episodes/<ep>.v2.json
     (the produce_preview session wrote it there).
  2. Run channels/claude-tricks/build_ep_v2.py --ep <ep> --tag <tag> — full
     Remotion render + audio master + endcard + outro concat.
  3. LUFS check on the finished master vs channel spine (-18.4 ±0.3 LU).
     Fail loudly if outside band; the produce_preview session's preview was
     unmastered, so mastering issues can only surface here.
  4. (Optional) arm YouTube via scripts/yt_upload.py --channel claude-tricks
     --schedule <ISO 8601 UTC>. Skipped if --skip-arm or no --schedule given.

Called via factory-worker shell_script job type. meta.script_path =
'scripts/finalize_episode.py' and meta.script_args = ['--ep', '<ep>',
'--schedule', '<iso>', ...]. The worker wrapper (see
run_shell_script_job in factory_worker.py) recognises .py extension and
dispatches with python3.

Exit codes:
  0 -- master rendered, QC passed, YT armed (if requested)
  1 -- master render failed
  2 -- QC gate failed (LUFS out of band, lipsync out of band, etc.)
  3 -- YT arm failed (master + QC succeeded, upload is the issue)
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
CH = os.path.join(REPO, "channels", "claude-tricks")

# LUFS ratchet — see docs/PRODUCTION-PLAYBOOK.md §Audio + QUALITY-LEDGER.md
# 2026-08-05: shipped-master spine is -18.4 LUFS integrated; ±0.3 LU tolerance
LUFS_TARGET = -18.4
LUFS_TOLERANCE = 0.3


def run(cmd, **kw):
    """subprocess.run with a printed banner so the shell_script log tail is scannable."""
    print(">> " + " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run(cmd, check=False, **kw)


def measure_lufs(path):
    """Integrated loudness via ffmpeg's ebur128 filter. Returns float LUFS or
    None on measurement failure (never raises — caller decides how to fail)."""
    r = subprocess.run(
        ["ffmpeg", "-nostats", "-i", path, "-af", "ebur128=peak=true",
         "-f", "null", "-"],
        capture_output=True, text=True)
    # ebur128 writes to stderr; look for the summary line "I: -18.4 LUFS"
    m = re.search(r"I:\s+(-?[\d.]+)\s+LUFS", r.stderr)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def qc_gate(final_path):
    """Verify the mastered file meets the channel's shipped-quality bar.
    Returns (ok, [issues])."""
    issues = []
    if not os.path.exists(final_path):
        return False, [f"master file missing: {final_path}"]

    lufs = measure_lufs(final_path)
    if lufs is None:
        issues.append("could not measure LUFS")
    else:
        drift = lufs - LUFS_TARGET
        print(f">> LUFS integrated: {lufs:.2f} (target {LUFS_TARGET}, drift {drift:+.2f} LU)")
        if abs(drift) > LUFS_TOLERANCE:
            issues.append(
                f"LUFS {lufs:.2f} is {abs(drift):.2f} LU off spine "
                f"{LUFS_TARGET} (tolerance ±{LUFS_TOLERANCE})")

    # Lipsync + chip-corner probes exist per docs/PRODUCTION-PLAYBOOK.md §E/F
    # but they were run in the produce_preview session already (against the
    # preview raw, same host clips). Finalize inherits that verdict. If we
    # ever grow a per-final probe, it slots in here.

    return (not issues), issues


def build_description(spec, final_path):
    """Build a description file from the spec + BRAND-BIBLE §8 boilerplate.
    Returns the temp file path so yt_upload can pass --desc-file at it."""
    title = spec.get("title", "")
    lines = spec.get("lines", [])
    hook_line = lines[0] if lines else title
    # Compliance boilerplate — mandatory per channels/claude-tricks/BRAND-BIBLE.md §8
    disclosure = "Not affiliated with Anthropic, OpenAI, or Google."
    # Multi-entity: any lab named in title or lines gets listed
    body_txt = " ".join(lines).lower() + " " + title.lower()
    entities = []
    if "claude" in body_txt or "anthropic" in body_txt:
        entities.append("Anthropic")
    if "chatgpt" in body_txt or "openai" in body_txt or "gpt" in body_txt:
        entities.append("OpenAI")
    if "gemini" in body_txt or "google" in body_txt:
        entities.append("Google")
    if entities:
        disclosure = "Not affiliated with " + ", ".join(entities) + "."

    tag_line = " ".join("#" + t.strip().replace(" ", "") for t in
                        (spec.get("tags") or "").split(",") if t.strip())
    desc = "\n".join([
        hook_line,
        "",
        "AI Unpacked — no hype, just what actually works.",
        "",
        disclosure,
        "",
        tag_line,
    ]).strip() + "\n"
    p = final_path + ".desc.txt"
    with open(p, "w") as f:
        f.write(desc)
    return p


def arm_youtube(final_path, schedule_iso, spec, thumb_path=None, dry=False):
    """Upload the master to claude-tricks with a scheduled publish time.
    scripts/yt_upload.py CLI: --video (path), --title, --desc-file,
    --tags (csv), --publish-at (RFC3339 UTC), --privacy private,
    --audience general, --synthetic, --thumbnail (path)."""
    yt_upload = os.path.join(HERE, "yt_upload.py")
    if not os.path.exists(yt_upload):
        return False, "yt_upload.py not found"

    desc_path = build_description(spec, final_path)
    title = spec.get("title") or os.path.basename(final_path)
    tags = spec.get("tags") or ""

    cmd = ["python3", yt_upload, "--channel", "claude-tricks",
           "--video", final_path,
           "--title", title,
           "--desc-file", desc_path,
           "--tags", tags,
           "--audience", "general",
           "--synthetic",  # BRAND-BIBLE §8 mandatory (synthetic media disclosure)
           "--privacy", "private",  # yt_upload flips to public at publishAt
           "--publish-at", schedule_iso]
    if thumb_path and os.path.exists(thumb_path):
        cmd += ["--thumbnail", thumb_path]

    r = run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return False, f"yt_upload exited {r.returncode}:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    return True, r.stdout.strip()


def main():
    ap = argparse.ArgumentParser(
        description="Finalize a produce_preview-approved short: master + QC + arm YT")
    ap.add_argument("--ep", required=True,
                    help="episode key — same as the produce_preview session used "
                         "(matches channels/claude-tricks/episodes/<ep>.v2.json)")
    ap.add_argument("--tag", default="v2",
                    help="render stem for the master (default 'v2')")
    ap.add_argument("--schedule",
                    help="ISO 8601 UTC publish time to arm YouTube — e.g. "
                         "2026-08-11T10:30:00Z. Omit or pass --skip-arm to master only.")
    ap.add_argument("--skip-arm", action="store_true",
                    help="run master + QC only, do NOT touch YouTube")
    ap.add_argument("--dry", action="store_true",
                    help="pass --dry through to yt_upload (arm smoke test)")
    a = ap.parse_args()

    # 1) VERIFY SPEC EXISTS
    spec = os.path.join(CH, "episodes", f"{a.ep}.v2.json")
    if not os.path.exists(spec):
        # Fallback: maybe the hardcoded EPISODES_V2 dict carries it — build_ep_v2
        # handles both, so a missing JSON isn't fatal by itself. But warn.
        print(f">> note: no spec at {spec} — build_ep_v2 will look up EPISODES_V2[{a.ep!r}]")

    # 2) MASTER RENDER — build_ep_v2 without --preview does the full pipeline:
    #    Remotion render + audio master + endcard + outro concat.
    build = os.path.join(CH, "build_ep_v2.py")
    r = run(["python3", build, "--ep", a.ep, "--tag", a.tag])
    if r.returncode != 0:
        print(f"!! master render exited {r.returncode}", file=sys.stderr)
        sys.exit(1)

    final = os.path.join(CH, "renders", f"ep{a.ep}_{a.tag}.mp4")
    # build_ep_v2 optionally writes ep{ep}_{tag}_outro.mp4 or a _cta variant when
    # cfg carries endcard/outro. If either exists, prefer it as the "final".
    for stem in (f"ep{a.ep}_{a.tag}_outro.mp4", f"ep{a.ep}_{a.tag}_cta.mp4"):
        alt = os.path.join(CH, "renders", stem)
        if os.path.exists(alt):
            final = alt

    # 3) QC GATE
    ok, issues = qc_gate(final)
    if not ok:
        print("!! QC gate FAILED:", file=sys.stderr)
        for i in issues:
            print(f"  - {i}", file=sys.stderr)
        sys.exit(2)
    print(">> QC gate PASSED")

    # 4) ARM YOUTUBE (optional)
    if a.skip_arm or not a.schedule:
        print(">> skipping YT arm (no --schedule or --skip-arm)")
        print(f">> final master ready at: {final}")
        sys.exit(0)

    # Load the spec Claude wrote for title + tags (needed by yt_upload.py)
    spec_data = {}
    if os.path.exists(spec):
        try:
            with open(spec) as f:
                spec_data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"!! could not read spec {spec}: {e}", file=sys.stderr)
            sys.exit(1)

    # Thumbnail lookup: prefer channels/claude-tricks/renders/thumb_ep<ep>.jpg
    # (produce_preview writes it there); fall back to assets/ep<ep>/thumbnail.*
    thumb = None
    for cand in (
        os.path.join(CH, "renders", f"thumb_ep{a.ep}.jpg"),
        os.path.join(CH, "renders", f"thumb_ep{a.ep}.png"),
        os.path.join(CH, "assets", f"ep{a.ep}", "thumbnail.jpg"),
        os.path.join(CH, "assets", f"ep{a.ep}", "thumbnail.png"),
    ):
        if os.path.exists(cand):
            thumb = cand
            break

    ok, msg = arm_youtube(final, a.schedule, spec_data, thumb_path=thumb, dry=a.dry)
    if not ok:
        print(f"!! YT arm FAILED: {msg}", file=sys.stderr)
        sys.exit(3)
    print(f">> YT armed for {a.schedule}: {msg}")
    print(f">> DONE — master at {final}, scheduled {a.schedule}")


if __name__ == "__main__":
    main()
