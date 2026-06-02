@echo off
chcp 65001 >nul
echo 正在停止旧服务...
taskkill /F /FI "WINDOWTITLE eq python app.py" >nul 2>&1
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| findstr /i "PID"') do (
    wmic process where "ProcessId=%%a" get CommandLine 2>nul | findstr "app.py" >nul && taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 >nul

echo 正在启动服务...
cd /d "%~dp0backend"
start /b python app.py > "%~dp0server.log" 2>&1

echo [OK] 服务已启动
echo   前台查看: http://localhost:5000
echo   后台管理: http://localhost:5000/admin
echo   日志文件: server.log
pause
