#!/usr/bin/env python3
"""Factory worker daemon: claims dashboard jobs from Supabase and runs them with Claude Code.

Architecture: dashboard -> Supabase queue (factory_jobs) -> THIS WORKER -> `claude -p`
on this machine (owner's Claude Code subscription does all reasoning; no Anthropic
API key anywhere). Results (manifest files) are uploaded to the public
`factory-renders` storage bucket and registered in factory_renders.

v2 additions: model mapping (fable -> claude-fable-5), per-job `ultracode` flag
(prepends the literal keyword 'ultracode' as the prompt's first line), native
`analytics_sync` jobs (network_stats.py -> history.csv -> factory_stats upsert ->
auto follow-up `analyze_and_suggest` job), `analyze_and_suggest` claude jobs whose
suggestions land in factory_calendar (status 'suggested'), and calendar items
flipping to 'produced' when their queued job finishes.

v4 additions:
- `suggest_brief` claude jobs: worker dumps a per-channel context file
  (guidelines + 14d stats + last 10 job titles + 14d calendar), claude researches
  the niche (WebSearch) and writes renders_out/brief_<JOBID>.json
  {title, brief, tags}; the JSON becomes job.result (no manifest, no renders).
- Production manifests may carry per-file yt_title/yt_description/yt_tags and
  contributors [{generator, role}]. After upload the worker stores
  factory_renders.local_path, credits factory_render_contributors, and creates a
  DRAFT factory_posts row per video (audience/synthetic from UPLOAD_DEFAULTS).
- Publisher: every poll cycle, ARMED posts (and only armed posts) are uploaded via
  scripts/yt_upload.py (scheduled at publish_at); success -> 'scheduled'+video_id,
  failure -> 'failed'+error; 'scheduled' flips to 'published' lazily once
  publish_at passes.
- analyze_and_suggest v2 prompt: real web research, optional kind='factory'
  improvement suggestions (calendar kind='factory', type custom), and per-channel
  insights that land in factory_insights.
- Daily auto-sync: once local time (factory_settings auto_sync_tz) passes
  auto_sync_hour, an analytics_sync job (model fable) is queued, guarded by an
  'auto_sync' event so it fires at most once per day.

v5 additions:
- analytics_sync ALSO pulls PER-VIDEO daily metrics into factory_video_stats:
  preferred source is YouTube Analytics API v2 (dimensions=video,day + a
  multi-value video filter, last 30 days, per-channel OAuth token). If a token
  lacks an analytics-capable scope (real call 403s), the channel falls back to
  Data API videos.list lifetime totals turned into daily deltas vs the previous
  stored day (source='data_api_fallback') and the job result names the channels
  needing a one-time re-auth (the worker NEVER starts an OAuth flow itself).
- dump_analysis_context gains a 'video_summary' section (top/bottom 3 videos per
  channel by 30d views + weighted avg_view_pct) so suggestions cite per-video
  evidence.

v6 additions:
- Job recaps: every manifest-writing claude job is asked to include a "recap"
  object in its manifest (headline/steps/decisions/issues/outputs/next --
  written by the producing run itself, honest and specific). On success the
  recap is copied into factory_jobs.result.recap; if the manifest lacks one,
  and ALWAYS on job FAILURE, the worker synthesizes a recap from the log tail
  (+ error) with a quick `claude -p --model haiku --effort low` call. Recaps
  are strictly parsed but always best-effort: a job never fails over a recap.
  suggest_brief and analytics_sync jobs skip recaps (results already structured).

v6 challenge additions:
- CHALLENGE PASS: RETIRED 2026-08-20 by owner decision. The strategist used to
  re-audit upcoming items and write a CHALLENGER row (replaces_id + why_not)
  proposing to replace one. The prompt no longer asks for it and
  challenger_row() refuses any that still arrives. The replaces_id/why_not
  columns and the two edge actions remain so historical rows stay resolvable.
- analytics_sync upserts factory_settings.last_sync_at (ISO) after a successful
  sync -- powers the dashboard's "last ran" display.

v7 additions (job control):
- factory_jobs gains control (text, 'stop' = user requested termination) and
  heartbeat_at (timestamptz). While a claude child runs, the ~4s loop bumps
  heartbeat_at and reads control back; control='stop' -> SIGTERM the child's
  WHOLE process group (children start with start_new_session=True, so ffmpeg/
  Bash grandchildren die too), 5s grace, then SIGKILL -> job status 'cancelled'
  (error 'stopped by user'), control cleared, event 'job_stopped', and the
  job's calendar item (if any) returns to its pre-queue status ('suggested'
  when origin is ai_suggestion, else 'planned') with job_id cleared.
- Orphan reap: on startup any 'running' job cannot be ours (single-instance
  worker just started) -> failed with 'orphaned: worker restarted mid-job',
  best-effort haiku recap from its stored logs, calendar reset as above, event
  'orphan_reaped'. Mid-loop (defensive): running jobs whose heartbeat_at is
  older than 3 minutes and that are not the job this worker just handled are
  reaped the same way (legacy rows with heartbeat_at null are skipped).

v9 additions (staged production -- docs/STAGED-PIPELINE.md):
- plan_assets claude jobs: brief + channel guidelines + playbook -> the run writes
  renders_out/assets_plan_<JOBID>.json; the worker ingests it into factory_assets
  rows (version 1, status 'queued') plus one generate_asset job per asset
  (idempotent: skipped when assets already exist for the calendar item).
- generate_asset claude jobs: prompt built at run time from the factory_assets row
  (spec.prompt/params + ALL revision notes + reviewer feedback verbatim); exactly
  ONE primary file (+ poster jpg for videos) under renders_out/staged/..., declared
  in asset_out_<JOBID>.json; the worker uploads to <channel>/assets/... and flips
  the asset row to 'review'. Claim flips it to 'generating'; failure/stop/orphan
  flips it to 'failed' (revise = retry).
- assemble_episode claude jobs: worker dumps staged_ctx_<JOBID>.json (item +
  channel + approved latest-version assets with local paths), claude assembles the
  final video from those local files and writes the standard v4 manifest; the
  normal upload/draft-post flow runs, then the calendar item (meta.calendar_id)
  flips to 'produced'. mark_calendar_produced never fires for plan_assets /
  generate_asset (calendar.job_id points at the plan job).

Usage:
  python3 scripts/factory_worker.py            # daemon loop (launchd runs this)
  python3 scripts/factory_worker.py --once     # single claim attempt, then exit
  python3 scripts/factory_worker.py --dry-run  # print the exact claude command for a fake job, execute nothing

Config: secrets/factory.env needs SUPABASE_URL and SUPABASE_SERVICE_KEY (service role).
See docs/FACTORY.md.
"""

import argparse
import ast
import csv
import json
import mimetypes
import os
import platform
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("FATAL: python 'requests' package missing. Install with: python3 -m pip install requests")

# ---------------------------------------------------------------- constants

REPO = Path(os.environ.get("FACTORY_REPO", "")).expanduser() if os.environ.get("FACTORY_REPO") else Path(__file__).resolve().parent.parent
ENV_FILE = REPO / "secrets" / "factory.env"
PLAYBOOK = REPO / "docs" / "PRODUCTION-PLAYBOOK.md"
RENDERS_OUT = REPO / "renders_out"
LOGS_DIR = REPO / "logs"
SCRIPTS_DIR = REPO / "scripts"

DEFAULT_SUPABASE_URL = "https://xfqyovimnqdghiekicqr.supabase.co"
BUCKET = "factory-renders"

# Cross-platform child-process grouping so a stop/timeout can kill the WHOLE job
# tree (claude + ffmpeg/Bash grandchildren). POSIX: new session -> own pgid, use
# killpg. Windows: new process group, use `taskkill /T` to kill the tree.
IS_WINDOWS = os.name == "nt"
_POPEN_GROUP_KW = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
                   if IS_WINDOWS else {"start_new_session": True})

POLL_SLEEP_S = 10
LOG_FLUSH_S = 4  # also the v7 heartbeat_at + control-check cadence while a child runs
STALE_REAP_S = 180  # v7: 'running' jobs with a heartbeat older than this are orphans
# v11: parallel job execution. Light jobs (claude/API-bound: asset generation,
# planning, briefs) run concurrently up to MAX_PARALLEL_JOBS; HEAVY jobs
# (cpu-bound ffmpeg assembly / full-pipeline renders) never overlap each other
# -- while one runs, the claim RPC (factory_claim_job_v2) excludes their types.
# Override the cap with FACTORY_MAX_PARALLEL in secrets/factory.env.
MAX_PARALLEL_JOBS = 3
HEAVY_TYPES = ("assemble_episode", "produce_short", "preview_episode")

# v14: multi-worker. Each machine registers itself in factory_workers, heartbeats
# last_seen, and reads its routing config (paused + accept_types) back from its
# row every poll -- so the dashboard can pause a worker or change which job types
# it pulls WITHOUT a restart. Claims go through factory_claim_job_v3, which routes
# by accept_types (allow-list; empty=all) and per-job target_worker pins.
WORKER_ID = (os.environ.get("FACTORY_WORKER_ID") or socket.gethostname() or "worker").strip()
WORKER_NAME = (os.environ.get("FACTORY_WORKER_NAME") or socket.gethostname() or WORKER_ID).strip()
WORKER_HEARTBEAT_S = 20  # how often to bump factory_workers.last_seen + reload routing
LOG_PUSH_MAX = 30  # max log lines to push per heartbeat (newest first)
# v17: usage rollup surfaced in factory_workers.meta.usage (dashboard Workers page).
# The Claude subscription's rolling-limit % is NOT exposed by the CLI in any
# non-interactive form (/usage is interactive-only; there's no `claude usage`
# subcommand/flag/cache), so "usage limit" here is the actionable proxy: real
# spend + token totals the CLI reports per run (factory_jobs.result.usage),
# summed over the subscription's rolling window, plus a rate_limited tripwire.
USAGE_WINDOW_H = 5  # Claude subscription rolling window; report spend/tokens within it
USAGE_REFRESH_S = 120  # throttle the factory_jobs rollup query (meta still writes every HB)
# v18: machine resource-health (GPU/CPU/RAM/disk) surfaced in factory_workers.meta
# .resources (dashboard Machines page). Best-effort + throttled: nvidia-smi is
# spawned at most once per RESOURCES_REFRESH_S even though meta writes every HB.
RESOURCES_REFRESH_S = 15  # throttle the resource-health snapshot (esp. nvidia-smi)
STOP_GRACE_S = 5  # v7: SIGTERM -> this many seconds -> SIGKILL (whole process group)
LOG_CAP_BYTES = 200_000
JOB_TIMEOUT_S = 45 * 60
STATS_TIMEOUT_S = 15 * 60  # network_stats.py refresh cap inside analytics_sync
PUBLISH_TIMEOUT_S = 30 * 60  # v4: yt_upload.py cap per armed post
AUTO_SYNC_CHECK_S = 300  # v4: re-check the auto-sync clock at most every 5 min

ALLOWED_TOOLS = "Bash Edit Write Read Glob Grep WebFetch WebSearch Skill mcp__claude-in-chrome"  # last entry allows all Chrome-extension tools

# v2: dashboard model names -> claude CLI model ids (anything else passes through)
MODEL_MAP = {"fable": "claude-fable-5"}

# v6: job recaps -- structured "what actually happened" stored in result.recap.
# The schema string is shared verbatim by the manifest instruction (the producing
# run writes its own recap) and the haiku fallback summarizer prompt.
RECAP_SCHEMA = (
    '{"headline": str (one sentence: what happened), '
    '"steps": [str, ...] (short past-tense bullets, max 8), '
    '"decisions": [str, ...] (key choice + why, max 4), '
    '"issues": [str, ...] (problem hit + how resolved/worked around, max 4, may be empty), '
    '"outputs": [{"filename": str, "kind": str, "note": str (one phrase, e.g. '
    '"28s vertical, hook at 0:00")}], '
    '"next": [str, ...] (suggested follow-up, max 2, may be empty)}'
)
RECAP_SKIP_TYPES = ("suggest_brief", "analytics_sync", "plan_assets", "generate_asset",
                    "preview_episode", "plan_content", "channel_intake")  # results already structured
RECAP_TIMEOUT_S = 180  # haiku fallback summarizer cap; recap is always best-effort
RECAP_LOG_TAIL_CHARS = 6000  # ~6KB of log tail fed to the summarizer

# staged production (docs/STAGED-PIPELINE.md): asset taxonomy shared by the
# plan_assets prompt and the plan ingest validation
ASSET_GROUPS = ("thumbnail", "scene", "clip", "audio", "bookend", "overlay", "other")
ASSET_KINDS = ("image", "video", "audio", "text", "other")

# v2: analytics ground truth written by scripts/network_stats.py
HISTORY_CSV = REPO / "docs" / "stats" / "history.csv"

# v4: per-channel YouTube upload defaults (from the verified contributors/tags
# catalog). token_file lives in secrets/; audience 'kids' -> `--audience kids`
# (COPPA), anything else -> `--audience general`; synthetic -> `--synthetic`
# (AI-content disclosure, REQUIRED for the photoreal-host channels).
UPLOAD_DEFAULTS = {
    "lulla":         {"audience": "kids",       "synthetic": False, "token_file": "token.json"},
    "language-abc":  {"audience": "kids",       "synthetic": False, "token_file": "token_poly.json"},
    "vehicles":      {"audience": "kids",       "synthetic": False, "token_file": "token_vehicles.json"},
    "claude-tricks": {"audience": "notForKids", "synthetic": True,  "token_file": "token_claude-tricks.json"},
    "aashiqana":     {"audience": "notForKids", "synthetic": True,  "token_file": "token_aashiqana.json"},
    "already-happening": {"audience": "notForKids", "synthetic": True,  "token_file": "token_already-happening.json"},
    # calm-ai: incubating (scaffolded 2026-08-12). token_calm-ai.json does NOT exist
    # yet — a human OAuth step, see channels/calm-ai/NEEDS-ATTENTION.md.
    "calm-ai":       {"audience": "notForKids", "synthetic": True,  "token_file": "token_calm-ai.json"},
}

# v2: history.csv stores DISPLAY channel names; map (case-insensitive substring)
# to factory channel keys. Unmatched names are logged, never guessed.
DISPLAY_MAP = [
    (("lulla", "moonlit"), "lulla"),
    (("ai unpacked",), "claude-tricks"),
    (("rumble", "truck", "vehicle"), "vehicles"),
    (("aashiqana",), "aashiqana"),
    (("language", "abc", "poly"), "language-abc"),
    (("already happening",), "already-happening"),
    (("calm ai",), "calm-ai"),
]

MISSING_KEY_MSG = f"""
FATAL: SUPABASE_SERVICE_KEY is not set in {ENV_FILE}

The worker cannot talk to Supabase without the service-role key.
One manual step to fix it:
  1. Open the Supabase dashboard -> project xfqyovimnqdghiekicqr -> Settings -> API keys
  2. Copy the 'service_role' secret key
  3. Add this line to {ENV_FILE}:
       SUPABASE_SERVICE_KEY=<paste the key here>
Then re-run: python3 scripts/factory_worker.py --once
"""

# Channels seeded on start (idempotent; dashboard edits are never overwritten).
# `match` is the key used in docs/PRODUCTION-PLAYBOOK.md section 14's table.
CHANNEL_SEED = [
    {"key": "lulla", "name": "Pip's Moonlit Garden (Lulla)",
     "niche": "calm bedtime songs for toddlers", "accent": "periwinkle",
     "match": "pip-moonlit-garden"},
    {"key": "claude-tricks", "name": "AI Unpacked",
     "niche": "AI tips + news Shorts for general beginners", "accent": "#E0218A",
     "match": "claude-tricks"},
    {"key": "vehicles", "name": "Rumble Trucks",
     "niche": "hyper-active kids vehicle songs", "accent": "",
     "match": "vehicles"},
    {"key": "aashiqana", "name": "Aashiqana",
     "niche": "original AI Hindi romantic songs", "accent": "",
     "match": "aashiqana"},
    {"key": "language-abc", "name": "Poly",
     "niche": "multilingual early-learning", "accent": "teal",
     "match": "language-abc"},
    {"key": "already-happening", "name": "Already Happening",
     "niche": "cinematic near-future AI Shorts grounded in what's real today", "accent": "#22D3EE",
     "match": "already-happening"},
    # calm-ai — scaffolded on disk 2026-08-12, but its factory_channels row (and the
    # scaffold job itself) were DELETED from Supabase mid-scaffold. CHANNEL_SEED runs on
    # every worker start, so leaving this active would silently resurrect a channel that
    # may have been removed on purpose. Uncomment when VJ confirms the channel is wanted
    # — see channels/calm-ai/NEEDS-ATTENTION.md item 0.
    # {"key": "calm-ai", "name": "Calm AI",
    #  "niche": "de-escalated AI news for busy adults — what it actually means for your week",
    #  "accent": "#6366F1", "match": "calm-ai"},
]

# ---------------------------------------------------------------- env / config


def load_env(require_service_key=True):
    """Parse secrets/factory.env (KEY=VALUE lines). Exit clearly if the service key is missing."""
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    env.setdefault("SUPABASE_URL", DEFAULT_SUPABASE_URL)
    if require_service_key and not env.get("SUPABASE_SERVICE_KEY"):
        sys.exit(MISSING_KEY_MSG)
    return env


class Supa:
    """Minimal PostgREST + Storage client over plain HTTP (no supabase-py)."""

    def __init__(self, url, service_key):
        self.url = url.rstrip("/")
        self.headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
        }

    def _check(self, r):
        if r.status_code >= 300:
            raise RuntimeError(f"Supabase HTTP {r.status_code} {r.request.method} {r.request.url}: {r.text[:500]}")
        return r

    def rpc(self, fn, payload=None):
        r = requests.post(f"{self.url}/rest/v1/rpc/{fn}", headers={**self.headers, "Content-Type": "application/json"},
                          json=payload or {}, timeout=(10, 60))
        self._check(r)
        return r.json() if r.text.strip() else None

    def select(self, table, query):
        r = requests.get(f"{self.url}/rest/v1/{table}?{query}", headers=self.headers, timeout=(10, 60))
        self._check(r)
        return r.json()

    def insert(self, table, rows, on_conflict=None, resolution=None):
        params = f"?on_conflict={on_conflict}" if on_conflict else ""
        prefer = "return=minimal"
        if resolution:
            prefer = f"resolution={resolution},return=minimal"
        r = requests.post(f"{self.url}/rest/v1/{table}{params}",
                          headers={**self.headers, "Content-Type": "application/json", "Prefer": prefer},
                          json=rows, timeout=(10, 60))
        self._check(r)

    def insert_returning(self, table, rows):
        """INSERT and return the created rows (needed when we must know a generated id)."""
        r = requests.post(f"{self.url}/rest/v1/{table}",
                          headers={**self.headers, "Content-Type": "application/json",
                                   "Prefer": "return=representation"},
                          json=rows, timeout=(10, 60))
        self._check(r)
        return r.json()

    def patch(self, table, query, payload):
        r = requests.patch(f"{self.url}/rest/v1/{table}?{query}",
                           headers={**self.headers, "Content-Type": "application/json", "Prefer": "return=minimal"},
                           json=payload, timeout=(10, 60))
        self._check(r)

    def patch_returning(self, table, query, payload, select="*"):
        """PATCH and return the updated rows (v7: one round-trip for
        heartbeat-write + control-read)."""
        r = requests.patch(f"{self.url}/rest/v1/{table}?{query}&select={select}",
                           headers={**self.headers, "Content-Type": "application/json",
                                    "Prefer": "return=representation"},
                           json=payload, timeout=(10, 60))
        self._check(r)
        return r.json()

    def upload(self, storage_path, data, content_type):
        r = requests.post(f"{self.url}/storage/v1/object/{BUCKET}/{storage_path}",
                          headers={**self.headers, "Content-Type": content_type, "x-upsert": "true"},
                          data=data, timeout=(10, 600))
        self._check(r)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# v15: thread-safe ring buffer that collects log lines for push to Supabase
# during each heartbeat cycle. The dashboard Workers page shows these.
_log_ring_lock = threading.Lock()
_log_ring = []  # list of (iso_ts, level, message)


def log(msg, level="info"):
    ts = now_iso()
    print(f"[{ts}] {msg}", flush=True)
    with _log_ring_lock:
        _log_ring.append((ts, level, msg))
        # keep ring bounded in memory (2x push max)
        if len(_log_ring) > LOG_PUSH_MAX * 2:
            del _log_ring[:len(_log_ring) - LOG_PUSH_MAX]


def _drain_log_ring():
    """Pop all buffered log lines (newest last). Thread-safe."""
    with _log_ring_lock:
        lines = list(_log_ring)
        _log_ring.clear()
    return lines


def _push_logs(supa, lines):
    """Best-effort insert of log lines into factory_worker_logs. Never raises."""
    if not lines:
        return
    # Take only the newest LOG_PUSH_MAX lines
    lines = lines[-LOG_PUSH_MAX:]
    rows = [{"worker_id": WORKER_ID, "ts": ts, "level": lvl, "message": msg}
            for ts, lvl, msg in lines]
    try:
        supa.insert("factory_worker_logs", rows)
    except (RuntimeError, requests.RequestException):
        pass  # swallow -- log push is best-effort


# ---------------------------------------------------------------- seeding


def playbook_guidelines(match_key):
    """Extract the channel's locked-parameter row from PRODUCTION-PLAYBOOK.md section 14."""
    try:
        text = PLAYBOOK.read_text()
    except OSError:
        return ""
    m = re.search(r"^## 14\..*?(?=^## |\Z)", text, re.M | re.S)
    section = m.group(0) if m else text
    for line in section.splitlines():
        if f"`{match_key}`" in line and line.strip().startswith("|"):
            clean = re.sub(r"[*`]", "", line).strip().strip("|")
            cells = [c.strip() for c in clean.split("|")]
            row = " | ".join(c for c in cells if c)
            return ("Locked parameters (docs/PRODUCTION-PLAYBOOK.md section 14 -- "
                    "Channel | Pipeline | Host/character | Voice | Accent | Cadence | Content mix | Status):\n"
                    f"{row}\n"
                    "Cross-cluster rule: kids channels and the adult (AI Unpacked) cluster never cross-link.")
    return ""


def seed_channels(supa):
    rows = []
    for ch in CHANNEL_SEED:
        rows.append({
            "key": ch["key"],
            "name": ch["name"],
            "niche": ch["niche"],
            "accent": ch["accent"],
            "guidelines": playbook_guidelines(ch["match"]),
        })
    # on conflict (key) DO NOTHING -- dashboard edits are never overwritten
    supa.insert("factory_channels", rows, on_conflict="key", resolution="ignore-duplicates")
    log(f"seeded factory_channels ({len(rows)} rows, ignore-duplicates)")


def first_docstring_line(path):
    try:
        tree = ast.parse(path.read_text(), filename=str(path))
        doc = ast.get_docstring(tree)
        if doc:
            for line in doc.splitlines():
                if line.strip():
                    return line.strip()[:300]
    except (SyntaxError, OSError, ValueError):
        pass
    return ""


def seed_generators(supa):
    rows = []
    ts = now_iso()
    for p in sorted(SCRIPTS_DIR.glob("*.py")):
        rows.append({
            "name": p.name,
            "path": str(p.relative_to(REPO)),
            "description": first_docstring_line(p),
            "updated_at": ts,
        })
    if rows:
        # on conflict (name) update description + updated_at
        supa.insert("factory_generators", rows, on_conflict="name", resolution="merge-duplicates")
    log(f"seeded factory_generators ({len(rows)} rows, merge-duplicates)")


def seed_settings(supa):
    """v4: default auto-sync settings (dashboard edits win -- ignore-duplicates)."""
    supa.insert("factory_settings", [
        {"key": "auto_sync_hour", "value": "07:30"},
        {"key": "auto_sync_tz", "value": "Asia/Kolkata"},
        {"key": "default_publish_time", "value": "16:00"},  # v8: draft publish slot (local tz)
    ], on_conflict="key", resolution="ignore-duplicates")
    log("seeded factory_settings auto_sync defaults (ignore-duplicates)")


# ---------------------------------------------------------------- v14: worker registry


def detect_gpu():
    """Best-effort NVIDIA GPU name via nvidia-smi (None if absent). Never raises."""
    try:
        exe = shutil.which("nvidia-smi")
        if not exe:
            return None
        out = subprocess.run([exe, "--query-gpu=name", "--format=csv,noheader"],
                             capture_output=True, text=True, timeout=10)
        name = (out.stdout or "").strip().splitlines()
        return name[0].strip() if name and name[0].strip() else None
    except (OSError, subprocess.SubprocessError):
        return None


# v19: surface the worker's checked-out commit in its status row, so operators
# (and a re-enqueue gate) can see exactly which code a worker runs and confirm an
# auto-update landed before dispatching version-sensitive jobs. Cached ~60s.
_git_sha_cache = {"at": 0.0, "val": None}


def _worker_git_sha():
    """Short HEAD sha of the worker's checkout (cached), '' on any git error."""
    now = time.time()
    if _git_sha_cache["val"] is not None and now - _git_sha_cache["at"] < 60:
        return _git_sha_cache["val"]
    try:
        rc, out, _ = _git(["rev-parse", "--short", "HEAD"], timeout=15)
        val = out if rc == 0 else ""
    except (OSError, subprocess.SubprocessError):
        val = ""
    _git_sha_cache.update(at=now, val=val)
    return val


def _worker_meta(usage=None, resources=None):
    """The factory_workers.meta JSONB payload. Static host facts always; the v17
    usage rollup and v18 resource-health snapshot folded in when present. Rebuilt
    whole on every write so a heartbeat that adds meta.usage/meta.resources never
    clobbers python/platform (patch replaces the JSONB column, not deep-merges it)."""
    m = {"python": platform.python_version(), "platform": platform.platform(),
         "git": _worker_git_sha()}
    if usage is not None:
        m["usage"] = usage
    if resources is not None:
        m["resources"] = resources
    return m


# v17: cache the rolling usage rollup so writing meta.usage on every ~20s
# heartbeat costs at most one factory_jobs query per USAGE_REFRESH_S.
_usage_cache = {"at": 0.0, "val": None}

# Claude Code prints "Claude AI usage limit reached|<unix_epoch>" when the
# subscription's rolling cap is hit; the number is WHEN it resets. Pull it out of
# the stored job error so the dashboard can say "healthy again <time>" instead of
# an open-ended "RATE LIMITED".
_RATE_RESET_RE = re.compile(r"limit reached\s*\|\s*(\d{9,13})", re.I)


def parse_rate_reset(text):
    """Reset time (unix epoch SECONDS) embedded in a Claude usage-limit error, or
    None. Tolerates the epoch being reported in seconds or milliseconds."""
    m = _RATE_RESET_RE.search(text or "")
    if not m:
        return None
    val = int(m.group(1))
    return val // 1000 if val > 1_000_000_000_000 else val


def _parse_iso(s):
    """PostgREST timestamptz string -> aware UTC datetime, or None."""
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def usage_rollup(supa):
    """Near-real-time usage snapshot for this worker's status row.

    There is no non-interactive way to read the Claude subscription's rolling-limit
    percentage (the `/usage` slash command shows it interactively; the CLI exposes
    no `claude usage` subcommand, flag, or local cache). What IS live and real is
    the per-run cost + token usage the CLI emits on its `result` event, which
    run_job stores in factory_jobs.result.usage. This sums that across THIS
    worker's jobs finished inside the subscription's rolling window, plus a
    rate_limited tripwire (any recent job that failed on a usage/rate cap). Result
    goes into factory_workers.meta.usage. Throttled + cached; best-effort, never
    raises (returns the last good value, or None if never computed)."""
    now = time.time()
    if _usage_cache["val"] is not None and now - _usage_cache["at"] < USAGE_REFRESH_S:
        return _usage_cache["val"]
    # 'Z' suffix, never '+00:00': this value goes into a PostgREST URL query,
    # where an unencoded '+' decodes to a space and silently breaks the filter.
    since = (datetime.now(timezone.utc) - timedelta(hours=USAGE_WINDOW_H)
             ).strftime("%Y-%m-%dT%H:%M:%SZ")
    # window_start = when the current 5h window opened (earliest Claude activity in
    # it); reset_at = the AUTHORITATIVE reset from a cap-hit error; reset_est = the
    # estimate window_start + 5h used before any cap is hit. The dashboard draws a
    # time-through-window bar from these (the true subscription quota % is not
    # machine-readable, so we show elapsed-time, not a fake used/total).
    out = {"window_h": USAGE_WINDOW_H, "since": since, "jobs": 0,
           "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0,
           "rate_limited": False, "reset_at": None, "reset_est": None,
           "window_start": None, "at": now_iso()}
    try:
        # factory_jobs carries the claimer in assigned_worker (there is no
        # worker_id column on jobs — that name lives on factory_workers).
        rows = supa.select(
            "factory_jobs",
            f"assigned_worker=eq.{WORKER_ID}&finished_at=gte.{since}"
            "&select=status,error,result,finished_at")
    except (RuntimeError, requests.RequestException) as e:
        log(f"usage rollup query failed (keeping last value): {e}", level="warn")
        return _usage_cache["val"]  # keep last good value; retry next heartbeat
    matched_limit = False
    reset_epoch = 0
    earliest_ai = None  # earliest finished_at (dt) of a Claude-consuming job
    for r in rows or []:
        u = (r.get("result") or {}).get("usage") or {}
        consumed = False
        try:
            c = float(u.get("cost_usd") or 0)
            it = int(u.get("input_tokens") or 0)
            ot = int(u.get("output_tokens") or 0)
            out["cost_usd"] += c
            out["input_tokens"] += it
            out["output_tokens"] += ot
            consumed = bool(c or it or ot)
        except (TypeError, ValueError):
            pass
        out["jobs"] += 1
        err_raw = r.get("error") or ""
        err = err_raw.lower()
        if r.get("status") == "failed" and any(s in err for s in
                                                ("rate limit", "usage limit", "429")):
            matched_limit = True
            consumed = True  # a capped attempt still marks Claude activity
            ep = parse_rate_reset(err_raw)
            if ep and ep > reset_epoch:
                reset_epoch = ep
        if consumed:
            ts = _parse_iso(r.get("finished_at"))
            if ts and (earliest_ai is None or ts < earliest_ai):
                earliest_ai = ts
    out["cost_usd"] = round(out["cost_usd"], 4)
    # window anchor + estimated reset from observed Claude activity
    if earliest_ai is not None:
        out["window_start"] = earliest_ai.strftime("%Y-%m-%dT%H:%M:%SZ")
        out["reset_est"] = (earliest_ai + timedelta(hours=USAGE_WINDOW_H)
                            ).strftime("%Y-%m-%dT%H:%M:%SZ")
    if matched_limit:
        if reset_epoch:
            reset_dt = datetime.fromtimestamp(reset_epoch, timezone.utc)
            out["reset_at"] = reset_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            # a real cap gives the exact window: anchor it precisely
            out["window_start"] = (reset_dt - timedelta(hours=USAGE_WINDOW_H)
                                   ).strftime("%Y-%m-%dT%H:%M:%SZ")
            # Self-clearing: a reset time already in the past means the rolling
            # window rolled and AI jobs work again -- even though the failed row
            # is still inside the reporting window and would otherwise keep the
            # tripwire stuck on for USAGE_WINDOW_H.
            out["rate_limited"] = reset_epoch > now
        else:
            out["rate_limited"] = True  # capped, but the CLI gave no reset epoch
    _usage_cache.update(at=now, val=out)
    return out


