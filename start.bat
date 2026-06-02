@echo off
chcp 65001 >nul
cd /d "%~dp0backend"
echo ========================================
echo   股票持仓管理系统
echo   前台查看: http://localhost:5000
echo   后台管理: http://localhost:5000/admin
echo   按 Ctrl+C 停止服务
echo ========================================
python app.py
