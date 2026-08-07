# deploy/setup_watchdog.ps1
# Creates a Task Scheduler entry that restarts the factory worker if it dies.
# Run once after initial worker setup. No admin needed (runs as current user).

param([string]$RepoRoot = $env:FACTORY_REPO)
if (-not $RepoRoot) { $RepoRoot = Split-Path $PSScriptRoot -Parent }

$workerCtl = Join-Path $RepoRoot "deploy\worker-ctl.ps1"
$pidFile   = Join-Path $RepoRoot "logs\worker.pid"

# Watchdog script written to repo logs dir (stable path)
$watchdogScript = Join-Path $RepoRoot "logs\watchdog.ps1"
Set-Content $watchdogScript @"
# Auto-generated watchdog — checks every 2min if worker is alive, restarts if not
`$Repo    = '$RepoRoot'
`$PidFile = '$pidFile'
`$Log     = Join-Path `$Repo 'logs\watchdog.log'
function log(`$m) { "`$(Get-Date -f 'HH:mm:ss') `$m" | Tee-Object -FilePath `$Log -Append | Write-Host }
while (`$true) {
    Start-Sleep -Seconds 120
    `$alive = `$false
    if (Test-Path `$PidFile) {
        `$pid = Get-Content `$PidFile | Select-Object -First 1
        `$alive = (Get-Process -Id ([int]`$pid) -ErrorAction SilentlyContinue) -ne `$null
    }
    if (-not `$alive) {
        log "Worker dead — restarting via worker-ctl.ps1"
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File '$workerCtl' start 2>>`$Log
        log "Restart triggered"
    }
}
"@

# Create Task Scheduler job (runs as current user, no admin)
$taskName = "FactoryWorkerWatchdog"
$action   = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$watchdogScript`""
$trigger  = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 99 -RestartInterval (New-TimeSpan -Minutes 1)

# Remove existing if present
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -RunLevel Limited -ErrorAction Stop | Out-Null

# Start it immediately too
Start-ScheduledTask -TaskName $taskName

Write-Host "=============================================="
Write-Host "WATCHDOG: Task '$taskName' created and started"
Write-Host "Checks every 2min. Restarts worker if PID dead."
Write-Host "Survives reboots (runs at logon)."
Write-Host "=============================================="
