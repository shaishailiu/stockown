@echo off
chcp 65001 >nul
echo 正在停止服务...
for /f "tokens=2 delims=," %%a in ('wmic process where "CommandLine like '%%app.py%%' and Name='python.exe'" get ProcessId /format:csv 2^>nul ^| findstr /r "[0-9]"') do (
    taskkill /F /PID %%a >nul 2>&1
)

if %errorlevel%==0 (
    echo [OK] 服务已停止
) else (
    echo [!] 没有找到运行中的服务
)
pause
