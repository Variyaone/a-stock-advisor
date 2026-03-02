#!/usr/bin/env python3
"""
持仓监控脚本
功能：计算组合波动率、VaR、行业偏离度、个股集中度，生成每日风险报告
"""

import sys
import os
import json
import pickle as pkl
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

class PortfolioMonitor:
    """持仓监控器"""

    def __init__(self):
        """初始化"""
        self.portfolio_file = 'data/portfolio_state.json'
        self.data_file = 'data/akshare_real_data_fixed.pkl'
        self.risk_report_file = 'reports/daily_risk_report.json'

    def load_portfolio(self) -> Dict:
        """加载持仓状态"""
        if os.path.exists(self.portfolio_file):
            try:
                with open(self.portfolio_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载持仓失败: {e}")
        return {'positions': []}

    def load_stock_data(self) -> pd.DataFrame:
        """加载股票数据"""
        try:
            with open(self.data_file, 'rb') as f:
                df = pkl.load(f)
            return df
        except Exception as e:
            print(f"加载数据失败: {e}")
            return pd.DataFrame()

    def calculate_portfolio_volatility(self, portfolio: Dict, stock_data: pd.DataFrame,
                                      days: int = 20) -> Dict:
        """
        计算组合波动率（20日年化）

        Args:
            portfolio: 持仓数据
            stock_data: 股票数据
            days: 计算周期

        Returns:
            波动率信息字典
        """
        if not portfolio.get('positions'):
            return {'volatility': 0, 'status': '无持仓', 'level': 'info'}

        positions = portfolio['positions']

        # 获取持仓股票代码
        stock_codes = [pos['code'] for pos in positions]
        weights = [pos.get('weight', 0) for pos in positions]
        total_weight = sum(weights)

        if total_weight == 0:
            return {'volatility': 0, 'status': '空仓', 'level': 'info'}

        weights = [w / total_weight for w in weights]

        # 计算每只股票的波动率
        stock_volatilities = []

        for code, weight in zip(stock_codes, weights):
            # 从数据中获取该股票的20日收益率
            try:
                stock_hist = stock_data[stock_data['stock_code'] == code].copy()

                if len(stock_hist) < days:
                    # 如果数据不足，跳过
                    continue

                # 计算日收益率
                stock_hist = stock_hist.sort_values('date_dt')
                stock_hist['return'] = stock_hist['close'].pct_change()

                # 计算波动率（标准差）
                returns = stock_hist['return'].dropna().tail(days)

                if len(returns) > 0:
                    daily_vol = returns.std() * np.sqrt(252)  # 年化
                    stock_volatilities.append(daily_vol * weight)
            except Exception as e:
                print(f"计算{code}波动率失败: {e}")
                continue

        # 组合波动率 = sqrt(sum(w_i^2 * sigma_i^2 + 2 * sum(w_i * w_j * sigma_i * sigma_j * rho_ij)))
        # 这里简化使用加权平均
        portfolio_vol = sum(stock_volatilities)

        # 判断状态
        if portfolio_vol < 0.20:
            status = '正常'
            level = 'info'
        elif portfolio_vol < 0.25:
            status = '警告'
            level = 'warning'
        else:
            status = '危险'
            level = 'danger'

        return {
            'volatility': float(portfolio_vol),
            'status': status,
            'level': level,
            'value': f'{portfolio_vol:.1%}'
        }

    def calculate_var(self, portfolio: Dict, stock_data: pd.DataFrame,
                      days: int = 10, confidence: float = 0.95) -> Dict:
        """
        计算VaR（Value at Risk）

        Args:
            portfolio: 持仓数据
            stock_data: 股票数据
            days: 计算周期
            confidence: 置信度

        Returns:
            VaR信息字典
        """
        if not portfolio.get('positions'):
            return {'var': 0, 'status': '无持仓', 'level': 'info'}

        positions = portfolio['positions']

        # 获取持仓股票代码和权重
        stock_codes = [pos['code'] for pos in positions]
        weights = [pos.get('weight', 0) for pos in positions]
        total_weight = sum(weights)

        if total_weight == 0:
            return {'var': 0, 'status': '空仓', 'level': 'info'}

        weights = [w / total_weight for w in weights]

        # 获取每只股票的历史收益率
        all_returns = []

        for code, weight in zip(stock_codes, weights):
            try:
                stock_hist = stock_data[stock_data['stock_code'] == code].copy()

                if len(stock_hist) < days:
                    continue

                stock_hist = stock_hist.sort_values('date_dt')
                stock_hist['return'] = stock_hist['close'].pct_change()

                returns = stock_hist['return'].dropna().tail(days)

                # 加权收益率
                weighted_returns = returns * weight
                all_returns.extend(weighted_returns.tolist())
            except Exception as e:
                print(f"计算{code}收益率失败: {e}")
                continue

        if not all_returns:
            return {'var': 0, 'status': '数据不足', 'level': 'warning'}

        # 计算组合收益率
        portfolio_returns = pd.Series(all_returns)

        # 计算VaR（历史模拟法）
        var = np.percentile(portfolio_returns, (1 - confidence) * 100)

        # VaR为负数，表示损失
        var_loss = -var

        # 判断状态
        if var_loss < 0.10:
            status = '正常'
            level = 'info'
        elif var_loss < 0.15:
            status = '警告'
            level = 'warning'
        else:
            status = '危险'
            level = 'danger'

        return {
            'var': float(var_loss),
            'status': status,
            'level': level,
            'value': f'{var_loss:.1%}',
            'confidence': f'{confidence:.0%}'
        }

    def calculate_industry_deviation(self, portfolio: Dict,
                                    benchmark: Dict = None) -> Dict:
        """
        计算行业偏离度

        Args:
            portfolio: 持仓数据
            benchmark: 基准行业权重

        Returns:
            行业偏离度信息
        """
        if not portfolio.get('positions'):
            return {'deviations': [], 'status': '无持仓', 'level': 'info'}

        positions = portfolio['positions']

        # 统计行业权重
        industry_weights = {}
        total_weight = sum(pos.get('weight', 0) for pos in positions)

        if total_weight == 0:
            return {'deviations': [], 'status': '空仓', 'level': 'info'}

        for pos in positions:
            industry = pos.get('industry', '其他')
            weight = pos.get('weight', 0) / total_weight * 100
            industry_weights[industry] = industry_weights.get(industry, 0) + weight

        # 如果没有提供基准，使用等权重作为基准
        if benchmark is None:
            num_industries = len(industry_weights)
            if num_industries == 0:
                return {'deviations': [], 'status': '无行业数据', 'level': 'info'}
            benchmark = {industry: 100 / num_industries for industry in industry_weights}

        # 计算偏离度
        deviations = []
        has_warning = False

        for industry, portfolio_weight in industry_weights.items():
            benchmark_weight = benchmark.get(industry, 100 / len(benchmark))
            deviation = portfolio_weight - benchmark_weight

            # 判断状态
            if abs(deviation) > 12:
                status = '警告'
                level = 'warning'
                has_warning = True
            elif abs(deviation) > 20:
                status = '危险'
                level = 'danger'
                has_warning = True
            else:
                status = '正常'
                level = 'info'

            deviations.append({
                'industry': industry,
                'portfolio_weight': round(portfolio_weight, 1),
                'benchmark_weight': round(benchmark_weight, 1),
                'deviation': round(deviation, 1),
                'status': status,
                'level': level
            })

        overall_status = '警告' if has_warning else '正常'

        return {
            'deviations': deviations,
            'status': overall_status,
            'level': 'warning' if has_warning else 'info'
        }

    def calculate_concentration(self, portfolio: Dict) -> Dict:
        """
        计算个股集中度

        Args:
            portfolio: 持仓数据

        Returns:
            集中度信息
        """
        if not portfolio.get('positions'):
            return {'concentrations': [], 'status': '无持仓', 'level': 'info'}

        positions = portfolio['positions']
        total_weight = sum(pos.get('weight', 0) for pos in positions)

        if total_weight == 0:
            return {'concentrations': [], 'status': '空仓', 'level': 'info'}

        concentrations = []
        has_warning = False

        for pos in positions:
            weight = pos.get('weight', 0) / total_weight * 100

            # 判断状态
            if weight > 15:
                status = '危险'
                level = 'danger'
                has_warning = True
            elif weight > 12:
                status = '警告'
                level = 'warning'
                has_warning = True
            else:
                status = '正常'
                level = 'info'

            concentrations.append({
                'code': pos.get('code', 'N/A'),
                'name': pos.get('name', 'N/A'),
                'weight': round(weight, 1),
                'status': status,
                'level': level
            })

        overall_status = '警告' if has_warning else '正常'

        return {
            'concentrations': concentrations,
            'status': overall_status,
            'level': 'warning' if has_warning else 'info'
        }

    def calculate_max_drawdown(self, portfolio: Dict, stock_data: pd.DataFrame) -> Dict:
        """
        计算最大回撤

        Args:
            portfolio: 持仓数据
            stock_data: 股票数据

        Returns:
            最大回撤信息
        """
        if not portfolio.get('positions'):
            return {'max_drawdown': 0, 'status': '无持仓', 'level': 'info'}

        positions = portfolio['positions']

        # 获取持仓股票代码
        stock_codes = [pos['code'] for pos in positions]
        weights = [pos.get('weight', 0) for pos in positions]
        total_weight = sum(weights)

        if total_weight == 0:
            return {'max_drawdown': 0, 'status': '空仓', 'level': 'info'}

        weights = [w / total_weight for w in weights]

        # 计算组合净值曲线
        portfolio_values = []

        for code, weight in zip(stock_codes, weights):
            try:
                stock_hist = stock_data[stock_data['stock_code'] == code].copy()

                if len(stock_hist) == 0:
                    continue

                stock_hist = stock_hist.sort_values('date_dt')

                # 归一化价格
                normalized_prices = stock_hist['close'] / stock_hist['close'].iloc[0]

                # 加权
                weighted_values = normalized_prices * weight

                if len(portfolio_values) == 0:
                    portfolio_values = weighted_values.tolist()
                else:
                    # 对齐日期（简化处理）
                    min_len = min(len(portfolio_values), len(weighted_values))
                    portfolio_values = [
                        portfolio_values[i] + weighted_values[i]
                        for i in range(min_len)
                    ]
            except Exception as e:
                print(f"计算{code}净值失败: {e}")
                continue

        if len(portfolio_values) < 2:
            return {'max_drawdown': 0, 'status': '数据不足', 'level': 'warning'}

        # 计算回撤
        portfolio_series = pd.Series(portfolio_values)
        rolling_max = portfolio_series.expanding().max()
        drawdown = (portfolio_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        # 判断状态
        if max_drawdown > -0.10:
            status = '正常'
            level = 'info'
        elif max_drawdown > -0.15:
            status = '警告'
            level = 'warning'
        else:
            status = '危险'
            level = 'danger'

        return {
            'max_drawdown': float(max_drawdown),
            'status': status,
            'level': level,
            'value': f'{max_drawdown:.1%}'
        }

    def generate_risk_report(self) -> Dict:
        """生成每日风险报告"""
        print("=" * 60)
        print("📊 持仓风险监控")
        print("=" * 60)

        # 加载数据
        portfolio = self.load_portfolio()
        stock_data = self.load_stock_data()

        print(f"持仓数量: {len(portfolio.get('positions', []))}")
        print(f"数据日期范围: {len(stock_data)}条记录")
        print()

        # 计算各项指标
        volatility = self.calculate_portfolio_volatility(portfolio, stock_data)
        print(f"✓ 组合波动率: {volatility['value']} ({volatility['status']})")

        var = self.calculate_var(portfolio, stock_data)
        print(f"✓ VaR(10日,95%): {var['value']} ({var['status']})")

        drawdown = self.calculate_max_drawdown(portfolio, stock_data)
        print(f"✓ 最大回撤: {drawdown.get('value', '0%')} ({drawdown.get('status', 'N/A')})")

        industry = self.calculate_industry_deviation(portfolio)
        print(f"✓ 行业偏离度: {industry['status']}")

        concentration = self.calculate_concentration(portfolio)
        print(f"✓ 个股集中度: {concentration['status']}")

        print()

        # 汇总报告
        report = {
            'report_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'risk_indicators': {
                'volatility': volatility,
                'var': var,
                'max_drawdown': drawdown
            },
            'industry_deviation': industry,
            'concentration': concentration,
            'overall_status': self._calculate_overall_status([
                volatility['level'],
                var['level'],
                drawdown.get('level', 'info'),
                industry['level'],
                concentration['level']
            ])
        }

        # 保存报告
        os.makedirs(os.path.dirname(self.risk_report_file), exist_ok=True)
        with open(self.risk_report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"✓ 风险报告已保存: {self.risk_report_file}")
        print("=" * 60)
        print()

        return report

    def _calculate_overall_status(self, levels: List[str]) -> str:
        """计算整体状态"""
        if 'danger' in levels:
            return 'danger'
        elif 'warning' in levels:
            return 'warning'
        else:
            return 'normal'

    def format_report(self, report: Dict) -> str:
        """格式化报告为文本"""
        lines = []
        lines.append('📊 每日风险监控')
        lines.append('')

        # 风险指标
        lines.append('一、风险指标')
        risk = report['risk_indicators']
        lines.append(f"• 组合波动率：{risk['volatility']['value']}（{risk['volatility']['status']}）")
        lines.append(f"• VaR({risk['var']['confidence']}）：{risk['var']['value']}（{risk['var']['status']}）")
        drawdown_val = risk['max_drawdown'].get('value', '0%')
        drawdown_status = risk['max_drawdown'].get('status', 'N/A')
        lines.append(f"• 最大回撤：{drawdown_val}（{drawdown_status}）")
        lines.append('')

        # 行业偏离度
        lines.append('二、行业偏离度')
        for dev in report['industry_deviation']['deviations'][:3]:
            sign = '+' if dev['deviation'] > 0 else ''
            lines.append(f"• {dev['industry']}：{sign}{dev['deviation']}%（{dev['status']}）")
        lines.append('')

        # 个股集中度
        lines.append('三、个股集中度')
        for conc in report['concentration']['concentrations'][:3]:
            lines.append(f"• {conc['name']}：{conc['weight']}%（{conc['status']}）")
        lines.append('')

        return '\n'.join(lines)

def main():
    """主函数"""
    monitor = PortfolioMonitor()
    report = monitor.generate_risk_report()

    # 打印格式化报告
    print(monitor.format_report(report))

    return report

if __name__ == "__main__":
    main()
