# deploy/gpu/musetalk_gen.ps1
# MuseTalk 1.5 talking-head: downloads a face (still image or mp4) + an audio wav,
# lip-syncs them on the RTX 3060, uploads the mp4, prints MT_GEN_OK RENDER_PATH +
# PUBLIC_URL. Assumes musetalk_setup.ps1 has run.
#
# worker: powershell.exe -NonInteractive -File <this> -RepoRoot <REPO>
#   -FaceUrl <png/mp4 url> -AudioUrl <wav url> [-BboxShift 0] [-Fps 25] [-Tag mt]
param([string]$RepoRoot, [string]$FaceUrl, [string]$AudioUrl, [int]$BboxShift = 0, [int]$Fps = 25, [string]$Tag = "mt")
$ErrorActionPreference = "Continue"; $ProgressPreference = "SilentlyContinue"
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"

$Root = Join-Path $env:LOCALAPPDATA "musetalk"
$Venv = Join-Path $Root "venv"; $Repo = Join-Path $Root "MuseTalk"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
$env:HF_HOME = Join-Path $Root "hf-cache"
function Say ($m) { Write-Host ("[mtgen] " + $m) }
function Die ($m) { Write-Host ("MT_GEN_FAIL " + $m); exit 1 }

if (-not $FaceUrl -or -not $AudioUrl) { Die "need -FaceUrl and -AudioUrl" }
if (-not (Test-Path $VenvPy)) { Die "no venv -- run musetalk_setup.ps1 first" }
if (-not (Test-Path (Join-Path $Repo "models\musetalkV15\unet.pth"))) { Die "no model -- run musetalk_setup.ps1" }

$dataV = Join-Path $Repo "data\video"; $dataA = Join-Path $Repo "data\audio"
New-Item -ItemType Directory -Force -Path $dataV, $dataA | Out-Null
$faceExt = if ($FaceUrl -match '\.mp4($|\?)') { "mp4" } else { "png" }
$face = Join-Path $dataV ("host." + $faceExt)
$audio = Join-Path $dataA "line.wav"
try { Invoke-WebRequest -UseBasicParsing -Uri $FaceUrl -OutFile $face -TimeoutSec 90 | Out-Null } catch { Die ("face download failed: " + $_.Exception.Message) }
try { Invoke-WebRequest -UseBasicParsing -Uri $AudioUrl -OutFile $audio -TimeoutSec 90 | Out-Null } catch { Die ("audio download failed: " + $_.Exception.Message) }

$cfgDir = Join-Path $Repo "configs\inference"; New-Item -ItemType Directory -Force -Path $cfgDir | Out-Null
$cfg = Join-Path $cfgDir "test_img.yaml"
@"
task_0:
  video_path: "data/video/host.$faceExt"
  audio_path: "data/audio/line.wav"
  bbox_shift: $BboxShift
"@ | Set-Content -Encoding UTF8 $cfg

$resDir = Join-Path $Repo "results\test"
if (Test-Path $resDir) { Get-ChildItem $resDir -Filter *.mp4 -Recurse -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue }
$ffdir = Split-Path (Get-Command ffmpeg).Source
$sw = [System.Diagnostics.Stopwatch]::StartNew()

Push-Location $Repo
Say "running MuseTalk v1.5 (first face-detect is slower)..."
& $VenvPy -m scripts.inference --inference_config configs\inference\test_img.yaml `
  --result_dir results\test --unet_model_path models\musetalkV15\unet.pth `
  --unet_config models\musetalkV15\musetalk.json --version v15 --fps $Fps `
  --batch_size 8 --use_float16 --ffmpeg_path $ffdir 2>&1 | Out-Host
$rc = $LASTEXITCODE
Pop-Location
if ($rc -ne 0) { Die "scripts.inference exited $rc" }

$mp4 = Get-ChildItem $resDir -Filter *.mp4 -Recurse -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1
if (-not $mp4) { Die "no output mp4 in results\test" }
$OutDir = Join-Path $RepoRoot "renders_out\gpu"; New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$OutMp4 = Join-Path $OutDir ("talk_" + $Tag + "_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".mp4")
Copy-Item $mp4.FullName $OutMp4 -Force
$sz = (Get-Item $OutMp4).Length
if ($sz -lt 20000) { Die "output mp4 too small ($sz bytes)" }

$envf = Join-Path $RepoRoot "secrets\factory.env"
function GetEnv ($n) { $m = Select-String -Path $envf -Pattern "^$n=" | Select-Object -First 1; if ($m) { return ($m.Line -replace "^$n=", "").Trim() } return "" }
$SUPA = GetEnv "SUPABASE_URL"; $KEY = GetEnv "SUPABASE_SERVICE_KEY"; $pub = ""
if ($SUPA -and $KEY) {
  $dest = "gpu-samples/" + (Split-Path $OutMp4 -Leaf)
  try {
    Invoke-RestMethod -Method Put -Uri "$SUPA/storage/v1/object/factory-renders/$dest" -ContentType "video/mp4" `
      -Headers @{ Authorization = "Bearer $KEY"; apikey = $KEY; "x-upsert" = "true" } -Body ([IO.File]::ReadAllBytes($OutMp4)) | Out-Null
    $pub = "$SUPA/storage/v1/object/public/factory-renders/$dest"
  } catch { Say ("upload failed: " + $_.Exception.Message) }
}
$sw.Stop()
$vram = ""; try { $vram = ((& nvidia-smi --query-gpu=memory.used --format=csv,noheader) -join "; ") } catch {}
Write-Host ("MT_GEN_OK RENDER_PATH=$OutMp4 bytes=$sz elapsed_s=" + [int]$sw.Elapsed.TotalSeconds + " vram=$vram PUBLIC_URL=$pub")
exit 0
