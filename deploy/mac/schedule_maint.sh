#!/usr/bin/env bash
# Register a weekly cache cleanup on the Mac worker — the launchd twin of
# deploy/gpu/schedule_maint.ps1's scheduled task. A LaunchAgent under the user's
# own ~/Library/LaunchAgents needs no root.
#
#   (no flags)  install / refresh the weekly job (Sundays 03:00 local)
#   --off       remove it
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LABEL="com.factory.diskmaint"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$UID/$LABEL" 2>/dev/null
if [ "${1:-}" = "--off" ]; then
  rm -f "$PLIST"; echo "weekly cleanup removed"; exit 0
fi

mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$REPO/deploy/mac/disk_maint.sh</string>
    <string>--clean</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Weekday</key><integer>0</integer><key>Hour</key><integer>3</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>$HOME/.factory_diskmaint.log</string>
  <key>StandardErrorPath</key><string>$HOME/.factory_diskmaint.log</string>
</dict></plist>
PLIST_EOF

launchctl bootstrap "gui/$UID" "$PLIST" 2>/dev/null || launchctl load "$PLIST" 2>/dev/null
launchctl list | grep -q "$LABEL" \
  && echo "weekly cleanup registered — Sundays 03:00, log at ~/.factory_diskmaint.log" \
  || echo "could not register the agent; plist written to $PLIST"
