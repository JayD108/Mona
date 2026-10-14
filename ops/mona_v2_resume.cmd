@echo off
rem Resume MONA v2 (the 28-hour English-centric pretraining, then chat tuning on top).
rem Removes the hold, makes sure the power guard and watchdog are running, and starts the queue now.
rem Safe to run twice: every program exits at once if it is already running.
del "C:\LLM\runs\HOLD_V2" 2>nul
del "C:\LLM\runs\mona_v2\STOP" 2>nul
echo v2 > "C:\LLM\runs\ACTIVE_PLAN"
start "MONA power guard" /min powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File C:\LLM\ops\mona_power_guard.ps1
start "MONA watchdog" /min /d C:\LLM pythonw -u C:\LLM\ops\mona_watchdog.py
start "MONA v2 queue" /min /d C:\LLM pythonw -u -m scripts.mona_run_v2
echo MONA v2 resumed. Check progress with:  python -m scripts.mona_status mona_v2   (and runs\logs\mona_run_v2.log)
