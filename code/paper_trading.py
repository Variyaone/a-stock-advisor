#!/usr/bin/env python3
"""
模拟盘系统 - 模块化设计
包含数据模块、信号模块、风控模块、交易模块分离
支持监控系统：日志、报警、异常检测
"""

import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import warnings
warnings.filterwarnings('ignore')

# 导入回测引擎
from backtest_engine_v2 import BacktestEngineV2, CostModel, Portfolio
from baseline_model import BaselineModel


# ========== 数据模块 ==========

class DataModule(ABC):
    """数据模块抽象基类"""
    
    @abstractmethod
    def get_market_data(self, date: str) -> pd.DataFrame:
        """获取市场数据"""
        pass
    
    @abstractmethod
    def get_factor_data(self, date: str) -> pd.DataFrame:
        """获取因子数据"""
        pass
    
    @abstractmethod
    def get_stock_info(self, stock_codes: List[str] = None) -> pd.DataFrame:
        """获取股票信息"""
        pass


class HistoricalDataModule(DataModule):
    """历史数据模块 - 用于回测"""
    
    def __init__(self, data_path: str):
        """
        初始化历史数据模块
        
        Args:
            data_path: 数据文件路径
        """
        self.data_path = data_path
        self.data = None
        self._load_data()
    
    def _load_data(self):
        """加载数据"""
        if self.data_path.endswith('.pkl'):
            import pickle
            with open(self.data_path, 'rb') as f:
                self.data = pickle.load(f)
        elif self.data_path.endswith('.parquet'):
            self.data = pd.read_parquet(self.data_path)
        elif self.data_path.endswith('.csv'):
            self.data = pd.read_csv(self.data_path)
        else:
            raise ValueError(f"Unsupported file format: {self.data_path}")
        
        print(f"✓ 加载数据: {self.data.shape[0]:,} 行")
    
    def get_market_data(self, date: str = None) -> pd.DataFrame:
        """
        获取市场数据
        
        Args:
            date: 日期 (None表示返回全部数据)
            
        Returns:
            市场数据DataFrame
        """
        if date is None:
            return self.data.copy()
        
        # 支持按月或按日查询
        if 'month' in self.data.columns:
            return self.data[self.data['month'] == date].copy()
        else:
            return self.data[self.data['date'] == date].copy()
    
    def get_factor_data(self, date: str = None) -> pd.DataFrame:
        """
        获取因子数据
        
        Args:
            date: 日期 (None表示返回全部数据)
            
        Returns:
            因子数据DataFrame
        """
        return self.get_market_data(date)
    
    def get_stock_info(self, stock_codes: List[str] = None) -> pd.DataFrame:
        """
        获取股票信息
        
        Args:
            stock_codes: 股票代码列表 (None表示返回全部)
            
        Returns:
            股票信息DataFrame
        """
        if stock_codes is None:
            return self.data[['stock_code', '股票名称']].drop_duplicates()
        
        return self.data[self.data['stock_code'].isin(stock_codes)].copy()


# ========== 信号模块 ==========

class SignalModule(ABC):
    """信号模块抽象基类"""
    
    @abstractmethod
    def generate_signals(self, date: str, data: pd.DataFrame) -> Dict[str, float]:
        """
        生成交易信号
        
        Args:
            date: 日期
            data: 市场数据
            
        Returns:
            股票代码到目标权重的映射
        """
        pass


