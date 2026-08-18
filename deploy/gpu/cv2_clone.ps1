# deploy/gpu/cv2_clone.ps1
# CosyVoice 2 English zero-shot clone from a reference URL. Downloads the ref,
# runs scripts/gpu/cv2_infer.py in the CosyVoice venv, verifies, uploads the result
# to the public factory-renders bucket, prints CV2_CLONE_OK RENDER_PATH + PUBLIC_URL.
# Assumes cv2_setup.ps1 has run.
#
# worker: powershell.exe -NonInteractive -File <this> -RepoRoot <REPO>
#   -RefUrl <url> -RefText "<exact transcript of ref>" -Text "<what to speak>" [-Tag cv2]
param([string]$RepoRoot, [string]$RefUrl, [string]$RefText, [string]$Text, [string]$Tag = "cv2")
$ErrorActionPreference = "Continue"; $ProgressPreference = "SilentlyContinue"
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"

$Root = Join-Path $env:LOCALAPPDATA "cv"
$Venv = Join-Path $Root "venv"; $Repo = Join-Path $Root "CosyVoice"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
$Model = Join-Path $Repo "pretrained_models\CosyVoice2-0.5B"
$env:MODELSCOPE_CACHE = Join-Path $Root "cache\modelscope"; $env:HF_HOME = Join-Path $Root "cache\hf"
function Say ($m) { Write-Host ("[cv2clone] " + $m) }
function Die ($m) { Write-Host ("CV2_CLONE_FAIL " + $m); exit 1 }

if (-not $RefUrl -or -not $RefText -or -not $Text) { Die "need -RefUrl, -RefText, -Text" }
if (-not (Test-Path $VenvPy)) { Die "no venv -- run cv2_setup.ps1 first" }
if (-not (Test-Path (Join-Path $Model "llm.pt"))) { Die "no model -- run cv2_setup.ps1 first" }
$infer = Join-Path $RepoRoot "scripts\gpu\cv2_infer.py"
if (-not (Test-Path $infer)) { Die "missing $infer" }

New-Item -ItemType Directory -Force -Path (Join-Path $Root "ref") | Out-Null
$RefWav = Join-Path $Root ("ref\" + $Tag + "_ref.wav")
$OutDir = Join-Path $RepoRoot "renders_out\gpu"; New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$OutWav = Join-Path $OutDir ("tts_" + $Tag + "_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".wav")
$sw = [System.Diagnostics.Stopwatch]::StartNew()

Say "downloading reference: $RefUrl"
try { Invoke-WebRequest -UseBasicParsing -Uri $RefUrl -OutFile $RefWav -TimeoutSec 60 | Out-Null }
catch { Die ("ref download failed: " + $_.Exception.Message) }

Say "running CosyVoice2 zero-shot (first load ~30-60s)..."
& $VenvPy $infer --cv-repo $Repo --model-dir $Model --ref $RefWav --ref-text $RefText --text $Text --out $OutWav 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $OutWav)) { Die "cv2_infer.py failed (exit $LASTEXITCODE)" }
$sz = (Get-Item $OutWav).Length
if ($sz -lt 8000) { Die "output too small ($sz bytes)" }
$dur = ""; try { $dur = (& ffprobe -v error -show_entries format=duration -of csv=p=0 "$OutWav").Trim() } catch {}

# upload result to the public bucket
$envf = Join-Path $RepoRoot "secrets\factory.env"
function GetEnv ($n) { $m = Select-String -Path $envf -Pattern "^$n=" | Select-Object -First 1; if ($m) { return ($m.Line -replace "^$n=", "").Trim() } return "" }
$SUPA = GetEnv "SUPABASE_URL"; $KEY = GetEnv "SUPABASE_SERVICE_KEY"; $pub = ""
if ($SUPA -and $KEY) {
  $dest = "gpu-samples/" + (Split-Path $OutWav -Leaf)
  try {
    Invoke-RestMethod -Method Put -Uri "$SUPA/storage/v1/object/factory-renders/$dest" -ContentType "audio/wav" `
      -Headers @{ Authorization = "Bearer $KEY"; apikey = $KEY; "x-upsert" = "true" } -Body ([IO.File]::ReadAllBytes($OutWav)) | Out-Null
    $pub = "$SUPA/storage/v1/object/public/factory-renders/$dest"
  } catch { Say ("upload failed: " + $_.Exception.Message) }
}
$sw.Stop()
$vram = ""; try { $vram = ((& nvidia-smi --query-gpu=memory.used --format=csv,noheader) -join "; ") } catch {}
Write-Host ("CV2_CLONE_OK RENDER_PATH=$OutWav bytes=$sz dur=${dur}s elapsed_s=" + [int]$sw.Elapsed.TotalSeconds + " vram=$vram PUBLIC_URL=$pub")
exit 0
