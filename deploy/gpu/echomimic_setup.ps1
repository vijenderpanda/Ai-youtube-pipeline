# deploy/gpu/echomimic_setup.ps1
# Idempotent install of EchoMimic V1 (BadToBest/antgroup — audio-driven portrait
# talking-head, HeyGen-class, FREE) on the RTX 3060 worker. Native Windows, NO
# conda/compiler: every dep resolves to a cp310 wheel. Own venv + ~14GB weights
# under %LOCALAPPDATA%\echomimic (outside the git repo). Spec verified against the
# repo (torch<=2.2.2 hard cap; diffusers 0.24.0 needs hub 0.20.3 + transformers
# 4.38.2; numpy 1.26.4 / Pillow 9.5.0 pinned last). Markers ECHO_STEP0..5/ECHO_SETUP_OK.
param([string]$RepoRoot)
$ErrorActionPreference = "Continue"; $ProgressPreference = "SilentlyContinue"
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"

$Root = Join-Path $env:LOCALAPPDATA "echomimic"
$Venv = Join-Path $Root "venv"
$Repo = Join-Path $Root "EchoMimic"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
$env:HF_HOME = Join-Path $Root "hf-cache"
New-Item -ItemType Directory -Force -Path $Root, $env:HF_HOME | Out-Null
function Say ($m) { Write-Host ("[em] " + $m) }
function Die ($m) { Write-Host ("ECHO_SETUP_FAIL " + $m); exit 1 }
$sw = [System.Diagnostics.Stopwatch]::StartNew()
try { Say ("gpu: " + ((& nvidia-smi --query-gpu=name,memory.free,driver_version --format=csv,noheader) -join "; ")) } catch {}

function Find310 {
  try { $p = (& py -3.10 -c "import sys;print(sys.executable)" 2>$null); if ($p) { return $p.Trim() } } catch {}
  $c = Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe"; if (Test-Path $c) { return $c }; return $null
}
$py = Find310
if (-not $py) { Die "no python 3.10" }
& git config --global core.longpaths true
Say "python=$py"; Write-Host "ECHO_STEP0_OK"

if (-not (Test-Path $VenvPy)) {
  & $py -m venv $Venv 2>&1 | Out-Host
  if (-not (Test-Path $VenvPy)) { Die "venv creation failed" }
  & $VenvPy -m pip install -U pip wheel setuptools 2>&1 | Out-Host
}
Write-Host "ECHO_STEP1_OK"

if (-not (Test-Path (Join-Path $Repo "infer_audio2vid_acc.py"))) {
  Say "cloning EchoMimic..."
  if (Test-Path $Repo) { Remove-Item -Recurse -Force $Repo }
  & git clone --depth 1 https://github.com/BadToBest/EchoMimic "$Repo" 2>&1 | Out-Host
  if (-not (Test-Path (Join-Path $Repo "infer_audio2vid_acc.py"))) { Die "clone failed" }
}
Write-Host "ECHO_STEP2_OK"

# torch 2.2.2 cu121 FIRST + EXPLICIT (the <=2.2.2 constraint otherwise lets pip grab a
# CPU wheel). 3060=sm_86 is in cu121. cu118 fallback if the driver were <531 (not here).
function CudaOK { try { return ((& $VenvPy -c "import torch;print(torch.cuda.is_available())" 2>$null).Trim() -eq "True") } catch { return $false } }
if (-not (CudaOK)) {
  Say "installing torch 2.2.2 cu121..."
  & $VenvPy -m pip install torch==2.2.2 torchvision==0.17.2 torchaudio==2.2.2 --index-url https://download.pytorch.org/whl/cu121 2>&1 | Out-Host
}
if (-not (CudaOK)) { Die "torch CUDA not available" }
Write-Host "ECHO_STEP3_OK"

