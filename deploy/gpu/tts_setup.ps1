# deploy/gpu/tts_setup.ps1
# One-time (idempotent) setup of GPT-SoVITS (MIT) for ENGLISH zero-shot TTS on the
# RTX 3060 Windows worker. EVERYTHING lives OUTSIDE the factory repo, under
# %LOCALAPPDATA%\gpt-sovits, so git pull / auto-update / the T5 offload never touch
# the multi-GB venv + weights.
#
# Compiler-free: skips pyopenjtalk / jieba_fast / opencc (JA/ZH only, lazily imported,
# never on the English path). Verified recipe. Prints stepwise markers; on the first
# failure prints SETUP_FAIL <why> and exits 1 so we know exactly how far it got.
#
# Run by the worker as: powershell.exe -NonInteractive -File <this> -RepoRoot <REPO>
param([string]$RepoRoot)
$ErrorActionPreference = "Continue"   # native tools (pip/git/winget) write progress to stderr; check exit codes explicitly
$ProgressPreference = "SilentlyContinue"
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"

$Root   = Join-Path $env:LOCALAPPDATA "gpt-sovits"
$Venv   = Join-Path $Root "venv"
$Repo   = Join-Path $Root "GPT-SoVITS"
$Cache  = Join-Path $Root "cache\pretrained_models"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
$Cfg    = Join-Path $Root "tts_infer.yaml"
New-Item -ItemType Directory -Force -Path $Root, (Join-Path $Root "cache") | Out-Null

function Say ($m) { Write-Host ("[setup] " + $m) }
function Die ($m) { Write-Host ("SETUP_FAIL " + $m); exit 1 }

$sw = [System.Diagnostics.Stopwatch]::StartNew()
Say "root=$Root repo_root=$RepoRoot"
try { Say ("gpu: " + ((& nvidia-smi --query-gpu=name,memory.free --format=csv,noheader) -join "; ")) } catch {}

# --- Step 0: Python 3.10 (fall back to system python only if winget can't provide it) ---
function Find310 {
  try { $p = (& py -3.10 -c "import sys;print(sys.executable)" 2>$null); if ($p) { return $p.Trim() } } catch {}
  $cand = Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe"
  if (Test-Path $cand) { return $cand }
  return $null
}
$pyBase = Find310
if (-not $pyBase) {
  Say "Python 3.10 absent -> winget install (user scope)..."
  & winget install -e --id Python.Python.3.10 --scope user --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Host
  Start-Sleep -Seconds 3
  $pyBase = Find310
}
if (-not $pyBase) {
  $sys = (Get-Command python -ErrorAction SilentlyContinue)
  if ($sys) { $pyBase = $sys.Source; Say "WARNING: using system python ($pyBase) -- 3.10 unavailable; English-only, untested upstream" }
}
if (-not $pyBase) { Die "no usable python (3.10 install failed and no system python)" }
Say "python = $pyBase"
Write-Host "STEP0_PYTHON_OK $pyBase"

# --- Step 1: venv ---
if (-not (Test-Path $VenvPy)) {
  Say "creating venv..."
  & $pyBase -m venv $Venv 2>&1 | Out-Host
  if (-not (Test-Path $VenvPy)) { Die "venv creation failed" }
  & $VenvPy -m pip install -U pip wheel 2>&1 | Out-Host
}
Write-Host "STEP1_VENV_OK"

# --- Step 2: clone repo (code only) ---
if (-not (Test-Path (Join-Path $Repo "api_v2.py"))) {
  Say "cloning GPT-SoVITS..."
  if (Test-Path $Repo) { Remove-Item -Recurse -Force $Repo }
  & git clone --depth 1 https://github.com/RVC-Boss/GPT-SoVITS "$Repo" 2>&1 | Out-Host
  if (-not (Test-Path (Join-Path $Repo "api_v2.py"))) { Die "git clone failed (no api_v2.py)" }
}
Write-Host "STEP2_CLONE_OK"

# --- Step 3: torch + torchaudio CUDA (cu121) FIRST so requirements never pulls a CPU build ---
function CudaOK { try { return ((& $VenvPy -c "import torch;print(torch.cuda.is_available())" 2>$null).Trim() -eq "True") } catch { return $false } }
if (-not (CudaOK)) {
  Say "installing torch+torchaudio cu121 (~2.5 GB)..."
  & $VenvPy -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121 2>&1 | Out-Host
}
if (-not (CudaOK)) { Die "torch CUDA not available after install" }
Write-Host "STEP3_TORCH_OK"