# v18: cache the resource-health snapshot so writing meta.resources on every ~20s
# heartbeat spawns nvidia-smi at most once per RESOURCES_REFRESH_S.
_resources_cache = {"at": 0.0, "val": None}


def _gpu_snapshot():
    """NVIDIA GPU health via nvidia-smi -> {name, util_pct, mem_used_mb,
    mem_total_mb, temp_c, power_w}, or None when there's no nvidia-smi / no GPU.
    Same shell-out approach as detect_gpu; never raises (returns None on any error).
    Individual fields are None when nvidia-smi reports them as [N/A] (common for
    temp/power on laptop or virtualised GPUs)."""
    try:
        exe = shutil.which("nvidia-smi")
        if not exe:
            return None
        out = subprocess.run(
            [exe, "--query-gpu=name,utilization.gpu,memory.used,memory.total,"
             "temperature.gpu,power.draw", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10)
        lines = [ln for ln in (out.stdout or "").strip().splitlines() if ln.strip()]
        if not lines:
            return None
        parts = [p.strip() for p in lines[0].split(",")]

        def _num(i, cast):
            try:
                v = parts[i]
            except IndexError:
                return None
            if v in ("", "[N/A]", "N/A", "[Not Supported]", "[Unknown Error]"):
                return None
            try:
                return cast(v)
            except (TypeError, ValueError):
                return None

        name = parts[0] if parts and parts[0] else None
        return {
            "name": name,
            "util_pct": _num(1, int),
            "mem_used_mb": _num(2, int),
            "mem_total_mb": _num(3, int),
            "temp_c": _num(4, int),
            "power_w": _num(5, float),
        }
    except (OSError, subprocess.SubprocessError):
        return None


def resources_snapshot():
    """Best-effort machine resource-health snapshot for factory_workers.meta
    .resources (dashboard Machines page). Every field is independently optional and
    NOTHING here ever raises -- any probe that fails is simply omitted:

      gpu   {name, util_pct, mem_used_mb, mem_total_mb, temp_c, power_w} | None
      disk  {used_gb, total_gb}          (repo volume, via shutil.disk_usage)
      cpu   {cores, pct?}                (cores always; pct only if psutil present)
      ram   {used_gb, total_gb}          (only if psutil present)
      at    ISO timestamp

    psutil is optional on purpose: workers do not re-pip on auto-upgrade, so CPU%
    and RAM gracefully drop out while GPU + disk + cores still populate. Throttled +
    cached so the ~20s heartbeat spawns nvidia-smi at most once per
    RESOURCES_REFRESH_S; returns the last good value between refreshes."""
    now = time.time()
    cached = _resources_cache["val"]
    if cached is not None and now - _resources_cache["at"] < RESOURCES_REFRESH_S:
        return cached
    out = {"at": now_iso()}
    try:
        # GPU: the key is written even when None so the UI can hide the row.
        out["gpu"] = _gpu_snapshot()
        # Disk usage of the repo's volume (round to 1 decimal GiB).
        try:
            du = shutil.disk_usage(str(REPO))
            out["disk"] = {"used_gb": round(du.used / (1024 ** 3), 1),
                           "total_gb": round(du.total / (1024 ** 3), 1)}
        except OSError:
            pass
        # CPU cores always (stdlib); percent + RAM only when psutil imports.
        cpu = {}
        cores = os.cpu_count()
        if cores:
            cpu["cores"] = int(cores)
        try:
            import psutil  # optional -- absent on auto-upgraded workers
        except ImportError:
            psutil = None
        if psutil is not None:
            try:
                cpu["pct"] = round(float(psutil.cpu_percent()), 1)
            except Exception:
                pass
            try:
                vm = psutil.virtual_memory()
                out["ram"] = {"used_gb": round(vm.used / (1024 ** 3), 1),
                              "total_gb": round(vm.total / (1024 ** 3), 1)}
            except Exception:
                pass
        if cpu:
            out["cpu"] = cpu
    except Exception:
        # Truly best-effort: on any unexpected failure keep the last good value if
        # we have one, else return whatever partial dict we built.
        if cached is not None:
            return cached
    _resources_cache.update(at=now, val=out)
    return out


# Outages shorter than this on a restart are just a clean bounce (auto-update, manual
# restart) -- not worth an event. Longer gaps (power cut, crash, sleep) get logged.
DOWNTIME_LOG_MIN = 4


def _last_unclean_shutdown():
    """Windows only: TimeCreated (UTC) of the most recent UNEXPECTED shutdown --
    System-log Kernel-Power id 41 or EventLog id 6008 (both mean 'last shutdown was
    dirty', i.e. a power cut / hard reset). None off Windows, on error, or if none
    found. Best-effort; the System log is readable without elevation."""
    if not IS_WINDOWS:
        return None
    try:
        ps = ("$e=Get-WinEvent -FilterHashtable @{LogName='System';Id=41,6008} "
              "-MaxEvents 1 -ErrorAction SilentlyContinue; "
              "if($e){$e.TimeCreated.ToUniversalTime().ToString('o')}")
        out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                             capture_output=True, text=True, timeout=30)
        s = (out.stdout or "").strip()
        return _parse_iso(s) if s else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def _log_downtime(supa, prev_last_seen):
    """After a (re)start, record a factory_events 'worker_downtime' row when the
    worker was gone longer than DOWNTIME_LOG_MIN -- classified as a power cut when a
    matching Windows unexpected-shutdown event lines up. Makes silent outages (the
    power cuts we weren't logging) visible on the dashboard. Never raises."""
    if not prev_last_seen:
        return
    gap = (datetime.now(timezone.utc) - prev_last_seen).total_seconds()
    if gap < DOWNTIME_LOG_MIN * 60:
        return  # clean bounce, not an outage
    unclean = _last_unclean_shutdown()
    # a dirty-shutdown event at/after our last heartbeat => this outage was a power cut
    if unclean and unclean >= prev_last_seen - timedelta(minutes=5):
        cause = "power_cut"
    else:
        cause = "unknown"  # sleep / crash / manual stop / clean shutdown
    mins = int(gap // 60)
    try:
        supa.insert("factory_events", [{
            "kind": "worker_downtime",
            "message": (f"worker {WORKER_ID} recovered after ~{mins}min down "
                        f"(cause: {cause})"),
            "meta": {"worker_id": WORKER_ID, "down_seconds": int(gap),
                     "down_since": prev_last_seen.isoformat(), "cause": cause,
                     "unclean_shutdown_at": unclean.isoformat() if unclean else None},
        }])
        log(f"downtime logged: ~{mins}min down (cause: {cause})")
    except (RuntimeError, requests.RequestException) as e:
        log(f"downtime log failed (continuing): {e}")


def register_worker(supa, max_parallel):
    """Upsert this machine's row in factory_workers. Preserves dashboard-owned
    fields (paused, accept_types, name) on re-registration by NOT overwriting them
    here -- only identity/capability/liveness columns are (re)written."""
    row = {
        "worker_id": WORKER_ID,
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "gpu": detect_gpu(),
        "max_parallel": max_parallel,
        "last_seen": now_iso(),
        "meta": _worker_meta(),
    }
    # First insert seeds name (friendly default); later upserts leave name/paused/
    # accept_types alone so dashboard edits stick. Also grab the prior last_seen so a
    # (re)start can measure + log how long this worker was gone (power cuts etc.).
    prev_last_seen = None
    try:
        existing = supa.select("factory_workers",
                               f"worker_id=eq.{WORKER_ID}&select=worker_id,last_seen")
    except (RuntimeError, requests.RequestException):
        existing = []
    if existing:
        prev_last_seen = _parse_iso(existing[0].get("last_seen"))
    else:
        row["name"] = WORKER_NAME
    supa.insert("factory_workers", [row], on_conflict="worker_id",
                resolution="merge-duplicates")
    log(f"registered worker '{WORKER_NAME}' ({WORKER_ID}) os={row['os']} gpu={row['gpu'] or 'none'}")
    _log_downtime(supa, prev_last_seen)


def worker_heartbeat(supa):
    """Bump last_seen (+ v17 meta.usage rollup) and read this worker's live routing
    config back in one round-trip. Returns (paused: bool, accept_types: list|None).
    On ANY error returns (False, None) so a heartbeat hiccup never stalls claiming."""
    patch = {"last_seen": now_iso()}
    usage = usage_rollup(supa)  # v17: near-real-time spend/token rollup (throttled)
    resources = resources_snapshot()  # v18: GPU/CPU/RAM/disk health (throttled)
    if usage is not None or resources is not None:
        patch["meta"] = _worker_meta(usage, resources)
    try:
        rows = supa.patch_returning("factory_workers", f"worker_id=eq.{WORKER_ID}",
                                    patch, select="paused,accept_types")
        if rows:
            r = rows[0]
            acc = r.get("accept_types")
            return bool(r.get("paused")), (acc if acc else None)
    except (RuntimeError, requests.RequestException):
        pass
    return False, None


# ---------------------------------------------------------------- prompt + command


def manifest_path(job_id):
    return RENDERS_OUT / f"manifest_{job_id}.json"


def suggestions_path(job_id):
    return RENDERS_OUT / f"suggestions_{job_id}.json"


def factory_backlog_path():
    """v16: kind='factory' suggestions land here (Markdown, review from Claude Code)
    instead of factory_calendar rows that clutter every calendar surface. Convention
    matches docs/NETWORK-ATTENTION.md and docs/PRODUCTION-PLAYBOOK.md."""
    return REPO / "docs" / "FACTORY-BACKLOG.md"


def brief_path(job_id):
    return RENDERS_OUT / f"brief_{job_id}.json"


def brief_ctx_path(job_id):
    return RENDERS_OUT / f"brief_ctx_{job_id}.json"


def plan_content_path(job_id):
    return RENDERS_OUT / f"plan_content_{job_id}.json"


def plan_content_ctx_path(job_id):
    return RENDERS_OUT / f"plan_content_ctx_{job_id}.json"


def assets_plan_path(job_id):
    return RENDERS_OUT / f"assets_plan_{job_id}.json"


def asset_out_path(job_id):
    return RENDERS_OUT / f"asset_out_{job_id}.json"


def staged_ctx_path(job_id):
    return RENDERS_OUT / f"staged_ctx_{job_id}.json"


def preview_out_path(job_id):
    return RENDERS_OUT / f"preview_out_{job_id}.json"


def channel_intake_path(job_id):
    return RENDERS_OUT / f"channel_intake_{job_id}.json"


def channel_scaffold_path(job_id):
    return RENDERS_OUT / f"channel_scaffold_{job_id}.json"


# v19: template registry (factory_templates). A channel's template row names its
# production pipeline (produce_style / plan_style / blueprint_source); the
# per-channel prompt branches below select on STYLE, not channel key. Channels
# with no template resolve through LEGACY_TEMPLATE_STYLES so behavior never
# regresses if the DB rows are missing or the fetch fails.
LEGACY_TEMPLATE_STYLES = {
    "claude-tricks": {"produce_style": "claude-tricks-v16", "plan_style": "ai-unpacked"},
    "already-happening": {"produce_style": "cinematic-animatic", "plan_style": "cinematic"},
    "aashiqana": {"produce_style": "sensual-motion", "plan_style": "blueprint"},
}


def channel_template(supa, key):
    """factory_channels.template -> factory_templates row (dict), else the legacy
    per-key style stub, else None. Best-effort: any fetch error falls back."""
    if not key or key == "_network":
        return None
    try:
        rows = supa.select("factory_channels", f"key=eq.{key}&select=template")
        tkey = rows[0].get("template") if rows else None
        if tkey:
            trows = supa.select("factory_templates", f"key=eq.{tkey}&select=*")
            if trows:
                return trows[0]
    except (RuntimeError, requests.RequestException) as e:
        log(f"  could not fetch template for {key} (using legacy styles): {e}")
    return LEGACY_TEMPLATE_STYLES.get(key)


def build_prompt(job, guidelines="", ctx_path=None, asset=None, template=None):
    jtype = job.get("type") or "custom"
    jprompt = (job.get("prompt") or "").strip()
    key = job.get("channel_key") or ""
    # v19: prompt branches select on the channel's template STYLE, not its key
    # (channel_template() already fell back to the legacy per-key styles).
    # No style at all -> the historical defaults below, exactly as before.
    tpl = template or {}
    produce_style = str(tpl.get("produce_style") or "")
    plan_style = str(tpl.get("plan_style") or "")

    if jtype == "produce_short":
        body = (f"Produce a short for channel {key}.\n\n"
                f"CHANNEL GUIDELINES:\n{guidelines or '(none on file)'}\n\n"
                f"JOB BRIEF:\n{jprompt}\n\n"
                "STANDING RULES: follow docs/PRODUCTION-PLAYBOOK.md, premium quality bar.")
    elif jtype == "produce_preview" and (
        (job.get("meta") or {}).get("incubation") or produce_style == "blueprint"
    ):
        # v18: incubation Ep01 TEMP for a brand-new channel; v19: also every
        # post-lock produce for a 'blueprint'-style template channel (no bespoke
        # render pipeline — the channel's own blueprint IS the pipeline). Produce
        # a watchable ~30s cut by FOLLOWING the blueprint, improvising with
        # in-house tools. Do NOT master at 1080p and do NOT arm YouTube — this
        # stops at a preview like every other produce.
        cal_id = (job.get("meta") or {}).get("calendar_id") or ""
        ep_key = str((job.get("meta") or {}).get("ep") or "").strip()
        iteration = int((job.get("meta") or {}).get("iteration") or 1)
        incub = bool((job.get("meta") or {}).get("incubation"))
        intro = (
            f"You are producing the Episode 1 TEMP for the NEW, incubating channel "
            f"'{key}'. This is revision {iteration}. One Claude session, ~25 min budget, "
            "opus/medium tier. It is a TEMP for review — the creator will give feedback "
            "and you'll revise; once they approve, this channel's blueprint gets LOCKED "
            "from what you make here, so make it genuinely good and on-brand.\n\n"
        ) if incub else (
            f"You are producing the next episode PREVIEW for the channel '{key}'. "
            "One Claude session, ~25 min budget, opus/medium tier. The channel's "
            "blueprint is its LOCKED baseline recipe — follow it exactly; the human "
            "reviews the preview in Studio before any finalize/arm.\n\n"
        )
        body = (
            intro
            + f"READ FIRST (this channel's law): channels/{key}/PRODUCTION-BLUEPRINT.md, "
            f"channels/{key}/BRAND-BIBLE.md, and channels/{key}/channel.json. FOLLOW the "
            "blueprint's beat spine, visual/audio identity, and invariants exactly.\n\n"
            + (f"EP KEY: use ep_key = {ep_key} for ALL files "
               f"(channels/{key}/episodes/{ep_key}.json, channels/{key}/assets/ep{ep_key}/, "
               f"channels/{key}/renders/ep{ep_key}_*). Do NOT invent a different number.\n\n"
               if ep_key else "")
            + f"JOB BRIEF (includes any accumulated revision feedback — honor it):\n"
            f"{jprompt}\n\n"
            "PIPELINE (in order):\n"
            "1. PLAN: develop the brief into a full plan that fits the blueprint (title, "
            "hook, VO/script ~28-38s, the shot/asset list, on-screen text). VERIFY every "
            "factual claim with WebSearch first; if a claim can't be verified OR an asset "
            "can't be honestly made, STOP with a manifest error (never fabricate).\n"
            "2. GENERATE ASSETS in blueprint order using IN-HOUSE tools only (PIL/ffmpeg "
            "mocks, ElevenLabs VO if the style has a voice, existing scripts/ helpers). Do "
            "NOT spend on blocked external generators — mock a placeholder and note it. "
            "After EACH asset lands on disk, call `python3 scripts/push_asset.py "
            f"--calendar-id {cal_id} --asset-key <slug> --file <path> --kind "
            "<image|video|audio|text> --group <thumbnail|scene|clip|audio|overlay|other>` "
            "so Studio's filmstrip populates live — unpushed assets are invisible to the "
            "reviewer.\n"
            f"3. WRITE SPEC at channels/{key}/episodes/{ep_key or '01'}.json capturing the "
            "plan you produced (so freeze_baseline can lock the recipe from it).\n"
            "4. PREVIEW RENDER: stitch the assets into a single ~30s vertical (9:16 unless "
            "the blueprint says otherwise) TEMP MP4 with the VO — unmastered, no premium "
            "polish. That IS the preview.\n"
            "5. MANIFEST: write manifest_<job_id>.json listing the preview MP4 as the "
            "primary file, plus a `spec_path` field pointing at the episodes/ JSON.\n\n"
            "COST DISCIPLINE: in-house mocks only, no 1080p master, no endcard/outro "
            "concat, no external paid generators. Those come after the baseline is locked."
        )
    elif jtype == "produce_preview" and produce_style == "cinematic-animatic":
        # v17: "already-happening" is a CINEMATIC, host-less channel whose 6 motion
        # clips CANNOT be generated headlessly (Leonardo's generation API is
        # 402-blocked; the web UI needs an interactive Chrome session). So this
        # headless produce_preview session preps everything it CAN — script +
        # fact-check receipts + VO + a per-episode build_ep<ep>.py + an ANIMATIC
        # (VO + running captions over BLACK placeholder beds; that animatic IS the
        # Studio preview) — and writes a MOTION-TODO.md sentinel carrying the 6 Wan
        # 2.6 prompts for a human to render in Chrome. scripts/finalize_already_
        # happening.py refuses to arm until those 6 real clips replace the
        # placeholders and MOTION-TODO.md is deleted. See
        # channels/already-happening/PRODUCTION-BLUEPRINT.md (the locked recipe).
        cal_id = (job.get("meta") or {}).get("calendar_id") or ""
        ep = str((job.get("meta") or {}).get("ep") or "").strip()
        ep_title = re.sub(r"^Preview\s*[—:-]\s*", "", (job.get("title") or "")).strip()
        body = (
            "You are producing the ANIMATIC PREVIEW of an 'already-happening' Short "
            "(host-less cinematic channel on the near future of AI, teal identity). "
            "ONE headless Claude session. You CANNOT generate motion footage — "
            "Leonardo's generation API is blocked and there is no browser here; a "
            "human renders the 6 Wan 2.6 clips in Chrome AFTER you. Your job is to "
            "prep everything else and STOP at a black-bed animatic.\n\n"
            f"EP KEY: use ep = {ep!r} for ALL paths and names (channels/already-"
            f"happening/episodes/ep{ep}.*, assets/ep{ep}/, renders/ep{ep}/). Do NOT "
            f"invent a different number.\n"
            f"EPISODE TITLE (from the channel planner): {ep_title!r} — this is the "
            "locked YouTube title; build the script to deliver it.\n\n"
            f"CHANNEL GUIDELINES:\n{guidelines or '(none on file)'}\n\n"
            f"TOPIC / BRIEF:\n{jprompt}\n\n"
            "READ FIRST: channels/already-happening/PRODUCTION-BLUEPRINT.md and "
            "channels/already-happening/CHANNEL-SETUP.md and docs/PRODUCTION-"
            "PLAYBOOK.md. build_ep01_v3.py is the CANONICAL builder/template.\n\n"
            "PIPELINE (in order — do each, push each to Studio as it lands):\n"
            "1. SCRIPT: write a 6-beat script on the locked spine (cold-open hook -> "
            "TODAY anchor -> +5yr extrapolation -> gut-punch impact -> binary "
            "button), punchy AI-Unpacked style (short lines, curiosity gaps), VO "
            f"total ~28-35s. Alternate wonder/provocation vs the previous episode. "
            "FACT-CHECK GATE (the channel's whole wedge): VERIFY every on-screen "
            "number/claim with WebSearch against a DATED primary source; keep stated "
            "figures CONSERVATIVE. If an anchor can't be verified, pick another — "
            "never fabricate. Write channels/already-happening/episodes/"
            f"ep{ep}.script.json (beats + title + hot_words) and episodes/"
            f"ep{ep}.receipts.md (each claim -> dated source URL).\n"
            "2. VO (Brian, non-robotic): for i in 1..6 run `python3 scripts/eleven_vo.py "
            f"--voice nPczCjzI2devNBz1zQrb --text \"<beat i>\" --out channels/already-"
            f"happening/renders/ep{ep}/vo/beat<i>.wav --style 0.32 --speed 1.0`. Each "
            "call also writes beat<i>.wav.words.json (word timing that drives the "
            "running captions). Push each wav to Studio.\n"
            "3. MOTION PROMPTS (for the human, NOT for you): write 6 Wan 2.6 prompts, "
            "one per beat — cinematic, grounded-futuristic, electric-teal, explicit "
            "camera move, end each with 'coherent stable shapes, no distortion'. Vary "
            "all 6 visuals genuinely (anti-throttle). Write them to channels/already-"
            f"happening/assets/ep{ep}/MOTION-TODO.md (a numbered checklist: model=Wan "
            "2.6, 9:16, 5s, audio OFF; download to assets/ep"
            f"{ep}/motion/beat<i>.mp4; delete this file when all 6 are real) AND into "
            f"the episode manifest (step 8). Do NOT try to generate motion.\n"
            "4. PLACEHOLDER BEDS (so the UNMODIFIED builder can render an animatic): "
            "for i in 1..6 create a black 720x1280 clip of beat<i>'s VO duration with "
            "a faint centered teal glow -> channels/already-happening/assets/ep"
            f"{ep}/motion/beat<i>.mp4 (ffmpeg lavfi color=black + the VO length). "
            "These are DISPOSABLE — the human overwrites them with real Wan 2.6 "
            "clips. Keep each well under 200KB so finalize can tell them from real "
            "footage.\n"
            "5. BUILDER: `cp channels/already-happening/build_ep01_v3.py channels/"
            f"already-happening/build_ep{ep}.py` and edit ONLY the marked spots: MOT "
            f"= assets/ep{ep}/motion, VO = renders/ep{ep}/vo, OUT = renders/ep{ep}, "
            "the BEATS clip filenames (beat1.mp4..beat6.mp4 paired to beat1..beat6 "
            "VO), the HOT keyword set (this topic's numbers + punchy nouns), and the "
            f"output name -> ep{ep}.mp4. Do NOT touch the opener / brand bug / end "
            "card / grade / bed_3 score / encode — those are the LOCKED brand frame "
            "(cold-open stays 'THE FUTURE ISN'T COMING').\n"
            f"6. ANIMATIC RENDER: run `python3 channels/already-happening/build_ep{ep}.py`. "
            f"It renders channels/already-happening/renders/ep{ep}/ep{ep}.mp4 (cold-"
            "open + black beds + VO + running teal captions + end card). COPY it to "
            f"renders/ep{ep}/ep{ep}_prev.mp4 (the '_prev' + 'ep{ep}_' name lets the "
            "worker stamp it as the Studio preview). This animatic is the QC gate for "
            "SCRIPT + VO + CAPTION TIMING only — motion comes later.\n"
            "7. PUSH TO STUDIO: after each asset lands call `python3 scripts/push_asset.py "
            f"--calendar-id {cal_id} --asset-key <slug> --file <path> --kind "
            "<text|audio|video> --group <other|audio|clip>` — push the script, the "
            "receipts, the MOTION-TODO.md (so the reviewer sees the 6 prompts), the 6 "
            "VO wavs, and the animatic. Unpushed assets are invisible to the reviewer.\n"
            f"8. EPISODE MANIFEST: write channels/already-happening/episodes/ep{ep}.json "
            '= {"ep": str, "title": str, "tags": str (csv), "description_path": '
            f'"episodes/ep{ep}_description.txt", "builder": "build_ep{ep}.py", '
            f'"output": "renders/ep{ep}/ep{ep}_web.mp4", "motion_dir": "assets/ep{ep}/'
            'motion", "motion_clips": ["beat1.mp4",...,"beat6.mp4"], "motion_prompts": '
            '[{"beat": int, "prompt": str, "file": "beat<i>.mp4"}]}. Also write '
            f"episodes/ep{ep}_description.txt (SEO description + 3-5 hashtags led by "
            "#Shorts, per CHANNEL-SETUP.md).\n"
            f"9. JOB MANIFEST: write {manifest_path(job['id'])} with files = [{{\"path\": "
            f"\"channels/already-happening/renders/ep{ep}/ep{ep}_prev.mp4\", \"kind\": "
            "\"video\", \"channel_key\": \"already-happening\"}] plus a recap "
            "(headline/steps/decisions/issues/outputs/next). The animatic is the only "
            "file here — it becomes the Studio preview; NO post is drafted for it.\n\n"
            "COST DISCIPLINE: NO motion generation (blocked — the human does it), NO "
            "Leonardo image gen, ffmpeg/PIL only. STOP at the animatic. Finalize "
            "(after the human renders motion) will build the real cut + arm YouTube."
        )
    elif jtype == "produce_preview" and produce_style == "sensual-motion":
        # v18: Aashiqana sensual-motion Shorts. Like already-happening, the
        # creative generation CANNOT run headlessly — both the Suno song AND the
        # Leonardo keyframes+Hailuo motion need an interactive, logged-in Chrome
        # session + human face/keyframe approvals. So this session preps the
        # DETERMINISTIC parts (word-first hookcut + caption timing + manifest +
        # description) and writes a LEONARDO-TODO.md sentinel carrying the locked
        # 8 prompts (1 anchor + 4 keyframes + 4 motion) for a human to render in
        # Chrome. If the human has ALREADY dropped the 4 motion clips + hookcut,
        # it assembles + brands a preview. scripts/finalize_aashiqana.py assembles
        # (if needed) + arms once the clips are real and the sentinel is gone.
        # Locked recipe: channels/aashiqana/SHORTS-TEMPLATE-LOCKED.md.
        cal_id = (job.get("meta") or {}).get("calendar_id") or ""
        ep = str((job.get("meta") or {}).get("ep") or "").strip()
        ep_title = re.sub(r"^Preview\s*[—:-]\s*", "", (job.get("title") or "")).strip()
        body = (
            "You are producing the PREVIEW of an Aashiqana Short (premium AI Hindi "
            "romantic-song channel, monsoon/golden palette). ONE headless Claude "
            "session. You CANNOT generate the song or the couple footage headlessly "
            "— Suno and Leonardo both need an interactive logged-in Chrome session "
            "with human approvals. Prep everything deterministic, leave a sentinel "
            "for the interactive steps, and STOP.\n\n"
            f"EP KEY: ep = {ep!r}. TITLE (locked, from planner): {ep_title!r}.\n\n"
            f"CHANNEL GUIDELINES:\n{guidelines or '(none on file)'}\n\n"
            f"BRIEF:\n{jprompt}\n\n"
            "READ FIRST (non-negotiable): channels/aashiqana/SHORTS-TEMPLATE-LOCKED.md "
            "(the locked pipeline), channels/aashiqana/BRAND-BIBLE.md, and "
            "docs/PRODUCTION-PLAYBOOK.md. Reusable: scripts/assemble_motion_generic.py "
            "and channels/aashiqana/songs/03-aadhi-raat/polish_short.py "
            "(--src --out --pov1 --pov2).\n\n"
            "PIPELINE (do the deterministic parts; push each to Studio):\n"
            "1. SONG SLUG: derive a song slug from the brief (e.g. 02-aaja-ve). Use "
            "channels/aashiqana/songs/<slug>/ for ALL paths.\n"
            "2. HOOK AUDIO (only if a Suno mp3 already exists at songs/<slug>/"
            "renders/*.mp3 or track/*.mp3): whisper-verify (faster_whisper small, hi, "
            "word_timestamps) where the VOCAL WORD starts, then cut a ~24s word-first "
            "hookcut that OPENS on the word at 0.0s (never humming) -> songs/<slug>/"
            "renders/<slug>_hookcut.mp3. Build songs/<slug>/lyrics/timing_hook.json "
            "(4 bilingual lines: {s,e,text,hi}). If no mp3 yet, note it in the "
            "sentinel and skip.\n"
            "3. LEONARDO-TODO.md (for the human — the interactive gate): write "
            "channels/aashiqana/songs/<slug>/LEONARDO-TODO.md with the 8 locked "
            "prompts from SHORTS-TEMPLATE-LOCKED.md, adapted to THIS song's SETTING "
            "(pick a setting that ROTATES OFF the previous short's location): "
            "(a) 1 anchor prompt (Nano Banana 2, 2:3, fresh couple, VJ approves face); "
            "(b) 4 keyframe prompts K1 establishing / K2 her single / K3 bold beat "
            "(embrace-from-behind) / K4 near-kiss (Nano Banana 2, Image-Ref=anchor, "
            "tasteful wording — NO 'sensual/lips/almost-kiss/bare shoulders' or "
            "Leonardo disables Generate); (c) 4 Hailuo 2.3 motion prompts (start-frame, "
            "9:16, 6s: front-to-camera turn / push-in / from-behind hot turn / "
            "sink-to-bed). Tell the human to drop the 4 clips into songs/<slug>/_motion/"
            "CLIP_{anchor,her,behind,kiss}.mp4 and delete this file when done.\n"
            "4. IF the 4 motion clips + the hookcut already exist (human did Leonardo): "
            "assemble `python3 scripts/assemble_motion_generic.py --clips <ordered "
            "CLIP_*.mp4> --audio songs/<slug>/renders/<slug>_hookcut.mp3 --lyrics "
            "songs/<slug>/lyrics/timing_hook.json --out songs/<slug>/renders/<slug>_"
            "motion_prev.mp4`, then brand `python3 channels/aashiqana/songs/03-aadhi-"
            "raat/polish_short.py --src <prev> --out songs/<slug>/renders/<slug>_"
            "branded.mp4 --pov1 \"<Hinglish POV tied to the hook lyric>\" --pov2 "
            "\"<2nd line>\"`. That branded file is the Studio preview. Else render "
            "nothing (the sentinel stands).\n"
            "5. DESCRIPTION: write songs/<slug>/description_short.txt = the hook line "
            "+ '🎧 Use this sound.' + the AI/synthetic disclosure (original song & "
            "visuals created with AI, not affiliated) + @aashiqana.diaries + #shorts "
            "#hindisong #lovesong hashtags.\n"
            "6. MANIFEST: write channels/aashiqana/episodes/ep" + ep + ".json = "
            '{"ep": str, "title": str, "tags": str (csv), "song_slug": str, '
            '"branded_path": "channels/aashiqana/songs/<slug>/renders/<slug>_branded.mp4", '
            '"description_path": "channels/aashiqana/songs/<slug>/description_short.txt"}.\n'
            f"7. PUSH: after each asset call `python3 scripts/push_asset.py --calendar-id "
            f"{cal_id} --asset-key <slug> --file <path> --kind <text|audio|video> "
            "--group <other|audio|clip>` — push the hookcut, the LEONARDO-TODO.md, and "
            "the branded preview if it exists. Unpushed assets are invisible in Studio.\n"
            f"8. JOB MANIFEST: write {manifest_path(job['id'])} with files = [the branded "
            "preview if it exists, else the LEONARDO-TODO.md as kind text] + a recap "
            "(headline/steps/decisions/issues/outputs/next). NO post is drafted here.\n\n"
            "COST DISCIPLINE: ffmpeg/PIL/whisper only. NO Suno, NO Leonardo, NO Seedance. "
            "STOP at the preview-or-sentinel. Finalize assembles (if needed) + arms YouTube."
        )
    elif jtype == "produce_preview":
        # v16: monolithic one-Claude-call short production that STOPS at a
        # low-cost preview. Human reviews the preview MP4 in Studio; a scripted
        # finalize_episode.py job later runs mastering + endcard + outro + arm
        # YT. Cost profile: opus/medium ~$2.5/short (vs $4 for full produce_short),
        # ~22-28 min wall vs 34 min. Human quality gate before spending on the
        # 1080p master. See scripts/push_asset.py for the per-asset Studio
        # visibility hook.
        cal_id = (job.get("meta") or {}).get("calendar_id") or ""
        ep_key = str((job.get("meta") or {}).get("ep") or "").strip()
        body = (
            "You are producing a low-res PREVIEW of a claude-tricks Short. "
            "One Claude session, ~25 min budget, opus/medium tier. Do NOT master "
            "at 1080p — that happens later via scripts/finalize_episode.py.\n\n"
            + (f"EP KEY: use ep_key = {ep_key} for ALL files "
               f"(channels/claude-tricks/episodes/{ep_key}.v2.json, assets/ep{ep_key}/, "
               f"renders/ep{ep_key}_*) and epTag 'EP{ep_key} · <TOPIC>'. Do NOT invent "
               f"a different number.\n\n" if ep_key else "")
            + f"CHANNEL GUIDELINES:\n{guidelines or '(none on file)'}\n\n"
            f"JOB BRIEF (locked plan JSON follows):\n{jprompt}\n\n"
            "STANDING RULES: follow docs/PRODUCTION-PLAYBOOK.md, premium quality bar.\n\n"
            "PIPELINE (in order):\n"
            "1. PLAN: the brief may be a full locked plan OR just a TOPIC/idea from "
            "the channel planner. If it is a full plan, use it. If it is a topic, "
            "DEVELOP it into a full plan (title, hook, VO lines ~28s, single-beat "
            "demo, thumbnail) FOLLOWING the locked templates episodes/11.v2.json "
            "(ranked countdown) and episodes/12.v2.json (single-tip) — that is the "
            "job. VERIFY every factual claim with WebSearch first; if a claim can't "
            "be verified OR the demo can't be honestly shot, STOP with a manifest "
            "error (never fabricate).\n"
            "2. HOST: the host is PINNED to the Ep11 host (outfit_11_sol_magenta) by "
            "build_ep_v2.py automatically — do NOT register an outfit pool and do NOT "
            "pick a random outfit folder (that rotation is HELD per owner directive "
            "2026-08-11; it re-enables via HOST_OUTFIT_POOL=on). Every host cutaway "
            "is the Ep11 magenta Sol; you do not choose wardrobe.\n"
            "3. GENERATE ASSETS in order. After EACH asset lands on disk, call "
            f"`python3 scripts/push_asset.py --calendar-id {cal_id} "
            "--asset-key <slug> --file <path> --kind <image|video|audio|text> "
            "--group <thumbnail|scene|clip|audio|overlay|other>` so Studio's "
            "filmstrip populates live during your session. Assets that don't "
            "get pushed are invisible to the reviewer.\n"
            "4. WRITE SPEC at channels/claude-tricks/episodes/<ep_key>.v2.json. "
            "TEMPLATE STRICTLY from the LOCKED masters episodes/11.v2.json (ranked "
            "countdown) or episodes/12.v2.json (single-tip / how-to, Vaibhav-DNA "
            "callout demo) — pick whichever shape this episode is. Copy its "
            "structure; change ONLY the content (title, tags, epTag, lines, "
            "hot_words, demo). Do NOT drift to ep10/older templates. INVARIANTS:\n"
            "   - OUTRO: generate THIS episode's own Ep11-style card — `python3 "
            "channels/claude-tricks/gen_outro_card.py --out assets/ep<ep_key>/"
            "outro_card.mp4 --q \"line1|line2\" --pill \"Comment yours\"` with an "
            "episode-specific engagement question — and set `outro_src: "
            "\"ep<ep_key>/outro_card.mp4\"`. NEVER ep10's subscribe/comment sting nor "
            "ep11's literal 'which command' card. KEEP the template's `outro_cta: "
            "\"auto\"` (VJ-approved 2026-08-13): at finalize, Sol SPEAKS a series "
            "CTA over the card (next-planned-episode tease from factory_calendar, "
            "else the series promise). Do NOT write a custom outro_cta line and do "
            "NOT put any CTA before the outro segment — payoff first stays law.\n"
            "   - Opener: a `hook` block (illustration image + lines + hot + kicker), "
            "NEVER a `cover` title card (cover reads as an intro and gets scrolled "
            "past). If no hook illustration exists, generate one (in-house PIL/mock) "
            "— do not fall back to `cover`.\n"
            "   - `steps`: [] (EMPTY, no step chips) UNLESS this is a ranked countdown.\n"
            "   - RANKING: only a RANKED-COUNTDOWN episode (multiple numbered items) "
            "uses `pip:` beats each carrying a `num` (06..01) — that is what shows the "
            "header ranking rail. A SINGLE-TIP / how-to episode (most episodes) has NO "
            "`num` anywhere and uses ONE `rec:<demo>@<t>` demo beat; the rail then "
            "auto-hides (Short.tsx gates it on `num` presence).\n"
            "   - Host beats stay `host`/`host2`; build renders them WIDE 16:9 from the "
            "pinned Ep11 wide avatar — do NOT set a host photo or use the pip crop.\n"
            "   - Keep `music: music/bed_active.mp3`. Set header_scrim/cap_low_rec ONLY "
            "when the demo recording is a LIGHT/full-frame screen (then both are correct "
            "— they keep the header legible + captions off the content).\n"
            "5. PREVIEW RENDER: run `python3 channels/claude-tricks/build_ep_v2.py "
            "--ep <ep_key> --preview --tag prev`. This produces "
            "channels/claude-tricks/renders/ep<ep_key>_prev_raw.mp4 — 1080x1920, "
            "unmastered VO, no music bed, no polish. That IS the preview.\n"
            "   - CAST INTEGRITY (hard rule): if this build ABORTS with CastUnrenderable "
            "— or ANY error naming 'cast' / 'unrenderable' / a host outfit with no "
            "pip/wide photo-avatar ids / a template_version divergence — STOP and REPORT "
            "it in your manifest as `cast unrenderable — hold for owner fix`, quoting the "
            "error. Do NOT edit the episode spec to re-pin a different template_version, "
            "do NOT swap outro_src or the host to something that builds, and do NOT pass "
            "--allow-cast-override. The owner's cast pin (template_version / host outfit / "
            "outro card) is a DELIBERATE choice, NOT a misconfiguration for you to work "
            "around — silently substituting a build-able cast is exactly the EP15 defect "
            "this gate exists to stop.\n"
            "6. QC LITE: run scripts/lipsync_align.py measure and scripts/probe_frames.py "
            "corner on the preview raw. Log offsets but do NOT re-render — that's "
            "for finalize_episode. Fail loudly only if lipsync offset > 60ms.\n"
            "7. MANIFEST: write manifest_<job_id>.json listing the preview raw as "
            "the primary file, plus a `spec_path` field pointing at the episodes/ "
            "JSON so finalize_episode can pick up.\n\n"
            "COST DISCIPLINE: no Leonardo (5 tokens left, blocked — use in-house "
            "PIL mocks). No 1080p master. No endcard composite. No outro concat. "
            "Those are finalize's job."
        )
    elif jtype == "record_demo":
        body = ("Record an authentic tool demo using scripts/record_demo.py and frame it "
                f"with the pro styles (scripts/style_punch.py etc.): {jprompt}")
    elif jtype == "new_channel_scaffold":
        # v18: two-phase channel bring-up for the incubation loop.
        #   phase='bringup'        -> write channels/<key>/ from the wizard brand
        #                             jsonb, clone a blueprint from the chosen
        #                             production style, gen brand assets, and hand
        #                             the app a ready Ep01 brief to auto-produce.
        #   phase='freeze_baseline' -> rewrite that blueprint into the LOCKED
        #                             canonical recipe from the approved Ep01 TEMP.
        meta = job.get("meta") or {}
        phase = str(meta.get("phase") or "bringup").strip()
        out_json = channel_scaffold_path(job["id"])
        if phase == "freeze_baseline":
            cal_id = str(meta.get("calendar_id") or "").strip()
            ep_key = str(meta.get("ep") or "").strip()
            body = (
                f"You are FREEZING the baseline for the incubating channel '{key}'. The "
                "creator approved its Episode 1 TEMP; your job is to rewrite the channel's "
                "blueprint into the LOCKED, canonical recipe that every future episode of "
                "this channel MUST follow — captured tightly enough that a fresh producer "
                "reproduces the exact look/sound without guessing.\n\n"
                f"APPROVED EPISODE: ep_key = {ep_key or '(see the newest preview)'}"
                f"{', calendar_id ' + cal_id if cal_id else ''}. Study what actually shipped "
                "in the approved TEMP:\n"
                f"  - the preview render + the pushed assets under channels/{key}/ "
                "(images, clips, audio, overlays),\n"
                f"  - any spec/plan JSON the produce wrote under channels/{key}/,\n"
                "  - the brief + accumulated revision feedback on the calendar item.\n\n"
                "THEN rewrite these files so they describe the APPROVED result as LOCKED law "
                "(not the earlier draft aspirations):\n"
                f"  1. channels/{key}/PRODUCTION-BLUEPRINT.md — the canonical, reproducible "
                "recipe: exact beat spine + timings, the shot/asset recipe, fonts/type "
                "treatment, colour grade + accent hex, motion/host treatment, audio bed + "
                "loudness (LUFS), caption style, opener/outro rules, and the hard INVARIANTS "
                "('always / never') that define the format. Pin real values from the approved "
                "episode — no placeholders.\n"
                f"  2. channels/{key}/BRAND-BIBLE.md — reconcile it with the locked recipe.\n"
                f"  3. channels/{key}/channel.json — set \"baseline_ep\" to the approved ep "
                "and \"lifecycle\": \"active\".\n\n"
                "Do NOT re-render or re-produce anything, do NOT arm YouTube, do NOT touch "
                "other channels or any factory scripts. This is a documentation-freeze pass.\n\n"
                f"FINALLY write {out_json} (this JSON IS the job result — no manifest, no "
                "renders):\n"
                '{"phase": "freeze_baseline", "locked": true, "baseline_ep": "<ep>", '
                '"blueprint_path": "channels/<key>/PRODUCTION-BLUEPRINT.md", '
                '"summary": "<2-3 sentences: what the locked recipe pins>", '
                '"invariants": ["<the always/never rules you locked>", ...], '
                '"files": ["<repo-relative paths you wrote/updated>", ...]}'
            )
        else:  # bringup
            brand = meta.get("brand") or {}
            # v19: the wizard already picked a starter template — its
            # blueprint_source is THE file to clone. The style mapping below
            # stays as fallback for jobs queued before the registry existed.
            tpl_meta = meta.get("template") or {}
            bsrc = str(tpl_meta.get("blueprint_source") or "").strip()
            clone_step = (
                (
                    f"STEP 2 — CLONE THE BLUEPRINT. This channel's template is "
                    f"'{tpl_meta.get('key')}'; clone {bsrc} as the skeleton for "
                    f"channels/{key}/PRODUCTION-BLUEPRINT.md, then adapt it to THIS "
                    "channel's brand (do not copy the source channel's topic/identity). "
                ) if bsrc else (
                    "STEP 2 — CLONE A BLUEPRINT FROM THE CHOSEN PRODUCTION STYLE. Read the brand's "
                    "production style and clone the CLOSEST existing channel blueprint as the "
                    f"skeleton for channels/{key}/PRODUCTION-BLUEPRINT.md, then adapt it to THIS "
                    "channel's brand (do not copy the source channel's topic/identity):\n"
                    "   - host-less / cinematic    -> channels/already-happening/PRODUCTION-BLUEPRINT.md\n"
                    "   - synthetic / avatar host  -> channels/claude-tricks/BRAND-BIBLE.md (avatar-host build)\n"
                    "   - illustrated / baked-text -> channels/pip-moonlit-garden/BRAND-BIBLE.md (baked-in text)\n"
                    "   - image-to-video / story   -> channels/aashiqana/SHORTS-TEMPLATE-LOCKED.md\n"
                    "   Pick the best fit from the production answer; if unclear, use host-less "
                    "cinematic. "
                )
            ) + (
                "The blueprint is a SKELETON for now (it gets frozen into the locked "
                "recipe after Ep01 is approved) — capture the beat spine, the asset recipe, the "
                "visual/audio identity, and the invariants, and clearly mark it 'DRAFT — locks "
                "after Ep01'.\n\n"
            )
            body = (
                f"You are BRINGING UP a brand-new YouTube channel, key '{key}'. It was just "
                "created in the factory wizard and is 'incubating': set up its home on disk so "
                "the app can immediately produce Episode 1 as a TEMP the creator will refine "
                "and then lock. Work ONLY inside channels/" + key + "/ (plus this job's result "
                "JSON) — never edit factory scripts or other channels.\n\n"
                f"THE CREATOR'S BRAND ANSWERS (machine-readable, from the wizard):\n"
                f"{json.dumps(brand, indent=2)[:3000]}\n\n"
                "STEP 1 — SCAFFOLD FILES:\n"
                f"  - channels/{key}/channel.json — key, name, and the normalized brand fields "
                "(niche, audience, format/aspect, runtime target, production style, tone, accent "
                "hex, made_for_kids from the audience answer, cadence). Add "
                "\"lifecycle\": \"incubating\".\n"
                f"  - channels/{key}/BRAND-BIBLE.md — the human-readable brand bible: vision, "
                "purpose, audience, voice/tone, visual identity (accent, type, grade), the "
                "format + cadence, and explicit do/don't rules. This is the channel's north "
                "star; write it well.\n\n"
                + clone_step +
                "STEP 3 — BRAND ASSETS: generate a channel icon and a banner consistent with the "
                f"accent + identity, into channels/{key}/brand/ (use in-house PIL/ffmpeg mocks or "
                "an existing gen_brand.py you can adapt as a NEW file under this channel — do not "
                "spend on blocked external generators). If you can only mock them, that's fine "
                "for incubation; note it.\n\n"
                "STEP 4 — REPORT (do NOT do) the owner wiring this channel still needs before it "
                "can arm on YouTube: the YouTube OAuth token for this channel and its "
                "UPLOAD_DEFAULTS entry (audience/made_for_kids/tags/description defaults). List "
                "exactly what the owner must add and where.\n\n"
                "STEP 5 — PROPOSE EPISODE 1: draft ONE production-ready Ep01 brief that fits the "
                "blueprint (a strong opening topic for this channel), so the app can auto-produce "
                "the TEMP. Title + a detailed brief (the beat outline + any facts to verify).\n\n"
                f"FINALLY write {out_json} (this JSON IS the job result — no manifest, no "
                "renders):\n"
                '{"phase": "bringup", "production_style": "<the style you cloned>", '
                '"cloned_from": "<source blueprint path>", '
                '"first_episode": {"title": "<Ep01 title>", "brief": "<production-ready Ep01 '
                'brief>"}, '
                '"wiring_report": "<the exact owner steps for the YouTube token + UPLOAD_DEFAULTS '
                'entry>", '
                '"assets": {"icon": "<path or \'mocked\'>", "banner": "<path or \'mocked\'>"}, '
                '"files": ["<repo-relative paths you created>", ...], '
                '"summary": "<2-3 sentences on what you set up>"}'
            )
    elif jtype == "analyze_and_suggest":
        body = (
            "You are the content strategist for this YouTube factory. "
            f"Read {ctx_path or '(context file missing)'} and docs/PRODUCTION-PLAYBOOK.md.\n"
            "STEP 1 -- RESEARCH: do real web research with WebSearch/WebFetch on what is "
            "working RIGHT NOW in each channel's niche (current trends, competitor formats, "
            "hooks). Cite what you actually found in each suggestion's reason.\n"
            "STEP 2 -- ANALYZE performance per channel (mind the ~48h analytics lag; small "
            "channels = judge by trend, not absolutes). The context file's video_summary "
            "section lists each channel's top/bottom videos (30d views + avg_view_pct) -- "
            "cite specific videos as evidence where relevant. RETENTION CURVES (primary signal): "
            "for each channel run `python scripts/yt_retention.py --channel <key> --days 30 "
            "--summary` and read the per-video 15s-hold and the 3 steepest drop_points -- a single "
            "avg_view_pct hides WHERE a video bleeds (claude-tricks Ep1 48% vs Ep2 71% was entirely "
            "a 15s-sustain gap, not the hook; the battle is 5-11s). Videos below YouTube's sample "
            "threshold return insufficient_data -- judge those by trend, never fabricate. Prefer "
            "format/hook changes that raise the 15s hold and remove any single >6pp early cliff. "
            "Decide: (a) which planned calendar "
            "items to alter or pull forward, (b) what NEW content each channel should produce "
            "next (2-4 content suggestions total across channels, premium-quality briefs "
            "consistent with each channel's guidelines), (c) how the FACTORY ITSELF should "
            "improve: 0-2 suggestions with kind 'factory' -- each a concrete generator "
            "create/update task that names the exact scripts/<file> (see the generator "
            "catalog in the context file).\n"
            f"Write {suggestions_path(job['id'])}: "
            '{"analysis_summary": str, '
            '"suggestions": [{"kind": "content"|"factory", '
            '"channel_key": str (factory items use "_network"), '
            '"planned_date": "YYYY-MM-DD" (may be today), "title": str, '
            '"brief": str (detailed, production-ready; factory items: the concrete generator '
            'create/update task naming scripts/<file>), '
            '"type": "produce_short"|"record_demo"|"custom" (factory items always "custom"), '
            '"model": str, "effort": str, '
            '"ultracode": bool, "reason": str (one crisp sentence citing the data or the '
            'research you found)}], '
            '"insights": {"<channel_key>": {"summary": str, "details": {"wins": [str], '
            '"risks": [str], "next": [str]}}}}\n'
            "This job is planning only -- do NOT produce any videos. "
            "Also write the usual manifest with files: []."
        )
    elif jtype == "suggest_brief":
        seed = f"SEED IDEA (build on it): {jprompt}\n" if jprompt else ""
        body = (
            f"You are the content strategist for the YouTube channel '{key}'.\n"
            f"Read {ctx_path or '(context file missing)'} (channel guidelines, last-14-day "
            "stats, recent job titles, upcoming calendar) and docs/PRODUCTION-PLAYBOOK.md.\n"
            "STEP 1 -- RESEARCH: use WebSearch/WebFetch to find what would perform NOW in "
            "this niche: current trends, hot formats and hooks, competitor angles.\n"
            "STEP 2 -- write ONE production-ready brief for the channel's next video, "
            "premium bar per docs/PRODUCTION-PLAYBOOK.md.\n"
            f"{seed}"
            f"Write {brief_path(job['id'])}: "
            '{"title": str, "brief": str (production-ready), "tags": [str, ...]}\n'
            "Planning only -- do NOT produce any videos and do NOT write a manifest."
        )
    elif jtype == "plan_content" and plan_style == "cinematic":
        # v17: idea engine for the "already-happening" cinematic channel. Grounded
        # speculation — every idea is a near-future-of-AI claim ANCHORED to a real,
        # dated capability today. Ranked list; each idea is a production-ready brief
        # the user can pick -> produce_channel (the animatic pipeline above).
        body = (
            f"You are the content strategist for 'already-happening' ('{key}'): a host-less "
            "CINEMATIC Shorts channel on the near future of AI. Thesis: the future isn't "
            "coming — it's already happening. Every episode anchors a +5yr claim to a REAL "
            "capability that exists TODAY (grounded speculation, never sci-fi fantasy). "
            "Electric-teal identity, ~28-40s, alternate wonder/provocation.\n"
            f"Read {ctx_path or '(context file missing)'} (guidelines, last-30d stats, recent "
            "episode titles, calendar) + channels/already-happening/PRODUCTION-BLUEPRINT.md + "
            "CHANNEL-SETUP.md.\n\n"
            "Produce a RANKED list of 5 ideas for the NEXT Short, each driven by ONE signal:\n"
            "1. ANALYTICS -- read the ctx stats (this channel is new; judge by TREND, never "
            "fabricate). Favour the spine that has held retention; propose a topic that plays "
            "to it.\n"
            "2. BREAKING NEWS -- WebSearch a REAL AI capability that shipped THIS WEEK "
            "(verified + dated); make it the TODAY anchor, then extrapolate 5yr. CITE source "
            "+ date in why_viral.\n"
            "3. NEW DOMAIN -- pick a life domain NOT yet covered (Ep01 transport, Ep02 jobs "
            "are done — so health, money, education, relationships, creativity, law, war, "
            "food, aging...); anchor it to a real deployed system today.\n"
            "4. UPCOMING EVENT -- from the calendar + today's date, a near-term hook (a launch, "
            "a deadline, a date) that pegs a grounded future claim.\n"
            "5. WILDCARD -- your single strongest bet, any angle.\n\n"
            "Every idea MUST fit the locked 6-beat spine (cold-open hook -> TODAY anchor -> "
            "+5yr extrapolation -> gut-punch -> binary button) and PASS the fact-check gate: "
            "the TODAY anchor MUST be a verifiable, dated, CONSERVATIVE fact (one wrong stat "
            "detonates the 'this is REAL' brand). VERIFY with WebSearch — never fabricate.\n"
            f"Write {plan_content_path(job['id'])}: "
            '{"ideas": [{"rank": int (1=best), '
            '"angle": "analytics"|"news"|"domain"|"event"|"wildcard", '
            '"title": str (provocation/curiosity, keyword front-loaded, 40-55 chars), '
            '"hook": str (the <=1.5s spoken cold-open line), '
            '"why_viral": str (1-2 sentences; cite the dated source that anchors it), '
            # BEAT SKELETON (2026-08-20): the planner emits the shot list as
            # BeatIntents so the visual library can propose a component per beat
            # BEFORE the money gate. pickCookbook (remotion-studio/src/cookbook/
            # registry.ts) ranks on exactly these fields, and its `keywords` are
            # documented as "free words from the script / plan" -- so this does
            # not need the final VO, which is written later inside the produce.
            # The vocabularies are CLOSED: an invented value ranks nothing.
            '"beats": [{"beat": "hook"|"context"|"stat"|"process"|"comparison"|"demo"'
            '|"punchline"|"cta"|"social-proof", '
            '"shows": str (one line: what is literally ON SCREEN in this beat), '
            '"needs": "series"|"metrics"|"single-number"|"facts"|"before-after"|"steps"|"options"'
            '|"dialogue"|"phrase"|"query-results"|"hub-spokes"|"ledger"|"part-whole"|"alerts"|"utterance" '
            '(the SHAPE of what is on screen, not the topic), '
            '"keywords": [str] (3-6 CONCRETE nouns this visual is about -- they are matched '
            'against a component library, so "budget, spending, category, total" ranks and '
            '"useful, clean, modern" ranks nothing)}] '
            '(3-6 beats IN ORDER; the LAST beat must be "cta"), '
            '"brief": str (production-ready: the 6-beat outline, the verified TODAY anchor + '
            'its source, and the 6 shot ideas -- enough for produce_channel to run)}]}\n'
            "Rank by viral potential. Planning only -- do NOT produce videos, do NOT write a manifest."
        )
    elif jtype == "plan_content" and plan_style == "blueprint":
        # v19: generic blueprint-driven idea engine for template channels with no
        # bespoke planner (new channels + aashiqana). Reads the channel's OWN
        # blueprint/brand files instead of assuming any specific format.
        body = (
            f"You are the content strategist for the YouTube channel '{key}'.\n"
            f"READ FIRST (this channel's law): channels/{key}/PRODUCTION-BLUEPRINT.md, "
            f"channels/{key}/BRAND-BIBLE.md, channels/{key}/channel.json, and "
            f"{ctx_path or '(context file missing)'} (guidelines, recent stats, episode "
            "titles, upcoming calendar).\n\n"
            "Produce a RANKED list of 5 ideas for the NEXT episode, each driven by ONE "
            "signal:\n"
            "1. ANALYTICS -- read the ctx stats (small/new channel: judge by TREND, never "
            "fabricate). Favour what has held retention so far.\n"
            "2. NICHE PULSE -- WebSearch what is working RIGHT NOW in this channel's "
            "niche (formats, hooks, competitor angles; verified + dated). CITE source + "
            "date in why_viral.\n"
            "3. FRESH GROUND -- a topic/angle the channel has NOT covered yet that fits "
            "the brand bible.\n"
            "4. UPCOMING EVENT -- from the calendar + today's date, a near-term peg (a "
            "launch, a date, a season) for a timely episode.\n"
            "5. WILDCARD -- your single strongest bet, any angle.\n\n"
            "Every idea MUST fit the channel's locked blueprint (beat spine, runtime, "
            "identity, invariants). VERIFY every factual claim with WebSearch -- never "
            "fabricate.\n"
            f"Write {plan_content_path(job['id'])}: "
            '{"ideas": [{"rank": int (1=best), '
            '"angle": "analytics"|"niche"|"fresh"|"event"|"wildcard", '
            '"title": str (YouTube title in this channel\'s voice), '
            '"hook": str (the cold-open line), '
            '"why_viral": str (1-2 sentences; cite the evidence/source/date), '
            # BEAT SKELETON (2026-08-20): the planner emits the shot list as
            # BeatIntents so the visual library can propose a component per beat
            # BEFORE the money gate. pickCookbook (remotion-studio/src/cookbook/
            # registry.ts) ranks on exactly these fields, and its `keywords` are
            # documented as "free words from the script / plan" -- so this does
            # not need the final VO, which is written later inside the produce.
            # The vocabularies are CLOSED: an invented value ranks nothing.
            '"beats": [{"beat": "hook"|"context"|"stat"|"process"|"comparison"|"demo"'
            '|"punchline"|"cta"|"social-proof", '
            '"shows": str (one line: what is literally ON SCREEN in this beat), '
            '"needs": "series"|"metrics"|"single-number"|"facts"|"before-after"|"steps"|"options"'
            '|"dialogue"|"phrase"|"query-results"|"hub-spokes"|"ledger"|"part-whole"|"alerts"|"utterance" '
            '(the SHAPE of what is on screen, not the topic), '
            '"keywords": [str] (3-6 CONCRETE nouns this visual is about -- they are matched '
            'against a component library, so "budget, spending, category, total" ranks and '
            '"useful, clean, modern" ranks nothing)}] '
            '(3-6 beats IN ORDER; the LAST beat must be "cta"), '
            '"brief": str (production-ready brief following the channel blueprint -- '
            'enough for produce_channel to run)}]}\n'
            "Rank by viral potential. Planning only -- do NOT produce videos, do NOT write a manifest."
        )
    elif jtype == "plan_content":
        # v17: the channel-page "Plan content" idea engine. Ranked list across 4
        # signals (analytics / Vaibhav-DNA / recent news / upcoming events). Each
        # idea carries a production-ready brief so the user can pick -> produce_channel.
        #
        # One Desk · Make: the owner may PASTE fresh rows out of YouTube Studio
        # before asking. That paste outranks everything else in the context file:
        # the Analytics API finalizes with ~48h lag and a 1-3 day old Short has no
        # rows at all, so the stored numbers can be flatly wrong about exactly the
        # videos the next idea should learn from.
        fresh = str((job.get("meta") or {}).get("fresh_numbers") or "").strip()
        fresh_block = (
            "FRESH NUMBERS, PASTED BY THE OWNER MINUTES AGO -- this is the newest and most\n"
            "trustworthy source you have. It OUTRANKS the stats in the context file and the\n"
            "Analytics API (both lag ~48h; the newest Shorts have no API rows at all). Read it\n"
            "as ground truth for the videos it names, and SAY in why_viral when an idea is\n"
            "driven by it:\n"
            f"<<<PASTED\n{fresh}\nPASTED\n\n"
        ) if fresh else ""
        body = (
            fresh_block +
            f"You are the content strategist for the AI Unpacked channel ('{key}': a premium "
            "AI-tips Short channel for GENERAL beginners; synthetic host Sol, magenta).\n"
            f"Read {ctx_path or '(context file missing)'} (guidelines, last-30d stats, recent "
            "episode titles, upcoming calendar) + docs/PRODUCTION-PLAYBOOK.md.\n\n"
            "Produce a RANKED list of 5 ideas for the NEXT Short, each driven by ONE signal:\n"
            "1. ANALYTICS -- run `python scripts/yt_retention.py --channel claude-tricks --days 30 "
            "--summary` and read the ctx stats. On this channel curriculum beats news ~3:1 on the "
            "15s hold and stacked demo beats bleed at 5-13s -> favour SINGLE-BEAT curriculum; "
            "propose a topic that plays to what actually holds retention.\n"
            "2. VAIBHAV-DNA -- competitor DNA (@vaibhavsisinty, verified): Stop-X + FREE + 2-emoji "
            "hook, ~28s, one concrete fix reaching the screen fast; propose a topic in that mold.\n"
            "3. RECENT NEWS -- WebSearch what is BREAKING in AI this week (verified + dated); a "
            "timely, beginner-relevant peg. CITE the source + date in why_viral.\n"
            "4. UPCOMING EVENT -- from the calendar + today's date, a near-term hook (e.g. "
            "Independence Day 15 Aug, a product launch, a price deadline); a tie-in for a viral peg.\n"
            "5. WILDCARD -- your single strongest bet, any angle.\n\n"
            "Every idea MUST fit the LOCKED Ep11/Ep12 template (single-beat how-to OR ranked "
            "countdown; a REAL on-screen demo; ~28s; Sol host). VERIFY every factual claim with "
            "WebSearch -- never fabricate.\n"
            f"Write {plan_content_path(job['id'])}: "
            '{"ideas": [{"rank": int (1=best), '
            '"angle": "analytics"|"vaibhav"|"news"|"event"|"wildcard", '
            '"title": str (YouTube title w/ emoji, Vaibhav-DNA hook grammar), '
            '"hook": str (the <=1.5s spoken hook line), '
            '"why_viral": str (1-2 sentences; cite the evidence/source/date), '
            # BEAT SKELETON (2026-08-20): the planner emits the shot list as
            # BeatIntents so the visual library can propose a component per beat
            # BEFORE the money gate. pickCookbook (remotion-studio/src/cookbook/
            # registry.ts) ranks on exactly these fields, and its `keywords` are
            # documented as "free words from the script / plan" -- so this does
            # not need the final VO, which is written later inside the produce.
            # The vocabularies are CLOSED: an invented value ranks nothing.
            '"beats": [{"beat": "hook"|"context"|"stat"|"process"|"comparison"|"demo"'
            '|"punchline"|"cta"|"social-proof", '
            '"shows": str (one line: what is literally ON SCREEN in this beat), '
            '"needs": "series"|"metrics"|"single-number"|"facts"|"before-after"|"steps"|"options"'
            '|"dialogue"|"phrase"|"query-results"|"hub-spokes"|"ledger"|"part-whole"|"alerts"|"utterance" '
            '(the SHAPE of what is on screen, not the topic), '
            '"keywords": [str] (3-6 CONCRETE nouns this visual is about -- they are matched '
            'against a component library, so "budget, spending, category, total" ranks and '
            '"useful, clean, modern" ranks nothing)}] '
            '(3-6 beats IN ORDER; the LAST beat must be "cta"), '
            '"brief": str (production-ready brief following the Ep11/Ep12 template -- enough for '
            'produce_channel to run)}]}\n'
            "Rank by viral potential. Planning only -- do NOT produce videos, do NOT write a manifest."
        )
    elif jtype == "channel_intake":
        # v18: channel-creation wizard -- suggest tailored options for one step.
        meta = job.get("meta") or {}
        ans = meta.get("answers") or {}
        question = str(meta.get("question") or "the next channel attribute")
        field = str(meta.get("field") or "value")
        body = (
            "You are helping a creator design a NEW YouTube channel in a step-by-step wizard.\n"
            f"Their answers so far (JSON): {json.dumps(ans)[:1600]}\n\n"
            f"CURRENT QUESTION: {question}\n"
            f"Suggest 4-6 SHORT, punchy, DISTINCT options the creator can tap to answer for "
            f"'{field}'. Tailor them to THIS specific channel idea -- never generic filler. Each "
            "option = a 2-5 word label + a one-line value (the actual answer text they'd pick).\n"
            "If the question is about competitors/references or production style, use WebSearch to "
            "ground the options in real, current examples (keep the value text clean, no URLs).\n"
            f"Write {channel_intake_path(job['id'])}: "
            '{"question": str (optional cleaner restatement), '
            '"options": [{"label": str (2-5 words), "value": str (one line)}], '
            '"ready_to_advance": true}\n'
            "Options only -- do NOT produce anything, no manifest, no renders."
        )
    elif jtype == "plan_assets":
        body = (
            f"You are the asset planner for channel {key} (staged production -- read "
            "docs/STAGED-PIPELINE.md and docs/PRODUCTION-PLAYBOOK.md first).\n\n"
            f"CHANNEL GUIDELINES:\n{guidelines or '(none on file)'}\n\n"
            f"EPISODE BRIEF:\n{jprompt}\n\n"
            "Design the complete asset list for this episode: EVERY visual and audio "
            "fragment the final video needs (thumbnail included) -- stills, clips, VO, "
            "music, bookends, overlays. 6-20 assets is typical.\n"
            f"Write {assets_plan_path(job['id'])}: "
            '{"summary": str, "assets": [{'
            '"asset_key": str (stable kebab/snake slug, e.g. "thumbnail", '
            '"scene_03_still", "vo_master"), '
            f'"group": "{"|".join(ASSET_GROUPS)}", '
            f'"kind": "{"|".join(ASSET_KINDS)}", '
            '"title": str (short human label), '
            '"spec": {"prompt": str (complete generation instructions for this ONE '
            'asset), "params": {} (concrete generator params)}, '
            '"effort": str (optional override), "model": str (optional override)}]}\n'
            "List assets in PRODUCTION STEP ORDER (research/script first, then audio, "
            "scenes, clips, overlays, thumbnail/bookends last) -- the dashboard shows "
            "them to the reviewer as numbered steps in exactly this order.\n"
            "This job PLANS only -- do NOT generate any media and do NOT write a manifest."
        )
    elif jtype == "generate_asset":
        a = asset or {}
        spec = a.get("spec") if isinstance(a.get("spec"), dict) else {}
        # entries are {'ts','notes'} dicts from the edge fn (plain strings tolerated)
        rev = [(r.get("notes") if isinstance(r, dict) else str(r)) or ""
               for r in (spec.get("revision_notes") or [])]
        rev = [r.strip() for r in rev if r.strip()]
        rev_block = ("REVISION NOTES (oldest first -- the LAST one is what THIS version "
                     "must fix):\n" + "\n".join(f"- {r}" for r in rev) + "\n\n") if rev else ""
        notes = str(a.get("notes") or "").strip()
        notes_block = f"REVIEWER FEEDBACK (verbatim):\n{notes}\n\n" if notes else ""
        out_dir = (RENDERS_OUT / "staged" / str(a.get("calendar_id") or "unknown")
                   / str(a.get("asset_key") or "asset") / f"v{a.get('version') or 1}")
        poster_rule = (" For this VIDEO asset also write a poster .jpg (one representative "
                       "frame, role 'poster') AND 3 frame stills -- start/middle/end -- "
                       "each listed with role 'frame', so the reviewer sees the piece "
                       "without playing it."
                       if a.get("kind") == "video" else "")
        if a.get("group_key") == "overlay":
            # Ep11 rule: overlap bugs only show composited -- a spec alone is unreviewable
            poster_rule = (" This is an OVERLAY asset: you MUST also render a composite "
                           "preview .jpg (role 'poster') showing the overlay ON TOP of the "
                           "actual frame/beat it will sit on in the final video (use the "
                           "episode's beat map / target stills). The reviewer judges "
                           "overlap ('chips never cover taught content' -- Ep11 rule) from "
                           "this composite, so it must be honest, not a mockup.")
        body = (
            f"Generate ONE staged production asset for channel {key} "
            "(docs/STAGED-PIPELINE.md).\n\n"
            f"ASSET: {a.get('asset_key')} v{a.get('version') or 1} -- "
            f"kind={a.get('kind') or 'image'}, group={a.get('group_key') or 'other'}"
            + (f", title: {a.get('title')}" if a.get("title") else "") + "\n\n"
            f"GENERATION SPEC:\n{spec.get('prompt') or '(spec has no prompt)'}\n\n"
            f"SPEC PARAMS:\n{json.dumps(spec.get('params') or {}, indent=2)}\n\n"
            f"{rev_block}{notes_block}"
            f"CHANNEL GUIDELINES:\n{guidelines or '(none on file)'}\n\n"
            f"Apply the kind-specific quality rules for {a.get('kind') or 'image'} assets "
            "from docs/PRODUCTION-PLAYBOOK.md (premium bar; use the repo's existing "
            "generator scripts where they fit).\n"
            f"Generate exactly ONE primary file under {out_dir}/ ."
            f"{poster_rule}\n"
            f"When done, write {asset_out_path(job['id'])}: "
            '{"summary": str, "review_note": str, "files": [{"path": abs or repo-rel path, '
            '"role": "asset"|"poster"|"frame"}]}\n'
            "review_note is the reviewer's cheat-sheet shown in the dashboard: 2-5 short "
            "markdown bullets -- what this asset is, exactly what to check before "
            "approving, and any judgment calls you made. Essential for long text assets "
            "(scripts, research docs) so the human can review at a glance.\n"
            "This job produces ONE fragment only -- NO assembly, NO uploads, NO posts, "
            "NO manifest.\n"
            "PARALLEL WORKERS: other asset jobs may be running concurrently. If your "
            "asset records via a shared .browser-profiles/<site> profile and the "
            "launch dies on SingletonLock ('profile is already in use'), another job "
            "holds it -- WAIT for it (poll `pgrep -f 'user-data-dir=.*browser-profiles/"
            "<site>'` every 5s, up to ~10 min) instead of failing or killing the other "
            "job's browser."
        )
        # ---- Host-wardrobe lock (claude-tricks avatar) ----
        # Staged host clips (hook/setup/payoff) each run as their OWN job; nothing here
        # pinned the outfit, so clips diverged or each fell back to the stale global
        # host_canonical (the "very old host image" + "inconsistent intro->outro" glitch,
        # 2026-08-06). Pin ONE outfit per episode (deterministic by calendar_id; pick() is
        # pure file-ops, no network) and forbid the canonical fallback in every host agent.
        _ak = str(a.get("asset_key") or "").lower()
        if key == "claude-tricks" and "host" in _ak and a.get("kind") == "video":
            _epk = str(a.get("calendar_id") or job["id"])
            try:
                import host_outfit
                _o = host_outfit.pick(_epk)
                body += (
                    "\n\nHOST WARDROBE -- MANDATORY, DO NOT DEVIATE:\n"
                    f"This episode's LOCKED outfit is '{_o['name']}'. Every host clip in this "
                    "episode (hook, setup, payoff) MUST wear this same outfit. Register/reuse its "
                    f"HeyGen id with `python scripts/host_outfit.py --register {_epk}` (idempotent, "
                    "free) and drive scripts/heygen_avatar.py with that talking_photo_id. Face "
                    f"source = {_o.get('center')}. NEVER use host_canonical or the global "
                    "channels/claude-tricks/assets/character/.heygen_photo_id -- that is the OLD "
                    "host. If registration fails, STOP and surface it; do NOT fall back to the "
                    "canonical (a mismatched host is worse than a blocked asset)."
                )
            except Exception as _e:
                body += (
                    "\n\nHOST WARDROBE -- MANDATORY: select ONE outfit for this whole episode via "
                    "scripts/host_outfit.py (pick + --register) and use it for every host clip; "
                    "NEVER use host_canonical / the global .heygen_photo_id (the OLD host). "
                    f"[auto-pin unavailable: {str(_e)[:100]}]"
                )
    elif jtype == "assemble_episode":
        body = (
            f"Assemble the FINAL episode video for channel {key} (staged production -- "
            "docs/STAGED-PIPELINE.md).\n"
            f"Read {ctx_path or '(context file missing)'}: the calendar item, the channel "
            "guidelines and every approved asset (latest version) with its local_path on "
            "this machine.\n"
            "Assemble the final video FROM THOSE LOCAL FILES using the repo's existing "
            "generator/assembly scripts and the locked params in "
            "docs/PRODUCTION-PLAYBOOK.md. Do NOT regenerate approved assets -- only glue "
            "work (cuts, transitions, audio mix, timing) is allowed here.\n"
            + (f"JOB BRIEF:\n{jprompt}\n\n" if jprompt else "")
            + "STANDING RULES: follow docs/PRODUCTION-PLAYBOOK.md, premium quality bar.\n"
            "PREMIUM GATE (v12) -- MEASURE each of these on the finished file and abort "
            "(fix and re-render) on any failure; write the measured values into the "
            "manifest under 'qc':\n"
            "  1. Opening title/cover card HOLDS 2.5-4.0s from frame zero, over a calm "
            "frame (frame-diff the card window to prove it is static).\n"
            "  2. The host appears ON CAMERA (full-frame or split) within the first 8s.\n"
            "  3. Every information-carrying overlay chip holds >= 1.5s; chips sit in "
            "dead space, never over taught content (Ep11 rule).\n"
            "  4. Integrated loudness within 0.3 LU of the channel's last shipped "
            "master (ffmpeg ebur128; playbook section 3 gate).\n"
            "  5. If the brief/script defines a comment KEYWORD CTA, the end-card must "
            "carry that exact keyword visually, not a generic 'comment' card, and the "
            "uploaded description must include it too.\n"
            "  6. Total duration within the brief's target; end-card + sting <= 4s "
            "combined.\n"
            "A cut that fails the gate is NOT delivered -- the gate exists because a "
            "shipped cut once lost its title card in ~1s and dropped its keyword CTA."
        )
    elif jtype == "preview_episode":
        body = (
            f"Build a fast DRAFT PREVIEW of the episode for channel {key} (staged "
            "production -- docs/STAGED-PIPELINE.md). This is NOT the final render: the "
            "human uses it to judge, before assembly, what would actually go out on "
            "YouTube -- beat order, timing, overlays over content, audio sync.\n"
            f"Read {ctx_path or '(context file missing)'}: the calendar item, channel "
            "guidelines and every current asset (latest approved or in-review version) "
            "with its local_path on this machine.\n"
            "Stitch those LOCAL FILES into one draft video with the episode's real beat "
            "structure (use the beat map / script assets). SPEED over polish: 540x960, "
            "-preset ultrafast, -crf 30, skip mastering/loudnorm, and burn a small "
            "'DRAFT' watermark in a corner. Do NOT regenerate any asset.\n"
            f"When done, write {preview_out_path(job['id'])}: "
            '{"summary": str, "file": path to the draft .mp4}\n'
            "NO manifest, NO posts -- this draft is never published."
        )
    else:  # custom (and any unknown type)
        body = f"{jprompt}\n\nRepo: this factory. Follow docs/PRODUCTION-PLAYBOOK.md conventions."

    manifest = (
        "When fully done, write a manifest JSON to "
        f"{manifest_path(job['id'])}: "
        '{"summary": str, "files": [{"path": abs or repo-rel path, '
        '"kind": "video|image|audio|other", "channel_key": str, '
        '"yt_title": str (optional -- ready-to-publish YouTube title, <=100 chars), '
        '"yt_description": str (optional), "yt_tags": [str, ...] (optional), '
        '"contributors": [{"generator": "scripts/<file>.py basename", "role": short human '
        'phrase like "karaoke captions" or "intro/outro bookends"}] (optional)}], '
        f'"recap": {RECAP_SCHEMA}}}. '
        "Only list final deliverables. Each VIDEO becomes a draft YouTube post, so give "
        "videos yt_title/yt_description/yt_tags and credit every generator script that "
        "contributed to each file. The recap is YOUR honest production diary of this run: "
        "the real steps you took, the real choices you made and why, and the real problems "
        "you hit and how you resolved or worked around them -- specific, never fluff "
        "(issues/next may be empty if genuinely none); recap.outputs mirrors the final "
        "deliverables, one short note phrase each."
    )
    if jtype in ("suggest_brief", "plan_content", "plan_assets", "generate_asset", "preview_episode",
                 "channel_intake"):
        prompt = body  # structured-result jobs: their own JSON only, no manifest / renders
    else:
        prompt = f"{body}\n\n{manifest}"
    if job.get("ultracode"):
        # opts the headless run into multi-agent orchestration
        prompt = "ultracode\n" + prompt
    return prompt


def map_model(model):
    """Dashboard model name -> claude CLI model id (fable -> claude-fable-5, rest pass through)."""
    m = (model or "opus").strip()
    return MODEL_MAP.get(m, m)


def claude_argv(*args):
    """Argv to invoke the Claude CLI, cross-platform. On Windows an npm-installed
    `claude` is a .cmd/.bat shim that CreateProcess can't launch from a list, so
    wrap it in `cmd /c`; a native claude.exe (or POSIX) is called directly."""
    claude_bin = shutil.which("claude") or "claude"
    argv = [claude_bin, *args]
    if IS_WINDOWS and str(claude_bin).lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", *argv]
    return argv


def build_command(job, prompt):
    return claude_argv(
        "-p", prompt,
        "--model", map_model(job.get("model")),
        "--effort", job.get("effort") or "high",
        "--output-format", "stream-json",
        "--verbose",
        "--permission-mode", "acceptEdits",
        "--allowedTools", ALLOWED_TOOLS,
        "--chrome",  # real-Chrome tools (Suno flows etc.); requires Chrome open
    )


def apply_global_override(supa, job):
    """v13 (2026-08-07): global model/effort override. When factory_settings
    override_enabled='1', EVERY job runs with override_model / override_effort
    instead of the model/effort it was queued with. Turned off (default, or the
    key absent) -> each job keeps its own. Best-effort: a settings-read failure
    never blocks a job — it just runs with its queued model/effort."""
    try:
        rows = supa.select(
            "factory_settings",
            "key=in.(override_enabled,override_model,override_effort)&select=key,value",
        )
        s = {r["key"]: r.get("value") for r in (rows or [])}
        if str(s.get("override_enabled") or "0") == "1":
            if s.get("override_model"):
                job["model"] = s["override_model"]
            if s.get("override_effort"):
                job["effort"] = s["override_effort"]
    except Exception as e:  # noqa: BLE001 -- override is convenience, never a gate
        log(f"  global override read failed (job keeps its own model/effort): {e}")
    return job


# ---------------------------------------------------------------- job execution


def render_line(raw, buf=None):
    """Turn one stream-json stdout line into a short human-readable log line (or None to skip).
    v16: when a `result` event carries `total_cost_usd` + `usage` (input_tokens,
    output_tokens, cache_creation_input_tokens, cache_read_input_tokens), splat
    them onto buf.usage so run_job can attach them to factory_jobs.result. This
    is the only place the Anthropic CLI emits real per-run cost + token totals
    for a claude -p session."""
    raw = raw.rstrip("\n")
    if not raw.strip():
        return None
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw[:800]
    t = obj.get("type")
    if t == "system":
        sub = obj.get("subtype", "")
        if sub == "init":
            return f"[system:init] model={obj.get('model', '?')}"
        if sub == "thinking_tokens":
            return "[thinking…]"  # private reasoning in progress; no per-event model field exists
        return f"[system:{sub}]"
    if t == "assistant":
        parts = []
        for block in (obj.get("message") or {}).get("content", []):
            bt = block.get("type")
            if bt == "text" and block.get("text", "").strip():
                parts.append(block["text"].strip())
            elif bt == "tool_use":
                try:
                    inp = json.dumps(block.get("input", {}))[:200]
                except (TypeError, ValueError):
                    inp = "?"
                parts.append(f"[tool:{block.get('name', '?')}] {inp}")
        return "\n".join(parts) or None
    if t == "result":
        u = obj.get("usage") or {}
        # v16: capture the CLI's own numbers so factory_jobs.result carries usage
        if buf is not None:
            buf.usage = {
                "cost_usd": obj.get("total_cost_usd"),
                "input_tokens": u.get("input_tokens"),
                "output_tokens": u.get("output_tokens"),
                "cache_read_input_tokens": u.get("cache_read_input_tokens"),
                "cache_creation_input_tokens": u.get("cache_creation_input_tokens"),
                "num_turns": obj.get("num_turns"),
                "duration_ms": obj.get("duration_ms"),
                "subtype": obj.get("subtype"),
            }
        return (f"[result:{obj.get('subtype', '')}] turns={obj.get('num_turns', '?')} "
                f"duration_ms={obj.get('duration_ms', '?')} "
                f"cost_usd={obj.get('total_cost_usd', '?')} "
                f"in={u.get('input_tokens', '?')} out={u.get('output_tokens', '?')} "
                f"cache_r={u.get('cache_read_input_tokens', '?')} "
                f"cache_w={u.get('cache_creation_input_tokens', '?')}")
    return None  # tool results ("user" turns) etc. are too noisy for the dashboard


class LogBuffer:
    def __init__(self):
        self._lines = []
        self._lock = threading.Lock()
        self.dirty = False
        # v16: filled by render_line() on the CLI's `result` event
        self.usage = None

    def add(self, line):
        with self._lock:
            if line == "[thinking…]" and self._lines and self._lines[-1].startswith("[thinking"):
                n = self._lines[-1].count("×")
                self._lines[-1] = f"[thinking… ×{n + 2}]" if n == 0 else f"[thinking… ×{int(self._lines[-1].split('×')[1].rstrip(']')) + 1}]"
            else:
                self._lines.append(line)
            self.dirty = True

    def text(self):
        with self._lock:
            full = "\n".join(self._lines)
        if len(full.encode("utf-8", "replace")) > LOG_CAP_BYTES:
            full = "...[log truncated to last 200KB]...\n" + full[-LOG_CAP_BYTES:]
        return full


def probe_duration(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=30)
        return round(float(out.stdout.strip()), 2)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def kind_for(path, declared):
    if declared in ("video", "image", "audio", "other"):
        return declared
    ext = path.suffix.lower()
    if ext in (".mp4", ".mov", ".webm", ".mkv"):
        return "video"
    if ext in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        return "image"
    if ext in (".mp3", ".wav", ".m4a", ".aac", ".flac"):
        return "audio"
    return "other"


def norm_generator(name):
    """Contributor generator names match factory_generators.name: '<file>.py'."""
    n = str(name or "").strip()
    if n.startswith("scripts/"):
        n = n[len("scripts/"):]
    if n and "." not in n:
        n += ".py"
    return n


def default_publish_at(supa, job):
    """v8: prefill the draft's publish slot so calendar-planned content never
    sits waiting on a manual date pick. Slot = the linked calendar item's
    planned_date (join via job_id) at factory_settings.default_publish_time
    (local auto_sync_tz; default 16:00 IST = the network's standard 10:30Z
    slot); no calendar item -> the next upcoming slot. Always clamped to the
    future — YouTube rejects a past publishAt. Returns an ISO UTC string."""
    from zoneinfo import ZoneInfo
    hour, minute, tzname = 16, 0, "Asia/Kolkata"
    try:
        cfg = {r["key"]: r["value"] for r in supa.select(
            "factory_settings", "key=in.(default_publish_time,auto_sync_tz)&select=key,value")}
        tzname = cfg.get("auto_sync_tz") or tzname
        m = re.fullmatch(r"(\d{1,2}):(\d{2})", (cfg.get("default_publish_time") or "").strip())
        if m:
            hour, minute = int(m.group(1)), int(m.group(2))
    except (RuntimeError, requests.RequestException):
        pass
    try:
        tz = ZoneInfo(tzname)
    except (KeyError, ValueError):
        tz = ZoneInfo("Asia/Kolkata")
    planned = None
    if job.get("id"):
        try:
            cal = supa.select("factory_calendar",
                              f"job_id=eq.{job['id']}&select=planned_date&limit=1")
            if cal and cal[0].get("planned_date"):
                planned = date.fromisoformat(str(cal[0]["planned_date"])[:10])
        except (RuntimeError, requests.RequestException, ValueError):
            pass
    now = datetime.now(tz)
    d = planned or now.date()
    slot = datetime(d.year, d.month, d.day, hour, minute, tzinfo=tz)
    while slot <= now:
        slot += timedelta(days=1)
    return slot.astimezone(timezone.utc).isoformat()


def make_post_draft(supa, job, entry, p, channel_key, render_id):
    """v4: every uploaded VIDEO becomes a DRAFT factory_posts row (audience/synthetic
    prefilled from UPLOAD_DEFAULTS; v8 also prefills publish_at from the calendar
    slot; user edits + arms it on the dashboard). Returns 1 on success, 0 otherwise."""
    defaults = UPLOAD_DEFAULTS.get(channel_key, {})
    row = {
        "channel_key": channel_key,
        "render_id": render_id,
        "job_id": job["id"],
        "local_path": str(p),
        "yt_title": (entry.get("yt_title") or job.get("title") or p.stem)[:100],
        "yt_description": entry.get("yt_description") or "",
        "tags": entry.get("yt_tags") or [],
        "audience": defaults.get("audience"),
        "synthetic": bool(defaults.get("synthetic")),
        "publish_at": default_publish_at(supa, job),
    }
    # v12: non-blocking heads-up at DRAFT time -- the human sees slot/duplicate
    # warnings on the card BEFORE arming (the publish preflight enforces later)
    try:
        early = preflight_post_warnings(supa, {**row, "id": None}, check_youtube=False)
        if early:
            row["error"] = ("HEADS-UP (not blocking; publish preflight will "
                            "re-check):\n- " + "\n- ".join(early))[:8000]
    except Exception as e:  # noqa: BLE001
        log(f"  draft preflight failed (continuing): {e}")
    try:
        created = supa.insert_returning("factory_posts", [row])
        post_id = created[0]["id"] if created else None
        supa.insert("factory_events", [{
            "kind": "post_draft",
            "message": f"draft post for {channel_key}: {row['yt_title']!r} ({p.name})",
            "meta": {"post_id": post_id, "job_id": job["id"], "render_id": render_id,
                     "channel_key": channel_key},
        }])
        log(f"  draft post {post_id} created for {p.name}")
        return 1
    except (RuntimeError, requests.RequestException) as e:
        log(f"  post draft failed for {p.name}: {e}")
        return 0


def upload_manifest_files(supa, job, manifest):
    """Upload deliverables to storage; register factory_renders (+ local_path), credit
    factory_render_contributors, and draft a factory_posts row per video.
    Returns (uploaded, drafts)."""
    uploaded = drafts = 0
    for entry in manifest.get("files", []):
        try:
            p = Path(entry.get("path", ""))
            if not p.is_absolute():
                p = REPO / p
            if not p.exists():
                log(f"  manifest file missing on disk, skipped: {p}")
                continue
            channel_key = entry.get("channel_key") or job.get("channel_key") or "unassigned"
            storage_path = f"{channel_key}/{job['id']}/{p.name}"
            ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
            kind = kind_for(p, entry.get("kind"))
            data = p.read_bytes()
            supa.upload(storage_path, data, ctype)
            created = supa.insert_returning("factory_renders", [{
                "channel_key": channel_key,
                "job_id": job["id"],
                "filename": p.name,
                "storage_path": storage_path,
                "kind": kind,
                "size_bytes": len(data),
                "duration_s": probe_duration(p) if kind in ("video", "audio") else None,
                "local_path": str(p),
            }])
            render_id = created[0]["id"] if created else None
            uploaded += 1
            log(f"  uploaded {storage_path} ({len(data)} bytes)")
            contribs = [{"render_id": render_id,
                         "generator": norm_generator(c.get("generator")),
                         "role": str(c.get("role") or "")}
                        for c in (entry.get("contributors") or [])
                        if isinstance(c, dict) and c.get("generator")]
            if render_id and contribs:
                try:
                    supa.insert("factory_render_contributors", contribs)
                    log(f"  credited {len(contribs)} contributor(s) for {p.name}")
                except (RuntimeError, requests.RequestException) as e:
                    log(f"  contributor insert failed for {p.name}: {e}")
            # v16 gap-2: a produce_preview job's video IS the unmastered preview
            # raw — it must reach Studio as a render (above) but must NEVER become
            # an armable factory_posts row (arming it would publish the unmastered
            # cut). The mastered master + its scheduled post come later, from
            # scripts/finalize_episode.py. So skip drafting a post for previews.
            if kind == "video" and job.get("type") != "produce_preview":
                drafts += make_post_draft(supa, job, entry, p, channel_key, render_id)
        except (RuntimeError, requests.RequestException, OSError) as e:
            log(f"  upload failed for {entry}: {e}")
    return uploaded, drafts


# ---------------------------------------------------------------- v2: calendar + analytics + suggestions


def mark_calendar_produced(supa, job_id):
    """Any calendar item pointing at this finished job flips to 'produced' (no-op if none)."""
    try:
        supa.patch("factory_calendar", f"job_id=eq.{job_id}", {"status": "produced"})
    except (RuntimeError, requests.RequestException) as e:
        log(f"  could not mark calendar item produced for job {job_id}: {e}")


def display_to_key(display_name):
    """Map a history.csv DISPLAY channel name to a factory channel key (None if unmatched)."""
    low = (display_name or "").lower()
    for needles, key in DISPLAY_MAP:
        if any(n in low for n in needles):
            return key
    return None


def aggregate_history():
    """history.csv -> factory_stats rows: one per (channel_key, date) with summed views,
    max subs and the raw per-video array. Returns (rows, unmatched_display_names)."""
    agg, unmatched = {}, set()
    with open(HISTORY_CSV, newline="") as f:
        for row in csv.DictReader(f):
            key = display_to_key(row.get("channel"))
            if not key:
                unmatched.add(row.get("channel") or "(blank)")
                continue
            a = agg.setdefault((key, row["date"]), {"views": 0, "subs": 0, "raw": []})
            a["views"] += int(row.get("views") or 0)
            a["subs"] = max(a["subs"], int(row.get("subs") or 0))
            a["raw"].append({
                "video_id": row.get("video_id"), "title": row.get("title"),
                "privacy": row.get("privacy"), "publish_at": row.get("publish_at"),
                "views": int(row.get("views") or 0), "likes": int(row.get("likes") or 0),
                "comments": int(row.get("comments") or 0),
            })
    rows = [{"channel_key": k, "date": d, "views": a["views"], "subs": a["subs"], "raw": a["raw"]}
            for (k, d), a in sorted(agg.items())]
    return rows, unmatched


# ---------------------------------------------------------------- v5: per-video daily stats


VIDEO_STATS_DAYS = 30
ANALYTICS_METRICS = ("views,estimatedMinutesWatched,averageViewDuration,"
                     "averageViewPercentage,subscribersGained,likes,comments,shares")
# 5 videos x 31 days = max 155 rows per query -- safely under any Analytics API
# result cap. (startIndex paging silently drops rows on video,day reports, so
# chunking the video filter is the only reliable way to stay complete.)
VIDEO_FILTER_CHUNK = 5


def yt_creds(token_file):
    """Load one channel's OAuth creds from secrets/<token_file> (absolute path),
    refreshing if stale. NEVER interactive -- a missing/dead token raises instead
    of opening a browser (re-auth is a manual, human step)."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    tp = REPO / "secrets" / token_file
    if not tp.exists():
        raise RuntimeError(f"token file missing: {tp}")
    creds = Credentials.from_authorized_user_file(str(tp))
    if not creds.valid:
        if not creds.refresh_token:
            raise RuntimeError(f"token invalid and not refreshable: {tp}")
        creds.refresh(Request())
        tp.write_text(creds.to_json())
    return creds


def history_video_index():
    """history.csv -> (titles {video_id: title}, prev {video_id: latest pre-today
    lifetime snapshot {date, views, likes, comments}}) for v5 title lookups and
    fallback baselines."""
    titles, prev = {}, {}
    if not HISTORY_CSV.exists():
        return titles, prev
    today = datetime.now().strftime("%Y-%m-%d")  # history.csv dates are local
    with open(HISTORY_CSV, newline="") as f:
        for row in csv.DictReader(f):
            vid = row.get("video_id")
            if not vid:
                continue
            if row.get("title"):
                titles[vid] = row["title"]
            if row.get("date", "") < today and (vid not in prev or row["date"] > prev[vid]["date"]):
                prev[vid] = {"date": row["date"], "views": int(row.get("views") or 0),
                             "likes": int(row.get("likes") or 0),
                             "comments": int(row.get("comments") or 0)}
    return titles, prev


def channel_video_ids(yt):
    """All video ids in the authorized channel's uploads playlist (Data API)."""
    ch = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, page = [], None
    while True:
        pl = yt.playlistItems().list(part="contentDetails", playlistId=uploads,
                                     maxResults=50, pageToken=page).execute()
        ids += [i["contentDetails"]["videoId"] for i in pl.get("items", [])]
        page = pl.get("nextPageToken")
        if not page:
            break
    return ids


def _iso_dur_to_s(iso):
    """ISO-8601 PT#H#M#S (YouTube contentDetails.duration) -> seconds, or None."""
    if not iso:
        return None
    m = re.match(r"P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?$", iso)
    if not m:
        return None
    d, h, mi, s = (float(x) if x else 0.0 for x in m.groups())
    return int(d * 86400 + h * 3600 + mi * 60 + s)


def video_meta(yt, ids):
    """Data API videos.list -> {video_id: {title, views, likes, comments, duration_s}}
    (titles for both paths, lifetime totals for the fallback path; duration_s maps
    the ~3s/~15s retention gates onto the elapsed-time-ratio curve)."""
    meta = {}
    for i in range(0, len(ids), 50):
        vr = yt.videos().list(part="snippet,statistics,contentDetails",
                              id=",".join(ids[i:i + 50])).execute()
        for v in vr.get("items", []):
            st = v.get("statistics", {})
            meta[v["id"]] = {"title": v["snippet"]["title"],
                             "views": int(st.get("viewCount", 0) or 0),
                             "likes": int(st.get("likeCount", 0) or 0),
                             "comments": int(st.get("commentCount", 0) or 0),
                             "duration_s": _iso_dur_to_s(
                                 (v.get("contentDetails") or {}).get("duration"))}
    return meta


def fetch_video_analytics(yta, video_ids, start, end):
    """Analytics API v2: per-video per-day rows for the window, chunked by
    VIDEO_FILTER_CHUNK ids per query (multi-value video filter + video dimension).
    Row order: video, day, then ANALYTICS_METRICS."""
    rows = []
    for i in range(0, len(video_ids), VIDEO_FILTER_CHUNK):
        chunk = video_ids[i:i + VIDEO_FILTER_CHUNK]
        r = yta.reports().query(
            ids="channel==MINE", startDate=str(start), endDate=str(end),
            metrics=ANALYTICS_METRICS, dimensions="video,day",
            filters="video==" + ",".join(chunk), sort="day", maxResults=200).execute()
        rows += r.get("rows") or []
    return rows


def analytics_to_rows(key, arows, meta, titles_hist):
    """Analytics API rows -> factory_video_stats rows (source='analytics_api')."""
    rows = []
    for r in arows:
        if not isinstance(r, list) or len(r) < 10:
            continue
        vid = r[0]
        rows.append({
            "channel_key": key, "video_id": vid, "date": r[1],
            "title": (meta.get(vid) or {}).get("title") or titles_hist.get(vid),
            "views": int(r[2] or 0),
            "watch_minutes": r[3],
            "avg_view_duration_s": r[4],
            "avg_view_pct": r[5],
            "subs_gained": int(r[6] or 0),
            "likes": int(r[7] or 0),
            "comments": int(r[8] or 0),
            "shares": int(r[9] or 0),
            "source": "analytics_api",
            # window signals: NULL on every row; attach_window_signals() overwrites
            # the latest daily row per video. Kept on ALL rows so the bulk insert
            # payload stays homogeneous (PostgREST needs consistent columns).
            "shorts_pct": None, "traffic_mix": None,
            "hold_3s": None, "hold_15s": None,
        })
    return rows


def fetch_video_traffic(yta, video_ids, start, end):
    """Analytics API: per-video window views split by insightTrafficSourceType.
    -> {video_id: {SOURCE: views}}. Chunked by VIDEO_FILTER_CHUNK. Best-effort:
    a failed chunk is skipped (traffic mix is a nice-to-have, never fails a sync)."""
    out = {}
    for i in range(0, len(video_ids), VIDEO_FILTER_CHUNK):
        chunk = video_ids[i:i + VIDEO_FILTER_CHUNK]
        try:
            r = yta.reports().query(
                ids="channel==MINE", startDate=str(start), endDate=str(end),
                metrics="views", dimensions="video,insightTrafficSourceType",
                filters="video==" + ",".join(chunk), maxResults=500).execute()
        except Exception:  # noqa: BLE001 -- best-effort
            continue
        for row in r.get("rows") or []:
            if not isinstance(row, list) or len(row) < 3:
                continue
            vid, src, views = row[0], row[1], int(row[2] or 0)
            out.setdefault(vid, {})[src] = out.setdefault(vid, {}).get(src, 0) + views
    return out


def _hold_at(rows, sec, dur):
    """rows = [[elapsed_ratio, watch_ratio], ...]; nearest watch_ratio to sec/dur."""
    if not rows or not dur:
        return None
    tgt = sec / dur
    p = min(rows, key=lambda x: abs(x[0] - tgt))
    return round(p[1], 4)


def fetch_video_holds(yta, video_ids, meta, start, end):
    """Analytics API: per-video audience-retention curve (elapsedVideoTimeRatio)
    -> {video_id: {hold_3s, hold_15s}}, the watch ratio nearest the 3s hook gate
    and the 15s sustained-distribution gate. One query per video (the only reliable
    shape for elapsedVideoTimeRatio). Best-effort per video: YouTube withholds
    low-sample curves and 400s some videos -> that video simply gets no holds."""
    out = {}
    for vid in video_ids:
        dur = (meta.get(vid) or {}).get("duration_s")
        if not dur:
            continue
        try:
            r = yta.reports().query(
                ids="channel==MINE", startDate=str(start), endDate=str(end),
                metrics="audienceWatchRatio", dimensions="elapsedVideoTimeRatio",
                filters=f"video=={vid}", sort="elapsedVideoTimeRatio").execute()
        except Exception:  # noqa: BLE001 -- best-effort per video
            continue
        rows = [[float(x[0]), float(x[1])] for x in (r.get("rows") or [])
                if isinstance(x, list) and len(x) >= 2]
        if not rows:
            continue
        out[vid] = {"hold_3s": _hold_at(rows, 3, dur),
                    "hold_15s": _hold_at(rows, 15, dur)}
    return out


def attach_window_signals(rows, traffic, holds):
    """Stamp per-video window signals (shorts_pct, traffic_mix, hold_3s, hold_15s)
    onto the LATEST daily row per video, so the video_summary edge query picks them
    up via array_agg(order by date desc). Mutates `rows` in place."""
    latest = {}  # video_id -> the row with the max date
    for r in rows:
        vid = r.get("video_id")
        if not vid:
            continue
        cur = latest.get(vid)
        if cur is None or str(r.get("date") or "") > str(cur.get("date") or ""):
            latest[vid] = r
    for vid, r in latest.items():
        mix = traffic.get(vid)
        if mix:
            total = sum(mix.values())
            r["traffic_mix"] = mix
            r["shorts_pct"] = round(mix.get("SHORTS", 0) / total * 100, 1) if total else None
        h = holds.get(vid)
        if h:
            r["hold_3s"] = h.get("hold_3s")
            r["hold_15s"] = h.get("hold_15s")


def fallback_rows(supa, key, meta, hist_prev, today):
    """v5 fallback (token lacks an analytics scope): Data API lifetime totals ->
    daily deltas vs the previous stored day. Baseline preference: the channel's
    latest prior factory_video_stats fallback row (raw.lifetime), else the last
    pre-today history.csv snapshot. First-ever sighting seeds with the lifetime
    total and marks raw.baseline=true. Only views/likes/comments are available;
    watch/retention/subs/shares stay null."""
    base = {}
    try:
        stored = supa.select(
            "factory_video_stats",
            f"channel_key=eq.{key}&source=eq.data_api_fallback&date=lt.{today}"
            f"&select=video_id,date,raw&order=date.desc&limit=1000")
        for r in stored:
            life = (r.get("raw") or {}).get("lifetime")
            if r["video_id"] not in base and isinstance(life, dict):
                base[r["video_id"]] = life
    except (RuntimeError, requests.RequestException):
        pass
    rows = []
    for vid, m in meta.items():
        prev = base.get(vid) or hist_prev.get(vid)
        raw = {"lifetime": {"views": m["views"], "likes": m["likes"], "comments": m["comments"]}}
        if prev is None:
            views, likes, comments = m["views"], m["likes"], m["comments"]
            raw["baseline"] = True
        else:
            views = max(0, m["views"] - int(prev.get("views") or 0))
            likes = max(0, m["likes"] - int(prev.get("likes") or 0))
            comments = max(0, m["comments"] - int(prev.get("comments") or 0))
        rows.append({"channel_key": key, "video_id": vid, "date": str(today),
                     "title": m["title"], "views": views, "likes": likes,
                     "comments": comments, "source": "data_api_fallback", "raw": raw})
    return rows


def build_snapshot_rows(key, meta, rows, sync_at, source):
    """v12: one factory_video_snapshots row per video for this channel, stamped
    with the run's single sync_at. Lifetime views/likes/comments come from `meta`
    (Data API -- clean on BOTH sources, so sync-to-sync deltas are meaningful even
    on the fallback path). window_views/window_days/avg_view_pct/subs_gained/shares
    are aggregated from the trailing-window `rows` (NULL/partial on fallback). rank
    is within this channel by window_views desc (1 = top), nulls last."""
    agg = {}
    for r in rows:
        vid = r.get("video_id")
        if not vid:
            continue
        a = agg.setdefault(vid, {"views": 0, "dates": [], "wpct": 0.0, "wviews": 0,
                                 "subs": None, "shares": None})
        v = int(r.get("views") or 0)
        a["views"] += v
        if r.get("date"):
            a["dates"].append(str(r["date"])[:10])
        if r.get("avg_view_pct") is not None:
            a["wpct"] += float(r["avg_view_pct"]) * v
            a["wviews"] += v
        if r.get("subs_gained") is not None:
            a["subs"] = (a["subs"] or 0) + int(r["subs_gained"] or 0)
        if r.get("shares") is not None:
            a["shares"] = (a["shares"] or 0) + int(r["shares"] or 0)
    snaps = []
    for vid, m in meta.items():
        a = agg.get(vid)
        window_views = window_days = avg_pct = subs = shares = None
        if a:
            window_views = a["views"]
            if a["dates"]:
                try:
                    d0 = datetime.strptime(min(a["dates"]), "%Y-%m-%d")
                    d1 = datetime.strptime(max(a["dates"]), "%Y-%m-%d")
                    window_days = (d1 - d0).days + 1
                except ValueError:
                    window_days = None
            avg_pct = round(a["wpct"] / a["wviews"], 2) if a["wviews"] else None
            subs, shares = a["subs"], a["shares"]
        snaps.append({
            "sync_at": sync_at, "channel_key": key, "video_id": vid,
            "title": m.get("title"), "source": source,
            "views": int(m.get("views") or 0),
            "likes": int(m.get("likes") or 0),
            "comments": int(m.get("comments") or 0),
            "window_views": window_views, "window_days": window_days,
            "avg_view_pct": avg_pct, "subs_gained": subs, "shares": shares,
        })
    ranked = sorted(snaps, key=lambda s: (s["window_views"] is None,
                                          -(s["window_views"] or 0)))
    for i, s in enumerate(ranked, 1):
        s["rank"] = i if s["window_views"] is not None else None
    return snaps


def sync_video_stats(supa, buf, sync_at):
    """v5: pull per-video daily metrics for every channel in UPLOAD_DEFAULTS and
    upsert factory_video_stats. Preferred source: Analytics API v2; on a real-call
    403 (insufficient scope) fall back to Data API lifetime deltas so the
    dashboard still populates. Returns (total_rows, per_channel_source, reauth):
    reauth lists channels whose token needs a one-time re-auth with the
    yt-analytics.readonly scope (the worker never starts an OAuth flow)."""
    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
    except ImportError as e:
        buf.add(f"[worker] WARNING: googleapiclient unavailable ({e}) -- video stats skipped")
        return 0, {}, []
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=VIDEO_STATS_DAYS)
    titles_hist, hist_prev = history_video_index()
    total, sources, reauth = 0, {}, []
    for key, defaults in UPLOAD_DEFAULTS.items():
        try:
            creds = yt_creds(defaults["token_file"])
            yt = build("youtube", "v3", credentials=creds)
            ids = channel_video_ids(yt)
            meta = video_meta(yt, ids)
        except Exception as e:  # noqa: BLE001 -- one channel must not kill the sync
            buf.add(f"[worker] WARNING: {key}: video stats Data API setup failed: {e}")
            sources[key] = "error"
            continue
        if not ids:
            sources[key] = "no_videos"
            buf.add(f"[worker] {key}: no uploads found, skipped")
            continue
        source = "analytics_api"
        try:
            yta = build("youtubeAnalytics", "v2", credentials=creds)
            rows = analytics_to_rows(key, fetch_video_analytics(yta, ids, start, today),
                                     meta, titles_hist)
            # window signals: traffic-source mix + 3s/15s retention holds, stamped
            # onto each video's latest daily row (best-effort; bounded to videos
            # with activity in the window so per-video hold queries stay cheap).
            active = list({r["video_id"] for r in rows if r.get("video_id")})
            if active:
                try:
                    traffic = fetch_video_traffic(yta, active, start, today)
                    holds = fetch_video_holds(yta, active, meta, start, today)
                    attach_window_signals(rows, traffic, holds)
                except Exception as e:  # noqa: BLE001 -- never fail the sync on this
                    buf.add(f"[worker] {key}: window signals (traffic/holds) skipped: {e}")
        except HttpError as e:
            status = getattr(getattr(e, "resp", None), "status", None)
            if status == 403:
                source = "data_api_fallback"
                if re.search(r"insufficient|permission", str(e), re.I):
                    reauth.append(key)
                buf.add(f"[worker] {key}: Analytics API denied (HTTP 403 -- token lacks "
                        "the yt-analytics.readonly scope?), falling back to Data API "
                        "lifetime deltas. Fix: one-time re-auth of this channel's token "
                        "with the yt-analytics.readonly scope added (manual step).")
                rows = fallback_rows(supa, key, meta, hist_prev, today)
            else:
                buf.add(f"[worker] WARNING: {key}: Analytics API error (HTTP {status}): "
                        f"{str(e)[:300]}")
                sources[key] = "error"
                continue
        except Exception as e:  # noqa: BLE001
            buf.add(f"[worker] WARNING: {key}: Analytics query failed: {e}")
            sources[key] = "error"
            continue
        if rows:
            try:
                supa.insert("factory_video_stats", rows,
                            on_conflict="channel_key,video_id,date",
                            resolution="merge-duplicates")
            except (RuntimeError, requests.RequestException) as e:
                buf.add(f"[worker] WARNING: {key}: factory_video_stats upsert failed: {e}")
                sources[key] = "error"
                continue
        sources[key] = source
        total += len(rows)
        buf.add(f"[worker] {key}: {len(rows)} video-day row(s) upserted (source={source})")
        # v12: per-sync snapshot for sync-to-sync deltas (must never fail the sync)
        try:
            snaps = build_snapshot_rows(key, meta, rows, sync_at, source)
            if snaps:
                supa.insert("factory_video_snapshots", snaps,
                            on_conflict="video_id,sync_at",
                            resolution="merge-duplicates")
                buf.add(f"[worker] {key}: {len(snaps)} snapshot row(s) written")
        except (RuntimeError, requests.RequestException, ValueError) as e:
            buf.add(f"[worker] WARNING: {key}: snapshot write failed: {e}")
    return total, sources, reauth


