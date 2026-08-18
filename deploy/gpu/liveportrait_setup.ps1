# deploy/gpu/liveportrait_setup.ps1
# Idempotent install of LivePortrait (KwaiVGI) on the RTX 3060 worker — adds natural
# head MOTION to a still portrait (driven by an idle clip), full-res. Native Windows,
# NO conda/compiler: the one trap (insightface) uses a prebuilt cp310 wheel; no
# mmcv/dlib. Own venv under %LOCALAPPDATA%\liveportrait. Markers LP_STEP0..5/LP_SETUP_OK.
param([string]$RepoRoot)
$ErrorActionPreference = "Continue"; $ProgressPreference = "SilentlyContinue"
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"

$Root = Join-Path $env:LOCALAPPDATA "liveportrait"
$Venv = Join-Path $Root "venv"
$Repo = Join-Path $Root "LivePortrait"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
$env:HF_HOME = Join-Path $Root "hf-cache"
$IF_WHEEL = "https://huggingface.co/ussoewwin/Insightface_for_windows/resolve/main/insightface-0.7.3-cp310-cp310-win_amd64.whl"
New-Item -ItemType Directory -Force -Path $Root, $env:HF_HOME | Out-Null
function Say ($m) { Write-Host ("[lp] " + $m) }
function Die ($m) { Write-Host ("LP_SETUP_FAIL " + $m); exit 1 }
$sw = [System.Diagnostics.Stopwatch]::StartNew()
try { Say ("gpu: " + ((& nvidia-smi --query-gpu=name,memory.free --format=csv,noheader) -join "; ")) } catch {}

function Find310 {
  try { $p = (& py -3.10 -c "import sys;print(sys.executable)" 2>$null); if ($p) { return $p.Trim() } } catch {}
  $c = Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe"; if (Test-Path $c) { return $c }; return $null
}
$py = Find310
if (-not $py) { Die "no python 3.10" }
& git config --global core.longpaths true
Say "python=$py"; Write-Host "LP_STEP0_OK"

if (-not (Test-Path $VenvPy)) {
  & $py -m venv $Venv 2>&1 | Out-Host
  if (-not (Test-Path $VenvPy)) { Die "venv creation failed" }
  & $VenvPy -m pip install -U pip wheel setuptools 2>&1 | Out-Host
}
Write-Host "LP_STEP1_OK"

if (-not (Test-Path (Join-Path $Repo "inference.py"))) {
  Say "cloning LivePortrait..."
  if (Test-Path $Repo) { Remove-Item -Recurse -Force $Repo }
  & git clone --depth 1 https://github.com/KwaiVGI/LivePortrait "$Repo" 2>&1 | Out-Host
  if (-not (Test-Path (Join-Path $Repo "inference.py"))) { Die "clone failed" }
}
Write-Host "LP_STEP2_OK"

function CudaOK { try { return ((& $VenvPy -c "import torch;print(torch.cuda.is_available())" 2>$null).Trim() -eq "True") } catch { return $false } }
if (-not (CudaOK)) {
  Say "installing torch 2.3.0 cu121..."
  & $VenvPy -m pip install torch==2.3.0 torchvision==0.18.0 torchaudio==2.3.0 --index-url https://download.pytorch.org/whl/cu121 2>&1 | Out-Host
}
if (-not (CudaOK)) { Die "torch CUDA not available" }
Write-Host "LP_STEP3_OK"

# insightface via PREBUILT wheel (NEVER pip-build it -> needs MSVC), then the rest
function IFaceOK { try { return ((& $VenvPy -c "import insightface;print(1)" 2>$null).Trim() -eq "1") } catch { return $false } }
if (-not (IFaceOK)) {
  Say "installing insightface (prebuilt cp310 wheel)..."
  & $VenvPy -m pip install $IF_WHEEL 2>&1 | Out-Host
}
if (-not (IFaceOK)) { Die "insightface import failed (prebuilt wheel)" }
Say "installing LivePortrait requirements..."
& $VenvPy -m pip install -r (Join-Path $Repo "requirements.txt") 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) { Die "requirements install failed" }
Write-Host "LP_STEP4_OK"

# weights -> pretrained_weights/
$warp = Join-Path $Repo "pretrained_weights\liveportrait\base_models\warping_module.pth"
if (-not (Test-Path $warp)) {
  Push-Location $Repo
  Say "downloading LivePortrait weights..."
  & $VenvPy -m pip install "huggingface_hub[cli]" 2>&1 | Out-Host
  & $VenvPy -m huggingface_hub.commands.huggingface_cli download KwaiVGI/LivePortrait --local-dir pretrained_weights --exclude "*.git*" "README.md" "docs" 2>&1 | Out-Host
  if (-not (Test-Path $warp)) {
    # fallback: snapshot_download
    & $VenvPy -c "from huggingface_hub import snapshot_download; snapshot_download('KwaiVGI/LivePortrait', local_dir='pretrained_weights', allow_patterns=['liveportrait/*','insightface/*'])" 2>&1 | Out-Host
  }
  Pop-Location
}
if (-not (Test-Path $warp)) { Die "LivePortrait weights incomplete (no warping_module.pth)" }
Write-Host "LP_STEP5_OK"

$sw.Stop()
Write-Host ("LP_SETUP_OK root=$Root venv=$VenvPy repo=$Repo elapsed_s=" + [int]$sw.Elapsed.TotalSeconds)
exit 0
