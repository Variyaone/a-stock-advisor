#!/usr/bin/env python3
"""
A股量化系统 - 监控仪表盘
提供统一的监控接口，包括性能监控、行为监控和市场环境监控
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from code.p0_performance_metrics import calculate_performance_metrics


class MonitoringDashboard:
    """监控仪表盘"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化监控仪表盘

        Args:
            config_path: 风险配置文件路径
        """
        self.config = self._load_risk_limits(config_path)
        self.alerts = []
        self.metrics = {
            'performance': {},
            'behavior': {},
            'market_environment': {},
            'alerts': []
        }

    def _load_risk_limits(self, config_path: Optional[str] = None) -> Dict:
        """
        加载风险限制配置

        Args:
            config_path: 配置文件路径

        Returns:
            风险限制配置字典
        """
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'config', 'risk_limits.json'
            )

        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    full_config = json.load(f)
                    # 提取扁平化的配置以便使用
                    limits = full_config.get('limits', {})
                    return self._flatten_config(limits)
        except Exception as e:
            print(f"⚠️ 加载风险配置失败: {e}")

        # 默认配置（扁平化结构）
        return {
            "drawdown_limit": {
                "live_to_backtest_ratio": 1.5,
                "absolute_max": -0.25,
                "warning_threshold": -0.15
            },
            "ic_limit": {
                "min_threshold": 0.03,
                "warning_threshold": 0.05,
                "consecutive_periods": 5
            },
            "exposure_limits": {
                "industry_max_deviation": 0.10,
                "style_max_beta": 0.3,
                "position_concentration": 0.15
            },
            "performance_targets": {
                "min_annual_return": 0.15,
                "min_information_ratio": 1.5,
                "max_volatility": 0.20
            }
        }

    def _flatten_config(self, limits: Dict) -> Dict:
        """
        将嵌套的配置扁平化

        Args:
            limits: 原始嵌套配置

        Returns:
            扁平化配置
        """
        flat = {}

        # 处理 drawdown_limit
        if 'drawdown_limit' in limits:
            dd = limits['drawdown_limit']
            flat['drawdown_limit'] = {}
            for key in ['live_to_backtest_ratio', 'absolute_max', 'warning_threshold']:
                if key in dd and isinstance(dd[key], dict) and 'value' in dd[key]:
                    flat['drawdown_limit'][key] = dd[key]['value']

        # 处理 ic_limit
        if 'ic_limit' in limits:
            ic = limits['ic_limit']
            flat['ic_limit'] = {}
            for key in ['min_threshold', 'warning_threshold', 'consecutive_periods']:
                if key in ic and isinstance(ic[key], dict) and 'value' in ic[key]:
                    flat['ic_limit'][key] = ic[key]['value']

        # 处理 exposure_limits
        if 'exposure_limits' in limits:
            exp = limits['exposure_limits']
            flat['exposure_limits'] = {}
            for key in ['industry_max_deviation', 'style_max_beta', 'position_concentration']:
                if key in exp and isinstance(exp[key], dict) and 'value' in exp[key]:
                    flat['exposure_limits'][key] = exp[key]['value']

        # 处理 performance_targets
        if 'performance_targets' in limits:
            perf = limits['performance_targets']
            flat['performance_targets'] = {}
            for key in ['min_annual_return', 'min_information_ratio', 'max_volatility', 'win_rate_target']:
                if key in perf and isinstance(perf[key], dict) and 'value' in perf[key]:
                    flat['performance_targets'][key] = perf[key]['value']

        return flat

    def monitor_performance(self,
                           portfolio_returns: pd.Series,
                           backtest_max_drawdown: float,
                           benchmark_returns: Optional[pd.Series] = None) -> Dict:
        """
        性能监控 - 监控策略收益和风险指标

        Args:
            portfolio_returns: 组合收益率序列
            backtest_max_drawdown: 历史回测最大回撤
            benchmark_returns: 基准收益率（可选）

        Returns:
            性能监控结果字典
        """
        performance_metrics = calculate_performance_metrics(portfolio_returns)

        # 检查最大回撤
        live_max_drawdown = performance_metrics.get('最大回撤', 0)
        drawdown_config = self.config.get('drawdown_limit', {})

        # 获取配置值，使用默认值如果不存在
        live_to_backtest_ratio = drawdown_config.get('live_to_backtest_ratio', 1.5)
        absolute_max = drawdown_config.get('absolute_max', -0.25)
        warning_threshold = drawdown_config.get('warning_threshold', -0.15)

        backtest_limit = backtest_max_drawdown * live_to_backtest_ratio

        drawdown_alert = None
        if live_max_drawdown < backtest_limit:
            drawdown_alert = {
                'level': 'CRITICAL',
                'message': f'实盘最大回撤 {live_max_drawdown:.2%} 超过回测{live_to_backtest_ratio}倍阈值 {backtest_limit:.2%}',
                'action': 'PAUSE_STRATEGY'
            }
            self.alerts.append(drawdown_alert)
        elif live_max_drawdown < warning_threshold:
            drawdown_alert = {
                'level': 'WARNING',
                'message': f'实盘最大回撤 {live_max_drawdown:.2%} 接近预警阈值 {warning_threshold:.2%}',
                'action': 'MONITOR_CLOSLY'
            }
            self.alerts.append(drawdown_alert)

        # 检查是否达到绝对止损线
        absolute_alert = None
        if live_max_drawdown < absolute_max:
            absolute_alert = {
                'level': 'CRITICAL',
                'message': f'实盘最大回撤 {live_max_drawdown:.2%} 达到绝对止损线 {absolute_max:.2%}',
                'action': 'STOP_STRATEGY'
            }
            self.alerts.append(absolute_alert)

        # 检查夏普比率
        sharpe_ratio = performance_metrics.get('夏普比率', 0)
        annual_return = performance_metrics.get('年化收益率', 0)

        performance_result = {
            '年度收益': annual_return,
            '年化波动率': performance_metrics.get('年化波动率', 0),
            '夏普比率': sharpe_ratio,
            '最大回撤': live_max_drawdown,
            '胜率': performance_metrics.get('胜率', 0),
            '盈亏比': performance_metrics.get('盈亏比', 0),
            '回撤检查': {
                'live_max_drawdown': live_max_drawdown,
                'backtest_limit': backtest_limit,
                'absolute_max': self.config['drawdown_limit']['absolute_max'],
                'warning_threshold': self.config['drawdown_limit']['warning_threshold'],
                'status': 'PASS' if drawdown_alert is None else 'FAIL'
            },
            '达标检查': {
                'annual_return_target': self.config['performance_targets']['min_annual_return'],
                'annual_return_status': 'PASS' if annual_return >= self.config['performance_targets']['min_annual_return'] else 'FAIL',
                'sharpe_target': self.config['performance_targets']['min_information_ratio'],
                'sharpe_status': 'PASS' if sharpe_ratio >= self.config['performance_targets']['min_information_ratio'] else 'FAIL'
            }
        }

        self.metrics['performance'] = performance_result

        return performance_result

    def monitor_behavior(self,
                        factor_scores: pd.DataFrame,
                        positions: Optional[pd.DataFrame] = None,
                        ic_series: Optional[pd.Series] = None) -> Dict:
        """
        行为监控 - 监控模型预测值分布和持仓暴露

        Args:
            factor_scores: 因子得分DataFrame
            positions: 持仓DataFrame（可选）
            ic_series: IC值序列（可选）

        Returns:
            行为监控结果字典
        """
        behavior_result = {}
        behavior_alerts = []

        # 1. 分析因子得分分布
        if factor_scores is not None and len(factor_scores) > 0:
            # 假设factor_scores是多列数据，取最后一列作为最新得分
            latest_column = factor_scores.columns[-1] if len(factor_scores.columns) > 0 else factor_scores.columns[0]
            latest_scores = factor_scores[latest_column].dropna()

            if len(latest_scores) > 0:
                score_distribution = {
                    'mean': float(latest_scores.mean()),
                    'std': float(latest_scores.std()),
                    'min': float(latest_scores.min()),
                    'max': float(latest_scores.max()),
                    'median': float(latest_scores.median()),
                    'skewness': float(latest_scores.skew()),
                    'kurtosis': float(latest_scores.kurtosis())
                }

                behavior_result['因子得分分布'] = score_distribution

                # 检查分布是否异常
                if abs(score_distribution['skewness']) > 2:
                    alert = {
                        'level': 'WARNING',
                        'message': f'因子得分分布偏度异常: {score_distribution["skewness"]:.2f}',
                        'action': 'CHECK_FACTOR'
                    }
                    behavior_alerts.append(alert)

                if score_distribution['kurtosis'] > 10:
                    alert = {
                        'level': 'WARNING',
                        'message': f'因子得分分布峰度异常: {score_distribution["kurtosis"]:.2f}',
                        'action': 'CHECK_FACTOR'
                    }
                    behavior_alerts.append(alert)

        # 2. 分析IC趋势
        if ic_series is not None and len(ic_series) > 0:
            recent_ic = ic_series.tail(10)
            ic_mean = recent_ic.mean()
            ic_std = recent_ic.std()

            ic_config = self.config.get('ic_limit', {})
            min_threshold = ic_config.get('min_threshold', 0.03)
            warning_threshold = ic_config.get('warning_threshold', 0.05)
            consecutive_periods = ic_config.get('consecutive_periods', 5)

            ic_check = {
                'recent_mean': float(ic_mean),
                'recent_std': float(ic_std),
                'current_ic': float(ic_series.iloc[-1]),
                'min_threshold': min_threshold,
                'warning_threshold': warning_threshold,
                'consecutive_periods': consecutive_periods
            }

            # 检查IC是否持续低于阈值
            below_threshold_count = (recent_ic < min_threshold).sum()
            ic_check['below_threshold_count'] = int(below_threshold_count)

            if below_threshold_count >= consecutive_periods:
                alert = {
                    'level': 'CRITICAL',
                    'message': f'IC值连续{below_threshold_count}期低于阈值{min_threshold:.2f}，触发模型复审',
                    'action': 'MODEL_REVIEW'
                }
                behavior_alerts.append(alert)

            behavior_result['IC监控'] = ic_check

        # 3. 持仓暴露分析（如果有持仓数据）
        if positions is not None and len(positions) > 0:
            # 这里可以根据实际持仓数据结构进行分析
            # 示例：持仓集中度
            if '权重' in positions.columns:
                max_weight = positions['权重'].max()
                exposure_config = self.config.get('exposure_limits', {})
                concentration_limit = exposure_config.get('position_concentration', 0.15)

                concentration_check = {
                    'max_position': float(max_weight),
                    'limit': concentration_limit,
                    'status': 'PASS' if max_weight <= concentration_limit else 'FAIL'
                }

                if concentration_check['status'] == 'FAIL':
                    alert = {
                        'level': 'WARNING',
                        'message': f'持仓集中度过高: {max_weight:.2%} 超过限制 {concentration_limit:.2%}',
                        'action': 'REDUCE_CONCENTRATION'
                    }
                    behavior_alerts.append(alert)

                behavior_result['持仓集中度'] = concentration_check

        behavior_result['alerts'] = behavior_alerts
        self.metrics['behavior'] = behavior_result
        self.alerts.extend(behavior_alerts)

        return behavior_result

    def monitor_market_environment(self,
                                   market_data: pd.DataFrame,
                                   benchmark_returns: Optional[pd.Series] = None) -> Dict:
        """
        市场环境监控 - 监控市场状态指标

        Args:
            market_data: 市场数据DataFrame（包含收益率）
            benchmark_returns: 基准收益率（可选）

        Returns:
            市场环境监控结果字典
        """
        market_result = {}

        if market_data is None or len(market_data) == 0:
            return {'error': '无市场数据'}

        # 1. 计算市场波动率
        if '收益率' in market_data.columns:
            returns = market_data['收益率'].dropna()
            volatility = returns.rolling(20).std() * np.sqrt(252)  # 20日滚动波动率
            current_volatility = volatility.iloc[-1]

            volatility_check = {
                'current': float(current_volatility),
                'mean': float(volatility.mean()),
                'percentile': float((volatility < current_volatility).mean() * 100),
                'trend': 'RISING' if current_volatility > volatility.iloc[-5] else 'FALLING'
            }

            market_result['波动率'] = volatility_check

        # 2. 计算市场相关性（如果有多个资产）
        if '收益率' in market_data.columns:
            # 可以添加更多资产计算相关性
            pass

        # 3. 市场状态判断
        market_state = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'high_volatility': current_volatility > volatility.quantile(0.75) if 'current_volatility' in locals() else False,
            'low_volatility': current_volatility < volatility.quantile(0.25) if 'current_volatility' in locals() else False
        }

        market_result['市场状态'] = market_state
        self.metrics['market_environment'] = market_result

        return market_result

    def generate_report(self) -> str:
        """
        生成监控报告

        Returns:
            格式化的监控报告字符串
        """
        report = []
        report.append("=" * 60)
        report.append("A股量化系统 - 监控仪表盘")
        report.append(f"报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 60)
        report.append("")

        # 1. 性能监控
        if 'performance' in self.metrics and self.metrics['performance']:
            report.append("📊 性能监控")
            report.append("-" * 40)

            perf = self.metrics['performance']
            report.append(f"年度收益: {perf.get('年度收益', 0):.2%}")
            report.append(f"年化波动率: {perf.get('年化波动率', 0):.2%}")
            report.append(f"夏普比率: {perf.get('夏普比率', 0):.2f}")
            report.append(f"最大回撤: {perf.get('最大回撤', 0):.2%}")
            report.append(f"胜率: {perf.get('胜率', 0):.2%}")
            report.append(f"盈亏比: {perf.get('盈亏比', 0):.2f}")
            report.append("")

            # 回撤检查
            if '回撤检查' in perf:
                dd_check = perf['回撤检查']
                status_symbol = "✅" if dd_check['status'] == 'PASS' else "❌"
                ratio = self.config.get('drawdown_limit', {}).get('live_to_backtest_ratio', 1.5)
                report.append(f"{status_symbol} 回撤检查: {dd_check['status']}")
                report.append(f"   实盘最大回撤: {dd_check['live_max_drawdown']:.2%}")
                report.append(f"   回测阈值 ({ratio}倍): {dd_check['backtest_limit']:.2%}")
                report.append(f"   预警阈值: {dd_check['warning_threshold']:.2%}")
                report.append(f"   绝对止损线: {dd_check['absolute_max']:.2%}")
                report.append("")

            # 达标检查
            if '达标检查' in perf:
                target_check = perf['达标检查']
                report.append("🎯 目标达成检查:")

                return_status = "✅" if target_check['annual_return_status'] == 'PASS' else "❌"
                target_return = target_check['annual_return_target']
                report.append(f"  {return_status} 年度收益: {perf.get('年度收益', 0):.2%} (目标: {target_return:.0%})")

                sharpe_status = "✅" if target_check['sharpe_status'] == 'PASS' else "❌"
                target_sharpe = target_check['sharpe_target']
                report.append(f"  {sharpe_status} 夏普比率: {perf.get('夏普比率', 0):.2f} (目标: {target_sharpe:.1f})")
                report.append("")

        # 2. 行为监控
        if 'behavior' in self.metrics and self.metrics['behavior']:
            report.append("🎯 行为监控")
            report.append("-" * 40)

            behavior = self.metrics['behavior']

            if '因子得分分布' in behavior:
                dist = behavior['因子得分分布']
                report.append("因子得分分布:")
                report.append(f"  均值: {dist.get('mean', 0):.4f}")
                report.append(f"  标准差: {dist.get('std', 0):.4f}")
                report.append(f"  偏度: {dist.get('skewness', 0):.4f}")
                report.append(f"  峰度: {dist.get('kurtosis', 0):.4f}")
                report.append("")

            if 'IC监控' in behavior:
                ic = behavior['IC监控']
                ic_status = "✅" if ic['below_threshold_count'] < ic['consecutive_periods'] else "❌"
                report.append(f"{ic_status} IC监控:")
                report.append(f"  近期均值: {ic.get('recent_mean', 0):.4f}")
                report.append(f"  当前IC: {ic.get('current_ic', 0):.4f}")
                report.append(f"  低阈值次数: {ic.get('below_threshold_count', 0)}/{ic['consecutive_periods']}")
                report.append(f"  最小阈值: {ic['min_threshold']:.2f}")
                report.append("")

            if '持仓集中度' in behavior:
                conc = behavior['持仓集中度']
                conc_status = "✅" if conc['status'] == 'PASS' else "❌"
                report.append(f"{conc_status} 持仓集中度:")
                report.append(f"  最大持仓: {conc.get('max_position', 0):.2%}")
                report.append(f"  限制: {conc['limit']:.0%}")
                report.append("")

        # 3. 市场环境监控
        if 'market_environment' in self.metrics and self.metrics['market_environment']:
            report.append("🌊 市场环境")
            report.append("-" * 40)

            market = self.metrics['market_environment']

            if '波动率' in market:
                vol = market['波动率']
                report.append("波动率:")
                report.append(f"  当前: {vol.get('current', 0):.2%}")
                report.append(f"  均值: {vol.get('mean', 0):.2%}")
                report.append(f"  百分位: {vol.get('percentile', 0):.1f}%")
                trend_symbol = "📈" if vol.get('trend') == 'RISING' else "📉"
                report.append(f"  趋势: {trend_symbol} {vol.get('trend', 'N/A')}")
                report.append("")

            if '市场状态' in market:
                state = market['市场状态']
                report.append("市场状态:")
                if state.get('high_volatility'):
                    report.append("  ⚠️ 高波动环境")
                elif state.get('low_volatility'):
                    report.append("  ℹ️ 低波动环境")
                else:
                    report.append("  📊 正常波动环境")
                report.append("")

        # 4. 告警汇总
        if self.alerts:
            report.append("🚨 告警汇总")
            report.append("-" * 40)

            for i, alert in enumerate(self.alerts, 1):
                level_symbol = "🔴" if alert['level'] == 'CRITICAL' else "🟡"
                report.append(f"{i}. {level_symbol} [{alert['level']}] {alert['message']}")
                report.append(f"   建议操作: {alert['action']}")
                report.append("")
        else:
            report.append("✅ 无告警")
            report.append("")

        report.append("=" * 60)
        report.append("监控报告结束")
        report.append("=" * 60)

        return "\n".join(report)

    def save_metrics(self, filepath: str):
        """
        保存监控指标到文件

        Args:
            filepath: 保存路径
        """
        import pathlib

        def convert_to_serializable(obj):
            """递归转换不可序列化的对象"""
            if isinstance(obj, (bool, np.bool_)):
                return bool(obj)
            elif isinstance(obj, (int, np.integer)):
                return int(obj)
            elif isinstance(obj, (float, np.floating)):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_to_serializable(item) for item in obj]
            elif isinstance(obj, str):
                return obj
            else:
                return str(obj)

        output_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'metrics': convert_to_serializable(self.metrics),
            'alerts': convert_to_serializable(self.alerts),
            'config': convert_to_serializable(self.config)
        }

        # 确保目录存在
        pathlib.Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"✅ 监控指标已保存到: {filepath}")


def main():
    """主函数 - 演示监控仪表盘"""

    print("🔍 A股量化系统 - 监控仪表盘")
    print("=" * 60)

    # 创建监控仪表盘
    dashboard = MonitoringDashboard()

    # 演示：生成模拟数据
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=252, freq='D')
    portfolio_returns = pd.Series(np.random.normal(0.001, 0.02, 252))

    # 1. 性能监控
    print("\n📊 执行性能监控...")
    dashboard.monitor_performance(
        portfolio_returns=portfolio_returns,
        backtest_max_drawdown=-0.15
    )

    # 2. 行为监控
    print("\n🎯 执行行为监控...")
    factor_scores = pd.DataFrame({
        '股票代码': [f"{i:06d}" for i in range(100, 200)],
        'factor_score': np.random.normal(0, 1, 100)
    })
    factor_scores = factor_scores.set_index('股票代码')

    ic_series = pd.Series(np.random.normal(0.04, 0.02, 20))

    dashboard.monitor_behavior(
        factor_scores=factor_scores,
        ic_series=ic_series
    )

    # 3. 市场环境监控
    print("\n🌊 执行市场环境监控...")
    market_data = pd.DataFrame({
        '收益率': np.random.normal(0.001, 0.015, 252)
    })
    market_data.index = dates

    dashboard.monitor_market_environment(market_data=market_data)

    # 生成报告
    print("\n📋 生成监控报告...")
    report = dashboard.generate_report()
    print(report)

    # 保存指标
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports')
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"monitoring_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    dashboard.save_metrics(output_file)

    # 如果有告警，输出告警信息
    if dashboard.alerts:
        print(f"\n⚠️ 发现 {len(dashboard.alerts)} 个告警，请注意处理！")
    else:
        print("\n✅ 系统运行正常，无告警")


if __name__ == '__main__':
    main()
