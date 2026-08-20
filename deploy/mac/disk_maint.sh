#!/usr/bin/env bash
# Disk maintenance for the macOS worker (Vijenders-MacBook-Pro.local).
#
# Mirrors deploy/gpu/disk_maint.ps1, which is Windows-only. Run by the worker
# under the `shell_script` job type: `bash deploy/mac/disk_maint.sh [flags]`.
# No -RepoRoot is passed for .sh jobs, so we locate the repo from our own path.
#
#   (no flags)   report only — reads, deletes nothing
#   --clean      delete regenerable package/tool caches
#   --deep       --clean plus browser + ML caches (heavier, still regenerable)
#   --docker     reclaim the Docker VM disk (removes unused images/containers)
#
# Nothing here touches channels/, renders/, or anything under git control.

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLEAN=0; DEEP=0; DOCKER=0
for a in "$@"; do
  case "$a" in
    --clean)  CLEAN=1 ;;
    --deep)   CLEAN=1; DEEP=1 ;;
    --docker) DOCKER=1 ;;
    *) echo "unknown flag: $a" ;;
  esac
done

free_gb () { df -g /System/Volumes/Data | tail -1 | awk '{print $4}'; }
sz () { [ -e "$1" ] && du -sh "$1" 2>/dev/null | cut -f1 || echo "-"; }

BEFORE=$(free_gb)
echo "=== DISK ==="
df -h /System/Volumes/Data | tail -1
echo "free: ${BEFORE} GB"

echo
echo "=== WHAT IS EATING IT ==="
printf '%-34s %s\n' "Docker VM disk"    "$(sz "$HOME/Library/Containers/com.docker.docker")"
printf '%-34s %s\n' "npm cache"         "$(sz "$HOME/.npm")"
printf '%-34s %s\n' "pip cache"         "$(sz "$HOME/Library/Caches/pip")"
printf '%-34s %s\n' "uv cache"          "$(sz "$HOME/.cache/uv")"
printf '%-34s %s\n' "poetry cache"      "$(sz "$HOME/Library/Caches/pypoetry")"
printf '%-34s %s\n' "playwright browsers" "$(sz "$HOME/Library/Caches/ms-playwright")"
printf '%-34s %s\n' "huggingface models" "$(sz "$HOME/.cache/huggingface")"
printf '%-34s %s\n' "browser caches"    "$(sz "$HOME/Library/Caches/BraveSoftware") + $(sz "$HOME/Library/Caches/Google")"
printf '%-34s %s\n' "repo: channels/"   "$(sz "$REPO/channels")"
printf '%-34s %s\n' "repo: node_modules" "$(sz "$REPO/remotion-studio/node_modules")"

if [ "$CLEAN" = 0 ] && [ "$DOCKER" = 0 ]; then
  echo
  echo "=== REPORT ONLY — nothing was deleted ==="
  echo "Run with --clean for package caches, --deep to also drop browser/ML caches,"
  echo "or --docker to reclaim the Docker VM disk."
  exit 0
fi

# --- deletions below this line -------------------------------------------
# Every path is a cache the tool rebuilds on next use. Each is guarded so an
# unset or missing path can never widen into an rm of something else.
drop () {  # drop <label> <path>
  local label="$1" path="$2"
  case "$path" in ""|"/"|"$HOME") echo "refusing: $label"; return ;; esac
  [ -e "$path" ] || { printf '  %-28s (absent)\n' "$label"; return; }
  local was; was=$(sz "$path")
  rm -rf -- "$path" 2>/dev/null
  printf '  %-28s freed %s\n' "$label" "$was"
}

if [ "$CLEAN" = 1 ]; then
  echo
  echo "=== CLEANING PACKAGE CACHES ==="
  command -v npm >/dev/null && npm cache clean --force >/dev/null 2>&1 && echo "  npm cache clean               ok"
  drop "pip cache"      "$HOME/Library/Caches/pip"
  drop "poetry cache"   "$HOME/Library/Caches/pypoetry"
  drop "uv cache"       "$HOME/.cache/uv"
  drop "Homebrew cache" "$HOME/Library/Caches/Homebrew"
  command -v brew >/dev/null && brew cleanup -s >/dev/null 2>&1 && echo "  brew cleanup                  ok"
fi

if [ "$DEEP" = 1 ]; then
  echo
  echo "=== DEEP: browser + ML caches ==="
  drop "Brave cache"       "$HOME/Library/Caches/BraveSoftware"
  drop "Chrome cache"      "$HOME/Library/Caches/Google"
  drop "playwright browsers" "$HOME/Library/Caches/ms-playwright"
  drop "whisper models"    "$HOME/.cache/whisper"
  echo "  (huggingface models left alone — re-downloading them is expensive)"
fi

if [ "$DOCKER" = 1 ]; then
  echo
  echo "=== DOCKER RECLAIM ==="
  if command -v docker >/dev/null && docker info >/dev/null 2>&1; then
    # NEVER --volumes. Named volumes here hold local project databases
    # (postgres data for pregmitra, globallivetracker, panda_logix, supabase...)
    # and a volume that is merely "unused" is just one whose container is not
    # running right now. Pruning them reclaims ~250 MB and can destroy data that
    # exists nowhere else. Images and build cache are re-pullable; volumes are not.
    docker system prune -a -f 2>&1 | tail -3
    docker builder prune -a -f 2>&1 | tail -2
  else
    echo "  Docker is not running — start Docker Desktop and re-run."
    echo "  Its VM disk is $(sz "$HOME/Library/Containers/com.docker.docker"); the space"
    echo "  only returns to the OS after a prune while the engine is up."
  fi
fi

AFTER=$(free_gb)
echo
echo "=== DONE ==="
echo "free before: ${BEFORE} GB   free now: ${AFTER} GB   reclaimed: $((AFTER - BEFORE)) GB"
