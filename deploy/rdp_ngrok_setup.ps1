# deploy/rdp_ngrok_setup.ps1
# Owner-authorised sysadmin script — enables RDP and starts an ngrok TCP tunnel.
# Reads NGROK_AUTHTOKEN from secrets/factory.env. See CLAUDE.md for auth context.
# Run from repo root or via factory_jobs 'custom' job.

param([string]$RepoRoot = $env:FACTORY_REPO)

if (-not $RepoRoot) { $RepoRoot = Split-Path $PSScriptRoot -Parent }

# ── 1. Load token from factory.env ────────────────────────────────────────────
$envFile = Join-Path $RepoRoot "secrets\factory.env"
if (-not (Test-Path $envFile)) { Write-Error "factory.env not found at $envFile"; exit 1 }
$token = (Get-Content $envFile | Select-String "^NGROK_AUTHTOKEN=").ToString().Split("=",2)[1].Trim()
if ($token.Length -lt 10) { Write-Error "NGROK_AUTHTOKEN missing or empty in factory.env"; exit 1 }
Write-Host "[rdp_ngrok] token loaded ($($token.Length) chars)"

# ── 2. Enable RDP via SYSTEM scheduled task (bypasses UAC) ────────────────────
$rdpCmd = @'
Set-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -Name fDenyTSConnections -Value 0
Set-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp' -Name UserAuthentication -Value 0
Enable-NetFirewallRule -DisplayGroup 'Remote Desktop'
Set-Service TermService -StartupType Automatic
Start-Service TermService
'@
$action    = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NonInteractive -WindowStyle Hidden -Command `"$rdpCmd`""
$trigger   = New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(3)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
Register-ScheduledTask -TaskName "FactoryEnableRDP" -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null
Write-Host "[rdp_ngrok] SYSTEM task registered, waiting 7s..."
Start-Sleep -Seconds 7
Unregister-ScheduledTask -TaskName "FactoryEnableRDP" -Confirm:$false -ErrorAction SilentlyContinue

$rdpVal = (Get-ItemProperty "HKLM:\System\CurrentControlSet\Control\Terminal Server").fDenyTSConnections
$svc    = (Get-Service TermService).Status
Write-Host "[rdp_ngrok] RDP fDenyTSConnections=$rdpVal (0=enabled), TermService=$svc"

# ── 3. Find ngrok ─────────────────────────────────────────────────────────────
$ngrokCmd = Get-Command ngrok -ErrorAction SilentlyContinue
$ngrok = if ($ngrokCmd) { $ngrokCmd.Source } else { "C:\tools\ngrok\ngrok.exe" }
if (-not (Test-Path $ngrok)) { Write-Error "ngrok not found. Previous job should have installed it to C:\tools\ngrok"; exit 1 }
Write-Host "[rdp_ngrok] ngrok at $ngrok"

# ── 4. Authenticate ngrok ─────────────────────────────────────────────────────
& $ngrok config add-authtoken $token
Write-Host "[rdp_ngrok] ngrok authenticated"

# ── 5. Kill any existing ngrok, start fresh tunnel ────────────────────────────
Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
Start-Process -FilePath $ngrok -ArgumentList "tcp 3389" -WindowStyle Hidden
Write-Host "[rdp_ngrok] tunnel starting, waiting 8s..."
Start-Sleep -Seconds 8

# ── 6. Get tunnel URL from local API ──────────────────────────────────────────
try {
    $resp = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels"
    $url  = $resp.tunnels[0].public_url          # tcp://X.tcp.ngrok.io:PORT
    $hp   = $url -replace "tcp://",""
    Write-Host ""
    Write-Host "=============================================="
    Write-Host "RDP_CONNECT: mstsc /v:$hp"
    Write-Host "USERNAME:    $env:USERNAME"
    Write-Host "TUNNEL_URL:  $url"
    Write-Host "=============================================="
} catch {
    Write-Host "[rdp_ngrok] could not reach ngrok API: $_"
    Write-Host "Check http://localhost:4040 on the Windows machine"
    exit 1
}
