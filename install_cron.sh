#!/bin/bash
#
# A股量化系统 - Cron安装脚本
#

WORKSPACE="/Users/variya/.openclaw/workspace/projects/a-stock-advisor"
CRON_JOB="30 18 * * 1-5 cd $WORKSPACE && /opt/homebrew/bin/python3 run_daily.py >> $WORKSPACE/logs/daily_run.log 2>&1"

# 检查工作目录
if [ ! -d "$WORKSPACE" ]; then
    echo "❌ 工作目录不存在: $WORKSPACE"
    exit 1
fi

# 创建日志目录
mkdir -p "$WORKSPACE/logs"

# 检查是否已安装
if crontab -l 2>/dev/null | grep -q "run_daily.py"; then
    echo "⚠️ Cron job已存在，先删除旧任务"
    crontab -l 2>/dev/null | grep -v "run_daily.py" | crontab -
fi

# 安装新任务
(
    crontab -l 2>/dev/null
    echo "$CRON_JOB"
) | crontab -

echo "✅ Cron任务已安装"
echo "📋 任务详情:"
echo "   - 运行时间: 每周一至周五 18:30"
echo "   - 工作目录: $WORKSPACE"
echo "   - 日志文件: $WORKSPACE/logs/daily_run.log"
echo ""
echo "📝 查看当前Cron任务: crontab -l"
echo "🗑️ 删除Cron任务: crontab -e (删除对应的行)"
