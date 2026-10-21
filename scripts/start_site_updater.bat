@echo off
rem 网站数据自动更新（两个循环）：
rem   1) watch_site_data.py  监视数据变化 → 重建网站数据（60s 检查）
rem   2) build_live_data.py  实时比分/胜率/预测 → assets/live.js（30s 刷新）
rem 双击运行；关闭窗口即停止。
cd /d "%~dp0"
rem 优先使用训练环境的 Python 3.14；没有 py launcher 时才退回 PATH 上的 python
set "PY=python"
py -3.14 -c "import sys" >nul 2>nul
if not errorlevel 1 set "PY=py -3.14"
start "KPL-Site-Watch" "%ComSpec%" /k %PY% watch_site_data.py --interval 60
%PY% build_live_data.py --watch 30
