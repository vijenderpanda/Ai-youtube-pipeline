# deploy/gpu/echomimic_v3_setup.ps1
# Idempotent install of EchoMimicV3-Flash (antgroup/echomimic_v3, AAAI 2026) on the
# RTX 3060 worker. Apache-2.0 code+weights; the Flash path is the "12G VRAM is All
# YOU NEED" variant: 8-step generation, up to 768x768, audio-driven portrait from a
# still. Own venv + weights under %LOCALAPPDATA%\echomimic_v3 (outside the git repo).
#
# Weights (~10GB total, resumable):
#   alibaba-pai/Wan2.1-Fun-V1.1-1.3B-InP        -> weights\Wan2.1-Fun-V1.1-1.3B-InP
#   TencentGameMate/chinese-wav2vec2-base        -> weights\chinese-wav2vec2-base
#   BadToBest/EchoMimicV3 echomimicv3-flash-pro/* -> weights\flash\transformer\
# Markers EM3_STEP0..5 / EM3_SETUP_OK|EM3_SETUP_FAIL.
param([string]$RepoRoot, [switch]$Fresh)
$ErrorActionPreference = "Continue"; $ProgressPreference = "SilentlyContinue"
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"

$Root = Join-Path $env:LOCALAPPDATA "echomimic_v3"
$Venv = Join-Path $Root "venv"
$Repo = Join-Path $Root "echomimic_v3"
$W = Join-Path $Root "weights"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
$env:HF_HOME = Join-Path $Root "hf-cache"
New-Item -ItemType Directory -Force -Path $Root, $W, $env:HF_HOME | Out-Null
function Say ($m) { Write-Host ("[em3] " + $m) }
function Die ($m) { Remove-Item $Lock -ErrorAction SilentlyContinue; Write-Host ("EM3_SETUP_FAIL " + $m); exit 1 }
$sw = [System.Diagnostics.Stopwatch]::StartNew()

# concurrency guard (same trap as V1: two installs into one venv = WinError 32)
$Lock = Join-Path $Root ".installing.lock"
if ((Test-Path $Lock) -and -not $Fresh) {
  $age = ((Get-Date) - (Get-Item $Lock).LastWriteTime).TotalMinutes
  if ($age -lt 95) { Die ("another install in progress (lock age " + [int]$age + "min); pass -Fresh to override") }
}
if ($Fresh -and (Test-Path $Venv)) { Say "-Fresh: removing venv..."; Remove-Item -Recurse -Force $Venv -ErrorAction SilentlyContinue }
Set-Content -Path $Lock -Value $PID -Encoding ASCII
try { Say ("gpu: " + ((& nvidia-smi --query-gpu=name,memory.free,driver_version --format=csv,noheader) -join "; ")) } catch {}

function Find310 {
  try { $p = (& py -3.10 -c "import sys;print(sys.executable)" 2>$null); if ($p) { return $p.Trim() } } catch {}
  $c = Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe"; if (Test-Path $c) { return $c }; return $null
}
$py = Find310
if (-not $py) { Die "no python 3.10" }
& git config --global core.longpaths true
Say "python=$py"; Write-Host "EM3_STEP0_OK"

if (-not (Test-Path $VenvPy)) {
  & $py -m venv $Venv 2>&1 | Out-Host
  if (-not (Test-Path $VenvPy)) { Die "venv creation failed" }
  & $VenvPy -m pip install -U pip wheel setuptools 2>&1 | Out-Host
}
Write-Host "EM3_STEP1_OK"

if (-not (Test-Path (Join-Path $Repo "infer_flash.py"))) {
  Say "cloning echomimic_v3..."
  if (Test-Path $Repo) { Remove-Item -Recurse -Force $Repo }
  & git clone --depth 1 https://github.com/antgroup/echomimic_v3 "$Repo" 2>&1 | Out-Host
  if (-not (Test-Path (Join-Path $Repo "infer_flash.py"))) { Die "clone failed (no infer_flash.py)" }
}
Write-Host "EM3_STEP2_OK"

# torch cu121 FIRST + EXPLICIT (requirements says torch>=2.1.2; unpinned pip grabs CPU).
# 2.5.1 cu121 is the wheel already proven on this worker (numpy 2.x compatible).
function CudaOK { try { return ((& $VenvPy -c "import torch;print(torch.cuda.is_available() and tuple(map(int,torch.__version__.split('+')[0].split('.')[:2]))>=(2,6))" 2>$null).Trim() -eq "True") } catch { return $false } }
if (-not (CudaOK)) {
  Say "installing torch 2.6.0 cu124 (transformers CVE-2025-32434 gate needs >=2.6 for torch.load)..."
  & $VenvPy -m pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124 2>&1 | Out-Host
}
if (-not (CudaOK)) { Die "torch CUDA not available" }
Write-Host "EM3_STEP3_OK"

