#!/usr/bin/env python3
"""
测试AKShare和Tushare数据源连接
"""

import akshare as ak
import tushare as ts
import pandas as pd
import sys

TUSHARE_TOKEN = "14423f1b4d5af6dc47dd1dc8d9d5994dc05d10dbb86cc2d0da753d25"

print("=" * 70)
print("数据源连接测试")
print("=" * 70)

# 测试1: AKShare
print("\n[1/5] 测试 AKShare...")
try:
    # 获取股票列表
    stock_list = ak.stock_zh_a_spot_em()
    print(f"  ✓ AKShare 正常")
    print(f"    - 获取股票列表: {len(stock_list)} 只股票")
    print(f"    - 列字段: {list(stock_list.columns)}")
except Exception as e:
    print(f"  ✗ AKShare 失败: {e}")
    sys.exit(1)

# 测试2: AKShare 获取历史数据
print("\n[2/5] 测试 AKShare 获取历史数据...")
try:
    # 测试获取平安银行(000001)的历史数据
    hist_data = ak.stock_zh_a_hist(
        symbol="000001",
        period="daily",
        start_date="20240101",
        end_date="20241231",
        adjust="qfq"
    )
    print(f"  ✓ AKShare 历史数据正常")
    print(f"    - 获取记录数: {len(hist_data)}")
    print(f"    - 列字段: {list(hist_data.columns)}")
    print(f"    - 数据样例:")
    print(f"    {hist_data.head(1).to_string(index=False).replace(chr(10), chr(10) + '    ')}")
except Exception as e:
    print(f"  ✗ AKShare 历史数据失败: {e}")
    sys.exit(1)

# 测试3: Tushare
print("\n[3/5] 测试 Tushare...")
try:
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()

    # 获取股票列表
    stock_list = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
    print(f"  ✓ Tushare 正常")
    print(f"    - 获取股票列表: {len(stock_list)} 只股票")
    print(f"    - 列字段: {list(stock_list.columns)}")
except Exception as e:
    print(f"  ✗ Tushare 失败: {e}")

# 测试4: Tushare 获取历史数据
print("\n[4/5] 测试 Tushare 获取历史数据...")
try:
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()

    # 获取平安银行(000001.SZ)的历史数据
    daily_data = pro.daily(ts_code='000001.SZ', start_date='20240101', end_date='20241231')
    print(f"  ✓ Tushare 历史数据正常")
    print(f"    - 获取记录数: {len(daily_data)}")
    print(f"    - 列字段: {list(daily_data.columns)}")
    if len(daily_data) > 0:
        print(f"    - 数据样例:")
        print(f"    {daily_data.head(1).to_string(index=False).replace(chr(10), chr(10) + '    ')}")
except Exception as e:
    print(f"  ✗ Tushare 历史数据失败: {e}")

# 测试5: 比较数据字段
print("\n[5/5] 数据字段对比...")

print("\n  AKShare 列名:")
akshare_cols = [
    '日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率'
]
for col in akshare_cols:
    print(f"    - {col}")

print("\n  Tushare 列名:")
tushare_cols = [
    'ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'pre_close',
    'change', 'pct_chg', 'vol', 'amount'
]
for col in tushare_cols:
    print(f"    - {col}")

print("\n  目标字段:")
target_cols = [
    'ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'turnover_rate'
]
for col in target_cols:
    print(f"    - {col}")

# 推荐方案
print("\n" + "=" * 70)
print("推荐方案")
print("=" * 70)
print("""
主要数据源: AKShare
  优势:
    - 完全免费，无调用限制
    - 数据更新及时
    - 接口稳定
  使用方式:
    - stock_zh_a_hist() 获取日线数据
    - 列名标准化: 日期->date, 开盘->open, 成交量->volume, etc.

备用数据源: Tushare
  优势:
    - 数据质量高
    - API规范
  限制:
    - 每日200次调用限制
  使用方式:
    - daily() 获取日线数据
    - pro.trade_cal() 获取交易日历
""")

print("\n✓ 数据源测试完成！")
