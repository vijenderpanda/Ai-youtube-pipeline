# Ep11 — the "20 secret commands" myth-bust (REAL claude)
# Part 1: /premortem does NOT exist -> Part 2: create it -> Part 3: it runs.
# 1080x1920 native so newsSplit "full" beats need zero cropping.
Output channels/claude-tricks/assets/ep11/term_premortem.mp4
Set FontSize 34
Set Width 1080
Set Height 1920
Set Padding 40
Set Theme "Catppuccin Mocha"
Set TypingSpeed 60ms
Set Shell "bash"

Hide
Type "cd ~/demo-project && rm -f .claude/commands/premortem.md && unset $(env | awk -F= '/^CLAUDE/{print $1}') && clear"
Enter
Show

# PART 1 — try the "secret" command on a stock claude
Sleep 500ms
Type "claude"
Enter
Sleep 9s
Type "/premortem"
Sleep 2.5s
Enter
Sleep 4s

# exit claude
Hide
Ctrl+C
Sleep 300ms
Ctrl+C
Sleep 1s
Type "clear"
Enter
Show

# PART 2 — make it real: one file = one command
Sleep 500ms
Type "cat > .claude/commands/premortem.md << 'DONE'"
Enter
Sleep 300ms
Type "Run a premortem on this project: assume the launch"
Enter
Type "FAILED. List the top 5 reasons why, ranked, each"
Enter
Type "with a one-line prevention. Be brutal and specific."
Enter
Type "DONE"
Enter
Sleep 2s

# PART 3 — fresh claude, the command now exists and runs
Type "clear && claude"
Enter
Sleep 9s
Type "/premortem"
Sleep 2.5s
Enter
Sleep 75s