class ModelBasedSignalModule(SignalModule):
    """基于模型的信号模块"""
    
    def __init__(self, model: BaselineModel, top_n: int = 10, 
                 position_size: float = 0.05):
        """
        初始化基于模型的信号模块
        
        Args:
            model: 基准模型
            top_n: 选股数量
            position_size: 单票仓位大小
        """
        self.model = model
        self.top_n = top_n
        self.position_size = position_size
    
    def generate_signals(self, date: str, data: pd.DataFrame) -> Dict[str, float]:
        """
        基于模型预测生成交易信号
        
        Args:
            date: 日期
            data: 市场数据
            
        Returns:
            股票代码到目标权重的映射
        """
        if not self.model.is_fitted:
            raise ValueError("Model must be fitted before generating signals")
        
        # 准备特征
        exclude_cols = [
            'date', 'stock_code', 'month', '股票名称', '股票代码', 'is_suspended',
            'target_return'
        ]
        
        X, _, feature_names = self.model.prepare_data(data, exclude_cols=exclude_cols)
        
        if X is None or len(X) == 0:
            return {}
        
        # 预测
        predictions = self.model.predict(X)
        
        # 获取股票代码
        stock_codes = data['stock_code'].values[:len(predictions)]
        
        # 创建预测结果DataFrame
        pred_df = pd.DataFrame({
            'stock_code': stock_codes,
            'prediction': predictions
        })
        
        # 过滤掉有问题的股票
        if '股票名称' in data.columns:
            pred_df = pred_df.merge(
                data[['stock_code', '股票名称', 'is_suspended']].drop_duplicates(),
                on='stock_code',
                how='left'
            )
            
            # 过滤ST、停牌股票
            pred_df = pred_df[
                (~pred_df['股票名称'].str.startswith('ST', na=False)) &
                (~pred_df['股票名称'].str.startswith('*ST', na=False)) &
                (pred_df['is_suspended'] != 1)
            ]
        
        # 按预测值排序，选择top N
        pred_df = pred_df.nlargest(self.top_n, 'prediction')
        
        # 生成等权信号
        signals = {code: self.position_size for code in pred_df['stock_code']}
        
        return signals


class FactorScoreSignalModule(SignalModule):
    """基于因子得分的信号模块"""
    
    def __init__(self, factor_col: str = 'factor_score', top_n: int = 10,
                 position_size: float = 0.05):
        """
        初始化因子得分信号模块
        
        Args:
            factor_col: 因子得分列名
            top_n: 选股数量
            position_size: 单票仓位大小
        """
        self.factor_col = factor_col
        self.top_n = top_n
        self.position_size = position_size
    
    def generate_signals(self, date: str, data: pd.DataFrame) -> Dict[str, float]:
        """
        基于因子得分生成交易信号
        
        Args:
            date: 日期
            data: 市场数据
            
        Returns:
            股票代码到目标权重的映射
        """
        if self.factor_col not in data.columns:
            raise ValueError(f"Factor column '{self.factor_col}' not found in data")
        
        # 获取当日数据
        day_data = data.copy()
        
        # 过滤问题股票
        if '股票名称' in day_data.columns:
            day_data = day_data[
                (~day_data['股票名称'].str.startswith('ST', na=False)) &
                (~day_data['股票名称'].str.startswith('*ST', na=False)) &
                (day_data['is_suspended'] != 1)
            ]
        
        # 按因子得分排序，选择top N
        top_stocks = day_data.nlargest(self.top_n, self.factor_col)
        
        # 生成等权信号
        signals = {code: self.position_size for code in top_stocks['stock_code']}
        
        return signals


# ========== 风控模块 ==========

class RiskModule(ABC):
    """风控模块抽象基类"""
    
    @abstractmethod
    def check(self, signals: Dict[str, float], portfolio: Portfolio, 
             data: pd.DataFrame) -> Dict[str, float]:
        """
        检查交易信号，返回修正后的信号
        
        Args:
            signals: 原始信号
            portfolio: 投资组合
            data: 市场数据
            
        Returns:
            修正后的信号
        """
        pass
    
    @abstractmethod
    def check_portfolio(self, portfolio: Portfolio, data: pd.DataFrame) -> List[str]:
        """
        检查投资组合，返回警告列表
        
        Args:
            portfolio: 投资组合
            data: 市场数据
            
        Returns:
            警告列表
        """
        pass


