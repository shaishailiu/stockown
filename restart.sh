#!/bin/bash

PORT=${1:-8080}

# 停止已有的 Flask 进程
echo "正在停止旧服务..."
pkill -f "python app.py" 2>/dev/null
sleep 1

# 启动服务
echo "正在启动服务 (端口: $PORT)..."
cd "$(dirname "$0")/backend"
nohup python app.py -p "$PORT" > ../server.log 2>&1 &

echo "✅ 服务已启动 (PID: $!)"
echo "  前台查看: http://localhost:$PORT"
echo "  后台管理: http://localhost:$PORT/admin"
echo "  日志文件: server.log"