def video_summary_for_context(supa, days=VIDEO_STATS_DAYS, top_n=3):
    """v5: per-channel top/bottom videos over the window (total views + weighted
    avg_view_pct) for the analyze_and_suggest context dump -- lets suggestions
    cite per-video evidence. Empty dict on any error (context stays usable)."""
    today = datetime.now(timezone.utc).date()
    try:
        rows = supa.select(
            "factory_video_stats",
            f"select=channel_key,video_id,title,views,avg_view_pct"
            f"&date=gte.{today - timedelta(days=days)}")
    except (RuntimeError, requests.RequestException):
        return {}
    agg = {}
    for r in rows:
        a = agg.setdefault((r["channel_key"], r["video_id"]),
                           {"title": None, "views": 0, "wpct": 0.0, "wviews": 0})
        v = int(r.get("views") or 0)
        a["views"] += v
        if r.get("title"):
            a["title"] = r["title"]
        if r.get("avg_view_pct") is not None:
            a["wpct"] += float(r["avg_view_pct"]) * v
            a["wviews"] += v
    per = {}
    for (ck, vid), a in agg.items():
        per.setdefault(ck, []).append({
            "video_id": vid, "title": a["title"], "views": a["views"],
            "avg_view_pct": round(a["wpct"] / a["wviews"], 2) if a["wviews"] else None,
        })
    out = {}
    for ck, vids in per.items():
        vids.sort(key=lambda x: x["views"], reverse=True)
        out[ck] = {"top": vids[:top_n],
                   "bottom": vids[-top_n:][::-1] if len(vids) > top_n else []}
    return out


