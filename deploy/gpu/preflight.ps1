# deploy/gpu/preflight.ps1
# Fast, READ-ONLY probe of the Windows GPU worker (DESKTOP-DEIR7RS) so the real
# GPT-SoVITS install script can be written to land first-try instead of burning
# 20-minute install cycles. Installs nothing. Always reaches PREFLIGHT_OK so the
# job succeeds and its full report is captured in result.script_output.
#
# Run by the worker as: powershell.exe -NonInteractive -File <this> -RepoRoot <REPO>
param([string]$RepoRoot)
$ErrorActionPreference = "Continue"

function kv($k, $v) { Write-Host ("{0,-18}: {1}" -f $k, $v) }

Write-Host "=== FACTORY GPU PREFLIGHT ==="
kv "host"          $env:COMPUTERNAME
kv "user"          $env:USERNAME
kv "repo_root"     $RepoRoot
kv "localappdata"  $env:LOCALAPPDATA
try { kv "os" ((Get-CimInstance Win32_OperatingSystem).Caption) } catch {}

Write-Host "--- python ---"
try { kv "python" (& python --version 2>&1) } catch { kv "python" "NOT FOUND" }
try { kv "python_where" ((Get-Command python -ErrorAction Stop).Source) } catch {}
# py launcher: -0p lists every installed version + its exe path (what venv creation needs)
try { kv "py_launcher_versions" (((& py -0p 2>&1) | Out-String).Trim() -replace "\r?\n", " | ") }
catch { kv "py_launcher_versions" "py launcher NOT FOUND" }

Write-Host "--- tools ---"
foreach ($t in @("git", "ffmpeg", "ffprobe", "7z", "conda", "nvidia-smi", "curl")) {
  $c = Get-Command $t -ErrorAction SilentlyContinue
  kv "tool[$t]" $(if ($c) { $c.Source } else { "NOT FOUND" })
}

Write-Host "--- gpu / vram ---"
try {
  $smi = (& nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version --format=csv,noheader 2>&1 | Out-String).Trim()
  kv "gpu" $smi
} catch { kv "gpu" "nvidia-smi FAILED" }

Write-Host "--- disk ---"
try { kv "disk_C_free_GB" ([math]::Round((Get-PSDrive C).Free / 1GB, 1)) } catch {}
try {
  $q = (Split-Path $env:LOCALAPPDATA -Qualifier).TrimEnd(":")
  kv "cache_drive_free_GB" ([math]::Round((Get-PSDrive $q).Free / 1GB, 1))
} catch {}

Write-Host "--- network reachability ---"
foreach ($u in @("https://github.com", "https://huggingface.co", "https://download.pytorch.org")) {
  try {
    $r = Invoke-WebRequest -Uri $u -Method Head -TimeoutSec 15 -UseBasicParsing
    kv "net[$u]" ("OK http " + $r.StatusCode)
  } catch { kv "net[$u]" ("FAIL " + $_.Exception.Message) }
}

Write-Host "--- gpu-cache state ---"
kv "C:\gpu-cache exists" (Test-Path "C:\gpu-cache")
kv "localgen cache exists" (Test-Path (Join-Path $env:LOCALAPPDATA "factory-localgen"))

Write-Host ("PREFLIGHT_OK host={0} at={1}" -f $env:COMPUTERNAME, (Get-Date -Format o))
exit 0
