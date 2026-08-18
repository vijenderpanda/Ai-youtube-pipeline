# deploy/gpu/cv2_setup.ps1
# Idempotent install of CosyVoice 2 (Alibaba, Apache-2.0) for English zero-shot
# cloning on the RTX 3060 worker. Native Windows, NO conda / 7-Zip / compiler —
# the current repo uses `wetext` (pure-py) + prebuilt `kaldifst` wheels instead of
# pynini. Everything lives under %LOCALAPPDATA%\cv (outside the factory repo).
# Markers CV2_STEP0..6 / CV2_SETUP_OK / CV2_SETUP_FAIL.
param([string]$RepoRoot)
$ErrorActionPreference = "Continue"; $ProgressPreference = "SilentlyContinue"
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"

$Root = Join-Path $env:LOCALAPPDATA "cv"
$Venv = Join-Path $Root "venv"
$Repo = Join-Path $Root "CosyVoice"
$Cache = Join-Path $Root "cache"
$Model = Join-Path $Repo "pretrained_models\CosyVoice2-0.5B"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
$env:MODELSCOPE_CACHE = Join-Path $Cache "modelscope"; $env:HF_HOME = Join-Path $Cache "hf"
New-Item -ItemType Directory -Force -Path $Root, $Cache | Out-Null
function Say ($m) { Write-Host ("[cv2] " + $m) }
function Die ($m) { Write-Host ("CV2_SETUP_FAIL " + $m); exit 1 }
$sw = [System.Diagnostics.Stopwatch]::StartNew()
try { Say ("gpu: " + ((& nvidia-smi --query-gpu=name,memory.free --format=csv,noheader) -join "; ")) } catch {}

function Find310 {
  try { $p = (& py -3.10 -c "import sys;print(sys.executable)" 2>$null); if ($p) { return $p.Trim() } } catch {}
  $c = Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe"; if (Test-Path $c) { return $c }; return $null
}
$py = Find310
if (-not $py) { $s = Get-Command python -ErrorAction SilentlyContinue; if ($s) { $py = $s.Source } }
if (-not $py) { Die "no python 3.10 (run tts_setup first, it winget-installs it)" }
& git config --global core.longpaths true
Say "python=$py"; Write-Host "CV2_STEP0_OK"

if (-not (Test-Path $VenvPy)) {
  & $py -m venv $Venv 2>&1 | Out-Host
  if (-not (Test-Path $VenvPy)) { Die "venv creation failed" }
  & $VenvPy -m pip install -U pip setuptools wheel 2>&1 | Out-Host
}
Write-Host "CV2_STEP1_OK"

if (-not (Test-Path (Join-Path $Repo "requirements.txt"))) {
  Say "cloning CosyVoice (recursive)..."
  if (Test-Path $Repo) { Remove-Item -Recurse -Force $Repo }
  & git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git "$Repo" 2>&1 | Out-Host
  Push-Location $Repo; & git submodule update --init --recursive 2>&1 | Out-Host; Pop-Location
  if (-not (Test-Path (Join-Path $Repo "requirements.txt"))) { Die "clone failed" }
}
Write-Host "CV2_STEP2_OK"

function CudaOK { try { return ((& $VenvPy -c "import torch;print(torch.cuda.is_available())" 2>$null).Trim() -eq "True") } catch { return $false } }
if (-not (CudaOK)) {
  Say "installing torch 2.3.1 cu121..."
  & $VenvPy -m pip install torch==2.3.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cu121 2>&1 | Out-Host
}
if (-not (CudaOK)) { Die "torch CUDA not available" }
Write-Host "CV2_STEP3_OK"

# openai-whisper's setup.py does `import pkg_resources`, which setuptools>=81 drops.
# Pin setuptools<81 in the venv AND (via PIP_CONSTRAINT) in the isolated build envs
# so the sdist builds on a box without a compiler.
& $VenvPy -m pip install "setuptools<81" wheel 2>&1 | Out-Host
$constraints = Join-Path $Root "constraints.txt"
"setuptools<81" | Set-Content -Encoding ASCII $constraints
$env:PIP_CONSTRAINT = $constraints
Say "installing requirements (compiler-free: wetext + kaldifst wheel)..."
& $VenvPy -m pip install -r (Join-Path $Repo "requirements.txt") 2>&1 | Out-Host
$rc = $LASTEXITCODE
& $VenvPy -m pip install "wetext==0.0.4" 2>&1 | Out-Host
Remove-Item Env:\PIP_CONSTRAINT -ErrorAction SilentlyContinue
if ($rc -ne 0) { Die "pip install -r requirements failed (exit $rc)" }
Write-Host "CV2_STEP4_OK"

# verify the cosyvoice package imports (class only, no weights yet)
$imp = (& $VenvPy -c "import sys;sys.path.insert(0,r'$Repo\third_party\Matcha-TTS');sys.path.insert(0,r'$Repo');from cosyvoice.cli.cosyvoice import CosyVoice2;print('impok')" 2>&1)
if ("$imp" -notmatch "impok") { Die ("cosyvoice import failed: " + ("$imp" -replace "`r?`n"," | ").Substring(0,[Math]::Min(400,"$imp".Length))) }
Write-Host "CV2_STEP5_OK"

if (-not (Test-Path (Join-Path $Model "llm.pt"))) {
  Say "downloading CosyVoice2-0.5B weights (~2.5 GB)..."
  & $VenvPy -c "import os;os.environ['MODELSCOPE_CACHE']=r'$($Cache)\modelscope';from modelscope import snapshot_download;snapshot_download('iic/CosyVoice2-0.5B', local_dir=r'$Model')" 2>&1 | Out-Host
}
if (-not (Test-Path (Join-Path $Model "llm.pt"))) { Die "weights download incomplete (no llm.pt)" }
Write-Host "CV2_STEP6_OK"

$sw.Stop()
Write-Host ("CV2_SETUP_OK root=$Root venv=$VenvPy repo=$Repo model=$Model elapsed_s=" + [int]$sw.Elapsed.TotalSeconds)
exit 0