def run_analytics_sync(supa, job):
    """Native handler for type 'analytics_sync' -- no claude call.
    Refresh stats via network_stats.py (best effort), aggregate history.csv into
    factory_stats, pull per-video daily metrics into factory_video_stats (v5),
    then queue a follow-up analyze_and_suggest job."""
    job_id = job["id"]
    log(f"claimed analytics_sync job {job_id}")
    buf = LogBuffer()
    buf.add(f"[worker] analytics_sync started at {now_iso()}")

    def flush():
        try:
            supa.patch("factory_jobs", f"id=eq.{job_id}",
                       {"logs": buf.text(), "heartbeat_at": now_iso()})  # v7: heartbeat too
        except (RuntimeError, requests.RequestException) as e:
            log(f"  log flush failed: {e}")

    flush()
    try:
        proc = subprocess.run([sys.executable, str(SCRIPTS_DIR / "network_stats.py")],
                              cwd=str(REPO), capture_output=True, text=True,
                              timeout=STATS_TIMEOUT_S)
        if proc.returncode != 0:
            buf.add(f"[worker] WARNING: network_stats.py exited {proc.returncode} -- "
                    f"proceeding with existing csv. Tail:\n{(proc.stderr or proc.stdout or '')[-1500:]}")
        else:
            buf.add(f"[worker] network_stats.py refreshed stats: {(proc.stdout or '').strip()[-500:]}")
    except (OSError, subprocess.TimeoutExpired) as e:
        buf.add(f"[worker] WARNING: network_stats.py failed ({e}) -- proceeding with existing csv")
    flush()

    if not HISTORY_CSV.exists():
        fail(supa, job_id, f"no stats history at {HISTORY_CSV} (and refresh failed)", buf)
        return
    try:
        rows, unmatched = aggregate_history()
    except (OSError, ValueError, KeyError) as e:
        fail(supa, job_id, f"could not parse {HISTORY_CSV}: {e}", buf)
        return
    for name in sorted(unmatched):
        buf.add(f"[worker] WARNING: unmatched display channel {name!r} in history.csv "
                "(extend DISPLAY_MAP)")
    try:
        supa.insert("factory_stats", rows, on_conflict="channel_key,date",
                    resolution="merge-duplicates")
    except (RuntimeError, requests.RequestException) as e:
        fail(supa, job_id, f"factory_stats upsert failed: {e}", buf)
        return
    buf.add(f"[worker] upserted {len(rows)} factory_stats row(s)")
    flush()

    # v5: per-video daily metrics -> factory_video_stats (must never fail the sync)
    # v12: capture ONE sync_at for the whole run so every snapshot row (across all
    # channels, written seconds apart) shares a single timestamp bucket -- the diff
    # "two most recent distinct sync_at" depends on this.
    sync_at = now_iso()
    video_rows, video_sources, reauth = 0, {}, []
    try:
        video_rows, video_sources, reauth = sync_video_stats(supa, buf, sync_at)
    except Exception as e:  # noqa: BLE001
        buf.add(f"[worker] WARNING: per-video stats sync failed: {e}")
    flush()

    # v6: stamp the successful sync -- powers the dashboard's "last ran" display
    # (best effort: a settings hiccup must never fail the sync itself). Reuse the
    # same sync_at so last_sync_at aligns with the snapshot the UI diffs against.
    try:
        supa.insert("factory_settings", [{"key": "last_sync_at", "value": sync_at}],
                    on_conflict="key", resolution="merge-duplicates")
        buf.add("[worker] factory_settings.last_sync_at updated")
    except (RuntimeError, requests.RequestException) as e:
        buf.add(f"[worker] WARNING: could not update last_sync_at: {e}")

    follow_id = None
    try:
        created = supa.insert_returning("factory_jobs", [{
            "type": "analyze_and_suggest",
            "channel_key": "_network",
            "title": "AI content analysis",
            "prompt": "",
            "model": job.get("model") or "sonnet",
            "effort": job.get("effort") or "low",
            "ultracode": bool(job.get("ultracode")),
        }])
        follow_id = created[0]["id"] if created else None
        buf.add(f"[worker] queued follow-up analyze_and_suggest job {follow_id}")
    except (RuntimeError, requests.RequestException) as e:
        buf.add(f"[worker] WARNING: could not queue follow-up analyze_and_suggest job: {e}")

    result = {"rows_upserted": len(rows), "video_rows": video_rows,
              "video_sources": video_sources, "reauth_needed": reauth,
              "follow_up_job_id": follow_id}
    if reauth:
        result["note"] = ("channels needing a one-time re-auth with the "
                          "yt-analytics.readonly scope: " + ", ".join(reauth) +
                          " (their per-video stats used the Data API fallback)")
    buf.add(f"[worker] analytics_sync done at {now_iso()}")
    try:
        supa.patch("factory_jobs", f"id=eq.{job_id}",
                   {"status": "done", "finished_at": now_iso(), "result": result, "logs": buf.text()})
        supa.insert("factory_events", [{
            "kind": "job_done",
            "message": (f"analytics_sync done ({len(rows)} stats row(s), "
                        f"{video_rows} video-day row(s) upserted)"),
            "meta": {"job_id": job_id, **result},
        }])
    except (RuntimeError, requests.RequestException) as e:
        log(f"  final status update failed: {e}")
    mark_calendar_produced(supa, job_id)
    log(f"analytics_sync {job_id} done rows={len(rows)} video_rows={video_rows} "
        f"follow_up={follow_id}")


