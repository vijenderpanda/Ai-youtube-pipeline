# deploy/gpu/echomimic_v3_gen.ps1
# EchoMimicV3-Flash talking head: reference portrait + wav -> lip-synced mp4 at up
# to 768x768 in 8 steps (the 12GB-VRAM Flash path). Assumes echomimic_v3_setup.ps1
# has run. Prints EM3_GEN_OK RENDER_PATH + PUBLIC_URL (same contract as V1's script
# so avatar_render.py can switch tracks by script_path alone).
#
# worker: powershell.exe -NonInteractive -File <this> -RepoRoot <REPO>
#   -SrcUrl <portrait png/jpg> -AudioUrl <wav> [-Size 768] [-Steps 8] [-Fps 25] [-Tag em3]
param([string]$RepoRoot, [string]$SrcUrl, [string]$AudioUrl,
      [int]$Size = 512, [int]$Steps = 8, [int]$Fps = 25, [string]$Tag = "em3",
      [string]$MemMode = "model_cpu_offload_and_qfloat8")
# MemMode: this box has 16GB RAM — sequential_cpu_offload parks the ~11GB T5 in
# system RAM and froze the worker (2026-08-24). qfloat8 + model offload halves
# the transformer; 512² default cuts activations. 768 needs a RAM upgrade.
$ErrorActionPreference = "Continue"; $ProgressPreference = "SilentlyContinue"
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"

$Root = Join-Path $env:LOCALAPPDATA "echomimic_v3"
$Venv = Join-Path $Root "venv"; $Repo = Join-Path $Root "echomimic_v3"
$W = Join-Path $Root "weights"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
$env:HF_HOME = Join-Path $Root "hf-cache"
function Say ($m) { Write-Host ("[em3gen] " + $m) }
function Die ($m) { Write-Host ("EM3_GEN_FAIL " + $m); exit 1 }

if (-not $SrcUrl -or -not $AudioUrl) { Die "need -SrcUrl and -AudioUrl" }
if (-not (Test-Path $VenvPy)) { Die "no venv -- run echomimic_v3_setup.ps1 first" }
if (-not (Test-Path (Join-Path $Repo "infer_flash.py"))) { Die "no echomimic_v3 repo" }

$ff = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($ff) { $env:FFMPEG_PATH = Split-Path $ff.Source }
$ffprobe = (Get-Command ffprobe -ErrorAction SilentlyContinue).Source

$inp = Join-Path $Root "inputs"; New-Item -ItemType Directory -Force -Path $inp | Out-Null
$img = Join-Path $inp "ref.png"
$araw = Join-Path $inp "audio_src.bin"
$wav = Join-Path $inp "audio.wav"
try { Invoke-WebRequest -UseBasicParsing -Uri $SrcUrl -OutFile $img -TimeoutSec 90 | Out-Null } catch { Die ("image download failed: " + $_.Exception.Message) }
try { Invoke-WebRequest -UseBasicParsing -Uri $AudioUrl -OutFile $araw -TimeoutSec 90 | Out-Null } catch { Die ("audio download failed: " + $_.Exception.Message) }
& ffmpeg -y -v error -i $araw -ar 16000 -ac 1 $wav 2>&1 | Out-Host
if (-not (Test-Path $wav)) { Die "ffmpeg audio convert failed" }

# video_length = frames per window; cap by audio (81 = the tuned Flash window)
$dur = 4.0
if ($ffprobe) { try { $dur = [double](& $ffprobe -v error -show_entries format=duration -of csv=p=0 $wav) } catch {} }
$L = [int][math]::Ceiling($dur * $Fps) + 1
if ($L -lt 49) { $L = 49 }
if ($L -gt 113) { $L = 113 }   # tighter window on 16GB-RAM box   # ~6.4s per window cap on 12GB; longer audio -> model windows internally
Say ("audio=" + [math]::Round($dur, 2) + "s -> video_length=$L @ $Fps fps; ${Size}x${Size} steps=$Steps")

$outRoot = Join-Path $Root "outputs"
if (Test-Path $outRoot) { Get-ChildItem $outRoot -Recurse -Filter *.mp4 -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue }
New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
$sw = [System.Diagnostics.Stopwatch]::StartNew()

$imgF = ($img -replace '\\', '/'); $wavF = ($wav -replace '\\', '/')
$model = (Join-Path $W "Wan2.1-Fun-V1.1-1.3B-InP") -replace '\\', '/'
$tfp = (Join-Path $W "em3\echomimicv3-flash-pro\diffusion_pytorch_model.safetensors") -replace '\\', '/'
$w2v = (Join-Path $W "chinese-wav2vec2-base") -replace '\\', '/'
$outF = ($outRoot -replace '\\', '/')

Push-Location $Repo
Say "running EchoMimicV3-Flash (8-step)..."
& $VenvPy -u infer_flash.py `
  --image_path "$imgF" --audio_path "$wavF" --prompt "A person is speaking." `
  --num_inference_steps $Steps --config_path "config/config.yaml" `
  --model_name "$model" --ckpt_idx 50000 --transformer_path "$tfp" `
  --save_path "$outF" --wav2vec_model_dir "$w2v" --sampler_name "Flow_Unipc" `
  --video_length $L --guidance_scale 6.0 --audio_guidance_scale 3.0 --audio_scale 1.0 `
  --neg_scale 1.0 --neg_steps 0 --seed 43 --enable_teacache --teacache_threshold 0.1 `
  --num_skip_start_steps 5 --riflex_k 6 --ulysses_degree 1 --ring_degree 1 `
  --weight_dtype "bfloat16" --sample_size $Size $Size --fps $Fps `
  --GPU_memory_mode $MemMode --shift 5.0 2>&1 | Out-Host
  # (--add_prompt/--negative_prompt omitted: PowerShell drops empty-string args and argparse dies)
$rc = $LASTEXITCODE
Pop-Location
if ($rc -ne 0) { Die "infer_flash.py exited $rc" }

$mp4 = Get-ChildItem $outRoot -Recurse -Filter *.mp4 -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1
if (-not $mp4) { Die "no output mp4 under outputs/" }

$OutDir = Join-Path $RepoRoot "renders_out\gpu"; New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$OutMp4 = Join-Path $OutDir ("echomimic_v3_" + $Tag + "_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".mp4")
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
Write-Host ("EM3_GEN_OK RENDER_PATH=$OutMp4 bytes=$sz frames=$L elapsed_s=" + [int]$sw.Elapsed.TotalSeconds + " vram=$vram PUBLIC_URL=$pub")
exit 0
