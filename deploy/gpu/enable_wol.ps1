# Prepare DESKTOP-DEIR7RS to be woken remotely. Run this while the box is AWAKE.
# Pure ASCII on purpose - PS 5.1 chokes on smart quotes and dashes.
param([string]$RepoRoot = "")

Write-Output "=== NETWORK ADAPTERS ==="
$nics = Get-NetAdapter -Physical | Where-Object { $_.Status -eq 'Up' }
foreach ($n in $nics) {
  Write-Output ("{0}  mac={1}  link={2}" -f $n.Name, $n.MacAddress, $n.LinkSpeed)
}
if (-not $nics) { Write-Output "no adapter is up"; exit 1 }

Write-Output ""
Write-Output "=== ENABLING WAKE ON MAGIC PACKET ==="
foreach ($n in $nics) {
  try {
    Set-NetAdapterPowerManagement -Name $n.Name -WakeOnMagicPacket Enabled -WakeOnPattern Disabled -ErrorAction Stop
    Write-Output ("  {0}: magic packet enabled" -f $n.Name)
  } catch {
    Write-Output ("  {0}: power-management set failed - {1}" -f $n.Name, $_.Exception.Message)
  }
  try {
    Set-NetAdapterAdvancedProperty -Name $n.Name -DisplayName "Wake on Magic Packet" -DisplayValue "Enabled" -ErrorAction Stop
    Write-Output ("  {0}: driver property enabled" -f $n.Name)
  } catch { }
}

Write-Output ""
Write-Output "=== FAST STARTUP ==="
# Windows Fast Startup puts the box in a hybrid-hibernate the NIC cannot wake
# from, so WoL after a normal shutdown silently never works while it is on.
$key = "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Power"
try {
  Set-ItemProperty -Path $key -Name HiberbootEnabled -Value 0 -ErrorAction Stop
  Write-Output "  fast startup disabled (WoL now works from a full shutdown)"
} catch {
  Write-Output "  could not disable fast startup - needs an elevated session"
  Write-Output "  run as admin: powercfg /hibernate off"
}

Write-Output ""
Write-Output "=== WHAT IS ARMED TO WAKE THIS PC ==="
powercfg -devicequery wake_armed

Write-Output ""
Write-Output "=== STILL TO DO IN THE BIOS (no script can set these) ==="
Write-Output "  1. Restore on AC Power Loss = Power On   <- THE fix for outages."
Write-Output "     Named 'AC BACK', 'After Power Failure' or 'Restore on AC/Power Loss'."
Write-Output "     With this set the PC boots itself the moment mains returns."
Write-Output "  2. Wake on LAN / PCIe Power On = Enabled  <- lets the wake button work"
Write-Output "     after a normal shutdown, as long as the PSU still has standby power."
Write-Output ""
Write-Output "Copy the mac= value above into the app so the wake button can target it."
