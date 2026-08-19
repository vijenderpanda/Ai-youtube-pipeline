# deploy/gpu/disk_maint.ps1
# Worker disk maintenance. -Report (default, non-destructive): breaks down what the
# GPU installs consume. -Clean: frees ONLY redundant data - HF/pip/modelscope/torch
# download caches (model WEIGHTS live in each tool's own dir, so caches are dupes),
# already-uploaded GPU renders, and stale temp. Model venvs + weights are KEPT.
# Markers DISK_REPORT_OK / DISK_CLEAN_OK.
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
Write-Host ("DISK C: total={0}GB used={1}GB free={2}GB" -f `
  [math]::Round(($drv.Used + $drv.Free) / 1GB, 1), [math]::Round($drv.Used / 1GB, 1), [math]::Round($drv.Free / 1GB, 1))

$modelscope = Join-Path $UP ".cache\modelscope"
$hfGlobal   = Join-Path $UP ".cache\huggingface"
$torchHub   = Join-Path $UP ".cache\torch"
$pipCache   = Join-Path $LA "pip\Cache"
$rendersOut = Join-Path $RepoRoot "renders_out"

Write-Host ("--- per-tool ({0}) ---" -f $LA)
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
Write-Host ("PIP_CACHE     {0}GB   {1}" -f (DirGB $pipCache), $pipCache)
Write-Host ("MODELSCOPE    {0}GB   {1}" -f (DirGB $modelscope), $modelscope)
Write-Host ("HF_GLOBAL     {0}GB   {1}" -f (DirGB $hfGlobal), $hfGlobal)
Write-Host ("TORCH_HUB     {0}GB   {1}" -f (DirGB $torchHub), $torchHub)
Write-Host ("RENDERS_OUT   {0}GB   {1}  (uploaded to Supabase by *_gen.ps1)" -f (DirGB $rendersOut), $rendersOut)
Write-Host ("WIN_TEMP      {0}GB   {1}" -f (DirGB $env:TEMP), $env:TEMP)

if (-not $Clean) {
  Write-Host "DISK_REPORT_OK (dry run - pass -Clean to free the caches/renders/temp above)"
  exit 0
}

# ---- CLEAN (safe: caches are dupes of kept weights; renders already uploaded) ----
$before = FreeGB
function Nuke ($p, $label) {
  if (-not (Test-Path $p)) { return }
  $g = DirGB $p
  try {
    Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host ("  cleaned {0} (~{1}GB): {2}" -f $label, $g, $p)
  } catch {
    Write-Host ("  skip {0} (locked?): {1}" -f $label, $p)
  }
}
Write-Host "--- cleaning ---"
foreach ($hf in $hfCaches) { Nuke $hf "hf-cache" }
Nuke $pipCache "pip cache"
Nuke $modelscope "modelscope cache"
Nuke $torchHub "torch hub cache"
# renders: contents only (keep the folder); already in the factory-renders bucket
$rgpu = Join-Path $rendersOut "gpu"
if (Test-Path $rgpu) {
  $g = DirGB $rgpu
  Get-ChildItem -LiteralPath $rgpu -Recurse -File -Force -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
  Write-Host ("  cleaned renders_out\gpu (~{0}GB, already uploaded)" -f $g)
}
# stale temp (>1 day) - never touch in-use files
try {
  $cut = (Get-Date).AddDays(-1)
  Get-ChildItem -LiteralPath $env:TEMP -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -lt $cut } |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
  Write-Host "  cleaned stale temp (>1 day)"
} catch {}
# pip cache purge inside each venv too
foreach ($t in $TOOLS) {
  $vp = Join-Path (Join-Path $LA $t) "venv\Scripts\python.exe"
  if (Test-Path $vp) { & $vp -m pip cache purge 2>$null | Out-Null }
}

$after = FreeGB
Write-Host ("DISK_CLEAN_OK freed={0}GB free_now={1}GB was={2}GB" -f [math]::Round(($after - $before), 2), $after, $before)
exit 0
