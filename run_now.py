#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
立即运行选股测试 - 忽略周末检测
"""

import sys
sys.path.insert(0, '.')

from code import multi_factor_model, stock_selector, generate_report
import pandas as pd
import pickle
from datetime import datetime
import json

print("=" * 60)
print("A股量化系统 - 立即测试运行")
print("=" * 60)
print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("注意: 忽略周末检测，强制执行选股")
print("")

# 加载数据
print("📊 加载数据...")
try:
    with open('data/mock_data.pkl', 'rb') as f:
        data = pickle.load(f)
    print(f"   ✅ 数据加载成功: {data.shape[0]:,} 条记录")
except FileNotFoundError:
    print("   ❌ 数据文件不存在")
    sys.exit(1)

# 获取最新数据日期（用于演示）
latest_date = data['date'].max()
print(f"   最新数据日期: {latest_date}")

# 设置因子权重（简化版本）
print("\n🔧 初始化因子模型...")
numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
factor_cols = [col for col in numeric_cols if col not in ['date', 'stock_code', 'month']]
print(f"   可用因子: {factor_cols}")

# 创建简单的等权模型
ic_weights = {col: 1.0 for col in factor_cols}
score_model = multi_factor_model.MultiFactorScoreModel()
score_model.set_ic_weighted(ic_weights, factor_cols)
print("   ✅ 因子模型初始化完成")

# 选股
print(f"\n🎯 执行选股...")
selector = stock_selector.StockSelector(score_model, n=10)
result = selector.select_top_stocks(data)
print(f"   ✅ 成功选出 {len(result)} 只股票")

# 生成报告
print(f"📝 生成报告...")
report_content = generate_report.generate_daily_recommendation(
    run_date=datetime.now(),
    factor_data=data,
    score_model=score_model,
    stock_selector=selector,
    risk_controller=None,
    n=10
)

# 保存报告
report_file = f"reports/test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
with open(report_file, 'w', encoding='utf-8') as f:
    f.write(report_content)
print(f"   ✅ 报告已保存: {report_file}")

print("\n" + "=" * 60)
print("🎉 测试运行完成！")
print("=" * 60)
print(f"\n📄 查看报告: {report_file}")
print(f"   cat {report_file}")
print("\n📋 选股结果预览:")
print(result[['综合得分']].head(10))
