        # 更新仓位市值
        for stock_code, pos in self.portfolio.positions.items():
            stock_data = price_df[price_df['stock_code'] == stock_code]
            if len(stock_data) > 0:
                pos.market_value = pos.quantity * stock_data['close'].values[0]
            else:
                pos.market_value = pos.quantity * pos.avg_price

class StrategyReportGenerator:
    """策略报告生成器"""
    
    def __init__(self, results: Dict, reports_dir: str = 'reports'):
        self.results = results
        self.reports_dir = reports_dir
        
    def generate_comparison_matrix(self) -> pd.DataFrame:
        """生成策略对比矩阵"""
        print("生成策略对比矩阵...")
        
        matrix_data = []
        for strategy_name, result in self.results.items():
            if 'error' in result:
                continue
            
            matrix_data.append({
                '策略名称': strategy_name,
                '年化收益率': f"{result.get('annual_return', 0)*100:.2f}%",
                '年化波动率': f"{result.get('annual_volatility', 0)*100:.2f}%",
                '夏普比率': f"{result.get('sharpe_ratio', 0):.2f}",
                '最大回撤': f"{result.get('max_drawdown', 0)*100:.2f}%",
                '胜率': f"{result.get('win_rate', 0)*100:.1f}%",
                '交易次数': result.get('num_trades', 0),
                '总收益率': f"{result.get('total_return', 0)*100:.2f}%"
            })
        
        df = pd.DataFrame(matrix_data)
        df = df.sort_values('夏普比率', ascending=False)
        
        return df
    
    def generate_full_report(self) -> str:
        """生成完整回测报告"""
        print("生成完整回测报告...")
        
        report = []
        report.append("# 全面策略回测报告")
        report.append(f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"\n## 回测概况")
        report.append(f"- **回测期间**: 2019-2024（5年）")
        report.append(f"- **初始资金**: 1,000,000 元")
        report.append(f"- **交易成本**: 佣金0.03% | 印花税0.1%（卖出）")
        report.append(f"- **策略总数**: {len(self.results)} 个")
        
        # 分类统计
        categories = {
            '趋势跟踪': [k for k in self.results.keys() if any(x in k for x in ['双均线', 'MACD', '动量突破', '布林带突破'])],
            '均值回归': [k for k in self.results.keys() if any(x in k for x in ['RSI', '均值回归', '偏离度', '低波动', '布林带均值回归'])],
            '多因子选股': [k for k in self.results.keys() if any(x in k for x in ['因子', '价值', '成长'])],
            '事件驱动': [k for k in self.results.keys() if any(x in k for x in ['事件'])],
            '市场中性': [k for k in self.results.keys() if any(x in k for x in ['中性', '对冲'])]
        }
        
        report.append(f"\n## 策略分类")
        for category, strategies in categories.items():
            valid_strategies = [s for s in strategies if 'error' not in self.results.get(s, {})]
            report.append(f"- **{category}**: {len(valid_strategies)} 个策略")
        
        # 按类别详细报告
        report.append("\n---")
        for category, strategies in categories.items():
            report.append(f"\n## {category}")
            
            category_results = []
            for strategy in strategies:
                if strategy in self.results and 'error' not in self.results[strategy]:
                    result = self.results[strategy]
                    category_results.append((strategy, result))
            
            if not category_results:
                report.append(f"\n暂无有效回测结果")
                continue
            
            # 按夏普比率排序
            category_results.sort(key=lambda x: x[1].get('sharpe_ratio', 0), reverse=True)
            
            # Top 3 策略
            report.append(f"\n### Top 3 策略（按夏普比率）")
            for i, (strategy, result) in enumerate(category_results[:3], 1):
                report.append(f"\n#### {i}. {strategy}")
                report.append(f"- 年化收益率: {result['annual_return']*100:.2f}%")
                report.append(f"- 年化波动率: {result['annual_volatility']*100:.2f}%")
                report.append(f"- 夏普比率: {result['sharpe_ratio']:.2f}")
                report.append(f"- 最大回撤: {result['max_drawdown']*100:.2f}%")
                report.append(f"- 胜率: {result['win_rate']*100:.1f}%")
                report.append(f"- 交易次数: {result['num_trades']}")
                report.append(f"- 总收益率: {result['total_return']*100:.2f}%")
        
        # 风险收益散点图数据
        report.append("\n---")
        report.append("\n## 风险收益分析")
        
        scatter_data = []
        for strategy, result in self.results.items():
            if 'error' not in result:
                scatter_data.append({
                    '策略': strategy,
                    '年化收益率': result['annual_return'] * 100,
                    '夏普比率': result['sharpe_ratio']
                })
        
        scatter_df = pd.DataFrame(scatter_data)
        if len(scatter_df) > 0:
            report.append("\n### 高夏普策略（夏普比率 > 1.0）")
            high_sharpe = scatter_df[scatter_df['夏普比率'] > 1.0].sort_values('夏普比率', ascending=False)
            for _, row in high_sharpe.iterrows():
                report.append(f"- **{row['策略']}**: 收益率={row['年化收益率']:.2f}%, 夏普={row['夏普比率']:.2f}")
            
            report.append("\n### 高收益策略（年化收益率 > 10%）")
            high_return = scatter_df[scatter_df['年化收益率'] > 10].sort_values('年化收益率', ascending=False)
            for _, row in high_return.iterrows():
                report.append(f"- **{row['策略']}**: 收益率={row['年化收益率']:.2f}%, 夏普={row['夏普比率']:.2f}")
        
        # 最优策略推荐
        report.append("\n---")
        report.append("\n## 最优策略推荐")
        
        # 综合评分
        valid_results = {k: v for k, v in self.results.items() if 'error' not in v}
        if valid_results:
            scored_strategies = []
            for strategy, result in valid_results.items():
                # 综合评分 = 夏普*0.4 + (年化收益/20)*0.3 + (1-最大回撤)*0.3
                sharpe_score = max(0, result['sharpe_ratio']) * 0.4
                return_score = min(1, result['annual_return'] / 0.2) * 0.3  # 20%封顶
                drawdown_score = (1 - result['max_drawdown']) * 0.3
                
                total_score = sharpe_score + return_score + drawdown_score
                scored_strategies.append((strategy, total_score, result))
            
            scored_strategies.sort(key=lambda x: x[1], reverse=True)
            
            report.append("\n### 综合评分Top 5")
            for i, (strategy, score, result) in enumerate(scored_strategies[:5], 1):
                report.append(f"\n#### {i}. {strategy} (评分: {score:.2f})")
                report.append(f"- 年化收益率: {result['annual_return']*100:.2f}%")
                report.append(f"- 夏普比率: {result['sharpe_ratio']:.2f}")
                report.append(f"- 最大回撤: {result['max_drawdown']*100:.2f}%")
        
        # 策略组合建议
        report.append("\n---")
        report.append("\n## 策略组合建议")
        
        if valid_results:
            # 按类别选择最优
            category_best = {}
            for category, strategies in categories.items():
                category_valid = {s: valid_results[s] for s in strategies if s in valid_results}
                if category_valid:
                    best = max(category_valid.items(), key=lambda x: x[1]['sharpe_ratio'])
                    category_best[category] = best
            
            report.append("\n### 各类别最优策略")
            for category, (strategy, result) in category_best.items():
                report.append(f"- **{category}**: {strategy} (夏普={result['sharpe_ratio']:.2f})")
            
            report.append("\n### 推荐组合")
            
            # 保守组合：高夏普
            high_sharpe_strategies = sorted(valid_results.items(), 
                                           key=lambda x: x[1]['sharpe_ratio'], 
                                           reverse=True)[:3]
            report.append("\n#### 保守组合（高夏普）")
            for strategy, result in high_sharpe_strategies:
                report.append(f"- {strategy}: 30% (夏普={result['sharpe_ratio']:.2f})")
            
            # 进取组合：高收益
            high_return_strategies = sorted(valid_results.items(), 
                                           key=lambda x: x[1]['annual_return'], 
                                           reverse=True)[:3]
            report.append("\n#### 进取组合（高收益）")
            for strategy, result in high_return_strategies:
                report.append(f"- {strategy}: 30% (收益={result['annual_return']*100:.2f}%)")
        
        # 风险提示
        report.append("\n---")
        report.append("\n## 风险提示")
        report.append("\n1. **过拟合风险**: 回测结果可能过拟合历史数据，实战表现可能不同")
        report.append("2. **市场环境变化**: A股市场结构持续变化，历史策略效果有待验证")
        report.append("3. **交易成本影响**: 本回测已包含真实交易成本，但仍需考虑滑点等额外成本")
        report.append("4. **流动性风险**: 部分策略在实战中可能面临流动性不足的问题")
        report.append("5. **监管风险**: 量化交易监管政策变化可能影响策略有效性")
        
        report.append("\n---")
        report.append(f"\n**报告生成**: OpenClaw Architect Agent")
        report.append(f"\n*本报告仅供参考，不构成投资建议*")
        
        return '\n'.join(report)
    
    def save_reports(self):
        """保存报告"""
        print("\n保存报告...")
        
        # 保存对比矩阵
        matrix_df = self.generate_comparison_matrix()
        matrix_path = os.path.join(self.reports_dir, 'strategy_comparison_matrix.csv')
        matrix_df.to_csv(matrix_path, index=False, encoding='utf-8-sig')
        print(f"  ✓ 对比矩阵: {matrix_path}")
        
        # 保存完整报告
        full_report = self.generate_full_report()
        report_path = os.path.join(self.reports_dir, 'full_strategy_backtest.md')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(full_report)
        print(f"  ✓ 完整报告: {report_path}")
        
        # 保存JSON格式结果
        json_path = os.path.join(self.reports_dir, 'full_backtest_results.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"  ✓ JSON结果: {json_path}")
        
        # 保存最优策略推荐
        self._save_optimal_strategy_recommendation()
        
        return matrix_path, report_path, json_path
    
    def _save_optimal_strategy_recommendation(self):
        """保存最优策略推荐"""
        print("生成最优策略推荐...")
        
        valid_results = {k: v for k, v in self.results.items() if 'error' not in v}
        
        if not valid_results:
            return
        
        # 综合评分
        scored_strategies = []
        for strategy, result in valid_results.items():
            sharpe = result['sharpe_ratio']
            annual_return = result['annual_return']
            max_dd = result['max_drawdown']
            
            # 综合评分
            sharpe_score = max(0, sharpe) * 0.4
            return_score = min(1, annual_return / 0.2) * 0.3
            drawdown_score = (1 - max_dd) * 0.3
            total_score = sharpe_score + return_score + drawdown_score
            
            scored_strategies.append({
                'strategy': strategy,
                'score': total_score,
                'sharpe': sharpe,
                'annual_return': annual_return,
                'max_drawdown': max_dd,
                'win_rate': result['win_rate'],
                'num_trades': result['num_trades']
            })
        
        scored_strategies.sort(key=lambda x: x['score'], reverse=True)
        
        # 生成推荐报告
        report = []
        report.append("# 最优策略推荐报告")
        report.append(f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("\n## 综合评分Top 10")
        
        for i, item in enumerate(scored_strategies[:10], 1):
            report.append(f"\n### {i}. {item['strategy']}")
            report.append(f"- **综合评分**: {item['score']:.2f}")
            report.append(f"- **年化收益率**: {item['annual_return']*100:.2f}%")
            report.append(f"- **夏普比率**: {item['sharpe']:.2f}")
            report.append(f"- **最大回撤**: {item['max_drawdown']*100:.2f}%")
            report.append(f"- **胜率**: {item['win_rate']*100:.1f}%")
            report.append(f"- **交易次数**: {item['num_trades']}")
        
        # 策略组合建议
        report.append("\n---")
        report.append("\n## 推荐策略组合")
        
        # 保守组合（高夏普）
        report.append("\n### 保守组合（优先夏普比率）")
        conservative = scored_strategies[:3]
        for item in conservative:
            report.append(f"- {item['strategy']}: 权重33%")
        avg_sharpe = sum(item['sharpe'] for item in conservative) / 3
        avg_return = sum(item['annual_return'] for item in conservative) / 3
        avg_dd = sum(item['max_drawdown'] for item in conservative) / 3
        report.append(f"\n**组合预期**:")
        report.append(f"- 夏普比率: {avg_sharpe:.2f}")
        report.append(f"- 年化收益率: {avg_return*100:.2f}%")
        report.append(f"- 最大回撤: {avg_dd*100:.2f}%")
        
        # 平衡组合
        report.append("\n### 平衡组合（收益风险平衡）")
        balanced = scored_strategies[:5]
        for item in balanced:
            report.append(f"- {item['strategy']}: 权重20%")
        
        # 实施建议
        report.append("\n---")
        report.append("\n## 实施建议")
        report.append("\n1. **渐进式部署**: 先小资金验证，逐步扩大规模")
        report.append("2. **动态调整**: 根据市场环境变化调整权重")
        report.append("3. **风险控制**: 单策略最大仓位30%，单回撤止损15%")
        report.append("4. **定期回顾**: 每季度回顾策略表现，淘汰失效策略")
        report.append("5. **持续优化**: 根据回测和实战数据持续优化参数")
        
        # 保存
        path = os.path.join(self.reports_dir, 'optimal_strategy_recommendation.md')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        print(f"  ✓ 最优策略推荐: {path}")


def main():
    """主函数"""
    import sys
    
    print("="*80)
    print("全面策略回测 - P1任务")
    print("="*80)
    
    # 加载数据
    print("\n加载数据...")
    data_path = 'data/real_stock_data.pkl'
    data = pd.read_pickle(data_path)
    print(f"  ✓ 数据加载完成: {len(data):,} 条记录")
    print(f"  ✓ 时间范围: {data['date'].min()} 到 {data['date'].max()}")
    print(f"  ✓ 股票数量: {data['stock_code'].nunique()}")
    
    # 创建回测器
    print("\n初始化回测引擎...")
    backtester = StrategyBacktester(data)
    
    # 运行所有策略
    results = backtester.run_all_strategies()
    
    # 生成报告
    print("\n生成回测报告...")
    reporter = StrategyReportGenerator(results)
    matrix_path, report_path, json_path = reporter.save_reports()
    
    print("\n" + "="*80)
    print("✓ 全面策略回测完成！")
    print("="*80)
    print(f"\n生成文件:")
    print(f"  1. {report_path}")
    print(f"  2. {matrix_path}")
    print(f"  3. {json_path}")
    print(f"  4. {os.path.join('reports', 'optimal_strategy_recommendation.md')}")
    
    # 打印摘要
    valid_results = {k: v for k, v in results.items() if 'error' not in v}
    if valid_results:
        print(f"\n回测摘要:")
        print(f"  成功回测策略: {len(valid_results)} 个")
        print(f"  失败策略: {len(results) - len(valid_results)} 个")
        
        best_sharpe = max(valid_results.items(), key=lambda x: x[1]['sharpe_ratio'])
        best_return = max(valid_results.items(), key=lambda x: x[1]['annual_return'])
        
        print(f"\n最佳夏普策略:")
        print(f"  {best_sharpe[0]}: 夏普={best_sharpe[1]['sharpe_ratio']:.2f}, 收益={best_sharpe[1]['annual_return']*100:.2f}%")
        
        print(f"\n最佳收益策略:")
        print(f"  {best_return[0]}: 收益={best_return[1]['annual_return']*100:.2f}%, 夏普={best_return[1]['sharpe_ratio']:.2f}")
    
    return results


if __name__ == '__main__':
    main()
