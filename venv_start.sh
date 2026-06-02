#!/bin/bash
# ============================================
#  使用虚拟环境启动服务
#  用法: ./venv_start.sh
# ============================================

cd "$(dirname "$0")"

# 如果虚拟环境不存在，先创建并安装依赖
if [ ! -d "venv" ]; then
    echo "📦 未找到虚拟环境，正在创建..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r backend/requirements.txt
    echo "✅ 虚拟环境创建完成，依赖已安装"
else
    source venv/bin/activate
    echo "✅ 已激活虚拟环境"
fi

echo "========================================"
echo "  股票持仓管理系统（虚拟环境）"
echo "  前台查看: http://localhost:8080"
echo "  后台管理: http://localhost:8080/admin"
echo "  按 Ctrl+C 停止服务"
echo "========================================"

cd backend
python app.py -p 8080