def dump_analysis_context(supa, job_id):
    """Write renders_out/analysis_ctx_<JOBID>.json for the analyze_and_suggest prompt."""
    today = datetime.now(timezone.utc).date()
    ctx = {
        "generated_at": now_iso(),
        "note": "stats views/subs are cumulative snapshots per channel per date; "
                "YouTube Analytics lags ~48h",
        "channels": supa.select("factory_channels", "select=key,name,niche,guidelines&order=key"),
        "stats": supa.select(
            "factory_stats",
            f"select=channel_key,date,views,subs&date=gte.{today - timedelta(days=30)}&order=date.asc"),
        # v5: per-video evidence -- top/bottom videos per channel over 30d
        # (total views + views-weighted avg_view_pct from factory_video_stats)
        "video_summary": video_summary_for_context(supa),
        # v6: id/status/full brief power the challenge pass; replaces_id/why_not
        # expose existing challengers so items are never challenged twice
        "calendar": supa.select(
            "factory_calendar",
            f"select=id,channel_key,planned_date,title,brief,type,kind,status,origin,"
            f"suggestion_reason,replaces_id,why_not"
            f"&planned_date=gte.{today - timedelta(days=14)}"
            f"&planned_date=lte.{today + timedelta(days=21)}&order=planned_date.asc"),
        "recent_jobs": supa.select("factory_jobs",
                                   "select=type,title,status&order=created_at.desc&limit=20"),
        # v4: what the strategist said last time + what tools the factory already has
        "last_insights": supa.select(
            "factory_insights", "select=channel_key,ts,summary,details&order=ts.desc&limit=10"),
        "generator_catalog": supa.select(
            "factory_generators", "select=name,description,tags,scope&order=name"),
    }
    RENDERS_OUT.mkdir(exist_ok=True)
    path = RENDERS_OUT / f"analysis_ctx_{job_id}.json"
    path.write_text(json.dumps(ctx, indent=2, default=str))
    return path


def dump_brief_context(supa, job):
    """v4: write renders_out/brief_ctx_<JOBID>.json for the suggest_brief prompt:
    channel guidelines + last-14d stats + last 10 job titles + next-14d calendar."""
    key = job.get("channel_key") or ""
    today = datetime.now(timezone.utc).date()
    chan = supa.select("factory_channels", f"key=eq.{key}&select=key,name,niche,guidelines")
    jobs = supa.select(
        "factory_jobs", f"select=title&channel_key=eq.{key}&order=created_at.desc&limit=10")
    ctx = {
        "generated_at": now_iso(),
        "channel": chan[0] if chan else {"key": key, "note": "channel row missing"},
        "stats_last_14d": supa.select(
            "factory_stats",
            f"select=date,views,subs&channel_key=eq.{key}"
            f"&date=gte.{today - timedelta(days=14)}&order=date.asc"),
        "recent_job_titles": [j["title"] for j in jobs if j.get("title")],
        "calendar_next_14d": supa.select(
            "factory_calendar",
            f"select=planned_date,title,brief,type,status,kind&channel_key=eq.{key}"
            f"&planned_date=gte.{today}&planned_date=lte.{today + timedelta(days=14)}"
            f"&order=planned_date.asc"),
    }
    RENDERS_OUT.mkdir(exist_ok=True)
    path = brief_ctx_path(job["id"])
    path.write_text(json.dumps(ctx, indent=2, default=str))
    return path


def dump_plan_content_context(supa, job):
    """v17: context for the plan_content idea engine — guidelines + last-30d stats +
    recent published/job titles + upcoming calendar (near-term events). The prompt
    itself runs yt_retention.py + WebSearch for the deeper signals."""
    key = job.get("channel_key") or ""
    today = datetime.now(timezone.utc).date()
    chan = supa.select("factory_channels", f"key=eq.{key}&select=key,name,niche,guidelines")
    jobs = supa.select("factory_jobs",
                       f"select=title&channel_key=eq.{key}&order=created_at.desc&limit=20")
    posts = supa.select("factory_posts",
                        f"select=yt_title,status,publish_at&channel_key=eq.{key}"
                        "&order=publish_at.desc&limit=15")
    ctx = {
        "generated_at": now_iso(),
        "today": str(today),
        "channel": chan[0] if chan else {"key": key},
        "stats_last_30d": supa.select(
            "factory_stats",
            f"select=date,views,subs&channel_key=eq.{key}"
            f"&date=gte.{today - timedelta(days=30)}&order=date.asc"),
        "recent_published_titles": [p["yt_title"] for p in posts if p.get("yt_title")],
        "recent_job_titles": [j["title"] for j in jobs if j.get("title")],
        "calendar_next_21d": supa.select(
            "factory_calendar",
            f"select=planned_date,title,status&channel_key=eq.{key}"
            f"&planned_date=gte.{today}&planned_date=lte.{today + timedelta(days=21)}"
            f"&order=planned_date.asc"),
    }
    RENDERS_OUT.mkdir(exist_ok=True)
    path = plan_content_ctx_path(job["id"])
    path.write_text(json.dumps(ctx, indent=2, default=str))
    return path


def ingest_insights(supa, data, buf):
    """v4: insert the per-channel insights block from the analyze_and_suggest output
    into factory_insights. Returns the number of rows inserted."""
    rows = []
    for ck, ins in (data.get("insights") or {}).items():
        if not isinstance(ins, dict) or not str(ins.get("summary") or "").strip():
            continue
        rows.append({
            "channel_key": ck,
            "summary": str(ins["summary"]),
            "details": ins.get("details") if isinstance(ins.get("details"), dict) else {},
        })
    if not rows:
        return 0
    try:
        supa.insert("factory_insights", rows)
    except (RuntimeError, requests.RequestException) as e:
        buf.add(f"[worker] WARNING: could not insert insights: {e}")
        return 0
    buf.add(f"[worker] recorded {len(rows)} channel insight(s) in factory_insights")
    return len(rows)


def challenger_row(supa, s, row, buf):
    """RETIRED 2026-08-20 by owner decision: the challenge pass is gone.

    It wrote a CHALLENGER calendar row (replaces_id + why_not) proposing to
    replace an already-planned piece, and the app showed those within 72h of
    publish as a decision to make. The prompt no longer asks for one; this
    refuses any that still arrives, so a stray replaces_ref in an old cached
    plan cannot quietly resurrect rows nothing renders. The two edge actions
    (supersede_calendar_item, dismiss_challenge) stay callable so the existing
    rows can still be resolved."""
    ref = str(s.get("replaces_ref") or "").strip()
    if ref:
        buf.add(f"[worker] ignored challenger for {ref!r} — the challenge pass is retired")
    return None


def _challenger_row_retired(supa, s, row, buf):
    ref = str(s.get("replaces_ref") or "").strip()
    try:
        orig = supa.select("factory_calendar", f"id=eq.{ref}&select=id,kind,status")
    except (RuntimeError, requests.RequestException) as e:
        buf.add(f"[worker] skipped challenger (lookup of original {ref!r} failed: {e})")
        return None
    if not orig:
        buf.add(f"[worker] skipped challenger for unknown calendar item {ref!r}")
        return None
    try:
        live = supa.select(
            "factory_calendar",
            f"replaces_id=eq.{ref}&status=eq.suggested&select=id&limit=1")
    except (RuntimeError, requests.RequestException) as e:
        buf.add(f"[worker] skipped challenger (live-challenger check for {ref!r} failed: {e})")
        return None
    if live:
        buf.add(f"[worker] skipped duplicate challenger for {ref!r} (one already live)")
        return None
    row["kind"] = orig[0].get("kind") or row["kind"]
    row["replaces_id"] = ref
    row["why_not"] = str(s.get("why_not") or "")
    return row


_BACKLOG_HEADER = (
    "# Factory Backlog\n\n"
    "Code / factory-internal suggestions written by `analyze_and_suggest` runs. Reviewed "
    "from a Claude Code session (not the calendar). Content-facing suggestions still land "
    "in `factory_calendar` and drive the calendar UI. See `scripts/factory_worker.py::ingest_suggestions`.\n\n"
    "Sections are dedup'd by title. Flip `- [ ] open` to `- [x] done` once actioned; move "
    "actioned items into an `# Actioned` section at the bottom if you want history.\n\n"
)


def _existing_backlog_titles(text):
    """Set of every `## <title>` already present in the backlog (case-insensitive, trimmed)."""
    out = set()
    for line in text.splitlines():
        if line.startswith("## "):
            out.add(line[3:].strip().lower())
    return out


def append_factory_backlog(rows, job_id, buf):
    """Append kind='factory' suggestion rows as new sections to docs/FACTORY-BACKLOG.md.
    Dedup by title (case-insensitive). Returns the number appended (0 if all were dupes
    or rows was empty). Never raises -- backlog failures are logged and swallowed so
    the content-suggestion ingest stays authoritative."""
    if not rows:
        return 0
    path = factory_backlog_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text() if path.exists() else _BACKLOG_HEADER
        seen = _existing_backlog_titles(existing)
        chunks = []
        for r in rows:
            title = (r.get("title") or "").strip()
            if not title or title.lower() in seen:
                buf.add(f"[worker] backlog dupe skipped: {title!r}")
                continue
            seen.add(title.lower())
            reason = (r.get("suggestion_reason") or "").strip() or "(no reason recorded)"
            brief = (r.get("brief") or "").strip() or "(no brief)"
            date = r.get("planned_date") or ""
            chunks.append(
                f"## {title}\n"
                f"_source: analyze_and_suggest {job_id} · {date}_\n\n"
                f"**Why:** {reason}\n\n"
                f"**Interface / acceptance:**\n\n{brief}\n\n"
                f"- [ ] open\n\n"
            )
        if not chunks:
            return 0
        # ensure file ends with a blank line before append
        if existing and not existing.endswith("\n\n"):
            existing = existing.rstrip("\n") + "\n\n"
        path.write_text(existing + "".join(chunks))
        buf.add(f"[worker] appended {len(chunks)} factory suggestion(s) to {path.relative_to(REPO)}")
        return len(chunks)
    except OSError as e:
        buf.add(f"[worker] WARNING: could not append factory backlog: {e}")
        return 0


def suggestion_row(channel_key, planned_date, title, *, brief="", kind="content",
                   type_=None, model=None, effort=None, ultracode=False, reason="",
                   evidence=None, suggestion_source=None, suggestion_confidence="scored"):
    """THE canonical factory_calendar 'suggested' row shape. Every producer of
    suggestions (analyze_and_suggest via ingest_suggestions(), and the deterministic
    scripts/suggest_next.py) must build rows through here so the two stay in sync.

    PostgREST bulk insert demands identical keys on EVERY row of the batch (PGRST102),
    so challenger-only columns (replaces_id / why_not) must exist on plain suggestions
    too -- do not "optimise" them away. Same goes for the 022 provenance columns.
    """
    return {
        "channel_key": channel_key,
        "planned_date": planned_date,
        "title": title,
        "brief": brief or "",
        "kind": kind,
        # factory items are concrete generator create/update tasks -> always custom
        "type": ("custom" if kind == "factory" else (type_ or "produce_short")),
        # opus is what this network actually produces with (every shipped
        # claude-tricks episode; fable was a default nobody chose and it
        # silently became the model for auto-suggested pieces -- VJ 2026-08-18)
        "model": model or "opus",
        "effort": effort or "high",
        "ultracode": bool(ultracode),
        "status": "suggested",
        "origin": "ai_suggestion",
        "suggestion_reason": reason or "",
        # PostgREST bulk insert demands identical keys on every row (PGRST102),
        # so challenger-only columns must exist on plain suggestions too
        "replaces_id": None,
        "why_not": None,
        # --- migration 022_suggestion_provenance ---------------------------------
        # evidence is NEVER null and NEVER {"cites": []} for an ai_suggestion row;
        # the write-side guard lives in scripts/suggest_next.py::assert_evidence().
        "evidence": evidence,
        "suggestion_source": suggestion_source,
        "suggestion_confidence": suggestion_confidence or "scored",
    }