class BasicRiskModule(RiskModule):
    """基础风控模块"""
    
    def __init__(self, max_single_position: float = 0.10,
                 max_industry_exposure: float = 0.30,
                 max_position_count: int = 20):
        """
        初始化风控模块
        
        Args:
            max_single_position: 单票最大仓位
            max_industry_exposure: 单行业最大暴露
            max_position_count: 最大持仓数量
        """
        self.max_single_position = max_single_position
        self.max_industry_exposure = max_industry_exposure
        self.max_position_count = max_position_count
    
    def check(self, signals: Dict[str, float], portfolio: Portfolio,
             data: pd.DataFrame) -> Dict[str, float]:
        """
        检查交易信号
        
        Args:
            signals: 原始信号
            portfolio: 投资组合
            data: 市场数据
            
        Returns:
            修正后的信号
        """
        filtered_signals = {}
        
        # 获取行业信息
        industry_map = {}
        if 'industry' in data.columns:
            industry_info = data[['stock_code', 'industry']].drop_duplicates()
            industry_map = dict(zip(industry_info['stock_code'], industry_info['industry']))
        
        # 现有行业暴露
        industry_exposure = portfolio.get_industry_exposure()
        
        for stock_code, target_weight in signals.items():
            # 检查单票仓位限制
            current_weight = portfolio.get_position_weight(stock_code)
            if current_weight + target_weight > self.max_single_position:
                # 调整权重
                target_weight = max(0, self.max_single_position - current_weight)
            
            if target_weight <= 0:
                continue
            
            # 检查行业暴露限制
            if stock_code in industry_map:
                industry = industry_map[stock_code]
                current_exposure = industry_exposure.get(industry, 0)
                if current_exposure + target_weight > self.max_industry_exposure:
                    continue
            
            filtered_signals[stock_code] = target_weight
        
        return filtered_signals
    
    def check_portfolio(self, portfolio: Portfolio, data: pd.DataFrame) -> List[str]:
        """
        检查投资组合
        
        Args:
            portfolio: 投资组合
            data: 市场数据
            
        Returns:
            警告列表
        """
        warnings_list = []
        
        # 检查持仓数量
        if len(portfolio.positions) > self.max_position_count:
            warnings_list.append(
                f"持仓数量超限: {len(portfolio.positions)} > {self.max_position_count}"
            )
        
        # 检查单票仓位
        for stock_code, pos in portfolio.positions.items():
            weight = portfolio.get_position_weight(stock_code)
            if weight > self.max_single_position:
                warnings_list.append(
                    f"单票仓位超限: {stock_code} {weight:.2%} > {self.max_single_position:.2%}"
                )
        
        # 检查行业暴露
        industry_exposure = portfolio.get_industry_exposure()
        for industry, exposure in industry_exposure.items():
            if exposure > self.max_industry_exposure:
                warnings_list.append(
                    f"行业暴露超限: {industry} {exposure:.2%} > {self.max_industry_exposure:.2%}"
                )
        
        return warnings_list


# ========== 交易模块 ==========

class TradingModule:
    """交易模块"""
    
    def __init__(self, engine: BacktestEngineV2):
        """
        初始化交易模块
        
        Args:
            engine: 回测引擎
        """
        self.engine = engine
    
    def execute_signals(self, date: str, signals: Dict[str, float],
                       data: pd.DataFrame) -> List[Dict]:
        """
        执行交易信号
        
        Args:
            date: 日期
            signals: 交易信号
            data: 市场数据
            
        Returns:
            交易记录列表
        """
        trades = []
        
        # 卖出不在目标中的持仓
        stocks_to_sell = [code for code in self.engine.portfolio.positions.keys()
                         if code not in signals]
        
        for stock_code in stocks_to_sell:
            trade = self.engine.execute_sell(
                stock_code, date, data,
                order_type='market'
            )
            trades.append(trade)
        
        # 买入目标持仓
        for stock_code, target_weight in signals.items():
            target_amount = self.engine.portfolio.total_value * target_weight
            
            if target_amount > 0:
                trade = self.engine.execute_buy(
                    stock_code, date, data, data,
                    target_amount,
                    order_type='market'
                )
                trades.append(trade)
        
        return trades


# ========== 监控系统 ==========

@dataclass
class Alert:
    """报警信息"""
    level: str  # 'info', 'warning', 'error', 'critical'
    timestamp: str
    message: str
    details: Dict = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


