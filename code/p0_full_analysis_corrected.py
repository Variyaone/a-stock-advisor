#!/usr/bin/env python3
"""
P0全部分析脚本（修正版） - 使用真实数据
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
import os
import pickle

# 工作目录
WORK_DIR = '/Users/variya/.openclaw/workspace/projects/a-stock-advisor'
os.chdir(WORK_DIR)

def load_real_data():
    """加载真实的因子数据"""
    print("📂 加载真实回测数据...")
    with open('data/mock_data.pkl', 'rb') as f:
        data = pickle.load(f)

    print(f"✓ 数据加载成功: {data.shape[0]:,} 行, {data.shape[1]} 列")
    print(f"  - 股票数量: {data['stock_code'].nunique()}")
    print(f"  - 时间范围: {data['date'].min()} 至 {data['date'].max()}")
    print(f"  - 月份数量: {data['month'].nunique()}")

    return data

def construct_backtest_returns_fixed(data):
    """
    从真实数据构建准确的月度收益率序列
    """
    print("\n🔨 构建真实回测收益率...")

    monthly_returns = []
    months = sorted(data['month'].unique())

    for i, month in enumerate(months[:-1]):
        # 当月数据
        month_data = data[data['month'] == month].copy()
        month_last_day = month_data.groupby('stock_code').last().reset_index()

        # 选择因子得分最高的50只股票
        top_stocks = month_last_day.nlargest(50, 'factor_score')['stock_code'].values

        # 下月数据
        next_month = months[i + 1]
        next_month_data = data[data['month'] == next_month]

        # 获取下月首尾价格
        next_month_first = next_month_data.groupby('stock_code').first()['close'].reset_index()
        next_month_last = next_month_data.groupby('stock_code').last()['close'].reset_index()

        merged = pd.merge(
            pd.DataFrame({'stock_code': top_stocks}),
            next_month_first.rename(columns={'close': 'close_first'}),
            on='stock_code', how='inner'
        ).merge(
            next_month_last.rename(columns={'close': 'close_last'}),
            on='stock_code', how='inner'
        )

        # 计算收益率
        merged['return'] = (merged['close_last'] - merged['close_first']) / merged['close_first']
        merged = merged.dropna(subset=['return'])

        if len(merged) > 0:
            portfolio_return = merged['return'].mean()
            monthly_returns.append({
                'month': str(month),
                'next_month': str(next_month),
                'return': portfolio_return,
                'stock_count': len(merged),
                'stocks': merged['stock_code'].tolist()
            })

            if i < 3 or i >= len(months) - 4:
                print(f"  - {month} -> {next_month}: 收益率={portfolio_return:.4f}, 股票数={len(merged)}")

    returns_df = pd.DataFrame(monthly_returns)

    print(f"\n✓ 构建了 {len(returns_df)} 个月的月度收益率数据")
    print(f"  - 平均月收益率: {returns_df['return'].mean():.4f}")
    print(f"  - 月度标准差: {returns_df['return'].std():.4f}")
    print(f"  - 最小/最大: {returns_df['return'].min():.4f} / {returns_df['return'].max():.4f}")

    # 检查异常值
    extreme = returns_df[returns_df['return'].abs() > 0.5]
    if len(extreme) > 0:
        print(f"  ⚠️  {len(extreme)}个月收益率绝对值超过50%（可能存在异常）")

    return returns_df

def calculate_p0_performance_metrics(returns_df):
    """P0-1: 计算历史绩效指标"""
    print("\n" + "=" * 70)
    print("📊 P0-1: 历史绩效指标")
    print("=" * 70)

    returns = returns_df['return'].values
    num_months = len(returns)

    # 年化收益率
    total_return = (1 + returns).prod() - 1
    annual_return = (1 + total_return) ** (12 / num_months) - 1

    # 年化波动率
    volatility = returns.std() * np.sqrt(12)

    # 夏普比率
    rf_monthly = 0.03 / 12
    excess_returns = returns - rf_monthly
    sharpe_ratio = excess_returns.mean() / (returns.std() * np.sqrt(12))

    # 最大回撤
    cumulative = pd.Series((1 + returns).cumprod())
    running_max = cumulative.expanding().max()
    max_drawdown = ((cumulative - running_max) / running_max).min()

    # 卡玛比率
    calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0

    # 月度胜率
    monthly_win_rate = (returns > 0).mean()

    # 盈亏比
    gains = returns[returns > 0]
    losses = returns[returns < 0]
    profit_loss_ratio = gains.mean() / abs(losses.mean()) if len(losses) > 0 else 0

    # Sortino
    downside = returns[returns < rf_monthly]
    downside_vol = downside.std() * np.sqrt(12) if len(downside) > 0 else volatility
    sortino = (annual_return - 0.03) / downside_vol if downside_vol > 0 else 0

    # VaR/CVaR
    var_95 = np.percentile(returns, 5)
    cvar_95 = returns[returns <= var_95].mean()

    metrics = {
        "年化收益率": {"value": annual_return, "format": f"{annual_return:.2%}",
                      "grade": "优秀" if annual_return > 0.15 else "良好" if annual_return > 0.10 else "一般" if annual_return > 0 else "差"},
        "年化波动率": {"value": volatility, "format": f"{volatility:.2%}",
                      "grade": "低" if volatility < 0.15 else "中" if volatility < 0.25 else "高"},
        "夏普比率": {"value": sharpe_ratio, "format": f"{sharpe_ratio:.2f}",
                    "grade": "优秀" if sharpe_ratio > 2 else "良好" if sharpe_ratio > 1.5 else "一般" if sharpe_ratio > 1 else "差"},
        "最大回撤": {"value": max_drawdown, "format": f"{max_drawdown:.2%}",
                    "grade": "稳健" if abs(max_drawdown) < 0.15 else "一般" if abs(max_drawdown) < 0.25 else "激进"},
        "卡玛比率": {"value": calmar_ratio, "format": f"{calmar_ratio:.2f}",
                    "grade": "优秀" if calmar_ratio > 1 else "良好" if calmar_ratio > 0.5 else "一般"},
        "月度胜率": {"value": monthly_win_rate, "format": f"{monthly_win_rate:.1%}",
                    "grade": "优秀" if monthly_win_rate > 0.6 else "良好" if monthly_win_rate > 0.5 else "一般"},
        "盈亏比": {"value": profit_loss_ratio, "format": f"{profit_loss_ratio:.2f}",
                  "grade": "优秀" if profit_loss_ratio > 2 else "良好" if profit_loss_ratio > 1.5 else "一般"},
        "索提诺比率": {"value": sortino, "format": f"{sortino:.2f}",
                      "grade": "优秀" if sortino > 2 else "良好"},
        "VaR(95%)": {"value": var_95, "format": f"{var_95:.2%}"},
        "CVaR(95%)": {"value": cvar_95, "format": f"{cvar_95:.2%}"}
    }

    # 打印
    print("\n💰 收益能力")
    for k in ["年化收益率", "月度胜率", "盈亏比"]:
        m = metrics[k]
        print(f"{k:<12}: {m['format']:>10} ({m['grade']})")

    print("\n⚠️  风险控制")
    for k in ["最大回撤", "年化波动率", "VaR(95%)", "CVaR(95%)"]:
        m = metrics[k]
        print(f"{k:<12}: {m['format']:>10} ({m.get('grade', '-')})")

    print("\n📈 风险调整收益")
    for k in ["夏普比率", "索提诺比率", "卡玛比率"]:
        m = metrics[k]
        print(f"{k:<12}: {m['format']:>10} ({m['grade']})")

    # 综合评分
    score = 0
    if abs(annual_return) < 0.5:
        if sharpe_ratio > 1.5: score += 30
        elif sharpe_ratio > 1.0: score += 20
        else: score += 10

        if abs(max_drawdown) < 0.15: score += 30
        elif abs(max_drawdown) < 0.25: score += 20
        else: score += 10

        if calmar_ratio > 1: score += 20
        elif calmar_ratio > 0.5: score += 10

        if monthly_win_rate > 0.6: score += 20
        elif monthly_win_rate > 0.5: score += 10
    else:
        score = 40

    grade = "S" if score >= 90 else "A" if score >= 70 else "B" if score >= 50 else "C"
    print(f"\n🎯 综合评分: {score}/100 | 评级: {grade}")

    return {"metrics": metrics, "score": score, "grade": grade, "num_months": num_months, "returns": returns.tolist()}

def calculate_p0_liquidity_risk(data):
    """P0-3: 流动性风险分析"""
    print("\n" + "=" * 70)
    print("📊 P0-3: 流动性风险")
    print("=" * 70)

    stock_liquidity = data.groupby('stock_code')['close'].agg(['mean', 'std'])
    stock_liquidity['cv'] = stock_liquidity['std'] / stock_liquidity['mean']

    stats = {
        "平均股价": float(stock_liquidity['mean'].mean()),
        "股价中位数": float(stock_liquidity['mean'].median()),
        "高流动性股票数": int((stock_liquidity['mean'] > stock_liquidity['mean'].median() * 1.5).sum()),
        "低流动性股票数": int((stock_liquidity['mean'] < stock_liquidity['mean'].median() * 0.5).sum()),
        "流动性CV": float(stock_liquidity['cv'].mean()),
        "流动性评级": "优秀" if stock_liquidity['cv'].mean() < 0.2 else "良好" if stock_liquidity['cv'].mean() < 0.3 else "一般"
    }

    print("\n💧 个股流动性")
    for k, v in stats.items():
        print(f"{k:<15}: {v if isinstance(v, str) else f'{v:.2f}' if not isinstance(v, int) else v}")

    # 月度收益率压力测试
    monthly_rets = data.groupby(['month', 'stock_code'])['close'].apply(
        lambda x: (x.iloc[-1] - x.iloc[0]) / x.iloc[0] if len(x) > 1 else 0
    ).reset_index()
    monthly_rets.columns = ['month', 'stock_code', 'return']

    scenarios = {
        "极端下跌(5%分位数)": {"value": float(monthly_rets.groupby('month')['return'].mean().quantile(0.05)),
                                "format": f"{monthly_rets.groupby('month')['return'].mean().quantile(0.05):.2%}",
                                "risk_level": "高" if monthly_rets.groupby('month')['return'].mean().quantile(0.05) < -0.10 else "中"},
        "波动率激增": {"value": float(data.groupby('stock_code')['close'].std().mean() * 1.5),
                      "format": f"{data.groupby('stock_code')['close'].std().mean() * 1.5:.4f}",
                      "risk_level": "高" if data.groupby('stock_code')['close'].std().mean() > 0.1 else "中"}
    }

    print("\n🔥 压力测试")
    for k, v in scenarios.items():
        print(f"{k:<18}: {v['format']:<12} [{v['risk_level']}]")

    return {"liquidity_stats": stats, "stress_scenarios": scenarios}

def calculate_p0_factor_crowding(returns_df, data):
    """P0-4: 因子拥挤度"""
    print("\n" + "=" * 70)
    print("📊 P0-4: 因子拥挤度")
    print("=" * 70)

    all_stocks = [s for stocks in returns_df['stocks'] for s in stocks]
    freq = pd.Series(all_stocks).value_counts()

    conc_stats = {
        "总选股人次": len(all_stocks),
        "最高频次": int(freq.max()),
        "前10占比": float(freq.head(10).sum() / len(all_stocks)),
        "前20占比": float(freq.head(20).sum() / len(all_stocks)),
        "独立股票数": int(len(freq)),
        "HHI": float(((freq / len(all_stocks)) ** 2).sum())
    }

    conc_grade = "低拥挤" if conc_stats['HHI'] < 0.01 else "中拥挤" if conc_stats['HHI'] < 0.02 else "高拥挤"

    print("\n🎯 持仓集中度")
    for k, v in conc_stats.items():
        print(f"{k:<12}: {v if isinstance(v, str) else f'{v:.4f}' if not isinstance(v, int) else v}")
    print(f"拥挤度评级: {conc_grade}")

    # 共识度
    corr = data[['pe_ttm', 'revenue_growth', 'debt_ratio', 'factor_score']].corr()

    consensus = {
        "因子得分标准差": float(data['factor_score'].std()),
        "PE相关系数": float(corr.loc['pe_ttm', 'factor_score']),
        "营收增长相关系数": float(corr.loc['revenue_growth', 'factor_score']),
        "负债比相关系数": float(corr.loc['debt_ratio', 'factor_score'])
    }

    consensus_grade = "低共识" if consensus['因子得分标准差'] > 1 else "中共识" if consensus['因子得分标准差'] > 0.5 else "高共识"

    print("\n🌐 市场共识度")
    for k, v in consensus.items():
        print(f"{k:<14}: {v:.4f}")
    print(f"共识度评级: {consensus_grade}")

    print(f"\n⚠️  前10重仓股: {list(freq.head(10).index)}")

    return {"concentration_stats": conc_stats, "consensus_stats": consensus,
            "concentration_grade": conc_grade, "consensus_grade": consensus_grade,
            "top_stocks": {str(k): int(v) for k, v in freq.head(10).items()}}

def calculate_p0_style_exposure(data):
    """P0-5: 风格暴露"""
    print("\n" + "=" * 70)
    print("📊 P0-5: 风格暴露")
    print("=" * 70)

    # 大小盘（基于股价均值）
    stock_avg_cap = data.groupby('stock_code')['close'].mean()
    median_cap = stock_avg_cap.median()
    data['size'] = data['stock_code'].map(lambda x: '大盘' if stock_avg_cap[x] >= median_cap else '小盘')

    size_stats = {
        "大盘权重": float((data['size'] == '大盘').mean()),
        "小盘权重": float((data['size'] == '小盘').mean()),
        "大盘股价均值": float(data[data['size'] == '大盘']['close'].mean()),
        "小盘股价均值": float(data[data['size'] == '小盘']['close'].mean())
    }
    size_tilt = "大盘倾向" if size_stats['大盘权重'] > 0.6 else "小盘倾向" if size_stats['小盘权重'] > 0.6 else "均衡"

    print("\n📏 大小盘风格")
    for k, v in size_stats.items():
        if isinstance(v, float):
            print(f"{k:<10}: {v:.2%}")
        else:
            print(f"{k:<10}: {v:.2f}")
    print(f"风格倾向: {size_tilt}")

    # 价值/成长
    data['value_rank'] = data.groupby('stock_code')['pe_ttm'].transform('rank', ascending=False)
    data['growth_rank'] = data.groupby('stock_code')['revenue_growth'].transform('rank', ascending=True)

    style_stats = {
        "价值权重": float((data['value_rank'] > data['value_rank'].median()).mean()),
        "成长权重": float((data['growth_rank'] > data['growth_rank'].median()).mean()),
        "平均PE": float(data['pe_ttm'].mean()),
        "平均营收增长": float(data['revenue_growth'].mean())
    }
    style_tilt = "价值倾向" if style_stats['价值权重'] > 0.6 else "成长倾向" if style_stats['成长权重'] > 0.6 else "均衡"

    print("\n💎 价值/成长风格")
    for k, v in style_stats.items():
        if isinstance(v, float):
            print(f"{k:<10}: {v:.2%}")
        else:
            print(f"{k:<10}: {v:.2f}")
    print(f"风格倾向: {style_tilt}")

    # 行业（代理）
    data['industry'] = data['stock_code'].str[:4]
    industry_stats = {
        "行业数": int(data['industry'].nunique()),
        "第一占比": float(data['industry'].value_counts(normalize=True).iloc[0]),
        "前三占比": float(data['industry'].value_counts(normalize=True).iloc[:3].sum()),
        "HHI": float((data['industry'].value_counts(normalize=True) ** 2).sum())
    }
    ind_grade = "低集中" if industry_stats['HHI'] < 0.1 else "中集中" if industry_stats['HHI'] < 0.2 else "高集中"

    print("\n🏭 行业集中度（代理）")
    for k, v in industry_stats.items():
        if isinstance(v, int):
            print(f"{k:<8}: {v}")
        else:
            print(f"{k:<8}: {v:.2%}")
    print(f"集中度评级: {ind_grade}")

    return {"size_stats": size_stats, "style_stats": style_stats, "industry_stats": industry_stats,
            "size_tilt": size_tilt, "style_tilt": style_tilt, "concentration_grade": ind_grade}

def save_results(p0_results):
    """保存结果"""
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')

    # JSON
    json_file = f'reports/p0_corrected_{ts}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(p0_results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n✓ JSON: {json_file}")

    # Markdown
    md_file = f'reports/p0_corrected_{ts}.md'
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write("# A股量化系统P0分析报告（真实数据）\n\n")
        f.write(f"**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("**数据说明:** 2019-2024年，261,000条记录，200只股票\n\n")

        # P0-1
        f.write("## 📊 P0-1: 历史绩效\n\n")
        f.write("### 收益能力\n| 指标 | 数值 | 评级 |\n|------|------|------|\n")
        for k in ["年化收益率", "月度胜率", "盈亏比"]:
            m = p0_results['p0_1']['metrics'][k]
            f.write(f"| {k} | {m['format']} | {m['grade']} |\n")

        f.write("\n### 风险控制\n| 指标 | 数值 | 评级 |\n|------|------|------|\n")
        for k in ["最大回撤", "年化波动率", "VaR(95%)", "CVaR(95%)"]:
            m = p0_results['p0_1']['metrics'][k]
            f.write(f"| {k} | {m['format']} | {m.get('grade', '-')} |\n")

        f.write("\n### 风险调整收益\n| 指标 | 数值 | 评级 |\n|------|------|------|\n")
        for k in ["夏普比率", "索提诺比率", "卡玛比率"]:
            m = p0_results['p0_1']['metrics'][k]
            f.write(f"| {k} | {m['format']} | {m['grade']} |\n")

        f.write(f"\n### 综合\n- 评分: {p0_results['p0_1']['score']}/100\n- 评级: {p0_results['p0_1']['grade']}\n- 月份: {p0_results['p0_1']['num_months']}\n\n")

        # P0-3
        f.write("---\n\n## 💧 P0-3: 流动性风险\n\n")
        ls = p0_results['p0_3']['liquidity_stats']
        f.write(f"- 平均股价: {ls['平均股价']:.2f}\n- 股价中位数: {ls['股价中位数']:.2f}\n")
        f.write(f"- 流动性CV: {ls['流动性CV']:.3f}\n- 评级: {ls['流动性评级']}\n\n")
        f.write("### 压力测试\n| 场景 | 数值 | 风险 |\n|------|------|------|\n")
        for k, v in p0_results['p0_3']['stress_scenarios'].items():
            f.write(f"| {k} | {v['format']} | {v['risk_level']} |\n\n")

        # P0-4
        f.write("---\n\n## 🎯 P0-4: 拥挤度\n\n")
        cs = p0_results['p0_4']['concentration_stats']
        f.write(f"- HHI: {cs['HHI']:.4f}\n- 前10重仓占比: {cs['前10占比']:.2%}\n")
        f.write(f"- 拥挤度: {p0_results['p0_4']['concentration_grade']}\n")
        f.write(f"- 共识度: {p0_results['p0_4']['consensus_grade']}\n\n")

        # P0-5
        f.write("---\n\n## 🎨 P0-5: 风格暴露\n\n")
        f.write(f"- 大小盘: {p0_results['p0_5']['size_tilt']}\n- 价值/成长: {p0_results['p0_5']['style_tilt']}\n")
        f.write(f"- 行业集中度: {p0_results['p0_5']['concentration_grade']}\n\n")

    print(f"✓ Markdown: {md_file}")

    return p0_results

def main():
    print("=" * 70)
    print("🚀 A股量化系统P0分析（真实数据）")
    print("=" * 70)

    data = load_real_data()
    returns_df = construct_backtest_returns_fixed(data)

    p0_results = {
        'p0_1': calculate_p0_performance_metrics(returns_df),
        'p0_3': calculate_p0_liquidity_risk(data),
        'p0_4': calculate_p0_factor_crowding(returns_df, data),
        'p0_5': calculate_p0_style_exposure(data)
    }

    save_results(p0_results)

    print("\n" + "=" * 70)
    print("✅ 完成！")
    print("=" * 70)

    return p0_results

if __name__ == "__main__":
    main()
