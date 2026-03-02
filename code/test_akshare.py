#!/usr/bin/env python3
"""
测试AKShare接口
"""

import os
# 禁用所有代理设置
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('ALL_PROXY', None)

import akshare as ak
import pandas as pd

print("=" * 70)
print("测试AKShare接口")
print("=" * 70)

# 测试1：获取股票列表
print("\n测试1：获取股票列表...")
try:
    stock_list = ak.stock_zh_a_spot()
    print(f"✓ 成功获取股票列表: {len(stock_list)} 只")
    print(f"示例数据:\n{stock_list.head()}")
except Exception as e:
    print(f"✗ 失败: {e}")

# 测试2：获取单只股票历史数据
print("\n" + "=" * 70)
print("测试2：获取平顶银行（000001）历史数据...")
try:
    hist = ak.stock_zh_a_hist(
        symbol='000001',
        period='daily',
        start_date='20190101',
        end_date='20241231',
        adjust='qfq'
    )
    print(f"✓ 成功获取历史数据: {len(hist)} 条")
    print(f"列名: {list(hist.columns)}")
    print(f"示例数据:\n{hist.head()}")
except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback
    traceback.print_exc()

# 测试3：使用其他接口获取股票列表
print("\n" + "=" * 70)
print("测试3：获取股票列表（其他方法）...")

# 方法A：获取A股实时行情
print("\n方法A：stock_zh_a_spot()")
try:
    stock_list_a = ak.stock_zh_a_spot()
    print(f"✓ stock_zh_a_spot: {len(stock_list_a)} 只")
except Exception as e:
    print(f"✗ stock_zh_a_spot 失败: {e}")

# 方法B：获取A股实时行情（东方财富）
print("\n方法B：stock_zh_a_spot_em()")
try:
    stock_list_b = ak.stock_zh_a_spot_em()
    print(f"✓ stock_zh_a_spot_em: {len(stock_list_b)} 只")
except Exception as e:
    print(f"✗ stock_zh_a_spot_em 失败: {e}")

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)
