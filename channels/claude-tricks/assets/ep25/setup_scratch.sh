#!/usr/bin/env bash
# Stage the /tmp/factory scratch dir the ep25_worker.tape films in.
# It lives in /tmp, NOT under $HOME, because claude's tool-call lines echo
# ABSOLUTE paths -- a ~/... cwd would render the owner's username on camera.
# Run from the repo root, then: vhs channels/claude-tricks/tapes/ep25_worker.tape
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
rm -rf /tmp/factory
mkdir -p /tmp/factory/renders_out
cp "$REPO/renders_out/assets_plan_4c74c790-f323-4432-b8bb-6a186112ae87.json" /tmp/factory/renders_out/
cp "$REPO/channels/claude-tricks/assets/ep25/stream_pretty.py" /tmp/factory/
printf 'This is a scratch workspace for a screen recording. Answer concisely.\n' > /tmp/factory/CLAUDE.md
echo "staged /tmp/factory"
