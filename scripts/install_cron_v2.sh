#!/bin/bash
#
# 安装Cron任务V2
# 包含8:00盘前推送
#

# 工作目录
WORK_DIR="/Users/variya/.openclaw/workspace/projects/a-stock-advisor"

# 备份现有crontab
echo "备份现有crontab..."
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null || echo "无现有crontab"

# 清理旧的A股任务
echo "清理旧的A股任务..."
crontab -l 2>/dev/null | grep -v "a-stock-advisor" | crontab -

# 安装新的Cron任务
echo "安装新的Cron任务..."
(crontab -l 2>/dev/null; cat <<'EOF'
# A股推送系统 - Cron任务
# 更新时间: 2026-03-02 08:30

# 7:00 -早盘数据验证（工作日）
0 7 * * 1-5 cd /Users/variya/.openclaw/workspace/projects/a-stock-advisor && /opt/homebrew/bin/python3 scripts/data_update_v2.py >> logs/morning_data_check.log 2>&1

# 8:00 -盘前推送（工作日）
0 8 * * 1-5 cd /Users/variya/.openclaw/workspace/projects/a-stock-advisor && /opt/homebrew/bin/python3 scripts/paper_trading_push.py >> logs/morning_push.log 2>&1

# 16:00 -收盘后数据验证（工作日）
0 16 * * 1-5 cd /Users/variya/.openclaw/workspace/projects/a-stock-advisor && /opt/homebrew/bin/python3 scripts/data_update_v2.py >> logs/evening_data_check.log 2>&1

# 18:30 -每日选股和推送（工作日）
30 18 * * 1-5 cd /Users/variya/.openclaw/workspace/projects/a-stock-advisor && /opt/homebrew/bin/python3 run_daily.py >> logs/daily_run.log 2>&1

# 3:00 -系统健康检查（每日）
0 3 * * * cd /Users/variya/.openclaw/workspace/projects/a-stock-advisor && /opt/homebrew/bin/python3 scripts/health_check.py >> logs/health_check.log 2>&1

# 每小时 -监控数据收集
0 * * * * cd /Users/variya/.openclaw/workspace/projects/a-stock-advisor && /opt/homebrew/bin/python3 scripts/monitor_collector.py >> logs/monitor_collector.log 2>&1

# 周日2:00 -周度策略回测
0 2 * * 0 cd /Users/variya/.openclaw/workspace/projects/a-stock-advisor && /opt/homebrew/bin/python3 scripts/run_backtest.py >> logs/backtest.log 2>&1
EOF
) | crontab -

# 验证安装
echo "验证安装..."
crontab -l | grep "a-stock-advisor"

echo ""
echo "✅ Cron任务安装完成！"
echo ""
echo "已安装任务："
echo "  07:00 -早盘数据验证"
echo "  08:00 -盘前推送（新增！）"
echo "  16:00 -收盘后数据验证"
echo "  18:30 -每日选股和推送"
echo "  03:00 -系统健康检查"
echo "  每小时 -监控数据收集"
echo "  周日 02:00 -周度回测"
echo ""
