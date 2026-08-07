# =============================================================================
# AI YouTube factory - local worker installer for WINDOWS (native).
#
# The worker claims jobs from Supabase and runs them with `claude -p` using THIS
# machine's Claude Code subscription (no Anthropic API key involved). Video
# encoding is offloaded to the NVIDIA GPU (NVENC) automatically when available.
#
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
#   .\install.ps1 -NoService     # config + deps only, no autostart task
#
# Safe to re-run: never overwrites an existing secrets\factory.env or .env.
# =============================================================================
param([switch]$NoService)

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Repo

function Say  ($m) { Write-Host "> $m"   -ForegroundColor Cyan }
function Ok   ($m) { Write-Host "[OK] $m" -ForegroundColor Green }
function Warn ($m) { Write-Host "[!] $m"  -ForegroundColor Yellow }
function Die  ($m) { Write-Host "[X] $m"  -ForegroundColor Red; exit 1 }

# -- 1. Claude Code CLI -------------------------------------------------------
Say "Checking for the Claude Code CLI..."
$claude = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claude) {
  Die "'claude' not found on PATH. Install Claude Code for Windows and sign in first: https://docs.claude.com/en/docs/claude-code  Then re-run install.ps1"
}
Ok "claude found: $($claude.Source)"

# -- 2. Python + deps ---------------------------------------------------------
Say "Locating Python..."
# Resolve to an executable + base args so paths with spaces are handled by the
# call operator (never string-interpolated into a cmd line).
$PyExe = $null; $PyArgs = @()
$pyc = Get-Command python -ErrorAction SilentlyContinue
if ($pyc) { $PyExe = $pyc.Source }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $PyExe = "py"; $PyArgs = @("-3") }
if (-not $PyExe) { Die "Python 3.9+ not found. Install from https://python.org (tick 'Add to PATH'), then re-run." }
Ok "Python: $PyExe $($PyArgs -join ' ')"

Say "Installing Python dependencies (requirements.txt)..."
& $PyExe @PyArgs -m pip install -r requirements.txt 2>&1 | Out-File "$env:TEMP\factory_pip.log"
if ($LASTEXITCODE -ne 0) { Die "pip install failed. See $env:TEMP\factory_pip.log" }
Ok "dependencies installed"

# -- 3. GPU / NVENC preflight -------------------------------------------------
Say "Checking GPU video-encode acceleration (NVENC)..."
& $PyExe @PyArgs scripts\gpu_check.py 2>&1 | Out-File "$env:TEMP\factory_gpu.log"
if ($LASTEXITCODE -eq 0) {
  Ok "NVENC works - the worker will offload video encoding to the RTX GPU."
} else {
  Warn "No usable NVENC yet - worker will encode on CPU (still fully functional)."
  Warn "Install an NVENC-enabled ffmpeg (see WINDOWS-SETUP.md), then: python scripts\gpu_check.py"
}

# -- 4. Config files ----------------------------------------------------------
Say "Setting up config..."
New-Item -ItemType Directory -Force -Path secrets, logs, renders_out | Out-Null

if (Test-Path secrets\factory.env) {
  Ok "secrets\factory.env already exists - leaving it untouched"
} else {
  Copy-Item deploy\factory.env.example secrets\factory.env
  Warn "Created secrets\factory.env - EDIT IT: set SUPABASE_URL and SUPABASE_SERVICE_KEY"
}
if (Test-Path .env) {
  Ok ".env already exists - leaving it untouched"
} else {
  Copy-Item deploy\api-keys.env.example .env
  Ok "Created .env for generation API keys (optional)"
}

# -- 5. Worker smoke test (constructs a job command; executes nothing) --------
Say "Smoke-testing the worker (dry-run)..."
$env:FACTORY_REPO = $Repo
& $PyExe @PyArgs scripts\factory_worker.py --dry-run 2>&1 | Out-File "$env:TEMP\factory_dry.log"
if ($LASTEXITCODE -eq 0) {
  Ok "worker dry-run OK"
} else {
  Warn "dry-run issue - see $env:TEMP\factory_dry.log (usually an unfilled secrets\factory.env)"
}

# -- 6. Autostart at logon (Scheduled Task) -----------------------------------
if ($NoService) {
  Ok "Setup complete (no autostart task)."
  Write-Host "Run the worker with:  powershell -ExecutionPolicy Bypass -File deploy\run-worker.ps1"
  exit 0
}

Say "Register a Scheduled Task to start the worker at logon?"
$ans = Read-Host "  [y/N]"
if ($ans -match '^[Yy]') {
  $runner = Join-Path $Repo "deploy\run-worker.ps1"
  $action = New-ScheduledTaskAction -Execute "powershell.exe" `
      -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$runner`""
  $trigger = New-ScheduledTaskTrigger -AtLogOn
  # Interactive user session (needed so `claude` uses YOUR subscription auth and
  # Chrome-driving jobs can reach a real browser). Restart on crash.
  $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
      -DontStopIfGoingOnBatteries -StartWhenAvailable `
      -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
      -ExecutionTimeLimit (New-TimeSpan -Seconds 0)
  Register-ScheduledTask -TaskName "FactoryWorker" -Action $action -Trigger $trigger `
      -Settings $settings -Description "AI YouTube factory worker (claims Supabase jobs, runs claude -p)" `
      -Force | Out-Null
  Ok "Scheduled Task 'FactoryWorker' registered (starts at each logon)."
  Write-Host "  start now:  Start-ScheduledTask -TaskName FactoryWorker"
  Write-Host "  stop:       Stop-ScheduledTask  -TaskName FactoryWorker"
  Write-Host "  remove:     Unregister-ScheduledTask -TaskName FactoryWorker -Confirm:`$false"
  Write-Host "  logs:       Get-Content logs\factory_worker.log -Wait"
} else {
  Write-Host "Skipped. Run by hand: powershell -ExecutionPolicy Bypass -File deploy\run-worker.ps1"
}

Write-Host ""
Ok "Done."
Warn "FIRST: sign in to Claude once - open a terminal, run 'claude', complete the"
Warn "browser login, then /exit. THEN fill secrets\factory.env. The worker then"
Warn "auto-starts at your next logon (or start it now with the command above)."