# deps: LEAN set — only what infer_flash.py actually imports (verified against the
# file: diffusers/transformers/omegaconf/PIL/decord/librosa/moviepy/pyloudnorm/
# einops + src/* internals). tensorflow+retina-face are NOT used by the flash
# path (app-only) and their resolver fights broke two installs; mmgp (quantized
# UI only) hijacked torch to 2.13-CPU. All three DROPPED. torch re-pinned after.
function DepsOK { try { return ((& $VenvPy -c "import diffusers,transformers,librosa,decord,omegaconf,einops,safetensors,accelerate,pyloudnorm,imageio;from moviepy import VideoFileClip;print(1)" 2>$null).Trim() -eq "1") } catch { return $false } }
if (-not (DepsOK)) {
  Say "installing lean deps (no tf / no retina-face / no mmgp)..."
  & $VenvPy -m pip install "diffusers>=0.30.1" "transformers>=4.46.2" "accelerate>=0.25.0" `
      einops safetensors omegaconf SentencePiece "imageio[ffmpeg]" ftfy `
      scikit-image opencv-python librosa "moviepy==2.2.1" pyloudnorm 2>&1 | Out-Host
  if ($LASTEXITCODE -ne 0) { Die "lean deps install failed" }
  Say "installing decord (prebuilt wheel only)..."
  & $VenvPy -m pip install decord --only-binary=:all: 2>&1 | Out-Host
  if ($LASTEXITCODE -ne 0) { Die "decord wheel install failed" }
  # resolver may have moved torch/numpy — force the known-good pins back LAST
  Say "re-pinning torch 2.6.0 cu124 + numpy 2.1.3..."
  & $VenvPy -m pip install --force-reinstall --no-deps torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124 2>&1 | Out-Host
  & $VenvPy -m pip install "numpy==2.1.3" 2>&1 | Out-Host
}
if (-not (DepsOK)) {
  Say "deps import failed -- detail:"
  & $VenvPy -c "import diffusers,transformers,librosa,decord,omegaconf,einops,safetensors,accelerate,pyloudnorm,imageio;from moviepy import VideoFileClip" 2>&1 | Out-Host
  Die "deps import failed"
}
if (-not (CudaOK)) { Die "torch lost CUDA after dep resolution" }
Write-Host "EM3_STEP4_OK"

# weights: three snapshot_downloads (resumable; a killed 90-min job finishes on re-run)
$dl = Join-Path $Root "_em3w.py"
$WF = ($W -replace '\\', '/')
@"
from huggingface_hub import snapshot_download
snapshot_download('alibaba-pai/Wan2.1-Fun-V1.1-1.3B-InP', local_dir='$WF/Wan2.1-Fun-V1.1-1.3B-InP', local_dir_use_symlinks=False)
print('W1_DONE')
snapshot_download('TencentGameMate/chinese-wav2vec2-base', local_dir='$WF/chinese-wav2vec2-base', local_dir_use_symlinks=False)
print('W2_DONE')
snapshot_download('BadToBest/EchoMimicV3', local_dir='$WF/em3', local_dir_use_symlinks=False, allow_patterns=['echomimicv3-flash-pro/*'])
print('W3_DONE')
"@ | Set-Content -Encoding UTF8 $dl
$tf = Join-Path $W "em3\echomimicv3-flash-pro\diffusion_pytorch_model.safetensors"
$w1 = Join-Path $W "Wan2.1-Fun-V1.1-1.3B-InP\diffusion_pytorch_model.safetensors"
if (-not (Test-Path $tf) -or -not (Test-Path $w1)) {
  Say "downloading weights (~10GB; resumable)..."
  & $VenvPy $dl 2>&1 | Out-Host
}
foreach ($n in @($tf, $w1, (Join-Path $W "chinese-wav2vec2-base\config.json"))) {
  if (-not (Test-Path $n)) { Die "weight missing: $n (re-run to resume)" }
}
Write-Host "EM3_STEP5_OK"

Remove-Item $Lock -ErrorAction SilentlyContinue
$sw.Stop()
Write-Host ("EM3_SETUP_OK root=$Root venv=$VenvPy repo=$Repo weights=$W elapsed_s=" + [int]$sw.Elapsed.TotalSeconds)
exit 0
