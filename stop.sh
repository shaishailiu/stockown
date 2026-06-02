#!/bin/bash

echo "正在停止服务..."
pkill -f "python app.py" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ 服务已停止"
else
    echo "⚠️  没有找到运行中的服务"
fi
