#!/usr/bin/env python3
"""
增强推送系统
集成持仓跟踪、α选股、换仓策略，推送具有连续性的内容
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
import json
from datetime import datetime
from typing import Dict, List, Optional

from portfolio_tracker import PortfolioTracker, TradingDecision
from alpha_stock_selector import AlphaStockSelector
from rebalance_strategy import RebalanceStrategy

class EnhancedPusher:
    """增强推送器"""
    
    def __init__(self, config_file: str = 'config/feishu_config.json'):
        """
        初始化增强推送器
        
        Args:
            config_file: 配置文件路径
        """
        # 加载配置
        self.config = self._load_config(config_file)
        
        # 初始化核心模块
        self.portfolio = PortfolioTracker()
        self.alpha_selector = AlphaStockSelector()
        self.rebalance_strategy = RebalanceStrategy()
        
        # 推送状态
        self.push_log_file = 'data/push_log.json'
        self.push_history = self._load_push_history()
    
    def _load_config(self, config_file: str) -> Dict:
        """加载配置"""
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'webhook_url': '',
            'enabled': True,
            'push_time': '18:30',
            'timezone': 'Asia/Shanghai',
            'push_type': 'daily'
        }
    
    def _load_push_history(self) -> List[Dict]:
        """加载推送历史"""
        if os.path.exists(self.push_log_file):
            try:
                with open(self.push_log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 加载推送历史失败: {e}")
        return []
    
    def _save_push_history(self, push_data: Dict):
        """保存推送记录"""
        self.push_history.append(push_data)
        
        # 只保留最近30条
        if len(self.push_history) > 30:
            self.push_history = self.push_history[-30:]
        
        os.makedirs(os.path.dirname(self.push_log_file), exist_ok=True)
        with open(self.push_log_file, 'w', encoding='utf-8') as f:
            json.dump(self.push_history, f, ensure_ascii=False, indent=2)
    
    def _get_yesterday_plan(self) -> Optional[Dict]:
        """
        获取昨日的推送计划
        
        Returns:
            昨日的推送数据或None
        """
        if not self.push_history:
            return None
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 找到最近一次推送
        for push in reversed(self.push_history):
            if push.get('date') != today:
                return push
        
        return None
    
    def _get_yesterday_actions(self) -> List[Dict]:
        """
        获取昨日建议的操作
        
        Returns:
            操作列表
        """
        yesterday_plan = self._get_yesterday_plan()
        if not yesterday_plan:
            return []
        
        return yesterday_plan.get('today_decision', {})
    
    def _execute_tracking(self) -> pd.DataFrame:
        """
        执行持仓跟踪检查
        
        Returns:
            持仓DataFrame
        """
        # 获取当前持仓数据
        positions_df = self.portfolio.get_positions_summary()
        
        return positions_df
    
    def run_selection(self, stock_data: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """
        执行选股
        
        Args:
            stock_data: 股票数据
            
        Returns:
            (选中的股票DataFrame, 组合配置)
        """
        selected, portfolio_config = self.alpha_selector.select_stocks(
            stock_data, n=10, apply_filters=True
        )
        
        return selected, portfolio_config
    
    def evaluate_rebalancing(self, stock_data: pd.DataFrame, 
                           alpha_scores: pd.Series,
                           portfolio_config: Dict) -> Dict:
        """
        评估换仓
        
        Args:
            stock_data: 股票数据
            alpha_scores: α得分
            portfolio_config: 目标组合配置
            
        Returns:
            换仓计划
        """
        plan = self.rebalance_strategy.evaluate_rebalancing(
            self.portfolio,
            stock_data,
            alpha_scores,
            portfolio_config
        )
        
        return plan
    
    def generate_push_content(self, stock_data: pd.DataFrame = None,
                            alpha_scores: pd.Series = None) -> str:
        """
        生成推送内容
        
        Args:
            stock_data: 股票数据
            alpha_scores: α得分
            
        Returns:
            推送内容文本
        """
        today = datetime.now().strftime('%Y-%m-%d')
        now = datetime.now().strftime('%H:%M:%S')
        
        content = []
        content.append("🦞 A股量化日报 - 智能推送")
        content.append("━━━━━━━━━━━━━━━━━━━━━━━━")
        content.append(f"📅 推送时间: {today} {now}")
        content.append(f"📌 类型: 实盘推送（含持仓跟踪）")
        content.append("")
        
        # 1. 昨日回顾
        content.append("🕐 昨日回顾")
        content.append("────────────────────")
        
        yesterday_plan = self._get_yesterday_plan()
        if yesterday_plan:
            yesterday_date = yesterday_plan.get('date', 'N/A')
            yesterday_positions = yesterday_plan.get('today_positions', [])
            yesterday_decisions = yesterday_plan.get('today_decision', [])
            
            content.append(f"昨日推送: {yesterday_date}")
            content.append(f"持仓数量: {len(yesterday_positions)}只")
            content.append("")
            
            # 检查昨日建议执行情况
            content.append("昨日建议执行情况:")
            
            if yesterday_decisions:
                for decision in yesterday_decisions[:3]:
                    action_emoji = "🟢" if decision.get('type') == '建仓' else ("🔴" if decision.get('type') in ['清仓', '止损'] else "🟡")
                    content.append(f"{action_emoji} {decision.get('name', 'N/A')} - {decision.get('reason', '')}")
            else:
                content.append("→ 无调整建议，保持原持仓")
            
            content.append("")
        else:
            content.append("昨日: 无历史推送记录")
            content.append("→ 系统首次运行或历史记录缺失")
            content.append("")
        
        # 2. 今日持仓
        content.append("📊 今日持仓")
        content.append("────────────────────")
        
        positions_df = self._execute_tracking()
        portfolio_summary = self.portfolio.get_portfolio_summary()
        
        if positions_df.empty:
            content.append("当前无持仓")
            content.append("→ 建议按照今日选股结果建仓")
            content.append("")
        else:
            content.append(f"持仓总数: {portfolio_summary['持仓数量']}只")
            content.append(f"总资产: {portfolio_summary['总资产']:,.0f}元")
            content.append(f"总盈亏: {portfolio_summary['总盈亏']:,.0f}元 ({portfolio_summary['总盈亏%']:.2f}%)")
            content.append(f"现金: {portfolio_summary['现金']:,.0f}元 ({portfolio_summary['现金比例']:.1f}%)")
            content.append("")
            
            # 显示持仓列表
            content.append("持仓明细:")
            for idx, row in positions_df.head(5).iterrows():
                emoji = "📈" if row['盈亏%'] > 0 else ("📉" if row['盈亏%'] < 0 else "➡️")
                content.append(f"{emoji} {row['股票名称']}({row['股票代码']})")
                content.append(f"   盈亏: {row['盈亏']:,.0f}元 ({row['盈亏%']:.2f}%) | 持仓天数: {row['持仓天数']}天")
                content.append(f"   市值: {row['市值']:,.0f}元 ({row['市值']/portfolio_summary['总资产']*100:.1f}%)")
                if row['α得分'] > 0:
                    content.append(f"   α得分: {row['α得分']:.1f}")
            content.append("")
        
        # 3. 选股结果（如果有数据）
        if stock_data is not None and alpha_scores is not None:
            selected, portfolio_config = self.run_selection(stock_data)
            
            content.append("🎯 今日选股（α因子筛选）")
            content.append("────────────────────")
            
            for idx, (stock_code, row) in enumerate(selected.iterrows(), 1):
                stock_name = row.get('股票名称', row.get('name', stock_code))
                alpha_score = row.get('alpha_score', alpha_scores.get(stock_code, 0))
                weight = stock_code in [h['stock_code'] for h in portfolio_config.get('core', [])] \
                        or stock_code in [h['stock_code'] for h in portfolio_config.get('satellite', [])]
                
                holding_type = "🔑核心" if stock_code in [h['stock_code'] for h in portfolio_config.get('core', [])] \
                               else ("🌟卫星" if stock_code in [h['stock_code'] for h in portfolio_config.get('satellite', [])] else "")
                
                weight_text = ""
                for h in portfolio_config.get('core', []) + portfolio_config.get('satellite', []):
                    if h['stock_code'] == stock_code:
                        weight_text = f" | 权重: {h['weight']*100:.1f}%"
                        break
                
                content.append(f"{idx}. {holding_type} {stock_name}({stock_code})")
                content.append(f"   α得分: {alpha_score:.1f}分{weight_text}")
            content.append("")
            
            # 4. 换仓策略评估
            plan = self.evaluate_rebalancing(stock_data, alpha_scores, portfolio_config)
            
            content.append("🔄 今日决策")
            content.append("────────────────────")
            
            if plan.actions:
                for action in plan.actions[:5]:
                    emoji = "🛑" if action['action'] == 'sell' else ("⬇️" if action['action'] == 'reduce' else ("⬆️" if action['action'] == 'add' else ("📈" if action['action'] == 'buy' else "👀")))
                    
                    action_name = {
                        'sell': '清仓',
                        'reduce': '减仓',
                        'add': '加仓',
                        'buy': '建仓',
                        'review': '复查'
                    }.get(action['action'], action['action'])
                    
                    content.append(f"{emoji} {action['stock_name']}({action['stock_code']}) - {action_name}")
                    content.append(f"   原因: {action['reason']}")
                    
                    if action.get('amount', 0) > 0:
                        content.append(f"   涉及金额: {action['amount']:,.0f}元")
                    
                    if 'replacements' in action and action['replacements']:
                        content.append(f"   替代: {action['replacements'][0]['stock_name']}({action['replacements'][0]['stock_code']})")
            else:
                content.append("✓ 无需调整，当前持仓符合策略")
            
            content.append("")
            
            # 5. 换仓逻辑说明
            content.append("⚙️ 换仓逻辑")
            content.append("────────────────────")
            content.append("止盈触发: 收益>20% → 分批止盈")
            content.append("止损触发: 亏损>10% → 立即止损")
            content.append("时间触发: 持仓>60天 → 评估换仓")
            content.append("因子触发: α得分下降>20% → 建议换仓")
            content.append("")
            
            # 6. 明日计划
            content.append("📅 明日计划")
            content.append("────────────────────")
            
            if plan.actions:
                today_decision = []
                
                for action in plan.actions:
                    action_name = {
                        'sell': '清仓',
                        'reduce': '减仓',
                        'add': '加仓',
                        'buy': '建仓',
                        'review': '复查'
                    }.get(action['action'], action['action'])
                    
                    today_decision.append({
                        'stock_code': action['stock_code'],
                        'name': action['stock_name'],
                        'type': action_name,
                        'reason': action['reason'],
                        'amount': action.get('amount', 0)
                    })
                
                content.append(f"关注今日操作执行情况:")
                
                # 建仓计划
                build_stocks = [d for d in today_decision if d['type'] == '建仓']
                if build_stocks:
                    content.append(f"• 建仓: {len(build_stocks)}只")
                
                # 调仓计划
                adjust_stocks = [d for d in today_decision if d['type'] in ['加仓', '减仓']]
                if adjust_stocks:
                    content.append(f"• 调仓: {len(adjust_stocks)}只")
                
                # 清仓计划
                clear_stocks = [d for d in today_decision if d['type'] == '清仓']
                if clear_stocks:
                    content.append(f"• 清仓: {len(clear_stocks)}只")
                
                content.append("")
                content.append("明日根据执行结果:")
                content.append("• 如收盘前30分钟有调仓，建议及时跟进")
                content.append("• 如未触发调仓，继续保持当前持仓")
            else:
                content.append("• 保持当前持仓，无需调整")
                content.append("• 继续监控止盈止损触发条件")
                content.append("• 关注市场环境变化")
            
            # 持仓列表用于明日对比
            today_positions = []
            for stock_code, position in self.portfolio.positions.items():
                today_positions.append({
                    'stock_code': stock_code,
                    'name': position.stock_name,
                    'cost_price': position.cost_price,
                    'current_price': position.current_price
                })
        else:
            content.append("明日计划:")
            content.append("→ 等待选股数据完成后再生成计划")
            
            today_decision = []
            today_positions = []
        
        content.append("")
        
        # 7. 仓位建议
        content.append("💰 仓位管理建议")
        content.append("────────────────────")
        
        if not positions_df.empty:
            current_cash_ratio = portfolio_summary['现金比例']
            
            if current_cash_ratio < 15:
                content.append(f"当前仓位偏高 ({100-current_cash_ratio:.1f}%)")
                content.append("→ 总仓位保持在60-85%范围内")
                content.append("→ 如遇回调，使用现金加仓")
            elif current_cash_ratio > 40:
                content.append(f"当前现金比例较高 ({current_cash_ratio:.1f}%)")
                content.append("→ 建议逢低建仓或加仓高α股票")
            else:
                content.append(f"当前仓位适中 ({100-current_cash_ratio:.1f}%)")
                content.append("→ 按计划执行，关注换仓信号")
        else:
            content.append("建议分批建仓:")
            content.append("• 核心持仓 (60%): 5只高α+低估股票")
            content.append("• 卫星持仓 (20%): 2只行业轮动股票")
            content.append("• 现金 (20%): 应对加仓和风险")
        
        content.append("")
        
        # 8. 风险提示
        content.append("⚠️ 风险提示")
        content.append("────────────────────")
        content.append("• 单股止损线: -10%")
        content.append("• 单股止盈线: +20%")
        content.append("• 组合最大回撤: -15%")
        content.append("• 请根据自身风险承受能力调整仓位")
        content.append("")
        
        content.append("━━━━━━━━━━━━━━━━━━━━━━━━")
        content.append(f"📊 数据来源: α因子选股 + 持仓跟踪")
        content.append(f"🦞 A股量化系统 v2.0 | {today}")
        
        push_content = "\n".join(content)
        
        # 保存推送日志
        self._save_push_history({
            'date': today,
            'time': now,
            'positions_count': portfolio_summary['持仓数量'],
            'total_assets': portfolio_summary['总资产'],
            'total_profit': portfolio_summary['总盈亏'],
            'today_positions': today_positions[:5],
            'today_decision': today_decision[:5],
            'content': push_content
        })
        
        return push_content


# 测试代码
if __name__ == "__main__":
    # 创建测试推送器
    pusher = EnhancedPusher()
    
    # 创建测试股票数据
    np.random.seed(42)
    test_data = pd.DataFrame({
        'stock_code': [f'{i:06d}' for i in range(1, 51)],
        '股票名称': [f'测试股票{i}' for i in range(1, 51)],
        'PE_TTM': np.random.uniform(5, 50, 50),
        'PB': np.random.uniform(0.5, 10, 50),
        'PEG': np.random.uniform(0.3, 3, 50),
        'ROE': np.random.uniform(0, 0.3, 50),
        'Revenue_Growth': np.random.uniform(-0.1, 0.5, 50),
        'Turnover_Rate': np.random.uniform(0.5, 10, 50),
        '市值_亿': np.random.uniform(50, 5000, 50),
        'industry': np.random.choice(['银行', '房地产', '消费品', '科技', '医药'], 50)
    })
    test_data = test_data.set_index('stock_code')
    
    # 生成测试α得分
    alpha_scores = pd.Series(
        pusher.alpha_selector.calculate_alpha_score(test_data)
    )
    
    # 生成推送内容
    push_content = pusher.generate_push_content(test_data, alpha_scores)
    
    print(push_content)
