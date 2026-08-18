# deploy/gpu/tts_finetune.ps1
# Headless GPT-SoVITS v2 single-speaker fine-tune on the RTX 3060 worker. Downloads
# a dataset zip (wavs/ + <list>), extracts features, trains SoVITS (s2) + GPT (s1),
# and reports the fine-tuned weight paths. Verified recipe (webui.py-driven). Stage
# markers PREP_* / S2_TRAIN_OK / S1_TRAIN_OK / FINETUNE_OK; FT_FAIL <why> on error.
#
# worker: powershell.exe -NonInteractive -File <this> -RepoRoot <REPO>
#   -DatasetUrl <zip url> [-Exp sol] [-ListName sol.list] [-S2Epochs 10] [-S1Epochs 15] [-Batch 4]
param(
  [string]$RepoRoot,
  [string]$DatasetUrl,
  [string]$Exp = "sol",
  [string]$ListName = "sol.list",
  [int]$S2Epochs = 10,
  [int]$S1Epochs = 15,
  [int]$Batch = 4
)
$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"

$Root   = Join-Path $env:LOCALAPPDATA "gpt-sovits"
$Repo   = Join-Path $Root "GPT-SoVITS"
$VenvPy = Join-Path $Root "venv\Scripts\python.exe"
$Input  = Join-Path $Repo "input"
$WavDir = Join-Path $Input "wavs"
$ListF  = Join-Path $Input $ListName
$Logs   = Join-Path $Repo ("logs\" + $Exp)
$PM     = "GPT_SoVITS/pretrained_models"

function Say ($m) { Write-Host ("[ft] " + $m) }
function Die ($m) { Write-Host ("FT_FAIL " + $m); Pop-Location -ErrorAction SilentlyContinue; exit 1 }
foreach ($p in @($VenvPy, (Join-Path $Repo "api_v2.py"))) { if (-not (Test-Path $p)) { Die "missing $p -- run tts_setup.ps1 first" } }
if (-not $DatasetUrl) { Die "need -DatasetUrl" }

$sw = [System.Diagnostics.Stopwatch]::StartNew()
try { Say ("gpu: " + ((& nvidia-smi --query-gpu=name,memory.free --format=csv,noheader) -join "; ")) } catch {}

# --- fetch + extract dataset (clean slate) ---
if (Test-Path $Input) { Remove-Item -Recurse -Force $Input }
if (Test-Path $Logs)  { Remove-Item -Recurse -Force $Logs }
New-Item -ItemType Directory -Force -Path $Input, $Logs | Out-Null
$zip = Join-Path $Root "dataset.zip"
Say "downloading dataset: $DatasetUrl"
try { Invoke-WebRequest -Uri $DatasetUrl -OutFile $zip -TimeoutSec 120 | Out-Null } catch { Die ("dataset download failed: " + $_.Exception.Message) }
try { Expand-Archive -Path $zip -DestinationPath $Input -Force } catch { Die ("unzip failed: " + $_.Exception.Message) }
if (-not (Test-Path $ListF)) { Die "list not found after extract: $ListF" }
$nwav = (Get-ChildItem $WavDir -Filter *.wav -ErrorAction SilentlyContinue).Count
if ($nwav -lt 3) { Die "too few wavs extracted ($nwav)" }
Say "dataset: $nwav wavs, list=$ListF"
Write-Host "PREP_DATASET_OK"

# --- ensure the SoVITS discriminator (s2D) exists (needed for s2 training) ---
$s2D = Join-Path $Repo "GPT_SoVITS\pretrained_models\gsv-v2final-pretrained\s2D2333k.pth"
if (-not (Test-Path $s2D)) {
  Say "downloading s2D2333k.pth..."
  & $VenvPy -c "from huggingface_hub import snapshot_download as s; s(repo_id='lj1995/GPT-SoVITS', local_dir=r'$($Root)\cache\pretrained_models', allow_patterns=['gsv-v2final-pretrained/s2D2333k.pth'])" 2>&1 | Out-Host
}
if (-not (Test-Path $s2D)) { Die "s2D2333k.pth missing (discriminator) -- cannot train s2" }

# --- Windows DataLoader safety: force num_workers=0 in s2_train.py (recipe: #1 hang risk) ---
$s2py = Join-Path $Repo "GPT_SoVITS\s2_train.py"
$src = Get-Content $s2py -Raw
$patched = $src -replace 'num_workers\s*=\s*\d+', 'num_workers=0' `
                -replace 'persistent_workers\s*=\s*True', 'persistent_workers=False' `
                -replace 'prefetch_factor\s*=\s*\d+', 'prefetch_factor=None'
if ($patched -ne $src) { Set-Content -Encoding UTF8 $s2py $patched; Say "patched s2_train.py DataLoader -> num_workers=0" }
# s1 (GPT) DataLoader hardcodes persistent_workers=True + prefetch_factor=16, both
# illegal with the num_workers=0 we set in the s1 config -> patch them too.
$s1dm = Join-Path $Repo "GPT_SoVITS\AR\data\data_module.py"
if (Test-Path $s1dm) {
  $s1src = Get-Content $s1dm -Raw
  $s1p = $s1src -replace 'persistent_workers\s*=\s*True', 'persistent_workers=False' `
                -replace 'prefetch_factor\s*=\s*\d+', 'prefetch_factor=None'
  if ($s1p -ne $s1src) { Set-Content -Encoding UTF8 $s1dm $s1p; Say "patched s1 data_module.py DataLoader" }
}

# --- headless import path + CWD (the scripts do bare `from text...`/`import utils`) ---
$env:PYTHONPATH = "$Repo;$Repo\GPT_SoVITS;$Repo\GPT_SoVITS\BigVGAN;$Repo\tools;$Repo\tools\asr;$Repo\tools\uvr5"
Push-Location $Repo

# common preprocessing env
$env:inp_text = $ListF
$env:inp_wav_dir = $WavDir
$env:exp_name = $Exp
$env:opt_dir = $Logs
$env:is_half = "True"
$env:i_part = "0"
$env:all_parts = "1"
$env:_CUDA_VISIBLE_DEVICES = "0"
$env:version = "v2"

# --- 1A: text/phonemes ---
$env:bert_pretrained_dir = "$Repo\GPT_SoVITS\pretrained_models\chinese-roberta-wwm-ext-large"
Say "1A get-text..."
& $VenvPy -s "GPT_SoVITS/prepare_datasets/1-get-text.py" 2>&1 | Out-Host
$n2t0 = Join-Path $Logs "2-name2text-0.txt"
if (-not (Test-Path $n2t0)) { Die "1A produced no 2-name2text-0.txt" }
Copy-Item -Force $n2t0 (Join-Path $Logs "2-name2text.txt")
Write-Host "PREP_1A_OK"

# --- 1B: SSL (hubert) + 32k wav ---
$env:cnhubert_base_dir = "$Repo\GPT_SoVITS\pretrained_models\chinese-hubert-base"
Say "1B get-hubert-wav32k..."
& $VenvPy -s "GPT_SoVITS/prepare_datasets/2-get-hubert-wav32k.py" 2>&1 | Out-Host
if (-not (Test-Path (Join-Path $Logs "4-cnhubert"))) { Die "1B produced no 4-cnhubert" }
Write-Host "PREP_1B_OK"

# --- 1C: semantic tokens (v2 auto-detected from s2G size) ---
$env:pretrained_s2G = "$PM/gsv-v2final-pretrained/s2G2333k.pth"
$env:s2config_path = "GPT_SoVITS/configs/s2.json"
Say "1C get-semantic..."
& $VenvPy -s "GPT_SoVITS/prepare_datasets/3-get-semantic.py" 2>&1 | Out-Host
$sem0 = Join-Path $Logs "6-name2semantic-0.tsv"
if (-not (Test-Path $sem0)) { Die "1C produced no 6-name2semantic-0.tsv" }
$sem = Join-Path $Logs "6-name2semantic.tsv"
"item_name`tsemantic_audio" | Set-Content -Encoding UTF8 $sem
Get-Content $sem0 | Add-Content -Encoding UTF8 $sem
Write-Host "PREP_1C_OK"

# --- write patched training configs via the venv python (json + yaml) ---
$patchPy = Join-Path $Root "_patch_ft.py"
@'
import json, os, sys
import yaml
repo, exp, s2ep, s1ep, batch = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
logs = f"logs/{exp}"; pm = "GPT_SoVITS/pretrained_models"
logsdir = os.path.join(repo, "logs", exp)
# ---- s2.json ----
s2 = json.load(open(os.path.join(repo, "GPT_SoVITS", "configs", "s2.json"), encoding="utf-8"))
s2.setdefault("train", {}); s2.setdefault("model", {}); s2.setdefault("data", {})
s2["train"].update({
    "batch_size": batch, "epochs": s2ep, "text_low_lr_rate": 0.4,
    "pretrained_s2G": f"{pm}/gsv-v2final-pretrained/s2G2333k.pth",
    "pretrained_s2D": f"{pm}/gsv-v2final-pretrained/s2D2333k.pth",
    "if_save_latest": True, "if_save_every_weights": True,
    "save_every_epoch": max(2, s2ep // 2), "gpu_numbers": "0",
    "grad_ckpt": False, "fp16_run": True,
})
s2["model"]["version"] = "v2"
s2["data"]["exp_dir"] = logs
s2["s2_ckpt_dir"] = logs
s2["save_weight_dir"] = "SoVITS_weights_v2"
s2["name"] = exp
s2["version"] = "v2"
json.dump(s2, open(os.path.join(logsdir, "tmp_s2.json"), "w", encoding="utf-8"), indent=2)
print("wrote tmp_s2.json")
# ---- s1longer-v2.yaml ----
s1 = yaml.safe_load(open(os.path.join(repo, "GPT_SoVITS", "configs", "s1longer-v2.yaml"), encoding="utf-8"))
s1.setdefault("train", {}); s1.setdefault("data", {})
s1["train"].update({
    "batch_size": batch, "epochs": s1ep, "save_every_n_epoch": max(2, s1ep // 3),
    "if_save_every_weights": True, "if_save_latest": True, "if_dpo": False,
    "precision": "16-mixed", "half_weights_save_dir": "GPT_weights_v2", "exp_name": exp,
})
s1["train_semantic_path"] = f"{logs}/6-name2semantic.tsv"
s1["train_phoneme_path"] = f"{logs}/2-name2text.txt"
s1["output_dir"] = f"{logs}/logs_s1_v2"
s1["pretrained_s1"] = f"{pm}/gsv-v2final-pretrained/s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt"
s1["data"]["num_workers"] = 0
yaml.safe_dump(s1, open(os.path.join(logsdir, "tmp_s1.yaml"), "w", encoding="utf-8"), sort_keys=False, allow_unicode=True)
print("wrote tmp_s1.yaml")
'@ | Set-Content -Encoding UTF8 $patchPy
& $VenvPy $patchPy $Repo $Exp $S2Epochs $S1Epochs $Batch 2>&1 | Out-Host
$tmpS2 = Join-Path $Logs "tmp_s2.json"; $tmpS1 = Join-Path $Logs "tmp_s1.yaml"
if (-not (Test-Path $tmpS2) -or -not (Test-Path $tmpS1)) { Die "config patch failed" }
Write-Host "PREP_CONFIG_OK"

# checkpoint + weight output dirs — the WebUI pre-creates these; headless my_save()
# does a bare shutil.move into them and errors if they don't exist.
New-Item -ItemType Directory -Force -Path `
  (Join-Path $Logs "logs_s2_v2"), (Join-Path $Logs "logs_s1_v2"), `
  (Join-Path $Repo "SoVITS_weights_v2"), (Join-Path $Repo "GPT_weights_v2") | Out-Null

# --- train SoVITS (s2) ---
Say "training SoVITS (s2): batch=$Batch epochs=$S2Epochs ..."
& $VenvPy -s "GPT_SoVITS/s2_train.py" --config "$tmpS2" 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) { Die "s2_train.py exited $LASTEXITCODE" }
$sovits = Get-ChildItem (Join-Path $Repo "SoVITS_weights_v2") -Filter "$Exp*.pth" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1
if (-not $sovits) { Die "no SoVITS weight produced in SoVITS_weights_v2" }
Write-Host ("S2_TRAIN_OK " + $sovits.FullName)

# --- train GPT (s1) ---
$env:hz = "25hz"
Say "training GPT (s1): batch=$Batch epochs=$S1Epochs ..."
& $VenvPy -s "GPT_SoVITS/s1_train.py" --config_file "$tmpS1" 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) { Die "s1_train.py exited $LASTEXITCODE" }
$gpt = Get-ChildItem (Join-Path $Repo "GPT_weights_v2") -Filter "$Exp*.ckpt" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1
if (-not $gpt) { Die "no GPT weight produced in GPT_weights_v2" }
Write-Host ("S1_TRAIN_OK " + $gpt.FullName)

Pop-Location
$sw.Stop()
# emit repo-relative weight paths (what /set_*_weights wants)
$sovitsRel = "SoVITS_weights_v2/" + $sovits.Name
$gptRel = "GPT_weights_v2/" + $gpt.Name
Write-Host ("FINETUNE_OK exp=$Exp SOVITS=$sovitsRel GPT=$gptRel elapsed_s=" + [int]$sw.Elapsed.TotalSeconds)
exit 0
