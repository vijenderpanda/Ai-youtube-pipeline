# deploy/anydesk_unattended.ps1
# Confirms AnyDesk is running and enables unattended access (no Accept dialog needed).
# AnyDesk ID from previous job: 542345771

param([string]$RepoRoot = $env:FACTORY_REPO)

$adExe = "$env:TEMP\AnyDesk.exe"
if (-not (Test-Path $adExe)) {
    # Try renders_out location from previous job
    $adExe = "$RepoRoot\renders_out\tools\anydesk\AnyDesk.exe"
}

# ── 1. Confirm AnyDesk process is running ────────────────────────────────────
$proc = Get-Process AnyDesk -ErrorAction SilentlyContinue
if (-not $proc) {
    Write-Host "[anydesk] Not running — restarting..."
    if (Test-Path $adExe) {
        Start-Process -FilePath $adExe
        Start-Sleep -Seconds 5
        $proc = Get-Process AnyDesk -ErrorAction SilentlyContinue
    }
}
Write-Host "[anydesk] Process: $(if ($proc) { "RUNNING (PID $($proc.Id))" } else { "NOT FOUND" })"

# ── 2. Read current ID ────────────────────────────────────────────────────────
$id = $null
$cfgPaths = @(
    "$env:APPDATA\AnyDesk\system.conf",
    "$env:ProgramData\AnyDesk\system.conf",
    (Join-Path (Split-Path $adExe) "system.conf")
)
foreach ($cp in $cfgPaths) {
    if (Test-Path $cp) {
        $line = Get-Content $cp -ErrorAction SilentlyContinue | Select-String "ad.anynet.id"
        if ($line) { $id = $line.ToString().Split("=",2)[1].Trim(); break }
    }
}
# Registry fallback
if (-not $id) {
    foreach ($rp in @("HKCU:\Software\AnyDesk","HKLM:\Software\AnyDesk")) {
        if (Test-Path $rp) {
            $val = (Get-ItemProperty $rp -ErrorAction SilentlyContinue).ad_id
            if ($val) { $id = $val; break }
        }
    }
}
Write-Host "[anydesk] ID: $(if ($id) { $id } else { 'not found' })"

# ── 3. Set unattended access password via config file ─────────────────────────
# AnyDesk stores the unattended password hash in user.conf; easier path is to
# write the security.unattended_access setting so next connect auto-accepts.
$cfgDir = "$env:APPDATA\AnyDesk"
$userConf = "$cfgDir\user.conf"
if (-not (Test-Path $cfgDir)) { New-Item -ItemType Directory -Path $cfgDir -Force | Out-Null }

# Password to use for unattended access
$pwd = "Factory2026!"

# Set via AnyDesk CLI (most reliable method)
$set = $false
if (Test-Path $adExe) {
    try {
        # AnyDesk --set-password reads from stdin
        $proc2 = Start-Process -FilePath $adExe -ArgumentList "--set-password" `
            -RedirectStandardInput "$env:TEMP\adpwd.txt" -Wait -PassThru -WindowStyle Hidden
        # Write password to temp file first
        Set-Content "$env:TEMP\adpwd.txt" $pwd -NoNewline
        $proc2 = Start-Process -FilePath $adExe -ArgumentList "--set-password" `
            -RedirectStandardInput "$env:TEMP\adpwd.txt" -Wait -PassThru -WindowStyle Hidden
        Write-Host "[anydesk] --set-password exit: $($proc2.ExitCode)"
        if ($proc2.ExitCode -eq 0) { $set = $true }
    } catch { Write-Host "[anydesk] CLI set-password error: $_" }
    Remove-Item "$env:TEMP\adpwd.txt" -ErrorAction SilentlyContinue
}

# Fallback: write to user.conf directly
if (-not $set) {
    Write-Host "[anydesk] Writing security config to user.conf..."
    $confContent = @"
ad.security.unattended_access=true
ad.security.interactive_access=2
"@
    if (Test-Path $userConf) {
        # Update existing keys rather than overwriting
        $existing = Get-Content $userConf
        $existing = $existing | Where-Object { $_ -notmatch "^ad.security.unattended_access|^ad.security.interactive_access" }
        $existing += "ad.security.unattended_access=true"
        $existing += "ad.security.interactive_access=2"
        Set-Content $userConf ($existing -join "`n")
    } else {
        Set-Content $userConf $confContent
    }
    Write-Host "[anydesk] user.conf updated"
    # Restart AnyDesk to pick up config
    Get-Process AnyDesk -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 2
    Start-Process -FilePath $adExe
    Start-Sleep -Seconds 5
}

# ── 4. Final report ───────────────────────────────────────────────────────────
$finalId = $id
Write-Host ""
Write-Host "=============================================="
Write-Host "ANYDESK_ID: $finalId"
Write-Host "UNATTENDED_PASSWORD: $pwd"
Write-Host ""
Write-Host "Connect steps:"
Write-Host "1. Download AnyDesk: https://anydesk.com/download"
Write-Host "2. Enter ID: $finalId"
Write-Host "3. When asked for password enter: $pwd"
Write-Host "   (if prompted on screen just accept)"
Write-Host "4. Open Chrome -> remotedesktop.google.com/access"
Write-Host "5. Set PIN -> Chrome Remote Desktop is live"
Write-Host "6. Close AnyDesk after CRD is set up"
Write-Host "=============================================="
