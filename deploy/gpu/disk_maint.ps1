# deploy/gpu/disk_maint.ps1
# Worker disk maintenance. -Report (default, non-destructive): breaks down what the
# GPU installs consume. -Clean: frees space by removing ONLY redundant data — HF/pip
# download caches (the model WEIGHTS live in each tool's own dir, so caches are
# duplicates), already-uploaded GPU renders, torch hub cache, and stale temp. Model
# venvs + weights are KEPT (the working set). Markers DISK_REPORT_OK / DISK_CLEAN_OK.
#
# worker: powershell.exe -NonInteractive -File <this> -RepoRoot <REPO> [-Clean]
param([string]$RepoRoot, [switch]$Clean)
$ErrorActionPreference = "Continue"; $ProgressPreference = "SilentlyContinue"
$LA = $env:LOCALAPPDATA
$UP = $env:USERPROFILE
$TOOLS = @("comfy", "cv", "echomimic", "gpt-sovits", "liveportrait", "musetalk", "factory-localgen")

function DirGB ($p) {
  if (-not (Test-Path $p)) { return 0.0 }
  try {
    $b = (Get-ChildItem -LiteralPath $p -Recurse -File -Force -ErrorAction SilentlyContinue |
          Measure-Object -Property Length -Sum).Sum
    if (-not $b) { return 0.0 }
    return [math]::Round(($b / 1GB), 2)
  } catch { return -1.0 }
}
function FreeGB { return [math]::Round((Get-PSDrive C).Free / 1GB, 2) }

$drv = Get-PSDrive C
$totGB = [math]::Round(($drv.Used + $drv.Free) / 1GB, 1)
$usedGB = [math]::Round($drv.Used / 1GB, 1)
$freeGB = [math]::Round($drv.Free / 1GB, 1)
Write-Host ("DISK C: total=${totGB}GB used=${usedGB}GB free=${freeGB}GB")

# candidate cache/redundant locations (path, label, deletable-in-clean)
$modelscope = Join-Path $UP ".cache\modelscope"
$hfGlobal   = Join-Path $UP ".cache\huggingface"
$torchHub   = Join-Path $UP ".cache\torch"
$pipCache   = Join-Path $LA "pip\Cache"
$rendersOut = Join-Path $RepoRoot "renders_out"

Write-Host "--- per-tool ($LA) ---"
$hfCaches = @()
foreach ($t in $TOOLS) {
  $d = Join-Path $LA $t
  if (-not (Test-Path $d)) { continue }
  $tot = DirGB $d
  $hf = Join-Path $d "hf-cache"
  $hfGB = DirGB $hf
  $venvGB = DirGB (Join-Path $d "venv")
  if ($hfGB -gt 0.05) { $hfCaches += $hf }
  Write-Host ("TOOL {0,-16} total={1}GB venv={2}GB hf-cache={3}GB" -f $t, $tot, $venvGB, $hfGB)
}
Write-Host "--- shared caches / outputs ---"
Write-Host ("PIP_CACHE     $(DirGB $pipCache)GB   $pipCache")
Write-Host ("MODELSCOPE    $(DirGB $modelscope)GB   $modelscope")
Write-Host ("HF_GLOBAL     $(DirGB $hfGlobal)GB   $hfGlobal")
Write-Host ("TORCH_HUB     $(DirGB $torchHub)GB   $torchHub")
Write-Host ("RENDERS_OUT   $(DirGB $rendersOut)GB   $rendersOut  (uploaded to Supabase by *_gen.ps1)")
Write-Host ("WIN_TEMP      $(DirGB $env:TEMP)GB   $env:TEMP")

if (-not $Clean) {
  Write-Host "DISK_REPORT_OK (dry run — pass -Clean to free the caches/renders/temp above)"
  exit 0
}

# ---- CLEAN (safe: caches are duplicates of kept weights; renders are already uploaded) ----
$before = FreeGB
function Nuke ($p, $label) {
  if (-not (Test-Path $p)) { return }
  $g = DirGB $p
  try { Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue; Write-Host ("  cleaned $label (~${g}GB): $p") }
  catch { Write-Host ("  skip $label (locked?): $p") }
}
Write-Host "--- cleaning ---"
foreach ($hf in $hfCaches) { Nuke $hf "hf-cache" }        # weights kept in each tool's model dir
Nuke $pipCache "pip cache"
Nuke $modelscope "modelscope cache"
Nuke $torchHub "torch hub cache"
# renders: contents only (keep the folder); they're already in the factory-renders bucket
if (Test-Path (Join-Path $rendersOut "gpu")) {
  $g = DirGB (Join-Path $rendersOut "gpu")
  Get-ChildItem -LiteralPath (Join-Path $rendersOut "gpu") -Recurse -File -Force -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
  Write-Host ("  cleaned renders_out\gpu (~${g}GB, already uploaded)")
}
# stale temp (>1 day) — never touch in-use files
try {
  $cut = (Get-Date).AddDays(-1)
  Get-ChildItem -LiteralPath $env:TEMP -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -lt $cut } |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
  Write-Host "  cleaned stale temp (>1 day)"
} catch {}
# pip cache purge inside each venv too (belt + suspenders)
foreach ($t in $TOOLS) {
  $vp = Join-Path (Join-Path $LA $t) "venv\Scripts\python.exe"
  if (Test-Path $vp) { & $vp -m pip cache purge 2>$null | Out-Null }
}

$after = FreeGB
$freed = [math]::Round(($after - $before), 2)
Write-Host ("DISK_CLEAN_OK freed=${freed}GB free_now=${after}GB (was ${before}GB)")
exit 0
