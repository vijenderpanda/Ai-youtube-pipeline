# =============================================================================
# Factory worker control (Windows) - background process manager. No admin needed.
#
#   powershell -ExecutionPolicy Bypass -File deploy\worker-ctl.ps1 <action>
#
# actions:
#   start     launch the worker DETACHED (keeps running after you close the
#             terminal). Idempotent - won't start a second copy.
#   stop      terminate the worker and its whole job tree (claude/ffmpeg too).
#   restart   stop, then start.
#   status    is it running? shows PID + the last log lines.
#   logs      live-tail logs\factory_worker.log (Ctrl-C to stop watching).
#   pause     tell THIS worker to stop claiming new jobs (running jobs finish).
#   resume    let it claim jobs again.
#
# pause/resume flip factory_workers.paused in Supabase (same effect as the
# dashboard's Pause button); they take effect within ~20s. Everything else
# manages the local OS process.
# =============================================================================
param(
  [Parameter(Position = 0)]
  [ValidateSet('start', 'stop', 'restart', 'status', 'logs', 'pause', 'resume')]
  [string]$Action = 'status'
)

$ErrorActionPreference = "Continue"
$Repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Repo
$Runner  = Join-Path $Repo "deploy\run-worker.ps1"
$Log     = Join-Path $Repo "logs\factory_worker.log"
$PidFile = Join-Path $Repo "logs\worker.pid"
New-Item -ItemType Directory -Force -Path (Join-Path $Repo "logs") | Out-Null

function Get-WorkerProc {
  if (-not (Test-Path $PidFile)) { return $null }
  $wpid = Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $wpid) { return $null }
  return Get-Process -Id ([int]$wpid) -ErrorAction SilentlyContinue
}


# Find EVERY live worker process, not just whatever the PID file remembers.
# The PID file is written by Start-Worker, so a supervisor started at boot, by a
# watchdog, or in an earlier session is invisible to it -- and then Stop-Worker
# reports "not running" and kills nothing, Start-Worker hits the single-instance
# mutex in run-worker.ps1 and exits silently inside a hidden window, and the
# STALE supervisor keeps serving jobs. That is how a freshly installed node
# stayed invisible to the worker across three restarts: PID 16628 from 12:38 PM
# outlived every one of them.
function Get-LiveWorkerProcs {
  $out = @()
  try {
    $out += Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" |
      Where-Object { $_.CommandLine -and $_.CommandLine -like "*run-worker.ps1*" }
    $out += Get-CimInstance Win32_Process |
      Where-Object { $_.Name -like "python*" -and $_.CommandLine -and $_.CommandLine -like "*factory_worker.py*" }
  } catch { }
  return $out
}

function Show-LiveWorkers($label) {
  $ps = Get-LiveWorkerProcs
  if (-not $ps) { Write-Host "     $label none alive"; return @() }
  foreach ($p in $ps) { Write-Host ("     $label pid {0} started {1}" -f $p.ProcessId, $p.CreationDate) }
  return $ps
}

function Start-Worker {
  $p = Get-WorkerProc
  if ($p) { Write-Host "[!] already running (PID $($p.Id))"; return }
  $before = @(Get-LiveWorkerProcs | ForEach-Object { $_.ProcessId })
  if ($before.Count -gt 0) {
    Write-Host "[X] a worker is ALREADY alive that the PID file does not know about:" -ForegroundColor Red
    Show-LiveWorkers "" | Out-Null
    Write-Host "    run-worker.ps1's mutex will make this start exit silently, and that stale"
    Write-Host "    process keeps serving jobs with its ORIGINAL environment. Stop it first:"
    Write-Host "      Stop-Process -Id $($before -join ',') -Force"
    return
  }
  $proc = Start-Process powershell `
    -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-File', $Runner `
    -WindowStyle Hidden -PassThru
  Set-Content -Path $PidFile -Value $proc.Id -Encoding ASCII
  Start-Sleep -Seconds 3
  # the launcher exits immediately when the mutex is held, and its window is
  # hidden -- so verify a supervisor is actually alive rather than trusting it
  if (-not (Get-LiveWorkerProcs)) {
    Write-Host "[X] started PID $($proc.Id) but no worker is alive 3s later." -ForegroundColor Red
    Write-Host "    Almost certainly the single-instance mutex: something still holds it."
    return
  }
  Write-Host "[OK] worker started in background (PID $($proc.Id)). Survives closing this terminal."
  Write-Host "     logs:  powershell -ExecutionPolicy Bypass -File deploy\worker-ctl.ps1 logs"
}

