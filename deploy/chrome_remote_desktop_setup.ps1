# deploy/chrome_remote_desktop_setup.ps1
# Sets up Chrome Remote Desktop host on this machine using the already-logged-in
# Chrome profile (vijender.in@gmail.com). No admin needed, no card, completely free.
# After this runs, connect from https://remotedesktop.google.com on any device.

param([string]$RepoRoot = $env:FACTORY_REPO)
if (-not $RepoRoot) { $RepoRoot = Split-Path $PSScriptRoot -Parent }

Write-Host "[crd] Starting Chrome Remote Desktop host setup"

# ── 1. Check if CRD host is already installed ─────────────────────────────────
$crdService = Get-Service -Name "chromoting" -ErrorAction SilentlyContinue
if ($crdService) {
    Write-Host "[crd] Chrome Remote Desktop host already installed (service: $($crdService.Status))"
    if ($crdService.Status -ne "Running") {
        Start-Service chromoting -ErrorAction SilentlyContinue
        Write-Host "[crd] Started chromoting service"
    }
    Write-Host ""
    Write-Host "=============================================="
    Write-Host "CRD already set up. Connect at:"
    Write-Host "https://remotedesktop.google.com/access"
    Write-Host "Sign in as: vijender.in@gmail.com"
    Write-Host "=============================================="
    exit 0
}

# ── 2. Download Chrome Remote Desktop host MSI ────────────────────────────────
$msiUrl  = "https://dl.google.com/chrome-remote-desktop/chromeremotedesktophost.msi"
$msiPath = "$env:TEMP\chromeremotedesktophost.msi"
Write-Host "[crd] Downloading CRD host from $msiUrl ..."
try {
    Invoke-WebRequest -Uri $msiUrl -OutFile $msiPath -UseBasicParsing
    Write-Host "[crd] Downloaded to $msiPath"
} catch {
    Write-Error "[crd] Download failed: $_"; exit 1
}

# ── 3. Install silently (no admin prompt needed for per-user install) ──────────
Write-Host "[crd] Installing CRD host (silent)..."
$proc = Start-Process msiexec.exe -ArgumentList "/i `"$msiPath`" /quiet /norestart" -Wait -PassThru
Write-Host "[crd] msiexec exit code: $($proc.ExitCode)"
if ($proc.ExitCode -notin @(0, 3010)) {
    Write-Error "[crd] Install failed with exit code $($proc.ExitCode)"; exit 1
}

# ── 4. Verify service created ─────────────────────────────────────────────────
Start-Sleep -Seconds 3
$svc = Get-Service -Name "chromoting" -ErrorAction SilentlyContinue
if ($svc) {
    Write-Host "[crd] chromoting service: $($svc.Status)"
} else {
    Write-Host "[crd] WARNING: chromoting service not found after install — may need Chrome sign-in step"
}

# ── 5. Report ─────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=============================================="
Write-Host "ACTION REQUIRED (one-time, in Chrome on this machine):"
Write-Host "1. Open Chrome -> https://remotedesktop.google.com/access"
Write-Host "2. Sign in as vijender.in@gmail.com (already logged in)"
Write-Host "3. Click 'Set up remote access' and set a PIN"
Write-Host "4. This machine will then appear in your device list"
Write-Host ""
Write-Host "After that, connect from ANY device at:"
Write-Host "https://remotedesktop.google.com/access"
Write-Host "No ngrok, no card, no admin needed."
Write-Host "=============================================="
