#!/usr/bin/env bash
# Stop the Mac worker sleeping mid-job. The Windows twin (deploy/gpu/keep_awake.ps1)
# uses powercfg; macOS pmset needs root, which the worker does not have — caffeinate
# does the same job from a normal user, so this holds the machine awake instead.
#
#   (no flags)  hold this Mac awake until told otherwise
#   --off       release the hold
set -uo pipefail
PIDF="$HOME/.factory_caffeinate.pid"

if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then
  kill "$(cat "$PIDF")" 2>/dev/null; rm -f "$PIDF"; echo "released the previous hold"
fi
if [ "${1:-}" = "--off" ]; then
  echo "This Mac may sleep normally again."; exit 0
fi

# -i no idle sleep, -m no disk sleep, -s no system sleep on AC. The display is
# left alone deliberately: the screen can still turn off while jobs keep running.
nohup caffeinate -ims >/dev/null 2>&1 &
echo $! > "$PIDF"
echo "holding this Mac awake (pid $(cat "$PIDF")) — the screen may still sleep, the machine will not"
