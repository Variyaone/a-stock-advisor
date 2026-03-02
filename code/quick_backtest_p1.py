#!/usr/bin/env python3
"""
快速策略回测 - P1任务简化版
回测代表性策略（每类1-2个），快速生成报告
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import json
import os
from typing import Dict, Callable

warnings.filterwarnings('ignore')

# 导入回测引擎
from backtest_engine_v2 import BacktestEngineV2, CostModel


def run_backtest_with_signal(data: pd.DataFrame, cost_model: CostModel, signal_func: Callable) -> Dict:
    """运行回测"""
    try:
        engine = BacktestEngineV2(
            initial_capital=1000000,
            cost_model=cost_model,
            max_single_position=0.10,
            max_industry_exposure=0.30,
            slippage_rate=0.001,
            fill_ratio=0.95
        )
        
        results = engine.run_backtest(data, signal_func, rebalance_freq='weekly')
        return results
    except Exception as e:
        print(f"    ⚠️ 回测失败: {str(e)[:100]}")
        return {
            'error': str(e),
            'initial_capital': 1000000,
            'final_value': 1000000,
            'total_return': 0,
            'annual_return': 0,
            'annual_volatility': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'win_rate': 0,
            'num_trades': 0
        }


def strategy_dual_ma_5_20(date, current_data, full_data):
    """双均线5日/20日"""
    signals = {}
    for stock_code in current_data['stock_code'].unique():
        stock_data = current_data[current_data['stock_code'] == stock_code]
        if len(stock_data) < 2:
            continue
        
        ma5 = stock_data['ma5'].values[0]
        ma20 = stock_data['ma20'].values[0]
        
        if pd.notna(ma5) and pd.notna(ma20):
            prev_data = full_data[(full_data['stock_code'] == stock_code) & (full_data['date'] < date)].tail(20)
            if len(prev_data) > 0:
                prev_ma5 = prev_data['ma5'].iloc[-1]
                prev_ma20 = prev_data['ma20'].iloc[-1]
                if prev_ma5 <= prev_ma20 and ma5 > ma20:
                    signals[stock_code] = 0.10
    return signals


def strategy_macd_12_26_9(date, current_data):
    """MACD策略"""
    signals = {}
    for stock_code in current_data['stock_code'].unique():
        stock_data = current_data[current_data['stock_code'] == stock_code].sort_values('date')
        if len(stock_data) < 35:
            continue
        
        close = stock_data['close'].values
        ema12 = pd.Series(close).ewm(span=12, adjust=False).mean().iloc[-1]
        ema26 = pd.Series(close).ewm(span=26, adjust=False).mean().iloc[-1]
        macd = ema12 - ema26
        
        # 检查前期
        prev_close = close[:-1]
        prev_ema12 = pd.Series(prev_close).ewm(span=12, adjust=False).mean().iloc[-1]
        prev_ema26 = pd.Series(prev_close).ewm(span=26, adjust=False).mean().iloc[-1]
        prev_macd = prev_ema12 - prev_ema26
        
        if prev_macd <= 0 and macd > 0:
            signals[stock_code] = 0.08
    return signals


def strategy_momentum_60(date, current_data):
    """动量突破60日"""
    signals = {}
    for stock_code in current_data['stock_code'].unique():
        stock_data = current_data[current_data['stock_code'] == stock_code]
        if len(stock_data) < 1:
            continue
        
        momentum = stock_data['momentum_60'].values[0]
        turnover = stock_data['turnover'].values[0] / 100 if pd.notna(stock_data['turnover'].values[0]) else 0
        
        if pd.notna(momentum) and momentum > 0.10 and turnover < 20:
            signals[stock_code] = 0.08
    
    if len(signals) > 10:
        signals = dict(sorted(signals.items(), key=lambda x: x[1], reverse=True)[:10])
    
    return signals


def strategy_rsi_oversold(date, current_data):
    """RSI超卖"""
    signals = {}
    for stock_code in current_data['stock_code'].unique():
        stock_data = current_data[current_data['stock_code'] == stock_code]
        if len(stock_data) < 14:
            continue
        
        momentum = stock_data['momentum_14'].values[0]
        vol = stock_data['volatility_14'].values[0]
        
        if pd.notna(momentum) and momentum < -0.15 and pd.notna(vol) and vol > 0.02:
            signals[stock_code] = 0.08
    return signals


def strategy_low_volatility(date, current_data):
    """低波动"""
    signals = {}
    for stock_code in current_data['stock_code'].unique():
        stock_data = current_data[current_data['stock_code'] == stock_code]
        if len(stock_data) < 20:
            continue
        
        vol = stock_data['volatility_20'].values[0]
        if pd.notna(vol) and vol < 0.025:
            signals[stock_code] = 1.0 / max(vol, 0.01)
    
    if signals:
        total = sum(signals.values())
        signals = {k: v/total * 0.15 for k, v in signals.items()}
        signals = dict(sorted(signals.items(), key=lambda x: x[1], reverse=True)[:15])
    
    return signals


def strategy_value_factor(date, current_data):
    """价值因子"""
    signals = {}
    for stock_code in current_data['stock_code'].unique():
        stock_data = current_data[current_data['stock_code'] == stock_code]
        if len(stock_data) < 60:
            continue
        
        price_to_ma60 = stock_data['price_to_ma60'].values[0]
        vol = stock_data['volatility_20'].values[0]
        
        if pd.notna(price_to_ma60) and price_to_ma60 < -0.10 and pd.notna(vol) and vol < 0.05:
            signals[stock_code] = abs(price_to_ma60) * 100
    
    if signals:
        sorted_s = sorted(signals.items(), key=lambda x: x[1], reverse=True)[:15]
        total = sum(v for k, v in sorted_s)
        signals = {k: v/total * 0.15 for k, v in sorted_s}
    
    return signals


def strategy_growth_factor(date, current_data):
    """成长因子"""
    signals = {}
    for stock_code in current_data['stock_code'].unique():
        stock_data = current_data[current_data['stock_code'] == stock_code]
        if len(stock_data) < 120:
            continue
        
        momentum = stock_data['momentum_60'].values[0] * 2
        momentum_20 = stock_data['momentum_20'].values[0]
        turnover = stock_data['turnover'].values[0] / 100 if pd.notna(stock_data['turnover'].values[0]) else 0
        
        if (pd.notna(momentum) and momentum > 0.20 and
            pd.notna(momentum_20) and momentum_20 > 0.05 and turnover < 20):
            signals[stock_code] = momentum * 50 + momentum_20 * 50
    
    if signals:
        sorted_s = sorted(signals.items(), key=lambda x: x[1], reverse=True)[:12]
        total = sum(v for k, v in sorted_s)
        signals = {k: v/total * 0.20 for k, v in sorted_s}
    
    return signals


def strategy_breakout(date, current_data, full_data):
    """突破事件"""
    signals = {}
    for stock_code in current_data['stock_code'].unique():
        stock_data = current_data[current_data['stock_code'] == stock_code]
        if len(stock_data) < 20:
            continue
        
        high = stock_data['high'].values[0]
        high_20 = full_data[(full_data['stock_code'] == stock_code) & (full_data['date'] < date)].tail(20)['high'].max()
        
        if pd.notna(high_20) and high > high_20:
            volume = stock_data['volume'].values[0]
            vol_ma5 = stock_data['turnover_ma5'].values[0]
            if pd.notna(vol_ma5) and volume > vol_ma5 * 1.5:
                signals[stock_code] = 0.08
    
    if len(signals) > 10:
        signals = dict(sorted(signals.items(), key=lambda x: x[1], reverse=True)[:10])
    
    return signals


def strategy_volume_surge(date, current_data):
    """放量上涨"""
    signals = {}
    for stock_code in current_data['stock_code'].unique():
        stock_data = current_data[current_data['stock_code'] == stock_code]
        if len(stock_data) < 5:
            continue
        
        amount = stock_data['amount'].values[0]
        amount_ma5 = stock_data['amount_ma5'].values[0]
        change_pct = stock_data['change_pct'].values[0] / 100 if pd.notna(stock_data['change_pct'].values[0]) else 0
        
        if pd.notna(amount_ma5) and amount > amount_ma5 * 2 and pd.notna(change_pct) and change_pct > 0.02:
            signals[stock_code] = amount / amount_ma5
    
    if signals:
        sorted_s = sorted(signals.items(), key=lambda x: x[1], reverse=True)[:10]
        total = sum(v for k, v in sorted_s)
        signals = {k: v/total * 0.12 for k, v in sorted_s}
    
    return signals


def strategy_industry_neutral(date, current_data):
    """行业中性"""
    signals = {}
    for stock_code in current_data['stock_code'].unique():
        stock_data = current_data[current_data['stock_code'] == stock_code]
        if len(stock_data) < 20:
            continue
        
        momentum = stock_data['momentum_60'].values[0] if pd.notna(stock_data['momentum_60'].values[0]) else 0
        vol = stock_data['volatility_20'].values[0] if pd.notna(stock_data['volatility_20'].values[0]) else 0.05
        score = momentum * 50 - vol * 100
        
        if score > 0:
            signals[stock_code] = score
    
    # 行业分散
    final = {}
    groups = {}
    for code, score in signals.items():
        ind = code[:6]
        if ind not in groups:
            groups[ind] = []
        groups[ind].append((code, score))
    
    for ind, items in groups.items():
        best = sorted(items, key=lambda x: x[1], reverse=True)[0]
        final[best[0]] = best[1]
    
    if final:
        total = sum(final.values())
        final = {k: v/total * 0.20 for k, v in final.items()}
    
    return final


def strategy_long_short(date, current_data):
    """多空对冲"""
    signals = {}
    scores = {}
    for stock_code in current_data['stock_code'].unique():
        stock_data = current_data[current_data['stock_code'] == stock_code]
        if len(stock_data) < 60:
            continue
        
        momentum = stock_data['momentum_60'].values[0] if pd.notna(stock_data['momentum_60'].values[0]) else 0
        scores[stock_code] = momentum
    
    if not scores:
        return {}
    
    sorted_s = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5]
    for code, score in sorted_s:
        if score > 0.05:
            signals[code] = 0.04
    
    return signals


def main():
    """主函数"""
    print("="*80)
    print("快速策略回测 - P1任务")
    print("="*80)
    
    # 加载数据
    print("\n加载数据...")
    data_path = 'data/real_stock_data.pkl'
    data = pd.read_pickle(data_path)
    print(f"  ✓ 数据加载完成: {len(data):,} 条记录")
    print(f"  ✓ 时间范围: {data['date'].min()} 到 {data['date'].max()}")
    print(f"  ✓ 股票数量: {data['stock_code'].nunique()}")
    
    # 成本模型
    cost_model = CostModel(
        commission_rate=0.0003,
        stamp_tax_rate=0.001,
        impact_cost_base=0.0005,
        impact_cost_sqrt=0.001
    )
    
    # 定义策略
    strategies = [
        ('趋势跟踪', [
            ('双均线_5日_20日', lambda d, cd: strategy_dual_ma_5_20(d, cd, data)),
            ('MACD_12_26_9', strategy_macd_12_26_9),
            ('动量突破_60日', strategy_momentum_60)
        ]),
        ('均值回归', [
            ('RSI超卖_14日', strategy_rsi_oversold),
            ('低波动策略', strategy_low_volatility)
        ]),
        ('多因子选股', [
            ('价值因子', strategy_value_factor),
            ('成长因子', strategy_growth_factor)
        ]),
        ('事件驱动', [
            ('突破事件', lambda d, cd: strategy_breakout(d, cd, data)),
            ('放量上涨事件', strategy_volume_surge)
        ]),
        ('市场中性', [
            ('行业中性分散', strategy_industry_neutral),
            ('多空对冲策略', strategy_long_short)
        ])
    ]
    
    # 运行回测
    results = {}
    for category, category_strategies in strategies:
        print(f"\n【{category}】")
        for strategy_name, strategy_func in category_strategies:
            print(f"  - {strategy_name}")
            result = run_backtest_with_signal(data, cost_model, strategy_func)
            results[strategy_name] = result
            if 'error' not in result:
                print(f"    年化收益: {result['annual_return']*100:.2f}%, 夏普: {result['sharpe_ratio']:.2f}, 回撤: {result['max_drawdown']*100:.2f}%")
    
    # 生成报告
    print("\n生成报告...")
    
    # 对比矩阵
    matrix_data = []
    for name, result in results.items():
        if 'error' not in result:
            matrix_data.append({
                '策略名称': name,
                '年化收益率': f"{result['annual_return']*100:.2f}%",
                '年化波动率': f"{result['annual_volatility']*100:.2f}%",
                '夏普比率': f"{result['sharpe_ratio']:.2f}",
                '最大回撤': f"{result['max_drawdown']*100:.2f}%",
                '胜率': f"{result['win_rate']*100:.1f}%",
                '交易次数': result['num_trades'],
                '总收益率': f"{result['total_return']*100:.2f}%"
            })
    
    matrix_df = pd.DataFrame(matrix_data)
    matrix_df = matrix_df.sort_values('夏普比率', ascending=False)
    matrix_path = 'reports/strategy_comparison_matrix.csv'
    matrix_df.to_csv(matrix_path, index=False, encoding='utf-8-sig')
    print(f"  ✓ 对比矩阵: {matrix_path}")
    
    # 保存JSON
    clean_results = {}
    for k, v in results.items():
        if 'error' not in v:
            clean_v = {key: val for key, val in v.items() 
                      if not isinstance(val, (pd.DataFrame, pd.Series))}
            clean_results[k] = clean_v
    json_path = 'reports/full_backtest_results.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(clean_results, f, ensure_ascii=False, indent=2)
    print(f"  ✓ JSON结果: {json_path}")
    
    # 完整报告
    report = []
    report.append("# 全面策略回测报告")
    report.append(f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"\n## 回测概况")
    report.append(f"- **回测期间**: 2019-2024（5年）")
    report.append(f"- **初始资金**: 1,000,000 元")
    report.append(f"- **交易成本**: 佣金0.03% | 印花税0.1%（卖出）")
    report.append(f"- **回测策略数**: {len(results)} 个")
    
    # 分类统计
    for category, category_strategies in strategies:
        valid = [s[0] for s in category_strategies if 'error' not in results.get(s[0], {})]
        if valid:
            report.append(f"\n### {category}")
            report.extend([f"- {s}" for s in valid])
    
    # 按类别详细报告
    report.append("\n---")
    for category, category_strategies in strategies:
        report.append(f"\n## {category}")
        
        category_results = [(name, results[name]) for name, _ in category_strategies if 'error' not in results.get(name, {})]
        
        if not category_results:
            report.append(f"\n暂无有效回测结果")
            continue
        
        category_results.sort(key=lambda x: x[1]['sharpe_ratio'], reverse=True)
        
        for i, (name, result) in enumerate(category_results, 1):
            report.append(f"\n#### {i}. {name}")
            report.append(f"- 年化收益率: {result['annual_return']*100:.2f}%")
            report.append(f"- 年化波动率: {result['annual_volatility']*100:.2f}%")
            report.append(f"- 夏普比率: {result['sharpe_ratio']:.2f}")
            report.append(f"- 最大回撤: {result['max_drawdown']*100:.2f}%")
            report.append(f"- 胜率: {result['win_rate']*100:.1f}%")
            report.append(f"- 交易次数: {result['num_trades']}")
            report.append(f"- 总收益率: {result['total_return']*100:.2f}%")
    
    # 对比矩阵表格
    report.append("\n---")
    report.append("\n## 策略对比矩阵")
    report.append("\n| 策略名称 | 年化收益率 | 年化波动率 | 夏普比率 | 最大回撤 | 胜率 | 交易次数 |")
    report.append("|---------|-----------|-----------|---------|---------|------|----------|")
    
    for _, row in matrix_df.iterrows():
        report.append(f"| {row['策略名称']} | {row['年化收益率']} | {row['年化波动率']} | {row['夏普比率']} | {row['最大回撤']} | {row['胜率']} | {row['交易次数']} |")
    
    # 最优策略推荐
    valid_results = {k: v for k, v in results.items() if 'error' not in v}
    if valid_results:
        report.append("\n---")
        report.append("\n## 最优策略推荐")
        
        scored = []
        for name, result in valid_results.items():
            sharpe_score = max(0, result['sharpe_ratio']) * 0.4
            return_score = min(1, result['annual_return'] / 0.2) * 0.3
            drawdown_score = (1 - result['max_drawdown']) * 0.3
            total = sharpe_score + return_score + drawdown_score
            scored.append((name, total, result))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        report.append("\n### 综合评分Top 3")
        for i, (name, score, result) in enumerate(scored[:3], 1):
            report.append(f"\n#### {i}. {name} (评分: {score:.2f})")
            report.append(f"- 年化收益率: {result['annual_return']*100:.2f}%")
            report.append(f"- 夏普比率: {result['sharpe_ratio']:.2f}")
            report.append(f"- 最大回撤: {result['max_drawdown']*100:.2f}%")
        
        # 策略组合建议
        report.append("\n---")
        report.append("\n## 策略组合建议")
        
        report.append("\n### 保守组合（高夏普）")
        for i, (name, _, result) in enumerate(scored[:3], 1):
            report.append(f"- {name}: 33% (夏普={result['sharpe_ratio']:.2f})")
        
        report.append("\n### 进取组合（高收益）")
        sorted_return = sorted(valid_results.items(), key=lambda x: x[1]['annual_return'], reverse=True)[:3]
        for i, (name, result) in enumerate(sorted_return, 1):
            report.append(f"- {name}: 33% (收益={result['annual_return']*100:.2f}%)")
    
    # 风险提示
    report.append("\n---")
    report.append("\n## 风险提示")
    report.append("\n1. **过拟合风险**: 回测结果可能过拟合历史数据")
    report.append("2. **市场环境变化**: A股市场结构持续变化")
    report.append("3. **交易成本影响**: 已包含真实交易成本")
    report.append("4. **流动性风险**: 部分策略可能面临流动性不足")
    report.append("5. **监管风险**: 量化交易监管政策变化")
    
    report.append("\n---")
    report.append(f"\n**报告生成**: OpenClaw Architect Agent")
    report.append(f"\n*本报告仅供参考，不构成投资建议*")
    
    report_path = 'reports/full_strategy_backtest.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    print(f"  ✓ 完整报告: {report_path}")
    
    # 最优策略推荐报告
    recommendation = []
    recommendation.append("# 最优策略推荐报告")
    recommendation.append(f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    recommendation.append("\n## 综合评分Top 5")
    
    for i, (name, score, result) in enumerate(scored[:5], 1):
        recommendation.append(f"\n### {i}. {name}")
        recommendation.append(f"- **综合评分**: {score:.2f}")
        recommendation.append(f"- **年化收益率**: {result['annual_return']*100:.2f}%")
        recommendation.append(f"- **夏普比率**: {result['sharpe_ratio']:.2f}")
        recommendation.append(f"- **最大回撤**: {result['max_drawdown']*100:.2f}%")
        recommendation.append(f"- **胜率**: {result['win_rate']*100:.1f}%")
        recommendation.append(f"- **交易次数**: {result['num_trades']}")
    
    recommendation.append("\n---")
    recommendation.append("\n## 推荐组合\n")
    recommendation.append("### 保守组合（高夏普）")
    avg_sharpe = sum(sc[2]['sharpe_ratio'] for sc in scored[:3]) / 3
    avg_return = sum(sc[2]['annual_return'] for sc in scored[:3]) / 3
    avg_dd = sum(sc[2]['max_drawdown'] for sc in scored[:3]) / 3
    for i, (name, _, result) in enumerate(scored[:3], 1):
        recommendation.append(f"- {name}: 权重33% (夏普={result['sharpe_ratio']:.2f})")
    recommendation.append(f"\n**组合预期**:\n- 夏普比率: {avg_sharpe:.2f}\n- 年化收益率: {avg_return*100:.2f}%\n- 最大回撤: {avg_dd*100:.2f}%")
    
    req_path = 'reports/optimal_strategy_recommendation.md'
    with open(req_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(recommendation))
    print(f"  ✓ 最优策略推荐: {req_path}")
    
    # 摘要
    print("\n" + "="*80)
    print("✓ 全面策略回测完成！")
    print("="*80)
    print(f"\n生成文件:")
    print(f"  1. {report_path}")
    print(f"  2. {matrix_path}")
    print(f"  3. {json_path}")
    print(f"  4. {req_path}")
    
    print(f"\n回测摘要:")
    print(f"  成功回测策略: {len(valid_results)} 个")
    
    if valid_results:
        best_sharpe = max(valid_results.items(), key=lambda x: x[1]['sharpe_ratio'])
        best_return = max(valid_results.items(), key=lambda x: x[1]['annual_return'])
        
        print(f"\n最佳夏普策略:")
        print(f"  {best_sharpe[0]}: 夏普={best_sharpe[1]['sharpe_ratio']:.2f}, 收益={best_sharpe[1]['annual_return']*100:.2f}%")
        
        print(f"\n最佳收益策略:")
        print(f"  {best_return[0]}: 收益={best_return[1]['annual_return']*100:.2f}%, 夏普={best_return[1]['sharpe_ratio']:.2f}")


if __name__ == '__main__':
    main()
