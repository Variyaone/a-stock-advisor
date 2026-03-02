#!/usr/bin/env python3
"""
月度绩效归因分析模块
使用Brinson归因模型分析超收益来源
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import os

@dataclass
class AttributionResult:
    """归因结果"""
    period: str  # 归因期间
    portfolio_return: float  # 组合收益率
    benchmark_return: float  # 基准收益率
    active_return: float  # 超收益
    
    # Brinson归因分解
    allocation_effect: float  # 配置效应
    selection_effect: float  # 选股效应
    interaction_effect: float  # 交互效应
    
    # 因子归因
    factor_returns: Dict[str, float]  # 各因子贡献
    
    # 风格归因
    style_returns: Dict[str, float]  # 各风格暴露贡献

class MonthlyAttribution:
    """月度归因分析器"""
    
    def __init__(self, benchmark_name: str = '沪深300'):
        """
        初始化归因分析器
        
        Args:
            benchmark_name: 基准名称
        """
        self.benchmark_name = benchmark_name
        self.attribution_file = 'data/attribution_results.json'
        
        self.attribution_history: List[AttributionResult] = []
        self._load_history()
    
    def _load_history(self):
        """加载历史归因结果"""
        if os.path.exists(self.attribution_file):
            try:
                with open(self.attribution_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                
                for result_data in history_data:
                    result = AttributionResult(**result_data)
                    self.attribution_history.append(result)
                
                print(f"✓ 加载归因历史: {len(self.attribution_history)}条记录")
            except Exception as e:
                print(f"⚠️ 加载归因历史失败: {e}")
    
    def _save_result(self, result: AttributionResult):
        """保存归因结果"""
        self.attribution_history.append(result)
        
        history_data = [
            {
                'period': r.period,
                'portfolio_return': r.portfolio_return,
                'benchmark_return': r.benchmark_return,
                'active_return': r.active_return,
                'allocation_effect': r.allocation_effect,
                'selection_effect': r.selection_effect,
                'interaction_effect': r.interaction_effect,
                'factor_returns': r.factor_returns,
                'style_returns': r.style_returns
            }
            for r in self.attribution_history
        ]
        
        os.makedirs(os.path.dirname(self.attribution_file), exist_ok=True)
        with open(self.attribution_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
    
    def calculate_portfolio_return(self, portfolio_df: pd.DataFrame) -> float:
        """
        计算组合收益率
        
        Args:
            portfolio_df: 组合数据 DataFrame，包含 'market_value', 'profit_loss' 列
            
        Returns:
            组合收益率
        """
        if portfolio_df.empty or 'market_value' not in portfolio_df.columns:
            return 0.0
        
        total_cost = portfolio_df['market_value'].sum() - portfolio_df['profit_loss'].sum()
        if total_cost == 0:
            return 0.0
        
        portfolio_return = portfolio_df['profit_loss'].sum() / total_cost * 100
        
        return portfolio_return
    
    def brinson_attribution(self, portfolio_weights: Dict[str, float],
                          benchmark_weights: Dict[str, float],
                          sector_returns: Dict[str, float]) -> Dict[str, float]:
        """
        Brinson归因分析
        
        Args:
            portfolio_weights: 组合各行业权重 {行业: 权重}
            benchmark_weights: 基准各行业权重 {行业: 权重}
            sector_returns: 各行业收益率 {行业: 收益率}
            
        Returns:
            归因结果
        """
        # 总组合收益率和基准收益率
        portfolio_return = sum(weight * sector_returns.get(sector, 0) 
                             for sector, weight in portfolio_weights.items())
        benchmark_return = sum(weight * sector_returns.get(sector, 0) 
                             for sector, weight in benchmark_weights.items())
        
        # 超收益
        active_return = portfolio_return - benchmark_return
        
        # 计算Brinson归因分解
        allocation_effect = 0.0  # 配置效应
        selection_effect = 0.0  # 选股效应
        interaction_effect = 0.0  # 交互效应
        
        sectors = set(portfolio_weights.keys()) | set(benchmark_weights.keys())
        
        for sector in sectors:
            w_p = portfolio_weights.get(sector, 0)
            w_b = benchmark_weights.get(sector, 0)
            r_s = sector_returns.get(sector, 0)
            r_b = benchmark_return  # 基准收益率
            
            # 配置效应: (权重差异) * (行业与基准收益差异)
            allocation_effect += (w_p - w_b) * (r_s - r_b)
            
            # 选股效应: 基准权重 * (行业收益率与基准差异)
            selection_effect += w_b * (r_s - r_b)
            
            # 交互效应: 权重差异 * 行业收益率
            interaction_effect += (w_p - w_b) * r_s
        
        # 交叉项调整
        cross_term = sum((portfolio_weights.get(s, 0) - benchmark_weights.get(s, 0)) * 
                        (sector_returns.get(s, 0) - benchmark_return)
                        for s in sectors)
        
        # 重新计算
        allocation_effect = sum(
            (portfolio_weights.get(s, 0) - benchmark_weights.get(s, 0)) * 
            (sector_returns.get(s, 0) - benchmark_return)
            for s in sectors
        )
        
        selection_effect = sum(
            benchmark_weights.get(s, 0) * 
            (sector_returns.get(s, 0) - benchmark_return)
            for s in sectors
        )
        
        interaction_effect = active_return - allocation_effect - selection_effect
        
        return {
            'portfolio_return': portfolio_return,
            'benchmark_return': benchmark_return,
            'active_return': active_return,
            'allocation_effect': allocation_effect,
            'selection_effect': selection_effect,
            'interaction_effect': interaction_effect
        }
    
    def factor_attribution(self, portfolio_df: pd.DataFrame,
                          factor_exposures: Dict[str, Dict[str, float]],
                          factor_returns: Dict[str, float]) -> Dict[str, float]:
        """
        因子归因分析
        
        Args:
            portfolio_df: 组合 DataFrame (index: stock_code)
            factor_exposures: 各股票的因子暴露 {stock_code: {factor_name: exposure}}
            factor_returns: 各因子收益率 {factor_name: return}
            
        Returns:
            各因子贡献
        """
        factor_contributions = {}
        
        if portfolio_df.empty:
            return factor_contributions
        
        # 计算组合权重
        total_value = portfolio_df['market_value'].sum()
        if total_value == 0:
            return factor_contributions
        
        for factor_name in factor_returns.keys():
            total_exposure = 0.0
            
            for stock_code, row in portfolio_df.iterrows():
                weight = row['market_value'] / total_value
                exposure = factor_exposures.get(stock_code, {}).get(factor_name, 0)
                total_exposure += weight * exposure
            
            # 因子贡献 = 组合因子暴露 × 因子收益率
            contribution = total_exposure * factor_returns[factor_name]
            factor_contributions[factor_name] = contribution
        
        return factor_contributions
    
    def style_attribution(self, portfolio_df: pd.DataFrame,
                         style_exposures: Dict[str, Dict[str, float]],
                         style_returns: Dict[str, float]) -> Dict[str, float]:
        """
        风格归因分析
        
        Args:
            portfolio_df: 组合 DataFrame
            style_exposures: 各股票的风格暴露 {stock_code: {style_name: exposure}}
            style_returns: 各风格收益率 {style_name: return}
            
        Returns:
            各风格贡献
        """
        similar_to_factor = self.factor_attribution(
            portfolio_df, style_exposures, style_returns
        )
        
        return similar_to_factor
    
    def analyze_month(self, portfolio_df: pd.DataFrame,
                     portfolio_weights: Dict[str, float],
                     benchmark_weights: Dict[str, float],
                     sector_returns: Dict[str, float],
                     factor_exposures: Dict[str, Dict[str, float]] = None,
                     factor_returns: Dict[str, float] = None,
                     period: str = None) -> AttributionResult:
        """
        分析月度归因
        
        Args:
            portfolio_df: 持仓数据 DataFrame
            portfolio_weights: 组合行业权重
            benchmark_weights: 基准行业权重
            sector_returns: 行业收益率
            factor_exposures: 因子暴露
            factor_returns: 因子收益率
            period: 归因期间 (如 "2024-03")
            
        Returns:
            归因结果
        """
        if period is None:
            period = datetime.now().strftime('%Y-%m')
        
        print("=" * 60)
        print(f"📊 月度归因分析 - {period}")
        print("=" * 60)
        
        # 1. 计算组合收益率
        portfolio_return = self.calculate_portfolio_return(portfolio_df)
        print(f"\n组合收益率: {portfolio_return:.2f}%")
        
        # 2. 计算基准收益率
        benchmark_return = sum(
            benchmark_weights.get(sector, 0) * sector_returns.get(sector, 0)
            for sector in benchmark_weights.keys()
        )
        print(f"基准收益率: {benchmark_return:.2f}%")
        
        # 3. 计算超收益
        active_return = portfolio_return - benchmark_return
        print(f"超收益: {active_return:.2f}%")
        
        # 4. Brinson归因
        print(f"\n🎯 Brinson归因分解...")
        brinson_results = self.brinson_attribution(
            portfolio_weights, benchmark_weights, sector_returns
        )
        
        print(f"  • 配置效应: {brinson_results['allocation_effect']:.2f}%")
        print(f"  • 选股效应: {brinson_results['selection_effect']:.2f}%")
        print(f"  • 交互效应: {brinson_results['interaction_effect']:.2f}%")
        
        # 5. 因子归因
        factor_returns_result = {}
        if factor_exposures and factor_returns:
            print(f"\n📈 因子归因...")
            factor_returns_result = self.factor_attribution(
                portfolio_df, factor_exposures, factor_returns
            )
            
            for factor, contribution in sorted(factor_returns_result.items(), 
                                              key=lambda x: abs(x[1]), reverse=True):
                print(f"  • {factor}: {contribution:.2f}%")
        
        # 6. 风格归因
        style_returns_result = {}
        if factor_exposures and factor_returns:
            # 使用行业暴露作为风格
            style_exposures = {}
            style_returns = {}
            
            for stock_code, exposures in factor_exposures.items():
                if stock_code in portfolio_df.index:
                    sector = portfolio_df.loc[stock_code, 'sector'] if 'sector' in portfolio_df.columns else '其他'
                    style_exposures[stock_code] = {sector: 1.0}
                    style_returns[sector] = sector_returns.get(sector, 0)
            
            print(f"\n🎨 风格归因...")
            style_returns_result = self.style_attribution(
                portfolio_df, style_exposures, style_returns
            )
            
            for style, contribution in sorted(style_returns_result.items(),
                                            key=lambda x: abs(x[1]), reverse=True):
                print(f"  • {style}: {contribution:.2f}%")
        
        # 7. 创建归因结果
        result = AttributionResult(
            period=period,
            portfolio_return=portfolio_return,
            benchmark_return=benchmark_return,
            active_return=active_return,
            allocation_effect=brinson_results['allocation_effect'],
            selection_effect=brinson_results['selection_effect'],
            interaction_effect=brinson_results['interaction_effect'],
            factor_returns=factor_returns_result,
            style_returns=style_returns_result
        )
        
        # 8. 保存结果
        self._save_result(result)
        
        print("\n" + "=" * 60)
        print(f"归因分析完成并保存")
        print("=" * 60)
        
        return result
    
    def generate_attribution_report(self, result: AttributionResult) -> str:
        """
        生成归因报告
        
        Args:
            result: 归因结果
            
        Returns:
            报告文本
        """
        report = []
        report.append("=" * 60)
        report.append("📊 归因分析报告")
        report.append("=" * 60)
        report.append(f"期间: {result.period}")
        report.append("")
        
        report.append("💰 收益率汇总")
        report.append("-" * 40)
        report.append(f"组合收益率: {result.portfolio_return:.2f}%")
        report.append(f"基准收益率: {result.benchmark_return:.2f}%")
        report.append(f"超收益: {result.active_return:.2f}%")
        report.append("")
        
        report.append("🎯 Brinson归因分解")
        report.append("-" * 40)
        report.append(f"配置效应: {result.allocation_effect:.2f}%")
        report.append(f"  - 含义: 通过行业配置偏离基准获得的收益")
        report.append(f"选股效应: {result.selection_effect:.2f}%")
        report.append(f"  - 含义: 在各行业内选股获得的收益")
        report.append(f"交互效应: {result.interaction_effect:.2f}%")
        report.append(f"  - 含义: 配置和选股的交互影响")
        report.append("")
        
        if result.factor_returns:
            report.append("📈 因子归因")
            report.append("-" * 40)
            
            # 按贡献度排序
            sorted_factors = sorted(result.factor_returns.items(), 
                                   key=lambda x: abs(x[1]), reverse=True)
            
            for factor, contribution in sorted_factors:
                emoji = "📈" if contribution > 0 else "📉"
                report.append(f"{emoji} {factor}: {contribution:.2f}%")
            report.append("")
        
        if result.style_returns:
            report.append("🎨 风格归因")
            report.append("-" * 40)
            
            sorted_styles = sorted(result.style_returns.items(),
                                 key=lambda x: abs(x[1]), reverse=True)
            
            for style, contribution in sorted_styles:
                emoji = "📈" if contribution > 0 else "📉"
                report.append(f"{emoji} {style}: {contribution:.2f}%")
            report.append("")
        
        # 总结
        report.append("💡 归因总结")
        report.append("-" * 40)
        
        total_effect = result.allocation_effect + result.selection_effect + result.interaction_effect
        if abs(total_effect - result.active_return) > 0.01:
            report.append(f"⚠️ 归因误差: {total_effect - result.active_return:.2f}%")
        
        if abs(result.allocation_effect) > abs(result.selection_effect):
            if result.allocation_effect > 0:
                report.append("✓ 主要收益来源: 行业配置能力")
            else:
                report.append("✗ 主要亏损来源: 行业配置偏离")
        elif abs(result.selection_effect) > 0:
            if result.selection_effect > 0:
                report.append("✓ 主要收益来源: 个股选择能力")
            else:
                report.append("✗ 主要亏损来源: 个股选择偏差")
        else:
            report.append("→ 收益来源均衡，无明显偏差")
        
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def generate_monthly_summary(self, months: int = 6) -> str:
        """
        生成最近N个月的归因汇总
        
        Args:
            months: 月份数量
            
        Returns:
            汇总报告文本
        """
        if not self.attribution_history:
            return "暂无归因数据"
        
        recent_results = self.attribution_history[-months:]
        
        report = []
        report.append("=" * 60)
        report.append(f"📊 最近{months}个月归因汇总")
        report.append("=" * 60)
        report.append("")
        
        # 收益率汇总
        total_portfolio_return = sum(r.portfolio_return for r in recent_results)
        total_benchmark_return = sum(r.benchmark_return for r in recent_results)
        total_active_return = sum(r.active_return for r in recent_results)
        
        avg_portfolio_return = total_portfolio_return / len(recent_results)
        avg_benchmark_return = total_benchmark_return / len(recent_results)
        avg_active_return = total_active_return / len(recent_results)
        
        report.append("💰 收益率汇总")
        report.append("-" * 40)
        report.append(f"累计组合收益: {total_portfolio_return:.2f}%")
        report.append(f"累计基准收益: {total_benchmark_return:.2f}%")
        report.append(f"累计超收益: {total_active_return:.2f}%")
        report.append(f"月均组合收益: {avg_portfolio_return:.2f}%")
        report.append(f"月均基准收益: {avg_benchmark_return:.2f}%")
        report.append(f"月均超收益: {avg_active_return:.2f}%")
        report.append("")
        
        # Brinson归因汇总
        total_allocation = sum(r.allocation_effect for r in recent_results)
        total_selection = sum(r.selection_effect for r in recent_results)
        total_interaction = sum(r.interaction_effect for r in recent_results)
        
        report.append("🎯 Brinson归因汇总")
        report.append("-" * 40)
        report.append(f"累计配置效应: {total_allocation:.2f}%")
        report.append(f"累计选股效应: {total_selection:.2f}%")
        report.append(f"累计交互效应: {total_interaction:.2f}%")
        report.append("")
        
        # 月度明细
        report.append("📅 月度明细")
        report.append("-" * 40)
        
        for result in recent_results:
            emoji = "📈" if result.active_return > 0 else "📉"
            report.append(f"{emoji} {result.period}")
            report.append(f"   组合: {result.portfolio_return:.2f}% | 基准: {result.benchmark_return:.2f}% | 超收益: {result.active_return:.2f}%")
            report.append(f"   配置: {result.allocation_effect:.2f}% | 选股: {result.selection_effect:.2f}% | 交互: {result.interaction_effect:.2f}%")
        
        report.append("=" * 60)
        
        return "\n".join(report)


# 测试代码
if __name__ == "__main__":
    # 创建测试数据
    portfolio_df = pd.DataFrame({
        'stock_code': ['000001', '000002', '600519'],
        'stock_name': ['平安银行', '万科A', '贵州茅台'],
        'market_value': [10000, 5000, 18000],
        'profit_loss': [1000, -500, 2000],
        'sector': ['金融', '房地产', '消费品']
    })
    
    portfolio_weights = {'金融': 0.3, '房地产': 0.15, '消费品': 0.55}
    benchmark_weights = {'金融': 0.25, '房地产': 0.20, '消费品': 0.50, '科技': 0.05}
    sector_returns = {'金融': 0.08, '房地产': -0.05, '消费品': 0.12, '科技': 0.15}
    
    factor_exposures = {
        '000001': {'PE_TTM': 5.0, 'PB': 0.8, 'ROE': 0.12},
        '000002': {'PE_TTM': 20.0, 'PB': 1.5, 'ROE': 0.08},
        '600519': {'PE_TTM': 25.0, 'PB': 10.0, 'ROE': 0.25}
    }
    
    factor_returns = {'PE_TTM': -0.05, 'PB': -0.03, 'ROE': 0.08}
    
    # 测试归因分析
    analyzer = MonthlyAttribution()
    result = analyzer.analyze_month(
        portfolio_df,
        portfolio_weights,
        benchmark_weights,
        sector_returns,
        factor_exposures,
        factor_returns,
        period='2024-03'
    )
    
    print("\n" + analyzer.generate_attribution_report(result))
    print("\n" + analyzer.generate_monthly_summary(1))
