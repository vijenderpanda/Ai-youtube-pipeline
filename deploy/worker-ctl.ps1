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

function Start-Worker {
  $p = Get-WorkerProc
  if ($p) { Write-Host "[!] already running (PID $($p.Id))"; return }
  $proc = Start-Process powershell `
    -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-File', $Runner `
    -WindowStyle Hidden -PassThru
  Set-Content -Path $PidFile -Value $proc.Id -Encoding ASCII
  Write-Host "[OK] worker started in background (PID $($proc.Id)). Survives closing this terminal."
  Write-Host "     logs:  powershell -ExecutionPolicy Bypass -File deploy\worker-ctl.ps1 logs"
}

function Stop-Worker {
  $p = Get-WorkerProc
  if (-not $p) { Write-Host "[!] not running (no live PID)"; Remove-Item $PidFile -ErrorAction SilentlyContinue; return }
  # /T kills the whole tree (this launcher's powershell + its python + claude/ffmpeg).
  & taskkill /F /T /PID $p.Id *> $null
  Remove-Item $PidFile -ErrorAction SilentlyContinue
  Write-Host "[OK] worker stopped (PID $($p.Id) and its job tree)."
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