def ingest_suggestions(supa, job, buf):
    """Parse suggestions_<JOBID>.json written by the analyze_and_suggest run.
    v16: content suggestions land as factory_calendar rows (status 'suggested', origin
    'ai_suggestion', kind 'content') and drive the calendar UI as before. Factory /
    code suggestions (kind 'factory') are appended to docs/FACTORY-BACKLOG.md instead
    -- they never enter factory_calendar, so every calendar surface stays content-only.
    v6: entries with replaces_ref become CHALLENGER rows (replaces_id + why_not,
    kind copied from the original) via challenger_row(); originals with a live
    challenger are skipped.
    Returns (n_total, analysis_summary, n_insights) where n_total = content + factory."""
    spath = suggestions_path(job["id"])
    if not spath.exists():
        buf.add(f"[worker] WARNING: no suggestions file at {spath}")
        return 0, "", 0
    try:
        data = json.loads(spath.read_text())
    except (json.JSONDecodeError, OSError) as e:
        buf.add(f"[worker] WARNING: suggestions file unreadable: {e}")
        return 0, "", 0
    summary = data.get("analysis_summary") or ""
    rows = []
    challenged = set()  # originals already challenged within THIS payload
    n_chal = 0
    for s in data.get("suggestions") or []:
        if not isinstance(s, dict) or not s.get("channel_key") or not s.get("title") \
                or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(s.get("planned_date") or "")):
            buf.add(f"[worker] skipped malformed suggestion: {json.dumps(s)[:200]}")
            continue
        kind = "factory" if s.get("kind") == "factory" else "content"
        row = suggestion_row(
            s["channel_key"], s["planned_date"], s["title"],
            brief=s.get("brief"), kind=kind, type_=s.get("type"),
            model=s.get("model"), effort=s.get("effort"),
            ultracode=s.get("ultracode"), reason=s.get("reason"),
            # analyze_and_suggest is model-authored and carries no file-level trail
            evidence=None, suggestion_source="analyze_and_suggest",
            suggestion_confidence="generated",
        )
        ref = str(s.get("replaces_ref") or "").strip()
        if ref:
            if ref in challenged:
                buf.add(f"[worker] skipped duplicate challenger for {ref!r} (already in this batch)")
                continue
            row = challenger_row(supa, s, row, buf)
            if row is None:
                continue
            challenged.add(ref)
            n_chal += 1
        rows.append(row)
    # v16: split by kind. content -> factory_calendar (calendar UI). factory ->
    # docs/FACTORY-BACKLOG.md (reviewed from Claude Code). challengers of factory
    # originals inherit kind='factory' via challenger_row() and route here too.
    content_rows = [r for r in rows if r.get("kind") != "factory"]
    factory_rows = [r for r in rows if r.get("kind") == "factory"]
    n_backlog = append_factory_backlog(factory_rows, job["id"], buf)
    if content_rows:
        try:
            supa.insert("factory_calendar", content_rows)
            supa.insert("factory_events", [{
                "kind": "suggestion",
                "message": (f"{len(content_rows)} new content suggestion(s)"
                            + (f" ({n_chal} challenger(s))" if n_chal else "")
                            + (f"; {n_backlog} factory item(s) -> docs/FACTORY-BACKLOG.md"
                               if n_backlog else "")),
                "meta": {"job_id": job["id"], "challengers": n_chal,
                         "backlog_appended": n_backlog},
            }])
        except (RuntimeError, requests.RequestException) as e:
            buf.add(f"[worker] WARNING: could not insert suggestions: {e}")
            return n_backlog, summary, ingest_insights(supa, data, buf)
    buf.add(f"[worker] ingested {len(content_rows)} content suggestion(s) into factory_calendar"
            + (f" ({n_chal} challenger(s))" if n_chal else "")
            + (f"; {n_backlog} factory item(s) appended to backlog" if n_backlog else ""))
    return len(content_rows) + n_backlog, summary, ingest_insights(supa, data, buf)


# ---------------------------------------------------------------- v9: staged production (docs/STAGED-PIPELINE.md)


def dump_staged_context(supa, job, include=("approved",)):
    """v9: write renders_out/staged_ctx_<JOBID>.json for the assemble_episode /
    preview_episode prompt: the calendar item + channel (key/name/guidelines) +
    every asset whose LATEST version's status is in `include` (assembly: approved
    only; draft preview: approved + review so pending revisions show up too).
    local_path -- local disk is the source of truth for assembly."""
    cal_id = (job.get("meta") or {}).get("calendar_id")
    if not cal_id:
        raise RuntimeError(f"{job.get('type')} job has no meta.calendar_id")
    items = supa.select("factory_calendar", f"id=eq.{cal_id}&select=*")
    if not items:
        raise RuntimeError(f"calendar item {cal_id} not found")
    item = items[0]
    chan = supa.select("factory_channels",
                       f"key=eq.{item.get('channel_key')}&select=key,name,guidelines")
    rows = supa.select(
        "factory_assets",
        f"calendar_id=eq.{cal_id}&select=asset_key,version,kind,group_key,title,spec,"
        f"local_path,status&order=asset_key.asc,version.desc")
    latest, assets = set(), []
    for r in rows:  # first row per asset_key = its latest version
        if r["asset_key"] in latest:
            continue
        latest.add(r["asset_key"])
        if r.get("status") in include:
            assets.append({"asset_key": r["asset_key"], "kind": r.get("kind"),
                           "group_key": r.get("group_key"), "title": r.get("title"),
                           "spec": r.get("spec"), "local_path": r.get("local_path")})
    ctx = {
        "generated_at": now_iso(),
        "item": item,
        "channel": chan[0] if chan else {"key": item.get("channel_key"),
                                         "note": "channel row missing"},
        "assets": assets,
    }
    RENDERS_OUT.mkdir(exist_ok=True)
    path = staged_ctx_path(job["id"])
    path.write_text(json.dumps(ctx, indent=2, default=str))
    return path


def mark_asset_failed(supa, job_id):
    """A failed/cancelled/orphaned generate_asset job flips its asset row to
    'failed' (revise = retry). Keyed by factory_assets.job_id (back-filled at plan
    ingest); the status guard keeps reviewer verdicts (skipped/superseded) intact.
    Never raises."""
    try:
        supa.patch("factory_assets",
                   f"job_id=eq.{job_id}&status=in.(queued,generating)",
                   {"status": "failed", "updated_at": now_iso()})
    except (RuntimeError, requests.RequestException) as e:
        log(f"  could not mark asset failed for job {job_id}: {e}")


def mark_calendar_produced_by_id(supa, calendar_id):
    """Staged assembly flips its calendar item to 'produced' explicitly by id
    (calendar.job_id points at the PLAN job, so the job_id join can't be used)."""
    if not calendar_id:
        return
    try:
        supa.patch("factory_calendar", f"id=eq.{calendar_id}", {"status": "produced"})
    except (RuntimeError, requests.RequestException) as e:
        log(f"  could not mark calendar item {calendar_id} produced: {e}")


def ingest_asset_plan(supa, job, buf):
    """v9: parse assets_plan_<JOBID>.json written by the plan_assets run and ingest
    it: one factory_assets row (version 1, status 'queued') + one generate_asset
    factory_jobs row per asset, then back-fill asset.job_id. Idempotent: if ANY
    factory_assets rows already exist for this calendar item the whole ingest is
    skipped (safe re-run). Returns the job result dict, or None after failing the
    job itself (missing/invalid plan, or no usable assets)."""
    job_id = job["id"]
    cal_id = (job.get("meta") or {}).get("calendar_id")
    ppath = assets_plan_path(job_id)
    try:
        plan = json.loads(ppath.read_text())
    except (OSError, json.JSONDecodeError) as e:
        fail(supa, job_id,
             f"plan_assets finished but the plan JSON is missing/unreadable ({ppath}): {e}",
             buf, job=job)
        return None
    if not cal_id:
        fail(supa, job_id, "plan_assets job has no meta.calendar_id", buf, job=job)
        return None
    try:
        existing = supa.select("factory_assets", f"calendar_id=eq.{cal_id}&select=id&limit=1")
    except (RuntimeError, requests.RequestException) as e:
        fail(supa, job_id, f"could not check existing assets for {cal_id}: {e}", buf, job=job)
        return None
    if existing:
        buf.add(f"[worker] assets already exist for calendar item {cal_id} -- "
                "ingest skipped (idempotent re-run)")
        return {"summary": plan.get("summary") or "", "planned": 0,
                "note": "assets already existed for this calendar item; ingest skipped"}
    channel_key = job.get("channel_key") or ""
    raw_assets = plan.get("assets")
    seen, planned = set(), 0
    for pos, a in enumerate(raw_assets if isinstance(raw_assets, list) else []):
        if not isinstance(a, dict):
            buf.add(f"[worker] skipped malformed asset entry: {json.dumps(a)[:200]}")
            continue
        akey = re.sub(r"[^a-z0-9_-]+", "_",
                      str(a.get("asset_key") or "").strip().lower()).strip("_-")
        if not akey or akey in seen:
            buf.add(f"[worker] skipped asset with missing/duplicate asset_key: "
                    f"{json.dumps(a)[:200]}")
            continue
        seen.add(akey)
        group = a.get("group") if a.get("group") in ASSET_GROUPS else "other"
        kind = a.get("kind") if a.get("kind") in ASSET_KINDS else "image"
        # clamp plan-emitted knobs: a bad value would fail every generate job downstream
        model = a.get("model") if a.get("model") in ("fable", "opus", "sonnet", "haiku") \
            else (job.get("model") or "fable")
        effort = a.get("effort") if a.get("effort") in ("low", "medium", "high", "xhigh", "max") \
            else (job.get("effort") or "high")
        # job.title is 'Plan assets — <item title>'; keep only the item title
        jtitle = re.sub(r"^Plan assets\s+—\s+", "", job.get("title") or "")
        asset_id = None
        try:
            created = supa.insert_returning("factory_assets", [{
                "calendar_id": cal_id,
                "channel_key": channel_key,
                "asset_key": akey,
                "version": 1,
                "group_key": group,
                "kind": kind,
                "title": str(a.get("title") or ""),
                "spec": a.get("spec") if isinstance(a.get("spec"), dict) else {},
                "status": "queued",
                "position": pos,
                "model": model,
                "effort": effort,
            }])
            asset_id = created[0]["id"]
            jcreated = supa.insert_returning("factory_jobs", [{
                "type": "generate_asset",
                "channel_key": channel_key,
                "title": f"Asset: {akey} — {jtitle}" if jtitle else f"Asset: {akey}",
                "prompt": (f"Staged asset {akey} v1 for calendar item {cal_id} -- "
                           f"full spec lives in factory_assets {asset_id}"),
                "model": model,
                "effort": effort,
                "meta": {"calendar_id": cal_id, "asset_id": asset_id,
                         "asset_key": akey, "version": 1},
            }])
            gen_job_id = jcreated[0]["id"]
            supa.patch("factory_assets", f"id=eq.{asset_id}", {"job_id": gen_job_id})
        except (RuntimeError, requests.RequestException) as e:
            buf.add(f"[worker] WARNING: could not ingest asset {akey!r}: {e}")
            if asset_id:
                # asset row exists but its generate job doesn't: flip to failed so the
                # board shows Revise (= retry) instead of a forever-queued ghost
                try:
                    supa.patch("factory_assets", f"id=eq.{asset_id}&status=eq.queued",
                               {"status": "failed"})
                except (RuntimeError, requests.RequestException):
                    pass
            continue
        planned += 1
        buf.add(f"[worker] planned asset {akey} ({group}/{kind}) -> job {gen_job_id}")
    if not planned:
        fail(supa, job_id, f"plan JSON at {ppath} contained no usable assets", buf, job=job)
        return None
    try:
        supa.insert("factory_events", [{
            "kind": "assets_planned",
            "message": f"{planned} asset(s) planned for calendar item {cal_id}",
            "meta": {"job_id": job_id, "calendar_id": cal_id,
                     "channel_key": channel_key, "planned": planned},
        }])
    except (RuntimeError, requests.RequestException) as e:
        buf.add(f"[worker] WARNING: could not log assets_planned event: {e}")
    return {"summary": plan.get("summary") or "", "planned": planned}


def finish_generate_asset(supa, job, asset, buf):
    """v9: exit-0 path for generate_asset -- parse asset_out_<JOBID>.json, upload
    the primary file (+ optional poster) to
    <channel_key>/assets/<calendar_id>/<asset_key>/v<version>/ and flip the asset
    row to 'review'. Returns the job result dict, or None after failing the job
    (fail() also flips the asset row to 'failed')."""
    job_id = job["id"]
    opath = asset_out_path(job_id)
    try:
        out = json.loads(opath.read_text())
    except (OSError, json.JSONDecodeError) as e:
        fail(supa, job_id,
             f"generate_asset finished but the output JSON is missing/unreadable ({opath}): {e}",
             buf, job=job)
        return None
    primary = poster = None
    frames = []
    for f in out.get("files") or []:
        if not isinstance(f, dict):
            continue
        p = Path(str(f.get("path") or ""))
        if not p.is_absolute():
            p = REPO / p
        if not p.exists():
            buf.add(f"[worker] output file missing on disk, skipped: {p}")
            continue
        if f.get("role") == "poster" and poster is None:
            poster = p
        elif f.get("role") == "frame" and len(frames) < 6:
            frames.append(p)
        elif f.get("role") == "asset" and primary is None:
            primary = p
    if primary is None:
        fail(supa, job_id,
             f"asset output JSON at {opath} lists no existing role='asset' file",
             buf, job=job)
        return None
    base = (f"{asset.get('channel_key')}/assets/{asset.get('calendar_id')}/"
            f"{asset.get('asset_key')}/v{asset.get('version')}")
    poster_path, frame_paths = None, []
    try:
        data = primary.read_bytes()
        supa.upload(f"{base}/{primary.name}", data,
                    mimetypes.guess_type(primary.name)[0] or "application/octet-stream")
        buf.add(f"[worker] uploaded {base}/{primary.name} ({len(data)} bytes)")
        if poster is not None:
            supa.upload(f"{base}/{poster.name}", poster.read_bytes(),
                        mimetypes.guess_type(poster.name)[0] or "image/jpeg")
            poster_path = f"{base}/{poster.name}"
            buf.add(f"[worker] uploaded poster {poster_path}")
        for fp in frames:
            supa.upload(f"{base}/{fp.name}", fp.read_bytes(),
                        mimetypes.guess_type(fp.name)[0] or "image/jpeg")
            frame_paths.append(f"{base}/{fp.name}")
        if frame_paths:
            buf.add(f"[worker] uploaded {len(frame_paths)} frame still(s)")
    except (RuntimeError, requests.RequestException, OSError) as e:
        fail(supa, job_id, f"asset upload failed: {e}", buf, job=job)
        return None
    # v10 exception-based review: the factory's own QC covers first generations, so
    # v1 lands approved; revisions (v2+) exist because the human flagged something,
    # so THOSE wait in review for explicit confirmation.
    landed = "approved" if (asset.get("version") or 1) == 1 else "review"
    try:
        # guarded like mark_asset_failed: a reviewer's skipped/superseded verdict set
        # while the job was running must never be overwritten
        supa.patch("factory_assets",
                   f"id=eq.{asset['id']}&status=in.(queued,generating)", {
            "status": landed,
            "filename": primary.name,
            "storage_path": f"{base}/{primary.name}",
            "poster_path": poster_path,
            "local_path": str(primary),
            "size_bytes": len(data),
            "duration_s": (probe_duration(primary)
                           if asset.get("kind") in ("video", "audio") else None),
            "review_note": str(out.get("review_note") or "")[:2000],
            "frames": frame_paths,
            "updated_at": now_iso(),
        })
    except (RuntimeError, requests.RequestException) as e:
        fail(supa, job_id, f"asset row update failed after upload: {e}", buf, job=job)
        return None
    try:
        supa.insert("factory_events", [{
            "kind": "asset_ready",
            "message": (f"asset {asset.get('asset_key')} v{asset.get('version')} "
                        f"{'auto-approved' if landed == 'approved' else 'ready for review'} "
                        f"({primary.name})"),
            "meta": {"job_id": job_id, "asset_id": asset["id"],
                     "calendar_id": asset.get("calendar_id"),
                     "channel_key": asset.get("channel_key")},
        }])
    except (RuntimeError, requests.RequestException) as e:
        buf.add(f"[worker] WARNING: could not log asset_ready event: {e}")
    buf.add(f"[worker] asset {asset.get('asset_key')} v{asset.get('version')} -> {landed}")
    return {"summary": out.get("summary") or "", "asset_id": asset["id"], "landed": landed}


def finish_preview_episode(supa, job, buf):
    """v10: exit-0 path for preview_episode -- parse preview_out_<JOBID>.json,
    upload the draft mp4 to <channel>/assets/<calendar_id>/_preview/, stamp
    factory_calendar.preview_path/preview_at. Never publishes anything."""
    job_id = job["id"]
    cal_id = (job.get("meta") or {}).get("calendar_id")
    ppath = preview_out_path(job_id)
    try:
        out = json.loads(ppath.read_text())
    except (OSError, json.JSONDecodeError) as e:
        fail(supa, job_id,
             f"preview_episode finished but the output JSON is missing/unreadable ({ppath}): {e}",
             buf, job=job)
        return None
    p = Path(str(out.get("file") or ""))
    if not p.is_absolute():
        p = REPO / p
    if not cal_id or not p.exists():
        fail(supa, job_id, f"preview output JSON at {ppath} has no existing draft file",
             buf, job=job)
        return None
    storage = f"{job.get('channel_key')}/assets/{cal_id}/_preview/{job_id[:8]}_{p.name}"
    try:
        supa.upload(storage, p.read_bytes(),
                    mimetypes.guess_type(p.name)[0] or "video/mp4")
        supa.patch("factory_calendar", f"id=eq.{cal_id}",
                   {"preview_path": storage, "preview_at": now_iso()})
    except (RuntimeError, requests.RequestException, OSError) as e:
        fail(supa, job_id, f"draft preview upload failed: {e}", buf, job=job)
        return None
    try:
        supa.insert("factory_events", [{
            "kind": "preview_ready",
            "message": f"draft preview ready ({p.name})",
            "meta": {"job_id": job_id, "calendar_id": cal_id,
                     "channel_key": job.get("channel_key")},
        }])
    except (RuntimeError, requests.RequestException) as e:
        buf.add(f"[worker] WARNING: could not log preview_ready event: {e}")
    buf.add(f"[worker] draft preview -> {storage}")
    return {"summary": out.get("summary") or "", "preview_path": storage}


def stamp_preview_from_render(supa, job, buf):
    """v16: a produce_preview job uploads its unmastered preview MP4 as a
    factory_render (public URL) but drafts NO post (gap-2 suppression). So the
    reviewer can WATCH it, copy that render's storage_path onto the calendar's
    preview_path/preview_at -- the exact field StudioBoard's program monitor
    renders (<video src=RENDERS_BASE+preview_path>). Best-effort; a failure here
    never fails the job (the render is still on the Renders page)."""
    cal_id = (job.get("meta") or {}).get("calendar_id")
    if not cal_id:
        buf.add("[worker] note: produce_preview job has no meta.calendar_id -- "
                "preview not stamped (Studio review needs the calendar link)")
        return
    try:
        rows = supa.select(
            "factory_renders",
            f"job_id=eq.{job['id']}&kind=eq.video"
            "&select=storage_path,filename,created_at&order=created_at.desc")
    except (RuntimeError, requests.RequestException) as e:
        buf.add(f"[worker] WARNING: could not read preview render to stamp: {e}")
        return
    if not rows:
        buf.add("[worker] note: produce_preview had no video render to stamp")
        return
    # prefer a filename that looks like the preview raw (ep<ep>_prev_raw.mp4)
    pick = next((r for r in rows if "prev" in (r.get("filename") or "").lower()), rows[0])
    storage = pick.get("storage_path")
    if not storage:
        return
    # v16: the produce_preview session picks its OWN ep key (it avoids colliding
    # with already-shipped episodes, e.g. asked for ep12 but used ep31). meta.ep
    # set at trigger time can therefore be stale, and finalize_episode reads it to
    # build --ep. So learn the ACTUAL ep from the preview filename and write it
    # back, keeping finalize in sync no matter what the session chose.
    m = re.search(r"ep(\d+)_", pick.get("filename") or "")
    if m:
        actual_ep = m.group(1)
        meta = dict(job.get("meta") or {})
        if str(meta.get("ep") or "") != actual_ep:
            meta["ep"] = actual_ep
            try:
                supa.patch("factory_jobs", f"id=eq.{job['id']}", {"meta": meta})
                buf.add(f"[worker] corrected job meta.ep -> {actual_ep} "
                        f"(session's real ep, from {pick.get('filename')})")
            except (RuntimeError, requests.RequestException) as e:
                buf.add(f"[worker] WARNING: could not correct meta.ep: {e}")
    try:
        supa.patch("factory_calendar", f"id=eq.{cal_id}",
                   {"preview_path": storage, "preview_at": now_iso()})
        supa.insert("factory_events", [{
            "kind": "preview_ready",
            "message": f"produce_preview draft ready ({pick.get('filename')})",
            "meta": {"job_id": job["id"], "calendar_id": cal_id,
                     "channel_key": job.get("channel_key")},
        }])
        buf.add(f"[worker] stamped calendar {cal_id[:8]} preview_path <- {storage}")
    except (RuntimeError, requests.RequestException) as e:
        buf.add(f"[worker] WARNING: could not stamp preview_path: {e}")


# ---------------------------------------------------------------- v4: post publisher


def utc_z(dt=None):
    """UTC timestamp with a Z suffix -- safe inside PostgREST query strings
    (an unencoded '+00:00' offset would decode as a space and break the filter)."""
    return (dt or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")


def rfc3339_utc(ts):
    """Any ISO timestamptz (e.g. '2026-08-05T15:00:00+00:00') -> RFC3339 UTC '...Z'
    as scripts/yt_upload.py --publish-at expects."""
    s = str(ts or "").strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def yt_channel_arg(token_file):
    """scripts/yt_upload.py resolves --channel X -> secrets/token_X.json
    (special case: lulla -> secrets/token.json)."""
    if token_file == "token.json":
        return "lulla"
    m = re.fullmatch(r"token_(.+)\.json", token_file or "")
    return m.group(1) if m else None


def build_publish_command(post, defaults, desc_path=None, thumb_path=None):
    """Construct the scripts/yt_upload.py argv for an armed post, using its real CLI:
    --channel/--video/--title/--audience/--publish-at/--tags/--desc-file/
    --synthetic/--thumbnail."""
    audience = post.get("audience") or defaults.get("audience") or ""
    cmd = [
        sys.executable, str(SCRIPTS_DIR / "yt_upload.py"),
        "--channel", yt_channel_arg(defaults.get("token_file")) or post.get("channel_key") or "",
        "--video", str(post.get("local_path") or ""),
        "--title", post.get("yt_title") or "",
        "--audience", "kids" if audience == "kids" else "general",
        "--publish-at", rfc3339_utc(post.get("publish_at")),
    ]
    tags = post.get("tags") or []
    if isinstance(tags, list) and tags:
        cmd += ["--tags", ",".join(str(t).strip() for t in tags if str(t).strip())]
    if desc_path:
        cmd += ["--desc-file", str(desc_path)]
    synthetic = post.get("synthetic")
    if synthetic is None:
        synthetic = defaults.get("synthetic")
    if synthetic:
        cmd += ["--synthetic"]
    if thumb_path:
        cmd += ["--thumbnail", str(thumb_path)]
    return cmd


def find_post_thumbnail(supa, post):
    """Optional: a local thumbnail from the same job's image renders ('thumb' in the
    filename and still on disk). None is fine -- yt_upload just skips the flag."""
    if not post.get("job_id"):
        return None
    try:
        rows = supa.select("factory_renders",
                           f"job_id=eq.{post['job_id']}&kind=eq.image&select=filename,local_path")
    except (RuntimeError, requests.RequestException):
        return None
    for r in rows:
        lp = r.get("local_path")
        if "thumb" in (r.get("filename") or "").lower() and lp and Path(lp).exists():
            return lp
    return None


def post_failed(supa, post, error):
    log(f"post {post['id']} FAILED: {error[:300]}")
    try:
        supa.patch("factory_posts", f"id=eq.{post['id']}",
                   {"status": "failed", "error": error[:8000], "updated_at": now_iso()})
        supa.insert("factory_events", [{
            "kind": "post_failed",
            "message": f"post {post.get('yt_title') or post['id']!r} failed: {error[:300]}",
            "meta": {"post_id": post["id"], "channel_key": post.get("channel_key")},
        }])
    except (RuntimeError, requests.RequestException) as e:
        log(f"  post failure status update also failed: {e}")


# v12: publish preflight -- slot-collision + duplicate-content warnings.
# Measured 5 Aug 2026: a failed-then-retried upload shipped the SAME Short
# twice (two private scheduled videos, consecutive days), and two different
# Shorts landed on the same 10:30 slot. Checks run against factory_posts AND
# the channel's live YouTube uploads (the latter is what catches orphan
# uploads no post row tracks).
SLOT_COLLISION_H = 6          # another video publishing within this window = collision
TITLE_DUP_RATIO = 0.90        # normalized-title similarity that counts as duplicate


def _norm_title(t):
    return re.sub(r"[^a-z0-9 ]+", "", str(t or "").lower()).strip()


def _titles_alike(a, b):
    import difflib
    na, nb = _norm_title(a), _norm_title(b)
    if not na or not nb:
        return False
    return na == nb or difflib.SequenceMatcher(None, na, nb).ratio() >= TITLE_DUP_RATIO


def preflight_post_warnings(supa, post, check_youtube=True):
    """Returns a list of warning strings; empty means clear to publish."""
    warns = []
    ch = post.get("channel_key") or ""
    pid = post.get("id")
    title = post.get("yt_title") or ""
    try:
        when = datetime.fromisoformat(str(post.get("publish_at")).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        when = None

    # 1) factory's own posts on this channel
    try:
        rows = supa.select("factory_posts",
                           f"channel_key=eq.{ch}&status=in.(armed,uploading,scheduled,published)"
                           f"&select=id,yt_title,publish_at,video_id,status")
    except (RuntimeError, requests.RequestException) as e:
        log(f"  preflight posts query failed (continuing): {e}")
        rows = []
    for r in rows:
        if r.get("id") == pid:
            continue
        if _titles_alike(title, r.get("yt_title")):
            warns.append(f"DUPLICATE TITLE vs post {r['id'][:8]} ({r.get('status')}, "
                         f"video {r.get('video_id') or '-'}): {str(r.get('yt_title'))[:60]!r}")
        if when is not None and r.get("publish_at"):
            try:
                other = datetime.fromisoformat(str(r["publish_at"]).replace("Z", "+00:00"))
                dh = abs((when - other).total_seconds()) / 3600
                if dh <= SLOT_COLLISION_H and r.get("status") in ("armed", "uploading", "scheduled"):
                    warns.append(f"SLOT COLLISION ({dh:.1f}h apart) with post {r['id'][:8]}: "
                                 f"{str(r.get('yt_title'))[:60]!r} at {r['publish_at']}")
            except (TypeError, ValueError):
                pass

    # 2) the channel's LIVE uploads -- catches orphan videos no post row tracks
    if check_youtube:
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            tp = REPO / "secrets" / (f"token_{ch}.json" if ch not in ("lulla", "pip") else "token.json")
            if tp.exists():
                creds = Credentials.from_authorized_user_file(str(tp), [
                    "https://www.googleapis.com/auth/youtube.upload",
                    "https://www.googleapis.com/auth/youtube"])
                yt = build("youtube", "v3", credentials=creds)
                chan = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0]
                pl = chan["contentDetails"]["relatedPlaylists"]["uploads"]
                items = yt.playlistItems().list(part="contentDetails", playlistId=pl,
                                                maxResults=15).execute().get("items", [])
                ids = [i["contentDetails"]["videoId"] for i in items]
                known = {r.get("video_id") for r in rows}
                if ids:
                    vids = yt.videos().list(part="snippet,status",
                                            id=",".join(ids)).execute().get("items", [])
                    for v in vids:
                        if v["id"] in known:
                            continue  # already compared via its post row
                        if _titles_alike(title, v["snippet"].get("title")):
                            warns.append(f"DUPLICATE TITLE on YouTube (UNTRACKED video "
                                         f"{v['id']}): {v['snippet']['title'][:60]!r}")
                        pa = (v.get("status") or {}).get("publishAt")
                        if when is not None and pa:
                            try:
                                other = datetime.fromisoformat(pa.replace("Z", "+00:00"))
                                if abs((when - other).total_seconds()) / 3600 <= SLOT_COLLISION_H:
                                    warns.append(f"SLOT COLLISION with UNTRACKED YouTube video "
                                                 f"{v['id']} at {pa}: {v['snippet']['title'][:60]!r}")
                            except (TypeError, ValueError):
                                pass
        except Exception as e:  # noqa: BLE001 -- best-effort; posts-table check already ran
            log(f"  preflight YouTube check failed (continuing with posts-only): {e}")
    return warns


def publish_post(supa, post):
    """Upload ONE armed post via scripts/yt_upload.py, scheduled for its publish_at.
    armed -> uploading -> scheduled (+video_id) on success, failed (+error) otherwise."""
    pid = post["id"]
    defaults = UPLOAD_DEFAULTS.get(post.get("channel_key") or "")
    if not defaults:
        post_failed(supa, post, f"no upload defaults for channel {post.get('channel_key')!r}")
        return
    lp = post.get("local_path") or ""
    if not lp or not Path(lp).exists():
        post_failed(supa, post, f"local video missing on disk: {lp!r}")
        return
    if not (post.get("yt_title") or "").strip() or not post.get("publish_at"):
        post_failed(supa, post, "armed post lacks yt_title or publish_at")
        return

    # v12: preflight gate -- never upload into a slot collision or a duplicate.
    # Violations bounce the post back to DRAFT with the warnings on the card;
    # the human re-arms deliberately after fixing (or accepts by re-arming).
    warns = preflight_post_warnings(supa, post)
    if warns:
        msg = "PREFLIGHT BLOCKED (re-arm to override after checking):\n- " + "\n- ".join(warns)
        log(f"post {pid} preflight blocked: {len(warns)} warning(s)")
        try:
            supa.patch("factory_posts", f"id=eq.{pid}&status=eq.armed",
                       {"status": "draft", "error": msg[:8000], "updated_at": now_iso()})
            supa.insert("factory_events", [{
                "kind": "post_preflight_blocked",
                "message": (f"{post.get('channel_key')}: {post.get('yt_title')!r} NOT "
                            f"uploaded -- {warns[0][:200]}"),
                "meta": {"post_id": pid, "warnings": warns[:6],
                         "channel_key": post.get("channel_key")},
            }])
        except (RuntimeError, requests.RequestException) as e:
            log(f"  preflight status update failed: {e}")
        return

    # claim armed -> uploading (conditional patch, then verify: no double upload)
    try:
        supa.patch("factory_posts", f"id=eq.{pid}&status=eq.armed",
                   {"status": "uploading", "updated_at": now_iso()})
        cur = supa.select("factory_posts", f"id=eq.{pid}&select=status")
    except (RuntimeError, requests.RequestException) as e:
        log(f"  could not claim post {pid}: {e}")
        return
    if not cur or cur[0].get("status") != "uploading":
        log(f"  post {pid} no longer armed, skipped")
        return

    desc_path = None
    if (post.get("yt_description") or "").strip():
        desc_path = RENDERS_OUT / f"post_desc_{pid}.txt"
        RENDERS_OUT.mkdir(exist_ok=True)
        desc_path.write_text(post["yt_description"])
    cmd = build_publish_command(post, defaults, desc_path, find_post_thumbnail(supa, post))
    log(f"publishing post {pid} ({post.get('channel_key')}): {post.get('yt_title')!r}")
    try:
        proc = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True,
                              timeout=PUBLISH_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired) as e:
        post_failed(supa, post, f"yt_upload.py did not finish: {e}")
        return
    out = f"{proc.stdout or ''}\n{proc.stderr or ''}"
    m = re.search(r"youtu\.be/([A-Za-z0-9_-]{6,})", out)
    # v11: the video id in the output is the truth, not the exit code. A crash
    # in a POST-upload step (thumbnail 403, playlist) used to mark an
    # uploaded+scheduled video as failed -- and a retry would upload a
    # DUPLICATE (measured 2026-08-05, thumbnails need phone verification).
    if not m:
        post_failed(supa, post,
                    f"yt_upload.py exited {proc.returncode}, no video id. Tail:\n{out[-2000:]}")
        return
    video_id = m.group(1)
    warn = None
    if proc.returncode != 0:
        warn = (f"video uploaded OK, but a post-upload step failed "
                f"(yt_upload.py exit {proc.returncode}). Tail:\n{out[-800:]}")
        log(f"  post {pid}: video {video_id} IS uploaded but yt_upload.py exited "
            f"{proc.returncode} (post-upload step failed) -- scheduling anyway")
    pub_at = rfc3339_utc(post.get("publish_at"))
    try:
        supa.patch("factory_posts", f"id=eq.{pid}",
                   {"status": "scheduled", "video_id": video_id, "error": warn,
                    "updated_at": now_iso()})
        supa.insert("factory_events", [{
            "kind": "post_scheduled",
            "message": (f"{post.get('channel_key')}: {post.get('yt_title')!r} uploaded, "
                        f"goes live {pub_at} (https://youtu.be/{video_id})"),
            "meta": {"post_id": pid, "video_id": video_id, "publish_at": pub_at},
        }])
    except (RuntimeError, requests.RequestException) as e:
        log(f"  post {pid} uploaded (video {video_id}) but status update failed: {e}")
    log(f"post {pid} scheduled -> https://youtu.be/{video_id} at {pub_at}")

    # v13: auto-post a pin comment after upload (best-effort, non-blocking).
    # The YouTube Data API cannot actually pin — yt_engage.py posts the comment
    # and prints the Studio deep-link for the one human click. Kids channels are
    # skipped automatically by yt_engage.py's MFK guard.
    _try_auto_pin(supa, post, video_id)


