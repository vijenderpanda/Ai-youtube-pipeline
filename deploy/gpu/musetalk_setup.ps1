# deploy/gpu/musetalk_setup.ps1
# Idempotent install of MuseTalk 1.5 (audio-driven lip-sync / talking head) on the
# RTX 3060 worker, headless, native Windows, NO conda/compiler. mmcv uses the
# prebuilt cp310/cu118 wheel; mmdet/mmpose are pure-Python. Everything under
# %LOCALAPPDATA%\musetalk (venv+weights outside the factory repo). Its own torch
# (2.0.1 cu118) in a separate venv, so it can't clash with the other GPU installs.
# Markers MT_STEP0..6 / MT_SETUP_OK.
param([string]$RepoRoot)
$ErrorActionPreference = "Continue"; $ProgressPreference = "SilentlyContinue"
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"

$Root = Join-Path $env:LOCALAPPDATA "musetalk"
$Venv = Join-Path $Root "venv"
$Repo = Join-Path $Root "MuseTalk"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
$env:HF_HOME = Join-Path $Root "hf-cache"
New-Item -ItemType Directory -Force -Path $Root, $env:HF_HOME | Out-Null
function Say ($m) { Write-Host ("[mt] " + $m) }
function Die ($m) { Write-Host ("MT_SETUP_FAIL " + $m); exit 1 }
$sw = [System.Diagnostics.Stopwatch]::StartNew()
try { Say ("gpu: " + ((& nvidia-smi --query-gpu=name,memory.free --format=csv,noheader) -join "; ")) } catch {}

function Find310 {
  try { $p = (& py -3.10 -c "import sys;print(sys.executable)" 2>$null); if ($p) { return $p.Trim() } } catch {}
  $c = Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe"; if (Test-Path $c) { return $c }; return $null
}
$py = Find310
if (-not $py) { Die "no python 3.10" }
& git config --global core.longpaths true
Say "python=$py"; Write-Host "MT_STEP0_OK"

if (-not (Test-Path $VenvPy)) {
  & $py -m venv $Venv 2>&1 | Out-Host
  if (-not (Test-Path $VenvPy)) { Die "venv creation failed" }
  & $VenvPy -m pip install -U pip wheel setuptools 2>&1 | Out-Host
}
Write-Host "MT_STEP1_OK"

if (-not (Test-Path (Join-Path $Repo "requirements.txt"))) {
  Say "cloning MuseTalk..."
  if (Test-Path $Repo) { Remove-Item -Recurse -Force $Repo }
  & git clone --depth 1 https://github.com/TMElyralab/MuseTalk.git "$Repo" 2>&1 | Out-Host
  if (-not (Test-Path (Join-Path $Repo "requirements.txt"))) { Die "clone failed" }
}
Write-Host "MT_STEP2_OK"

# torch 2.0.1 cu118 FIRST (mmcv wheel is built for torch2.0.x + cu118)
function CudaOK { try { return ((& $VenvPy -c "import torch;print(torch.cuda.is_available())" 2>$null).Trim() -eq "True") } catch { return $false } }
if (-not (CudaOK)) {
  Say "installing torch 2.0.1 cu118..."
  & $VenvPy -m pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118 2>&1 | Out-Host
}
if (-not (CudaOK)) { Die "torch CUDA not available" }
Write-Host "MT_STEP3_OK"

# mmlab stack (compiler-free): mmengine, mmcv from the prebuilt wheel index, mmdet, mmpose
function MmcvOK { try { return ((& $VenvPy -c "import mmcv;print(1)" 2>$null).Trim() -eq "1") } catch { return $false } }
if (-not (MmcvOK)) {
  Say "installing mmengine + mmcv (prebuilt wheel) + mmdet + mmpose..."
  & $VenvPy -m pip install -U openmim 2>&1 | Out-Host
  & $VenvPy -m mim install mmengine 2>&1 | Out-Host
  & $VenvPy -m pip install "mmcv==2.0.1" -f https://download.openmmlab.com/mmcv/dist/cu118/torch2.0.0/index.html 2>&1 | Out-Host
  & $VenvPy -m mim install "mmdet==3.1.0" 2>&1 | Out-Host
  & $VenvPy -m mim install "mmpose==1.1.0" 2>&1 | Out-Host
}
if (-not (MmcvOK)) { Die "mmcv import failed after install" }
Write-Host "MT_STEP4_OK"

# rest of requirements LAST (so numpy==1.23.5 wins)
Say "installing MuseTalk requirements (numpy pin last)..."
& $VenvPy -m pip install -r (Join-Path $Repo "requirements.txt") 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) { Die "requirements install failed" }
Write-Host "MT_STEP5_OK"

# weights -> models/ (skip syncnet = training only)
$mkV15 = Join-Path $Repo "models\musetalkV15\unet.pth"
if (-not (Test-Path $mkV15)) {
  Push-Location $Repo
  $wPy = Join-Path $Root "_mtw.py"
  @"
import os
from urllib.request import urlretrieve
from huggingface_hub import hf_hub_download
import gdown
def hf(repo, fn, ld): hf_hub_download(repo, fn, local_dir=ld, local_dir_use_symlinks=False)
for fn in ['musetalk/musetalk.json','musetalk/pytorch_model.bin','musetalkV15/musetalk.json','musetalkV15/unet.pth']:
    hf('TMElyralab/MuseTalk', fn, 'models')
for fn in ['config.json','diffusion_pytorch_model.bin']:
    hf('stabilityai/sd-vae-ft-mse', fn, 'models/sd-vae')
for fn in ['config.json','pytorch_model.bin','preprocessor_config.json']:
    hf('openai/whisper-tiny', fn, 'models/whisper')
hf('yzd-v/DWPose', 'dw-ll_ucoco_384.pth', 'models/dwpose')
os.makedirs('models/face-parse-bisent', exist_ok=True)
gdown.download(id='154JgKpzCPW82qINcVieuPH3fZ2e0P812', output='models/face-parse-bisent/79999_iter.pth', quiet=False)
urlretrieve('https://download.pytorch.org/models/resnet18-5c106cde.pth','models/face-parse-bisent/resnet18-5c106cde.pth')
print('WEIGHTS_DONE')
"@ | Set-Content -Encoding UTF8 $wPy
  Say "downloading MuseTalk weights..."
  & $VenvPy $wPy 2>&1 | Out-Host
  Pop-Location
}
if (-not (Test-Path $mkV15)) { Die "musetalkV15/unet.pth missing" }
if (-not (Test-Path (Join-Path $Repo "models\face-parse-bisent\79999_iter.pth"))) { Die "face-parse weight missing (gdown may have rate-limited)" }
Write-Host "MT_STEP6_OK"

$sw.Stop()
Write-Host ("MT_SETUP_OK root=$Root venv=$VenvPy repo=$Repo elapsed_s=" + [int]$sw.Elapsed.TotalSeconds)
exit 0
