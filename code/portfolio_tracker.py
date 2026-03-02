#!/usr/bin/env python3
"""
持仓跟踪系统
管理每日持仓状态、交易决策、收益率跟踪
"""

import pandas as pd
import numpy as np
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime, date
from dataclasses import dataclass, asdict
import os

@dataclass
class Position:
    """持仓数据类"""
    stock_code: str
    stock_name: str
    cost_price: float  # 成本价
    current_price: float  # 当前价
    shares: float  # 持仓股数
    market_value: float  # 市值
    profit_loss: float  # 盈亏金额
    profit_loss_pct: float  # 盈亏百分比
    holding_days: int  # 持仓天数
    sector: str = ""  # 所属行业
    buy_date: str = ""  # 建仓日期
    alpha_score: float = 0.0  # α因子得分

@dataclass
class TradingDecision:
    """交易决策数据类"""
    date: str
    stock_code: str
    stock_name: str
    action: str  # 'buy', 'sell', 'add', 'reduce'
    reason: str
    price: float
    shares: float
    amount: float

class PortfolioTracker:
    """持仓跟踪器"""
    
    def __init__(self, state_file: str = None, decisions_file: str = None):
        """
        初始化持仓跟踪器
        
        Args:
            state_file: 持仓状态文件路径
            decisions_file: 交易决策文件路径
        """
        self.state_file = state_file or 'data/portfolio_state.json'
        self.decisions_file = decisions_file or 'data/trading_decisions.json'
        
        self.positions: Dict[str, Position] = {}
        self.decisions: List[TradingDecision] = []
        self.total_assets: float = 1000000.0  # 初始资金100万
        self.cash: float = 1000000.0  # 现金
        self.portfolio_value: float = 0.0  # 持仓市值
        
        # 加载历史数据
        self._load_state()
        self._load_decisions()
    
    def _load_state(self):
        """加载持仓状态"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 加载持仓
                for position_data in data.get('positions', []):
                    pos = Position(**position_data)
                    self.positions[pos.stock_code] = pos
                
                # 加载资金状态
                self.total_assets = data.get('total_assets', 1000000.0)
                self.cash = data.get('cash', 1000000.0)
                self.portfolio_value = data.get('portfolio_value', 0.0)
                
                print(f"✓ 加载持仓状态: {len(self.positions)}只股票")
            except Exception as e:
                print(f"⚠️ 加载持仓状态失败: {e}")
    
    def _save_state(self):
        """保存持仓状态"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        
        data = {
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_assets': self.total_assets,
            'cash': self.cash,
            'portfolio_value': self.portfolio_value,
            'positions': []
        }
        
        for position in self.positions.values():
            data['positions'].append(asdict(position))
        
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _load_decisions(self):
        """加载交易决策"""
        if os.path.exists(self.decisions_file):
            try:
                with open(self.decisions_file, 'r', encoding='utf-8') as f:
                    decisions_data = json.load(f)
                
                for decision_data in decisions_data:
                    decision = TradingDecision(**decision_data)
                    self.decisions.append(decision)
                
                print(f"✓ 加载历史决策: {len(self.decisions)}条")
            except Exception as e:
                print(f"⚠️ 加载交易决策失败: {e}")
    
    def _save_decision(self, decision: TradingDecision):
        """保存单条决策"""
        self.decisions.append(decision)
        
        decisions_data = [asdict(d) for d in self.decisions]
        
        os.makedirs(os.path.dirname(self.decisions_file), exist_ok=True)
        with open(self.decisions_file, 'w', encoding='utf-8') as f:
            json.dump(decisions_data, f, ensure_ascii=False, indent=2)
    
    def add_position(self, stock_code: str, stock_name: str, price: float, 
                     shares: float, alpha_score: float = 0.0, 
                     sector: str = "", reason: str = "") -> Position:
        """
        建仓或加仓
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            price: 买入价格
            shares: 买入股数
            alpha_score: α因子得分
            sector: 所属行业
            reason: 买入理由
            
        Returns:
            持仓对象
        """
        today = datetime.now().strftime('%Y-%m-%d')
        amount = price * shares
        
        # 检查现金
        if amount > self.cash:
            raise ValueError(f"现金不足: 需要{amount:,}, 可用{self.cash:,.2f}")
        
        # 判断是建仓还是加仓
        if stock_code in self.positions:
            # 加仓
            position = self.positions[stock_code]
            old_shares = position.shares
            old_amount = position.cost_price * old_shares
            
            # 重新计算成本价
            total_shares = old_shares + shares
            total_amount = old_amount + amount
            new_cost_price = total_amount / total_shares
            
            position.shares = total_shares
            position.cost_price = new_cost_price
            position.current_price = price
            position.market_value = position.shares * price
            position.alpha_score = alpha_score
            if sector:
                position.sector = sector
            
            action = 'add'
            description = f"加仓: 从{old_shares:.0f}股增至{total_shares:.0f}股"
        else:
            # 建仓
            position = Position(
                stock_code=stock_code,
                stock_name=stock_name,
                cost_price=price,
                current_price=price,
                shares=shares,
                market_value=price * shares,
                profit_loss=0.0,
                profit_loss_pct=0.0,
                holding_days=0,
                sector=sector,
                buy_date=today,
                alpha_score=alpha_score
            )
            self.positions[stock_code] = position
            action = 'buy'
            description = f"建仓: {shares:.0f}股"
        
        # 更新现金和市值
        self.cash -= amount
        self._update_portfolio_value()
        
        # 记录决策
        decision = TradingDecision(
            date=today,
            stock_code=stock_code,
            stock_name=stock_name,
            action=action,
            reason=reason or description,
            price=price,
            shares=shares,
            amount=amount
        )
        self._save_decision(decision)
        
        # 保存状态
        self._save_state()
        
        print(f"✓ {description} {stock_name}({stock_code}) @ {price:.2f}元, 金额{amount:,.2f}元")
        
        return position
    
    def reduce_position(self, stock_code: str, shares: float, 
                       price: float, reason: str = "") -> float:
        """
        减仓或清仓
        
        Args:
            stock_code: 股票代码
            shares: 卖出股数
            price: 卖出价格
            reason: 卖出理由
            
        Returns:
            卖出金额
        """
        if stock_code not in self.positions:
            raise ValueError(f"股票{stock_code}不在持仓中")
        
        position = self.positions[stock_code]
        today = datetime.now().strftime('%Y-%m-%d')
        amount = price * shares
        
        # 判断是减仓还是清仓
        if shares >= position.shares:
            # 清仓
            action = 'sell'
            description = f"清仓: 卖出{position.shares:.0f}股"
            del self.positions[stock_code]
        else:
            # 减仓
            action = 'reduce'
            description = f"减仓: 从{position.shares:.0f}股减至{position.shares - shares:.0f}股"
            position.shares -= shares
            position.market_value = position.shares * price
        
        # 更新现金
        self.cash += amount
        self._update_portfolio_value()
        
        # 记录决策
        decision = TradingDecision(
            date=today,
            stock_code=stock_code,
            stock_name=position.stock_name,
            action=action,
            reason=reason or description,
            price=price,
            shares=shares,
            amount=amount
        )
        self._save_decision(decision)
        
        # 保存状态
        self._save_state()
        
        print(f"✓ {description} {position.stock_name}({stock_code}) @ {price:.2f}元, 金额{amount:,.2f}元")
        
        return amount
    
    def _update_portfolio_value(self):
        """更新持仓市值"""
        self.portfolio_value = sum(pos.market_value for pos in self.positions.values())
        self.total_assets = self.cash + self.portfolio_value
    
    def update_prices(self, stock_prices: Dict[str, float]):
        """
        更新持仓价格
        
        Args:
            stock_prices: {股票代码: 当前价格}
        """
        for stock_code, price in stock_prices.items():
            if stock_code in self.positions:
                position = self.positions[stock_code]
                position.current_price = price
                position.market_value = position.shares * price
                position.profit_loss = (price - position.cost_price) * position.shares
                position.profit_loss_pct = (price - position.cost_price) / position.cost_price * 100
        
        self._update_portfolio_value()
        self._save_state()
    
    def get_positions_summary(self) -> pd.DataFrame:
        """
        获取持仓汇总
        
        Returns:
            持仓DataFrame
        """
        if not self.positions:
            return pd.DataFrame()
        
        data = []
        for position in self.positions.values():
            data.append({
                '股票代码': position.stock_code,
                '股票名称': position.stock_name,
                '成本价': position.cost_price,
                '当前价': position.current_price,
                '持仓数': position.shares,
                '市值': position.market_value,
                '盈亏': position.profit_loss,
                '盈亏%': position.profit_loss_pct,
                '持仓天数': position.holding_days,
                '行业': position.sector,
                'α得分': position.alpha_score
            })
        
        df = pd.DataFrame(data)
        # 按市值排序
        df = df.sort_values('市值', ascending=False)
        
        return df
    
    def get_portfolio_summary(self) -> Dict:
        """
        获取组合汇总信息
        
        Returns:
            组合信息字典
        """
        total_profit = sum(pos.profit_loss for pos in self.positions.values())
        total_profit_pct = (total_profit / (self.total_assets - self.cash) * 100 
                           if (self.total_assets - self.cash) > 0 else 0.0)
        
        # 按盈亏分组
        profit_stocks = [p.stock_code for p in self.positions.values() if p.profit_loss > 0]
        loss_stocks = [p.stock_code for p in self.positions.values() if p.profit_loss < 0]
        
        # 资金分配
        cash_ratio = self.cash / self.total_assets * 100
        stock_ratio = self.portfolio_value / self.total_assets * 100
        
        return {
            '总资产': self.total_assets,
            '现金': self.cash,
            '现金比例': cash_ratio,
            '持仓市值': self.portfolio_value,
            '持仓比例': stock_ratio,
            '持仓数量': len(self.positions),
            '总盈亏': total_profit,
            '总盈亏%': total_profit_pct,
            '盈利股票数': len(profit_stocks),
            '亏损股票数': len(loss_stocks),
            '盈利股票': profit_stocks,
            '亏损股票': loss_stocks
        }
    
    def get_rebalance_targets(self, target_weights: Dict[str, float], 
                            current_prices: Dict[str, float]) -> List[Dict]:
        """
        计算调仓目标
        
        Args:
            target_weights: 目标权重 {股票代码: 目标权重}
            current_prices: 当前价格 {股票代码: 价格}
            
        Returns:
            调仓建议列表
        """
        rebalance_actions = []
        target_value = self.total_assets
        
        for stock_code, target_weight in target_weights.items():
            target_market_value = target_value * target_weight
            
            if stock_code in self.positions:
                # 已持仓，计算需要调整的金额
                position = self.positions[stock_code]
                current_market_value = position.market_value
                diff_value = target_market_value - current_market_value
                
                price = current_prices.get(stock_code, position.current_price)
                
                if abs(diff_value) > 100:  # 忽略微小调整
                    if diff_value > 0:
                        # 需要加仓
                        shares = diff_value / price
                        rebalance_actions.append({
                            'stock_code': stock_code,
                            'stock_name': position.stock_name,
                            'action': 'add' if stock_code in self.positions else 'buy',
                            'amount': diff_value,
                            'shares': shares,
                            'price': price,
                            'reason': '权重调整: 当前{:.1%}, 目标{:.1%}'.format(
                                current_market_value/target_value, target_weight
                            )
                        })
                    else:
                        # 需要减仓
                        shares = abs(diff_value) / price
                        shares = min(shares, position.shares)  # 不能超过持仓
                        rebalance_actions.append({
                            'stock_code': stock_code,
                            'stock_name': position.stock_name,
                            'action': 'reduce',
                            'amount': abs(diff_value),
                            'shares': shares,
                            'price': price,
                            'reason': '权重调整: 当前{:.1%}, 目标{:.1%}'.format(
                                current_market_value/target_value, target_weight
                            )
                        })
            else:
                # 未持仓，需要建仓
                price = current_prices.get(stock_code, 0)
                if price > 0:
                    shares = target_market_value / price
                    rebalance_actions.append({
                        'stock_code': stock_code,
                        'stock_name': stock_code,  # 需要从其他地方获取名称
                        'action': 'buy',
                        'amount': target_market_value,
                        'shares': shares,
                        'price': price,
                        'reason': '新建仓: 目标权重{:.1%}'.format(target_weight)
                    })
        
        return rebalance_actions
    
    def check_rebalance_triggers(self) -> List[Dict]:
        """
        检查换仓触发条件
        
        Returns:
            触发换仓的股票列表 [{'stock_code': xxx, 'reason': xxx, 'action': xxx}]
        """
        triggers = []
        
        for position in self.positions.values():
            reason = ""
            action = None
            
            # 止盈触发: 收益>20%
            if position.profit_loss_pct > 20:
                reason = f"止盈触发: 收益{position.profit_loss_pct:.1f}% > 20%"
                action = 'reduce'
            
            # 止损触发: 亏损>10%
            elif position.profit_loss_pct < -10:
                reason = f"止损触发: 亏损{position.profit_loss_pct:.1f}% < -10%"
                action = 'sell'
            
            # 时间触发: 持仓>60天
            elif position.holding_days > 60:
                reason = f"时间触发: 持仓{position.holding_days}天 > 60天"
                action = 'review'  # 仅建议复查
            
            # 因子触发: α因子得分下降>20% (需要传入当前得分)
            # 这个条件在外部调用时处理
            
            if reason and action:
                triggers.append({
                    'stock_code': position.stock_code,
                    'stock_name': position.stock_name,
                    'reason': reason,
                    'action': action,
                    'profit_loss_pct': position.profit_loss_pct,
                    'holding_days': position.holding_days
                })
        
        return triggers
    
    def generate_daily_report(self) -> str:
        """
        生成持仓日报
        
        Returns:
            报告文本
        """
        positions_df = self.get_positions_summary()
        portfolio_summary = self.get_portfolio_summary()
        
        report = []
        report.append("=" * 60)
        report.append("📊 持仓日报")
        report.append("=" * 60)
        report.append(f"日期: {datetime.now().strftime('%Y-%m-%d')}")
        report.append("")
        
        # 资产概览
        report.append("💰 资产概览")
        report.append("-" * 40)
        report.append(f"总资产: {portfolio_summary['总资产']:,.2f} 元")
        report.append(f"现金: {portfolio_summary['现金']:,.2f} 元 ({portfolio_summary['现金比例']:.1f}%)")
        report.append(f"持仓市值: {portfolio_summary['持仓市值']:,.2f} 元 ({portfolio_summary['持仓比例']:.1f}%)")
        report.append(f"持仓数量: {portfolio_summary['持仓数量']} 只")
        report.append(f"总盈亏: {portfolio_summary['总盈亏']:,.2f} 元 ({portfolio_summary['总盈亏%']:.2f}%)")
        report.append(f"盈利股票: {portfolio_summary['盈利股票数']} 只, 亏损股票: {portfolio_summary['亏损股票数']} 只")
        report.append("")
        
        # 持仓详情
        if not positions_df.empty:
            report.append("📋 持仓详情")
            report.append("-" * 40)
            
            for _, row in positions_df.iterrows():
                emoji = "📈" if row['盈亏%'] > 0 else ("📉" if row['盈亏%'] < 0 else "➡️")
                report.append(f"{emoji} {row['股票名称']}({row['股票代码']})")
                report.append(f"   成本价: {row['成本价']:.2f} → 当前价: {row['当前价']:.2f}")
                report.append(f"   持仓: {row['持仓数']:.0f}股, 市值: {row['市值']:,.0f}元")
                report.append(f"   盈亏: {row['盈亏']:,.0f}元 ({row['盈亏%']:.2f}%)")
                report.append(f"   持仓天数: {row['持仓天数']}天")
                report.append("")
        
        # 检查换仓触发
        triggers = self.check_rebalance_triggers()
        if triggers:
            report.append("⚠️ 换仓触发")
            report.append("-" * 40)
            for trigger in triggers:
                report.append(f"{trigger['stock_name']}({trigger['stock_code']})")
                report.append(f"   {trigger['reason']}")
                report.append(f"   建议操作: {trigger['action']}")
            report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)


# 测试代码
if __name__ == "__main__":
    # 测试持仓跟踪器
    tracker = PortfolioTracker()
    
    # 建仓
    tracker.add_position('000001', '平安银行', 10.0, 1000, alpha_score=85, sector='银行')
    tracker.add_position('000002', '万科A', 20.0, 500, alpha_score=82, sector='房地产')
    tracker.add_position('600519', '贵州茅台', 1800.0, 10, alpha_score=90, sector='消费品')
    
    # 更新价格
    tracker.update_prices({
        '000001': 11.0,  # 盈利10%
        '000002': 18.0,  # 亏损10%
        '600519': 2000.0  # 盈利11%
    })
    
    # 生成报告
    print(tracker.generate_daily_report())
