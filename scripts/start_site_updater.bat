@echo off
rem 网站数据自动更新（两个循环）：
rem   1) watch_site_data.py  监视数据变化 → 重建网站数据（60s 检查）
rem   2) build_live_data.py  实时比分/胜率/预测 → assets/live.js（30s 刷新）
rem 双击运行；关闭窗口即停止。
cd /d "%~dp0"
start "KPL-Site-Watch" "%ComSpec%" /k python watch_site_data.py --interval 60
python build_live_data.py --watch 30
