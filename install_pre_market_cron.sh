#!/bin/bash
#
# A股量化系统 - 盘前推送安装脚本
# 调整：从18:35盘后推送改为8:00盘前推送
#

WORKSPACE="/Users/variya/.openclaw/workspace/projects/a-stock-advisor"

# 旧任务（盘后18:35）
OLD_CRON="35 18 * * 1-5 cd $WORKSPACE && /opt/homebrew/bin/python3 run_daily.py >> $WORKSPACE/logs/daily_run.log 2>&1"

# 新任务（盘前8:00）
NEW_CRON="0 8 * * 1-5 cd $WORKSPACE && /opt/homebrew/bin/python3 run_daily.py >> $WORKSPACE/logs/daily_run.log 2>&1"

echo "=========================================="
echo "📊 A股量化系统 - 推送时间调整"
echo "=========================================="
echo ""
echo "调整前: 工作日 18:35（盘后）"
echo "调整后: 工作日 08:00（盘前）"
echo ""

# 检查工作目录
if [ ! -d "$WORKSPACE" ]; then
    echo "❌ 工作目录不存在: $WORKSPACE"
    exit 1
fi

# 创建日志目录
mkdir -p "$WORKSPACE/logs"

# 检查并删除旧任务（包括旧的cron格式）
echo "🔍 检查现有Cron任务..."
if crontab -l 2>/dev/null | grep -q "run_daily.py"; then
    echo "✓ 发现旧的Cron任务，正在删除..."
    # 删除所有包含run_daily.py的行
    crontab -l 2>/dev/null | grep -v "run_daily.py" | crontab -
    echo "✓ 旧任务已删除"
else
    echo "✓ 未发现旧的Cron任务"
fi

echo ""
echo "📌 安装新的盘前推送任务..."

# 安装新任务（使用OpenClaw cron）
if command -v openclaw &> /dev/null; then
    echo "✓ 检测到OpenClaw CLI"
    
    # 删除旧的OpenClaw cron任务
    echo "清理旧的OpenClaw cron任务..."
    openclaw cron list 2>/dev/null | grep -i "A股" | awk '{print $2}' | while read job_id; do
        if [ ! -z "$job_id" ]; then
            echo "  删除任务: $job_id"
            openclaw cron remove "$job_id" 2>/dev/null || true
        fi
    done
    
    # 添加新的盘前推送任务
    echo ""
    echo "添加新的盘前推送任务（8:00）..."
    openclaw cron add \
        --name "A股盘前量化推送" \
        --schedule "0 8 * * 1-5" \
        --timezone "Asia/Shanghai" \
        --session "main" \
        --command "cd $WORKSPACE && /opt/homebrew/bin/python3 run_daily.py"
    
    echo ""
    echo "✅ OpenClaw Cron任务已安装"
    echo ""
    echo "📋 当前任务列表:"
    openclaw cron list
else
    echo "⚠️ 未检测到OpenClaw CLI，使用系统Cron"
    
    # 使用系统crontab
    (crontab -l 2>/dev/null; echo "$NEW_CRON") | crontab -
    
    echo "✅ 系统Cron任务已安装"
fi

echo ""
echo "=========================================="
echo "✅ 推送时间调整完成！"
echo "=========================================="
echo ""
echo "📊 新的推送时间表:"
echo "   工作日早上 08:00"
echo "   用户将在开盘前（9:30）收到推送"
echo "   可以在开盘时（9:30）立即执行"
echo ""
echo "📂 日志文件: $WORKSPACE/logs/daily_run.log"
echo "📝 查看日志: tail -f $WORKSPACE/logs/daily_run.log"
echo ""
