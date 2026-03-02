#!/usr/bin/env python3
"""
P0任务：增强的过拟合检测模块 - 过拟合缓解
功能：
1. 加强参数敏感性测试
2. 完善IC衰减监控
3. 添加样本外验证
4. 优化交叉验证策略（Walk-Forward）

目标：确保模型稳健性，防止过拟合
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from collections import defaultdict
import json
import os
import warnings
import sys

warnings.filterwarnings('ignore')


class EnhancedOverfittingDetector:
    """增强的过拟合检测器"""

    def __init__(self, data_path: str, config: Dict = None):
        self.data_path = data_path
        self.config = config or self._default_config()
        self.df = None
        self.results = {}
        self.factor_names = []
        self._load_data()
        self._prepare_factors()

    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            'ic_periods': [5, 10, 20],
            'ic_decay_threshold': 0.3,
            'sensitivity_perturbations': [0.05, 0.1, 0.15, 0.2],
            'sensitivity_threshold_high': 0.05,
            'sensitivity_threshold_low': 0.02,
            'oos_periods': 12,
            'rolling_window': 24,
            'train_ratio': 0.7,
        }

    def _load_data(self):
        """加载数据"""
        print(f"📂 加载数据: {self.data_path}")
        self.df = pd.read_pickle(self.data_path)
        
        if 'date' in self.df.columns:
            self.df['date'] = pd.to_datetime(self.df['date'])
        
        self.df = self.df.sort_values('date')
        print(f"✓ 数据加载成功: {self.df.shape}")
        print(f"  日期范围: {self.df['date'].min()} 到 {self.df['date'].max()}")

    def _prepare_factors(self):
        """准备因子列表"""
        exclude_columns = [
            'date', 'stock_code', 'close', 'open', 'high', 'low', 'volume', 'amount',
            'month', 'factor_score', 'future_return', 'target_return',
            '股票名称', '股票代码', 'is_suspended', 'year_month'
        ]
        
        numeric_columns = self.df.select_dtypes(include=[np.number]).columns.tolist()
        self.factor_names = [col for col in numeric_columns if col not in exclude_columns]
        
        print(f"✓ 检测到 {len(self.factor_names)} 个因子")

    def calculate_forward_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算未来收益"""
        df = df.copy()
        df = df.sort_values(['stock_code', 'date'])
        
        for period in self.config['ic_periods']:
            df[f'future_return_{period}d'] = df.groupby('stock_code')['close'].pct_change(period).shift(-period)
        
        return df

    def calculate_ic_metrics(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """计算IC指标"""
        ic_results = {}
        
        for period in self.config['ic_periods']:
            return_col = f'future_return_{period}d'
            if return_col not in df.columns:
                continue
            
            period_results = {}
            
            for factor in self.factor_names:
                if factor not in df.columns:
                    continue
                
                daily_ic = df.groupby('date').apply(
                    lambda x: x[factor].corr(x[return_col]) if len(x) > 10 else np.nan
                ).dropna()
                
                if len(daily_ic) == 0:
                    continue
                
                mean_ic = daily_ic.mean()
                abs_mean_ic = np.abs(daily_ic).mean()
                std_ic = daily_ic.std()
                
                period_results[factor] = {
                    'mean_ic': float(mean_ic),
                    'abs_mean_ic': float(abs_mean_ic),
                    'std_ic': float(std_ic),
                    't_stat': float(mean_ic / (std_ic / np.sqrt(len(daily_ic))) if std_ic > 0 else 0),
                    'icir': float(mean_ic / std_ic if std_ic > 0 else 0),
                }
            
            ic_results[f'{period}d'] = period_results
        
        return ic_results

    def analyze_ic_decay(self, train_data: pd.DataFrame, test_data: pd.DataFrame) -> Dict:
        """P0-2: 完善IC衰减监控"""
        print("\n" + "=" * 70)
        print("📊 P0-2: IC衰减监控分析")
        print("=" * 70)
        
        train_ic = self.calculate_ic_metrics(train_data)
        test_ic = self.calculate_ic_metrics(test_data)
        
        decay_analysis = {}
        severe_decay_factors = []
        
        for period_key in train_ic:
            if period_key not in test_ic:
                continue
            
            period_decay = {}
            for factor in self.factor_names:
                if factor not in train_ic[period_key] or factor not in test_ic[period_key]:
                    continue
                
                train_abs = train_ic[period_key][factor]['abs_mean_ic']
                test_abs = test_ic[period_key][factor]['abs_mean_ic']
                
                if train_abs > 0:
                    decay_rate = (test_abs - train_abs) / train_abs
                else:
                    decay_rate = 0
                
                is_severe = abs(decay_rate) > self.config['ic_decay_threshold']
                
                period_decay[factor] = {
                    'train_abs_ic': train_abs,
                    'test_abs_ic': test_abs,
                    'decay_rate': decay_rate,
                    'is_severe_decay': is_severe
                }
                
                if is_severe:
                    severe_decay_factors.append(factor)
            
            decay_analysis[period_key] = period_decay
        
        print(f"  严重衰减因子数: {len(set(severe_decay_factors))}/{len(self.factor_names)}")
        
        self.results['ic_decay_analysis'] = decay_analysis
        self.results['severe_decay_factors'] = list(set(severe_decay_factors))
        
        return decay_analysis

    def enhanced_parameter_sensitivity(self, data: pd.DataFrame) -> Dict:
        """P0-1: 加强参数敏感性测试"""
        print("\n" + "=" * 70)
        print("📊 P0-1: 增强的参数敏感性测试")
        print("=" * 70)
        
        base_weights = {factor: 1.0 / len(self.factor_names) for factor in self.factor_names}
        base_ic = self._calculate_weighted_ic(data, base_weights)
        
        sensitivity_results = {}
        factor_sensitivity = defaultdict(list)
        
        for perturbation in self.config['sensitivity_perturbations']:
            for factor in self.factor_names:
                perturbed_weights = base_weights.copy()
                perturbed_weights[factor] *= (1 + perturbation)
                
                total = sum(perturbed_weights.values())
                perturbed_weights = {k: v / total for k, v in perturbed_weights.items()}
                
                perturbed_ic = self._calculate_weighted_ic(data, perturbed_weights)
                relative_change = (perturbed_ic - base_ic) / base_ic if base_ic != 0 else 0
                
                key = f'{factor}_perturb_{int(perturbation * 100)}%'
                sensitivity_results[key] = {
                    'factor': factor,
                    'perturbation': perturbation,
                    'base_ic': base_ic,
                    'perturbed_ic': perturbed_ic,
                    'relative_change': relative_change
                }
                
                factor_sensitivity[factor].append(abs(relative_change))
        
        sensitivity_summary = {}
        high_sensitivity = []
        low_sensitivity = []
        
        for factor, changes in factor_sensitivity.items():
            avg_sens = np.mean(changes)
            sensitivity_summary[factor] = {
                'mean_sensitivity': avg_sens,
                'level': 'high' if avg_sens > self.config['sensitivity_threshold_high']
                        else 'low' if avg_sens < self.config['sensitivity_threshold_low'] else 'medium'
            }
            
            if avg_sens > self.config['sensitivity_threshold_high']:
                high_sensitivity.append(factor)
            elif avg_sens < self.config['sensitivity_threshold_low']:
                low_sensitivity.append(factor)
        
        print(f"  高敏感性因子: {len(high_sensitivity)}个")
        print(f"  低敏感性因子: {len(low_sensitivity)}个")
        
        self.results['parameter_sensitivity'] = sensitivity_results
        self.results['sensitivity_summary'] = sensitivity_summary
        self.results['high_sensitivity_factors'] = high_sensitivity
        self.results['low_sensitivity_factors'] = low_sensitivity
        
        return sensitivity_results

    def _calculate_weighted_ic(self, data: pd.DataFrame, weights: Dict[str, float]) -> float:
        """计算加权IC"""
        data_copy = data.copy()
        
        factor_score = pd.Series(0.0, index=data_copy.index)
        for factor, weight in weights.items():
            if factor in data_copy.columns:
                factor_values = data_copy[factor].fillna(0)
                factor_mean = factor_values.mean()
                factor_std = factor_values.std()
                
                if factor_std > 0:
                    factor_normalized = (factor_values - factor_mean) / factor_std
                else:
                    factor_normalized = factor_values - factor_mean
                
                factor_score += factor_normalized * weight
        
        data_copy['factor_score'] = factor_score
        
        ic_values = []
        for period in self.config['ic_periods']:
            return_col = f'future_return_{period}d'
            if return_col in data_copy.columns:
                daily_ic = data_copy.groupby('date').apply(
                    lambda x: x['factor_score'].corr(x[return_col]) if len(x) > 10 else np.nan
                ).dropna()
                
                if len(daily_ic) > 0:
                    ic_values.append(np.mean(daily_ic))
        
        return np.mean(ic_values) if ic_values else 0.0

    def out_of_sample_validation(self, data: pd.DataFrame) -> Dict:
        """P0-3: 添加样本外验证"""
        print("\n" + "=" * 70)
        print("📊 P0-3: 样本外验证")
        print("=" * 70)
        
        split_idx = int(len(data) * self.config['train_ratio'])
        train_data = data.iloc[:split_idx].copy()
        oos_data = data.iloc[split_idx:].copy()
        
        train_data = self.calculate_forward_returns(train_data)
        oos_data = self.calculate_forward_returns(oos_data)
        
        train_ic = self.calculate_ic_metrics(train_data)
        oos_ic = self.calculate_ic_metrics(oos_data)
        
        oos_results = {
            'train_samples': len(train_data),
            'oos_samples': len(oos_data),
            'train_date_range': (str(train_data['date'].min()), str(train_data['date'].max())),
            'oos_date_range': (str(oos_data['date'].min()), str(oos_data['date'].max())),
            'train_ic': train_ic,
            'oos_ic': oos_ic
        }
        
        print(f"  训练集: {len(train_data):,} 样本")
        print(f"  样本外: {len(oos_data):,} 样本")
        
        self.results['out_of_sample_validation'] = oos_results
        
        return oos_results

    def walk_forward_validation(self, data: pd.DataFrame) -> Dict:
        """P0-4: Walk-Forward交叉验证"""
        print("\n" + "=" * 70)
        print("📊 P0-4: Walk-Forward交叉验证")
        print("=" * 70)
        
        data['year_month'] = data['date'].dt.to_period('M')
        unique_months = sorted(data['year_month'].unique())
        
        train_months = self.config['rolling_window']
        test_months = self.config['oos_periods']
        
        folds = []
        train_ic_list = []
        test_ic_list = []
        
        for i in range(len(unique_months) - train_months - test_months):
            train_months_list = unique_months[i : i + train_months]
            test_months_list = unique_months[i + train_months : i + train_months + test_months]
            
            train_data = data[data['year_month'].isin(train_months_list)].copy()
            test_data = data[data['year_month'].isin(test_months_list)].copy()
            
            train_data = self.calculate_forward_returns(train_data)
            test_data = self.calculate_forward_returns(test_data)
            
            train_ic = self.calculate_ic_metrics(train_data)
            test_ic = self.calculate_ic_metrics(test_data)
            
            for period_key in train_ic:
                for factor, ic_data in train_ic[period_key].items():
                    train_ic_list.append(ic_data['abs_mean_ic'])
            
            for period_key in test_ic:
                for factor, ic_data in test_ic[period_key].items():
                    test_ic_list.append(ic_data['abs_mean_ic'])
            
            folds.append({
                'fold': len(folds) + 1,
                'train_samples': len(train_data),
                'test_samples': len(test_data)
            })
        
        if train_ic_list and test_ic_list:
            summary = {
                'mean_train_ic': float(np.mean(train_ic_list)),
                'std_train_ic': float(np.std(train_ic_list)),
                'mean_test_ic': float(np.mean(test_ic_list)),
                'std_test_ic': float(np.std(test_ic_list)),
                'ic_decay_rate': (np.mean(test_ic_list) - np.mean(train_ic_list)) / np.mean(train_ic_list)
                                 if train_ic_list and np.mean(train_ic_list) > 0 else 0
            }
        else:
            summary = {}
        
        print(f"  训练集平均IC: {summary.get('mean_train_ic', 0):.4f}")
        print(f"  测试集平均IC: {summary.get('mean_test_ic', 0):.4f}")
        print(f"  IC衰减率: {summary.get('ic_decay_rate', 0):.2%}")
        
        self.results['walk_forward_validation'] = {'folds': folds, 'summary': summary}
        
        return {'folds': folds, 'summary': summary}

    def generate_diagnosis(self) -> Dict:
        """生成诊断报告"""
        print("\n" + "=" * 70)
        print("🔍 过拟合诊断报告")
        print("=" * 70)
        
        diagnosis = {
            'overall_status': 'unknown',
            'overfitting_severity': 'none',
            'issues': [],
            'recommendations': [],
            'actions_required': []
        }
        
        # IC衰减分析
        severe_decay = self.results.get('severe_decay_factors', [])
        if severe_decay:
            if len(severe_decay) > len(self.factor_names) * 0.5:
                diagnosis['overfitting_severity'] = 'severe'
                diagnosis['overall_status'] = 'overfitting_detected'
                diagnosis['issues'].append({
                    'type': 'IC Decay',
                    'severity': 'high',
                    'description': f"{len(severe_decay)}个因子出现严重IC衰减"
                })
            elif len(severe_decay) > len(self.factor_names) * 0.2:
                if diagnosis['overfitting_severity'] == 'none':
                    diagnosis['overfitting_severity'] = 'moderate'
                diagnosis['issues'].append({
                    'type': 'IC Decay',
                    'severity': 'moderate',
                    'description': f"{len(severe_decay)}个因子出现IC衰减"
                })
        
        # 参数敏感性
        high_sens = self.results.get('high_sensitivity_factors', [])
        if high_sens:
            if len(high_sens) > len(self.factor_names) * 0.5:
                if diagnosis['overfitting_severity'] != 'severe':
                    diagnosis['overfitting_severity'] = 'moderate'
                diagnosis['issues'].append({
                    'type': 'Parameter Sensitivity',
                    'severity': 'high',
                    'description': f"{len(high_sens)}个因子高度敏感"
                })
        
        # 生成建议
        diagnosis['recommendations'] = self._generate_recommendations(diagnosis)
        
        print(f"  整体状态: {diagnosis['overall_status']}")
        print(f"  严重程度: {diagnosis['overfitting_severity']}")
        
        if diagnosis['issues']:
            print(f"  发现问题: {len(diagnosis['issues'])}个")
        
        self.results['diagnosis'] = diagnosis
        
        return diagnosis

    def _generate_recommendations(self, diagnosis: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        issue_types = [issue['type'] for issue in diagnosis['issues']]
        
        if 'IC Decay' in issue_types:
            recommendations.append("降低或移除IC衰减严重的因子的权重")
            recommendations.append("使用滚动窗口动态调整因子权重")
        
        if 'Parameter Sensitivity' in issue_types:
            recommendations.append("对高敏感性因子进行正则化处理")
            recommendations.append("使用特征选择技术筛选稳健因子")
        
        recommendations.extend([
            "增加因子数量到15-20个，降低单一因子权重",
            "建立实时IC监控面板",
            "模型上线前强制执行样本外测试"
        ])
        
        return recommendations

    def run_full_detection(self) -> Dict:
        """运行完整检测"""
        print("\n" + "=" * 70)
        print("🚀 P0过拟合缓解检测")
        print("=" * 70)
        
        data = self.df.copy()
        data = self.calculate_forward_returns(data)
        
        # P0-3: 样本外验证
        self.out_of_sample_validation(data)
        
        # P0-4: Walk-Forward验证
        self.walk_forward_validation(data)
        
        # P0-2: IC衰减分析
        split_idx = int(len(data) * self.config['train_ratio'])
        self.analyze_ic_decay(data.iloc[:split_idx], data.iloc[split_idx:])
        
        # P0-1: 参数敏感性测试
        self.enhanced_parameter_sensitivity(data)
        
        # 生成诊断
        self.generate_diagnosis()
        
        print("\" + "=\" * 70)
        print("✅ P0检测完成")
        print("=" * 70)
        
        return self.results

    def save_report(self, output_dir: str = '/Users/variya/.openclaw/workspace/projects/a-stock-advisor/reports'):
        """保存报告"""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        json_path = os.path.join(output_dir, f'p0_overfitting_enhanced_{timestamp}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
        
        md_report = self._generate_markdown_report()
        md_path = os.path.join(output_dir, f'p0_overfitting_enhanced_{timestamp}.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_report)
        
        print(f"\\n✓ 报告已保存:")
        print(f"  JSON: {json_path}")
        print(f"  Markdown: {md_path}")
        
        return json_path, md_path

    def _generate_markdown_report(self) -> str:
        """生成Markdown报告"""
        lines = []
        
        lines.append("# P0过拟合缓解分析报告\\n")
        lines.append(f"**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
        lines.append(f"**因子数量:** {len(self.factor_names)}\\n")
        
        lines.append("---\\n")
        
        # 诊断结果
        diagnosis = self.results.get('diagnosis', {})
        lines.append("## \\u🔍 诊断摘要\\n")
        lines.append(f"- **整体状态:** {diagnosis.get('overall_status', 'unknown')}\\n")
        lines.append(f"- **严重程度:** {diagnosis.get('overfitting_severity', 'none')}\\n")
        
        if diagnosis.get('issues'):
            lines.append("\\n### 发现的问题\\n")
            for i, issue in enumerate(diagnosis['issues'], 1):
                severity_icon = "🔴" if issue['severity'] == 'high' else "🟡"
                lines.append(f"{i}. {severity_icon} **{issue['type']}**: {issue['description']}\\n")
        
        if diagnosis.get('recommendations'):
            lines.append("\\n### 改进建议\\n")
            for i, rec in enumerate(diagnosis['recommendations'], 1):
                lines.append(f"{i}. {rec}\\n")
        
        lines.append("\\n---\\n")
        
        # 参数敏感性
        sens_summary = self.results.get('sensitivity_summary', {})
        if sens_summary:
            lines.append("## 📊 P0-1: 参数敏感性分析\\n")
            lines.append("| 因子 | 平均敏感性 | 敏感性等级 |\\n")
            lines.append("|------|-----------|-----------|\\n")
            
            for factor, data in sens_summary.items():
                level_icon = "🔴" if data['level'] == 'high' else "🟡" if data['level'] == 'medium' else "🟢"
                lines.append(f"| {factor} | {data['mean_sensitivity']:.4f} | {level_icon} {data['level']} |\\n")
        
        lines.append("\\n---\\n")
        
        # IC衰减
        severe_decay = self.results.get('severe_decay_factors', [])
        if severe_decay:
            lines.append("## 📉 P0-2: IC衰减监控\\n")
            lines.append(f"### 严重衰减因子 ({len(severe_decay)}个)\\n")
            lines.append("| 因子 |\\n")
            lines.append("|------|\\n")
            for factor in severe_decay[:10]:
                lines.append(f"| {factor} |\\n")
        
        lines.append("\\n---\\n")
        
        # 样本外验证
        oos = self.results.get('out_of_sample_validation', {})
        if oos:
            lines.append("## 🧪 P0-3: 样本外验证\\n")
            lines.append(f"- 训练集: {oos['train_samples']:,} 样本\\n")
            lines.append(f"- 样本外: {oos['oos_samples']:,} 样本\\n")
        
        lines.append("\\n---\\n")
        
        # Walk-Forward
        wf = self.results.get('walk_forward_validation', {})
        if wf and wf.get('summary'):
            lines.append("## 🔄 P0-4: Walk-Forward验证\\n")
            summary = wf['summary']
            lines.append(f"- 训练集平均IC: {summary.get('mean_train_ic', 0):.4f}\\n")
            lines.append(f"- 测试集平均IC: {summary.get('mean_test_ic', 0):.4f}\\n")
            lines.append(f"- IC衰减率: {summary.get('ic_decay_rate', 0):.2%}\\n")
        
        return '\\n'.join(lines)


def main():
    """主函数"""
    print("=" * 70)
    print("🚀 P0过拟合缓解检测系统")
    print("=" * 70)
    
    detector = EnhancedOverfittingDetector(
        data_path='/Users/variya/.openclaw/workspace/projects/a-stock-advisor/data/mock_data.pkl'
    )
    
    results = detector.run_full_detection()
    detector.save_report()
    
    return results


if __name__ == '__main__':
    main()
