#!/usr/bin/env python3
"""
调试 Baostock API - 获取股票列表
"""

import baostock as bs
import pandas as pd

print("测试 Baostock 获取股票列表...")

lg = bs.login()
print(f"登录: {lg}")

# 方法1: query_stock_basic - 获取证券基本信息
print("\n[1] 尝试 query_stock_basic...")
rs = bs.query_stock_basic()
print(f"字段: {rs.fields}")

data_list = []
while (rs.error_code == '0') & rs.next():
    data_list.append(rs.get_row_data())

if data_list:
    df = pd.DataFrame(data_list, columns=rs.fields)
    print(f"总数: {len(df)}")
    print(f"列名: {list(df.columns)}")
    print("\n前10行:")
    print(df.head(10).to_string())
else:
    print("没有数据")

# 方法2: query_hs300_stocks - 获取沪深300成分股
print("\n[2] 尝试 query_hs300_stocks...")
rs = bs.query_hs300_stocks(date='2023-12-29')
print(f"字段: {rs.fields}")

data_list = []
while (rs.error_code == '0') & rs.next():
    data_list.append(rs.get_row_data())

if data_list:
    df = pd.DataFrame(data_list, columns=rs.fields)
    print(f"总数: {len(df)}")
    print(f"列名: {list(df.columns)}")
    print("\n前10行:")
    print(df.head(10).to_string())
else:
    print("没有数据")

# 方法3: query_sz50_stocks - 获取上证50成分股
print("\n[3] 尝试 query_sz50_stocks...")
rs = bs.query_sz50_stocks(date='2023-12-29')
print(f"字段: {rs.fields}")

data_list = []
while (rs.error_code == '0') & rs.next():
    data_list.append(rs.get_row_data())

if data_list:
    df = pd.DataFrame(data_list, columns=rs.fields)
    print(f"总数: {len(df)}")
    print(f"列名: {list(df.columns)}")
    print("\n前10行:")
    print(df.head(10).to_string())
else:
    print("没有数据")

bs.logout()
