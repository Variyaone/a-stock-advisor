#!/usr/bin/env python3
"""
P1任务：风控体系完善模块
功能：
1. 策略容量评估（最大资金容量）
2. 冲击成本评估
3. 流动性风险分析
4. 风格暴露分析（大盘/小盘、价值/成长）
5. 因子拥挤度分析

目标：建立完整的风险控制体系，确保系统安全稳健
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from collections import defaultdict
import json
import os
import warnings

warnings.filterwarnings('ignore')


class RiskControlSystem:
    """风控体系"""
    
    def __init__(self, data_path: str, config: Dict = None):
        self.data_path = data_path
        self.config = config or self._default_config()
        self.df = None
        self.results = {}
        self._load_data()
    
    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            'max_position_ratio': 0.10,
            'max_turnover_rate': 0.50,
            'liquidity_threshold': 10000000,
            'impact_cost_levels': [0.01, 0.05, 0.10],
            'base_impact_cost': 0.0005,
            'impact_cost_sqrt': 0.001,
            'small_cap_threshold': 0.4,
            'pe_value_threshold': 20,
            'growth_rate_threshold': 0.15,
            'top_n_concentration': 10,
            'hhi_threshold': 0.02,
        }
    
    def _load_data(self):
        """加载数据"""
        print(f"📂 加载数据: {self.data_path}")
        self.df = pd.read_pickle(self.data_path)
        
        if 'date' in self.df.columns:
            self.df['date'] = pd.to_datetime(self.df['date'])
        
        self.df = self.df.sort_values('date')
        print(f"✓ 数据加载成功: {self.df.shape}")
    
    def calculate_strategy_capacity(self, initial_capital: float = 10000000) -> Dict:
        """P1-1: 策略容量评估"""
        print("\n" + "=" * 70)
        print("📊 P1-1: 策略容量评估")
        print("=" * 70)
        
        capacity_analysis = {}
        
        # 基于流动性估算
        if 'volume' in self.df.columns:
            avg_daily_value = self.df.groupby('stock_code').apply(
                lambda x: (x['close'] * x['volume']).mean()
            )
            liquidity_capacity = avg_daily_value.sum() * 0.1  # 日成交额的10%
        else:
            avg_price = self.df.groupby('stock_code')['close'].mean()
            liquidity_capacity = avg_price.sum() * 1000000  # 简化估算
        
        # 基于换手率估算
        turnover_capacity = initial_capital * self.config['max_turnover_rate'] * 12
        
        # 综合容量
        max_capacity = min(liquidity_capacity, turnover_capacity)
        recommended_capacity = max_capacity * 0.8  # 80%安全边际
        
        capacity_analysis = {
            'liquidity_capacity': float(liquidity_capacity),
            'turnover_capacity': float(turnover_capacity),
            'max_capacity': float(max_capacity),
            'recommended_capacity': float(recommended_capacity),
            'capacity_grade': 'A' if recommended_capacity >= initial_capital * 5 else 'B' if recommended_capacity >= initial_capital * 2 else 'C'
        }
        
        print(f"  流动性容量: ¥{liquidity_capacity:,.0f}")
        print(f"  换手率容量: ¥{turnover_capacity:,.0f}")
        print(f"  推荐容量:   ¥{recommended_capacity:,.0f}")
        print(f"  容量评级:   {capacity_analysis['capacity_grade']}")
        
        self.results['strategy_capacity'] = capacity_analysis
        return capacity_analysis
    
    def assess_impact_cost(self, trade_amounts: List[float] = None) -> Dict:
        """P1-2: 冲击成本评估"""
        print("\n" + "=" * 70)
        print("📊 P1-2: 冲击成本评估")
        print("=" * 70)
        
        if trade_amounts is None:
            trade_amounts = [100000, 500000, 1000000, 5000000, 10000000]
        
        impact_analysis = {'impact_by_amount': {}}
        
        base_impact = self.config['base_impact_cost']
        impact_sqrt = self.config['impact_cost_sqrt']
        
        for amount in trade_amounts:
            impact = base_impact * amount + impact_sqrt * np.sqrt(amount) * amount
            impact_rate = impact / amount
            
            risk_level = "低" if impact_rate < 0.001 else "中" if impact_rate < 0.003 else "高"
            
            impact_analysis['impact_by_amount'][f'{int(amount/10000)}万'] = {
                'amount': float(amount),
                'impact_rate': float(impact_rate),
                'risk_level': risk_level
            }
        
        print(f"  冲击成本分析:")
        for label, data in impact_analysis['impact_by_amount'].items():
            print(f"    {label}: {data['impact_rate']:.4%} ({data['risk_level']})")
        
        self.results['impact_cost'] = impact_analysis
        return impact_analysis
    
    def analyze_liquidity_risk(self) -> Dict:
        """P1-3: 流动性风险分析"""
        print("\n" + "=" * 70)
        print("📊 P1-3: 流动性风险分析")
        print("=" * 70)
        
        liquidity_analysis = {}
        
        # 个股流动性
        if 'volume' in self.df.columns:
            self.df['turnover'] = self.df['close'] * self.df['volume']
            stock_liquidity = self.df.groupby('stock_code')['turnover'].agg(['mean', 'std'])
            stock_liquidity['cv'] = stock_liquidity['std'] / stock_liquidity['mean']
            
            high_risk_count = (stock_liquidity['cv'] > 0.5).sum()
            total_stocks = len(stock_liquidity)
            
            liquidity_analysis = {
                'high_risk_count': int(high_risk_count),
                'total_stocks': int(total_stocks),
                'high_risk_ratio': float(high_risk_count / total_stocks),
                'liquidity_grade': '高风险' if high_risk_count > total_stocks * 0.3 else '中风险' if high_risk_count > total_stocks * 0.1 else '低风险'
            }
        else:
            liquidity_analysis = {
                'liquidity_grade': '未知（缺少成交量数据）'
            }
        
        print(f"  高风险股票数: {liquidity_analysis.get('high_risk_count', 0)}")
        print(f"  流动性评级: {liquidity_analysis['liquidity_grade']}")
        
        self.results['liquidity_risk'] = liquidity_analysis
        return liquidity_analysis
    
    def analyze_style_exposure(self) -> Dict:
        """P1-4: 风格暴露分析"""
        print("\n" + "=" * 70)
        print("📊 P1-4: 风格暴露分析")
        print("=" * 70)
        
        style_analysis = {}
        
        # 大盘/小盘
        avg_price = self.df.groupby('stock_code')['close'].mean()
        price_quantile = avg_price.rank(pct=True)
        
        large_cap_count = (price_quantile >= self.config['small_cap_threshold']).sum()
        total_stocks = len(avg_price)
        
        style_analysis['size_exposure'] = {
            'large_cap_ratio': float(large_cap_count / total_stocks),
            'small_cap_ratio': float((total_stocks - large_cap_count) / total_stocks),
            'size_tilt': '大盘倾向' if large_cap_count > total_stocks * 0.6 else '小盘倾向' if large_cap_count < total_stocks * 0.4 else '均衡'
        }
        
        # 价值/成长
        if 'pe_ttm' in self.df.columns:
            avg_pe = self.df.groupby('stock_code')['pe_ttm'].mean()
            value_count = (avg_pe <= self.config['pe_value_threshold']).sum()
            
            style_analysis['value_growth_exposure'] = {
                'value_ratio': float(value_count / total_stocks),
                'growth_ratio': float((total_stocks - value_count) / total_stocks),
                'style_tilt': '价值倾向' if value_count > total_stocks * 0.6 else '成长倾向' if value_count < total_stocks * 0.4 else '均衡'
            }
        
        print(f"  大小盘风格: {style_analysis['size_exposure']['size_tilt']}")
        if 'value_growth_exposure' in style_analysis:
            print(f"  价值成长风格: {style_analysis['value_growth_exposure']['style_tilt']}")
        
        self.results['style_exposure'] = style_analysis
        return style_analysis
    
    def analyze_factor_crowding(self) -> Dict:
        """P1-5: 因子拥挤度分析"""
        print("\n" + "=" * 70)
        print("📊 P1-5: 因子拥挤度分析")
        print("=" * 70)
        
        crowding_analysis = {}
        
        # 持仓集中度（基于因子得分）
        if 'factor_score' in self.df.columns and 'month' in self.df.columns:
            top_stocks = []
            for month in self.df['month'].unique():
                month_data = self.df[self.df['month'] == month]
                top_10 = month_data.nlargest(10, 'factor_score')['stock_code'].tolist()
                top_stocks.extend(top_10)
            
            stock_freq = pd.Series(top_stocks).value_counts()
            total_selections = len(top_stocks)
            
            hhi = float(((stock_freq / total_selections) ** 2).sum())
            
            crowding_analysis = {
                'unique_stocks': len(stock_freq),
                'total_selections': total_selections,
                'hhi': hhi,
                'top_10_concentration': float(stock_freq.head(10).sum() / total_selections),
                'crowding_grade': '高拥挤' if hhi > 0.02 else '中拥挤' if hhi > 0.01 else '低拥挤'
            }
        else:
            crowding_analysis = {
                'crowding_grade': '未知（缺少因子得分数据）'
            }
        
        print(f"  HHI指数: {crowding_analysis.get('hhi', 0):.4f}")
        print(f"  拥挤度评级: {crowding_analysis['crowding_grade']}")
        
        self.results['factor_crowding'] = crowding_analysis
        return crowding_analysis
    
    def generate_risk_report(self) -> Dict:
        """生成综合风控报告"""
        print("\n" + "=" * 70)
        print("🔍 综合风控评估报告")
        print("=" * 70)
        
        risk_report = {
            'overall_risk_level': 'unknown',
            'risk_score': 0,
            'issues': [],
            'recommendations': []
        }
        
        scores = []
        
        # 容量风险
        if 'strategy_capacity' in self.results:
            capacity_grade = self.results['strategy_capacity']['capacity_grade']
            capacity_score = 90 if capacity_grade == 'A' else 70 if capacity_grade == 'B' else 50
            scores.append(capacity_score)
        
        # 流动性风险
        if 'liquidity_risk' in self.results:
            liquidity_grade = self.results['liquidity_risk']['liquidity_grade']
            liquidity_score = 90 if '低' in liquidity_grade else 70 if '中' in liquidity_grade else 50
            scores.append(liquidity_score)
        
        # 拥挤度风险
        if 'factor_crowding' in self.results:
            crowding_grade = self.results['factor_crowding']['crowding_grade']
            crowding_score = 90 if '低' in crowding_grade else 70 if '中' in crowding_grade else 50
            scores.append(crowding_score)
        
        if scores:
            risk_report['risk_score'] = int(np.mean(scores))
        
        # 风险等级
        score = risk_report['risk_score']
        if score >= 80:
            risk_report['overall_risk_level'] = 'LOW (低风险)'
        elif score >= 60:
            risk_report['overall_risk_level'] = 'MEDIUM (中等风险)'
        else:
            risk_report['overall_risk_level'] = 'HIGH (高风险)'
        
        print(f"\n🎯 综合风险评分: {risk_report['risk_score']}/100")
        print(f"   风险等级: {risk_report['overall_risk_level']}")
        
        self.results['risk_report'] = risk_report
        return risk_report
    
    def run_full_analysis(self) -> Dict:
        """运行完整风控分析"""
        print("\n" + "=" * 70)
        print("🚀 P1风控体系完整分析")
        print("=" * 70)
        
        self.calculate_strategy_capacity()
        self.assess_impact_cost()
        self.analyze_liquidity_risk()
        self.analyze_style_exposure()
        self.analyze_factor_crowding()
        self.generate_risk_report()
        
        print("\n" + "=" * 70)
        print("✅ P1风控分析完成")
        print("=" * 70)
        
        return self.results
    
    def save_report(self, output_dir: str = '/Users/variya/.openclaw/workspace/projects/a-stock-advisor/reports'):
        """保存报告"""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON报告
        json_path = os.path.join(output_dir, f'p1_risk_control_{timestamp}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
        
        # Markdown报告
        md_report = self._generate_markdown_report()
        md_path = os.path.join(output_dir, f'p1_risk_control_{timestamp}.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_report)
        
        print(f"\n✓ 报告已保存:")
        print(f"  JSON: {json_path}")
        print(f"  Markdown: {md_path}")
        
        return json_path, md_path
    
    def _generate_markdown_report(self) -> str:
        """生成Markdown报告"""
        lines = []
        
        lines.append("# P1风控体系分析报告\n")
        lines.append(f"**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append("---\n")
        
        # 综合评估
        if 'risk_report' in self.results:
            rr = self.results['risk_report']
            lines.append("## 🔍 综合风控评估\n")
            lines.append(f"- **风险评分:** {rr['risk_score']}/100\n")
            lines.append(f"- **风险等级:** {rr['overall_risk_level']}\n\n")
        
        # P1-1: 策略容量
        if 'strategy_capacity' in self.results:
            sc = self.results['strategy_capacity']
            lines.append("## 📊 P1-1: 策略容量评估\n")
            lines.append(f"- 推荐容量: ¥{sc['recommended_capacity']:,.0f}\n")
            lines.append(f"- 容量评级: {sc['capacity_grade']}\n\n")
        
        # P1-2: 冲击成本
        if 'impact_cost' in self.results:
            lines.append("## 📊 P1-2: 冲击成本评估\n")
            lines.append("| 交易规模 | 冲击成本率 | 风险等级 |\n")
            lines.append("|---------|-----------|----------|\n")
            for label, data in self.results['impact_cost']['impact_by_amount'].items():
                lines.append(f"| {label} | {data['impact_rate']:.4%} | {data['risk_level']} |\n")
            lines.append("\n")
        
        # P1-3: 流动性风险
        if 'liquidity_risk' in self.results:
            lr = self.results['liquidity_risk']
            lines.append("## 📊 P1-3: 流动性风险分析\n")
            lines.append(f"- 流动性评级: {lr['liquidity_grade']}\n")
            if 'high_risk_count' in lr:
                lines.append(f"- 高风险股票数: {lr['high_risk_count']}\n")
            lines.append("\n")
        
        # P1-4: 风格暴露
        if 'style_exposure' in self.results:
            se = self.results['style_exposure']
            lines.append("## 📊 P1-4: 风格暴露分析\n")
            if 'size_exposure' in se:
                lines.append(f"- 大小盘风格: {se['size_exposure']['size_tilt']}\n")
            if 'value_growth_exposure' in se:
                lines.append(f"- 价值成长风格: {se['value_growth_exposure']['style_tilt']}\n")
            lines.append("\n")
        
        # P1-5: 因子拥挤度
        if 'factor_crowding' in self.results:
            fc = self.results['factor_crowding']
            lines.append("## 📊 P1-5: 因子拥挤度分析\n")
            lines.append(f"- 拥挤度评级: {fc['crowding_grade']}\n")
            if 'hhi' in fc:
                lines.append(f"- HHI指数: {fc['hhi']:.4f}\n")
            lines.append("\n")
        
        lines.append("---\n")
        lines.append("\n## 📋 总结\n\n")
        lines.append("本报告完成了P1风控体系的全面分析，包括策略容量、冲击成本、流动性风险、风格暴露和因子拥挤度五个维度。\n")
        
        return '\n'.join(lines)


def main():
    """主函数"""
    print("=" * 70)
    print("🚀 P1风控体系分析系统")
    print("=" * 70)
    
    rcs = RiskControlSystem(
        data_path='/Users/variya/.openclaw/workspace/projects/a-stock-advisor/data/mock_data.pkl'
    )
    
    results = rcs.run_full_analysis()
    rcs.save_report()
    
    return results


if __name__ == '__main__':
    main()
