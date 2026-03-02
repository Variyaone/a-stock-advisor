#!/usr/bin/env python3
"""
P0-1: 补充历史绩效指标
计算年化收益率、夏普比率、最大回撤、胜率等关键指标
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
import sys
import os

def calculate_performance_metrics(portfolio_returns, risk_free_rate=0.03):
    """
    计算历史绩效指标

    Args:
        portfolio_returns: 组合收益率序列（日度）
        risk_free_rate: 无风险利率（年化，默认3%）

    Returns:
        dict: 包含所有绩效指标的字典
    """
    if len(portfolio_returns) == 0:
        return {"error": "没有收益率数据"}

    # 转换为numpy数组
    returns = np.array(portfolio_returns)
    returns = returns[~np.isnan(returns)]  # 移除NaN

    if len(returns) < 2:
        return {"error": "数据不足"}

    # 1. 年化收益率
    total_return = (1 + returns).prod() - 1
    num_days = len(returns)
    days_per_year = 252  # A股交易日
    annual_return = (1 + total_return) ** (days_per_year / num_days) - 1

    # 2. 年化波动率
    annual_volatility = returns.std() * np.sqrt(days_per_year)

    # 3. 夏普比率
    excess_return = annual_return - risk_free_rate
    sharpe_ratio = excess_return / annual_volatility if annual_volatility > 0 else 0

    # 4. 最大回撤
    cumulative = pd.Series((1 + returns).cumprod())
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()

    # 5. 卡玛比率（收益/最大回撤）
    calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0

    # 6. 月度/周度胜率
    if len(returns) >= 21:  # 至少一个月数据（假设每月21个交易日）
        # 简化计算：按月分组
        num_months = len(returns) // 21
        if num_months >= 1:
            monthly_returns = []
            for i in range(num_months):
                start = i * 21
                end = (i + 1) * 21
                if end <= len(returns):
                    monthly_returns.append(returns[start:end].sum())
            monthly_returns = np.array(monthly_returns)
            monthly_win_rate = (monthly_returns > 0).mean()
        else:
            monthly_win_rate = None
    else:
        monthly_win_rate = None

    # 7. 盈亏比（平均盈利/平均亏损）
    gains = returns[returns > 0]
    losses = returns[returns < 0]
    avg_gain = gains.mean() if len(gains) > 0 else 0
    avg_loss = abs(losses.mean()) if len(losses) > 0 else 1
    profit_loss_ratio = avg_gain / avg_loss if avg_loss > 0 else 0

    # 8. 信息比率（相对于基准的超额收益/跟踪误差）
    # 假设基准收益率为市场平均（可用实际基准数据替换）
    benchmark_returns = np.zeros_like(returns)  # 占位
    excess_returns = returns - benchmark_returns
    information_ratio = excess_returns.mean() / (excess_returns.std() * np.sqrt(days_per_year)) if excess_returns.std() > 0 else 0

    # 9. Sortino比率（只考虑下行风险）
    downside_returns = returns[returns < 0]
    downside_volatility = downside_returns.std() * np.sqrt(days_per_year) if len(downside_returns) > 0 else annual_volatility
    sortino_ratio = excess_return / downside_volatility if downside_volatility > 0 else 0

    # 10. 尾部风险（VaR和CVaR）
    var_95 = np.percentile(returns, 5)  # 95%置信度的VaR
    cvar_95 = returns[returns <= var_95].mean()  # 条件VaR

    return {
        "annual_return": {
            "value": annual_return,
            "format": f"{annual_return:.2%}",
            "grade": "优秀" if annual_return > 0.15 else "良好" if annual_return > 0.10 else "一般"
        },
        "annual_volatility": {
            "value": annual_volatility,
            "format": f"{annual_volatility:.2%}",
            "grade": "低" if annual_volatility < 0.15 else "中" if annual_volatility < 0.25 else "高"
        },
        "sharpe_ratio": {
            "value": sharpe_ratio,
            "format": f"{sharpe_ratio:.2f}",
            "grade": "优秀" if sharpe_ratio > 2.0 else "良好" if sharpe_ratio > 1.5 else "一般" if sharpe_ratio > 1.0 else "差"
        },
        "max_drawdown": {
            "value": max_drawdown,
            "format": f"{max_drawdown:.2%}",
            "grade": "稳健" if abs(max_drawdown) < 0.15 else "一般" if abs(max_drawdown) < 0.25 else "激进"
        },
        "calmar_ratio": {
            "value": calmar_ratio,
            "format": f"{calmar_ratio:.2f}",
            "grade": "优秀" if calmar_ratio > 1.0 else "良好" if calmar_ratio > 0.5 else "一般"
        },
        "monthly_win_rate": {
            "value": monthly_win_rate,
            "format": f"{monthly_win_rate:.1%}" if monthly_win_rate is not None else "N/A",
            "grade": "优秀" if monthly_win_rate and monthly_win_rate > 0.6 else "一般"
        },
        "profit_loss_ratio": {
            "value": profit_loss_ratio,
            "format": f"{profit_loss_ratio:.2f}",
            "grade": "良好" if profit_loss_ratio > 1.5 else "一般"
        },
        "information_ratio": {
            "value": information_ratio,
            "format": f"{information_ratio:.2f}",
            "grade": "优秀" if information_ratio > 1.0 else "一般" if information_ratio > 0.5 else "差"
        },
        "sortino_ratio": {
            "value": sortino_ratio,
            "format": f"{sortino_ratio:.2f}",
            "grade": "优秀" if sortino_ratio > 2.0 else "良好" if sortino_ratio > 1.5 else "一般"
        },
        "var_95": {
            "value": var_95,
            "format": f"{var_95:.2%}"
        },
        "cvar_95": {
            "value": cvar_95,
            "format": f"{cvar_95:.2%}"
        },
        "data_points": {
            "value": len(returns),
            "format": f"{len(returns)}个交易日",
            "years": len(returns) / 252
        }
    }


def load_backtest_data():
    """加载回测数据"""
    # 尝试加载回测结果
    try:
        with open('reports/backtest_results.json', 'r') as f:
            backtest_data = json.load(f)

        if 'daily_returns' in backtest_data:
            return backtest_data['daily_returns']
        elif 'portfolio_value' in backtest_data:
            portfolio_values = backtest_data['portfolio_value']
            if isinstance(portfolio_values, list):
                # 计算收益率
                portfolio_values = np.array(portfolio_values)
                returns = np.diff(portfolio_values) / portfolio_values[:-1]
                return returns.tolist()
    except Exception as e:
        print(f"⚠️ 无法加载回测数据: {e}")

    # 如果没有回测数据，生成模拟数据作为示例
    print("⚠️ 未找到回测数据，使用模拟数据展示指标计算")
    np.random.seed(42)
    num_days = 252  # 1年数据
    # 模拟正态分布的收益率
    returns = np.random.normal(loc=0.0008, scale=0.015, size=num_days)  # 年化~20%, 波动~24%
    return returns.tolist()


def generate_performance_report():
    """生成绩效指标报告"""
    print("=" * 70)
    print("📊 P0-1: 历史绩效指标计算")
    print("=" * 70)
    print()

    # 加载回测数据
    print("📂 加载回测数据...")
    returns = load_backtest_data()
    print(f"✓ 加载了 {len(returns)} 个交易日数据")
    print()

    # 计算绩效指标
    print("🔬 计算绩效指标...")
    metrics = calculate_performance_metrics(returns)

    if "error" in metrics:
        print(f"❌ 计算失败: {metrics['error']}")
        return None

    print("✓ 指标计算完成")
    print()

    # 打印报告
    print("=" * 70)
    print("📊 历史绩效指标报告")
    print("=" * 70)
    print()

    # 收益能力
    print("💰 收益能力")
    print("-" * 70)
    print(f"年化收益率: {metrics['annual_return']['format']:>12}  ({metrics['annual_return']['grade']})")
    print(f"月度胜率:   {metrics['monthly_win_rate']['format']:>12}  ({metrics['monthly_win_rate']['grade']})")
    print(f"盈亏比:     {metrics['profit_loss_ratio']['format']:>12}  ({metrics['profit_loss_ratio']['grade']})")
    print()

    # 风险控制
    print("⚠️  风险控制")
    print("-" * 70)
    print(f"最大回撤:   {metrics['max_drawdown']['format']:>12}  ({metrics['max_drawdown']['grade']})")
    print(f"年化波动率: {metrics['annual_volatility']['format']:>12}  ({metrics['annual_volatility']['grade']})")
    print(f"VaR (95%):  {metrics['var_95']['format']:>12}")
    print(f"CVaR (95%): {metrics['cvar_95']['format']:>12}")
    print()

    # 风险调整收益
    print("📈 风险调整收益")
    print("-" * 70)
    print(f"夏普比率:   {metrics['sharpe_ratio']['format']:>12}  ({metrics['sharpe_ratio']['grade']})")
    print(f"索提诺比率: {metrics['sortino_ratio']['format']:>12}  ({metrics['sortino_ratio']['grade']})")
    print(f"卡玛比率:   {metrics['calmar_ratio']['format']:>12}  ({metrics['calmar_ratio']['grade']})")
    print(f"信息比率:   {metrics['information_ratio']['format']:>12}  ({metrics['information_ratio']['grade']})")
    print()

    # 数据概览
    print("📊 数据概览")
    print("-" * 70)
    print(f"交易日:     {metrics['data_points']['format']:>12}")
    print(f"覆盖年限:   {metrics['data_points']['years']:.2f} 年")
    print()

    # 评估总结
    print("=" * 70)
    print("🎯 评估总结")
    print("=" * 70)
    print()

    # 根据指标给出综合评估
    score = 0
    if metrics['sharpe_ratio']['value'] > 1.5:
        score += 30
    elif metrics['sharpe_ratio']['value'] > 1.0:
        score += 20
    else:
        score += 10

    if abs(metrics['max_drawdown']['value']) < 0.15:
        score += 30
    elif abs(metrics['max_drawdown']['value']) < 0.25:
        score += 20
    else:
        score += 10

    if metrics['calmar_ratio']['value'] > 1.0:
        score += 20
    elif metrics['calmar_ratio']['value'] > 0.5:
        score += 10

    if metrics['monthly_win_rate']['value'] and metrics['monthly_win_rate']['value'] > 0.6:
        score += 20
    elif metrics['monthly_win_rate']['value']:
        score += 10

    grade = "S (优秀)" if score >= 90 else "A (良好)" if score >= 70 else "B (一般)" if score >= 50 else "C (较差)"

    print(f"综合评分: {score}/100")
    print(f"评级:     {grade}")
    print()

    # 保存结果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'reports/performance_metrics_{timestamp}.json'

    # 确保reports目录存在
    import os
    os.makedirs('reports', exist_ok=True)

    with open(output_file, 'w') as f:
        # 转换非JSON可序列化的值
        metrics_serializable = {}
        for key, value in metrics.items():
            if isinstance(value, dict) and 'value' in value:
                metrics_serializable[key] = {
                    'value': float(value['value']) if isinstance(value['value'], (int, float, np.number)) else value['value'],
                    'format': value['format'],
                    'grade': value.get('grade', 'N/A')
                }

        json.dump(metrics_serializable, f, indent=2, ensure_ascii=False)

    print(f"✓ 结果已保存: {output_file}")
    print()

    return metrics


if __name__ == "__main__":
    metrics = generate_performance_report()

    if metrics:
        print("✅ P0-1 历史绩效指标计算完成！")
    else:
        print("❌ 计算失败")
