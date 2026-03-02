#!/usr/bin/env python3
"""
过拟合检测模块
P0-2 任务：检测量化策略的过拟合问题
"""

import pandas as pd
import numpy as np
import json
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from multi_factor_model import MultiFactorScoreModel
from stock_selector import StockSelector


class OverfittingDetector:
    """过拟合检测器"""

    def __init__(self, data_path: str, split_date: str = '2023-01-01'):
        """
        Args:
            data_path: 数据文件路径
            split_date: 样本内/样本外划分日期
        """
        self.data_path = data_path
        self.split_date = pd.Timestamp(split_date)
        self.df = None
        self.in_sample = None
        self.out_of_sample = None
        self.factor_model = MultiFactorScoreModel()
        self.stock_selector = StockSelector(self.factor_model, n=10)
        self.results = {}

        self._load_data()
        self._prepare_model()

    def _load_data(self):
        """加载数据"""
        print(f"加载数据: {self.data_path}")
        self.df = pd.read_pickle(self.data_path)

        # 转换日期格式
        self.df['date'] = pd.to_datetime(self.df['date'])
        self.df = self.df.sort_values('date')

        print(f"数据形状: {self.df.shape}")
        print(f"日期范围: {self.df['date'].min()} 到 {self.df['date'].max()}")
        print(f"股票数量: {self.df['stock_code'].nunique()}")

    def _prepare_model(self):
        """准备模型"""
        # 自动检测因子并设置权重
        factor_df = self.df.groupby(['date', 'stock_code']).first().reset_index()

        # 查找因子列（排除特定列）
        exclude_columns = ['date', 'stock_code', 'close', 'month', 'factor_score', '股票名称', '股票代码']
        numeric_columns = factor_df.select_dtypes(include=[np.number]).columns.tolist()
        factor_columns = [col for col in numeric_columns if col not in exclude_columns]

        print(f"检测到因子: {factor_columns}")

        # 设置默认IC值（均匀分布）
        default_ic = {col: 0.1 for col in factor_columns}
        self.factor_model.set_ic_weighted(default_ic, factor_columns)

        # 因子名称
        self.factor_names = factor_columns

    def split_data(self):
        """分割样本内和样本外数据"""
        print(f"\n{'='*60}")
        print("样本内外分割")
        print(f"{'='*60}")

        self.in_sample = self.df[self.df['date'] < self.split_date].copy()
        self.out_of_sample = self.df[self.df['date'] >= self.split_date].copy()

        print(f"样本内数据: {self.in_sample.shape} ({self.in_sample['date'].min()} 到 {self.in_sample['date'].max()})")
        print(f"样本外数据: {self.out_of_sample.shape} ({self.out_of_sample['date'].min()} 到 {self.out_of_sample['date'].max()})")

        return self.in_sample, self.out_of_sample

    def calculate_forward_returns(self, df: pd.DataFrame, periods: List[int] = [1, 5, 10, 20]) -> pd.DataFrame:
        """
        计算未来收益

        Args:
            df: 数据
            periods: 未来的周期列表

        Returns:
            添加了未来收益的DataFrame
        """
        df = df.copy()
        df = df.sort_values(['stock_code', 'date'])

        for period in periods:
            # 按股票分组计算未来收益
            df[f'future_return_{period}d'] = df.groupby('stock_code')['close'].pct_change(period).shift(-period)

        return df

    def calculate_ic(self, df: pd.DataFrame, factor_names: List[str] = None) -> Dict[str, float]:
        """
        计算IC值（信息系数，因子与未来收益的相关性）

        Args:
            df: 数据
            factor_names: 因子名称列表

        Returns:
            IC值字典
        """
        if factor_names is None:
            factor_names = self.factor_names

        ic_values = {}

        # 确保有未来收益数据
        for period in [5, 10, 20]:
            return_col = f'future_return_{period}d'
            if return_col not in df.columns:
                continue

            for factor in factor_names:
                # 对于每个日期，计算因子与未来收益的相关性
                daily_ic = df.groupby('date').apply(
                    lambda x: x[factor].corr(x[return_col]) if len(x) > 10 else np.nan
                )

                # IC的均值
                mean_ic = daily_ic.mean()

                # IC的绝对值均值（衡量预测能力）
                abs_mean_ic = np.abs(daily_ic).mean()

                # IC的标准差（衡量稳定性）
                std_ic = daily_ic.std()

                # IC的t统计量（显著性）
                t_stat = mean_ic / (std_ic / np.sqrt(daily_ic.notna().sum())) if std_ic > 0 else 0

                key = f'{factor}_{period}d'
                ic_values[key] = {
                    'mean_ic': mean_ic,
                    'abs_mean_ic': abs_mean_ic,
                    'std_ic': std_ic,
                    't_stat': t_stat,
                    'ic_risk_ratio': abs_mean_ic / std_ic if std_ic > 0 else 0
                }

        return ic_values

    def test_in_sample_performance(self) -> Dict:
        """测试样本内性能"""
        print(f"\n{'='*60}")
        print("样本内性能测试")
        print(f"{'='*60}")

        # 计算未来收益
        self.in_sample = self.calculate_forward_returns(self.in_sample)

        # 计算IC
        in_sample_ic = self.calculate_ic(self.in_sample)

        print("\n样本内IC值:")
        for key, value in list(in_sample_ic.items())[:5]:
            print(f"  {key}: IC={value['mean_ic']:.4f}, |IC|={value['abs_mean_ic']:.4f}, t-stat={value['t_stat']:.4f}")

        self.results['in_sample_ic'] = in_sample_ic

        return in_sample_ic

    def test_out_of_sample_performance(self) -> Dict:
        """测试样本外性能"""
        print(f"\n{'='*60}")
        print("样本外性能测试")
        print(f"{'='*60}")

        # 计算未来收益
        self.out_of_sample = self.calculate_forward_returns(self.out_of_sample)

        # 计算IC
        out_of_sample_ic = self.calculate_ic(self.out_of_sample)

        print("\n样本外IC值:")
        for key, value in list(out_of_sample_ic.items())[:5]:
            print(f"  {key}: IC={value['mean_ic']:.4f}, |IC|={value['abs_mean_ic']:.4f}, t-stat={value['t_stat']:.4f}")

        self.results['out_of_sample_ic'] = out_of_sample_ic

        return out_of_sample_ic

    def compare_ic_decay(self) -> Dict:
        """比较IC衰减情况"""
        print(f"\n{'='*60}")
        print("IC值衰减检测")
        print(f"{'='*60}")

        in_sample_ic = self.results.get('in_sample_ic', {})
        out_of_sample_ic = self.results.get('out_of_sample_ic', {})

        decay_info = {}

        for key in in_sample_ic.keys():
            if key in out_of_sample_ic:
                in_ic = in_sample_ic[key]['mean_ic']
                out_ic = out_of_sample_ic[key]['mean_ic']

                # IC衰减率
                if in_ic != 0:
                    decay_rate = (out_ic - in_ic) / abs(in_ic)
                else:
                    decay_rate = 0

                # IC绝对值衰减
                abs_in_ic = in_sample_ic[key]['abs_mean_ic']
                abs_out_ic = out_of_sample_ic[key]['abs_mean_ic']
                abs_decay_rate = (abs_out_ic - abs_in_ic) / abs_in_ic if abs_in_ic > 0 else 0

                decay_info[key] = {
                    'in_sample_ic': in_ic,
                    'out_sample_ic': out_ic,
                    'ic_decay_rate': decay_rate,
                    'abs_in_sample_ic': abs_in_ic,
                    'abs_out_sample_ic': abs_out_ic,
                    'abs_decay_rate': abs_decay_rate,
                    'is_severe_decay': abs_decay_rate < -0.3  # IC绝对值衰减超过30%视为严重衰减
                }

        print("\nIC衰减分析:")
        for key, value in list(decay_info.items())[:5]:
            status = "⚠️ 严重衰减" if value['is_severe_decay'] else "✓ 正常"
            print(f"  {key}:")
            print(f"    样本内IC={value['in_sample_ic']:.4f}, 样本外IC={value['out_sample_ic']:.4f}")
            print(f"    IC绝对值衰减率={value['abs_decay_rate']:.2%} {status}")

        self.results['ic_decay'] = decay_info

        return decay_info

    def parameter_sensitivity_analysis(self) -> Dict:
        """参数敏感性分析"""
        print(f"\n{'='*60}")
        print("参数敏感性分析")
        print(f"{'='*60}")

        # 基础权重
        base_weights = self.factor_model.factor_weights.copy()

        # 测试不同的权重扰动
        perturbations = [0.05, 0.1, 0.15, 0.2]  # 5%, 10%, 15%, 20%

        sensitivity_results = {}

        for perturbation in perturbations:
            # 为每个因子单独增加权重，观察影响
            for factor in base_weights.keys():
                # 创建扰动权重
                perturbed_weights = base_weights.copy()

                # 增加该因子的权重
                original_weight = perturbed_weights[factor]
                perturbed_weights[factor] = min(original_weight * (1 + perturbation), 1.0)

                # 归一化权重
                total_weight = sum(perturbed_weights.values())
                perturbed_weights = {k: v/total_weight for k, v in perturbed_weights.items()}

                # 使用扰动权重计算样本外性能
                sensitivity_ic = self._test_with_weights(perturbed_weights, self.out_of_sample)

                # 记录结果
                key = f'{factor}_perturb_{int(perturbation*100)}%'
                sensitivity_results[key] = {
                    'perturbation': perturbation,
                    'base_weight': original_weight,
                    'perturbed_weight': perturbed_weights[factor],
                    'ic_change': sensitivity_ic,
                    'ic_stability': self._calculate_ic_stability(sensitivity_ic)
                }

        # 分析敏感性
        sensitivity_summary = self._summarize_sensitivity(sensitivity_results)

        print("\n参数敏感性总结:")
        print(f"  高敏感性因子（权重变化对IC影响>5%）: {sensitivity_summary['high_sensitivity']}")
        print(f"  低敏感性因子（权重变化对IC影响<2%）: {sensitivity_summary['low_sensitivity']}")

        self.results['parameter_sensitivity'] = sensitivity_results
        self.results['sensitivity_summary'] = sensitivity_summary

        return sensitivity_results

    def _test_with_weights(self, weights: Dict[str, float], data: pd.DataFrame) -> Dict:
        """使用指定权重测试"""
        # 临时修改模型权重
        original_weights = self.factor_model.factor_weights.copy()
        self.factor_model.factor_weights = weights

        try:
            # 计算IC
            ic_values = self.calculate_ic(data)

            # 计算平均IC
            avg_ic = np.mean([v['mean_ic'] for v in ic_values.values() if not np.isnan(v['mean_ic'])])
            avg_abs_ic = np.mean([v['abs_mean_ic'] for v in ic_values.values() if not np.isnan(v['abs_mean_ic'])])

            return {
                'avg_ic': avg_ic,
                'avg_abs_ic': avg_abs_ic,
                'ic_by_factor': ic_values
            }
        finally:
            # 恢复原始权重
            self.factor_model.factor_weights = original_weights

    def _calculate_ic_stability(self, ic_result: Dict) -> float:
        """计算IC稳定性"""
        ic_values = [v['mean_ic'] for v in ic_result['ic_by_factor'].values() if not np.isnan(v['mean_ic'])]

        if len(ic_values) < 2:
            return 0.0

        # 使用变异系数（标准差/均值）衡量稳定性
        mean_ic = np.mean(ic_values)
        std_ic = np.std(ic_values)

        return std_ic / abs(mean_ic) if abs(mean_ic) > 0 else float('inf')

    def _summarize_sensitivity(self, sensitivity_results: Dict) -> Dict:
        """总结敏感性分析结果"""
        factor_sensitivity = defaultdict(list)
        high_sensitivity = []
        low_sensitivity = []

        for key, result in sensitivity_results.items():
            factor = key.split('_perturb_')[0]
            ic_change = abs(result['ic_change']['avg_abs_ic'])

            factor_sensitivity[factor].append(ic_change)

        # 计算每个因子的平均敏感性
        for factor, changes in factor_sensitivity.items():
            avg_sensitivity = np.mean(changes)

            if avg_sensitivity > 0.05:
                high_sensitivity.append(factor)
            elif avg_sensitivity < 0.02:
                low_sensitivity.append(factor)

        return {
            'factor_sensitivity': dict(factor_sensitivity),
            'high_sensitivity': high_sensitivity,
            'low_sensitivity': low_sensitivity
        }

    def backtest_strategy(self, data: pd.DataFrame, rebalance_freq: str = 'monthly') -> Dict:
        """
        回测策略

        Args:
            data: 数据
            rebalance_freq: 再平衡频率

        Returns:
            回测结果
        """
        print(f"\n{'='*60}")
        print(f"策略回测（{rebalance_freq}再平衡）")
        print(f"{'='*60}")

        # 按时间分割
        if rebalance_freq == 'monthly':
            rebalance_dates = data['date'].dt.to_period('M').unique()[:12]  # 最多12个月
        elif rebalance_freq == 'weekly':
            rebalance_dates = pd.date_range(start=data['date'].min(), end=data['date'].max(), freq='W')
        else:
            rebalance_dates = data['date'].unique()

        total_return = 0.0
        returns = []

        for i, rebalance_date in enumerate(rebalance_dates):
            # 获取再平衡日期的数据
            if isinstance(rebalance_date, pd.Period):
                rebalance_date_ts = rebalance_date.to_timestamp()
            else:
                rebalance_date_ts = rebalance_date

            rebalance_data = data[data['date'] == rebalance_date_ts]

            if len(rebalance_data) == 0:
                continue

            # 选择股票
            factor_data = rebalance_data.set_index('stock_code')

            try:
                selected_stocks = self.stock_selector.select_top_stocks(factor_data, str(rebalance_date_ts))

                # 计算组合收益（等权重）
                if len(selected_stocks) > 0:
                    # 获取下一个周期的收益
                    period = 20  # 20天持有期
                    future_return_col = f'future_return_{period}d'

                    if future_return_col in factor_data.columns:
                        portfolio_return = selected_stocks[future_return_col].mean()
                        returns.append(portfolio_return)
                        total_return += portfolio_return

                        print(f"  {rebalance_date_ts}: 选股{len(selected_stocks)}只, 组合收益={portfolio_return:.4f}")

            except Exception as e:
                print(f"  {rebalance_date_ts}: 选股失败 - {e}")
                continue

        # 计算回测指标
        if returns:
            total_return = np.sum(returns)
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe_ratio = mean_return / std_return if std_return > 0 else 0
            win_rate = sum(1 for r in returns if r > 0) / len(returns) if returns else 0
        else:
            total_return = 0.0
            mean_return = 0.0
            std_return = 0.0
            sharpe_ratio = 0.0
            win_rate = 0.0

        backtest_result = {
            'total_return': total_return,
            'mean_return': mean_return,
            'std_return': std_return,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'num_rebalances': len(returns),
            'returns': returns
        }

        print(f"\n回测摘要:")
        print(f"  总收益: {total_return:.4f}")
        print(f"  平均收益: {mean_return:.4f}")
        print(f"  收益标准差: {std_return:.4f}")
        print(f"  夏普比率: {sharpe_ratio:.4f}")
        print(f"  胜率: {win_rate:.2%}")

        return backtest_result

    def generate_diagnosis(self) -> Dict:
        """生成过拟合诊断"""
        print(f"\n{'='*60}")
        print("过拟合诊断")
        print(f"{'='*60}")

        diagnosis = {
            'is_overfitting': False,
            'overfitting_severity': 'none',
            'issues': [],
            'recommendations': []
        }

        # 1. IC衰减检测
        ic_decay = self.results.get('ic_decay', {})
        severe_decay_factors = [k for k, v in ic_decay.items() if v.get('is_severe_decay', False)]

        if severe_decay_factors:
            diagnosis['is_overfitting'] = True
            diagnosis['overfitting_severity'] = 'moderate' if len(severe_decay_factors) <= 2 else 'severe'
            diagnosis['issues'].append({
                'type': 'IC Decay',
                'description': f"{len(severe_decay_factors)}个因子出现严重IC衰减",
                'factors': severe_decay_factors
            })

        # 2. 参数敏感性检测
        sensitivity_summary = self.results.get('sensitivity_summary', {})
        high_sensitivity = sensitivity_summary.get('high_sensitivity', [])

        if len(high_sensitivity) > len(self.factor_names) / 2:
            diagnosis['is_overfitting'] = True
            if diagnosis['overfitting_severity'] != 'severe':
                diagnosis['overfitting_severity'] = 'moderate'
            diagnosis['issues'].append({
                'type': 'Parameter Sensitivity',
                'description': f"超过一半因子({len(high_sensitivity)}/{len(self.factor_names)})对参数变化高度敏感",
                'factors': high_sensitivity
            })

        # 3. 样本内外性能对比
        in_sample_ic = self.results.get('in_sample_ic', {})
        out_sample_ic = self.results.get('out_of_sample_ic', {})

        if in_sample_ic and out_sample_ic:
            avg_in_ic = np.mean([v['abs_mean_ic'] for v in in_sample_ic.values()])
            avg_out_ic = np.mean([v['abs_mean_ic'] for v in out_sample_ic.values()])

            performance_gap = (avg_in_ic - avg_out_ic) / avg_in_ic if avg_in_ic > 0 else 0

            if performance_gap > 0.5:  # 性能下降超过50%
                diagnosis['is_overfitting'] = True
                diagnosis['overfitting_severity'] = 'severe'
                diagnosis['issues'].append({
                    'type': 'Performance Gap',
                    'description': f"样本内外性能差距过大（{performance_gap:.1%}）",
                    'details': {
                        'avg_in_sample_ic': avg_in_ic,
                        'avg_out_sample_ic': avg_out_ic,
                        'performance_gap': performance_gap
                    }
                })

        # 生成建议
        diagnosis['recommendations'] = self._generate_recommendations(diagnosis)

        # 打印诊断结果
        print(f"\n诊断结果:")
        print(f"  是否过拟合: {'⚠️ 是' if diagnosis['is_overfitting'] else '✓ 否'}")
        print(f"  严重程度: {diagnosis['overfitting_severity']}")

        if diagnosis['issues']:
            print(f"\n发现的问题:")
            for issue in diagnosis['issues']:
                print(f"  - {issue['type']}: {issue['description']}")

        if diagnosis['recommendations']:
            print(f"\n改进建议:")
            for i, rec in enumerate(diagnosis['recommendations'], 1):
                print(f"  {i}. {rec}")

        self.results['diagnosis'] = diagnosis

        return diagnosis

    def _generate_recommendations(self, diagnosis: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []

        issue_types = [issue['type'] for issue in diagnosis['issues']]

        if 'IC Decay' in issue_types:
            recommendations.append("对于IC衰减严重的因子，考虑降低权重或从模型中移除")
            recommendations.append("使用滚动窗口计算IC值，动态调整因子权重")

        if 'Parameter Sensitivity' in issue_types:
            recommendations.append("对高敏感性因子进行正则化处理，降低过拟合风险")
            recommendations.append("使用更稳健的因子筛选方法，如特征选择技术")

        if 'Performance Gap' in issue_types:
            recommendations.append("扩大样本外测试时间窗口，确保策略的稳健性")
            recommendations.append("使用交叉验证方法优化模型参数，避免过拟合")

        # 通用建议
        recommendations.extend([
            "增加因子数量，减少对单个因子的依赖",
            "实现止损和风险控制机制，降低极端损失",
            "定期监控策略表现，及时调整模型参数"
        ])

        return recommendations

    def run_full_detection(self) -> Dict:
        """运行完整的过拟合检测"""
        print(f"\n{'='*60}")
        print("开始过拟合检测")
        print(f"{'='*60}")

        # 分割数据
        self.split_data()

        # 样本内测试
        self.test_in_sample_performance()

        # 样本外测试
        self.test_out_of_sample_performance()

        # IC衰减检测
        self.compare_ic_decay()

        # 参数敏感性分析
        self.parameter_sensitivity_analysis()

        # 策略回测（样本内外对比）
        print(f"\n{'='*60}")
        print("策略回测对比")
        print(f"{'='*60}")

        in_sample_backtest = self.backtest_strategy(self.in_sample, 'monthly')
        out_sample_backtest = self.backtest_strategy(self.out_of_sample, 'monthly')

        self.results['in_sample_backtest'] = in_sample_backtest
        self.results['out_sample_backtest'] = out_sample_backtest

        # 生成诊断
        diagnosis = self.generate_diagnosis()

        print(f"\n{'='*60}")
        print("过拟合检测完成")
        print(f"{'='*60}")

        return self.results

    def save_report(self, output_dir: str = '/Users/variya/.openclaw/workspace/projects/a-stock-advisor/reports'):
        """保存报告"""
        import os
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 保存JSON报告
        json_path = os.path.join(output_dir, f'overfitting_detection_{timestamp}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)

        # 生成Markdown报告
        md_report = self._generate_markdown_report()
        md_path = os.path.join(output_dir, f'overfitting_detection_{timestamp}.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_report)

        print(f"\n报告已保存:")
        print(f"  JSON: {json_path}")
        print(f"  Markdown: {md_path}")

        return json_path, md_path

    def _generate_markdown_report(self) -> str:
        """生成Markdown报告"""
        lines = []

        lines.append("# 过拟合检测报告")
        lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"检测日期划分: 样本内 < {self.split_date}, 样本外 >= {self.split_date}")

        # 诊断结果
        diagnosis = self.results.get('diagnosis', {})
        lines.append("\n## 诊断摘要")
        lines.append(f"- **是否过拟合**: {'是' if diagnosis.get('is_overfitting', False) else '否'}")
        lines.append(f"- **严重程度**: {diagnosis.get('overfitting_severity', 'none')}")

        if diagnosis.get('issues'):
            lines.append("\n### 发现的问题")
            for issue in diagnosis['issues']:
                lines.append(f"- **{issue['type']}**: {issue['description']}")

        if diagnosis.get('recommendations'):
            lines.append("\n### 改进建议")
            for i, rec in enumerate(diagnosis['recommendations'], 1):
                lines.append(f"{i}. {rec}")

        # IC衰减分析
        ic_decay = self.results.get('ic_decay', {})
        if ic_decay:
            lines.append("\n## IC衰减分析")

            for key, value in list(ic_decay.items())[:10]:
                status = "⚠️ 严重" if value.get('is_severe_decay', False) else "✓ 正常"
                lines.append(f"\n### {key}")
                lines.append(f"- 样本内IC: {value['in_sample_ic']:.4f}")
                lines.append(f"- 样本外IC: {value['out_sample_ic']:.4f}")
                lines.append(f"- IC绝对值衰减率: {value['abs_decay_rate']:.2%}")
                lines.append(f"- 状态: {status}")

        # 参数敏感性分析
        sensitivity_summary = self.results.get('sensitivity_summary', {})
        if sensitivity_summary:
            lines.append("\n## 参数敏感性分析")
            lines.append(f"- **高敏感性因子**: {', '.join(sensitivity_summary.get('high_sensitivity', []))}")
            lines.append(f"- **低敏感性因子**: {', '.join(sensitivity_summary.get('low_sensitivity', []))}")

        # 回测对比
        in_sample_bt = self.results.get('in_sample_backtest', {})
        out_sample_bt = self.results.get('out_sample_backtest', {})

        if in_sample_bt and out_sample_bt:
            lines.append("\n## 策略回测对比")

            lines.append("\n### 样本内")
            lines.append(f"- 总收益: {in_sample_bt['total_return']:.4f}")
            lines.append(f"- 平均收益: {in_sample_bt['mean_return']:.4f}")
            lines.append(f"- 夏普比率: {in_sample_bt['sharpe_ratio']:.4f}")
            lines.append(f"- 胜率: {in_sample_bt['win_rate']:.2%}")

            lines.append("\n### 样本外")
            lines.append(f"- 总收益: {out_sample_bt['total_return']:.4f}")
            lines.append(f"- 平均收益: {out_sample_bt['mean_return']:.4f}")
            lines.append(f"- 夏普比率: {out_sample_bt['sharpe_ratio']:.4f}")
            lines.append(f"- 胜率: {out_sample_bt['win_rate']:.2%}")

        # 详细IC表
        in_sample_ic = self.results.get('in_sample_ic', {})
        out_sample_ic = self.results.get('out_of_sample_ic', {})

        if in_sample_ic and out_sample_ic:
            lines.append("\n## 详细IC值对比")

            lines.append("\n| 因子 | 周期 | 样本内IC | 样本外IC | 衰减率 | 状态 |")
            lines.append("|------|------|----------|----------|--------|------|")

            for key in in_sample_ic.keys():
                if key in out_sample_ic:
                    in_ic = in_sample_ic[key]['abs_mean_ic']
                    out_ic = out_sample_ic[key]['abs_mean_ic']

                    if in_ic > 0:
                        decay_rate = (out_ic - in_ic) / in_ic
                    else:
                        decay_rate = 0

                    status = "⚠️" if decay_rate < -0.3 else "✓"

                    lines.append(f"| {key} | | {in_ic:.4f} | {out_ic:.4f} | {decay_rate:.2%} | {status} |")

        return '\n'.join(lines)


def main():
    """主函数"""
    # 创建检测器
    detector = OverfittingDetector(
        data_path='/Users/variya/.openclaw/workspace/projects/a-stock-advisor/data/mock_data.pkl',
        split_date='2023-01-01'
    )

    # 运行检测
    results = detector.run_full_detection()

    # 保存报告
    detector.save_report()

    return results


if __name__ == '__main__':
    main()
