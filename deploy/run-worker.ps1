# =============================================================================
# Start the factory worker on Windows. Used by the "FactoryWorker" Scheduled
# Task and runnable by hand:
#   powershell -ExecutionPolicy Bypass -File deploy\run-worker.ps1
#
# Keeps the worker alive: if it exits, it is relaunched after a short delay
# (mirrors launchd KeepAlive / systemd Restart=always).
# =============================================================================
$ErrorActionPreference = "Continue"
$Repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Repo
$env:FACTORY_REPO = $Repo

# Resolve Python (python.exe preferred, else the py launcher) as exe + base args.
$PyExe = (Get-Command python -ErrorAction SilentlyContinue).Source
$PyArgs = @()
if (-not $PyExe) { $PyExe = "py"; $PyArgs = @("-3") }

# Guardrails before the first launch.
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
  Write-Host "[X] 'claude' not on PATH. Install Claude Code and run 'claude' once to sign in." -ForegroundColor Red
  exit 1
}
if (-not (Test-Path secrets\factory.env)) {
  Write-Host "[X] secrets\factory.env missing. Run install.ps1 and fill in Supabase settings." -ForegroundColor Red
  exit 1
}
if ((Get-Content secrets\factory.env -Raw) -match 'SUPABASE_SERVICE_KEY=your-service-role-key') {
  Write-Host "[X] Fill SUPABASE_SERVICE_KEY in secrets\factory.env before starting." -ForegroundColor Red
  exit 1
}

New-Item -ItemType Directory -Force -Path logs | Out-Null
$Log = Join-Path $Repo "logs\factory_worker.log"
# Unbuffered Python so log lines appear promptly when tailing the file.
$env:PYTHONUNBUFFERED = "1"
# UTF-8 mode: Windows otherwise defaults file reads to cp1252 and chokes on the
# repo's UTF-8 docs/manifests. Inherited by child python subprocesses too.
$env:PYTHONUTF8 = "1"
Write-Host "> Starting factory worker (Ctrl-C to stop)... logging to $Log" -ForegroundColor Cyan

while ($true) {
  # Tee worker output to the console AND the log file (append) so the Scheduled
  # Task run - which has no console - still produces logs\factory_worker.log.
  & $PyExe @PyArgs scripts\factory_worker.py 2>&1 | Tee-Object -FilePath $Log -Append
  ("[!] worker exited - restarting in 15s... ({0})" -f (Get-Date -Format o)) |
    Tee-Object -FilePath $Log -Append
  Start-Sleep -Seconds 15
}
