# deploy/gpu/liveportrait_gen.ps1
# LivePortrait: animate a still portrait with head motion from a driving clip (a
# bundled idle example by default) -> a moving base mp4 (silent), uploaded. Feed that
# mp4 into musetalk_gen.ps1 as -FaceUrl to add audio-synced lips. Assumes
# liveportrait_setup.ps1 has run. Prints LP_GEN_OK RENDER_PATH + PUBLIC_URL.
#
# worker: powershell.exe -NonInteractive -File <this> -RepoRoot <REPO>
#   -SrcUrl <portrait png/jpg> [-DrivingRel assets\examples\driving\d0.mp4] [-Tag lp]
param([string]$RepoRoot, [string]$SrcUrl, [string]$DrivingRel = "", [string]$Tag = "lp")
$ErrorActionPreference = "Continue"; $ProgressPreference = "SilentlyContinue"
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"

$Root = Join-Path $env:LOCALAPPDATA "liveportrait"
$Venv = Join-Path $Root "venv"; $Repo = Join-Path $Root "LivePortrait"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
$env:HF_HOME = Join-Path $Root "hf-cache"
function Say ($m) { Write-Host ("[lpgen] " + $m) }
function Die ($m) { Write-Host ("LP_GEN_FAIL " + $m); exit 1 }

if (-not $SrcUrl) { Die "need -SrcUrl" }
if (-not (Test-Path $VenvPy)) { Die "no venv -- run liveportrait_setup.ps1 first" }
if (-not (Test-Path (Join-Path $Repo "inference.py"))) { Die "no LivePortrait repo" }
$assets = Join-Path $Repo "assets"; New-Item -ItemType Directory -Force -Path $assets | Out-Null
$src = Join-Path $assets "host_src.jpg"
try { Invoke-WebRequest -UseBasicParsing -Uri $SrcUrl -OutFile $src -TimeoutSec 90 | Out-Null } catch { Die ("src download failed: " + $_.Exception.Message) }

# driving clip: provided rel path, else the first bundled example (subtle idle motion)
$drivDir = Join-Path $Repo "assets\examples\driving"
$driv = ""
if ($DrivingRel -and (Test-Path (Join-Path $Repo $DrivingRel))) { $driv = Join-Path $Repo $DrivingRel }
else { $c = Get-ChildItem $drivDir -Filter *.mp4 -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object -First 1; if ($c) { $driv = $c.FullName } }
if (-not $driv) { Die "no driving video in $drivDir" }
Say "driving=$driv"

$outDir = Join-Path $Repo "animations"
if (Test-Path $outDir) { Get-ChildItem $outDir -Filter *.mp4 -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue }
$sw = [System.Diagnostics.Stopwatch]::StartNew()
Push-Location $Repo
Say "running LivePortrait (first run warms up ~1 min)..."
& $VenvPy inference.py -s $src -d $driv --flag_crop_driving_video --output_dir animations 2>&1 | Out-Host
$rc = $LASTEXITCODE
Pop-Location
if ($rc -ne 0) { Die "inference.py exited $rc" }
# the animated result (skip the side-by-side *_concat.mp4)
$mp4 = Get-ChildItem $outDir -Filter *.mp4 -ErrorAction SilentlyContinue | Where-Object { $_.Name -notmatch "_concat" } | Sort-Object LastWriteTime | Select-Object -Last 1
if (-not $mp4) { $mp4 = Get-ChildItem $outDir -Filter *.mp4 -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1 }
if (-not $mp4) { Die "no output mp4 in animations" }

$OutDir2 = Join-Path $RepoRoot "renders_out\gpu"; New-Item -ItemType Directory -Force -Path $OutDir2 | Out-Null
$OutMp4 = Join-Path $OutDir2 ("motion_" + $Tag + "_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".mp4")
Copy-Item $mp4.FullName $OutMp4 -Force
$sz = (Get-Item $OutMp4).Length
if ($sz -lt 20000) { Die "output mp4 too small ($sz bytes)" }
$envf = Join-Path $RepoRoot "secrets\factory.env"
function GetEnv ($n) { $m = Select-String -Path $envf -Pattern "^$n=" | Select-Object -First 1; if ($m) { return ($m.Line -replace "^$n=", "").Trim() } return "" }
$SUPA = GetEnv "SUPABASE_URL"; $KEY = GetEnv "SUPABASE_SERVICE_KEY"; $pub = ""
if ($SUPA -and $KEY) {
  $dest = "gpu-refs/" + (Split-Path $OutMp4 -Leaf)
  try {
    Invoke-RestMethod -Method Put -Uri "$SUPA/storage/v1/object/factory-renders/$dest" -ContentType "video/mp4" `
      -Headers @{ Authorization = "Bearer $KEY"; apikey = $KEY; "x-upsert" = "true" } -Body ([IO.File]::ReadAllBytes($OutMp4)) | Out-Null
    $pub = "$SUPA/storage/v1/object/public/factory-renders/$dest"
  } catch { Say ("upload failed: " + $_.Exception.Message) }
}
$sw.Stop()
Write-Host ("LP_GEN_OK RENDER_PATH=$OutMp4 bytes=$sz elapsed_s=" + [int]$sw.Elapsed.TotalSeconds + " PUBLIC_URL=$pub")
exit 0
