#!/usr/bin/env python3
"""
验证生成的数据
"""

import pickle
import pandas as pd

workdir = '/Users/variya/.openclaw/workspace/projects/a-stock-advisor'

# 加载数据
with open(f'{workdir}/data/real_stock_data.pkl', 'rb') as f:
    data = pickle.load(f)

print("=" * 70)
print("数据验证报告")
print("=" * 70)

print(f"\n数据形状: {data.shape}")
print(f"列名: {list(data.columns)}")

print(f"\n股票数量: {data['stock_code'].nunique()}")
print(f"时间范围: {data['date'].min()} 至 {data['date'].max()}")
print(f"交易日数量: {data['date'].nunique()}")
print(f"月份数量: {data['month'].nunique()}")

print("\n前10只股票的代码:")
for code in data['stock_code'].unique()[:10]:
    count = len(data[data['stock_code'] == code])
    date_range = f"{data[data['stock_code'] == code]['date'].min()} to {data[data['stock_code'] == code]['date'].max()}"
    print(f"  {code}: {count} 条记录, 日期: {date_range}")

print("\n检查列是否存在:")
required_columns = [
    'date', 'stock_code', 'stock_name',
    'open', 'close', 'high', 'low',
    'volume', 'amount', 'change_pct',
    'turnover', 'month'
]
factor_columns = [
    'ma5', 'ma20', 'ma60',
    'momentum_20', 'volatility_20',
    'turnover_ma20', 'amount_ma20',
    'price_to_ma20'
]

for col in required_columns:
    status = "✓" if col in data.columns else "✗"
    print(f"  {status} {col}")

print("\n因子列存在性:")
for col in factor_columns:
    status = "✓" if col in data.columns else "✗"
    print(f"  {status} {col}")

print("\n数据样例:")
print(data.head().to_string())

print("\n" + "=" * 70)
print("验证完成")
print("=" * 70)
