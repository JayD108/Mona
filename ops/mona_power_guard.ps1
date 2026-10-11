# MONA power guard (single instance, started at log-in by MONA_resume.cmd). Adapted from APALA's guard.
# Training runs only when BOTH:
#   1) the laptop is on AC power        -> on battery, training is frozen at once
#   2) it is not an adapter-rest break  -> every 6 h of running, a 20 min break lets the charger cool down
# Processes are suspended in place (NtSuspendProcess), so no progress is lost.
# Log: C:\LLM\runs\logs\mona_power_guard.log
Add-Type -AssemblyName System.Windows.Forms
$RunSec = 6 * 3600; $BreakSec = 20 * 60; $PollSec = 5
$Ops = "C:\LLM\ops"
$Log = "C:\LLM\runs\logs\mona_power_guard.log"
$Lock = "$Ops\mona_power_guard.lock"
New-Item -ItemType Directory -Force (Split-Path $Log) | Out-Null
if (Test-Path $Lock) {
  $old = Get-Content $Lock -ErrorAction SilentlyContinue
  if ($old -and (Get-Process -Id ([int]$old) -ErrorAction SilentlyContinue)) { exit 0 }
}
Set-Content $Lock $PID
function Log($m) { Add-Content $Log ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $m) }
function OnAC { [System.Windows.Forms.SystemInformation]::PowerStatus.PowerLineStatus -eq "Online" }
function Charge { [int]([System.Windows.Forms.SystemInformation]::PowerStatus.BatteryLifePercent * 100) }
function Freeze { & powershell -NoProfile -ExecutionPolicy Bypass -File "$Ops\mona_pause_resume.ps1" suspend | Out-Null }
function Thaw   { & powershell -NoProfile -ExecutionPolicy Bypass -File "$Ops\mona_pause_resume.ps1" resume  | Out-Null }

$frozen = $false
$runSince = Get-Date
$ranSec = 0
$breakUntil = $null
Log "power guard started (pid $PID): adapter break $($BreakSec/60) min every $($RunSec/3600) h of running; AC: $(OnAC), battery $(Charge)%"
while ($true) {
  $now = Get-Date
  $ac = OnAC
  if ($breakUntil -and $now -ge $breakUntil) { $breakUntil = $null; $ranSec = 0; Log "adapter break over" }
  if (-not $frozen) { $ranSec += ($now - $runSince).TotalSeconds }
  $runSince = $now
  if (-not $frozen -and -not $breakUntil -and $ranSec -ge $RunSec) {
    $breakUntil = $now.AddSeconds($BreakSec)
    Log "adapter break: training frozen for $($BreakSec/60) min (after $([int]($ranSec/60)) min of running)"
  }
  $shouldRun = $ac -and -not $breakUntil
  if (-not $shouldRun -and -not $frozen) {
    Freeze; $frozen = $true
    if (-not $ac) { Log "AC power lost (battery $(Charge)%) -> training frozen" }
  } elseif ($shouldRun -and $frozen) {
    Thaw; $frozen = $false
    Log "training resumed (AC power, battery $(Charge)%)"
  }
  Start-Sleep -Seconds $PollSec
}
