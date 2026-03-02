#!/usr/bin/env python3
"""
换仓策略模块
定义止盈止损、时间触发、因子触发等换仓机制
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import os

from portfolio_tracker import PortfolioTracker, Position

@dataclass
class RebalancePlan:
    """换仓计划"""
    date: str
    actions: List[Dict]  # [{'stock_code': xxx, 'action': 'buy/sell/add/reduce', 'reason': xxx, 'amount': xxx, 'shares': xxx}]
    summary: Dict  # 换仓摘要

class RebalanceStrategy:
    """换仓策略"""
    
    def __init__(self):
        self.take_profit_threshold = 20.0  # 止盈阈值 20%
        self.stop_loss_threshold = -10.0  # 止损阈值 -10%
        self.max_holding_days = 60  # 最大持仓天数
        self.alpha_decline_threshold = 20.0  # α得分下降阈值 20%
        
        self.rebalance_history: List[RebalancePlan] = []
        self.history_file = 'data/rebalance_history.json'
        
        self._load_history()
    
    def _load_history(self):
        """加载换仓历史"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                
                for plan_data in history_data:
                    plan = RebalancePlan(
                        date=plan_data['date'],
                        actions=plan_data['actions'],
                        summary=plan_data['summary']
                    )
                    self.rebalance_history.append(plan)
                
                print(f"✓ 加载换仓历史: {len(self.rebalance_history)}条记录")
            except Exception as e:
                print(f"⚠️ 加载换仓历史失败: {e}")
    
    def _save_history(self, plan: RebalancePlan):
        """保存换仓计划到历史"""
        self.rebalance_history.append(plan)
        
        history_data = [
            {
                'date': p.date,
                'actions': p.actions,
                'summary': p.summary
            }
            for p in self.rebalance_history
        ]
        
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
    
    def check_take_profit(self, position: Position, price: float) -> Dict:
        """
        检查是否触发止盈
        
        Args:
            position: 持仓对象
            price: 当前价格
            
        Returns:
            触发信息 {'triggered': bool, 'action': str, 'reason': str}
        """
        profit_pct = (price - position.cost_price) / position.cost_price * 100
        
        if profit_pct >= self.take_profit_threshold:
            # 分批止盈: 先卖出一半
            action = 'reduce'
            reason = f"止盈触发: 收益{profit_pct:.1f}% >= {self.take_profit_threshold}%, 建议分批止盈"
            return {'triggered': True, 'action': action, 'reason': reason, 'profit_pct': profit_pct}
        
        return {'triggered': False, 'action': None, 'reason': '', 'profit_pct': profit_pct}
    
    def check_stop_loss(self, position: Position, price: float) -> Dict:
        """
        检查是否触发止损
        
        Args:
            position: 持仓对象
            price: 当前价格
            
        Returns:
            触发信息
        """
        profit_pct = (price - position.cost_price) / position.cost_price * 100
        
        if profit_pct <= self.stop_loss_threshold:
            # 立即止损: 全部卖出
            action = 'sell'
            reason = f"止损触发: 亏损{profit_pct:.1f}% <= {self.stop_loss_threshold}%, 立即清仓"
            return {'triggered': True, 'action': action, 'reason': reason, 'profit_pct': profit_pct}
        
        return {'triggered': False, 'action': None, 'reason': '', 'profit_pct': profit_pct}
    
    def check_time_trigger(self, position: Position, current_prices: Dict) -> Dict:
        """
        检查时间触发条件
        
        Args:
            position: 持仓对象
            current_prices: 当前价格字典 {stock_code: price}
            
        Returns:
            触发信息
        """
        if position.holding_days >= self.max_holding_days:
            price = current_prices.get(position.stock_code, position.current_price)
            profit_pct = (price - position.cost_price) / position.cost_price * 100
            
            action = 'review'
            reason = f"持仓{position.holding_days}天 >= {self.max_holding_days}天, 建议评估是否换仓"
            return {'triggered': True, 'action': action, 'reason': reason, 'profit_pct': profit_pct}
        
        return {'triggered': False, 'action': None, 'reason': '', 'profit_pct': 0}
    
    def check_alpha_decline(self, position: Position, current_alpha_score: float,
                           original_alpha_score: float) -> Dict:
        """
        检查α因子得分下降
        
        Args:
            position: 持仓对象
            current_alpha_score: 当前α得分
            original_alpha_score: 建仓时的α得分
            
        Returns:
            触发信息
        """
        if original_alpha_score > 0:
            decline_pct = (original_alpha_score - current_alpha_score) / original_alpha_score * 100
            
            if decline_pct >= self.alpha_decline_threshold:
                action = 'reduce'
                reason = f"α得分下降{decline_pct:.1f}% >= {self.alpha_decline_threshold}%, 建议减仓或清仓"
                return {
                    'triggered': True,
                    'action': action,
                    'reason': reason,
                    'original_alpha': original_alpha_score,
                    'current_alpha': current_alpha_score,
                    'decline_pct': decline_pct
                }
        
        return {'triggered': False, 'action': None, 'reason': '', 'decline_pct': 0}
    
    def find_replacement_stocks(self, portfolio_tracker: PortfolioTracker,
                               candidates: pd.DataFrame,
                               alpha_scores: pd.Series,
                               current_prices: Dict,
                               n: int = 3) -> List[Dict]:
        """
        为需要换出的股票寻找替代股票
        
        Args:
            portfolio_tracker: 持仓跟踪器
            candidates: 候选股票池 DataFrame
            alpha_scores: α得分 Series
            current_prices: 当前价格
            n: 返回替代股票数量
            
        Returns:
            替代股票列表
        """
        # 排除当前持仓的股票
        current_holdings = set(portfolio_tracker.positions.keys())
        available = candidates[~candidates.index.isin(current_holdings)]
        
        if len(available) == 0:
            return []
        
        # 按α得分排序
        available = available.copy()
        available['alpha_score'] = alpha_scores[available.index]
        available = available.sort_values('alpha_score', ascending=False).head(n)
        
        replacements = []
        for stock_code, row in available.iterrows():
            stock_name = row.get('股票名称', row.get('name', stock_code))
            price = current_prices.get(stock_code, 0)
            alpha_score = row['alpha_score']
            
            replacements.append({
                'stock_code': stock_code,
                'stock_name': stock_name,
                'price': price,
                'alpha_score': alpha_score,
                'reason': f"高α得分({alpha_score:.1f}), 建议作为替代"
            })
        
        return replacements
    
    def evaluate_rebalancing(self, portfolio_tracker: PortfolioTracker,
                            stock_data: pd.DataFrame,
                            alpha_scores: pd.Series,
                            target_portfolio: Dict = None) -> RebalancePlan:
        """
        评估是否需要调仓并生成调仓计划
        
        Args:
            portfolio_tracker: 持仓跟踪器
            stock_data: 股票数据 (index: stock_code)
            alpha_scores: α得分 Series
            target_portfolio: 目标组合配置（如果为None则不进行目标配置调整）
            
        Returns:
            换仓计划
        """
        actions = []
        today = datetime.now().strftime('%Y-%m-%d')
        
        print("=" * 60)
        print("🔄 换仓策略评估")
        print("=" * 60)
        print(f"日期: {today}")
        print("")
        
        # 1. 对每个持仓检查所有触发条件
        print("📋 检查持仓触发条件...")
        
        for stock_code, position in portfolio_tracker.positions.items():
            triggers = []
            
            # 获取当前价格和α得分
            current_price = stock_data.loc[stock_code, 'close'] if 'close' in stock_data.columns else position.current_price
            current_alpha = alpha_scores.get(stock_code, position.alpha_score)
            original_alpha = position.alpha_score
            current_prices = {stock_code: current_price}
            
            # 检查止盈
            take_profit_result = self.check_take_profit(position, current_price)
            if take_profit_result['triggered']:
                triggers.append(('止盈', take_profit_result))
            
            # 检查止损
            stop_loss_result = self.check_stop_loss(position, current_price)
            if stop_loss_result['triggered']:
                triggers.append(('止损', stop_loss_result))
            
            # 检查时间触发
            time_result = self.check_time_trigger(position, current_prices)
            if time_result['triggered']:
                triggers.append(('时间', time_result))
            
            # 检查α因子下降
            alpha_result = self.check_alpha_decline(position, current_alpha, original_alpha)
            if alpha_result['triggered']:
                triggers.append(('因子', alpha_result))
            
            # 如果有触发，生成调仓动作
            if triggers:
                for trigger_type, trigger_result in triggers:
                    action_detail = {
                        'stock_code': stock_code,
                        'stock_name': position.stock_name,
                        'type': trigger_type,
                        'action': trigger_result['action'],
                        'reason': trigger_result['reason'],
                        'current_price': current_price,
                        'cost_price': position.cost_price,
                        'profit_pct': trigger_result.get('profit_pct', 0),
                        'holding_days': position.holding_days,
                        'shares': position.shares,
                        'market_value': position.market_value
                    }
                    
                    # 根据动作类型确定操作股数
                    if trigger_result['action'] == 'sell':
                        action_detail['target_shares'] = position.shares
                    elif trigger_result['action'] == 'reduce':
                        action_detail['target_shares'] = position.shares * 0.5  # 减仓一半
                    elif trigger_result['action'] == 'review':
                        action_detail['target_shares'] = 0  # 仅复查，不操作
                    else:
                        action_detail['target_shares'] = 0
                    
                    # 计算涉及金额
                    price = current_price if current_price > 0 else position.cost_price
                    action_detail['amount'] = abs(action_detail['target_shares'] * price)
                    
                    actions.append(action_detail)
        
        # 2. 如果有目标组合配置，检查目标权重调整
        if target_portfolio:
            print("\n💯 检查目标权重...")
            target_weights = {}
            
            # 合并核心和卫星持仓
            for holding in target_portfolio.get('core', []):
                target_weights[holding['stock_code']] = holding['weight']
            for holding in target_portfolio.get('satellite', []):
                target_weights[holding['stock_code']] = holding['weight']
            
            if target_weights:
                current_prices = {stock_code: stock_data.loc[stock_code, 'close'] if 'close' in stock_data.columns else position.current_price
                                 for stock_code in portfolio_tracker.positions.keys()}
                
                rebalance_actions = portfolio_tracker.get_rebalance_targets(target_weights, current_prices)
                
                for action in rebalance_actions:
                    if abs(action['amount']) > 1000:  # 只保留金额超过1000元的调整
                        # 查找是否已存在触发条件的操作
                        existing = next((a for a in actions if a['stock_code'] == action['stock_code']), None)
                        if existing:
                            existing['reason'] += f"; {action['reason']}"
                        else:
                            actions.append({
                                'stock_code': action['stock_code'],
                                'stock_name': portfolio_tracker.positions[action['stock_code']].stock_name if action['stock_code'] in portfolio_tracker.positions else action['stock_code'],
                                'type': '权重调整',
                                'action': action['action'],
                                'reason': action['reason'],
                                'current_price': action['price'],
                                'shares': portfolio_tracker.positions[action['stock_code']].shares if action['stock_code'] in portfolio_tracker.positions else 0,
                                'target_shares': action['shares'],
                                'amount': action['amount']
                            })
        
        # 3. 为卖出操作寻找替代股票
        sell_actions = [a for a in actions if a['action'] in ['sell', 'reduce']]
        if sell_actions:
            print(f"\n🎯 为{len(sell_actions)}只卖出股票寻找替代...")
            
            for action in sell_actions:
                if action['action'] == 'sell' and action['type'] not in ['止损', '因子']:
                    # 只有非止损和非因子下降的卖出才需要替代
                    replacements = self.find_replacement_stocks(
                        portfolio_tracker,
                        stock_data,
                        alpha_scores,
                        {stock_code: action['current_price'] for stock_code in stock_data.index},
                        n=3
                    )
                    
                    if replacements:
                        action['replacements'] = replacements
                        print(f"  ✓ {action['stock_name']}({action['stock_code']}) - 找到{len(replacements)}只替代股票")
        
        # 4. 统计摘要
        summary = {
            'date': today,
            'total_actions': len(actions),
            'sell_actions': len([a for a in actions if a['action'] == 'sell']),
            'reduce_actions': len([a for a in actions if a['action'] == 'reduce']),
            'add_actions': len([a for a in actions if a['action'] == 'add']),
            'buy_actions': len([a for a in actions if a['action'] == 'buy']),
            'review_actions': len([a for a in actions if a['action'] == 'review']),
            'estimated_amount': sum(abs(a.get('amount', 0)) for a in actions)
        }
        
        # 5. 输出结果
        if actions:
            print(f"\n" + "=" * 60)
            print(f"📊 换仓计划")
            print("=" * 60)
            
            for action in actions:
                emoji = "🛑" if action['action'] == 'sell' else ("⬇️" if action['action'] == 'reduce' else ("⬆️" if action['action'] == 'add' else ("📈" if action['action'] == 'buy' else "👀")))
                print(f"\n{emoji} {action['stock_name']}({action['stock_code']})")
                print(f"   类型: {action['type']}")
                print(f"   操作: {action['action']}")
                print(f"   原因: {action['reason']}")
                print(f"   仓位: {action['shares']:.0f}股 →", end="")
                if action['target_shares'] > 0:
                    print(f" {action['target_shares']:.0f}股")
                else:
                    print(" 0股" if action['action'] == 'sell' else "")
                print(f"   金额: {action['amount']:,.0f}元")
                
                if 'replacements' in action:
                    print(f"   替代股票:")
                    for rep in action['replacements'][:2]:
                        print(f"     • {rep['stock_name']}({rep['stock_code']}) - α得分: {rep['alpha_score']:.1f}")
            
            print(f"\n" + "=" * 60)
            print(f"📈 换仓摘要")
            print("=" * 60)
            print(f"操作总数: {summary['total_actions']}")
            print(f"  • 清仓: {summary['sell_actions']}")
            print(f"  • 减仓: {summary['reduce_actions']}")
            print(f"  • 加仓: {summary['add_actions']}")
            print(f"  • 建仓: {summary['buy_actions']}")
            print(f"  • 复查: {summary['review_actions']}")
            print(f"涉及金额: {summary['estimated_amount']:,.0f}元")
        else:
            print("\n✓ 无需调仓")
        
        print("=" * 60)
        
        # 6. 创建换仓计划并保存
        plan = RebalancePlan(
            date=today,
            actions=actions,
            summary=summary
        )
        
        if actions:
            self._save_history(plan)
        
        return plan
    
    def execute_rebalance(self, plan: RebalancePlan, 
                         portfolio_tracker: PortfolioTracker,
                         stock_prices: Dict[str, float]) -> bool:
        """
        执行换仓计划
        
        Args:
            plan: 换仓计划
            portfolio_tracker: 持仓跟踪器
            stock_prices: 股票价格 {stock_code: price}
            
        Returns:
            是否执行成功
        """
        print("=" * 60)
        print("🚀 执行换仓")
        print("=" * 60)
        
        success = True
        
        for action in plan.actions:
            stock_code = action['stock_code']
            stock_name = action['stock_name']
            action_type = action['action']
            target_shares = action.get('target_shares', 0)
            reason = action['reason']
            
            # 获取价格
            price = stock_prices.get(stock_code, action.get('current_price', 0))
            
            try:
                if action_type == 'sell':
                    # 清仓
                    shares = action['shares']
                    portfolio_tracker.reduce_position(
                        stock_code, shares, price, 
                        reason=reason
                    )
                
                elif action_type == 'reduce':
                    # 减仓
                    shares = action.get('target_shares', 0)
                    if shares > 0:
                        portfolio_tracker.reduce_position(
                            stock_code, shares, price,
                            reason=reason
                        )
                
                elif action_type == 'add':
                    # 加仓
                    shares = action.get('target_shares', 0)
                    if shares > 0:
                        portfolio_tracker.add_position(
                            stock_code, stock_name, price, shares,
                            reason=reason
                        )
                
                elif action_type == 'buy':
                    # 建仓
                    shares = action.get('target_shares', 0)
                    if shares > 0:
                        portfolio_tracker.add_position(
                            stock_code, stock_name, price, shares,
                            reason=reason
                        )
                
                print(f"✓ {action_type} {stock_name} 完成")
                
            except Exception as e:
                print(f"✗ {action_type} {stock_name} 失败: {e}")
                success = False
        
        print("=" * 60)
        print(f"换仓执行完成: {'成功' if success else '部分失败'}")
        print("=" * 60)
        
        return success


