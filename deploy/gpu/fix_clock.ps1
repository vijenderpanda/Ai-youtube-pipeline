# fix_clock.ps1 — resync the worker's system clock (NTP).
# WHY THIS EXISTS: after the 2026-08-24 reboot the box came up ~42 min behind.
# factory_worker.py stamps heartbeat_at with the LOCAL clock (now_iso), and the
# reaper kills 'running' jobs whose heartbeat looks >180s stale — so a skewed
# clock makes every job longer than one reaper sweep die as an orphan while
# short jobs slip through. Resync fixes the fleet-wide symptom at its source.
# Runs fast (<30s) so it completes before the reaper can touch it.
$ErrorActionPreference = "Continue"

Write-Output "LOCAL_BEFORE=$((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))"

# ensure the time service is up, then force a resync
Start-Service w32time -ErrorAction SilentlyContinue
w32tm /resync /force 2>&1 | ForEach-Object { Write-Output "W32TM: $_" }

# if w32tm couldn't fix it (no admin / service issues), fall back to setting the
# clock directly from an HTTP Date header (good to ~1s, plenty for a 180s reaper).
$after = (Get-Date).ToUniversalTime()
try {
    $resp = Invoke-WebRequest -Uri "https://www.google.com/generate_204" -Method Head -UseBasicParsing -TimeoutSec 15
    $netUtc = ([DateTime]::Parse($resp.Headers["Date"])).ToUniversalTime()
    $skew = [Math]::Abs(($netUtc - $after).TotalSeconds)
    Write-Output "SKEW_AFTER_W32TM=${skew}s"
    if ($skew -gt 60) {
        Set-Date -Date $netUtc.ToLocalTime() 2>&1 | Out-Null
        Write-Output "FALLBACK_SET_DATE applied from HTTP Date header"
    }
} catch {
    Write-Output "HTTP_TIME_CHECK_FAILED: $($_.Exception.Message)"
}

Write-Output "LOCAL_AFTER=$((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))"
w32tm /query /status 2>&1 | Select-Object -First 8 | ForEach-Object { Write-Output "STATUS: $_" }
