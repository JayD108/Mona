# Freeze or unfreeze MONA's training processes in place (no progress lost).
# Usage: mona_pause_resume.ps1 suspend|resume      (adapted from APALA's pause_resume.ps1)
param([string]$mode)
Add-Type -TypeDefinition @"
using System; using System.Runtime.InteropServices;
public static class MonaPx {
  [DllImport("ntdll.dll")] public static extern int NtSuspendProcess(IntPtr h);
  [DllImport("ntdll.dll")] public static extern int NtResumeProcess(IntPtr h);
  [DllImport("kernel32.dll")] public static extern IntPtr OpenProcess(int a, bool b, int pid);
  [DllImport("kernel32.dll")] public static extern bool CloseHandle(IntPtr h);
}
"@
$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" | Where-Object { $_.CommandLine -match "scripts\.mona_(run_all|pretrain|sft|eval)|pipeline\.mona_build_sft" }
foreach ($p in $procs) {
  $h = [MonaPx]::OpenProcess(0x0800, $false, [int]$p.ProcessId)
  if ($h -ne [IntPtr]::Zero) {
    # resume 16x: releases every suspend count (APALA lesson: a process frozen twice needs two resumes)
    if ($mode -eq "suspend") { [void][MonaPx]::NtSuspendProcess($h) } else { for ($i = 0; $i -lt 16; $i++) { [void][MonaPx]::NtResumeProcess($h) } }
    [void][MonaPx]::CloseHandle($h)
  }
  "$mode $($p.ProcessId)"
}
