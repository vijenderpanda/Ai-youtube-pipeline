# deploy/setup_factory_chrome.ps1
# 1. Installs watchdog (permanent worker auto-restart)
# 2. Installs Chrome Remote Desktop host
# 3. Creates a dedicated "Factory" Chrome profile and opens it for owner sign-in
# Run while owner has AnyDesk access.

param([string]$RepoRoot = $env:FACTORY_REPO)
if (-not $RepoRoot) { $RepoRoot = Split-Path $PSScriptRoot -Parent }

# ── 1. Restart worker first (it was dead) ────────────────────────────────────
Write-Host "[setup] Restarting worker..."
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "deploy\worker-ctl.ps1") restart
Start-Sleep -Seconds 3

# ── 2. Set up watchdog ────────────────────────────────────────────────────────
Write-Host "[setup] Installing watchdog..."
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "deploy\setup_watchdog.ps1") -RepoRoot $RepoRoot
Start-Sleep -Seconds 2

# ── 3. Install Chrome Remote Desktop host ────────────────────────────────────
Write-Host "[setup] Installing CRD host..."
$crdSvc = Get-Service chromoting -ErrorAction SilentlyContinue
if (-not $crdSvc) {
    $msi = "$env:TEMP\chromeremotedesktophost.msi"
    Invoke-WebRequest "https://dl.google.com/chrome-remote-desktop/chromeremotedesktophost.msi" -OutFile $msi -UseBasicParsing
    Start-Process msiexec.exe -ArgumentList "/i `"$msi`" /quiet /norestart" -Wait
    Write-Host "[setup] CRD host installed"
} else {
    Write-Host "[setup] CRD host already installed ($($crdSvc.Status))"
}

# ── 4. Create dedicated Factory Chrome profile ────────────────────────────────
$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chrome)) {
    $chrome = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
}

# Profile lives in a predictable path the MCP config can reference
$profileDir = "$env:LOCALAPPDATA\Google\Chrome\User Data"
$profileName = "Factory"

Write-Host "[setup] Opening Chrome with Factory profile..."
# Open Chrome with the Factory profile — owner signs in via AnyDesk
$chromeArgs = @("--profile-directory=$profileName", "--no-first-run", "https://accounts.google.com/signin")
Start-Process -FilePath $chrome -ArgumentList $chromeArgs

Start-Sleep -Seconds 4

# ── 5. Report ─────────────────────────────────────────────────────────────────
$profilePath = Join-Path $profileDir $profileName
Write-Host ""
Write-Host "=============================================="
Write-Host "WORKER: restarted"
Write-Host "WATCHDOG: installed (auto-restarts every 2min)"
Write-Host "CRD: installed"
Write-Host ""
Write-Host "Chrome is open with the 'Factory' profile."
Write-Host "Via AnyDesk — do these steps NOW:"
Write-Host "  1. Sign into Google (vijender.in@gmail.com)"
Write-Host "  2. Go to remotedesktop.google.com/access -> Set up -> set PIN"
Write-Host "  3. Go to app.leonardo.ai -> Sign in with Google"
Write-Host "  4. Go to suno.com -> Sign in with Google"
Write-Host "  5. Install Claude Code extension in this Chrome profile:"
Write-Host "     chrome://extensions -> get from Claude Code app"
Write-Host ""
Write-Host "CHROME_PROFILE_PATH: $profilePath"
Write-Host "=============================================="
