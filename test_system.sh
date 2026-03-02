#!/bin/bash

# A股量化系统 - 系统测试脚本（强制运行模式）

echo "============================================================"
echo "A股量化系统 - 系统测试"
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

# 测试3: 模块导入
echo "[测试3] 测试模块导入..."
python3 -c "
import sys
sys.path.insert(0, 'code')
from multi_factor_model import MultiFactorScoreModel
from stock_selector import StockSelector
from risk_controller import RiskController
from generate_report import generate_daily_recommendation
print('✓ 模块导入成功')
" || exit 1
echo ""

# 测试4: 运行选股（强制模式）
echo "[测试4] 运行完整选股流程..."
python3 -c "
# 模拟强制运行（跳过交易日检查）
import sys
import os
sys.path.insert(0, './code')

from datetime import datetime
import pandas as pd
import numpy as np
import json
import warnings
warnings.filterwarnings('ignore')

# 导入模块
from multi_factor_model import MultiFactorScoreModel
from stock_selector import StockSelector
from risk_controller import RiskController
from generate_report import generate_daily_recommendation

# 1. 加载数据
factor_data = pd.read_pickle('data/mock_data.pkl')
latest_date = factor_data['date'].max() if 'date' in factor_data.columns else pd.Timestamp.now()
latest_factor_data = factor_data[factor_data['date'] == latest_date] if 'date' in factor_data.columns and len(factor_data[factor_data['date'] == latest_date]) > 0 else factor_data.copy()

# 确保有stock_code列
if 'stock_code' not in latest_factor_data.columns:
    latest_factor_data = latest_factor_data.reset_index()
    if 'index' in latest_factor_data.columns:
        latest_factor_data = latest_factor_data.rename(columns={'index': 'stock_code'})

# 2. 加载配置
score_model = MultiFactorScoreModel()
score_model.auto_detect_factors(latest_factor_data.copy())
stock_selector = StockSelector(score_model, n=10)
risk_controller = RiskController()

# 3. 选股
selected = stock_selector.select_top_stocks(latest_factor_data.set_index('stock_code').copy(), date=str(latest_date))

# 4. 风险控制
stock_list = pd.DataFrame(columns=['股票代码', '股票名称', 'is_suspended'])
controlled, _ = risk_controller.apply_all_controls(selected, stock_list, latest_factor_data.set_index('stock_code').copy())

# 5. 生成报告
report = generate_daily_recommendation(datetime.now(), latest_factor_data.set_index('stock_code').copy(), score_model, stock_selector, risk_controller, n=10)

# 6. 保存报告
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
report_path = f'reports/system_test_{timestamp}.md'
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(report)

print(f'✓ 选股完成: {len(controlled)}只股票')
print(f'✓ 报告已生成: {report_path}')
print(f'✓ 报告大小: {len(report)}字符')
" || exit 1
echo ""

# 测试5: 检查最新的报告
echo "[测试5] 检查生成的报告..."
LATEST_REPORT=$(ls -t reports/system_test_*.md 2>/dev/null | head -1)
if [ -n "$LATEST_REPORT" ]; then
    echo "✓ 找到测试报告: $LATEST_REPORT"
    echo ""
    echo "📄 报告内容预览（前30行）:"
    head -30 "$LATEST_REPORT"
else
    echo "✗ 未找到测试报告文件"
    exit 1
fi
echo ""

# 测试6: 检查日志
echo "[测试6] 检查日志目录..."
if [ -d "logs" ]; then
    echo "✓ 日志目录存在: logs/"
    LOG_COUNT=$(find logs -name "*.log" 2>/dev/null | wc -l)
    echo "  日志文件数量: $LOG_COUNT"
else
    echo "⚠️ 日志目录不存在，将自动创建"
    mkdir -p logs
    echo "✓ 已创建日志目录"
fi
echo ""

# 测试7: 检查配置文件
echo "[测试7] 检查配置文件..."
if [ -f "config/.sample/feishu_config.json" ]; then
    echo "✓ 配置示例文件存在"
else
    echo "⚠️ 配置示例文件不存在"
fi

if [ -f "config/feishu_config.json" ]; then
    echo "✓ 实际配置文件存在（已配置）"
else
    echo "⚠️ 实际配置文件不存在（使用默认配置）"
fi
echo ""

echo "============================================================"
echo "✅ 所有系统测试通过！"
echo "============================================================"
echo ""
echo "📋 后续步骤:"
echo "  1. 如需启用飞书推送，复制配置文件:"
echo "     cp config/.sample/feishu_config.json config/feishu_config.json"
echo "     并编辑填入webhook_url"
echo ""
echo "  2. 安装定时任务:"
echo "     ./install_cron.sh"
echo ""
echo "  3. 查看最新测试报告:"
echo "     cat $LATEST_REPORT"
