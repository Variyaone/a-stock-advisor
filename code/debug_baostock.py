#!/usr/bin/env python3
"""
调试 Baostock API
"""

import baostock as bs
import pandas as pd

print("测试 Baostock API...")

lg = bs.login()
print(f"登录结果: {lg}")

# 测试获取股票列表
rs = bs.query_all_stock(day='2023-12-29')
print(f"\n查询结果: {rs}")
print(f"错误代码: {rs.error_code}")
print(f"错误信息: {rs.error_msg}")
print(f"字段: {rs.fields}")

data_list = []
while (rs.error_code == '0') & rs.next():
    data_list.append(rs.get_row_data())

if data_list:
    df = pd.DataFrame(data_list, columns=rs.fields)
    print(f"\n数据样例（前5行）:")
    print(df.head())
    print(f"\n列名: {list(df.columns)}")
else:
    print("\n没有获取到数据")

bs.logout()
