#!/bin/bash
# retention_weekly.sh — recurring weekly retention snapshot for the AI Unpacked pivot gate.
# Scheduled via ~/Library/LaunchAgents/com.ytnetwork.retention-weekly.plist (Mondays 08:30 IST).
# Keeps 15s-hold + end-hold fresh so the collab-protocol pivot rule (15s<50% OR end<20% => pivot)
# always has recent data. Writes an ISOLATED snapshot — never touches the baseline retention.json.
set -e
REPO=/Users/vijenderpanda/Ai-youtube-pipeline
PY=/Users/vijenderpanda/miniconda3/bin/python3
cd "$REPO"

"$PY" scripts/yt_retention.py --channel claude-tricks --days 30 --summary \
  --out docs/stats/retention_weekly.json \
  --md docs/stats/RETENTION-WEEKLY.md >> /tmp/retention_weekly.log 2>&1

osascript -e 'display notification "Weekly retention pulled → docs/stats/retention_weekly.json. Ask Claude to check the pivot gate (15s<50% or end<20%)." with title "AI Unpacked · Weekly retention"' || true
