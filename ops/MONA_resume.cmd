@echo off
rem MONA auto-resume (copy of this file sits in the Windows Startup folder; delete that copy to disable).
rem Starts the power guard and the watchdog; the watchdog starts/resumes training. Both exit at once if
rem already running, so running this twice is harmless.
start "MONA power guard" /min powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File C:\LLM\ops\mona_power_guard.ps1
start "MONA watchdog" /min /d C:\LLM pythonw -u C:\LLM\ops\mona_watchdog.py
