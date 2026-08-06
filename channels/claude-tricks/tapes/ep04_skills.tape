# Ep4 — Agent Skills (REAL claude, real auto-trigger)
Output channels/claude-tricks/assets/ep04/term_skills.mp4
Set FontSize 32
Set Width 1080
Set Height 1350
Set Padding 36
Set Theme "Catppuccin Mocha"
Set TypingSpeed 60ms
Set Shell "bash"

Hide
Type "cd ~/demo-project && rm -rf .claude/skills/status-report && mkdir -p .claude/skills/status-report && clear"
Enter
Show

Sleep 1s
Type "mkdir -p .claude/skills/status-report"
Enter
Sleep 1s
Type "cat > .claude/skills/status-report/SKILL.md << 'DONE'"
Enter
Type "---"
Enter
Type "name: status-report"
Enter
Type "description: Write project status reports in our format"
Enter
Type "---"
Enter
Type "Format: 3 sections - Wins, Risks, Next."
Enter
Type "Tone: crisp bullets, no fluff, max 5 bullets each."
Enter
Type "DONE"
Enter
Sleep 1.5s
Type "clear && claude"
Sleep 500ms
Enter
Sleep 9s
Type "write a status report for this week"
Sleep 1.5s
Enter
Sleep 24s
