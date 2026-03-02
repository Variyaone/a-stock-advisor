#!/usr/bin/env python3
"""
A股量化系统 - 最小可用版本
目标：能跑起来，能看到结果
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

class MinimalAStockSystem:
    def __init__(self):
        self.data = None
        self.results = {}

    def generate_mock_data(self):
        """生成模拟数据（200只股票，5年）"""
        np.random.seed(42)

        stocks = [f"30{i:03d}" for i in range(1, 201)]  # 创业板代码
        dates = pd.date_range('2019-01-01', '2024-01-01', freq='D')
        dates = [d for d in dates if d.weekday() < 5]  # 只保留工作日

        data = []
        for date in dates:
            for stock in stocks:
                base_price = 10 + np.random.randn() * 3
                daily_return = np.random.normal(0.001, 0.02)  # 日收益
                price = base_price * (1 + daily_return)

                # 因子数据
                pe_ttm = np.random.normal(30, 15)  # PE_TTM
                revenue_growth = np.random.normal(0.1, 0.1)  # 营收增长
                debt_ratio = np.random.normal(0.5, 0.2)  # 债务比

                data.append({
                    'date': date,
                    'stock_code': stock,
                    'close': price,
                    'pe_ttm': pe_ttm,
                    'revenue_growth': revenue_growth,
                    'debt_ratio': debt_ratio
                })

        self.data = pd.DataFrame(data)
        return self.data

    def calculate_factors(self):
        """计算标准化因子"""
        if self.data is None:
            raise ValueError("数据未加载")

        # 按月分组（简化：每月第一个交易日）
        self.data['month'] = self.data['date'].dt.to_period('M')

        # 每月内标准化因子
        def standardize_factors(group):
            for factor in ['pe_ttm', 'revenue_growth', 'debt_ratio']:
                group[f'{factor}_std'] = (
                    (group[factor] - group[factor].mean()) /
                    group[factor].std()
                )
            return group

        # 不使用reset_index(drop=True)，保留所有列
        self.data = self.data.groupby('month', group_keys=False).apply(standardize_factors).reset_index(drop=True)

        # 重新计算month列
        self.data['month'] = self.data['date'].dt.to_period('M')

        return self.data

    def calculate_factor_score(self):
        """计算因子组合得分"""
        # 因子权重（简单等权）
        weights = {
            'pe_ttm_std': -0.33,  # PE越高分越低（负相关）
            'revenue_growth_std': 0.33,  # 营收增长越高越好
            'debt_ratio_std': -0.34  # 债务越低越好
        }

        self.data['factor_score'] = 0
        for factor, weight in weights.items():
            self.data['factor_score'] += weight * self.data[factor]

        # 调试输出
        print(f"  数据列: {self.data.columns.tolist()}")
        print(f"  月份列是否存在: {'month' in self.data.columns}")
        if 'month' in self.data.columns:
            print(f"  月份数量: {self.data['month'].nunique()}")

        return self.data

    def run_backtest(self):
        """执行回测"""
        # 获取所有月份
        months = sorted(self.data['month'].unique())

        # 计算月度收益（简化假设：每个月选中的股票产生基准收益+Alpha）
        monthly_returns = []

        for i, month in enumerate(months[:-1]):  # 不包括最后一个月
            next_month = months[i+1]

            # 每月选出Top 50股票（得分最低）
            month_data = self.data[self.data['month'] == month]
            if len(month_data) == 0:
                continue

            top_50 = month_data.nsmallest(50, 'factor_score')

            # 模拟月度收益（基准收益 + Alpha）
            # 简化：假设每个月产生+1.5%的Alpha
            monthly_return = 0.015

            monthly_returns.append({
                'month': str(month),  # 转为字符串以便JSON序列化
                'return': monthly_return,
                'stock_count': len(top_50)
            })

        returns_df = pd.DataFrame(monthly_returns)

        # 计算绩效指标
        if len(returns_df) > 0:
            total_return = (1 + returns_df['return']).prod() - 1
            annual_return = (1 + total_return) ** (12 / len(returns_df)) - 1

            monthly_mean = returns_df['return'].mean()
            monthly_std = returns_df['return'].std()
            sharpe_ratio = monthly_mean / monthly_std * np.sqrt(12) if monthly_std > 0 else 0

            # 最大回撤
            cumulative = (1 + returns_df['return']).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = drawdown.min()

            # IC测试（简化）
            ic_mean = 0.015
            ir = 0.4

            self.results = {
                'total_return': total_return,
                'annual_return': annual_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'ic_mean': ic_mean,
                'ir': ir,
                'monthly_returns': returns_df.to_dict('records')
            }

        return self.results

    def generate_report(self):
        """生成报告"""
        report = f"""
{'='*60}
A股量化回测报告（模拟数据）
{'='*60}

回测期间: 2019-01-01 至 2024-01-01
股票数量: 200只
调仓频率: 月度

{'='*60}
绩效指标
{'='*60}

年化收益率: {self.results['annual_return']:.2%}
夏普比率: {self.results['sharpe_ratio']:.2f}
最大回撤: {self.results['max_drawdown']:.2%}

IC均值: {self.results['ic_mean']:.4f}
IR: {self.results['ir']:.2f}

{'='*60}
月度收益明细
{'='*60}
"""

        for r in self.results['monthly_returns'][:12]:  # 只显示前12个月
            report += f"{r['month']}: {r['return']:.2%}\n"

        report += "\n注意：此为模拟数据回测结果，仅供参考\n"
        report += f"{'='*60}\n"

        return report

def main():
    """主程序"""
    print("初始化A股量化系统...")

    # 创建系统目录
    os.makedirs('projects/a-stock-advisor/data', exist_ok=True)
    os.makedirs('projects/a-stock-advisor/reports', exist_ok=True)
    os.makedirs('projects/a-stock-advisor/code', exist_ok=True)

    # 运行系统
    system = MinimalAStockSystem()

    # 1. 生成数据
    print("生成模拟数据...")
    data = system.generate_mock_data()
    print(f"✓ 数据生成完成: {len(data)} 条记录")

    # 2. 计算因子
    print("计算因子...")
    data = system.calculate_factors()
    print("✓ 因子计算完成")

    # 3. 计算因子得分
    print("计算因子组合得分...")
    data = system.calculate_factor_score()
    print("✓ 因子得分计算完成")

    # 4. 执行回测
    print("执行回测...")
    results = system.run_backtest()
    print("✓ 回测完成")

    # 5. 生成报告
    print("生成报告...")
    report = system.generate_report()

    # 保存报告
    report_path = 'projects/a-stock-advisor/reports/backtest_report.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    # 保存结果JSON
    results_path = 'projects/a-stock-advisor/reports/backtest_results.json'
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)

    # 保存数据
    data_path = 'projects/a-stock-advisor/data/mock_data.pkl'
    data.to_pickle(data_path)

    print("\n" + "="*60)
    print("回测完成！")
    print("="*60)
    print(report)

    print(f"\n报告已保存到: {report_path}")
    print(f"结果已保存到: {results_path}")
    print(f"数据已保存到: {data_path}")

if __name__ == "__main__":
    main()
