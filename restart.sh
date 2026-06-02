#!/bin/bash

# 停止已有的 Flask 进程
echo "正在停止旧服务..."
pkill -f "python app.py" 2>/dev/null
sleep 1

# 启动服务
echo "正在启动服务..."
cd "$(dirname "$0")/backend"
nohup python app.py > ../server.log 2>&1 &

echo "✅ 服务已启动 (PID: $!)"
echo "  前台查看: http://localhost:5000"
echo "  后台管理: http://localhost:5000/admin"
echo "  日志文件: server.log"
