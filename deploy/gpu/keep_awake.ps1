# deploy/gpu/keep_awake.ps1
# Stop the worker dropping mid-pipeline: disable idle SLEEP/STANDBY/HIBERNATE on AC
# power for the active scheme. No admin needed (powercfg /change edits the current
# user's active scheme). Idempotent. Prints the resulting timeouts + KEEPAWAKE_OK.
#
# worker: powershell.exe -NonInteractive -File <this> -RepoRoot <REPO>
param([string]$RepoRoot)
$ErrorActionPreference = "Continue"
function Say ($m) { Write-Host ("[awake] " + $m) }

# 0 = "Never". AC = plugged in (the desktop worker is always on AC).
& powercfg /change standby-timeout-ac 0   2>&1 | Out-Host
& powercfg /change hibernate-timeout-ac 0 2>&1 | Out-Host
& powercfg /change disk-timeout-ac 0      2>&1 | Out-Host
# leave monitor timeout alone (display sleeping is fine; only system sleep drops us)

# verify: STANDBYIDLE AC index should read 0x00000000
Say "active-scheme sleep settings after change:"
$q = (& powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE) 2>&1
($q | Select-String -Pattern "Power Setting|AC Power Setting Index") | ForEach-Object { Write-Host ("  " + $_.ToString().Trim()) }
$acIdx = ($q | Select-String -Pattern "AC Power Setting Index" | Select-Object -First 1)
$ok = ($acIdx -and $acIdx.ToString() -match "0x00000000")
$lbl = if ($ok) { "never" } else { "set(verify above)" }
Write-Host ("KEEPAWAKE_OK standby-ac=" + $lbl)
exit 0
