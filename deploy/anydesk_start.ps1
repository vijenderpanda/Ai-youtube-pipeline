# deploy/anydesk_start.ps1
# Downloads AnyDesk portable (no install, no admin) and starts it.
# Reports the AnyDesk ID so the owner can connect for the one-time CRD PIN setup.

param([string]$RepoRoot = $env:FACTORY_REPO)

$adExe = "$env:TEMP\AnyDesk.exe"

# ── 1. Download if not already present ────────────────────────────────────────
if (-not (Test-Path $adExe)) {
    Write-Host "[anydesk] Downloading AnyDesk portable..."
    try {
        Invoke-WebRequest -Uri "https://download.anydesk.com/AnyDesk.exe" `
            -OutFile $adExe -UseBasicParsing
        Write-Host "[anydesk] Downloaded to $adExe"
    } catch {
        Write-Error "[anydesk] Download failed: $_"; exit 1
    }
} else {
    Write-Host "[anydesk] AnyDesk already at $adExe"
}

# ── 2. Kill any existing AnyDesk instance ─────────────────────────────────────
Get-Process AnyDesk -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# ── 3. Start AnyDesk ──────────────────────────────────────────────────────────
Write-Host "[anydesk] Starting AnyDesk..."
Start-Process -FilePath $adExe
Start-Sleep -Seconds 6

# ── 4. Read AnyDesk ID from registry ──────────────────────────────────────────
$id = $null

# Try registry (populated after first run)
$regPaths = @(
    "HKCU:\Software\AnyDesk",
    "HKLM:\Software\AnyDesk",
    "HKLM:\Software\WOW6432Node\AnyDesk"
)
foreach ($rp in $regPaths) {
    if (Test-Path $rp) {
        $val = (Get-ItemProperty $rp -ErrorAction SilentlyContinue).ad_id
        if ($val) { $id = $val; break }
    }
}

# Try config file fallback
if (-not $id) {
    $cfgPaths = @(
        "$env:APPDATA\AnyDesk\system.conf",
        "$env:ProgramData\AnyDesk\system.conf"
    )
    foreach ($cp in $cfgPaths) {
        if (Test-Path $cp) {
            $line = Get-Content $cp | Select-String "ad.anynet.id"
            if ($line) {
                $id = $line.ToString().Split("=",2)[1].Trim()
                break
            }
        }
    }
}

# ── 5. Report ─────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=============================================="
if ($id) {
    Write-Host "ANYDESK_ID: $id"
    Write-Host ""
    Write-Host "Connect steps:"
    Write-Host "1. Download AnyDesk on your Mac/phone: https://anydesk.com/download"
    Write-Host "2. Enter ID: $id"
    Write-Host "3. When prompted for password — AnyDesk will show an Accept dialog"
    Write-Host "   on this machine (auto-accepted after 30s if unattended mode on)"
    Write-Host "4. Complete Chrome Remote Desktop PIN setup in Chrome"
    Write-Host "5. After CRD PIN is set, you can close AnyDesk"
} else {
    Write-Host "ANYDESK_ID: not found yet — AnyDesk may still be initialising"
    Write-Host "Wait 30s and check http://localhost:port or look for AnyDesk in system tray"
    Write-Host "The process is running; ID will appear in HKCU:\Software\AnyDesk reg key"
}
Write-Host "=============================================="
