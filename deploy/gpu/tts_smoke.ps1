# deploy/gpu/tts_smoke.ps1
# GPT-SoVITS English zero-shot smoke test on the RTX 3060 worker. Assumes
# tts_setup.ps1 already ran. Generates a reference clip ON-BOX via Windows SAPI
# (no committed binaries), starts api_v2.py headless, clones the reference to speak
# a NEW English line, verifies the wav, and prints SMOKE_OK RENDER_PATH=...
#
# Run by the worker as: powershell.exe -NonInteractive -File <this> -RepoRoot <REPO>
param([string]$RepoRoot)
$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"

$Root   = Join-Path $env:LOCALAPPDATA "gpt-sovits"
$Venv   = Join-Path $Root "venv"
$Repo   = Join-Path $Root "GPT-SoVITS"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
$Cfg    = Join-Path $Root "tts_infer.yaml"
$RefWav = Join-Path $Root "ref\sapi_ref.wav"
$srvOut = Join-Path $Root "api_stdout.log"
$srvErr = Join-Path $Root "api_stderr.log"

function Say ($m) { Write-Host ("[smoke] " + $m) }
function Die ($m) { Write-Host ("SMOKE_FAIL " + $m); exit 1 }
function ErrTail { (Get-Content $srvErr -Tail 30 -ErrorAction SilentlyContinue) -join "`n" }

foreach ($p in @($VenvPy, (Join-Path $Repo "api_v2.py"), $Cfg)) {
  if (-not (Test-Path $p)) { Die "missing $p -- run tts_setup.ps1 first" }
}
New-Item -ItemType Directory -Force -Path (Join-Path $Root "ref") | Out-Null
$OutDir = Join-Path $RepoRoot "renders_out\gpu"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$OutWav = Join-Path $OutDir ("tts_smoke_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".wav")

$sw = [System.Diagnostics.Stopwatch]::StartNew()

# --- reference clip via Windows SAPI (self-contained; run #2 will use Sol's real voice) ---
$refText = "The quick brown fox jumps over the lazy dog while the sun sets over the hills."
try {
  Add-Type -AssemblyName System.Speech
  $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
  $synth.Rate = -1
  $synth.SetOutputToWaveFile($RefWav)
  $synth.Speak($refText)
  $synth.Dispose()
} catch { Die ("SAPI reference generation failed: " + $_.Exception.Message) }
if (-not (Test-Path $RefWav)) { Die "reference wav not produced" }
Say ("reference: " + $RefWav)
Write-Host "SMOKE_REF_OK"

# --- start api_v2.py headless (models load before the port opens) ---
Say "starting api_v2.py (first model load ~30-90s)..."
$srv = Start-Process -FilePath $VenvPy `
  -ArgumentList @("api_v2.py", "-a", "127.0.0.1", "-p", "9880", "-c", $Cfg) `
  -WorkingDirectory $Repo -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput $srvOut -RedirectStandardError $srvErr
try {
  $ready = $false
  for ($i = 0; $i -lt 60; $i++) {
    if ($srv.HasExited) { break }
    try {
      $tcp = New-Object Net.Sockets.TcpClient
      $tcp.Connect("127.0.0.1", 9880); $tcp.Close(); $ready = $true; break
    } catch { Start-Sleep -Seconds 3 }
  }
  if ($srv.HasExited) { Die ("api_v2.py exited early (code " + $srv.ExitCode + "). stderr tail:`n" + (ErrTail)) }
  if (-not $ready) { Die ("api server did not open port 9880 within ~180s. stderr tail:`n" + (ErrTail)) }
  Say "server up; requesting synthesis..."

  $sayText = "Hello from the RTX thirty sixty. This voice was cloned locally with GPT SoVITS, no cloud service required."
  $body = @{
    text = $sayText; text_lang = "en"
    ref_audio_path = ($RefWav -replace '\\', '/')
    prompt_text = $refText; prompt_lang = "en"
    media_type = "wav"; streaming_mode = $false
  } | ConvertTo-Json
  try {
    Invoke-WebRequest -Uri "http://127.0.0.1:9880/tts" -Method Post -ContentType "application/json" `
      -Body $body -OutFile $OutWav -TimeoutSec 180 | Out-Null
  } catch {
    Die ("POST /tts failed: " + $_.Exception.Message + "`nstderr tail:`n" + (ErrTail))
  }
}
finally {
  if ($srv -and -not $srv.HasExited) { & taskkill /F /T /PID $srv.Id *> $null }
}

# --- verify the output ---
if (-not (Test-Path $OutWav)) { Die "no output wav produced" }
$sz = (Get-Item $OutWav).Length
if ($sz -lt 8000) { Die ("output too small ($sz bytes) -- likely a JSON error body, not audio") }
$dur = ""
try { $dur = (& ffprobe -v error -show_entries format=duration -of csv=p=0 "$OutWav").Trim() } catch {}
$sw.Stop()
$vram = ""
try { $vram = ((& nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader) -join "; ") } catch {}
Write-Host ("SMOKE_OK RENDER_PATH=$OutWav bytes=$sz dur=${dur}s elapsed_s=" + [int]$sw.Elapsed.TotalSeconds + " vram=$vram")
exit 0
