#!/bin/bash
# retention_recheck.sh — one-off before/after check of the NEW claude-tricks template.
# Scheduled via ~/Library/LaunchAgents/com.ytnetwork.retention.plist to run Aug 18 & 19 2026
# (08:30 IST), ~48h after the first new-template videos go public. It pulls a fresh retention
# snapshot into docs/stats/retention_new.json WITHOUT touching the baseline retention.json,
# then macOS-notifies VJ to ask Claude for the diff. Self-unloads after 2026-08-19.
set -e
REPO=/Users/vijenderpanda/Ai-youtube-pipeline
PY=/Users/vijenderpanda/miniconda3/bin/python3
cd "$REPO"

"$PY" scripts/yt_retention.py --channel claude-tricks --days 14 --summary \
  --out docs/stats/retention_new.json \
  --md docs/stats/RETENTION-NEW.md >> /tmp/retention_recheck.log 2>&1

osascript -e 'display notification "New-template retention pulled → docs/stats/retention_new.json. Ask Claude to diff vs baseline." with title "AI Unpacked · Retention recheck"' || true

# Self-cleanup once the second run (Aug 19) is done.
if [ "$(date +%Y%m%d)" -ge "20260819" ]; then
  launchctl unload ~/Library/LaunchAgents/com.ytnetwork.retention.plist 2>/dev/null || true
  rm -f ~/Library/LaunchAgents/com.ytnetwork.retention.plist
fi