# 测试代码
if __name__ == "__main__":
    # 创建测试持仓跟踪器
    tracker = PortfolioTracker()
    
    # 建仓
    tracker.add_position('000001', '平安银行', 10.0, 1000, alpha_score=85)
    tracker.add_position('000002', '万科A', 20.0, 500, alpha_score=75)
    tracker.add_position('600519', '贵州茅台', 1800.0, 10, alpha_score=90)
    
    # 更新价格（模拟盈亏）
    tracker.update_prices({
        '000001': 12.0,  # 盈利20%，触发止盈
        '000002': 18.0,  # 亏损10%，触发止损
        '600519': 2000.0  # 盈利11%
    })
    
    # 创建测试股票数据
    test_data = pd.DataFrame({
        'close': [12.0, 18.0, 2000.0],
        'PE_TTM': [5.0, 20.0, 25.0],
        'PB': [0.8, 1.5, 10.0]
    }, index=['000001', '000002', '600519'])
    
    # 创建α得分
    alpha_scores = pd.Series({
        '000001': 70.0,
        '000002': 60.0,
        '600519': 80.0
    })
    
    # 测试换仓策略
    strategy = RebalanceStrategy()
    plan = strategy.evaluate_rebalancing(tracker, test_data, alpha_scores)
    
    print("\n" + tracker.generate_daily_report())
