# deploy/gpu/comfy_setup.ps1
# Idempotent install of ComfyUI + FLUX.1-schnell (GGUF) on the RTX 3060 worker, for
# headless free/local image gen (Leonardo replacement). Native Windows, no compiler.
# Everything under %LOCALAPPDATA%\comfy (outside the factory repo). All weights are
# Apache-2.0/MIT (commercial-safe). Markers COMFY_STEP0..5 / COMFY_SETUP_OK.
param([string]$RepoRoot)
$ErrorActionPreference = "Continue"; $ProgressPreference = "SilentlyContinue"
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"

$Root = Join-Path $env:LOCALAPPDATA "comfy"
$Venv = Join-Path $Root "venv"
$Repo = Join-Path $Root "ComfyUI"
$Models = Join-Path $Repo "models"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
New-Item -ItemType Directory -Force -Path $Root | Out-Null
function Say ($m) { Write-Host ("[comfy] " + $m) }
function Die ($m) { Write-Host ("COMFY_SETUP_FAIL " + $m); exit 1 }
$sw = [System.Diagnostics.Stopwatch]::StartNew()
try { Say ("gpu: " + ((& nvidia-smi --query-gpu=name,memory.free --format=csv,noheader) -join "; ")) } catch {}

function Find310 {
  try { $p = (& py -3.10 -c "import sys;print(sys.executable)" 2>$null); if ($p) { return $p.Trim() } } catch {}
  $c = Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe"; if (Test-Path $c) { return $c }; return $null
}
$py = Find310
if (-not $py) { Die "no python 3.10 (run tts_setup first; it winget-installs it)" }
& git config --global core.longpaths true
Say "python=$py"; Write-Host "COMFY_STEP0_OK"

if (-not (Test-Path $VenvPy)) {
  & $py -m venv $Venv 2>&1 | Out-Host
  if (-not (Test-Path $VenvPy)) { Die "venv creation failed" }
  & $VenvPy -m pip install -U pip wheel 2>&1 | Out-Host
}
Write-Host "COMFY_STEP1_OK"

if (-not (Test-Path (Join-Path $Repo "main.py"))) {
  Say "cloning ComfyUI..."
  if (Test-Path $Repo) { Remove-Item -Recurse -Force $Repo }
  & git clone --depth 1 https://github.com/comfyanonymous/ComfyUI "$Repo" 2>&1 | Out-Host
  if (-not (Test-Path (Join-Path $Repo "main.py"))) { Die "ComfyUI clone failed" }
}
$gguf = Join-Path $Repo "custom_nodes\ComfyUI-GGUF"
if (-not (Test-Path (Join-Path $gguf "nodes.py"))) {
  & git clone --depth 1 https://github.com/city96/ComfyUI-GGUF "$gguf" 2>&1 | Out-Host
}
Write-Host "COMFY_STEP2_OK"

function CudaOK { try { return ((& $VenvPy -c "import torch;print(torch.cuda.is_available())" 2>$null).Trim() -eq "True") } catch { return $false } }
if (-not (CudaOK)) {
  Say "installing torch cu126 (cp310)..."
  & $VenvPy -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126 2>&1 | Out-Host
}
if (-not (CudaOK)) { Die "torch CUDA not available" }
Write-Host "COMFY_STEP3_OK"

Say "installing ComfyUI requirements + gguf..."
& $VenvPy -m pip install -r (Join-Path $Repo "requirements.txt") 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) { Die "ComfyUI requirements install failed" }
& $VenvPy -m pip install -U gguf huggingface_hub 2>&1 | Out-Host
Write-Host "COMFY_STEP4_OK"

New-Item -ItemType Directory -Force -Path (Join-Path $Models "unet"), (Join-Path $Models "text_encoders"), (Join-Path $Models "vae") | Out-Null
$dlPy = Join-Path $Root "_dl.py"
@"
import os
from huggingface_hub import hf_hub_download
jobs = [
 ('city96/FLUX.1-schnell-gguf',      'flux1-schnell-Q5_K_S.gguf',      r'$Models\unet'),
 ('comfyanonymous/flux_text_encoders','t5xxl_fp8_e4m3fn.safetensors',  r'$Models\text_encoders'),
 ('comfyanonymous/flux_text_encoders','clip_l.safetensors',            r'$Models\text_encoders'),
 ('black-forest-labs/FLUX.1-schnell', 'ae.safetensors',                r'$Models\vae'),
]
for repo, fn, dst in jobs:
    if os.path.exists(os.path.join(dst, fn)):
        print('have', fn); continue
    print('downloading', fn, 'from', repo)
    hf_hub_download(repo_id=repo, filename=fn, local_dir=dst)
print('MODELS_DONE')
"@ | Set-Content -Encoding UTF8 $dlPy
Say "downloading FLUX-schnell models (~14 GB total)..."
& $VenvPy $dlPy 2>&1 | Out-Host
if (-not (Test-Path (Join-Path $Models "unet\flux1-schnell-Q5_K_S.gguf"))) { Die "UNet GGUF download incomplete" }
if (-not (Test-Path (Join-Path $Models "vae\ae.safetensors"))) { Die "VAE download incomplete (schnell repo may be gated -- needs HF token)" }
if (-not (Test-Path (Join-Path $Models "text_encoders\t5xxl_fp8_e4m3fn.safetensors"))) { Die "T5 download incomplete" }
Write-Host "COMFY_STEP5_OK"

$sw.Stop()
Write-Host ("COMFY_SETUP_OK root=$Root venv=$VenvPy repo=$Repo elapsed_s=" + [int]$sw.Elapsed.TotalSeconds)
exit 0
