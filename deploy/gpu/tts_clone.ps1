# deploy/gpu/tts_clone.ps1
# GPT-SoVITS English zero-shot clone from a REFERENCE URL. Downloads the reference
# wav, runs api_v2.py headless, clones the voice to speak -Text, verifies, uploads
# the result to the public factory-renders bucket, and prints RENDER_PATH +
# PUBLIC_URL. Assumes tts_setup.ps1 has run.
#
# worker: powershell.exe -NonInteractive -File <this> -RepoRoot <REPO>
#   -RefUrl <url to reference wav> -RefText "<exact transcript of the ref>"
#   -Text "<what to speak>" [-Tag <label>]
param(
  [string]$RepoRoot,
  [string]$RefUrl,
  [string]$RefText,
  [string]$Text,
  [string]$Tag = "clone"
)
$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"

$Root   = Join-Path $env:LOCALAPPDATA "gpt-sovits"
$Venv   = Join-Path $Root "venv"
$Repo   = Join-Path $Root "GPT-SoVITS"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
$Cfg    = Join-Path $Root "tts_infer.yaml"
$RefWav = Join-Path $Root ("ref\" + $Tag + "_ref.wav")
$srvErr = Join-Path $Root "api_stderr.log"
$srvOut = Join-Path $Root "api_stdout.log"

function Say ($m) { Write-Host ("[clone] " + $m) }
function Die ($m) { Write-Host ("CLONE_FAIL " + $m); exit 1 }
function ErrTail { (Get-Content $srvErr -Tail 30 -ErrorAction SilentlyContinue) -join "`n" }

if (-not $RefUrl -or -not $RefText -or -not $Text) { Die "need -RefUrl, -RefText, -Text" }
foreach ($p in @($VenvPy, (Join-Path $Repo "api_v2.py"), $Cfg)) {
  if (-not (Test-Path $p)) { Die "missing $p -- run tts_setup.ps1 first" }
}
New-Item -ItemType Directory -Force -Path (Join-Path $Root "ref") | Out-Null
$OutDir = Join-Path $RepoRoot "renders_out\gpu"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$OutWav = Join-Path $OutDir ("tts_" + $Tag + "_" + $stamp + ".wav")

$sw = [System.Diagnostics.Stopwatch]::StartNew()

# --- download the reference ---
Say "downloading reference: $RefUrl"
try { Invoke-WebRequest -Uri $RefUrl -OutFile $RefWav -TimeoutSec 60 | Out-Null } catch { Die ("reference download failed: " + $_.Exception.Message) }
if (-not (Test-Path $RefWav) -or (Get-Item $RefWav).Length -lt 4000) { Die "reference wav missing/too small" }
Write-Host "CLONE_REF_OK"

# --- start api_v2.py headless ---
Say "starting api_v2.py (first model load ~30-90s)..."
$srv = Start-Process -FilePath $VenvPy `
  -ArgumentList @("api_v2.py", "-a", "127.0.0.1", "-p", "9880", "-c", $Cfg) `
  -WorkingDirectory $Repo -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput $srvOut -RedirectStandardError $srvErr
try {
  $ready = $false
  for ($i = 0; $i -lt 60; $i++) {
    if ($srv.HasExited) { break }
    try { $tcp = New-Object Net.Sockets.TcpClient; $tcp.Connect("127.0.0.1", 9880); $tcp.Close(); $ready = $true; break }
    catch { Start-Sleep -Seconds 3 }
  }
  if ($srv.HasExited) { Die ("api_v2.py exited early (code " + $srv.ExitCode + "). stderr tail:`n" + (ErrTail)) }
  if (-not $ready) { Die ("api server did not open port 9880 within ~180s. stderr tail:`n" + (ErrTail)) }
  Say "server up; cloning..."

  $body = @{
    text = $Text; text_lang = "en"
    ref_audio_path = ($RefWav -replace '\\', '/')
    prompt_text = $RefText; prompt_lang = "en"
    media_type = "wav"; streaming_mode = $false
  } | ConvertTo-Json
  try {
    Invoke-WebRequest -Uri "http://127.0.0.1:9880/tts" -Method Post -ContentType "application/json" `
      -Body $body -OutFile $OutWav -TimeoutSec 180 | Out-Null
  } catch { Die ("POST /tts failed: " + $_.Exception.Message + "`nstderr tail:`n" + (ErrTail)) }
}
finally {
  if ($srv -and -not $srv.HasExited) { & taskkill /F /T /PID $srv.Id *> $null }
}

# --- verify ---
if (-not (Test-Path $OutWav)) { Die "no output wav produced" }
$sz = (Get-Item $OutWav).Length
if ($sz -lt 8000) { Die ("output too small ($sz bytes) -- likely a JSON error body") }
$dur = ""
try { $dur = (& ffprobe -v error -show_entries format=duration -of csv=p=0 "$OutWav").Trim() } catch {}

# --- upload result to the public bucket ---
$envf = Join-Path $RepoRoot "secrets\factory.env"
function GetEnv ($n) { $m = Select-String -Path $envf -Pattern "^$n=" | Select-Object -First 1; if ($m) { return ($m.Line -replace "^$n=", "").Trim() } return "" }
$SUPA = GetEnv "SUPABASE_URL"; $KEY = GetEnv "SUPABASE_SERVICE_KEY"
$pub = ""
if ($SUPA -and $KEY) {
  $dest = "gpu-samples/" + (Split-Path $OutWav -Leaf)
  try {
    Invoke-RestMethod -Method Put -Uri "$SUPA/storage/v1/object/factory-renders/$dest" -ContentType "audio/wav" `
      -Headers @{ Authorization = "Bearer $KEY"; apikey = $KEY; "x-upsert" = "true" } -Body ([IO.File]::ReadAllBytes($OutWav)) | Out-Null
    $pub = "$SUPA/storage/v1/object/public/factory-renders/$dest"
  } catch { Say ("upload failed (non-fatal): " + $_.Exception.Message) }
}
$sw.Stop()
$vram = ""; try { $vram = ((& nvidia-smi --query-gpu=memory.used --format=csv,noheader) -join "; ") } catch {}
Write-Host ("CLONE_OK RENDER_PATH=$OutWav bytes=$sz dur=${dur}s elapsed_s=" + [int]$sw.Elapsed.TotalSeconds + " vram=$vram PUBLIC_URL=$pub")
exit 0
