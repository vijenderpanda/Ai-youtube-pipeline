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
# 2026-08-11 (Vaibhav-DNA pass): spine moved from -18.4 -> -14.0 LUFS to match
# the reference-loudness competitor teardown (vaibhavsisinty's 360K-view Short
# MYOdDsEAMns integrates -14.4 LUFS; ours at -18.4 sounded 4dB quieter in the
# YouTube Shorts feed). Chain now applies loudnorm=I=-14 as final normalize.
# Tolerance widened to ±0.5 LU because single-pass loudnorm is less precise
# than the earlier fixed-gain chain.
LUFS_TARGET = -14.0
LUFS_TOLERANCE = 0.5


def run(cmd, **kw):
    """subprocess.run with a printed banner so the shell_script log tail is scannable."""
    print(">> " + " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run(cmd, check=False, **kw)


def measure_lufs(path):
    """Integrated loudness via ffmpeg's ebur128 filter. Returns float LUFS or
    None on measurement failure (never raises — caller decides how to fail).

    v16 fix: ebur128 emits per-frame running-loudness lines during the stream
    (e.g. 'I: -70.0 LUFS' at t=0.1s while ramping up), THEN a 'Summary:' block
    with the true integrated value at EOF. The old regex matched the first
    streaming line and reported -70 dropouts for every valid file. Match only
    inside the Summary block."""
    r = subprocess.run(
        ["ffmpeg", "-nostats", "-i", path, "-af", "ebur128=peak=true",
         "-f", "null", "-"],
        capture_output=True, text=True)
    # locate the 'Summary:' section (ebur128 writes it once, at end)
    tail = r.stderr.rsplit("Summary:", 1)[-1] if "Summary:" in r.stderr else ""
    m = re.search(r"Integrated loudness:\s*\n?\s*I:\s*(-?[\d.]+)\s+LUFS", tail)
    if not m:
        # fallback: last "I: NNN LUFS" line in the whole output
        matches = re.findall(r"I:\s*(-?[\d.]+)\s+LUFS", r.stderr)
        if not matches:
            return None
        try:
            return float(matches[-1])
        except ValueError:
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



# ---------------------------------------------------------------------------
# ARM-TIME GATE — the last thing that runs before anything touches YouTube.
#
# Every check below exists because the thing it checks ALREADY SHIPPED WRONG,
# or came within minutes of doing so. Ordered by the damage each one prevented.
# Rationale and incident notes: docs/SHORTS-METHOD-AND-APP-GATES.md §3, §7.
# ---------------------------------------------------------------------------

# Words that carry no discovery value, so they are never required to appear in
# title/tags. Deliberately small: the point is to catch a MISSING artifact noun,
# not to police copy.
_GATE_STOP = {
    "build", "me", "a", "an", "the", "app", "that", "with", "for", "and", "my",
    "in", "to", "of", "what", "it", "this", "big", "clear", "huge", "just",
    "some", "very", "really", "simple", "small",
}


def _registry_entry(ep):
    """EPISODES_V2[ep] read by AST — never import build_ep_v2, it has side effects."""
    import ast
    src = os.path.join(CH, "build_ep_v2.py")
    if not os.path.exists(src):
        return None
    try:
        tree = ast.parse(open(src).read())
    except Exception:
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                getattr(t, "id", None) == "EPISODES_V2" for t in node.targets):
            for k, v in zip(node.value.keys, node.value.values):
                if getattr(k, "value", None) == ep:
                    try:
                        return ast.literal_eval(v)
                    except Exception:
                        return None
    return None


def _capture_prompt(ep):
    """The prompt REALLY typed on camera, from this episode's capture script.

    Convention: rec_<key>_app.py, where key is the episode key without its
    leading underscore (_game -> rec_game_app.py)."""
    import ast
    cand = os.path.join(CH, f"rec_{ep.lstrip('_')}_app.py")
    if not os.path.exists(cand):
        return None
    try:
        tree = ast.parse(open(cand).read())
    except Exception:
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                getattr(t, "id", None) == "PROMPT" for t in node.targets):
            try:
                return ast.literal_eval(node.value)
            except Exception:
                return None
    return None


