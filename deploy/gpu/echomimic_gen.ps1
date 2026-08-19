# deploy/gpu/echomimic_gen.ps1
# EchoMimic V1 audio-driven talking head: reference portrait + wav -> lip-synced mp4
# with natural head/eye motion (NO driving clip, NO mouth-inpaint seam). Assumes
# echomimic_setup.ps1 has run. Prints ECHO_GEN_OK RENDER_PATH + PUBLIC_URL.
#
# worker: powershell.exe -NonInteractive -File <this> -RepoRoot <REPO>
#   -SrcUrl <portrait png/jpg> -AudioUrl <wav> [-Steps 6] [-Cfg 1.0] [-Size 512] [-Fps 24] [-Tag em]
param([string]$RepoRoot, [string]$SrcUrl, [string]$AudioUrl,
      [int]$Steps = 6, [double]$Cfg = 1.0, [int]$Size = 512, [int]$Fps = 24, [string]$Tag = "em")
$ErrorActionPreference = "Continue"; $ProgressPreference = "SilentlyContinue"
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"

$Root = Join-Path $env:LOCALAPPDATA "echomimic"
$Venv = Join-Path $Root "venv"; $Repo = Join-Path $Root "EchoMimic"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
$env:HF_HOME = Join-Path $Root "hf-cache"
function Say ($m) { Write-Host ("[emgen] " + $m) }
function Die ($m) { Write-Host ("ECHO_GEN_FAIL " + $m); exit 1 }

if (-not $SrcUrl -or -not $AudioUrl) { Die "need -SrcUrl and -AudioUrl" }
if (-not (Test-Path $VenvPy)) { Die "no venv -- run echomimic_setup.ps1 first" }
if (-not (Test-Path (Join-Path $Repo "infer_audio2vid_acc.py"))) { Die "no EchoMimic repo" }

# EchoMimic's code prepends $env:FFMPEG_PATH to PATH; the worker already has ffmpeg.
$ff = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($ff) { $env:FFMPEG_PATH = Split-Path $ff.Source }
$ffprobe = (Get-Command ffprobe -ErrorAction SilentlyContinue).Source

$inp = Join-Path $Repo "inputs"; New-Item -ItemType Directory -Force -Path $inp | Out-Null
$img = Join-Path $inp "ref.png"
$araw = Join-Path $inp "audio_src.bin"
$wav = Join-Path $inp "audio.wav"
try { Invoke-WebRequest -UseBasicParsing -Uri $SrcUrl -OutFile $img -TimeoutSec 90 | Out-Null } catch { Die ("image download failed: " + $_.Exception.Message) }
try { Invoke-WebRequest -UseBasicParsing -Uri $AudioUrl -OutFile $araw -TimeoutSec 90 | Out-Null } catch { Die ("audio download failed: " + $_.Exception.Message) }
# normalize audio to 16k mono wav (EchoMimic --sample_rate 16000)
& ffmpeg -y -v error -i $araw -ar 16000 -ac 1 $wav 2>&1 | Out-Host
if (-not (Test-Path $wav)) { Die "ffmpeg audio convert failed" }

# frames L = ceil(seconds * fps); the model also caps by audio length. Guard a runaway.
$dur = 6.0
if ($ffprobe) { try { $dur = [double](& $ffprobe -v error -show_entries format=duration -of csv=p=0 $wav) } catch {} }
$L = [int][math]::Ceiling($dur * $Fps)
if ($L -lt 24) { $L = 24 }
if ($L -gt 1440) { $L = 1440 }   # ~60s hard cap on this card
Say ("audio=" + [math]::Round($dur, 2) + "s -> L=$L frames @ $Fps fps; size=${Size}x${Size} steps=$Steps cfg=$Cfg")

# rewrite the ACC config's test_cases to {ref.png: [audio.wav]} (absolute fwd-slash paths)
$imgF = ($img -replace '\\', '/'); $wavF = ($wav -replace '\\', '/')
$cfgYaml = Join-Path $Repo "configs\prompts\animation_acc.yaml"
$rw = Join-Path $Root "_emyaml.py"
@"
import sys
from omegaconf import OmegaConf
y, img, wav = sys.argv[1], sys.argv[2], sys.argv[3]
c = OmegaConf.load(y)
c.test_cases = { img: [wav] }
OmegaConf.save(c, y)
print('YAML_OK')
"@ | Set-Content -Encoding UTF8 $rw
& $VenvPy $rw $cfgYaml $imgF $wavF 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) { Die "yaml rewrite failed" }

# clear stale outputs so the newest-mp4 pick is unambiguous
$outRoot = Join-Path $Repo "output"
if (Test-Path $outRoot) { Get-ChildItem $outRoot -Recurse -Filter *.mp4 -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue }
$sw = [System.Diagnostics.Stopwatch]::StartNew()

Push-Location $Repo
Say "running EchoMimic V1 (ACC) -- diffusion, first run warms up..."
& $VenvPy -u infer_audio2vid_acc.py --config ./configs/prompts/animation_acc.yaml `
  -W $Size -H $Size -L $L --steps $Steps --cfg $Cfg --seed 420 --fps $Fps 2>&1 | Out-Host
$rc = $LASTEXITCODE
Pop-Location
if ($rc -ne 0) { Die "infer_audio2vid_acc.py exited $rc" }

$mp4 = Get-ChildItem $outRoot -Recurse -Filter *_withaudio.mp4 -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1
if (-not $mp4) { $mp4 = Get-ChildItem $outRoot -Recurse -Filter *.mp4 -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1 }
if (-not $mp4) { Die "no output mp4 under output/" }

$OutDir = Join-Path $RepoRoot "renders_out\gpu"; New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$OutMp4 = Join-Path $OutDir ("echomimic_" + $Tag + "_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".mp4")
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
Write-Host ("ECHO_GEN_OK RENDER_PATH=$OutMp4 bytes=$sz frames=$L elapsed_s=" + [int]$sw.Elapsed.TotalSeconds + " vram=$vram PUBLIC_URL=$pub")
exit 0