class Monitor:
    """监控系统"""
    
    def __init__(self, log_file: str = None):
        """
        初始化监控系统
        
        Args:
            log_file: 日志文件路径
        """
        self.alerts: List[Alert] = []
        self.log_file = log_file
        
        # 设置日志
        self.logger = logging.getLogger('PaperTrading')
        self.logger.setLevel(logging.INFO)
        
        if log_file:
            fh = logging.FileHandler(log_file)
            fh.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)
        
        # 控制台日志
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
    
    def log(self, level: str, message: str, details: Dict = None):
        """
        记录日志
        
        Args:
            level: 日志级别
            message: 日志消息
            details: 详细信息
        """
        timestamp = datetime.now().isoformat()
        alert = Alert(level=level, timestamp=timestamp, message=message, details=details)
        self.alerts.append(alert)
        
        # 记录到日志系统
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        log_msg = f"{message}"
        if details:
            log_msg += f" - {json.dumps(details, ensure_ascii=False, default=str)}"
        log_func(log_msg)
    
    def info(self, message: str, details: Dict = None):
        """记录信息日志"""
        self.log('info', message, details)
    
    def warning(self, message: str, details: Dict = None):
        """记录警告日志"""
        self.log('warning', message, details)
    
    def error(self, message: str, details: Dict = None):
        """记录错误日志"""
        self.log('error', message, details)
    
    def critical(self, message: str, details: Dict = None):
        """记录严重错误日志"""
        self.log('critical', message, details)
    
    def check_anomalies(self, portfolio: Portfolio, data: pd.DataFrame) -> List[str]:
        """
        检查异常情况
        
        Args:
            portfolio: 投资组合
            data: 市场数据
            
        Returns:
            异常列表
        """
        anomalies = []
        
        # 检查现金比例异常
        cash_ratio = portfolio.cash / portfolio.total_value
        if cash_ratio > 0.9:
            anomalies.append(f"现金比例过高: {cash_ratio:.2%}")
        elif cash_ratio < 0.05:
            anomalies.append(f"现金比例过低: {cash_ratio:.2%}")
        
        # 检查持仓市值异常
        for stock_code, pos in portfolio.positions.items():
            # 检查市值是否为负
            if pos.market_value < 0:
                anomalies.append(f"持仓市值异常: {stock_code} {pos.market_value}")
            
            # 检查持仓数量是否异常
            if pos.quantity <= 0:
                anomalies.append(f"持仓数量异常: {stock_code} {pos.quantity}")
        
        return anomalies
    
    def get_alerts(self, level: str = None) -> List[Alert]:
        """
        获取报警列表
        
        Args:
            level: 日志级别过滤 (None表示全部)
            
        Returns:
            报警列表
        """
        if level is None:
            return self.alerts
        
        return [a for a in self.alerts if a.level == level]
    
    def save_alerts(self, filepath: str):
        """
        保存报警列表
        
        Args:
            filepath: 文件路径
        """
        alert_dicts = [a.to_dict() for a in self.alerts]
        with open(filepath, 'w') as f:
            json.dump(alert_dicts, f, ensure_ascii=False, indent=2, default=str)
        
        self.info(f"报警列表已保存: {filepath}")


# ========== 模拟盘系统 ==========