def _artifact_nouns(prompt):
    """The words that NAME the thing that was built.

    Takes the noun phrase after "build me a/an/the", stopping at the first
    clause break, so "Build me a reaction time game that fills the whole
    screen..." yields {reaction, time, game} and not the whole spec."""
    import re
    m = re.search(r"\bbuild me (?:a|an|the)\s+(.+)", prompt or "", re.I)
    if not m:
        return []
    phrase = re.split(r"\s+-\s+|,|\.|\bthat\b", m.group(1), 1)[0]
    return sorted({w for w in re.findall(r"[a-z]+", phrase.lower())
                   if len(w) > 2 and w not in _GATE_STOP})


def _spoken_text(ep):
    """What the rendered voice track actually SAYS, normalised for comparison."""
    import re
    wp = os.path.join(CH, "assets", f"ep{ep}", "vo_v2.words.json")
    if not os.path.exists(wp):
        return None
    try:
        words = json.load(open(wp))
    except Exception:
        return None
    said = " ".join(w.get("w", "") for w in words
                    if not w.get("w", "").lower().startswith(("<break", "time=", "/")))
    return re.sub(r"[^a-z0-9]", "", said.lower())


def arm_gate(ep, spec_path, spec, thumb_path):
    """Hard pre-flight. Returns (issues, warnings); a non-empty issues list
    must abort before upload."""
    import re
    issues, warns = [], []

    # 1) THE MIRROR MUST EXIST. Tip #2 went live to real subscribers titled
    #    "ep_habit_v2_outro.mp4" because this file did not exist and finalize
    #    fell back to the filename.
    if not os.path.exists(spec_path):
        issues.append(f"metadata mirror missing: {spec_path} — finalize would "
                      f"title the video after the FILE (this already happened once)")
        return issues, warns
    for field in ("title", "tags", "lines"):
        if not spec.get(field):
            issues.append(f"mirror {os.path.basename(spec_path)} has no {field!r}")

    title = spec.get("title") or ""
    tags = spec.get("tags") or ""

    # 2) MIRROR MUST MATCH THE REGISTRY. build_ep_v2 renders from EPISODES_V2;
    #    finalize publishes from the mirror. When they drift, the video and its
    #    metadata describe different things. Drifted within MINUTES of an edit
    #    on _wheel (tags) — this is not a theoretical failure.
    reg = _registry_entry(ep)
    if reg is None:
        warns.append(f"no EPISODES_V2[{ep!r}] to cross-check the mirror against")
    else:
        for field in ("title", "tags", "lines"):
            if field in reg and reg[field] != spec.get(field):
                issues.append(
                    f"{field} DIVERGES between EPISODES_V2[{ep!r}] and the mirror\n"
                    f"       registry: {reg[field]!r}\n"
                    f"       mirror  : {spec.get(field)!r}")

    # 3) TITLE SANITY — a filename is never a title.
    if title.lower().endswith((".mp4", ".mov", ".json")) or re.match(r"^ep[_0-9]", title):
        issues.append(f"title looks like a filename, not a title: {title!r}")
    if len(title) > YT_TITLE_MAX:
        issues.append(f"title is {len(title)} chars, over YouTube's {YT_TITLE_MAX}")

    # 4) THE ARTIFACT'S OWN NOUNS MUST BE DISCOVERABLE. On _game the thing built
    #    was a GAME, the title said "Reaction Test", and "game" appeared only in
    #    the voiceover — i.e. nowhere the algorithm reads. A human caught that;
    #    nothing automated did. This is that check.
    prompt = _capture_prompt(ep)
    if prompt:
        nouns = _artifact_nouns(prompt)
        hay = (title + " " + tags).lower()
        missing = [w for w in nouns if w not in hay]
        if missing:
            issues.append(
                f"the prompt built {nouns} but {missing} appear in NEITHER title "
                f"nor tags — unsearchable\n       prompt: {prompt[:90]}...")
    else:
        warns.append(f"no rec_{ep.lstrip('_')}_app.py — skipped the keyword check")

    # 5) THUMBNAIL. This channel's CTR advantage (4.6% vs a 0.76% ceiling) rides
    #    on the thumbnail; _game would have armed without one.
    if not thumb_path:
        issues.append(f"no thumbnail found (renders/thumb_ep{ep}.jpg) — this "
                      f"channel's CTR depends on it")

    # 6) THE VOICE MUST MATCH THE PUBLISHED SCRIPT. The VO used to be cached on
    #    file existence, so an edited script shipped stale audio: a master went
    #    out showing 269ms while the voice said "two hundred and thirty one".
    said = _spoken_text(ep)
    if said is None:
        warns.append("no vo_v2.words.json — could not verify the voice matches the script")
    else:
        for i, line in enumerate(spec.get("lines") or []):
            norm = re.sub(r"[^a-z0-9]", "", line.lower())
            if norm and norm not in said:
                issues.append(
                    f"line {i} in the mirror is NOT what the voice track says — "
                    f"stale VO or edited metadata\n       mirror: {line!r}")
                break

    # 7) DESCRIPTION must render and carry the compliance line.
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            desc = open(build_description(spec, os.path.join(td, "probe"))).read()
        if "Not affiliated" not in desc:
            issues.append("description is missing the required disclosure line")
    except Exception as e:
        issues.append(f"description failed to build: {e!r}")

    return issues, warns


