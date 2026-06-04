#!/bin/bash
# ============================================
# 一键 git 提交并推送
# 用法: ./git_push.sh "提交信息"
#       ./git_push.sh           （自动生成提交信息）
# ============================================

cd "$(dirname "$0")"

# 检查是否有改动
if git diff --quiet && git diff --cached --quiet; then
    echo "✅ 没有需要提交的改动"
    exit 0
fi

# 提交信息：优先用参数，否则自动生成
if [ -n "$1" ]; then
    MSG="$1"
else
    MSG="update $(date '+%Y-%m-%d %H:%M:%S')"
fi

echo "📝 提交信息: $MSG"
echo "========================================"

# 显示即将提交的文件
echo "📂 待提交文件:"
git status -s
echo "========================================"

# add → commit → push
git add -A
git commit -m "$MSG"

echo ""
echo "🚀 推送到远程仓库..."
git push origin main

echo ""
echo "========================================"
echo "✅ 提交完成！"
echo "========================================"
