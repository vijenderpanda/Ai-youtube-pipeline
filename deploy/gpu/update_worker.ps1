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
function Check-Cmd($name, $probe) {
  $c = Get-Command $name -ErrorAction SilentlyContinue
  if ($c) {
    $v = ""
    try { $v = (& $name $probe 2>&1 | Select-Object -First 1) } catch { }
    Write-Output ("  {0,-10} YES  {1}" -f $name, $v)
  } else {
    Write-Output ("  {0,-10} MISSING" -f $name)
  }
}
Check-Cmd "python"  "--version"
Check-Cmd "node"    "--version"
Check-Cmd "npx"     "--version"
Check-Cmd "ffmpeg"  "-version"
Check-Cmd "git"     "--version"

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
Write-Output "=== RESTART THE WORKER TO LOAD THE NEW CODE ==="
Write-Output "  the worker imports factory_worker.py once at start, so a pull alone"
Write-Output "  changes nothing until it restarts:  deploy\worker-ctl.ps1 restart"