# deps: requirements.txt content, pinned; overrides installed LAST so they win.
function DepsOK { try { return ((& $VenvPy -c "import diffusers,transformers,facenet_pytorch,mediapipe,omegaconf,av,numpy;import moviepy.editor;from huggingface_hub import snapshot_download;print(1)" 2>$null).Trim() -eq "1") } catch { return $false } }
if (-not (DepsOK)) {
  Say "installing EchoMimic deps (torch already pinned; won't be touched)..."
  & $VenvPy -m pip install diffusers==0.24.0 transformers==4.38.2 einops==0.4.1 omegaconf==2.3.0 `
      ffmpeg-python==0.2.0 facenet_pytorch==2.5.0 moviepy==1.0.3 av==11.0.0 `
      torchmetrics torchtyping tqdm mediapipe gradio 2>&1 | Out-Host
  # 4 ecosystem breakages, pinned LAST: hub 0.20.3 (diffusers 0.24.0 cached_download,
  # issue #207); numpy 1.26.4 (numpy-2 ABI crash under torch/mediapipe/opencv); Pillow
  # 9.5.0 (moviepy 1.0.3 Image.ANTIALIAS); opencv 4.9.0.80 (holds numpy 1.26).
  Say "applying override pins (huggingface_hub / numpy / Pillow / opencv)..."
  & $VenvPy -m pip install "huggingface_hub==0.20.3" "numpy==1.26.4" "Pillow==9.5.0" "opencv-python==4.9.0.80" 2>&1 | Out-Host
}
if (-not (DepsOK)) {
  Say "deps import failed -- detail:"
  & $VenvPy -c "import diffusers,transformers,facenet_pytorch,mediapipe,omegaconf,av,numpy;import moviepy.editor;from huggingface_hub import snapshot_download" 2>&1 | Out-Host
  Die "deps import failed"
}
Write-Host "ECHO_STEP4_OK"

# weights: targeted ACC subset (~14GB) from the UNGATED BadToBest/EchoMimic repo ->
# pretrained_weights/. snapshot_download resumes, so a 90min-capped job that gets
# killed mid-download finishes on a re-run. All backbones (VAE, sd-image-variations,
# whisper-tiny) are bundled in this one repo -- no separate stabilityai/lambdalabs fetch.
$w1 = Join-Path $Repo "pretrained_weights\denoising_unet_acc.pth"
$ppw = ((Join-Path $Repo "pretrained_weights") -replace '\\', '/')
if (-not (Test-Path $w1)) {
  $dl = Join-Path $Root "_emw.py"
  @"
from huggingface_hub import snapshot_download
snapshot_download('BadToBest/EchoMimic', local_dir='$ppw', local_dir_use_symlinks=False, resume_download=True, allow_patterns=[
 'denoising_unet_acc.pth','motion_module_acc.pth','reference_unet.pth','face_locator.pth',
 'audio_processor/whisper_tiny.pt',
 'sd-vae-ft-mse/config.json','sd-vae-ft-mse/diffusion_pytorch_model.bin',
 'sd-image-variations-diffusers/model_index.json','sd-image-variations-diffusers/unet/*',
 'sd-image-variations-diffusers/image_encoder/*','sd-image-variations-diffusers/feature_extractor/*',
 'sd-image-variations-diffusers/vae/*','sd-image-variations-diffusers/scheduler/*'])
print('WEIGHTS_DONE')
"@ | Set-Content -Encoding UTF8 $dl
  Say "downloading EchoMimic ACC weights (~14GB; first run slow, resumable)..."
  & $VenvPy $dl 2>&1 | Out-Host
}
# verify the essential files landed
$need = @(
  "pretrained_weights\denoising_unet_acc.pth",
  "pretrained_weights\motion_module_acc.pth",
  "pretrained_weights\reference_unet.pth",
  "pretrained_weights\face_locator.pth",
  "pretrained_weights\audio_processor\whisper_tiny.pt",
  "pretrained_weights\sd-vae-ft-mse\config.json",
  "pretrained_weights\sd-image-variations-diffusers\model_index.json",
  "pretrained_weights\sd-image-variations-diffusers\unet\diffusion_pytorch_model.bin"
)
foreach ($n in $need) {
  $p = Join-Path $Repo $n
  if (-not (Test-Path $p)) { Die "weight missing: $n (download incomplete -- re-run to resume)" }
}
Write-Host "ECHO_STEP5_OK"

$sw.Stop()
Write-Host ("ECHO_SETUP_OK root=$Root venv=$VenvPy repo=$Repo elapsed_s=" + [int]$sw.Elapsed.TotalSeconds)
exit 0
