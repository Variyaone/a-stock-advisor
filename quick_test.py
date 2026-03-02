#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版测试运行 - 直接输出选股结果
"""

import sys
sys.path.insert(0, '.')

from code import multi_factor_model, stock_selector
import pandas as pd
import pickle
from datetime import datetime

print("=" * 60)
print("🦞 A股量化系统 - 快速测试")
print("=" * 60)
print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("")

# 加载数据
print("📊 加载数据...")
with open('data/mock_data.pkl', 'rb') as f:
    data = pickle.load(f)
print(f"   ✅ 数据: {data.shape[0]:,} 条记录")

# 获取最新数据
latest_date = data['date'].max()
print(f"   最新日期: {latest_date}")

# 初始化因子模型
numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
factor_cols = [col for col in numeric_cols if col not in ['date', 'stock_code', 'month']]
print(f"\n🔧 可用因子: {len(factor_cols)}个")

ic_weights = {col: 1.0 for col in factor_cols}
score_model = multi_factor_model.MultiFactorScoreModel()
score_model.set_ic_weighted(ic_weights, factor_cols)

# 选股 (取最新一天的数据)
latest_data = data[data['date'] == latest_date].set_index('stock_code')
if len(latest_data) == 0:
    print("   ⚠️ 最新日期无数据，使用全部数据")
    data_for_selection = data.set_index('stock_code')
else:
    data_for_selection = latest_data

print(f"\n🎯 选股池: {len(data_for_selection)} 只股票")
selector = stock_selector.StockSelector(score_model, n=10)
result = selector.select_top_stocks(data_for_selection)

print("\n" + "=" * 60)
print("📋 选股结果 (Top 10)")
print("=" * 60)

# 输出结果表格
print(f"\n{'排名':<6}{'股票代码':<12}{'综合得分':<12}")
print("-" * 30)
for idx, (stock_code, row) in enumerate(result.iterrows(), 1):
    score = row['综合得分']
    print(f"{idx:<6}{stock_code:<12}{score:<12.2f}")

print("\n✅ 测试运行完成！\n")
print(f"💡 提示:")
print(f"   - 当前是周末，Cron定时任务会在工作日18:30运行")
print(f"   - 查看Cron任务: crontab -l | grep run_daily")
print(f"   - 手动运行: python3 run_daily.py")