# --- Step 4: filtered requirements (drop the 4 compiler-only / ZH-JA lines) ---
$reqSrc = Join-Path $Repo "requirements.txt"
$reqEng = Join-Path $Root "requirements.english.txt"
if (-not (Test-Path $reqSrc)) { Die "requirements.txt missing in clone" }
(Get-Content $reqSrc) |
  Where-Object { $_.Trim() -ne "" -and $_ -notmatch 'pyopenjtalk|jieba_fast|opencc|--no-binary' } |
  Set-Content -Encoding UTF8 $reqEng
Say "installing filtered requirements (this is the long step)..."
& $VenvPy -m pip install -r $reqEng 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) { Die "pip install -r requirements.english.txt failed (exit $LASTEXITCODE)" }
Write-Host "STEP4_DEPS_OK"

# --- Step 5: NLTK data (g2p_en needs both tagger names + cmudict for headless EN) ---
Say "downloading NLTK data..."
& $VenvPy -c "import nltk; [nltk.download(x) for x in ('averaged_perceptron_tagger','averaged_perceptron_tagger_eng','cmudict')]" 2>&1 | Out-Host
Write-Host "STEP5_NLTK_OK"

# --- Step 6: v2 weights -> cache, junction the default path so hardcoded lookups resolve ---
$s2 = Join-Path $Cache "gsv-v2final-pretrained\s2G2333k.pth"
if (-not (Test-Path $s2)) {
  Say "downloading v2 pretrained weights (~1.1 GB)..."
  $dl = "from huggingface_hub import snapshot_download as s; s(repo_id='lj1995/GPT-SoVITS', local_dir=r'$Cache', allow_patterns=['chinese-hubert-base/*','chinese-roberta-wwm-ext-large/*','gsv-v2final-pretrained/*'])"
  & $VenvPy -c $dl 2>&1 | Out-Host
}
if (-not (Test-Path $s2)) { Die "weights download incomplete (no s2G2333k.pth)" }
$defPath = Join-Path $Repo "GPT_SoVITS\pretrained_models"
$isLink = (Test-Path $defPath) -and (((Get-Item $defPath -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)
if (-not $isLink) {
  if (Test-Path $defPath) { cmd /c rmdir /S /Q "$defPath" 2>$null }
  cmd /c mklink /J "$defPath" "$Cache" | Out-Host
}
if (-not (Test-Path (Join-Path $defPath "gsv-v2final-pretrained\s2G2333k.pth"))) { Die "junction to weights failed" }
Write-Host "STEP6_WEIGHTS_OK"

# --- Step 7: tts_infer.yaml -- load the repo's real config and set the custom: block
# (a bare custom-only file can miss keys the loader expects) ---
$cfgPy = @"
import yaml, os
src = os.path.join(r'$Repo', 'GPT_SoVITS', 'configs', 'tts_infer.yaml')
cfg = {}
if os.path.exists(src):
    with open(src, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f) or {}
cfg.setdefault('custom', {})
cfg['custom'].update({
    'device': 'cuda', 'is_half': True, 'version': 'v2',
    'bert_base_path': 'GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large',
    'cnhuhbert_base_path': 'GPT_SoVITS/pretrained_models/chinese-hubert-base',
    't2s_weights_path': 'GPT_SoVITS/pretrained_models/gsv-v2final-pretrained/s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt',
    'vits_weights_path': 'GPT_SoVITS/pretrained_models/gsv-v2final-pretrained/s2G2333k.pth',
})
with open(r'$Cfg', 'w', encoding='utf-8') as f:
    yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
print('config_written', r'$Cfg')
"@
& $VenvPy -c $cfgPy 2>&1 | Out-Host
if (-not (Test-Path $Cfg)) { Die "tts_infer.yaml not written" }
Write-Host "STEP7_CONFIG_OK"

$sw.Stop()
Write-Host ("SETUP_OK root=$Root venv_py=$VenvPy repo=$Repo cfg=$Cfg elapsed_s=" + [int]$sw.Elapsed.TotalSeconds)
exit 0
