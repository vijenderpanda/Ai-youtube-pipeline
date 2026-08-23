# Bring this worker's checkout up to date, and report whether it can actually
# run a produce. Pure ASCII on purpose - PS 5.1 chokes on smart quotes.
#
# Why this exists: the GPU box sat 61 commits behind for a day and nobody could
# see it. It had never run a produce_preview, and a produce renders through the
# Remotion cookbook - so an old checkout picks a component its own registry does
# not have and dies at the render step, AFTER the run has already paid for the
# voice track and the host clips. Being behind is not a cosmetic problem here.
#
# Run this from the app: Machines -> the box -> "Update + check".
param([string]$RepoRoot = "")

if (-not $RepoRoot) { $RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path }
Set-Location $RepoRoot

Write-Output "=== BEFORE ==="
$before = (git rev-parse --short HEAD)
Write-Output ("commit: {0}" -f $before)
Write-Output ("branch: {0}" -f (git rev-parse --abbrev-ref HEAD))

$dirty = (git status --porcelain)
if ($dirty) {
  Write-Output ""
  Write-Output "=== LOCAL CHANGES (not touched) ==="
  $dirty -split "`n" | Select-Object -First 12 | ForEach-Object { Write-Output ("  " + $_) }
}

Write-Output ""
Write-Output "=== PULLING ==="
git fetch --all --quiet 2>&1 | Out-Null
$pull = (git pull --ff-only 2>&1)
$pull -split "`n" | Select-Object -First 8 | ForEach-Object { Write-Output ("  " + $_) }

$after = (git rev-parse --short HEAD)
Write-Output ""
Write-Output ("=== AFTER: {0} -> {1} ===" -f $before, $after)
if ($before -eq $after) {
  Write-Output "  already current"
} else {
  $n = (git rev-list --count "$before..$after" 2>$null)
  Write-Output ("  advanced {0} commit(s)" -f $n)
}

# A produce needs more than the repo. Report what is actually present, because a
# missing ffmpeg or node shows up as a confusing failure 20 minutes in.
Write-Output ""
Write-Output "=== CAN THIS BOX RUN A PRODUCE? ==="
# "MISSING" was ambiguous and cost four round-trips: node WAS installed
# machine-wide, but the worker supervisor had started before the install, so its
# inherited PATH had no nodejs and every child saw nothing. A tool that is on the
# machine but invisible to this process needs a different answer than one that is
# not installed, because the fix is a restart, not an install.
function Check-Cmd($name, $probe, $knownPath) {
  $c = Get-Command $name -ErrorAction SilentlyContinue
  if ($c) {
    $v = ""
    try { $v = (& $name $probe 2>&1 | Select-Object -First 1) } catch { }
    Write-Output ("  {0,-10} YES  {1}" -f $name, $v)
    return
  }
  if ($knownPath -and (Test-Path $knownPath)) {
    Write-Output ("  {0,-10} INSTALLED BUT INVISIBLE TO THE WORKER" -f $name)
    Write-Output ("             found at {0}, but not on this process's PATH." -f $knownPath)
    Write-Output  "             The worker started before it was installed. RESTARTING IS THE FIX,"
    Write-Output  "             and note run-worker.ps1 holds a single-instance mutex: a second"
    Write-Output  "             start exits SILENTLY while the stale process keeps serving. Kill"
    Write-Output  "             the supervisor by PID first, then start."
    return
  }
  Write-Output ("  {0,-10} MISSING" -f $name)
}
Check-Cmd "python"  "--version" $null
Check-Cmd "node"    "--version" "C:\Program Files\nodejs\node.exe"
Check-Cmd "npx"     "--version" "C:\Program Files\nodejs\npx.cmd"
Check-Cmd "ffmpeg"  "-version" $null
Check-Cmd "git"     "--version" $null

$envFile = Join-Path $RepoRoot "secrets\factory.env"
Write-Output ""
if (Test-Path $envFile) {
  $keys = @("ELEVENLABS_API_KEY", "HEYGEN_API_KEY", "SUPABASE_SERVICE_KEY", "ANTHROPIC_API_KEY")
  foreach ($k in $keys) {
    $has = (Select-String -Path $envFile -Pattern ("^" + $k + "=.+") -Quiet)
    Write-Output ("  {0,-24} {1}" -f $k, $(if ($has) { "present" } else { "MISSING" }))
  }
} else {
  Write-Output "  secrets\factory.env NOT FOUND - this box cannot call any paid engine"
}

$nm = Join-Path $RepoRoot "remotion-studio\node_modules"
Write-Output ""
Write-Output ("  remotion node_modules  {0}" -f $(if (Test-Path $nm) { "present" } else { "MISSING - run npm install in remotion-studio" }))

Write-Output ""
Write-Output "=== HOW OLD IS THE PROCESS SERVING THIS JOB? ==="
try {
  $me = Get-CimInstance Win32_Process -Filter "ProcessId = $PID"
  $par = Get-CimInstance Win32_Process -Filter ("ProcessId = " + $me.ParentProcessId)
  Write-Output ("  worker pid {0} started {1}" -f $par.ProcessId, $par.CreationDate)
  Write-Output  "  anything installed AFTER that time is invisible to it until it restarts."
} catch { Write-Output "  could not read the parent process" }

Write-Output ""
Write-Output "=== RESTART THE WORKER TO LOAD THE NEW CODE ==="
Write-Output "  the worker imports factory_worker.py once at start, so a pull alone"
Write-Output "  changes nothing until it restarts."
Write-Output "  DO NOT trust 'worker-ctl.ps1 restart' on its own: run-worker.ps1 holds a"
Write-Output "  single-instance mutex, so if the old supervisor survives the stop, the new"
Write-Output "  start exits SILENTLY and the stale process keeps serving jobs. That is how"
Write-Output "  a freshly installed node stayed invisible across three restarts."
Write-Output "  Kill the supervisor by PID, confirm it is gone, THEN start."
