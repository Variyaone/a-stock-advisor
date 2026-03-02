#!/bin/bash

# A股量化系统 - 自动化测试脚本

echo "============================================================"
echo "A股量化系统 - 自动化测试"
echo "============================================================"
echo ""

# 测试1: 依赖检查
echo "[测试1] 检查依赖..."
python3 -c "import pandas; import numpy; print('✓ 依赖检查通过')" || exit 1
echo ""

# 测试2: 数据加载
echo "[测试2] 加载数据..."
python3 -c "
import pandas as pd
import os
if os.path.exists('data/factor_data.pkl'):
    data = pd.read_pickle('data/factor_data.pkl')
else:
    data = pd.read_pickle('data/mock_data.pkl')
print(f'✓ 数据加载成功: {len(data)} 条记录')
" || exit 1
echo ""

# 测试3: 运行选股
echo "[测试3] 运行选股..."
python3 run_daily.py || exit 1
echo ""

# 测试4: 报告生成
echo "[测试4] 检查报告..."
REPORT_FILE=$(ls -t reports/daily_recommendation_*.md 2>/dev/null | head -1)
if [ -n "$REPORT_FILE" ]; then
    echo "✓ 报告已生成: $REPORT_FILE"
    echo ""
    echo "📄 报告内容预览:"
    head -30 "$REPORT_FILE"
else
    echo "✗ 未找到报告文件"
    exit 1
fi
echo ""

# 测试5: 检查日志
echo "[测试5] 检查日志..."
LOG_FILE="logs/daily_run.log"
if [ -f "$LOG_FILE" ]; then
    echo "✓ 日志文件存在: $LOG_FILE"
    LOG_SIZE=$(du -h "$LOG_FILE" | cut -f1)
    echo "  日志大小: $LOG_SIZE"
else
    echo "⚠️ 日志文件不存在: $LOG_FILE"
fi
echo ""

echo "============================================================"
echo "✅ 所有测试通过！"
echo "============================================================"
