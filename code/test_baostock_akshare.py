#!/usr/bin/env python3
"""
测试 Baostock, AKShare, 智投API 三个数据源连接
"""

import sys
import pandas as pd
import requests
import json
from datetime import datetime

# 切换到项目目录
import os
WORK_DIR = '/Users/variya/.openclaw/workspace/projects/a-stock-advisor'
os.chdir(WORK_DIR)

print("=" * 70)
print("A股数据源连接测试 - Baostock + AKShare + 智投API")
print("=" * 70)

# ==================== 1. 测试 Baostock ====================
print("\n[1/3] 测试 Baostock...")
try:
    import baostock as bs

    lg = bs.login()
    print(f" 登录结果: {lg}")

    # 获取股票列表
    rs = bs.query_all_stock(day='2023-12-29')
    bs_stock_list = []
    while (rs.error_code == '0') & rs.next():
        bs_stock_list.append(rs.get_row_data())
    df_bs = pd.DataFrame(bs_stock_list, columns=rs.fields)
    print(f"  ✓ Baostock 连接成功")
    print(f"    - 获取股票列表: {len(df_bs)} 只股票")
    print(f"    - 列字段: {list(rs.fields)}")

    # 测试获取单只股票数据
    print("\n  测试获取平安银行(600000)数据...")
    rs = bs.query_history_k_data_plus(
        "sh.600000",
        "date,code,open,high,low,close,preclose,volume,amount,pctChg,turn",
        start_date='2023-01-01',
        end_date='2023-12-31',
        frequency="d",
        adjustflag="2"  # 后复权
    )
    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())
    df_hist = pd.DataFrame(data_list, columns=rs.fields)
    print(f"  ✓ 获取历史数据成功: {len(df_hist)} 条记录")
    print(f"    - 列字段: {list(rs.fields)}")

    bs.logout()

except ImportError as e:
    print(f"  ✗ Baostock 未安装: {e}")
    print(f"    安装命令: pip install baostock")
except Exception as e:
    print(f"  ✗ Baostock 连接失败: {e}")

# ==================== 2. 测试 AKShare ====================
print("\n[2/3] 测试 AKShare...")
try:
    import akshare as ak

    # 获取股票列表
    stock_list = ak.stock_zh_a_spot_em()
    print(f"  ✓ AKShare 连接成功")
    print(f"    - 获取股票列表: {len(stock_list)} 只股票")
    print(f"    - 列字段: {list(stock_list.columns)[:10]}...")  # 只显示前10个

    # 测试获取历史数据
    print("\n  测试获取平安银行(000001)数据...")
    hist_data = ak.stock_zh_a_hist(
        symbol="000001",
        period="daily",
        start_date="20230101",
        end_date="20231231",
        adjust="qfq"
    )
    print(f"  ✓ 获取历史数据成功: {len(hist_data)} 条记录")
    print(f"    - 列字段: {list(hist_data.columns)}")

except ImportError as e:
    print(f"  ✗ AKShare 未安装: {e}")
    print(f"    安装命令: pip install akshare")
except Exception as e:
    print(f"  ✗ AKShare 连接失败: {e}")

# ==================== 3. 测试智投API ====================
print("\n[3/3] 测试智投API...")
ZT_TOKEN = "37171346-847B-47D5-91F8-BCABDDF3C845"

try:
    # 尝试获取股票列表
    url = "https://www.zhituapi.com/api/stock/hsstock/list"
    headers = {
        'Token': ZT_TOKEN,
        'Content-Type': 'application/json'
    }

    # 根据智投API文档，这里需要调整实际请求方式
    print(f"  正在测试智投API token: {ZT_TOKEN[:20]}...")

    # 尝试不同的端点
    endpoints = [
        "https://www.zhituapi.com/api/stock/hsstock/list",
        "https://www.zhituapi.com/api/stock/list",
        "http://www.zhituapi.com/hsstockapi.html"  # 这可能是文档页面
    ]

    for endpoint in endpoints:
        try:
            print(f"    尝试端点: {endpoint}")
            response = requests.get(endpoint, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ 智投API 连接成功")
                print(f"    - 响应: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}...")
                break
            else:
                print(f"    - 状态码: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"    - 请求失败: {e}")
    else:
        print(f"  ⚠️ 智投API 测试未通过，可能需要查看文档获取正确端点")

except Exception as e:
    print(f"  ✗ 智投API 连接失败: {e}")

# ==================== 总结 ====================
print("\n" + "=" * 70)
print("总结")
print("=" * 70)
print("""
1. Baostock:
   - 优势：完全免费，无需注册，无调用限制
   - 使用：bs.login() -> query_history_k_data_plus() -> bs.logout()

2. AKShare:
   - 优势：更新及时，数据丰富
   - 使用：ak.stock_zh_a_hist() 获取历史数据

3. 智投API:
   - 需要查看准确文档获取正确端点
   - Token: 37171346-847B-47D5-91F8-BCABDDF3C845

推荐方案:
   - 主力: Baostock (稳定、无限制)
   - 补充: AKShare (实时更新)
   - 验证: 交叉验证两者数据一致性
""")

print("\n✓ 测试完成！")
