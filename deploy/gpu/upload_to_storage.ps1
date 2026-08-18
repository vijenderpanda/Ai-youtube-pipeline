# deploy/gpu/upload_to_storage.ps1
# Upload a local file (e.g. a GPU render on the Windows box) to the public
# factory-renders Supabase bucket and print its public URL, so results produced on
# the worker can be pulled to the Mac / dashboard. Creds are read from
# secrets\factory.env (relative to -RepoRoot). Prints UPLOAD_OK PUBLIC_URL=... or
# UPLOAD_FAIL <why>.
#
# worker: powershell.exe -NonInteractive -File <this> -RepoRoot <REPO> -FilePath <path> [-Dest <bucket/path>]
param([string]$RepoRoot, [string]$FilePath, [string]$Dest = "")
$ErrorActionPreference = "Continue"
function Die ($m) { Write-Host ("UPLOAD_FAIL " + $m); exit 1 }

$envf = Join-Path $RepoRoot "secrets\factory.env"
if (-not (Test-Path $envf)) { Die "no secrets\factory.env at $envf" }
function GetEnv ($n) {
  $m = Select-String -Path $envf -Pattern "^$n=" | Select-Object -First 1
  if ($m) { return ($m.Line -replace "^$n=", "").Trim() }
  return ""
}
$SUPA = GetEnv "SUPABASE_URL"
$KEY  = GetEnv "SUPABASE_SERVICE_KEY"
if (-not $SUPA -or -not $KEY) { Die "missing SUPABASE_URL / SUPABASE_SERVICE_KEY" }
if (-not (Test-Path $FilePath)) { Die "file not found: $FilePath" }
if (-not $Dest) { $Dest = "gpu-samples/" + (Split-Path $FilePath -Leaf) }

$ct = "application/octet-stream"
if ($FilePath -match '\.wav$') { $ct = "audio/wav" }
elseif ($FilePath -match '\.mp4$') { $ct = "video/mp4" }
elseif ($FilePath -match '\.png$') { $ct = "image/png" }

$uri = "$SUPA/storage/v1/object/factory-renders/$Dest"
try {
  $bytes = [IO.File]::ReadAllBytes($FilePath)
  Invoke-RestMethod -Method Put -Uri $uri -ContentType $ct `
    -Headers @{ Authorization = "Bearer $KEY"; apikey = $KEY; "x-upsert" = "true" } `
    -Body $bytes | Out-Null
  Write-Host ("UPLOAD_OK bytes=" + $bytes.Length + " PUBLIC_URL=$SUPA/storage/v1/object/public/factory-renders/$Dest")
} catch {
  Die ("PUT failed: " + $_.Exception.Message)
}
exit 0