# Series-follow numbering (VJ pick 2026-08-13): the YouTube title carries a
# "30 Claude tricks in 30 days" challenge suffix so every audition viewer sees
# there's a next episode to follow. The Vaibhav-DNA hook grammar stays LOCKED
# and FIRST — the suffix rides at the END, and if the combined title would
# blow YouTube's 100-char cap the SUFFIX is dropped, never the hook truncated.
# Day count == ep counter (Ep13 = Day 13/30; one counter, no drift). After the
# challenge window the suffix falls back to plain series numbering
# ("| Claude Tricks #31") so the series cue never disappears.
CHALLENGE_LEN = 30
YT_TITLE_MAX = 100


def apply_series_suffix(title, ep, spec=None):
    """Append the series suffix to a locked hook title. Idempotent (safe on
    finalize re-runs); no-op for unknown ep keys or when the cap bites.

    Build Club (Fridays, VJ 2026-08-13): a spec carrying series == "build-club"
    gets " — Build Club Ch. <chapter>" instead of the Day-counter suffix. The
    chapter number lives IN the spec (chapters are content-ordered and can't
    shuffle at arm time the way dailies do), and Build Club ep keys are
    non-numeric ("bc01"), so the Day/30 counter never sees Fridays — no skip
    logic, no drift."""
    if not title:
        return title
    if re.search(r"(Day \d+/\d+|Claude Tricks #\d+|Build Club Ch\. \d+)\s*$", title):
        return title
    if (spec or {}).get("series") == "build-club":
        ch = (spec or {}).get("chapter")
        if not str(ch).isdigit():
            return title
        suffix = f" — Build Club Ch. {int(ch)}"
    elif str(ep).isdigit():
        n = int(ep)
        suffix = (f" — Day {n}/{CHALLENGE_LEN}" if n <= CHALLENGE_LEN
                  else f" | Claude Tricks #{n}")
    else:
        return title
    if len(title) + len(suffix) > YT_TITLE_MAX:
        print(f">> series suffix dropped: title + suffix exceeds {YT_TITLE_MAX} chars")
        return title
    return title + suffix


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
    # Series promise — every viewer must see there's a next episode to follow
    # (VJ directive 2026-08-13; series-follow pass). Build Club specs carry
    # the Friday promise + the week's homework instead of the daily line.
    if spec.get("series") == "build-club":
        promise = ["Build Club — one real build move, every Friday. "
                   "By Chapter 6 you've shipped a real app."]
        # §0 NORTH STAR (BUILD-CLUB.md): dreamer-intent SEO copy + the gift
        # link ride in the description, both authored per-chapter in the spec.
        if spec.get("seo_line"):
            promise.append(spec["seo_line"])
        hw = (spec.get("homework") or "").strip()
        if hw:
            promise.append("This week's homework: " + hw)
        if spec.get("gift_line"):
            promise.append(spec["gift_line"])
    else:
        promise = ["One 30-second Claude trick, every day."]

    # Optional per-episode ask, placed directly under the hook line where it is
    # visible without expanding the description. Opt-in: episodes that do not set
    # `desc_cta` render exactly as before, so this changes no existing episode.
    # Added 2026-08-20 — YouTube analytics on tip #2 flagged zero likes and zero
    # viewer comments on 221 views and recommended asking a specific question, and
    # the ask existed only in the picture, not in any indexed text.
    ask = [spec["desc_cta"], ""] if spec.get("desc_cta") else []

    desc = "\n".join([
        hook_line,
        "",
        *ask,
        *promise,
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
        return False, f"yt_upload exited {r.returncode}:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}", None
    # yt_upload.py prints ">> UPLOADED: https://youtu.be/<id>" (or a recovery-mode
    # line with the same shape). Pull the 11-char video id back so the factory DB
    # sync can record the real scheduled post.
    m = re.search(r"youtu\.be/([A-Za-z0-9_-]{6,})", r.stdout or "")
    video_id = m.group(1) if m else None
    return True, r.stdout.strip(), video_id


def sync_factory_db(calendar_id, video_id, schedule_iso, spec, final_path, desc_path=None):
    """v16 gap-4 fix: finalize arms YouTube DIRECTLY (via yt_upload.py), so the
    factory app never saw a factory_posts row for it — Ep11 needed a manual
    Supa.insert. This writes that row automatically: a factory_posts row already
    at status='scheduled' (real video_id + publish_at), and flips the linked
    factory_calendar item to 'produced'. The worker's publisher only ever touches
    status='armed' rows, so a 'scheduled' row is never re-uploaded; it flips to
    'published' lazily once publish_at passes. Best-effort: the video is already
    armed on YouTube, so a DB hiccup here must NOT fail the job — it prints a
    loud WARNING with the manual fallback and returns False."""
    try:
        sys.path.insert(0, HERE)
        from factory_worker import Supa, load_env  # noqa: E402
        env = load_env()
        supa = Supa(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
    except Exception as e:  # noqa: BLE001
        print(f">> WARNING: factory DB sync skipped (could not init Supa): {e}")
        return False

    tags = [t.strip() for t in (spec.get("tags") or "").split(",") if t.strip()]
    yt_desc = ""
    if desc_path and os.path.exists(desc_path):
        try:
            with open(desc_path) as f:
                yt_desc = f.read().strip()
        except OSError:
            pass
    row = {
        "channel_key": "claude-tricks",
        "local_path": final_path,
        "yt_title": (spec.get("title") or os.path.basename(final_path))[:100],
        "yt_description": yt_desc,
        "tags": tags,
        "audience": "general",
        "synthetic": True,           # BRAND-BIBLE §8 synthetic-media disclosure
        "publish_at": schedule_iso,
        "video_id": video_id,
        "status": "scheduled",       # already live on YouTube's schedule
        # Phase 3 backlink: without this, calendar_id -> post -> video_id is
        # unwalkable in SQL, which breaks the asset -> "shipped in N episodes"
        # chain (and the retention payoff that rides on it).
        "calendar_id": calendar_id,
    }
    ok = True
    try:
        supa.insert("factory_posts", [row])
        print(f">> factory DB: factory_posts row inserted (scheduled, video {video_id})")
    except Exception as e:  # noqa: BLE001
        ok = False
        print(f">> WARNING: could not insert factory_posts row: {e}")
        print(f">> MANUAL FALLBACK: insert a factory_posts row (status=scheduled, "
              f"video_id={video_id}, publish_at={schedule_iso}) yourself.")
    if calendar_id:
        try:
            supa.patch("factory_calendar", f"id=eq.{calendar_id}",
                       {"status": "produced"})
            print(f">> factory DB: calendar item {calendar_id} -> produced")
        except Exception as e:  # noqa: BLE001
            ok = False
            print(f">> WARNING: could not flip calendar {calendar_id} to produced: {e}")
    try:
        supa.insert("factory_events", [{
            "kind": "post_scheduled",
            "message": f"finalize armed claude-tricks: {row['yt_title']!r} "
                       f"(video {video_id}, publish {schedule_iso})",
            "meta": {"calendar_id": calendar_id, "video_id": video_id,
                     "channel_key": "claude-tricks", "source": "finalize_episode.py"},
        }])
    except Exception:  # noqa: BLE001
        pass
    return ok


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
    ap.add_argument("--force-arm", action="store_true",
                    help="publish even if the arm-time gate finds problems. Every gate "
                         "check exists because that exact thing already shipped wrong — "
                         "read the failures before reaching for this.")
    ap.add_argument("--calendar-id",
                    help="factory_calendar item id — when given (and the arm "
                         "succeeds), a scheduled factory_posts row is inserted and "
                         "the calendar item is flipped to 'produced' so the app "
                         "reflects the arm without a manual DB write (v16 gap-4).")
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
    # --calendar-id rides through so an outro_cta spec can EXCLUDE this episode's
    # own calendar row from its next-episode tease lookup (outro_cta.py).
    r = run(["python3", build, "--ep", a.ep, "--tag", a.tag]
            + (["--calendar-id", a.calendar_id] if a.calendar_id else []))
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

    # Series-follow suffix — mutate the spec title HERE so arm_youtube and
    # sync_factory_db both ship the identical suffixed title.
    if spec_data.get("title"):
        suffixed = apply_series_suffix(spec_data["title"], a.ep, spec=spec_data)
        if suffixed != spec_data["title"]:
            print(f">> series title: {suffixed!r}")
            spec_data["title"] = suffixed

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

    # ---- ARM-TIME GATE: last stop before YouTube ----
    gate_issues, gate_warns = arm_gate(a.ep, spec, spec_data, thumb)
    for w in gate_warns:
        print(f"!! gate warning: {w}")
    if gate_issues:
        print("\n!! ARM GATE FAILED — nothing has been uploaded:", file=sys.stderr)
        for i in gate_issues:
            print(f"  - {i}", file=sys.stderr)
        if not a.force_arm:
            print("\n   Fix these, or re-run with --force-arm if you are certain.",
                  file=sys.stderr)
            sys.exit(3)
        print("\n!! --force-arm given: publishing DESPITE the failures above.",
              file=sys.stderr)
    else:
        print(">> arm gate PASSED")

    ok, msg, video_id = arm_youtube(final, a.schedule, spec_data, thumb_path=thumb, dry=a.dry)
    if not ok:
        print(f"!! YT arm FAILED: {msg}", file=sys.stderr)
        sys.exit(3)
    print(f">> YT armed for {a.schedule}: {msg}")

    # v16 gap-4: record the arm in the factory DB so the app reflects it (no more
    # manual Supa.insert). Skipped on --dry (no real upload → no real video_id).
    if a.calendar_id and not a.dry:
        if video_id:
            sync_factory_db(a.calendar_id, video_id, a.schedule, spec_data, final,
                            desc_path=final + ".desc.txt")
        else:
            print(">> WARNING: armed but could not parse a video_id from yt_upload "
                  "output — factory DB not synced. Check the post manually.")

    # v17: advance the channel ep counter so the next channel-page produce
    # auto-assigns ep+1 (sequential; the number is confirmed only here, at arm).
    if not a.dry and str(a.ep).isdigit():
        try:
            sys.path.insert(0, HERE)
            from factory_worker import Supa, load_env  # noqa: E402
            env = load_env(); supa = Supa(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
            cur = supa.select("factory_settings", "key=eq.claude-tricks_last_ep&select=value")
            curn = int(cur[0]["value"]) if cur and str(cur[0].get("value") or "").isdigit() else 0
            if int(a.ep) > curn:
                supa.insert("factory_settings",
                            [{"key": "claude-tricks_last_ep", "value": str(int(a.ep))}],
                            on_conflict="key", resolution="merge-duplicates")
                print(f">> ep counter -> claude-tricks_last_ep={int(a.ep)}")
        except Exception as e:  # noqa: BLE001
            print(f">> WARNING: could not advance ep counter: {e}")

    print(f">> DONE — master at {final}, scheduled {a.schedule}"
          + (f", video {video_id}" if video_id else ""))


if __name__ == "__main__":
    main()
