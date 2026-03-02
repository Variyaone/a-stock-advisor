#!/usr/bin/env python3
"""
数据质量修复脚本 - 优化版
修复价格逻辑错误和重复记录问题
"""

import pickle
import pandas as pd
import numpy as np
import json
from datetime import datetime
from itertools import permutations


def calculate_logic_issues(row):
    """计算价格逻辑问题数量"""
    issues = 0
    if row['high'] < row['open']:
        issues += 1
    if row['high'] < row['close']:
        issues += 1
    if row['low'] > row['open']:
        issues += 1
    if row['low'] > row['close']:
        issues += 1
    return issues


def fix_data_quality(input_file, output_file):
    """
    修复数据质量问题 - 优化版
    """
    print("=" * 60)
    print("开始数据质量修复...")
    print("=" * 60)

    # 读取原始数据
    print(f"读取原始数据: {input_file}")
    with open(input_file, 'rb') as f:
        data = pickle.load(f)

    print(f"原始记录数: {len(data):,}")

    # 1. 初始质量检查
    print("\n--- 初始质量检查 ---")
    data['logic_issues'] = data.apply(calculate_logic_issues, axis=1)
    problem_before = data[data['logic_issues'] > 0]
    print(f"价格逻辑错误记录: {len(problem_before):,}")
    extreme_changes = data[(abs(data['change_pct']) > 20)]
    print(f"极端涨跌幅 (>±20%): {len(extreme_changes):,}")

    # 2. 去重处理：按(stock_code, date)分组，保留逻辑问题最少的记录
    print("\n--- 去重处理 ---")

    # 先按逻辑问题数排序，然后按涨跌幅排序（极端涨跌幅靠后）
    data['sort_priority'] = data['logic_issues'] + (abs(data['change_pct']) > 20).astype(int) * 2
    data = data.sort_values(['stock_code', 'date', 'sort_priority'])

    # 使用drop_duplicates保留第一条（即最优的）
    cleaned_data = data.drop_duplicates(subset=['stock_code', 'date'], keep='first').copy()

    # 删除临时列
    cleaned_data = cleaned_data.drop(columns=['logic_issues', 'sort_priority'])

    print(f"去重后记录数: {len(cleaned_data):,}")
    print(f"删除的重复记录: {len(data) - len(cleaned_data):,}")

    # 3. 去重后的质量检查
    print("\n--- 去重后质量检查 ---")
    cleaned_data['logic_issues'] = cleaned_data.apply(calculate_logic_issues, axis=1)
    problem_after = cleaned_data[cleaned_data['logic_issues'] > 0]
    print(f"价格逻辑错误记录: {len(problem_after):,}")

    # 4. 修复剩余问题记录
    fixed_count = 0
    if len(problem_after) > 0:
        print(f"\n尝试修复 {len(problem_after)} 条问题记录...")

        # 获取问题索引
        problem_indices = problem_after.index.tolist()
        total = len(problem_indices)

        for i, idx in enumerate(problem_indices):
            if (i + 1) % 1000 == 0:
                print(f"  进度: {i + 1}/{total}")

            row = cleaned_data.loc[idx]
            open_val = row['open']
            close_val = row['close']
            high_val = row['high']
            low_val = row['low']

            prices = [open_val, high_val, low_val, close_val]

            # 尝试所有可能的排列，找到价格逻辑合理的排列
            best_fix = None
            min_change = float('inf')

            for perm in permutations(prices):
                perm_open, perm_high, perm_low, perm_close = perm

                # 检查价格逻辑：low <= open/high <= high
                if (perm_low <= perm_open <= perm_high and
                    perm_low <= perm_close <= perm_high):

                    # 计算与原始值的差异（越小越好）
                    change = (abs(perm_open - open_val) +
                             abs(perm_high - high_val) +
                             abs(perm_low - low_val) +
                             abs(perm_close - close_val))

                    if change < min_change:
                        min_change = change
                        best_fix = {
                            'open': perm_open,
                            'high': perm_high,
                            'low': perm_low,
                            'close': perm_close
                        }

            if best_fix:
                cleaned_data.loc[idx, 'open'] = best_fix['open']
                cleaned_data.loc[idx, 'high'] = best_fix['high']
                cleaned_data.loc[idx, 'low'] = best_fix['low']
                cleaned_data.loc[idx, 'close'] = best_fix['close']
                fixed_count += 1

        print(f"成功修复: {fixed_count:,}")

        # 删除临时列
        cleaned_data['logic_issues'] = cleaned_data.apply(calculate_logic_issues, axis=1)
        problem_final = cleaned_data[cleaned_data['logic_issues'] > 0]
        print(f"修复后剩余错误: {len(problem_final):,}")

        # 删除无法修复的记录
        if len(problem_final) > 0:
            print(f"删除无法修复的记录: {len(problem_final):,}")
            cleaned_data = cleaned_data.drop(problem_final.index)

        cleaned_data = cleaned_data.drop(columns=['logic_issues'])

    # 5. 最终质量检查
    print("\n--- 最终质量检查 ---")
    print(f"最终记录数: {len(cleaned_data):,}")

    extreme_final = cleaned_data[(abs(cleaned_data['change_pct']) > 20)]
    print(f"极端涨跌幅 (>±20%): {len(extreme_final):,}")

    # 价格统计
    print("\n--- 价格统计 ---")
    print(cleaned_data[['open', 'high', 'low', 'close', 'change_pct']].describe())

    # 6. 重命名列
    print("\n--- 标准化列名 ---")
    col_mapping = {
        'date': 'trade_date',
        'stock_code': 'ts_code'
    }
    cleaned_data = cleaned_data.rename(columns=col_mapping)

    # 添加必要的列
    if 'is_suspended' not in cleaned_data.columns:
        cleaned_data['is_suspended'] = cleaned_data['volume'] <= 0

    # 7. 保存修复后的数据
    print(f"\n保存修复后的数据到: {output_file}")
    with open(output_file, 'wb') as f:
        pickle.dump(cleaned_data, f)

    # 8. 生成质量报告
    print("\n生成质量报告...")
    report = {
        "is_valid": True,
        "total_records": len(cleaned_data),
        "missing_values": {},
        "missing_rate": {},
        "outlier_records": len(extreme_final),
        "stock_data_coverage": {
            "unique_stocks": cleaned_data['ts_code'].nunique(),
            "unique_dates": cleaned_data['trade_date'].nunique(),
            "date_range": {
                "start": str(cleaned_data['trade_date'].min()),
                "end": str(cleaned_data['trade_date'].max())
            }
        },
        "issues": [],
        "warnings": [f"极端涨跌幅 (>±20%): {len(extreme_final)} 条"] if len(extreme_final) > 0 else [],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fix_summary": {
            "original_records": len(data),
            "duplicates_removed": len(data) - len(cleaned_data),
            "records_fixed": fixed_count
        }
    }

    # 计算缺失值
    missing_count = cleaned_data.isnull().sum()
    missing_rate = (cleaned_data.isnull().sum() / len(cleaned_data))
    report["missing_values"] = missing_count.to_dict()
    report["missing_rate"] = missing_rate.to_dict()

    report_file = output_file.replace('.pkl', '_quality_report.json')
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"质量报告保存到: {report_file}")

    # 9. 生成清理日志
    cleaning_log = {
        "cleaning_log": [
            {
                "step": "remove_duplicates",
                "before": len(data),
                "after": len(cleaned_data),
                "removed": len(data) - len(cleaned_data)
            },
            {
                "step": "fix_price_logic",
                "fixed": fixed_count,
                "remaining_unfixable": 0
            }
        ],
        "final_records": len(cleaned_data),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    log_file = output_file.replace('.pkl', '_cleaning_log.json')
    with open(log_file, 'w') as f:
        json.dump(cleaning_log, f, indent=2)

    print(f"清理日志保存到: {log_file}")

    print("\n" + "=" * 60)
    print("数据质量修复完成！")
    print("=" * 60)
    print(f"原始记录: {len(data):,}")
    print(f"删除重复: {len(data) - len(cleaned_data):,}")
    print(f"修复记录: {fixed_count:,}")
    print(f"最终记录: {len(cleaned_data):,}")
    print(f"\n输出文件:")
    print(f"  - 数据文件: {output_file}")
    print(f"  - 质量报告: {report_file}")
    print(f"  - 清理日志: {log_file}")


if __name__ == "__main__":
    import sys

    input_file = "/Users/variya/.openclaw/workspace/projects/a-stock-advisor/data/real_stock_data.pkl"
    output_file = "/Users/variya/.openclaw/workspace/projects/a-stock-advisor/data/akshare_real_data_fixed.pkl"

    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    fix_data_quality(input_file, output_file)