def _try_auto_pin(supa, post, video_id):
    """Best-effort: post the first comment on a freshly uploaded video.
    Uses the post's pin_comment field if set, otherwise a channel-specific
    default question. Failures are logged but never block the publish flow."""
    channel_key = post.get("channel_key") or ""
    defaults = UPLOAD_DEFAULTS.get(channel_key, {})
    token_file = defaults.get("token_file")
    if not token_file:
        return
    # kids channels have comments disabled (COPPA) — skip early
    if defaults.get("audience") == "kids":
        return

    # prefer a per-post pin_comment (set in the brief / manifest); fall back to
    # a channel-default question that invites engagement
    PIN_DEFAULTS = {
        "claude-tricks": "Which part of this should I break down in detail next? 👇",
        "aashiqana":     "Which couple vibe should we do next? 💕 Comment below!",
    }
    pin_text = (post.get("pin_comment") or "").strip() or PIN_DEFAULTS.get(channel_key, "")
    if not pin_text:
        return

    token_path = Path(REPO) / "secrets" / token_file
    if not token_path.exists():
        log(f"  auto-pin: token file {token_path} not found, skipping")
        return

    cmd = [sys.executable, str(Path(REPO) / "scripts" / "yt_engage.py"),
           "--channel", channel_key, "--video", video_id,
           "--pin", pin_text]
    try:
        proc = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True, timeout=30)
        if proc.returncode == 0:
            log(f"  auto-pin OK on {video_id}: {pin_text[:60]!r}")
            # surface the Studio pin link in the factory event for one-click human pinning
            studio_link = ""
            for line in proc.stdout.splitlines():
                if "studio.youtube.com" in line:
                    studio_link = line.strip()
                    break
            supa.insert("factory_events", [{
                "kind": "pin_comment_posted",
                "message": f"{channel_key}: auto-comment posted on {video_id} — "
                           f"PIN IT: {studio_link}" if studio_link else
                           f"{channel_key}: auto-comment posted on {video_id}",
                "meta": {"post_id": post["id"], "video_id": video_id,
                         "pin_text": pin_text, "studio_link": studio_link},
            }])
        else:
            log(f"  auto-pin failed (exit {proc.returncode}): {proc.stderr[:200]}")
    except Exception as e:  # noqa: BLE001 -- must never kill the daemon
        log(f"  auto-pin exception: {e}")


def process_posts(supa):
    """Poll-cycle publisher. Uploads ARMED posts only -- drafts are NEVER touched --
    then lazily flips scheduled -> published once publish_at has passed."""
    try:
        armed = supa.select("factory_posts", "status=eq.armed&select=*&order=created_at.asc")
    except (RuntimeError, requests.RequestException) as e:
        log(f"posts poll failed: {e}")
        return
    for post in armed:
        try:
            publish_post(supa, post)
        except Exception as e:  # noqa: BLE001 -- publishing must never kill the daemon
            post_failed(supa, post, f"worker exception during publish: {e}")
    try:
        due = supa.select(
            "factory_posts",
            f"status=eq.scheduled&publish_at=lt.{utc_z()}&select=id,channel_key,yt_title,video_id")
        for p in due:
            supa.patch("factory_posts", f"id=eq.{p['id']}",
                       {"status": "published", "updated_at": now_iso()})
            supa.insert("factory_events", [{
                "kind": "post_published",
                "message": f"{p.get('channel_key')}: {p.get('yt_title')!r} is now live",
                "meta": {"post_id": p["id"], "video_id": p.get("video_id")},
            }])
            log(f"post {p['id']} flipped scheduled -> published")
    except (RuntimeError, requests.RequestException) as e:
        log(f"scheduled->published flip failed: {e}")


# ---------------------------------------------------------------- v4: daily auto-sync


_auto_sync_last_check = 0.0


def maybe_auto_sync(supa):
    """Queue the daily analytics_sync (model fable) once local time in
    factory_settings.auto_sync_tz passes auto_sync_hour. Double guard: skip if an
    analytics_sync job was already created today OR an 'auto_sync' event already
    fired today -- so it runs at most once per day."""
    global _auto_sync_last_check
    if time.time() - _auto_sync_last_check < AUTO_SYNC_CHECK_S:
        return
    _auto_sync_last_check = time.time()
    try:
        rows = supa.select("factory_settings",
                           "key=in.(auto_sync_hour,auto_sync_tz)&select=key,value")
        cfg = {r["key"]: (r.get("value") or "").strip() for r in rows}
        hour = cfg.get("auto_sync_hour") or "07:30"
        tzname = cfg.get("auto_sync_tz") or "Asia/Kolkata"
        try:
            hh, mm = (int(x) for x in hour.split(":", 1))
        except ValueError:
            log(f"auto-sync: bad auto_sync_hour {hour!r} (want HH:MM), skipping")
            return
        try:
            from zoneinfo import ZoneInfo
            now_local = datetime.now(ZoneInfo(tzname))
        except Exception:  # noqa: BLE001 -- a bad tz name must not kill the daemon
            log(f"auto-sync: unknown auto_sync_tz {tzname!r}, skipping")
            return
        if (now_local.hour, now_local.minute) < (hh, mm):
            return
        day_start_utc = utc_z(
            now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            .astimezone(timezone.utc))
        if supa.select("factory_jobs",
                       f"type=eq.analytics_sync&created_at=gte.{day_start_utc}&select=id&limit=1"):
            return
        if supa.select("factory_events",
                       f"kind=eq.auto_sync&ts=gte.{day_start_utc}&select=id&limit=1"):
            return
        created = supa.insert_returning("factory_jobs", [{
            "type": "analytics_sync",
            "channel_key": "_network",
            "title": f"Daily auto analytics sync ({hour} {tzname})",
            "prompt": "",
            "model": "sonnet",
            "effort": "low",
        }])
        job_id = created[0]["id"] if created else None
        supa.insert("factory_events", [{
            "kind": "auto_sync",
            "message": f"auto-queued daily analytics_sync (past {hour} {tzname})",
            "meta": {"job_id": job_id},
        }])
        log(f"auto-sync: queued daily analytics_sync job {job_id}")
    except (RuntimeError, requests.RequestException) as e:
        log(f"auto-sync check failed: {e}")


# ---------------------------------------------------------------- v6: job recaps


def _recap_str_list(val, cap):
    """Coerce to a list of trimmed non-empty strings, capped at `cap` items."""
    out = []
    for x in (val if isinstance(val, list) else []):
        s = str(x).strip()
        if s:
            out.append(s[:500])
        if len(out) >= cap:
            break
    return out


def sanitize_recap(data):
    """Strictly validate/trim a recap dict to RECAP_SCHEMA shape.
    Returns the normalized recap, or None if unusable (not a dict / no headline)."""
    if not isinstance(data, dict):
        return None
    headline = str(data.get("headline") or "").strip()
    if not headline:
        return None
    outputs = []
    raw_outputs = data.get("outputs")
    for o in (raw_outputs if isinstance(raw_outputs, list) else []):
        if isinstance(o, dict) and str(o.get("filename") or "").strip():
            outputs.append({
                "filename": str(o["filename"]).strip()[:300],
                "kind": str(o.get("kind") or "other").strip()[:50],
                "note": str(o.get("note") or "").strip()[:300],
            })
    return {
        "headline": headline[:500],
        "steps": _recap_str_list(data.get("steps"), 8),
        "decisions": _recap_str_list(data.get("decisions"), 4),
        "issues": _recap_str_list(data.get("issues"), 4),
        "outputs": outputs,
        "next": _recap_str_list(data.get("next"), 2),
    }


def parse_recap_text(text):
    """Model text output -> sanitized recap dict or None. Parsing is strict JSON;
    only surrounding prose/code fences are tolerated (outermost {...} span)."""
    s = (text or "").strip()
    a, b = s.find("{"), s.rfind("}")
    if a < 0 or b <= a:
        return None
    try:
        return sanitize_recap(json.loads(s[a:b + 1]))
    except (json.JSONDecodeError, ValueError):
        return None


def synthesize_recap(log_text, error=None):
    """Fallback summarizer: one QUICK `claude -p` haiku call over the log tail
    (+ the error on failed jobs) -> recap dict. Best-effort by contract: returns
    None on any problem and never raises -- a job never fails over a recap."""
    tail = (log_text or "")[-RECAP_LOG_TAIL_CHARS:]
    if error:
        tail += f"\n\nJOB FAILED with error:\n{str(error)[:2000]}"
    prompt = (
        "Summarize this job log into JSON exactly matching this schema: "
        f"{RECAP_SCHEMA}. "
        "Be honest and specific: real steps, decisions and problems from the log, not fluff. "
        + ("The job FAILED -- 'issues' MUST say what went wrong. " if error else "")
        + f"Output ONLY the JSON object. Log tail:\n{tail}"
    )
    try:
        child_env = os.environ.copy()
        child_env.pop("ANTHROPIC_API_KEY", None)  # subscription auth only, like the main run
        proc = subprocess.run(
            claude_argv("-p", prompt, "--model", "haiku", "--effort", "low",
                        "--output-format", "text"),
            cwd=str(REPO), capture_output=True, text=True,
            timeout=RECAP_TIMEOUT_S, env=child_env)
        if proc.returncode != 0:
            return None
        return parse_recap_text(proc.stdout)
    except Exception:  # noqa: BLE001 -- recap is optional, never let it hurt the job
        return None


# ---------------------------------------------------------------- v7: job control (stop + orphan reap)


def kill_proc_group(proc):
    """Terminate the child's WHOLE process tree. POSIX: SIGTERM the process group,
    STOP_GRACE_S grace, then SIGKILL. Windows: `taskkill /F /T` (kills the tree)
    with a proc.kill() fallback. The child is launched with _POPEN_GROUP_KW so its
    ffmpeg/Bash grandchildren are included. Never raises."""
    if IS_WINDOWS:
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=STOP_GRACE_S)
        except (OSError, subprocess.SubprocessError):
            try:
                proc.kill()
            except OSError:
                pass
        try:
            proc.wait(timeout=STOP_GRACE_S)
        except subprocess.TimeoutExpired:
            pass
        return
    try:
        pgid = os.getpgid(proc.pid)
    except (OSError, ProcessLookupError):
        pgid = proc.pid  # already reaped; killpg below becomes a no-op

    def _sig(s):
        try:
            os.killpg(pgid, s)
        except (OSError, ProcessLookupError):
            pass

    _sig(signal.SIGTERM)
    try:
        proc.wait(timeout=STOP_GRACE_S)
    except subprocess.TimeoutExpired:
        _sig(signal.SIGKILL)
        try:
            proc.wait(timeout=STOP_GRACE_S)
        except subprocess.TimeoutExpired:
            pass  # unkillable (D-state); proc.wait() upstream will collect it


def heartbeat_and_control(supa, job_id):
    """One round-trip: bump factory_jobs.heartbeat_at and read control back.
    Returns the control value ('' when unset or on ANY error -- a heartbeat
    hiccup must never affect the run)."""
    try:
        rows = supa.patch_returning("factory_jobs", f"id=eq.{job_id}",
                                    {"heartbeat_at": now_iso()}, select="control")
        if rows:
            return str(rows[0].get("control") or "").strip()
    except (RuntimeError, requests.RequestException) as e:
        log(f"  heartbeat failed (continuing): {e}")
    return ""


def reset_calendar_item(supa, job_id):
    """A stopped/orphaned job releases its calendar item back to its pre-queue
    status -- 'suggested' if the item came from an AI suggestion, else 'planned' --
    with job_id cleared. No-op when the job has no calendar item."""
    try:
        items = supa.select("factory_calendar", f"job_id=eq.{job_id}&select=id,origin")
    except (RuntimeError, requests.RequestException) as e:
        log(f"  calendar lookup failed for job {job_id}: {e}")
        return
    for it in items:
        status = "suggested" if it.get("origin") == "ai_suggestion" else "planned"
        try:
            supa.patch("factory_calendar", f"id=eq.{it['id']}",
                       {"status": status, "job_id": None})
            log(f"  calendar item {it['id']} reset to {status!r} (job {job_id})")
        except (RuntimeError, requests.RequestException) as e:
            log(f"  calendar reset failed for item {it['id']}: {e}")


def cancel_job(supa, job, buf):
    """control='stop' honored (child already dead): job -> 'cancelled' with error
    'stopped by user', control cleared, event 'job_stopped', calendar item reset."""
    job_id = job["id"]
    log(f"job {job_id} stopped by user")
    buf.add(f"[worker] job cancelled at {now_iso()}")
    try:
        supa.patch("factory_jobs", f"id=eq.{job_id}",
                   {"status": "cancelled", "finished_at": now_iso(),
                    "error": "stopped by user", "control": None, "logs": buf.text()})
        supa.insert("factory_events", [{
            "kind": "job_stopped",
            "message": f"job {job.get('title') or job_id!r} stopped by user",
            "meta": {"job_id": job_id, "channel_key": job.get("channel_key")},
        }])
    except (RuntimeError, requests.RequestException) as e:
        log(f"  cancel status update failed: {e}")
    if (job.get("type") or "") == "generate_asset":
        mark_asset_failed(supa, job_id)  # v9: stopped fragment -> asset 'failed'
    reset_calendar_item(supa, job_id)


# v11: transient failures self-heal. A job killed by an external signal (a
# stray pkill / another session's testing -- measured 5 Aug 2026: two claude
# children SIGTERMed in the same second by something outside this worker), an
# orphan reap after a daemon restart, or a network-blip worker exception is
# requeued ONCE (meta.retries). Deliberate failures -- spec aborts, acceptance
# gates, stop-by-user (those land 'cancelled', not 'failed') -- and second
# failures stay failed for the human revise flow.
RETRYABLE_ERROR_RE = re.compile(
    r"claude exited (?:143|137)\b|claude exited -(?:15|9)\b|orphaned:|"
    r"worker restarted mid-job|"
    r"worker exception: .*(?:Connection|Timeout|RemoteDisconnected|reset by peer)",
    re.I)


def maybe_auto_retry(supa, job, error):
    """Requeue a transiently-failed job once. Returns True when requeued."""
    if job is None:
        return False
    meta = dict(job.get("meta") or {})
    if int(meta.get("retries") or 0) >= 1:
        return False
    if not RETRYABLE_ERROR_RE.search(error or ""):
        return False
    meta["retries"] = int(meta.get("retries") or 0) + 1
    try:
        rows = supa.insert_returning("factory_jobs", [{
            "channel_key": job.get("channel_key"),
            "type": job.get("type"),
            "title": job.get("title"),
            "prompt": job.get("prompt"),
            "model": job.get("model"),
            "effort": job.get("effort"),
            "ultracode": bool(job.get("ultracode")),
            "status": "queued",
            "meta": meta,
        }])
        new_id = rows[0]["id"]
        # a retried fragment needs its asset row back in the queue; guarded so
        # a reviewer verdict set in the meantime is never overwritten
        aid = meta.get("asset_id")
        if (job.get("type") or "") == "generate_asset" and aid:
            supa.patch("factory_assets",
                       f"id=eq.{aid}&status=in.(failed,generating)",
                       {"status": "queued", "job_id": new_id,
                        "updated_at": now_iso()})
        supa.insert("factory_events", [{
            "kind": "job_auto_retried",
            "message": f"job {job.get('title') or job['id']!r} auto-requeued "
                       f"after transient failure (retry {meta['retries']}/1): "
                       f"{str(error)[:160]}",
            "meta": {"failed_job_id": job["id"], "retry_job_id": new_id,
                     "channel_key": job.get("channel_key")},
        }])
        log(f"  auto-retried as job {new_id} (retry {meta['retries']}/1)")
        return True
    except (RuntimeError, requests.RequestException) as e:
        log(f"  auto-retry failed (leaving job failed): {e}")
        return False


def reap_job(supa, j, error):
    """Mark a dead 'running' row failed, attempt the haiku failure-recap from its
    STORED logs (best effort, skipped for structured-result types), clear control,
    reset its calendar item, event 'orphan_reaped'."""
    job_id = j["id"]
    log(f"reaping orphaned job {job_id}: {error}")
    payload = {"status": "failed", "finished_at": now_iso(), "error": error,
               "control": None}
    if (j.get("type") or "custom") not in RECAP_SKIP_TYPES:
        recap = synthesize_recap(j.get("logs") or "", error=error)
        if recap:
            payload["result"] = {"recap": recap}
    try:
        supa.patch("factory_jobs", f"id=eq.{job_id}", payload)
        supa.insert("factory_events", [{
            "kind": "orphan_reaped",
            "message": f"job {j.get('title') or job_id!r} reaped: {error}",
            "meta": {"job_id": job_id, "channel_key": j.get("channel_key")},
        }])
    except (RuntimeError, requests.RequestException) as e:
        log(f"  orphan reap status update failed for {job_id}: {e}")
    if (j.get("type") or "") == "generate_asset":
        mark_asset_failed(supa, job_id)  # v9: orphaned fragment -> asset 'failed'
    reset_calendar_item(supa, job_id)
    maybe_auto_retry(supa, j, error)  # v11: orphans are transient by definition


ORPHAN_SELECT = "select=id,type,title,logs,channel_key,meta,prompt,model,effort,ultracode"


def reap_orphans(supa):
    """Startup reap: this worker is single-instance and JUST started, so any
    'running' job cannot be ours -- it died with a previous worker."""
    try:
        running = supa.select("factory_jobs", f"status=eq.running&{ORPHAN_SELECT}")
    except (RuntimeError, requests.RequestException) as e:
        log(f"startup orphan reap poll failed: {e}")
        return
    for j in running:
        reap_job(supa, j, "orphaned: worker restarted mid-job")


def reap_stale_jobs(supa, current_job_ids=None):
    """Defensive mid-loop reap: 'running' jobs whose heartbeat_at is older than
    STALE_REAP_S and that are not jobs THIS worker is currently running
    (v11: a set -- several can be live at once). The lt. filter naturally
    skips legacy rows with heartbeat_at null (SQL NULL < x is never true) --
    those are only reaped by the startup pass."""
    if isinstance(current_job_ids, str):  # tolerate the pre-v11 single-id call shape
        current_job_ids = {current_job_ids}
    current_job_ids = current_job_ids or set()
    cutoff = utc_z(datetime.now(timezone.utc) - timedelta(seconds=STALE_REAP_S))
    try:
        stale = supa.select("factory_jobs",
                            f"status=eq.running&heartbeat_at=lt.{cutoff}&{ORPHAN_SELECT}")
    except (RuntimeError, requests.RequestException) as e:
        log(f"stale-heartbeat reap poll failed: {e}")
        return
    for j in stale:
        if j["id"] in current_job_ids:
            continue
        reap_job(supa, j, f"orphaned: heartbeat stale for over {STALE_REAP_S // 60} minutes")


# ---------------------------------------------------------------- job runner


def run_shell_script_job(supa, job):
    """Execute a committed script directly — no claude -p. For owner-authorised
    sysadmin tasks (RDP, ngrok, etc.) that claude -p would refuse on safety grounds.
    job.meta.script_path = repo-relative path, e.g. 'deploy/rdp_ngrok_setup.ps1'."""
    job_id  = job["id"]
    meta    = job.get("meta") or {}
    script  = meta.get("script_path", "")
    if not script:
        fail(supa, job_id, "shell_script job missing meta.script_path", LogBuffer(), job=job)
        return

    full = os.path.join(REPO, script)
    if not os.path.isfile(full):
        fail(supa, job_id, f"script not found: {full}", LogBuffer(), job=job)
        return

    log(f"[shell_script] running {script}")
    buf = LogBuffer()
    try:
        supa.patch("factory_jobs", f"id=eq.{job_id}", {"heartbeat_at": now_iso()})
    except Exception:
        pass

    # v16: .py scripts dispatch through python3 so finalize_episode.py + other
    # deterministic Python steps can run under the shell_script job type without
    # a shell wrapper. meta.script_args is an optional list of extra CLI flags.
    extra_args = meta.get("script_args") or []
    if not isinstance(extra_args, list):
        extra_args = []
    if full.endswith(".ps1"):
        cmd = ["powershell.exe", "-NonInteractive", "-File", full,
               "-RepoRoot", REPO, *[str(a) for a in extra_args]]
    elif full.endswith(".py"):
        cmd = ["python3", full, *[str(a) for a in extra_args]]
    else:
        cmd = ["bash", full, *[str(a) for a in extra_args]]

    # Long GPU installs/inference stream silently for many minutes; this handler
    # stamped heartbeat_at only once at claim, so the cross-worker stale reaper
    # (STALE_REAP_S=180) on ANY other worker would orphan a job that runs >3 min.
    # The background heartbeat bumps heartbeat_at AND reads control back every 30s,
    # so a wedged shell_script is now killable: control='stop' or a wall-clock cap
    # (a silently-hung pip resolver has no timeout of its own) tears down the child.
    hb_stop = threading.Event()
    proc_box = {"p": None}
    started = time.time()
    SHJOB_MAX_S = 5400  # 90-min hard cap; a GPU install/inference past this is wedged

    def _shjob_heartbeat():
        while not hb_stop.wait(30):
            p = proc_box["p"]
            if p is None or p.poll() is not None:
                continue
            reason = None
            if heartbeat_and_control(supa, job_id) == "stop":
                reason = "stopped by user"
            elif time.time() - started > SHJOB_MAX_S:
                reason = f"exceeded {SHJOB_MAX_S // 60}min cap"
            if reason:
                log(f"  [shell_script] killing child ({reason})")
                buf.add(f"[shell] killing child ({reason})")
                proc_box["reason"] = reason
                try:
                    kill_proc_group(p)
                except Exception:  # noqa: BLE001 -- teardown must never raise here
                    pass
                hb_stop.set()
                return
    threading.Thread(target=_shjob_heartbeat, daemon=True,
                     name=f"shjob-hb-{job_id[:8]}").start()

    try:
        # own process group so kill_proc_group can take the whole ps1/python tree
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace",
                                **_POPEN_GROUP_KW)
        proc_box["p"] = proc
        output_lines = []
        for line in proc.stdout:
            line = line.rstrip()
            log(f"  {line}")
            buf.add(f"[shell] {line}")
            output_lines.append(line)
        proc.wait()
        rc = proc.returncode
    except Exception as e:
        fail(supa, job_id, f"failed to launch {script}: {e}", buf, job=job)
        return
    finally:
        hb_stop.set()

    output_text = "\n".join(output_lines)
    # Surface a headline marker line in the recap (sysadmin tunnels + GPU outputs)
    rdp_line = next((l for l in output_lines if any(
        m in l for m in ("RDP_CONNECT", "TUNNEL_URL", "RENDER_PATH", "SMOKE_OK"))), "")

    result = {
        "uploaded": 0,
        "recap": {
            "headline": f"shell_script {script} exited rc={rc}",
            "steps": [f"Ran {script} (exit {rc})", rdp_line] if rdp_line else [f"Ran {script} (exit {rc})"],
            "outputs": [rdp_line] if rdp_line else [],
            "issues": [] if rc == 0 else [f"Script exited {rc}"],
            "decisions": [],
            "next": [],
        },
        "script_output": output_text,
    }
    # a heartbeat-initiated teardown (control='stop' or the wall-clock cap) is not a
    # script failure: report it as cancelled and clear control so it isn't re-stopped
    kill_reason = proc_box.get("reason")
    if kill_reason:
        status, patch = "cancelled", {"control": None, "error": kill_reason}
    else:
        status, patch = ("done" if rc == 0 else "failed"), {}
    try:
        supa.patch("factory_jobs", f"id=eq.{job_id}",
                   {"status": status, "finished_at": now_iso(),
                    "result": result, "logs": buf.text(), **patch})
    except Exception as e:
        log(f"  could not finalize shell_script job: {e}")


