# deploy/worker_pip.ps1
# Install python packages into the WORKER's own interpreter (the one running
# factory_worker.py) — used to add optional deps like psutil that the auto-upgrade
# (git pull + restart, no pip) doesn't install. Idempotent (pip skips satisfied).
#
# worker: powershell.exe -NonInteractive -File <this> -RepoRoot <REPO> [-Packages "psutil"]
param([string]$RepoRoot, [string]$Packages = "psutil")
$ErrorActionPreference = "Continue"
$py = Get-Command python -ErrorAction SilentlyContinue
$base = @()
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue; $base = @("-3") }
if (-not $py) { Write-Host "PIP_FAIL no python on PATH"; exit 1 }
$pkgs = $Packages -split '\s+' | Where-Object { $_ }
Write-Host "installing [$($pkgs -join ', ')] into $($py.Source)"
& $py.Source @base -m pip install @pkgs 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) { Write-Host "PIP_FAIL pip exit $LASTEXITCODE"; exit 1 }
& $py.Source @base -c "import psutil, sys; print('PSUTIL_OK', psutil.__version__)" 2>&1 | Out-Host
Write-Host "PIP_OK"
exit 0
