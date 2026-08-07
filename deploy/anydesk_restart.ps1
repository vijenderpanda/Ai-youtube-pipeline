# deploy/anydesk_restart.ps1
# Kills any dead AnyDesk, restarts it, waits for online status, reports ID.
# Keeps it simple — no password config that could cause crashes.

param([string]$RepoRoot = $env:FACTORY_REPO)

# Find the exe
$candidates = @(
    "$env:TEMP\AnyDesk.exe",
    "$RepoRoot\renders_out\tools\anydesk\AnyDesk.exe",
    "C:\tools\anydesk\AnyDesk.exe"
)
$adExe = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $adExe) {
    Write-Host "[anydesk] Not found locally, downloading..."
    $adExe = "$env:TEMP\AnyDesk.exe"
    Invoke-WebRequest -Uri "https://download.anydesk.com/AnyDesk.exe" -OutFile $adExe -UseBasicParsing
}
Write-Host "[anydesk] Using exe: $adExe"

# Kill existing
Get-Process AnyDesk -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Start fresh
Start-Process -FilePath $adExe
Write-Host "[anydesk] Started, waiting 10s for server connection..."
Start-Sleep -Seconds 10

# Get ID
$id = $null
$confFiles = @(
    "$env:APPDATA\AnyDesk\system.conf",
    (Join-Path (Split-Path $adExe) "system.conf")
)
foreach ($cf in $confFiles) {
    if (Test-Path $cf) {
        $line = Get-Content $cf | Select-String "ad.anynet.id"
        if ($line) { $id = $line.ToString().Split("=",2)[1].Trim(); break }
    }
}
if (-not $id) {
    foreach ($rp in @("HKCU:\Software\AnyDesk","HKLM:\Software\AnyDesk")) {
        if (Test-Path $rp) {
            $v = (Get-ItemProperty $rp -ErrorAction SilentlyContinue).ad_id
            if ($v) { $id = $v; break }
        }
    }
}

$running = (Get-Process AnyDesk -ErrorAction SilentlyContinue) -ne $null

Write-Host ""
Write-Host "=============================================="
Write-Host "ANYDESK_ID: $id"
Write-Host "PROCESS_RUNNING: $running"
Write-Host ""
Write-Host "On your phone: open AnyDesk -> enter $id -> CONNECT"
Write-Host "You will see an Accept dialog on screen — tap Accept"
Write-Host "(or we set unattended after you're in)"
Write-Host "=============================================="