def run_job(supa, job):
    job_id = job["id"]

    if (job.get("type") or "") == "analytics_sync":
        run_analytics_sync(supa, job)  # native, no claude call
        return

    if (job.get("type") or "") == "shell_script":
        # Owner-authorised sysadmin jobs that must NOT go through claude -p.
        # meta.script_path = repo-relative path to a committed .ps1/.sh script.
        # Runs the script directly; stdout/stderr go to logs + result recap.
        run_shell_script_job(supa, job)
        return

    log(f"claimed job {job_id} type={job.get('type')} channel={job.get('channel_key')} title={job.get('title')!r}")

    # v7: stamp the first heartbeat right away (context dumps can take a while,
    # and the stale reaper must never mistake a fresh claim for an orphan)
    try:
        supa.patch("factory_jobs", f"id=eq.{job_id}", {"heartbeat_at": now_iso()})
    except (RuntimeError, requests.RequestException) as e:
        log(f"  initial heartbeat failed (continuing): {e}")

    # v9: a generate_asset job is driven by its factory_assets row (spec +
    # revision notes + reviewer feedback); the claim also flips it to 'generating'
    asset = None
    if job.get("type") == "generate_asset":
        asset_id = (job.get("meta") or {}).get("asset_id")
        if not asset_id:
            fail(supa, job_id, "generate_asset job has no meta.asset_id", LogBuffer(), job=job)
            return
        try:
            rows = supa.select("factory_assets", f"id=eq.{asset_id}&select=*")
        except (RuntimeError, requests.RequestException) as e:
            fail(supa, job_id, f"could not fetch asset row {asset_id}: {e}", LogBuffer(), job=job)
            return
        if not rows:
            fail(supa, job_id, f"asset row {asset_id} not found", LogBuffer(), job=job)
            return
        asset = rows[0]
        if asset.get("status") in ("skipped", "superseded"):
            # reviewer skipped/replaced this version while the job sat queued -- don't generate
            try:
                supa.patch("factory_jobs", f"id=eq.{job_id}",
                           {"status": "cancelled", "finished_at": now_iso(),
                            "error": f"asset {asset.get('asset_key')} was "
                                     f"{asset.get('status')} before generation started"})
            except (RuntimeError, requests.RequestException) as e:
                log(f"  could not cancel job for {asset.get('status')} asset: {e}")
            return
        try:
            # guarded: never resurrect a verdict the reviewer set in the meantime
            supa.patch("factory_assets", f"id=eq.{asset_id}&status=eq.queued",
                       {"status": "generating", "updated_at": now_iso()})
        except (RuntimeError, requests.RequestException) as e:
            log(f"  could not mark asset {asset_id} generating (continuing): {e}")

    guidelines = ""
    if job.get("type") in ("produce_short", "plan_assets", "generate_asset") and job.get("channel_key"):
        try:
            rows = supa.select("factory_channels", f"key=eq.{job['channel_key']}&select=guidelines")
            if rows:
                guidelines = rows[0].get("guidelines") or ""
        except (RuntimeError, requests.RequestException) as e:
            log(f"  could not fetch channel guidelines: {e}")

    ctx_path = None
    if job.get("type") == "analyze_and_suggest":
        try:
            ctx_path = dump_analysis_context(supa, job_id)
            log(f"  wrote analysis context {ctx_path}")
        except (RuntimeError, requests.RequestException, OSError) as e:
            fail(supa, job_id, f"could not build analysis context: {e}", LogBuffer(), job=job)
            return
    elif job.get("type") == "suggest_brief":
        try:
            ctx_path = dump_brief_context(supa, job)
            log(f"  wrote brief context {ctx_path}")
        except (RuntimeError, requests.RequestException, OSError) as e:
            fail(supa, job_id, f"could not build brief context: {e}", LogBuffer(), job=job)
            return
    elif job.get("type") == "plan_content":
        try:
            ctx_path = dump_plan_content_context(supa, job)
            log(f"  wrote plan_content context {ctx_path}")
        except (RuntimeError, requests.RequestException, OSError) as e:
            fail(supa, job_id, f"could not build plan_content context: {e}", LogBuffer(), job=job)
            return
    elif job.get("type") == "assemble_episode":
        try:
            ctx_path = dump_staged_context(supa, job)
            log(f"  wrote staged assembly context {ctx_path}")
        except (RuntimeError, requests.RequestException, OSError) as e:
            fail(supa, job_id, f"could not build staged assembly context: {e}", LogBuffer(), job=job)
            return
    elif job.get("type") == "preview_episode":
        try:
            # draft preview also shows still-in-review revisions
            ctx_path = dump_staged_context(supa, job, include=("approved", "review"))
            log(f"  wrote draft preview context {ctx_path}")
        except (RuntimeError, requests.RequestException, OSError) as e:
            fail(supa, job_id, f"could not build draft preview context: {e}", LogBuffer(), job=job)
            return

    # v19: prompt branches select on the channel's TEMPLATE style (registry row,
    # legacy per-key fallback inside channel_template). Only the types whose
    # prompts branch on style need it.
    template = None
    if job.get("type") in ("produce_preview", "plan_content", "new_channel_scaffold"):
        template = channel_template(supa, job.get("channel_key"))

    prompt = build_prompt(job, guidelines, ctx_path=ctx_path, asset=asset, template=template)
    apply_global_override(supa, job)  # v13: global model/effort override (if enabled)
    cmd = build_command(job, prompt)

    child_env = os.environ.copy()
    child_env.pop("ANTHROPIC_API_KEY", None)  # subscription auth only -- never the API

    buf = LogBuffer()
    buf.add(f"[worker] starting claude for job {job_id} at {now_iso()}")

    def flush_logs():
        if not buf.dirty:
            return
        buf.dirty = False
        try:
            supa.patch("factory_jobs", f"id=eq.{job_id}", {"logs": buf.text()})
        except (RuntimeError, requests.RequestException) as e:
            log(f"  log flush failed: {e}")

    try:
        # v7: put claude in its OWN process group/session (cross-platform via
        # _POPEN_GROUP_KW), so a stop/timeout can kill the whole tree
        # (ffmpeg/Bash grandchildren included).
        proc = subprocess.Popen(cmd, cwd=str(REPO), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, bufsize=1,
                                env=child_env, **_POPEN_GROUP_KW)
    except OSError as e:
        fail(supa, job_id, f"could not start claude: {e}", buf, job=job)
        return

    def reader():
        for raw in proc.stdout:
            line = render_line(raw, buf)  # v16: buf receives usage from `result` event
            if line:
                buf.add(line)
        proc.stdout.close()

    t = threading.Thread(target=reader, daemon=True)
    t.start()

    started = time.time()
    last_beat = 0.0
    timed_out = stopped = False
    while proc.poll() is None:
        if time.time() - started > JOB_TIMEOUT_S:
            timed_out = True
            buf.add(f"[worker] TIMEOUT after {JOB_TIMEOUT_S}s -- killing claude (whole process group)")
            kill_proc_group(proc)
            break
        # v7: every ~LOG_FLUSH_S, bump heartbeat_at and read control back
        if time.time() - last_beat >= LOG_FLUSH_S:
            last_beat = time.time()
            if heartbeat_and_control(supa, job_id) == "stop":
                stopped = True
                buf.add("[worker] STOP requested by user -- terminating claude "
                        f"(SIGTERM whole process group, {STOP_GRACE_S}s grace, then SIGKILL)")
                kill_proc_group(proc)
                break
        time.sleep(1)
        flush_logs()

    proc.wait()
    t.join(timeout=10)
    flush_logs()

    if stopped:
        cancel_job(supa, job, buf)
        return
    if timed_out:
        fail(supa, job_id, f"timed out after {JOB_TIMEOUT_S // 60} minutes", buf, job=job)
        return
    if proc.returncode != 0:
        tail = buf.text()[-4000:]
        fail(supa, job_id, f"claude exited {proc.returncode}. Log tail:\n{tail}", buf, job=job)
        return

    # exit 0 -> collect results
    if job.get("type") == "suggest_brief":
        # v4: the brief JSON IS the result -- no manifest, no renders
        bpath = brief_path(job_id)
        try:
            brief = json.loads(bpath.read_text())
        except (OSError, json.JSONDecodeError) as e:
            fail(supa, job_id,
                 f"suggest_brief finished but the brief JSON is missing/unreadable ({bpath}): {e}",
                 buf, job=job)
            return
        if not str(brief.get("title") or "").strip() or not str(brief.get("brief") or "").strip():
            fail(supa, job_id, "suggest_brief JSON lacks a non-empty title/brief", buf, job=job)
            return
        uploaded = 0
        result = {"title": brief["title"], "brief": brief["brief"],
                  "tags": brief.get("tags") or []}
        done_msg = f"suggest_brief '{job.get('title') or job_id}' done: {str(brief['title'])[:120]!r}"
        buf.add(f"[worker] brief {str(brief['title'])[:120]!r} stored in job.result")
    elif job.get("type") == "plan_content":
        # v17: the ranked ideas JSON IS the result -- no manifest, no renders
        ppath = plan_content_path(job_id)
        try:
            plan = json.loads(ppath.read_text())
        except (OSError, json.JSONDecodeError) as e:
            fail(supa, job_id,
                 f"plan_content finished but the ideas JSON is missing/unreadable ({ppath}): {e}",
                 buf, job=job)
            return
        ideas = plan.get("ideas") if isinstance(plan, dict) else None
        if not isinstance(ideas, list) or not ideas:
            fail(supa, job_id, "plan_content JSON has no 'ideas' list", buf, job=job)
            return
        # keep only well-formed ideas, sorted by rank
        clean = [i for i in ideas if isinstance(i, dict)
                 and str(i.get("title") or "").strip() and str(i.get("brief") or "").strip()]
        clean.sort(key=lambda i: i.get("rank", 99))
        if not clean:
            fail(supa, job_id, "plan_content ideas all lack a title/brief", buf, job=job)
            return
        uploaded = 0
        result = {"ideas": clean}
        done_msg = (f"plan_content '{job.get('channel_key')}' done: {len(clean)} idea(s), "
                    f"top: {str(clean[0]['title'])[:80]!r}")
        buf.add(f"[worker] {len(clean)} content ideas stored in job.result")
    elif job.get("type") == "channel_intake":
        # v18: the wizard options JSON IS the result -- no manifest, no renders
        ipath = channel_intake_path(job_id)
        try:
            data = json.loads(ipath.read_text())
        except (OSError, json.JSONDecodeError) as e:
            fail(supa, job_id,
                 f"channel_intake finished but the options JSON is missing/unreadable ({ipath}): {e}",
                 buf, job=job)
            return
        opts = data.get("options") if isinstance(data, dict) else None
        if not isinstance(opts, list) or not opts:
            fail(supa, job_id, "channel_intake JSON has no 'options' list", buf, job=job)
            return
        clean = []
        for o in opts:
            if not isinstance(o, dict):
                continue
            value = str(o.get("value") or o.get("label") or "").strip()
            if not value:
                continue
            clean.append({"label": str(o.get("label") or value).strip()[:48], "value": value})
        clean = clean[:6]
        if not clean:
            fail(supa, job_id, "channel_intake options all lack a value", buf, job=job)
            return
        uploaded = 0
        result = {"options": clean, "question": data.get("question"),
                  "ready_to_advance": bool(data.get("ready_to_advance", True))}
        done_msg = f"channel_intake done: {len(clean)} option(s)"
        buf.add(f"[worker] {len(clean)} wizard options stored in job.result")
    elif job.get("type") == "new_channel_scaffold":
        # v18: the scaffold JSON IS the result. bringup hands the app a ready Ep01
        # brief (result.first_episode) to auto-produce; freeze_baseline confirms the
        # blueprint is locked. Files created on disk are the real side effect; the
        # JSON is best-effort context, so a missing/partial one is non-fatal.
        phase = str((job.get("meta") or {}).get("phase") or "bringup")
        spath = channel_scaffold_path(job_id)
        result = {"phase": phase}
        try:
            data = json.loads(spath.read_text())
            if isinstance(data, dict):
                result.update(data)
        except (OSError, json.JSONDecodeError) as e:
            buf.add(f"[worker] note: no/invalid scaffold JSON at {spath}: {e}")
        # recap synthesized from the log tail so the Jobs drawer explains what happened
        recap = synthesize_recap(buf.text())
        if recap:
            result["recap"] = recap
        uploaded = 0
        if phase == "freeze_baseline":
            done_msg = (f"baseline frozen for '{job.get('channel_key')}'"
                        + (f" (ep {result.get('baseline_ep')})" if result.get("baseline_ep") else ""))
        else:
            fe = result.get("first_episode") or {}
            done_msg = (f"channel '{job.get('channel_key')}' scaffolded"
                        + (f" — Ep01: {str(fe.get('title'))[:80]!r}" if fe.get("title") else ""))
        buf.add(f"[worker] new_channel_scaffold {phase} result stored in job.result")
    elif job.get("type") == "plan_assets":
        # v9: the plan JSON becomes factory_assets rows + generate_asset jobs
        result = ingest_asset_plan(supa, job, buf)
        if result is None:
            return  # ingest already failed the job (and released the calendar item)
        uploaded = 0
        done_msg = (f"plan_assets '{job.get('title') or job_id}' done "
                    f"({result.get('planned', 0)} asset(s) planned)")
    elif job.get("type") == "generate_asset":
        # v9: one fragment uploaded; v1 auto-approves (factory QC), revisions -> review
        result = finish_generate_asset(supa, job, asset, buf)
        if result is None:
            return  # already failed the job (and flipped the asset row to 'failed')
        uploaded = 1
        done_msg = (f"generate_asset '{job.get('title') or job_id}' done "
                    f"({result.get('landed', 'ready')})")
    elif job.get("type") == "preview_episode":
        # v10: draft preview uploaded onto the calendar item (never published)
        result = finish_preview_episode(supa, job, buf)
        if result is None:
            return  # already failed the job
        uploaded = 1
        done_msg = f"draft preview ready for '{job.get('title') or job_id}'"
    else:
        # manifest -> upload (+ contributor credits + draft posts for videos)
        mpath = manifest_path(job_id)
        uploaded = drafts = 0
        recap = None
        if mpath.exists():
            try:
                manifest = json.loads(mpath.read_text())
            except (json.JSONDecodeError, OSError) as e:
                manifest = {"summary": f"manifest unreadable: {e}", "files": []}
            summary = manifest.get("summary") or "(no summary in manifest)"
            recap = sanitize_recap(manifest.get("recap"))  # v6: run wrote its own recap
            uploaded, drafts = upload_manifest_files(supa, job, manifest)
            # v16: make the produce_preview raw watchable in the Studio program
            # monitor (it drafts no post, so preview_path is its only review hook).
            if job.get("type") == "produce_preview":
                stamp_preview_from_render(supa, job, buf)
        else:
            summary = "completed, but no manifest was written (nothing uploaded)"
            buf.add(f"[worker] note: no manifest at {mpath}")

        result = {"summary": summary, "uploaded": uploaded, "posts": drafts}
        if recap is None:
            # v6: manifest lacked a usable recap -- synthesize one from the log
            # tail with a quick haiku call (best effort, never fails the job)
            recap = synthesize_recap(buf.text())
            buf.add("[worker] recap synthesized from log tail (haiku)" if recap
                    else "[worker] note: no recap (manifest had none, haiku fallback failed)")
        if recap:
            result["recap"] = recap
        if job.get("type") == "analyze_and_suggest":
            n_sugg, analysis_summary, n_ins = ingest_suggestions(supa, job, buf)
            result.update({"suggestions": n_sugg, "analysis_summary": analysis_summary,
                           "insights": n_ins})
        done_msg = (f"{job.get('type')} '{job.get('title') or job_id}' done "
                    f"({uploaded} file(s) uploaded"
                    + (f", {drafts} draft post(s)" if drafts else "") + ")")

    buf.add(f"[worker] done at {now_iso()} -- uploaded {uploaded} file(s)")
    buf.dirty = True
    # v16: attach the CLI's own cost + token totals to the job result so any
    # dashboard rollup (or a later plan_post reader) can pull real $ per job
    if getattr(buf, "usage", None):
        result["usage"] = buf.usage
    try:
        supa.patch("factory_jobs", f"id=eq.{job_id}",
                   {"status": "done", "finished_at": now_iso(), "result": result, "logs": buf.text()})
        supa.insert("factory_events", [{
            "kind": "job_done",
            "message": done_msg,
            "meta": {"job_id": job_id, "channel_key": job.get("channel_key"), "uploaded": uploaded},
        }])
    except (RuntimeError, requests.RequestException) as e:
        log(f"  final status update failed: {e}")
    # v9: staged jobs must never flip the calendar via the job_id join --
    # calendar.job_id points at the PLAN job, so a finished plan_assets (or a
    # fragment) would wrongly mark the item produced. Exactly one produced-flip
    # happens at assembly completion, keyed explicitly by meta.calendar_id.
    if job.get("type") == "assemble_episode":
        mark_calendar_produced_by_id(supa, (job.get("meta") or {}).get("calendar_id"))
    elif job.get("type") not in ("plan_assets", "generate_asset", "preview_episode",
                                 "produce_preview"):
        # v16: produce_preview is only a PREVIEW — calendar.job_id points at it, but
        # the episode is not 'produced' until scripts/finalize_episode.py masters +
        # arms it (finalize flips the item to produced itself, via --calendar-id).
        # Flipping here would falsely mark a preview-only (or QC-blocked) item done.
        mark_calendar_produced(supa, job_id)
    log(f"job {job_id} done, uploaded={uploaded}")


def fail(supa, job_id, error, buf, job=None):
    log(f"job {job_id} FAILED: {error[:300]}")
    payload = {"status": "failed", "finished_at": now_iso(), "error": error[:8000],
               "logs": buf.text()}
    # v6: failures are where recaps matter most -- when the caller passes the job
    # (claude jobs; suggest_brief/analytics_sync are skipped, their results are
    # already structured), summarize log tail + error into result.recap with
    # issues populated. Best effort: recap absent is fine, never fail over it.
    if job is not None and (job.get("type") or "custom") not in RECAP_SKIP_TYPES:
        recap = synthesize_recap(buf.text(), error=error)
        if recap:
            payload["result"] = {"recap": recap}
    try:
        supa.patch("factory_jobs", f"id=eq.{job_id}", payload)
        supa.insert("factory_events", [{
            "kind": "job_failed",
            "message": f"job {job_id} failed: {error[:300]}",
            "meta": {"job_id": job_id},
        }])
    except (RuntimeError, requests.RequestException) as e:
        log(f"  failure status update also failed: {e}")
    # v9 staged failure paths: a dead fragment flips its asset row to 'failed';
    # a dead plan releases its calendar item back to planned/suggested (the item's
    # job_id points at the plan job, so the existing reset path keys correctly)
    if job is not None and (job.get("type") or "") == "generate_asset":
        mark_asset_failed(supa, job_id)
    if job is not None and (job.get("type") or "") == "plan_assets":
        reset_calendar_item(supa, job_id)
    # v11: transient failures (external SIGTERM, restarts, network blips)
    # requeue themselves once instead of waiting for a human
    maybe_auto_retry(supa, job, error)


# ---------------------------------------------------------------- modes


def dry_run():
    fake = {
        "id": "00000000-0000-0000-0000-000000000000",
        "channel_key": "claude-tricks",
        "type": "produce_short",
        "title": "DRY RUN fake job",
        "prompt": "30s short: the one Claude Code flag beginners never use.",
        "model": "opus",
        "effort": "high",
    }
    guidelines = playbook_guidelines("claude-tricks") or "(guidelines would be fetched from factory_channels)"
    prompt = build_prompt(fake, guidelines)
    cmd = build_command(fake, prompt)
    print("--- DRY RUN (nothing executed) ---")
    print(f"cwd: {REPO}")
    print("exact command:")
    print(shlex.join(cmd))

    fake2 = {
        "id": "11111111-1111-1111-1111-111111111111",
        "channel_key": "_network",
        "type": "custom",
        "title": "DRY RUN fake fable+ultracode job",
        "prompt": "Say hello to the factory.",
        "model": "fable",
        "effort": "xhigh",
        "ultracode": True,
    }
    prompt2 = build_prompt(fake2)
    cmd2 = build_command(fake2, prompt2)
    print()
    print("--- DRY RUN #2: model=fable ultracode=true ---")
    print(f"model mapping: fable -> {map_model('fable')}")
    print(f"prompt first line: {prompt2.splitlines()[0]!r}")
    print("exact command:")
    print(shlex.join(cmd2))

    fake3 = {
        "id": "22222222-2222-2222-2222-222222222222",
        "channel_key": "claude-tricks",
        "type": "suggest_brief",
        "title": "DRY RUN brief suggestion: claude-tricks",
        "prompt": "one beginner Claude Code trick",
        "model": "sonnet",
        "effort": "medium",
    }
    prompt3 = build_prompt(fake3, ctx_path=brief_ctx_path(fake3["id"]))
    cmd3 = build_command(fake3, prompt3)
    print()
    print("--- DRY RUN #3: suggest_brief (worker would write the ctx file first) ---")
    print(f"brief lands in: {brief_path(fake3['id'])} -> job.result")
    print("exact command:")
    print(shlex.join(cmd3))

    fake_post = {
        "id": "33333333-3333-3333-3333-333333333333",
        "channel_key": "claude-tricks",
        "local_path": str(RENDERS_OUT / "fake_ep.mp4"),
        "yt_title": "DRY RUN fake armed post",
        "yt_description": "fake description (worker would write it to the desc file)",
        "tags": ["ai", "claude code"],
        "publish_at": "2027-01-01T15:00:00+00:00",
        "audience": "notForKids",
        "synthetic": True,
        "status": "armed",
    }
    cmd4 = build_publish_command(fake_post, UPLOAD_DEFAULTS["claude-tricks"],
                                 desc_path=RENDERS_OUT / f"post_desc_{fake_post['id']}.txt")
    print()
    print("--- DRY RUN #4: armed-post publish command (constructed, NOT executed) ---")
    print(f"fake post: status={fake_post['status']} publish_at={fake_post['publish_at']}"
          f" -> --publish-at {rfc3339_utc(fake_post['publish_at'])}")
    print("exact command:")
    print(shlex.join(cmd4))

    fake5 = {
        "id": "44444444-4444-4444-4444-444444444444",
        "channel_key": "lulla",
        "type": "plan_assets",
        "title": "DRY RUN staged plan: fireflies lullaby",
        "prompt": "Bedtime episode brief: Pip meets the fireflies by the moonlit pond.",
        "model": "fable",
        "effort": "high",
        "meta": {"calendar_id": "cccccccc-cccc-cccc-cccc-cccccccccccc"},
    }
    prompt5 = build_prompt(fake5, playbook_guidelines("pip-moonlit-garden"))
    cmd5 = build_command(fake5, prompt5)
    print()
    print("--- DRY RUN #5: plan_assets (staged) ---")
    print(f"plan lands in: {assets_plan_path(fake5['id'])} -> factory_assets rows "
          "+ one generate_asset job per asset")
    print("exact command:")
    print(shlex.join(cmd5))

    fake_asset = {
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "calendar_id": fake5["meta"]["calendar_id"],
        "channel_key": "lulla",
        "asset_key": "scene_03_still",
        "version": 2,
        "group_key": "scene",
        "kind": "image",
        "title": "Scene 3: fireflies over the pond",
        "spec": {"prompt": "Fireflies drifting over the moonlit pond, storybook style.",
                 "params": {"aspect": "16:9"},
                 "revision_notes": ["make the fireflies warmer and fewer"]},
        "notes": "make the fireflies warmer and fewer",
    }
    fake6 = {
        "id": "55555555-5555-5555-5555-555555555555",
        "channel_key": "lulla",
        "type": "generate_asset",
        "title": "Asset: scene_03_still — DRY RUN staged plan",
        "prompt": "Staged asset scene_03_still v2 (spec lives in factory_assets)",
        "model": "fable",
        "effort": "medium",
        "meta": {"calendar_id": fake_asset["calendar_id"], "asset_id": fake_asset["id"],
                 "asset_key": "scene_03_still", "version": 2},
    }
    prompt6 = build_prompt(fake6, playbook_guidelines("pip-moonlit-garden"), asset=fake_asset)
    cmd6 = build_command(fake6, prompt6)
    print()
    print("--- DRY RUN #6: generate_asset (worker would fetch the asset row + mark it 'generating') ---")
    print(f"output contract: {asset_out_path(fake6['id'])} -> upload + asset row 'review'")
    print("exact command:")
    print(shlex.join(cmd6))

    fake7 = {
        "id": "66666666-6666-6666-6666-666666666666",
        "channel_key": "lulla",
        "type": "assemble_episode",
        "title": "DRY RUN staged assembly: fireflies lullaby",
        "prompt": "",
        "model": "fable",
        "effort": "high",
        "meta": {"calendar_id": fake5["meta"]["calendar_id"]},
    }
    prompt7 = build_prompt(fake7, ctx_path=staged_ctx_path(fake7["id"]))
    cmd7 = build_command(fake7, prompt7)
    print()
    print("--- DRY RUN #7: assemble_episode (worker would write the staged ctx file first) ---")
    print(f"manifest lands in: {manifest_path(fake7['id'])} -> renders + draft posts, "
          f"then calendar item {fake7['meta']['calendar_id']} -> 'produced'")
    print("exact command:")
    print(shlex.join(cmd7))
    print("--- END DRY RUN ---")


# ---------------------------------------------------------------- self-upgrade
# The supervisors already auto-HEAL: launchd (KeepAlive), run-worker.ps1 (a
# while-loop), and systemd (Restart=always) all relaunch the process on ANY exit.
# So auto-UPGRADE is simply: when idle, fast-forward the checkout to
# origin/<current-branch> and exit(0) -- the supervisor relaunches us on the new
# code within seconds. Push to the branch a worker tracks (main, in production)
# and every idle worker upgrades itself within SELF_UPDATE_S. Disable per-host
# with FACTORY_AUTO_UPDATE=0.
SELF_UPDATE_S = 300  # how often an idle worker checks origin for new commits
_self_update_state = {"at": 0.0}


def _git(args, timeout=120):
    """Run one git command inside the repo -> (returncode, stdout, stderr)."""
    p = subprocess.run(["git", *args], cwd=str(REPO), capture_output=True,
                       text=True, timeout=timeout)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def maybe_self_update(supa, active):
    """When idle, fast-forward to origin/<current-branch> and restart onto it.

    Fast-forward ONLY -- never clobbers local commits or a dirty tree; a diverged
    or FF-blocked checkout logs a warning and is left for a human. A py_compile
    gate rolls the update back if the new worker code wouldn't even parse, so a
    bad commit can't put the fleet in a crash-restart loop. No-op when busy,
    disabled (FACTORY_AUTO_UPDATE=0), throttled, offline, or already current."""
    if os.environ.get("FACTORY_AUTO_UPDATE", "1") == "0" or active:
        return
    now = time.time()
    if now - _self_update_state["at"] < SELF_UPDATE_S:
        return
    _self_update_state["at"] = now
    try:
        rc, branch, _ = _git(["rev-parse", "--abbrev-ref", "HEAD"], timeout=30)
        if rc != 0 or not branch or branch == "HEAD":
            return  # git error or detached HEAD -- don't touch it
        if _git(["fetch", "--quiet", "origin", branch], timeout=120)[0] != 0:
            return  # offline / transient -- retry next window
        _, local, _ = _git(["rev-parse", "HEAD"], timeout=30)
        _, remote, _ = _git(["rev-parse", f"origin/{branch}"], timeout=30)
        if not local or not remote or local == remote:
            return  # already up to date
        # advance only if our HEAD is an ancestor of the remote (a clean FF)
        if _git(["merge-base", "--is-ancestor", "HEAD", f"origin/{branch}"])[0] != 0:
            log(f"auto-update: local diverged from origin/{branch}; skipping "
                "(manual reconcile needed)", level="warn")
            return
        rc, _, err = _git(["merge", "--ff-only", f"origin/{branch}"], timeout=120)
        if rc != 0:
            log("auto-update: fast-forward blocked -- likely local changes to "
                f"tracked files: {err[:180]}", level="warn")
            return
        # safety gate: never restart into a worker that won't even parse
        chk = subprocess.run([sys.executable, "-m", "py_compile",
                              str(SCRIPTS_DIR / "factory_worker.py")],
                             capture_output=True, text=True, timeout=60)
        if chk.returncode != 0:
            _git(["reset", "--hard", local], timeout=60)
            log(f"auto-update: new code fails py_compile; rolled back to {local[:7]} "
                f"({(chk.stderr or '').strip()[:180]})", level="error")
            return
        log(f"auto-update: {branch} {local[:7]} -> {remote[:7]}; restarting to load "
            "new code")
        _push_logs(supa, _drain_log_ring())  # surface the restart on the dashboard
        sys.exit(0)  # supervisor relaunches us on the fresh checkout
    except (OSError, subprocess.SubprocessError) as e:
        log(f"auto-update check failed (will retry): {e}", level="warn")


def ensure_utf8_mode():
    """Windows defaults open()/Path.read_text() to the locale codec (cp1252),
    which chokes on UTF-8 repo files (PRODUCTION-PLAYBOOK.md, manifests, etc.).
    Re-exec once in Python UTF-8 mode so every text read/write is UTF-8 no matter
    how the worker was launched, and export PYTHONUTF8 so child python subprocesses
    (network_stats.py, yt_upload.py, ...) inherit it. No-op off Windows / already-on."""
    if os.name != "nt" or sys.flags.utf8_mode:
        return
    os.environ["PYTHONUTF8"] = "1"
    if os.environ.get("FACTORY_UTF8_REEXEC") != "1":
        os.environ["FACTORY_UTF8_REEXEC"] = "1"
        try:
            os.execv(sys.executable, [sys.executable, "-X", "utf8", *sys.argv])
        except OSError:
            pass  # re-exec failed; PYTHONUTF8 is still set for any children


def main():
    ensure_utf8_mode()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--once", action="store_true", help="single claim attempt, then exit")
    ap.add_argument("--dry-run", action="store_true", help="print the exact claude command for a fake job; execute nothing")
    args = ap.parse_args()

    if args.dry_run:
        dry_run()
        return

    env = load_env()  # exits with a clear message if SUPABASE_SERVICE_KEY is missing
    # Propagate non-secret tuning knobs into the process env so the GPU/encode
    # settings reach child render subprocesses (ffmpeg helper, Remotion). Secrets
    # (service key etc.) are deliberately NOT exported to job children.
    # FACTORY_REMOTION_SCALE/_CRF must be here or a worker-run produce silently
    # ships 1080p while an interactive run on the same commit ships 4K — the
    # nastiest kind of divergence, because nothing errors.
    for _k in ("FACTORY_FFMPEG_HWACCEL", "FACTORY_FFMPEG", "FACTORY_REMOTION_GL",
               "FACTORY_REMOTION_CONCURRENCY", "FACTORY_REMOTION_HWACCEL",
               "FACTORY_REMOTION_SCALE", "FACTORY_REMOTION_CRF"):
        if env.get(_k):
            os.environ.setdefault(_k, env[_k])
    supa = Supa(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
    RENDERS_OUT.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)

    try:
        seed_channels(supa)
        seed_generators(supa)
        seed_settings(supa)
        supa.insert("factory_events", [{"kind": "worker_start", "message": "factory worker started",
                                        "meta": {"once": args.once}}])
    except (RuntimeError, requests.RequestException) as e:
        log(f"WARNING: startup seeding failed (continuing): {e}")

    # v7: single-instance worker just started -> any 'running' row is an orphan
    reap_orphans(supa)

    # v11: parallel execution. Each claimed job runs in its own thread; the
    # claim RPC excludes HEAVY_TYPES while a heavy job is live, so cpu-bound
    # assembly/renders stay strictly serial while light claude/API jobs
    # (asset generation, planning, briefs) fill the remaining slots.
    max_parallel = 1 if args.once else max(1, int(env.get("FACTORY_MAX_PARALLEL")
                                                  or MAX_PARALLEL_JOBS))
    try:
        register_worker(supa, max_parallel)
    except (RuntimeError, requests.RequestException) as e:
        log(f"WARNING: worker registration failed (continuing): {e}")
    log(f"worker ready -- polling for jobs (parallel x{max_parallel}, heavy serial)"
        + (" (--once)" if args.once else ""))
    active = {}  # job_id -> (thread, job_type)
    hb_state = {"paused": False, "accept": None, "at": 0.0}  # cached routing config

    def _run_in_thread(job):
        try:
            run_job(supa, job)
        except Exception as e:  # noqa: BLE001 -- a job must never kill the daemon
            fail(supa, job["id"], f"worker exception: {e}", LogBuffer(), job=job)

    while True:
        for jid in [j for j, (t, _) in active.items() if not t.is_alive()]:
            active.pop(jid)

        # v18: when idle, self-upgrade to origin/<branch> and restart on new code.
        # Placed outside every try/except Exception below so its sys.exit(0) is not
        # swallowed. Skipped for --once so a one-shot run never restarts itself.
        if not args.once:
            maybe_self_update(supa, active)

        # v14: heartbeat + reload this worker's routing config every ~20s. Cheap,
        # and lets the dashboard pause the worker / change its accepted job types
        # live. Failures are swallowed (returns defaults) so claiming never stalls.
        if time.time() - hb_state["at"] >= WORKER_HEARTBEAT_S:
            paused, accept = worker_heartbeat(supa)
            if paused != hb_state["paused"]:
                log(f"worker {'PAUSED' if paused else 'RESUMED'} via dashboard")
            if accept != hb_state["accept"]:
                log(f"accept_types -> {accept if accept else 'ALL'}")
            hb_state.update(paused=paused, accept=accept, at=time.time())
            # v15: push buffered log lines to Supabase (dashboard Workers page)
            _push_logs(supa, _drain_log_ring())

        claimed = False
        if not hb_state["paused"] and len(active) < max_parallel:
            heavy_live = any(tp in HEAVY_TYPES for _, tp in active.values())
            exclude = list(HEAVY_TYPES) if heavy_live else []
            accept = hb_state["accept"]  # None = all types
            try:
                jobs = supa.rpc("factory_claim_job_v3",
                                {"p_worker_id": WORKER_ID, "exclude_types": exclude,
                                 "accept_types": accept}) or []
            except (RuntimeError, requests.RequestException):
                # v3 RPC missing (old DB) -> v2 (no routing), then v1 serial when idle
                try:
                    jobs = supa.rpc("factory_claim_job_v2", {"exclude_types": exclude}) or []
                except (RuntimeError, requests.RequestException):
                    if active:
                        jobs = []
                    else:
                        try:
                            jobs = supa.rpc("factory_claim_job") or []
                        except (RuntimeError, requests.RequestException) as e2:
                            log(f"claim failed: {e2}")
                            jobs = []
            if jobs:
                job = jobs[0] if isinstance(jobs, list) else jobs
                claimed = True
                t = threading.Thread(target=_run_in_thread, args=(job,), daemon=True,
                                     name=f"job-{job['id'][:8]}")
                active[job["id"]] = (t, job.get("type") or "")
                t.start()
                log(f"started job thread ({len(active)}/{max_parallel} slots, "
                    f"type={job.get('type')})")
        # v4: per-cycle extras -- publish armed posts, flip scheduled->published,
        # queue the daily analytics_sync, reap stale-heartbeat orphans (v7).
        # Never allowed to kill the daemon.
        try:
            process_posts(supa)
            maybe_auto_sync(supa)
            reap_stale_jobs(supa, current_job_ids=set(active))
        except Exception as e:  # noqa: BLE001
            log(f"poll-cycle extras failed: {e}")
        if args.once:
            for t, _ in list(active.values()):
                t.join()
            break
        if not claimed:
            time.sleep(POLL_SLEEP_S)


if __name__ == "__main__":
    main()
