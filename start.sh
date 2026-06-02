#!/bin/bash

PORT=${1:-8080}

cd "$(dirname "$0")/backend"

echo "========================================"
echo "  股票持仓管理系统"
echo "  前台查看: http://localhost:$PORT"
echo "  后台管理: http://localhost:$PORT/admin"
echo "  按 Ctrl+C 停止服务"
echo "========================================"

python app.py -p "$PORT"