class PaperTradingSystem:
    """模拟盘系统"""
    
    def __init__(self,
                 data_module: DataModule,
                 signal_module: SignalModule,
                 risk_module: RiskModule,
                 initial_capital: float = 1000000.0,
                 cost_model: CostModel = None,
                 log_file: str = None):
        """
        初始化模拟盘系统
        
        Args:
            data_module: 数据模块
            signal_module: 信号模块
            risk_module: 风控模块
            initial_capital: 初始资金
            cost_model: 成本模型
            log_file: 日志文件路径
        """
        self.data_module = data_module
        self.signal_module = signal_module
        self.risk_module = risk_module
        self.cost_model = cost_model or CostModel()
        
        # 创建回测引擎
        self.engine = BacktestEngineV2(
            initial_capital=initial_capital,
            cost_model=self.cost_model,
            max_single_position=risk_module.max_single_position,
            max_industry_exposure=risk_module.max_industry_exposure
        )
        
        # 创建交易模块
        self.trading_module = TradingModule(self.engine)
        
        # 创建监控系统
        self.monitor = Monitor(log_file=log_file)
        
        self.is_running = False
        self.trades_history: List[Dict] = []
    
    def run_once(self, date: str) -> Dict:
        """
        运行一次模拟盘
        
        Args:
            date: 日期
            
        Returns:
            运行结果
        """
        self.monitor.info(f"开始运行: {date}")
        
        # 1. 获取数据
        try:
            data = self.data_module.get_market_data(date)
            self.monitor.info(f"获取市场数据: {len(data)} 行")
        except Exception as e:
            self.monitor.error(f"获取市场数据失败: {e}")
            return {'success': False, 'error': str(e)}
        
        if len(data) == 0:
            self.monitor.warning(f"无市场数据: {date}")
            return {'success': True, 'message': 'No data'}
        
        # 2. 更新持仓市值
        try:
            self.engine.update_portfolio_value(date, data)
        except Exception as e:
            self.monitor.error(f"更新持仓市值失败: {e}")
        
        # 3. 检查投资组合
        try:
            portfolio_warnings = self.risk_module.check_portfolio(
                self.engine.portfolio, data
            )
            for warning in portfolio_warnings:
                self.monitor.warning(warning)
        except Exception as e:
            self.monitor.error(f"检查投资组合失败: {e}")
        
        # 4. 检查异常
        try:
            anomalies = self.monitor.check_anomalies(
                self.engine.portfolio, data
            )
            for anomaly in anomalies:
                self.monitor.warning(anomaly)
        except Exception as e:
            self.monitor.error(f"检查异常失败: {e}")
        
        # 5. 生成交易信号
        try:
            signals = self.signal_module.generate_signals(date, data)
            self.monitor.info(f"生成交易信号: {len(signals)} 个", {'signals': signals})
        except Exception as e:
            self.monitor.error(f"生成交易信号失败: {e}")
            return {'success': False, 'error': str(e)}
        
        # 6. 风控检查
        try:
            filtered_signals = self.risk_module.check(
                signals, self.engine.portfolio, data
            )
            self.monitor.info(f"风控后信号: {len(filtered_signals)} 个")
        except Exception as e:
            self.monitor.error(f"风控检查失败: {e}")
            return {'success': False, 'error': str(e)}
        
        # 7. 执行交易
        try:
            trades = self.trading_module.execute_signals(date, filtered_signals, data)
            successful_trades = [t for t in trades if t['status'] == 'filled']
            failed_trades = [t for t in trades if t['status'] == 'failed']
            
            self.monitor.info(
                f"执行交易: 成功{len(successful_trades)}笔, 失败{len(failed_trades)}笔"
            )
            
            self.trades_history.extend(trades)
        except Exception as e:
            self.monitor.error(f"执行交易失败: {e}")
            return {'success': False, 'error': str(e)}
        
        # 8. 记录状态
        try:
            prices = dict(zip(data['stock_code'], data['close']))
            self.engine.portfolio.record_state(date, prices)
        except Exception as e:
            self.monitor.error(f"记录状态失败: {e}")
        
        # 9. 返回结果
        result = {
            'success': True,
            'date': date,
            'portfolio_value': self.engine.portfolio.total_value,
            'cash': self.engine.portfolio.cash,
            'position_count': len(self.engine.portfolio.positions),
            'signals_count': len(signals),
            'filtered_signals_count': len(filtered_signals),
            'trades_count': len(trades),
            'successful_trades': len(successful_trades)
        }
        
        self.monitor.info(f"运行完成: 总资产={result['portfolio_value']:.2f}")
        
        return result
    
    def run_backtest(self, date_list: List[str]) -> Dict:
        """
        运行回测
        
        Args:
            date_list: 日期列表
            
        Returns:
            回测结果
        """
        self.monitor.info(f"开始回测: {len(date_list)} 个周期")
        
        results = []
        
        for i, date in enumerate(date_list[:-1]):
            result = self.run_once(date)
            results.append(result)
            
            if i % max(1, len(date_list) // 10) == 0:
                progress = (i / len(date_list)) * 100
                self.monitor.info(f"进度: {progress:.1f}%")
        
        # 生成回测报告
        backtest_results = self._generate_results(results)
        
        self.monitor.info(f"回测完成")
        
        # 确保返回结果包含必要的字段
        if 'final_value' in backtest_results:
            self.monitor.info(f"最终资产: {backtest_results['final_value']:.2f}")
        if 'total_return' in backtest_results:
            self.monitor.info(f"总收益率: {backtest_results['total_return']:.2%}")
        
        return backtest_results
    
    def _generate_results(self, run_results: List[Dict]) -> Dict:
        """生成回测结果"""
        # 这里可以调用engine的generate_results方法
        return self.engine._generate_results()
    
    def get_portfolio_summary(self) -> Dict:
        """获取投资组合摘要"""
        return {
            'total_value': self.engine.portfolio.total_value,
            'cash': self.engine.portfolio.cash,
            'position_value': self.engine.portfolio.position_value,
            'position_count': len(self.engine.portfolio.positions),
            'positions': {
                code: {
                    'quantity': pos.quantity,
                    'avg_price': pos.avg_price,
                    'market_value': pos.market_value,
                    'weight': pos.market_value / self.engine.portfolio.total_value
                }
                for code, pos in self.engine.portfolio.positions.items()
            }
        }
    
    def get_monitor_summary(self) -> Dict:
        """获取监控摘要"""
        return {
            'total_alerts': len(self.monitor.alerts),
            'by_level': {
                level: len(self.monitor.get_alerts(level))
                for level in ['info', 'warning', 'error', 'critical']
            }
        }


if __name__ == '__main__':
    # 测试模拟盘系统
    print("=== 模拟盘系统测试 ===\n")
    
    # 创建模拟数据
    np.random.seed(42)
    n_samples = 1000
    dates = pd.date_range('2024-01-01', periods=n_samples)
    
    data = pd.DataFrame({
        'date': dates,
        'month': dates.strftime('%Y-%m'),
        'stock_code': np.random.choice(['000001', '000002', '600000', '600036'], n_samples),
        'close': np.random.randn(n_samples).cumsum() + 100,
        'factor_score': np.random.randn(n_samples),
        'volume': np.random.randint(1000000, 10000000, n_samples),
        '股票名称': np.random.choice(['平安银行', '万科A', '浦发银行', '招商银行'], n_samples),
        'is_suspended': np.random.choice([0, 1], n_samples, p=[0.95, 0.05])
    })
    
    # 保存到临时文件
    import tempfile
    import pickle
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pkl', delete=False) as f:
        temp_path = f.name
        pickle.dump(data, f)
    
    try:
        # 创建数据模块
        data_module = HistoricalDataModule(temp_path)
        
        # 创建信号模块
        signal_module = FactorScoreSignalModule(factor_col='factor_score', top_n=5, position_size=0.05)
        
        # 创建风控模块
        risk_module = BasicRiskModule(
            max_single_position=0.10,
            max_industry_exposure=0.30,
            max_position_count=10
        )
        
        # 创建模拟盘系统
        system = PaperTradingSystem(
            data_module=data_module,
            signal_module=signal_module,
            risk_module=risk_module,
            initial_capital=1000000,
            log_file=tempfile.mktemp(suffix='.log')
        )
        
        print(f"✓ 模拟盘系统创建成功")
        print(f"  初始资金: {system.engine.portfolio.total_value:.2f}")
        print(f"  回测引擎: {system.engine}")
        
        # 测试单次运行
        test_date = '2024-01-15'
        result = system.run_once(test_date)
        print(f"\n✓ 单次运行完成: {result}")
        
    finally:
        # 清理临时文件
        import os
        try:
            os.unlink(temp_path)
        except:
            pass
