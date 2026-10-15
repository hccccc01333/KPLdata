@echo off
rem Double-click from project root: start_monitor.bat
rem Do NOT run this file from Git Bash.
cd /d "%~dp0\.."
if not exist "data\realtime\logs" mkdir "data\realtime\logs"
title KPL-Monitor
echo [%date% %time%] launching run_monitor_loop.py
echo Pipeline: crawl 0.1s ^|^| predict async
echo Log file: data\realtime\logs\monitor_YYYYMMDD.log
python -u scripts\run_monitor_loop.py --interval 0.1 --interval-hot 0.1 --probes 1 --prestart-poll 20 %*
echo [%date% %time%] supervisor ended with errorlevel %ERRORLEVEL%
pause
