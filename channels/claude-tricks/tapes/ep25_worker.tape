# Ep25 — a REAL worker-shaped `claude -p` run, streaming.
# The argv is the same shape scripts/factory_worker.py build_command() issues
# (-p / --model / --effort / --output-format stream-json / --verbose /
#  --permission-mode acceptEdits); stdout is piped through stream_pretty.py,
# which IMPORTS render_line() from scripts/factory_worker.py — the on-screen
# lines are literally the worker's own renderer, not a lookalike.
# The task is real and about THIS episode: it reads this Short's own assets plan
# and prints its own fragment list.
# 1080x1920 native — this beat is full-frame, any other aspect gets cover-cropped.
Output channels/claude-tricks/assets/ep25/term_worker.mp4
Set Width 1080
Set Height 1920
Set FontSize 34
Set Padding 40
Set Theme "Catppuccin Mocha"
Set Shell "bash"
Set TypingSpeed 55ms

# ---- hidden setup: no home path, no hostname, no inherited-CLAUDE env footers.
# Scratch dir is /tmp/factory (NOT ~/...): tool-call lines echo absolute paths,
# so the cwd itself must contain no username.
Hide
Type "cd /tmp/factory && export FACTORY_REPO=$HOME/Ai-youtube-pipeline"
Enter
Type "export PS1='$ '"
Enter
Type "unset $(env | awk -F= '/^CLAUDE/{print $1}')"
Enter
Type "rm -f fragments.txt && clear"
Enter
Show

Sleep 1s
Type "claude -p 'Read renders_out/assets_plan_4c74c790-f323-4432-b8bb-6a186112ae87.json, write every planned asset_key in order to fragments.txt, then print the list.' \"
Enter
Type "  --model haiku --effort low \"
Enter
Type "  --output-format stream-json --verbose \"
Enter
Type "  --permission-mode acceptEdits \"
Enter
Type "  | python3 stream_pretty.py"
Enter

# CLI boot before anything streams
Sleep 9s
# generous tail so [result:success] lands on camera
Sleep 26s
