#!/usr/bin/env python3
"""
A股每日选股报告 - Phase 3.8
执行选股并保存结果到JSON，供推送脚本读取
"""
import pandas as pd
import numpy as np
import json
from pathlib import Path
import sys
from datetime import datetime

# 添加项目路径
PROJECT_DIR = Path(__file__).parent.parent
sys.path.append(str(PROJECT_DIR / 'code'))

from multi_factor_model import MultiFactorScoreModel
from stock_selector import StockSelector
from risk_controller import RiskController


def run_stock_selection_and_save():
    """
    执行选股并保存结果到JSON

    返回:
        selection_result: 选股结果字典
    """
    print("="*80)
    print("A股每日选股 - Phase 3.8")
    print("="*80)

    # 项目路径
    DATA_DIR = PROJECT_DIR / 'data'
    REPORTS_DIR = PROJECT_DIR / 'reports'

    # 加载数据
    print("\n[步骤1/5] 加载数据...")
    try:
        factor_data = pd.read_pickle(DATA_DIR / 'factor_data.pkl')
        with open(REPORTS_DIR / 'factor_scores.json', 'r', encoding='utf-8') as f:
            factor_scores = json.load(f)
        print("✓ 数据加载完成")
    except FileNotFoundError as e:
        print(f"✗ 错误: 找不到数据文件 - {e}")
        return None

    # 创建模型和控制器
    print("\n[步骤2/5] 创建模型和控制器...")
    score_threshold = 40
    score_model = MultiFactorScoreModel()
    score_model.set_ic_weighted(factor_scores, score_threshold=score_threshold)
    print(f"✓ 因子权重: {list(score_model.factor_weights.keys())}")

    n = 10  # 选股数量
    stock_selector = StockSelector(score_model, n=n)
    risk_controller = RiskController()
    print("✓ 选股器和风险控制器已创建")

    # 获取最新可用数据
    print("\n[步骤3/5] 准备选股数据...")
    DATE_COL = '日期'
    STOCK_COL = '股票代码'
    NAME_COL = '股票名称'

    factor_data_copy = factor_data.copy()
    factor_data_copy['dt_date'] = pd.to_datetime(factor_data_copy[DATE_COL])
    latest_month = factor_data_copy['dt_date'].dt.to_period('M').max()

    latest_factor_data = factor_data_copy[
        factor_data_copy['dt_date'].dt.to_period('M') == latest_month
    ].copy()

    print(f"✓ 使用数据月份: {latest_month}")

    # 准备因子DataFrame
    factor_df = latest_factor_data.set_index(STOCK_COL)

    # 移除非因子列
    non_factor_cols = [DATE_COL, STOCK_COL, NAME_COL, 'dt_date', 'future_return_1m']
    factor_df = factor_df[[col for col in factor_df.columns if col not in non_factor_cols]]

    # 只包含权重中的因子
    available_factors = [f for f in score_model.factor_weights.keys() if f in factor_df.columns]
    factor_df = factor_df[available_factors]

    # 选股
    print("\n[步骤4/5] 执行选股...")
    selected = stock_selector.select_top_stocks(
        factor_df,
        date=str(latest_month)
    )

    # 获取选股理由
    selected_with_reasons = stock_selector.get_selection_with_reasons(factor_df)

    # 应用风险控制
    stock_list_df = pd.read_csv(DATA_DIR / 'stock_list.csv')
    stock_list_df = stock_list_df.rename(columns={
        '代码': 'stock_code',
        'symbol': 'stock_code',
        '名称': 'stock_name',
        '板块': 'industry',
        '行业': 'industry'
    })

    controlled, control_summary = risk_controller.apply_all_controls(
        selected, stock_list_df, factor_df
    )

    print(f"✓ 选股完成，共 {len(controlled)} 只股票")

    # 获取股票名称
    stock_names = {}
    for _, row in stock_list_df.iterrows():
        stock_names[row['stock_code']] = row.get('stock_name', row.get('名称', ''))

    for _, row in controlled.iterrows():
        stock_code = row['stock_code']
        if stock_code not in stock_names:
            # 尝试从原始数据获取
            stock_info = latest_factor_data[latest_factor_data[STOCK_COL] == stock_code]
            if len(stock_info) > 0:
                stock_names[stock_code] = stock_info[NAME_COL].iloc[0]
            else:
                stock_names[stock_code] = stock_code

    # 准备选股结果数据
    selected_stocks = []
    for _, row in controlled.iterrows():
        stock_code = row['stock_code']
        stock_name = stock_names.get(stock_code, stock_code)
        score = float(row['score'])
        reasons = row.get('reasons', '综合得分最高')

        # 尝试从selected_with_reasons获取更详细的信息
        reason_row = selected_with_reasons[selected_with_reasons['stock_code'] == stock_code]
        if len(reason_row) > 0:
            reasons = reason_row['reasons'].iloc[0]

        selected_stocks.append({
            'rank': int(row['rank']),
            'stock_code': stock_code,
            'stock_name': stock_name,
            'score': round(score, 2),
            'reasons': reasons
        })

    # 准备组合配置
    portfolio_config = {
        'n': n,
        'rebalance_frequency': 'monthly',
        'weighting_method': 'ic_weighted',
        'score_threshold': score_threshold,
        'factor_weights': {k: round(v, 4) for k, v in score_model.factor_weights.items()}
    }

    # 准备完整结果
    selection_result = {
        'selected_stocks': selected_stocks,
        'portfolio_config': portfolio_config,
        'timestamp': datetime.now().isoformat(),
        'data_month': str(latest_month),
        'control_summary': control_summary
    }

    # 保存到JSON
    print("\n[步骤5/5] 保存选股结果...")
    output_file = DATA_DIR / 'selection_result.json'

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(selection_result, f, ensure_ascii=False, indent=2)

    print(f"✓ 选股结果已保存到: {output_file}")

    # 显示选股结果预览
    print("\n" + "="*80)
    print("选股结果预览")
    print("="*80)
    print(f"数据月份: {latest_month}")
    print(f"选股数量: {len(selected_stocks)}")
    print(f"\nTop 10 股票:")
    print(f"{'排名':<4} {'股票代码':<8} {'股票名称':<10} {'综合得分':<10} {'选股理由'}")
    print("-"*80)
    for stock in selected_stocks[:10]:
        print(f"{stock['rank']:<4} {stock['stock_code']:<8} {stock['stock_name']:<10} {stock['score']:<10.2f} {stock['reasons']}")

    print("\n" + "="*80)
    print("✓ 每日选股完成")
    print("="*80)

    return selection_result


def main():
    """主程序"""
    result = run_stock_selection_and_save()
    if result is not None:
        print("\n✓ 选股任务成功完成")
        return 0
    else:
        print("\n✗ 选股任务失败")
        return 1


if __name__ == '__main__':
    sys.exit(main())
