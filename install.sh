#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# AI YouTube factory — local worker installer.
#
# Sets up the factory worker on any machine that has the Claude Code CLI.
# The worker claims jobs from Supabase and runs them with `claude -p` using THIS
# machine's Claude subscription (no Anthropic API key involved).
#
#   ./install.sh              interactive setup (config + deps + optional service)
#   ./install.sh --no-service just config + deps, don't install a background service
#
# Safe to re-run: it never overwrites an existing secrets/factory.env or .env.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO"

NO_SERVICE=0
[[ "${1:-}" == "--no-service" ]] && NO_SERVICE=1

say()  { printf '\033[1;36m▸ %s\033[0m\n' "$*"; }
ok()   { printf '\033[1;32m✓ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m! %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

# ── 1. Claude Code CLI ───────────────────────────────────────────────────────
say "Checking for the Claude Code CLI…"
if ! command -v claude >/dev/null 2>&1; then
  die "'claude' not found on PATH. Install Claude Code and sign in first:
     https://docs.claude.com/en/docs/claude-code
   Then re-run ./install.sh"
fi
ok "claude found: $(command -v claude)"
warn "Make sure you've run 'claude' once and signed in (subscription auth). The"
warn "worker runs jobs as you — it never uses an ANTHROPIC_API_KEY."

# ── 2. Python + deps ─────────────────────────────────────────────────────────
say "Locating python3…"
PYTHON="$(command -v python3 || true)"
[[ -n "$PYTHON" ]] || die "python3 not found. Install Python 3.9+ and re-run."
ok "python3: $PYTHON ($("$PYTHON" -V 2>&1))"

say "Installing Python dependencies (requirements.txt)…"
if "$PYTHON" -m pip install -r requirements.txt >/tmp/factory_pip.log 2>&1; then
  ok "dependencies installed"
else
  warn "pip install hit an issue — trying --user…"
  "$PYTHON" -m pip install --user -r requirements.txt >/tmp/factory_pip.log 2>&1 \
    || die "dependency install failed. See /tmp/factory_pip.log"
  ok "dependencies installed (--user)"
fi

# ── 3. Config files ──────────────────────────────────────────────────────────
say "Setting up config…"
mkdir -p secrets logs renders_out

if [[ -f secrets/factory.env ]]; then
  ok "secrets/factory.env already exists — leaving it untouched"
else
  cp deploy/factory.env.example secrets/factory.env
  warn "Created secrets/factory.env from template — EDIT IT before starting:"
  warn "  set SUPABASE_URL and SUPABASE_SERVICE_KEY (service_role key)"
fi

if [[ -f .env ]]; then
  ok ".env already exists — leaving it untouched"
else
  cp deploy/api-keys.env.example .env
  ok "Created .env for generation API keys (optional — fill in as needed)"
fi

# ── 4. Verify the worker can construct a job (no queue hit) ──────────────────
say "Smoke-testing the worker (--dry-run, executes nothing)…"
if FACTORY_REPO="$REPO" "$PYTHON" scripts/factory_worker.py --dry-run >/tmp/factory_dry.log 2>&1; then
  ok "worker dry-run OK"
else
  warn "dry-run reported an issue (see /tmp/factory_dry.log) — usually just a"
  warn "missing dependency or an unfilled secrets/factory.env. Fix, then re-run."
fi

RUN_CMD="FACTORY_REPO=\"$REPO\" \"$PYTHON\" scripts/factory_worker.py"

# ── 5. Background service ────────────────────────────────────────────────────
if [[ "$NO_SERVICE" == "1" ]]; then
  echo
  ok "Setup complete (no service installed)."
  echo "Run the worker in the foreground with:"
  echo "  $RUN_CMD"
  echo "Single test claim (then exits):  $RUN_CMD --once"
  exit 0
fi

OS="$(uname -s)"
# PATH the service should use: prefer the current one so `claude`/`node` resolve.
SVC_PATH="$(dirname "$(command -v claude)"):$(dirname "$PYTHON"):/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

subst() { sed -e "s#__PYTHON__#$PYTHON#g" -e "s#__REPO__#$REPO#g" -e "s#__PATH__#$SVC_PATH#g" "$1"; }

case "$OS" in
  Darwin)
    read -r -p "Install as a launchd service that runs on login + keeps alive? [y/N] " ans
    if [[ "${ans:-N}" =~ ^[Yy]$ ]]; then
      PLIST="$HOME/Library/LaunchAgents/com.factory.worker.plist"
      subst deploy/com.factory.worker.plist.template > "$PLIST"
      launchctl unload "$PLIST" 2>/dev/null || true
      launchctl load "$PLIST"
      ok "launchd service installed: $PLIST"
      echo "  logs:    tail -f \"$REPO/logs/factory_worker.log\""
      echo "  restart: launchctl kickstart -k gui/\$(id -u)/com.factory.worker"
      echo "  stop:    launchctl unload \"$PLIST\""
    else
      echo "Skipped. Foreground run: $RUN_CMD"
    fi
    ;;
  Linux)
    read -r -p "Install as a systemd --user service (run on login + keep alive)? [y/N] " ans
    if [[ "${ans:-N}" =~ ^[Yy]$ ]]; then
      UNIT_DIR="$HOME/.config/systemd/user"
      mkdir -p "$UNIT_DIR"
      subst deploy/factory-worker.service.template > "$UNIT_DIR/factory-worker.service"
      systemctl --user daemon-reload
      systemctl --user enable --now factory-worker
      ok "systemd service installed and started."
      echo "  logs:    tail -f \"$REPO/logs/factory_worker.log\"  (or: journalctl --user -u factory-worker -f)"
      echo "  restart: systemctl --user restart factory-worker"
      echo "  stop:    systemctl --user stop factory-worker"
      warn "For it to run while you're logged out: sudo loginctl enable-linger \"$USER\""
    else
      echo "Skipped. Foreground run: $RUN_CMD"
    fi
    ;;
  *)
    warn "Unrecognized OS '$OS' — no service template. Run in foreground:"
    echo "  $RUN_CMD"
    ;;
esac

echo
ok "Done. Reminder: fill in secrets/factory.env before the worker can claim jobs."
