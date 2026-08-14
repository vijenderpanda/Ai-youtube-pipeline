#!/bin/bash
# Restart the factory worker on macOS so it reloads freshly pulled code.
# Run via the shell_script job type (meta.script_path = "deploy/restart_worker.sh").
#
# NOTE: when the worker itself executes this job, kickstart -k kills the worker's
# whole process tree INCLUDING this very job — launchd then relaunches the worker
# with the new code, and the reaper marks this job orphaned a few minutes later.
# That is expected and harmless: treat an 'orphaned' result on this job as success
# if `launchctl list | grep com.factory.worker` shows a fresh PID.
set -x
launchctl kickstart -k "gui/$(id -u)/com.factory.worker"
