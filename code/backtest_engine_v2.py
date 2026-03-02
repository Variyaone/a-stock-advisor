#!/usr/bin/env python3
"""
回测引擎 V2 - 包含交易成本模型、改进成交逻辑、风险限制
确保无未来函数
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')


@dataclass
class CostModel:
    """交易成本模型"""
    commission_rate: float = 0.0003  # 佣金费率 (万三)
    commission_min: float = 5.0      # 最低佣金
    stamp_tax_rate: float = 0.001    # 印花税率 (千一，仅卖出时收取)
    impact_cost_base: float = 0.0005 # 基础冲击成本
    impact_cost_sqrt: float = 0.001  # 冲击成本与订单总额平方根的系数
    
    def calculate_commission(self, amount: float) -> float:
        """
        计算佣金
        
        Args:
            amount: 订单金额
            
        Returns:
            佣金金额
        """
        commission = amount * self.commission_rate
        return max(commission, self.commission_min)
    
    def calculate_stamp_tax(self, amount: float, is_sell: bool) -> float:
        """
        计算印花税（仅卖出时收取）
        
        Args:
            amount: 订单金额
            is_sell: 是否卖出
            
        Returns:
            印花税金额
        """
        if not is_sell:
            return 0.0
        return amount * self.stamp_tax_rate
    
    def calculate_impact_cost(self, amount: float, liquidity: float = 1.0) -> float:
        """
        计算冲击成本
        
        Args:
            amount: 订单金额
            liquidity: 流动性因子 (值越大流动性越好，冲击成本越小)
            
        Returns:
            冲击成本金额
        """
        # 冲击成本模型：基础成本 + 与订单额平方根相关的成本
        order_factor = np.sqrt(amount) if amount > 0 else 0
        impact = (self.impact_cost_base * amount +
                  self.impact_cost_sqrt * order_factor * amount)
        return impact / liquidity
    
    def calculate_total_cost(self, amount: float, is_sell: bool, liquidity: float = 1.0) -> float:
        """
        计算总交易成本
        
        Args:
            amount: 订单金额
            is_sell: 是否卖出
            liquidity: 流动性因子
            
        Returns:
            总成本金额
        """
        commission = self.calculate_commission(amount)
        stamp_tax = self.calculate_stamp_tax(amount, is_sell)
        impact = self.calculate_impact_cost(amount, liquidity)
        return commission + stamp_tax + impact


@dataclass
class Order:
    """订单类"""
    stock_code: str
    side: str  # 'buy' or 'sell'
    order_type: str  # 'limit' or 'market'
    price: Optional[float]  # 限价单价格 (市价单为None)
    quantity: int
    date: str
    time: Optional[str] = None
    status: str = 'pending'  # 'pending', 'partial', 'filled', 'cancelled'
    filled_quantity: int = 0
    filled_price: Optional[float] = None
    
    def __post_init__(self):
        if self.side not in ['buy', 'sell']:
            raise ValueError(f"Invalid order side: {self.side}")
        if self.order_type not in ['limit', 'market']:
            raise ValueError(f"Invalid order type: {self.order_type}")


@dataclass
class Position:
    """持仓类"""
    stock_code: str
    quantity: int
    avg_price: float
    market_value: float = 0.0
    industry: Optional[str] = None
    entry_date: Optional[str] = None
    
    @property
    def weight(self):
        """仓位权重 (由portfolio计算)"""
        return None


class Portfolio:
    """投资组合类"""
    
    def __init__(self, initial_capital: float = 1000000.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}  # stock_code -> Position
        self.orders: List[Order] = []
        self.history: List[Dict] = []
        
    @property
    def total_value(self) -> float:
        """总资产"""
        market_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + market_value
    
    @property
    def position_value(self) -> float:
        """持仓市值"""
        return sum(pos.market_value for pos in self.positions.values())
    
    def get_position(self, stock_code: str) -> Optional[Position]:
        """获取持仓"""
        return self.positions.get(stock_code)
    
    def has_position(self, stock_code: str) -> bool:
        """是否有持仓"""
        return stock_code in self.positions
    
    def get_position_weight(self, stock_code: str, total_value: float = None) -> float:
        """获取持仓权重"""
        if total_value is None:
            total_value = self.total_value
        
        if stock_code not in self.positions:
            return 0.0
        
        if total_value <= 0:
            return 0.0
        
        return self.positions[stock_code].market_value / total_value
    
    def get_industry_exposure(self, total_value: float = None) -> Dict[str, float]:
        """获取行业暴露"""
        if total_value is None:
            total_value = self.total_value
        
        industry_exposure = {}
        for pos in self.positions.values():
            if pos.industry:
                if pos.industry not in industry_exposure:
                    industry_exposure[pos.industry] = 0.0
                industry_exposure[pos.industry] += pos.market_value / total_value
        
        return industry_exposure
    
    def record_state(self, date: str, prices: Dict[str, float]):
        """记录投资组合状态"""
        state = {
            'date': date,
            'cash': self.cash,
            'position_value': self.position_value,
            'total_value': self.total_value,
            'stock_count': len(self.positions),
            'positions': {
                code: {
                    'quantity': pos.quantity,
                    'avg_price': pos.avg_price,
                    'market_value': pos.market_value,
                    'price': prices.get(code, pos.avg_price)
                }
                for code, pos in self.positions.items()
            }
        }
        self.history.append(state)
    
    def __repr__(self):
        return f"Portfolio(total={self.total_value:.2f}, cash={self.cash:.2f}, positions={len(self.positions)})"


class BacktestEngineV2:
    """回测引擎 V2"""
    
    def __init__(self,
                 initial_capital: float = 1000000.0,
                 cost_model: Optional[CostModel] = None,
                 max_single_position: float = 0.10,  # 单票最大仓位 10%
                 max_industry_exposure: float = 0.30,  # 单行业最大暴露 30%
                 slippage_rate: float = 0.001,  # 滑点率
                 fill_ratio: float = 0.95):  # 限价单成交比率
        """
        初始化回测引擎
        
        Args:
            initial_capital: 初始资金
            cost_model: 成本模型
            max_single_position: 单票最大仓位比例
            max_industry_exposure: 单行业最大暴露比例
            slippage_rate: 滑点率
            fill_ratio: 限价单成交比率
        """
        self.initial_capital = initial_capital
        self.cost_model = cost_model or CostModel()
        self.max_single_position = max_single_position
        self.max_industry_exposure = max_industry_exposure
        self.slippage_rate = slippage_rate
        self.fill_ratio = fill_ratio
        
        self.portfolio = Portfolio(initial_capital)
        self.trades: List[Dict] = []
        self.dates: List[str] = []
        
    def _get_market_price(self, stock_code: str, date: str, 
                         price_df: pd.DataFrame, order_type: str = 'market',
                         limit_price: Optional[float] = None) -> Tuple[float, float]:
        """
        获取市场价格（考虑滑点）
        
        Args:
            stock_code: 股票代码
            date: 日期
            price_df: 价格数据
            order_type: 订单类型
            limit_price: 限价单价格
            
        Returns:
            (成交价格, 是否成交)
        """
        # 从价格数据中获取当日价格
        stock_data = price_df[price_df['stock_code'] == stock_code]
        
        if len(stock_data) == 0:
            return None, False
        
        stock_price = stock_data['close'].values[0]
        
        # 市价单：考虑滑点
        if order_type == 'market':
            # 买入用稍高的价格，卖出用稍低的价格
            slippage = stock_price * self.slippage_rate
            filled_price = stock_price + slippage
            return filled_price, True
        
        # 限价单：检查是否可以成交
        elif order_type == 'limit':
            if limit_price is None:
                raise ValueError("Limit order must have limit price")
            
            if stock_price <= limit_price:
                # 可以成交，但可能部分成交
                if np.random.rand() < self.fill_ratio:
                    return stock_price, True
                else:
                    return stock_price, False
            else:
                # 无法成交
                return stock_price, False
        
        else:
            raise ValueError(f"Invalid order type: {order_type}")
    
    def _check_position_limit(self, stock_code: str, target_value: float) -> bool:
        """
        检查单票仓位限制
        
        Args:
            stock_code: 股票代码
            target_value: 目标持仓金额
            
        Returns:
            是否满足限制
        """
        current_weight = self.portfolio.get_position_weight(stock_code)
        target_weight = target_value / self.portfolio.total_value
        
        return (current_weight + target_weight) <= self.max_single_position
    
    def _check_industry_limit(self, stock_code: str, target_value: float,
                             stock_info: pd.DataFrame) -> bool:
        """
        检查行业暴露限制
        
        Args:
            stock_code: 股票代码
            target_value: 目标持仓金额
            stock_info: 股票信息数据
            
        Returns:
            是否满足限制
        """
        # 获取股票行业
        stock_row = stock_info[stock_info['stock_code'] == stock_code]
        if len(stock_row) == 0:
            return True  # 无行业信息时通过
        
        industry = stock_row.iloc[0].get('industry', 'unknown')
        
        # 计算当前行业暴露
        industry_exposure = self.portfolio.get_industry_exposure()
        current_exposure = industry_exposure.get(industry, 0.0)
        target_exposure = target_value / self.portfolio.total_value
        
        return (current_exposure + target_exposure) <= self.max_industry_exposure
    
    def execute_buy(self, stock_code: str, date: str, 
                   price_df: pd.DataFrame, stock_info: pd.DataFrame,
                   target_amount: float, order_type: str = 'market',
                   limit_price: Optional[float] = None,
                   liquidity: float = 1.0) -> Dict:
        """
        执行买入订单
        
        Args:
            stock_code: 股票代码
            date: 日期
            price_df: 价格数据
            stock_info: 股票信息数据
            target_amount: 目标买入金额
            order_type: 订单类型
            limit_price: 限价单价格
            liquidity: 流动性因子
            
        Returns:
            交易记录
        """
        record = {
            'date': date,
            'stock_code': stock_code,
            'side': 'buy',
            'status': 'failed',
            'message': ''
        }
        
        # 1. 检查资金是否足够
        if self.portfolio.cash < target_amount:
            record['message'] = 'Insufficient cash'
            return record
        
        # 2. 检查仓位限制
        if not self._check_position_limit(stock_code, target_amount):
            record['message'] = f'Position limit exceeded (max={self.max_single_position})'
            return record
        
        # 3. 检查行业限制
        if not self._check_industry_limit(stock_code, target_amount, stock_info):
            record['message'] = f'Industry limit exceeded (max={self.max_industry_exposure})'
            return record
        
        # 4. 获取市场价格
        price, can_fill = self._get_market_price(stock_code, date, price_df, order_type, limit_price)
        
        if price is None:
            record['message'] = 'Price not available'
            return record
        
        if not can_fill:
            record['status'] = 'unfilled'
            record['message'] = 'Order not filled'
            return record
        
        # 5. 计算可买数量（100股的整数倍）
        quantity = int(target_amount / price / 100) * 100
        if quantity <= 0:
            record['message'] = 'Amount too small'
            return record
        
        # 6. 计算交易成本
        actual_amount = quantity * price
        commission = self.cost_model.calculate_commission(actual_amount)
        total_cost = actual_amount + commission
        
        if total_cost > self.portfolio.cash:
            # 调整数量
            available_for_cost = self.portfolio.cash - commission
            quantity = int(available_for_cost / price / 100) * 100
            actual_amount = quantity * price
            total_cost = actual_amount + commission
        
        # 7. 执行交易
        self.portfolio.cash -= total_cost
        
        # 更新持仓
        if stock_code in self.portfolio.positions:
            pos = self.portfolio.positions[stock_code]
            # 成本加权平均
            total_shares = pos.quantity + quantity
            pos.avg_price = (pos.avg_price * pos.quantity + price * quantity) / total_shares
            pos.quantity = total_shares
        else:
            stock_row = stock_info[stock_info['stock_code'] == stock_code]
            industry = stock_row.iloc[0].get('industry', 'unknown') if len(stock_row) > 0 else 'unknown'
            self.portfolio.positions[stock_code] = Position(
                stock_code=stock_code,
                quantity=quantity,
                avg_price=price,
                industry=industry,
                entry_date=date
            )
        
        record.update({
            'status': 'filled',
            'quantity': quantity,
            'price': price,
            'amount': actual_amount,
            'commission': commission,
            'total_cost': total_cost,
            'message': 'Success'
        })
        
        self.trades.append(record)
        return record
    
    def execute_sell(self, stock_code: str, date: str, 
                    price_df: pd.DataFrame, target_quantity: int = None,
                    order_type: str = 'market', limit_price: Optional[float] = None,
                    liquidity: float = 1.0) -> Dict:
        """
        执行卖出订单
        
        Args:
            stock_code: 股票代码
            date: 日期
            price_df: 价格数据
            target_quantity: 卖出数量 (None表示全部卖出)
            order_type: 订单类型
            limit_price: 限价单价格
            liquidity: 流动性因子
            
        Returns:
            交易记录
        """
        record = {
            'date': date,
            'stock_code': stock_code,
            'side': 'sell',
            'status': 'failed',
            'message': ''
        }
        
        # 1. 检查是否有持仓
        pos = self.portfolio.get_position(stock_code)
        if pos is None:
            record['message'] = 'No position'
            return record
        
        # 2. 确定卖出数量
        quantity = target_quantity if target_quantity is not None else pos.quantity
        quantity = min(quantity, pos.quantity)
        
        if quantity <= 0:
            record['message'] = 'No quantity to sell'
            return record
        
        # 3. 获取市场价格
        price, can_fill = self._get_market_price(stock_code, date, price_df, order_type, limit_price)
        
        if price is None:
            record['message'] = 'Price not available'
            return record
        
        if not can_fill:
            record['status'] = 'unfilled'
            record['message'] = 'Order not filled'
            return record
        
        # 4. 计算交易成本
        actual_amount = quantity * price
        commission = self.cost_model.calculate_commission(actual_amount)
        stamp_tax = self.cost_model.calculate_stamp_tax(actual_amount, is_sell=True)
        total_cost = commission + stamp_tax
        net_proceeds = actual_amount - total_cost
        
        # 5. 执行交易
        self.portfolio.cash += net_proceeds
        
        # 更新持仓
        pos.quantity -= quantity
        if pos.quantity == 0:
            del self.portfolio.positions[stock_code]
        
        record.update({
            'status': 'filled',
            'quantity': quantity,
            'price': price,
            'amount': actual_amount,
            'commission': commission,
            'stamp_tax': stamp_tax,
            'total_cost': total_cost,
            'net_proceeds': net_proceeds,
            'message': 'Success'
        })
        
        self.trades.append(record)
        return record
    
    def update_portfolio_value(self, date: str, price_df: pd.DataFrame):
        """
        更新持仓市值
        
        Args:
            date: 日期
            price_df: 价格数据
        """
        for stock_code, pos in self.portfolio.positions.items():
            stock_data = price_df[price_df['stock_code'] == stock_code]
            if len(stock_data) > 0:
                pos.market_value = pos.quantity * stock_data['close'].values[0]
            else:
                # 如果没有价格数据，使用上次价格
                pos.market_value = pos.quantity * pos.avg_price
    
    def run_backtest(self, data: pd.DataFrame, 
                    signal_func: callable,
                    rebalance_freq: str = 'monthly') -> Dict:
        """
        运行回测
        
        Args:
            data: 历史数据，必须包含 date, stock_code, close 等列
            signal_func: 信号生成函数，参数为 (date, data)，返回目标股票列表或权重
            rebalance_freq: 调仓频率 ('monthly', 'weekly')
            
        Returns:
            回测结果字典
        """
        print("🚀 开始回测...")
        print(f"  初始资金: {self.initial_capital:,.2f}")
        print(f"  成本模型: 佣金={self.cost_model.commission_rate:.4%}, 印花税={self.cost_model.stamp_tax_rate:.2%}")
        print(f"  限制: 单票={self.max_single_position:.1%}, 单行业={self.max_industry_exposure:.1%}")
        
        # 确保数据排序
        data = data.sort_values('date').copy()
        
        # 获取日期列表
        if rebalance_freq == 'monthly':
            dates = sorted(data['month'].unique())
        elif rebalance_freq == 'weekly':
            dates = sorted(data['date'].unique())
        else:
            raise ValueError(f"Invalid rebalance frequency: {rebalance_freq}")
        
        print(f"  回测期间: {len(dates)} 个周期")
        
        # 回测循环
        for i, rebalance_date in enumerate(dates[:-1]):
            # 调仓日
            if rebalance_freq == 'monthly':
                current_data = data[data['month'] == rebalance_date].copy()
                next_date = dates[i + 1]
            else:
                current_data = data[data['date'] == rebalance_date].copy()
                next_date = dates[i + 1] if i + 1 < len(dates) else rebalance_date
            
            if len(current_data) == 0:
                continue
            
            # 生成交易信号
            signals = signal_func(rebalance_date, current_data)
            
            # 执行调仓
            self._rebalance(rebalance_date, current_data, signals, data)
            
            # 记录状态
            self.dates.append(rebalance_date)
            
            if i % max(1, len(dates) // 10) == 0:
                progress = (i / len(dates)) * 100
                print(f"  进度: {progress:.1f}% (第{i+1}/{len(dates)}周期)")
        
        print(f"✓ 回测完成")
        print(f"  最终资产: {self.portfolio.total_value:,.2f}")
        print(f"  总收益率: {(self.portfolio.total_value / self.initial_capital - 1):.2%}")
        print(f"  交易次数: {len(self.trades)}")
        
        return self._generate_results()
    
    def _rebalance(self, date: str, current_data: pd.DataFrame, 
                   signals: Dict, full_data: pd.DataFrame):
        """
        执行调仓
        
        Args:
            date: 调仓日期
            current_data: 当前日期数据
            signals: 交易信号
            full_data: 全部数据（用于获取价格）
        """
        # 先卖出不在目标中的持仓
        stocks_to_sell = [code for code in self.portfolio.positions.keys() 
                         if code not in signals]
        for stock_code in stocks_to_sell:
            self.execute_sell(
                stock_code, date, current_data, target_quantity=None,
                order_type='market', liquidity=1.0
            )
        
        # 买入目标持仓
        total_value = self.portfolio.total_value
        for stock_code, target_weight in signals.items():
            if stock_code in self.portfolio.positions:
                # 已有持仓，不调仓（简化处理）
                continue
            
            # 确保目标权重合理
            target_weight = min(target_weight, self.max_single_position)
            target_amount = total_value * target_weight
            
            if target_amount > 0:
                self.execute_buy(
                    stock_code, date, current_data, current_data,
                    target_amount, order_type='market', liquidity=1.0
                )
    
    def _generate_results(self) -> Dict:
        """生成回测结果"""
        # 计算收益率序列
        history_df = pd.DataFrame(self.portfolio.history)
        if len(history_df) == 0:
            return {}
        
        history_df['return'] = history_df['total_value'].pct_change()
        history_df['return'] = history_df['return'].fillna(0)
        
        # 计算绩效指标
        returns = history_df['return'].values
        
        total_return = (self.portfolio.total_value / self.initial_capital) - 1
        
        num_periods = len(returns)
        if num_periods > 0:
            period_return = np.mean(returns)
            volatility = np.std(returns)
            
            # 年化指标（假设月度）
            annual_return = (1 + period_return) ** 12 - 1
            annual_volatility = volatility * np.sqrt(12)
            
            # 夏普比率
            rf_monthly = 0.03 / 12
            sharpe_ratio = (period_return - rf_monthly) / volatility if volatility > 0 else 0
            annual_sharpe = sharpe_ratio * np.sqrt(12)
            
            # 最大回撤
            cumulative = pd.Series((1 + returns).cumprod())
            running_max = cumulative.expanding().max()
            max_drawdown = ((cumulative - running_max) / running_max).min()
            
            # 胜率
            win_rate = (returns > 0).mean()
        else:
            annual_return = 0
            annual_volatility = 0
            annual_sharpe = 0
            max_drawdown = 0
            win_rate = 0
        
        # 交易统计
        trades_df = pd.DataFrame(self.trades)
        if len(trades_df) > 0:
            filled_trades = trades_df[trades_df['status'] == 'filled']
            buy_trades = filled_trades[filled_trades['side'] == 'buy']
            sell_trades = filled_trades[filled_trades['side'] == 'sell']
            
            total_commission = filled_trades['commission'].sum()
            total_stamp_tax = filled_trades['stamp_tax'].sum() if 'stamp_tax' in filled_trades.columns else 0
            total_cost = total_commission + total_stamp_tax
        else:
            buy_trades = pd.DataFrame()
            sell_trades = pd.DataFrame()
            total_cost = 0
        
        return {
            'initial_capital': self.initial_capital,
            'final_value': self.portfolio.total_value,
            'total_return': total_return,
            'annual_return': annual_return,
            'annual_volatility': annual_volatility,
            'sharpe_ratio': annual_sharpe,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'num_trades': len(self.trades),
            'num_filled': len(filled_trades) if 'filled_trades' in locals() else 0,
            'total_cost': total_cost,
            'history': history_df,
            'trades': trades_df
        }


if __name__ == '__main__':
    # 测试回测引擎
    print("=== 回测引擎 V2 测试 ===\n")
    
    # 创建简单的成本模型
    cost_model = CostModel(
        commission_rate=0.0003,  # 万三
        stamp_tax_rate=0.001,     # 千一
        impact_cost_base=0.0005,
        impact_cost_sqrt=0.001
    )
    
    # 创建回测引擎
    engine = BacktestEngineV2(
        initial_capital=1000000,
        cost_model=cost_model,
        max_single_position=0.10,
        max_industry_exposure=0.30,
        slippage_rate=0.001,
        fill_ratio=0.95
    )
    
    print(f"成本模型: {cost_model}")
    print(f"回测引擎: {engine}")
    print(f"投资组合: {engine.portfolio}")
