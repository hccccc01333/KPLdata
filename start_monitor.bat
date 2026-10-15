@echo off
rem Run by double-click in Explorer, or: cmd /c start_monitor.bat
cd /d "%~dp0"
if not exist "%~dp0data\realtime\logs" mkdir "%~dp0data\realtime\logs"
start "KPL-Monitor" "%ComSpec%" /k "%~dp0scripts\launch_monitor.bat"
echo [OK] KPL monitor started in a new window.
echo      Pipeline: crawl 0.1s ^|^| predict async
echo      Log: data\realtime\logs\monitor_YYYYMMDD.log
echo      Close that window to stop, or run stop_monitor.bat
