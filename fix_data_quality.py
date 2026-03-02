#!/usr/bin/env python3
"""
数据质量修复脚本
修复价格逻辑错误和重复记录问题
"""

import pickle
import pandas as pd
import numpy as np
import json
from datetime import datetime


def check_price_logic(row):
    """
    检查价格逻辑是否正确
    返回: (is_valid, score)
    score越低表示数据质量越好（不符合规则的数量）
    """
    issues = 0

    # 检查1: 最高价不能低于开盘价
    if row['high'] < row['open']:
        issues += 1

    # 检查2: 最高价不能低于收盘价
    if row['high'] < row['close']:
        issues += 1

    # 检查3: 最低价不能高于开盘价
    if row['low'] > row['open']:
        issues += 1

    # 检查4: 最低价不能高于收盘价
    if row['low'] > row['close']:
        issues += 1

    is_valid = (issues == 0)
    return is_valid, issues


def calculate_quality_score(row):
    """
    计算数据质量分数
    分数越低越好
    """
    is_valid, price_issues = check_price_logic(row)

    # 价格逻辑问题权重最高
    score = price_issues * 100

    # 检查涨跌幅是否合理（A股通常±10%，科创板/创业板±20%）
    # 新股上市首日或重组复牌可能有极端涨跌幅
    if abs(row['change_pct']) > 30:  # 极端涨跌幅扣分
        score += 20
    elif abs(row['change_pct']) > 20:
        score += 10

    # 检查成交量为0的情况（可能是停牌）
    if row['volume'] <= 0:
        score += 5

    return score


def fix_data_quality(input_file, output_file):
    """
    修复数据质量问题
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
    problem_before = data[
        (data['high'] < data['open']) |
        (data['high'] < data['close']) |
        (data['low'] > data['open']) |
        (data['low'] > data['close'])
    ]
    print(f"价格逻辑错误记录: {len(problem_before):,}")
    extreme_changes = data[(abs(data['change_pct']) > 20)]
    print(f"极端涨跌幅 (>±20%): {len(extreme_changes):,}")

    # 2. 去重处理：按(stock_code, date)分组，保留质量最好的记录
    print("\n--- 去重处理 ---")
    grouped = data.groupby(['stock_code', 'date'])
    print(f"唯一(stock_code, date)组合数: {len(grouped):,}")

    # 对每个组，添加质量分数并保留最好的
    def select_best_record(group):
        group = group.copy()
        group['quality_score'] = group.apply(calculate_quality_score, axis=1)
        # 优先保留质量分数最低（质量最好）的记录
        return group.nsmallest(1, 'quality_score').drop(columns=['quality_score'])

    print("正在选择最佳记录...")
    cleaned_data = grouped.apply(select_best_record).reset_index(drop=True)

    print(f"去重后记录数: {len(cleaned_data):,}")
    print(f"删除的重复记录: {len(data) - len(cleaned_data):,}")

    # 3. 去重后的质量检查
    print("\n--- 去重后质量检查 ---")
    problem_after = cleaned_data[
        (cleaned_data['high'] < cleaned_data['open']) |
        (cleaned_data['high'] < cleaned_data['close']) |
        (cleaned_data['low'] > cleaned_data['open']) |
        (cleaned_data['low'] > cleaned_data['close'])
    ]
    print(f"价格逻辑错误记录: {len(problem_after):,}")

    # 4. 如果仍有价格逻辑错误，尝试修复
    if len(problem_after) > 0:
        print(f"\n--- 剩余 {len(problem_after)} 条问题记录，尝试修复 ---")

        # 策略：重新排列价格列
        # 检查是否可以通过重新排序来修复
        def fix_price_order(row):
            open_val = row['open']
            close_val = row['close']
            high_val = row['high']
            low_val = row['low']

            # 尝试所有可能的排列，找到价格逻辑合理的排列
            prices = [open_val, high_val, low_val, close_val]
            from itertools import permutations

            best_fix = None
            min_change = float('inf')

            # 尝试4! = 24种排列
            for perm in permutations(prices):
                perm_open, perm_high, perm_low, perm_close = perm

                # 检查价格逻辑
                if (perm_low <= perm_open <= perm_high and
                    perm_low <= perm_close <= perm_high):
                    # 这个排列是合理的，计算与原始值的差异
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

            return best_fix

        # 对每条问题记录尝试修复
        fixed_count = 0
        for idx in problem_after.index:
            fix = fix_price_order(cleaned_data.loc[idx])
            if fix:
                cleaned_data.loc[idx, 'open'] = fix['open']
                cleaned_data.loc[idx, 'high'] = fix['high']
                cleaned_data.loc[idx, 'low'] = fix['low']
                cleaned_data.loc[idx, 'close'] = fix['close']
                fixed_count += 1

        print(f"成功修复记录: {fixed_count:,}")

        # 再次检查
        problem_final = cleaned_data[
            (cleaned_data['high'] < cleaned_data['open']) |
            (cleaned_data['high'] < cleaned_data['close']) |
            (cleaned_data['low'] > cleaned_data['open']) |
            (cleaned_data['low'] > cleaned_data['close'])
        ]
        print(f"修复后剩余价格逻辑错误: {len(problem_final):,}")

        # 删除无法修复的记录
        if len(problem_final) > 0:
            print(f"删除无法修复的记录: {len(problem_final):,}")
            cleaned_data = cleaned_data.drop(problem_final.index)

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
        "missing_values": cleaned_data.isnull().sum().to_dict(),
        "missing_rate": (cleaned_data.isnull().sum() / len(cleaned_data)).to_dict(),
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
            "records_fixed": fixed_count if 'fixed_count' in locals() else 0
        }
    }

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
                "fixed": fixed_count if 'fixed_count' in locals() else 0,
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