function Stop-Worker {
  $p = Get-WorkerProc
  if ($p) {
    # /T kills the whole tree (this launcher's powershell + its python + claude/ffmpeg).
    & taskkill /F /T /PID $p.Id *> $null
    Write-Host "[OK] worker stopped (PID $($p.Id) and its job tree)."
  } else {
    Write-Host "[!] the PID file names no live process."
  }
  Remove-Item $PidFile -ErrorAction SilentlyContinue

  # Whatever the PID file said, kill anything still serving -- otherwise a start
  # right after this silently no-ops against the mutex.
  $left = Get-LiveWorkerProcs
  if ($left) {
    Write-Host "[!] worker processes still alive that the PID file did not know about:"
    foreach ($q in $left) { Write-Host ("      pid {0} started {1}" -f $q.ProcessId, $q.CreationDate) }
    foreach ($q in $left) { & taskkill /F /T /PID $q.ProcessId *> $null }
    Start-Sleep -Seconds 2
    $still = Get-LiveWorkerProcs
    if ($still) {
      Write-Host "[X] could not kill: $(($still | ForEach-Object { $_.ProcessId }) -join ',')" -ForegroundColor Red
    } else {
      Write-Host "[OK] cleaned up the untracked worker process(es) too."
    }
  }
}

function Read-Env($name) {
  if (-not (Test-Path "secrets\factory.env")) { return $null }
  $m = Select-String -Path "secrets\factory.env" -Pattern "^$name=" -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($m) { return ($m.Line -replace "^$name=", "").Trim() }
  return $null
}

function Set-Paused([bool]$val) {
  $url = Read-Env "SUPABASE_URL"; $key = Read-Env "SUPABASE_SERVICE_KEY"
  if (-not $url -or -not $key) { Write-Host "[X] SUPABASE_URL / SUPABASE_SERVICE_KEY missing in secrets\factory.env"; return }
  $wid = if ($env:FACTORY_WORKER_ID) { $env:FACTORY_WORKER_ID } else { [System.Net.Dns]::GetHostName() }
  $uri = "$url/rest/v1/factory_workers?worker_id=eq.$wid"
  $hdr = @{ apikey = $key; Authorization = "Bearer $key"; "Content-Type" = "application/json"; Prefer = "return=minimal" }
  try {
    Invoke-RestMethod -Method Patch -Uri $uri -Headers $hdr -Body (@{ paused = $val } | ConvertTo-Json) | Out-Null
    $word = if ($val) { "paused" } else { "resumed" }
    Write-Host "[OK] worker '$wid' $word (applies within ~20s)."
  } catch {
    Write-Host "[X] failed: $($_.Exception.Message)"
  }
}

switch ($Action) {
  'start'   { Start-Worker }
  'stop'    { Stop-Worker }
  'restart' { Stop-Worker; Start-Sleep -Seconds 2; Start-Worker }
  'status'  {
    $p = Get-WorkerProc
    if ($p) { Write-Host "[OK] RUNNING (PID $($p.Id), since $($p.StartTime))" }
    else    { Write-Host "[--] stopped" }
    if (Test-Path $Log) {
      Write-Host "--- last 12 log lines ---------------------------------------"
      Get-Content $Log -Tail 12
    }
  }
  'logs'    {
    if (-not (Test-Path $Log)) { Write-Host "[!] no log yet at $Log"; break }
    Write-Host "Tailing $Log (Ctrl-C to stop)..."
    Get-Content $Log -Tail 30 -Wait
  }
  'pause'   { Set-Paused $true }
  'resume'  { Set-Paused $false }
}
