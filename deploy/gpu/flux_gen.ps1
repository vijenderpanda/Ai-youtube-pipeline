# deploy/gpu/flux_gen.ps1
# FLUX.1-schnell headless image gen on the RTX 3060 worker: starts ComfyUI, runs
# scripts/gpu/flux_gen.py against its API, verifies, uploads the PNG to the public
# bucket, prints FLUX_OK RENDER_PATH + PUBLIC_URL. Assumes comfy_setup.ps1 has run.
#
# worker: powershell.exe -NonInteractive -File <this> -RepoRoot <REPO>
#   -Prompt "<text>" [-Seed N] [-Width 1024] [-Height 1024] [-Tag flux]
param([string]$RepoRoot, [string]$Prompt, [int]$Seed = 0, [int]$Width = 1024, [int]$Height = 1024, [string]$Tag = "flux")
$ErrorActionPreference = "Continue"; $ProgressPreference = "SilentlyContinue"
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"

$Root = Join-Path $env:LOCALAPPDATA "comfy"
$Venv = Join-Path $Root "venv"; $Repo = Join-Path $Root "ComfyUI"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
$gen = Join-Path $RepoRoot "scripts\gpu\flux_gen.py"
$srvOut = Join-Path $Root "comfy_stdout.log"; $srvErr = Join-Path $Root "comfy_stderr.log"
function Say ($m) { Write-Host ("[flux] " + $m) }
function Die ($m) { Write-Host ("FLUX_FAIL " + $m); exit 1 }
function ErrTail { (Get-Content $srvErr -Tail 30 -ErrorAction SilentlyContinue) -join "`n" }

if (-not $Prompt) { Die "need -Prompt" }
if (-not (Test-Path $VenvPy)) { Die "no venv -- run comfy_setup.ps1 first" }
if (-not (Test-Path (Join-Path $Repo "models\unet\flux1-schnell-Q5_K_S.gguf"))) { Die "no model -- run comfy_setup.ps1" }
if (-not (Test-Path $gen)) { Die "missing $gen" }
$OutDir = Join-Path $RepoRoot "renders_out\gpu"; New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$OutPng = Join-Path $OutDir ("img_" + $Tag + "_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".png")
if ($Seed -eq 0) { $Seed = Get-Random -Minimum 1 -Maximum 2000000000 }
$sw = [System.Diagnostics.Stopwatch]::StartNew()

Say "starting ComfyUI (first model load ~60-120s)..."
$srv = Start-Process -FilePath $VenvPy `
  -ArgumentList @("$Repo\main.py", "--listen", "127.0.0.1", "--port", "8188") `
  -WorkingDirectory $Repo -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput $srvOut -RedirectStandardError $srvErr
try {
  $ready = $false
  for ($i = 0; $i -lt 90; $i++) {
    if ($srv.HasExited) { break }
    try { $t = New-Object Net.Sockets.TcpClient; $t.Connect("127.0.0.1", 8188); $t.Close(); $ready = $true; break }
    catch { Start-Sleep -Seconds 3 }
  }
  if ($srv.HasExited) { Die ("ComfyUI exited early (code " + $srv.ExitCode + "). stderr:`n" + (ErrTail)) }
  if (-not $ready) { Die ("ComfyUI port not up in ~270s. stderr:`n" + (ErrTail)) }
  Start-Sleep -Seconds 3
  Say "generating (seed=$Seed, ${Width}x${Height}, 4 steps)..."
  & $VenvPy $gen --server "http://127.0.0.1:8188" --prompt $Prompt --seed $Seed --width $Width --height $Height --out $OutPng 2>&1 | Out-Host
  if ($LASTEXITCODE -ne 0 -or -not (Test-Path $OutPng)) { Die ("flux_gen.py failed (exit $LASTEXITCODE). stderr:`n" + (ErrTail)) }
}
finally {
  if ($srv -and -not $srv.HasExited) { & taskkill /F /T /PID $srv.Id *> $null }
}

$sz = (Get-Item $OutPng).Length
if ($sz -lt 10000) { Die "output PNG too small ($sz bytes)" }
$envf = Join-Path $RepoRoot "secrets\factory.env"
function GetEnv ($n) { $m = Select-String -Path $envf -Pattern "^$n=" | Select-Object -First 1; if ($m) { return ($m.Line -replace "^$n=", "").Trim() } return "" }
$SUPA = GetEnv "SUPABASE_URL"; $KEY = GetEnv "SUPABASE_SERVICE_KEY"; $pub = ""
if ($SUPA -and $KEY) {
  $dest = "gpu-samples/" + (Split-Path $OutPng -Leaf)
  try {
    Invoke-RestMethod -Method Put -Uri "$SUPA/storage/v1/object/factory-renders/$dest" -ContentType "image/png" `
      -Headers @{ Authorization = "Bearer $KEY"; apikey = $KEY; "x-upsert" = "true" } -Body ([IO.File]::ReadAllBytes($OutPng)) | Out-Null
    $pub = "$SUPA/storage/v1/object/public/factory-renders/$dest"
  } catch { Say ("upload failed: " + $_.Exception.Message) }
}
$sw.Stop()
$vram = ""; try { $vram = ((& nvidia-smi --query-gpu=memory.used --format=csv,noheader) -join "; ") } catch {}
Write-Host ("FLUX_OK RENDER_PATH=$OutPng bytes=$sz seed=$Seed elapsed_s=" + [int]$sw.Elapsed.TotalSeconds + " vram=$vram PUBLIC_URL=$pub")
exit 0
