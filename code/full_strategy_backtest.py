#!/usr/bin/env python3
"""
全面策略回测 - P1任务
回测所有5大类策略（15+个子策略）
生成完整回测报告和策略对比矩阵
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
import json
import os
from typing import Dict, List, Tuple, Callable
import itertools

warnings.filterwarnings('ignore')
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 导入回测引擎
from backtest_engine_v2 import BacktestEngineV2, CostModel, Portfolio

class StrategyBacktester:
    """策略回测器"""
    
    def __init__(self, data: pd.DataFrame, reports_dir: str = 'reports'):
        self.data = data
        self.reports_dir = reports_dir
        self.results = {}
        
        # 创建回测引擎（共享成本模型）
        self.cost_model = CostModel(
            commission_rate=0.0003,
            stamp_tax_rate=0.001,
            impact_cost_base=0.0005,
            impact_cost_sqrt=0.001
        )
    
    def run_all_strategies(self) -> Dict:
        """运行所有策略回测"""
        print("="*80)
        print("全面策略回测 - P1任务")
        print("="*80)
        print(f"数据范围: {self.data['date'].min()} 到 {self.data['date'].max()}")
        print(f"股票数量: {self.data['stock_code'].nunique()}")
        print(f"数据记录: {len(self.data):,}")
        print("="*80)
        
        # 1. 趋势跟踪策略
        print("\n【1/5】回测趋势跟踪策略...")
        self._backtest_trend_strategies()
        
        # 2. 均值回归策略
        print("\n【2/5】回测均值回归策略...")
        self._backtest_mean_reversion_strategies()
        
        # 3. 多因子选股
        print("\n【3/5】回测多因子选股策略...")
        self._backtest_multi_factor_strategies()
        
        # 4. 事件驱动策略
        print("\n【4/5】回测事件驱动策略...")
        self._backtest_event_driven_strategies()
        
        # 5. 市场中性策略
        print("\n【5/5】回测市场中性策略...")
        self._backtest_market_neutral_strategies()
        
        # 生成报告
        self._generate_reports()
        
        return self.results
    
    def _backtest_trend_strategies(self):
        """回测趋势跟踪策略"""
        
        # 1.1 双均线策略
        for short, long in [(5, 20), (10, 30), (20, 60)]:
            strategy_name = f"双均线_{short}日_{long}日"
            self.results[strategy_name] = self._run_dual_ma_strategy(short, long)
        
        # 1.2 MACD策略
        for fast, slow, signal in [(12, 26, 9), (8, 17, 9)]:
            strategy_name = f"MACD_{fast}_{slow}_{signal}"
            self.results[strategy_name] = self._run_macd_strategy(fast, slow, signal)
        
        # 1.3 动量突破策略
        for period in [20, 60, 120]:
            strategy_name = f"动量突破_{period}日"
            self.results[strategy_name] = self._run_momentum_breakout(period)
        
        # 1.4 布林带突破
        for period, std in [(20, 2), (20, 2.5), (10, 2)]:
            strategy_name = f"布林带突破_{period}日_{std}σ"
            self.results[strategy_name] = self._run_bollinger_breakout(period, std)
    
    def _run_dual_ma_strategy(self, short_period: int, long_period: int) -> Dict:
        """双均线策略"""
        print(f"  - 双均线 {short_period}日/{long_period}日")
        
        def signal_func(date, current_data):
            if len(current_data) < long_period:
                return {}
            
            signals = {}
            for stock_code in current_data['stock_code'].unique():
                stock_data = current_data[current_data['stock_code'] == stock_code]
                if len(stock_data) < 2:
                    continue
                
                # 检查金叉
                short_ma = stock_data[f'ma{short_period}'].values[0]
                long_ma = stock_data[f'ma{long_period}'].values[0]
                
                if pd.notna(short_ma) and pd.notna(long_ma):
                    # 前一日检查（使用全数据）
                    full_stock_data = self.data[
                        (self.data['stock_code'] == stock_code) & 
                        (self.data['date'] < date)
                    ].sort_values('date')
                    
                    if len(full_stock_data) > 0:
                        prev_short_ma = full_stock_data[f'ma{short_period}'].iloc[-1]
                        prev_long_ma = full_stock_data[f'ma{long_period}'].iloc[-1]
                        
                        # 金叉信号
                        if prev_short_ma <= prev_long_ma and short_ma > long_ma:
                            signals[stock_code] = 0.10  # 10%仓位
            
            return signals
        
        return self._run_backtest(signal_func)
    
    def _run_macd_strategy(self, fast: int, slow: int, signal: int) -> Dict:
        """MACD策略"""
        print(f"  - MACD ({fast}, {slow}, {signal})")
        
        def signal_func(date, current_data):
            signals = {}
            for stock_code in current_data['stock_code'].unique():
                stock_data = current_data[current_data['stock_code'] == stock_code].sort_values('date')
                if len(stock_data) < slow + signal:
                    continue
                
                close_prices = stock_data['close'].values
                ema_fast = pd.Series(close_prices).ewm(span=fast, adjust=False).mean().iloc[-1]
                ema_slow = pd.Series(close_prices).ewm(span=slow, adjust=False).mean().iloc[-1]
                macd = ema_fast - ema_slow
                
                # 获取前一日MACD
                prev_data = self.data[
                    (self.data['stock_code'] == stock_code) & 
                    (self.data['date'] < date)
                ].sort_values('date').tail(slow + signal)
                
                if len(prev_data) < slow + signal:
                    continue
                
                prev_close = prev_data['close'].values
                prev_ema_fast = pd.Series(prev_close).ewm(span=fast, adjust=False).mean().iloc[-1]
                prev_ema_slow = pd.Series(prev_close).ewm(span=slow, adjust=False).mean().iloc[-1]
                prev_macd = prev_ema_fast - prev_ema_slow
                
                # MACD金叉
                if prev_macd <= 0 and macd > 0:
                    signals[stock_code] = 0.10
            
            return signals
        
        return self._run_backtest(signal_func)
    
    def _run_momentum_breakout(self, period: int) -> Dict:
        """动量突破策略"""
        print(f"  - 动量突破 {period}日")
        
        def signal_func(date, current_data):
            signals = {}
            
            # 计算动量
            for stock_code in current_data['stock_code'].unique():
                stock_data = current_data[current_data['stock_code'] == stock_code]
                if len(stock_data) < 1:
                    continue
                
                momentum_col = f'momentum_{period}'
                if momentum_col not in stock_data.columns:
                    continue
                
                momentum = stock_data[momentum_col].values[0]
                
                # 动量大于10%的股票
                if pd.notna(momentum) and momentum > 0.10:
                    # 确保不是短期炒作（换手率不过高）
                    turnover = stock_data['turnover'].values[0] / 100 if pd.notna(stock_data['turnover'].values[0]) else 0
                    if turnover < 20:  # 换手率小于20%
                        signals[stock_code] = 0.08
            
            # 按动量排序，选择Top-10
            if len(signals) > 10:
                sorted_signals = sorted(signals.items(), key=lambda x: x[1], reverse=True)[:10]
                signals = dict(sorted_signals)
            
            return signals
        
        return self._run_backtest(signal_func)
    
    def _run_bollinger_breakout(self, period: int, std_dev: float) -> Dict:
        """布林带突破策略"""
        print(f"  - 布林带突破 {period}日/{std_dev}σ")
        
        def signal_func(date, current_data):
            signals = {}
            
            for stock_code in current_data['stock_code'].unique():
                stock_data = current_data[current_data['stock_code'] == stock_code]
                if len(stock_data) < period:
                    continue
                
                close = stock_data['close'].values[0]
                ma20 = stock_data[f'ma{period}'].values[0]
                
                if pd.isna(ma20):
                    continue
                
                # 计算布林带（简化）
                price_to_ma = stock_data['price_to_ma20'].values[0]
                
                # 突破上轨（价格高于均值的std_dev倍）
                if pd.notna(price_to_ma) and price_to_ma > std_dev * 0.02:  # 转换为2%
                    # 成交量确认
                    volume = stock_data['volume'].values[0]
                    vol_ma5 = stock_data['turnover_ma5'].values[0]
                    
                    if pd.notna(vol_ma5) and volume > vol_ma5 * 1.5:
                        signals[stock_code] = 0.08
            
            return signals
        
        return self._run_backtest(signal_func)
    
    def _backtest_mean_reversion_strategies(self):
        """回测均值回归策略"""
        
        # 2.1 RSI均值回归
        for period, oversold, overbought in [(14, 30, 70), (7, 25, 75)]:
            strategy_name = f"RSI均值回归_{period}日_{oversold}_{overbought}"
            self.results[strategy_name] = self._run_rsi_strategy(period, oversold, overbought)
        
        # 2.2 布林带均值回归
        for period, threshold in [(20, 2), (20, 2.5)]:
            strategy_name = f"布林带均值回归_{period}日_{threshold}σ"
            self.results[strategy_name] = self._run_bollinger_mean_reversion(period, threshold)
        
        # 2.3 偏离度策略
        strategy_name = "偏离度策略"
        self.results[strategy_name] = self._run_deviation_strategy()
        
        # 2.4 低波动策略
        strategy_name = "低波动策略"
        self.results[strategy_name] = self._run_low_volatility_strategy()
    
    def _run_rsi_strategy(self, period: int, oversold: int, overbought: int) -> Dict:
        """RSI策略（简化版本）"""
        print(f"  - RSI {period}日 ({oversold}/{overbought})")
        
        def signal_func(date, current_data):
            signals = {}
            
            for stock_code in current_data['stock_code'].unique():
                stock_data = current_data[current_data['stock_code'] == stock_code]
                if len(stock_data) < period:
                    continue
                
                # 使用动量作为RSI代理
                momentum = stock_data[f'momentum_{period}'].values[0]
                
                # 超卖买入（大幅下跌）
                if pd.notna(momentum) and momentum < -0.15:  # 跌幅超过15%
                    volatility = stock_data[f'volatility_{period}'].values[0]
                    if pd.notna(volatility) and volatility > 0.02:  # 波动率较高
                        signals[stock_code] = 0.08
            
            return signals
        
        return self._run_backtest(signal_func)
    
    def _run_bollinger_mean_reversion(self, period: int, threshold: float) -> Dict:
        """布林带均值回归"""
        print(f"  - 布林带均值回归 {period}日/{threshold}σ")
        
        def signal_func(date, current_data):
            signals = {}
            
            for stock_code in current_data['stock_code'].unique():
                stock_data = current_data[current_data['stock_code'] == stock_code]
                if len(stock_data) < period:
                    continue
                
                price_to_ma = stock_data['price_to_ma20'].values[0]
                
                # 价格跌破下轨
                if pd.notna(price_to_ma) and price_to_ma < -threshold * 0.02:  # 偏差>4%
                    signals[stock_code] = 0.08
            
            return signals
        
        return self._run_backtest(signal_func)
    
    def _run_deviation_strategy(self) -> Dict:
        """偏离度策略"""
        print("  - 偏离度策略")
        
        def signal_func(date, current_data):
            signals = {}
            
            for stock_code in current_data['stock_code'].unique():
                stock_data = current_data[current_data['stock_code'] == stock_code]
                if len(stock_data) < 20:
                    continue
                
                # 使用20日偏离度
                price_to_ma = stock_data['price_to_ma20'].values[0]
                
                # 过度下跌
                if pd.notna(price_to_ma) and price_to_ma < -0.10:  # 跌幅超过10%
                    signals[stock_code] = 0.08
            
            return signals
        
        return self._run_backtest(signal_func)
    
    def _run_low_volatility_strategy(self) -> Dict:
        """低波动策略"""
        print("  - 低波动策略")
        
        def signal_func(date, current_data):
            signals = {}
            
            # 选择波动率最低的股票
            for stock_code in current_data['stock_code'].unique():
                stock_data = current_data[current_data['stock_code'] == stock_code]
                if len(stock_data) < 20:
                    continue
                
                volatility = stock_data['volatility_20'].values[0]
                
                if pd.notna(volatility) and volatility < 0.025:  # 20日波动率<2.5%
                    signals[stock_code] = 1.0 / max(volatility, 0.01)
            
            # 归一化并选择Top-15
            if signals:
                total = sum(signals.values())
                signals = {k: v/total * 0.15 for k, v in signals.items()}  # 总仓位15%
                sorted_signals = sorted(signals.items(), key=lambda x: x[1], reverse=True)[:15]
                signals = dict(sorted_signals)
            
            return signals
        
        return self._run_backtest(signal_func)
    
    def _backtest_multi_factor_strategies(self):
        """回测多因子选股策略"""
        
        # 3.1 基本面多因子（简化：使用量价因子代理）
        strategy_name = "技术面多因子"
        self.results[strategy_name] = self._run_technical_factor_strategy()
        
        # 3.2 动量+质量因子
        strategy_name = "动量质量因子"
        self.results[strategy_name] = self._run_momentum_quality_strategy()
        
        # 3.3 价值因子（低估值）
        strategy_name = "价值因子"
        self.results[strategy_name] = self._run_value_factor_strategy()
        
        # 3.4 成长因子
        strategy_name = "成长因子"
        self.results[strategy_name] = self._run_growth_factor_strategy()
    
    def _run_technical_factor_strategy(self) -> Dict:
        """技术面多因子策略"""
        print("  - 技术面多因子")
        
        def signal_func(date, current_data):
            signals = {}
            
            for stock_code in current_data['stock_code'].unique():
                stock_data = current_data[current_data['stock_code'] == stock_code]
                if len(stock_data) < 60:
                    continue
                
                score = 0
                weights = {
                    'momentum_60': 0.3,
                    'volatility_20': -0.2,  # 低波动加分
                    'turnover': 0.1,
                    'price_to_ma20': 0.2,
                    'price_to_ma60': 0.2
                }
                
                # 动量因子
                momentum = stock_data['momentum_60'].values[0]
                if pd.notna(momentum):
                    score += momentum * weights['momentum_60'] * 10
                
                # 波动率因子（低波动更好）
                vol = stock_data['volatility_20'].values[0]
                if pd.notna(vol):
                    score += (1 - vol * 10) * 0.3
                
                # 相对强度（相对均值）
                price_to_ma20 = stock_data['price_to_ma20'].values[0]
                price_to_ma60 = stock_data['price_to_ma60'].values[0]
                if pd.notna(price_to_ma20):
                    score += price_to_ma20 * weights['price_to_ma20'] * 50
                if pd.notna(price_to_ma60):
                    score += price_to_ma60 * weights['price_to_ma60'] * 50
                
                # 换手率
                turnover = stock_data['turnover'].values[0] / 100 if pd.notna(stock_data['turnover'].values[0]) else 0
                if 5 < turnover < 15:  # 适度换手率
                    score += weights['turnover'] * 10
                
                if score > 0:
                    signals[stock_code] = score
            
            # 选择Top-20
            if signals:
                sorted_signals = sorted(signals.items(), key=lambda x: x[1], reverse=True)[:20]
                # 归一化
                total = sum(v for k, v in sorted_signals)
                signals = {k: v/total * 0.20 for k, v in sorted_signals}  # 总仓位20%
            
            return signals
        
        return self._run_backtest(signal_func)
    
    def _run_momentum_quality_strategy(self) -> Dict:
        """动量质量因子"""
        print("  - 动量质量因子")
        
        def signal_func(date, current_data):
            signals = {}
            
            for stock_code in current_data['stock_code'].unique():
                stock_data = current_data[current_data['stock_code'] == stock_code]
                if len(stock_data) < 60:
                    continue
                
                # 动量
                momentum = stock_data['momentum_60'].values[0]
                
                # 质量：低波动+适度换手
                vol = stock_data['volatility_20'].values[0]
                turnover = stock_data['turnover'].values[0] / 100 if pd.notna(stock_data['turnover'].values[0]) else 0
                
                # 筛选条件
                if (pd.notna(momentum) and momentum > 0.05 and
                    pd.notna(vol) and vol < 0.03 and
                    3 < turnover < 15):
                    # 综合评分
                    score = momentum * 100 + (1 - vol * 20) * 30 + (turnover / 15) * 20
                    signals[stock_code] = score
            
            # 选择Top-15
            if signals:
                sorted_signals = sorted(signals.items(), key=lambda x: x[1], reverse=True)[:15]
                total = sum(v for k, v in sorted_signals)
                signals = {k: v/total * 0.20 for k, v in sorted_signals}
            
            return signals
        
        return self._run_backtest(signal_func)
    
    def _run_value_factor_strategy(self) -> Dict:
        """价值因子（使用价格相对位置代理）"""
        print("  - 价值因子")
        
        def signal_func(date, current_data):
            signals = {}
            
            for stock_code in current_data['stock_code'].unique():
                stock_data = current_data[current_data['stock_code'] == stock_code]
                if len(stock_data) < 60:
                    continue
                
                # 低价指标（相对60日均线便宜）
                price_to_ma60 = stock_data['price_to_ma60'].values[0]
                
                if pd.notna(price_to_ma60) and price_to_ma60 < -0.10:  # 低于60日均线10%以上
                    # 过滤劣质：波动不过大
                    vol = stock_data['volatility_20'].values[0]
                    if pd.notna(vol) and vol < 0.05:
                        signals[stock_code] = abs(price_to_ma60) * 100
            
            # 选择Top-15
            if signals:
                sorted_signals = sorted(signals.items(), key=lambda x: x[1], reverse=True)[:15]
                total = sum(v for k, v in sorted_signals)
                signals = {k: v/total * 0.15 for k, v in sorted_signals}
            
            return signals
        
        return self._run_backtest(signal_func)
    
    def _run_growth_factor_strategy(self) -> Dict:
        """成长因子（使用动量代理）"""
        print("  - 成长因子")
        
        def signal_func(date, current_data):
            signals = {}
            
            for stock_code in current_data['stock_code'].unique():
                stock_data = current_data[current_data['stock_code'] == stock_code]
                if len(stock_data) < 120:
                    continue
                
                # 120日动量（长期成长）
                momentum = stock_data['momentum_60'].values[0] * 2  # 放大120日效果
                
                # 60日动量（加速）
                momentum_60 = stock_data['momentum_60'].values[0]
                
                # 具备成长性：长期上涨+短期加速
                if (pd.notna(momentum) and momentum > 0.20 and
                    pd.notna(momentum_60) and momentum_60 > 0.05):
                    # 适度换手率（活跃但不炒作）
                    turnover = stock_data['turnover'].values[0] / 100 if pd.notna(stock_data['turnover'].values[0]) else 0
                    if turnover < 20:
                        score = momentum * 50 + momentum_60 * 50
                        signals[stock_code] = score
            
            # 选择Top-12
            if signals:
                sorted_signals = sorted(signals.items(), key=lambda x: x[1], reverse=True)[:12]
                total = sum(v for k, v in sorted_signals)
                signals = {k: v/total * 0.20 for k, v in sorted_signals}
            
            return signals
        
        return self._run_backtest(signal_func)
    
    def _backtest_event_driven_strategies(self):
        """回测事件驱动策略"""
        
        # 4.1 突破事件（价格突破）
        strategy_name = "突破事件"
        self.results[strategy_name] = self._run_breakout_event_strategy()
        
        # 4.2 高换手事件
        strategy_name = "高换手事件"
        self.results[strategy_name] = self._run_high_turnover_strategy()
        
        # 4.3 放量上涨
        strategy_name = "放量上涨事件"
        self.results[strategy_name] = self._run_volume_surge_strategy()
        
        # 4.4 反转事件
        strategy_name = "反转事件"
        self.results[strategy_name] = self._run_reversal_event_strategy()
    
    def _run_breakout_event_strategy(self) -> Dict:
        """突破事件"""
        print("  - 突破事件")
        
        def signal_func(date, current_data):
            signals = {}
            
            for stock_code in current_data['stock_code'].unique():
                stock_data = current_data[current_data['stock_code'] == stock_code]
                if len(stock_data) < 20:
                    continue
                
                # 价格创20日新高
                close = stock_data['close'].values[0]
                high = stock_data['high'].values[0]
                
                # 检查是否创20日新高
                high_20 = self.data[
                    (self.data['stock_code'] == stock_code) & 
                    (self.data['date'] < date)
                ].tail(20)['high'].max()
                
                if pd.notna(high_20) and high > high_20:
                    # 成交量确认
                    volume = stock_data['volume'].values[0]
                    vol_ma5 = stock_data['turnover_ma5'].values[0]
                    
                    if pd.notna(vol_ma5) and volume > vol_ma5 * 1.5:
                        signals[stock_code] = 0.08
            
            # 限制数量
            if len(signals) > 10:
                sorted_signals = sorted(signals.items(), key=lambda x: x[1], reverse=True)[:10]
                signals = dict(sorted_signals)
            
            return signals
        
        return self._run_backtest(signal_func)
    
    def _run_high_turnover_strategy(self) -> Dict:
        """高换手事件"""
        print("  - 高换手事件")
        
        def signal_func(date, current_data):
            signals = {}
            
            for stock_code in current_data['stock_code'].unique():
                stock_data = current_data[current_data['stock_code'] == stock_code]
                if len(stock_data) < 5:
                    continue
                
                turnover = stock_data['turnover'].values[0] / 100 if pd.notna(stock_data['turnover'].values[0]) else 0
                
                # 换手率异常高（10-20%区间）
                if 10 <= turnover <= 20:
                    # 涨幅确认（不过度追高）
                    change_pct = stock_data['change_pct'].values[0] / 100 if pd.notna(stock_data['change_pct'].values[0]) else 0
                    
                    if 0 < change_pct < 0.05:  # 涨幅0-5%
                        signals[stock_code] = turnover
            
            # 选择Top-8
            if signals:
                sorted_signals = sorted(signals.items(), key=lambda x: x[1], reverse=True)[:8]
                total = sum(v for k, v in sorted_signals)
                signals = {k: v/total * 0.10 for k, v in sorted_signals}
            
            return signals
        
        return self._run_backtest(signal_func)
    
    def _run_volume_surge_strategy(self) -> Dict:
        """放量上涨事件"""
        print("  - 放量上涨事件")
        
        def signal_func(date, current_data):
            signals = {}
            
            for stock_code in current_data['stock_code'].unique():
                stock_data = current_data[current_data['stock_code'] == stock_code]
                if len(stock_data) < 5:
                    continue
                
                # 放量（成交额倍数）
                amount = stock_data['amount'].values[0]
                amount_ma5 = stock_data['amount_ma5'].values[0]
                
                # 上涨
                change_pct = stock_data['change_pct'].values[0] / 100 if pd.notna(stock_data['change_pct'].values[0]) else 0
                
                if (pd.notna(amount_ma5) and amount > amount_ma5 * 2 and
                    pd.notna(change_pct) and change_pct > 0.02):  # 放量2倍+涨幅>2%
                    signals[stock_code] = amount / amount_ma5
            
            # 选择Top-10
            if signals:
                sorted_signals = sorted(signals.items(), key=lambda x: x[1], reverse=True)[:10]
                total = sum(v for k, v in sorted_signals)
                signals = {k: v/total * 0.12 for k, v in sorted_signals}
            
            return signals
        
        return self._run_backtest(signal_func)
    
    def _run_reversal_event_strategy(self) -> Dict:
        """反转事件"""
        print("  - 反转事件")
        
        def signal_func(date, current_data):
            signals = {}
            
            for stock_code in current_data['stock_code'].unique():
                stock_data = current_data[current_data['stock_code'] == stock_code]
                if len(stock_data) < 20:
                    continue
                
                # 连续下跌
                prev_data = self.data[
                    (self.data['stock_code'] == stock_code) & 
                    (self.data['date'] < date)
                ].tail(5)
                
                if len(prev_data) < 5:
                    continue
                
                # 前5日累计下跌
                total_decline = (1 + prev_data['change_pct'].values/100).prod() - 1
                
                # 当日止跌/反转
                change_pct = stock_data['change_pct'].values[0] / 100 if pd.notna(stock_data['change_pct'].values[0]) else 0
                
                if total_decline < -0.10 and change_pct > 0:  # 前5日跌超10%，今日上涨
                    # 放量确认
                    volume = stock_data['volume'].values[0]
                    if len(prev_data) > 0:
                        avg_volume = prev_data['volume'].mean()
                        if pd.notna(avg_volume) and volume > avg_volume * 1.5:
                            signals[stock_code] = 0.08
            
            # 限制数量
            if len(signals) > 8:
                signals = dict(list(signals.items())[:8])
            
            return signals
        
        return self._run_backtest(signal_func)
    
    def _backtest_market_neutral_strategies(self):
        """回测市场中性策略"""
        
        # 5.1 行业中性（分散化）
        strategy_name = "行业中性分散"
        self.results[strategy_name] = self._run_industry_neutral_strategy()
        
        # 5.2 多空对冲（买入强势+卖出弱势）
        strategy_name = "多空对冲策略"
        self.results[strategy_name] = self._run_long_short_strategy()
        
        # 5.3 动量反转对冲
        strategy_name = "动量反转对冲"
        self.results[strategy_name] = self._run_momentum_reversal_hedge()
    
    def _run_industry_neutral_strategy(self) -> Dict:
        """行业中性分散策略"""
        print("  - 行业中性分散")
        
        def signal_func(date, current_data):
            signals = {}
            
            # 简单行业分组（按股票代码段）
            for stock_code in current_data['stock_code'].unique():
                stock_data = current_data[current_data['stock_code'] == stock_code]
                if len(stock_data) < 20:
                    continue
                
                # 综合评分
                momentum = stock_data['momentum_60'].values[0] if pd.notna(stock_data['momentum_60'].values[0]) else 0
                vol = stock_data['volatility_20'].values[0] if pd.notna(stock_data['volatility_20'].values[0]) else 0.05
                
                score = momentum * 50 - vol * 100
                
                if score > 0:
                    signals[stock_code] = score
            
            # 按行业分散（简单按代码段）
            final_signals = {}
            industry_groups = {}
            
            for code, score in signals.items():
                # 简单行业分组：前6位
                industry = code[:6]
                if industry not in industry_groups:
                    industry_groups[industry] = []
                industry_groups[industry].append((code, score))
            
            # 每个行业选最好的1只
            for industry, items in industry_groups.items():
                best = sorted(items, key=lambda x: x[1], reverse=True)[0]
                final_signals[best[0]] = best[1]
            
            # 归一化
            if final_signals:
                total = sum(final_signals.values())
                final_signals = {k: v/total * 0.20 for k, v in final_signals.items()}
            
            return final_signals
        
        return self._run_backtest(signal_func)
    
    def _run_long_short_strategy(self) -> Dict:
        """多空对冲策略"""
        print("  - 多空对冲策略")
        
        def signal_func(date, current_data):
            signals = {}
            
            scores = {}
            for stock_code in current_data['stock_code'].unique():
                stock_data = current_data[current_data['stock_code'] == stock_code]
                if len(stock_data) < 60:
                    continue
                
                # 动量评分
                momentum = stock_data['momentum_60'].values[0] if pd.notna(stock_data['momentum_60'].values[0]) else 0
                scores[stock_code] = momentum
            
            if not scores:
                return {}
            
            # 买入Top-K
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            top_k = sorted_scores[:5]
            bottom_k = sorted_scores[-5:]
            
            # 只做多（简化版）
            for code, score in top_k:
                if score > 0.05:
                    signals[code] = 0.04  # 每只4%仓位
            
            return signals
        
        return self._run_backtest(signal_func)
    
    def _run_momentum_reversal_hedge(self) -> Dict:
        """动量反转对冲"""
        print("  - 动量反转对冲")
        
        def signal_func(date, current_data):
            signals = {}
            
            for stock_code in current_data['stock_code'].unique():
                stock_data = current_data[current_data['stock_code'] == stock_code]
                if len(stock_data) < 120:
                    continue
                
                # 长期动量+短期反转
                momentum_120 = stock_data['momentum_60'].values[0] * 2  # 代理120日
                momentum_20 = stock_data['momentum_20'].values[0]
                
                # 长期上涨+短期调整
                if (pd.notna(momentum_120) and momentum_120 > 0.15 and
                    pd.notna(momentum_20) and momentum_20 < 0):
                    # 买入信号
                    signals[stock_code] = abs(momentum_120) * 10
            
            # 选择Top-8
            if signals:
                sorted_signals = sorted(signals.items(), key=lambda x: x[1], reverse=True)[:8]
                total = sum(v for k, v in sorted_signals)
                signals = {k: v/total * 0.15 for k, v in sorted_signals}
            
            return signals
        
        return self._run_backtest(signal_func)
    
    def _run_backtest(self, signal_func: Callable) -> Dict:
        """运行单个策略回测"""
        try:
            engine = BacktestEngineV2(
                initial_capital=1000000,
                cost_model=self.cost_model,
                max_single_position=0.10,
                max_industry_exposure=0.30,
                slippage_rate=0.001,
                fill_ratio=0.95
            )
            
            results = engine.run_backtest(self.data, signal_func, rebalance_freq='weekly')
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
    
    def _generate_reports(self):
        """生成回测报告"""
        print("\n"