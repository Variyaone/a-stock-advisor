#!/usr/bin/env python3
"""
A股量化日报 - 统一推送系统
功能：生成完整的交易协助推送（盘前和日报合并）
执行时机：工作日8:00（盘前推送）和18:30（日报推送）
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'code'))

from datetime import datetime, timedelta
import logging
import json
import pickle
import pandas as pd
import numpy as np
import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/unified_push.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class UnifiedDailyPusher:
    """统一日报推送器"""
    
    def __init__(self):
        """初始化"""
        self.config = self._load_config()
        self.push_history_file = 'data/push_history.json'
        self.push_history = self._load_push_history()
        
    def _load_config(self):
        """加载配置"""
        config_file = 'config/feishu_config.json'
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _load_push_history(self):
        """加载推送历史"""
        if os.path.exists(self.push_history_file):
            try:
                with open(self.push_history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_push_history(self, push_data):
        """保存推送历史"""
        self.push_history.append(push_data)
        # 只保留最近30条
        if len(self.push_history) > 30:
            self.push_history = self.push_history[-30:]
        
        os.makedirs(os.path.dirname(self.push_history_file), exist_ok=True)
        with open(self.push_history_file, 'w', encoding='utf-8') as f:
            json.dump(self.push_history, f, ensure_ascii=False, indent=2)
    
    def _get_yesterday_push(self):
        """获取昨日推送"""
        if not self.push_history:
            return None
        
        today = datetime.now().strftime('%Y-%m-%d')
        # 找到最近一次非今日的推送
        for push in reversed(self.push_history):
            if push.get('date') != today:
                return push
        return None
    
    def _load_stock_data(self):
        """加载股票数据"""
        try:
            # 优先使用真实数据
            data_file = 'data/akshare_real_data_fixed.pkl'
            if os.path.exists(data_file):
                with open(data_file, 'rb') as f:
                    df = pickle.load(f)
                
                # 获取最新日期数据
                if 'date_dt' in df.columns:
                    latest_date = df['date_dt'].max()
                    latest_df = df[df['date_dt'] == latest_date].copy()
                else:
                    # 如果没有date_dt列，直接使用全部数据
                    latest_df = df.copy()
                
                # 过滤有效数据
                latest_df = latest_df[(latest_df['close'] > 0) & (latest_df['amount'] > 0)]
                
                # 过滤A股（sh和sz开头）
                if 'stock_code' in latest_df.columns:
                    a_stock_df = latest_df[latest_df['stock_code'].str[:2].isin(['sh', 'sz'])].copy()
                    return a_stock_df, latest_date if 'date_dt' in df.columns else datetime.now()
                
                return latest_df, latest_date if 'date_dt' in df.columns else datetime.now()
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            return None, None
    
    def _load_portfolio_state(self):
        """加载持仓状态"""
        portfolio_file = 'data/portfolio_state.json'
        if os.path.exists(portfolio_file):
            try:
                with open(portfolio_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return None
    
    def _load_selection_result(self):
        """加载选股结果"""
        selection_file = 'data/selection_result.json'
        if os.path.exists(selection_file):
            try:
                with open(selection_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return None
    
    def _load_rebalance_plan(self):
        """加载换仓计划"""
        rebalance_file = 'data/rebalance_plan.json'
        if os.path.exists(rebalance_file):
            try:
                with open(rebalance_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return None
    
    def generate_push_content(self, push_type='morning'):
        """生成推送内容
        
        Args:
            push_type: 'morning'（盘前）或 'evening'（日报）
        """
        now = datetime.now()
        today = now.strftime('%Y-%m-%d')
        
        content = []
        
        # 标题
        if push_type == 'morning':
            content.append('🦞 A股量化日报 - 盘前推送')
        else:
            content.append('🦞 A股量化日报 - 日报推送')
        
        content.append('━━━━━━━━━━━━━━━━━━━━━━━━')
        content.append(f'📅 推送时间: {now.strftime("%Y-%m-%d %H:%M")}')
        content.append(f'📌 类型: 实盘推送（含持仓跟踪）')
        
        # 加载数据
        stock_data, data_date = self._load_stock_data()
        if stock_data is not None:
            if hasattr(data_date, 'strftime'):
                data_date_str = data_date.strftime('%Y-%m-%d')
            else:
                data_date_str = str(data_date)
            content.append(f'📊 数据日期: {data_date_str}')
            content.append(f'📊 覆盖股票: {len(stock_data)}只A股')
        
        content.append('')
        
        # 1. 昨日回顾
        content.append('🕐 昨日回顾')
        content.append('────────────────────')
        yesterday_push = self._get_yesterday_push()
        if yesterday_push:
            content.append(f'昨日推送: {yesterday_push.get("date", "N/A")}')
            content.append(f'持仓数量: {yesterday_push.get("positions_count", 0)}只')
            
            # 显示昨日决策
            yesterday_decision = yesterday_push.get('today_decision', [])
            if yesterday_decision:
                content.append('')
                content.append('昨日决策执行情况:')
                for decision in yesterday_decision[:5]:
                    emoji = "🟢" if decision.get('type') == '建仓' else ("🔴" if decision.get('type') in ['清仓', '止损'] else "🟡")
                    content.append(f'{emoji} {decision.get("name", "N/A")} - {decision.get("reason", "")}')
            else:
                content.append('昨日: 无调整建议，保持原持仓')
        else:
            content.append('状态: 无历史推送记录（首次推送）')
            content.append('建议: 按照今日选股结果建仓')
        
        content.append('')
        
        # 2. 今日持仓
        content.append('📊 今日持仓')
        content.append('────────────────────')
        portfolio = self._load_portfolio_state()
        if portfolio and 'positions' in portfolio:
            positions = portfolio['positions']
            if positions:
                content.append(f'持仓总数: {len(positions)}只')
                
                # 计算总资产
                total_value = sum(p.get('current_value', 0) for p in positions)
                total_cost = sum(p.get('cost_basis', 0) for p in positions)
                total_profit = total_value - total_cost
                profit_pct = (total_profit / total_cost * 100) if total_cost > 0 else 0
                
                content.append(f'总资产: {total_value:,.0f}元')
                content.append(f'总盈亏: {total_profit:,.0f}元 ({profit_pct:.2f}%)')
                content.append('')
                content.append('持仓明细:')
                for pos in positions[:5]:
                    emoji = "📈" if pos.get('profit_loss', 0) > 0 else ("📉" if pos.get('profit_loss', 0) < 0 else "➡️")
                    content.append(f'{emoji} {pos.get("name", "N/A")}({pos.get("code", "N/A")})')
                    content.append(f'   盈亏: {pos.get("profit_loss", 0):,.0f}元 ({pos.get("profit_loss_pct", 0):.2f}%)')
            else:
                content.append('当前无持仓')
                content.append('→ 建议按照今日选股结果建仓')
        else:
            content.append('当前无持仓')
            content.append('→ 建议按照今日选股结果建仓')
        
        content.append('')
        
        # 3. 今日选股
        content.append('🎯 今日选股')
        content.append('────────────────────')
        
        selection = self._load_selection_result()
        if selection and 'selected_stocks' in selection:
            selected_stocks = selection['selected_stocks']
            portfolio_config = selection.get('portfolio_config', {})
            
            content.append(f'选股结果: {len(selected_stocks)}只股票')
            content.append('')
            
            for idx, stock in enumerate(selected_stocks[:10], 1):
                code = stock.get('code', stock.get('stock_code', 'N/A'))
                name = stock.get('name', stock.get('stock_name', 'N/A'))
                alpha_score = stock.get('alpha_score', 0)
                
                # 判断是核心还是卫星
                is_core = False
                for core_stock in portfolio_config.get('core', []):
                    if core_stock.get('code') == code:
                        is_core = True
                        break
                
                tag = "🔑核心" if is_core else "🌟卫星"
                content.append(f'{idx}. {tag} {name}({code})')
                content.append(f'   α得分: {alpha_score:.1f}分')
        elif stock_data is not None and len(stock_data) > 0:
            # 如果没有选股结果，基于成交额排序
            content.append('基于市场活跃度推荐:')
            content.append('')
            
            # 按成交额排序，取前10只
            top_stocks = stock_data.nlargest(10, 'amount')
            
            # 保存选股结果到JSON（用于推送脚本读取）
            try:
                selection_data = {
                    "selected_stocks": [
                        {
                            "rank": idx + 1,
                            "stock_code": stock_code,
                            "stock_name": row.get('stock_name', 'N/A'),
                            "score": float(row.get('amount', 0) / 1e8),  # 使用成交额作为分数
                            "reasons": "基于市场活跃度推荐"
                        }
                        for idx, (stock_code, row) in enumerate(top_stocks.iterrows())
                    ],
                    "portfolio_config": {
                        "n": 10,
                        "rebalance_frequency": "daily",
                        "weighting_method": "equal_weight",
                        "score_threshold": 0,
                        "factor_weights": {}
                    },
                    "timestamp": datetime.now().isoformat(),
                    "data_month": "daily",
                    "control_summary": {
                        "industry": "行业分散: N/A",
                        "volatility": "未应用",
                        "drawdown": "未应用"
                    }
                }
                
                selection_file = 'data/selection_result.json'
                os.makedirs(os.path.dirname(selection_file), exist_ok=True)
                with open(selection_file, 'w', encoding='utf-8') as f:
                    json.dump(selection_data, f, ensure_ascii=False, indent=2)
                print(f"[DEBUG] 选股结果已保存到: {selection_file}")
            except Exception as e:
                print(f"[WARNING] 保存选股结果失败: {e}")
            
            for idx, (stock_code, row) in enumerate(top_stocks.iterrows(), 1):
                stock_name = row.get('stock_name', 'N/A')
                close = row.get('close', 0)
                change_pct = row.get('change_pct', 0)
                amount = row.get('amount', 0)
                
                emoji = "📈" if change_pct > 0 else ("📉" if change_pct < 0 else "➡️")
                content.append(f'{idx}. {stock_code} {stock_name}')
                content.append(f'   {emoji} 收盘: {close:.2f}元 | 涨跌: {change_pct:+.2f}% | 成交: {amount/1e8:.2f}亿')
        else:
            content.append('⚠️ 暂无选股数据')
        
        content.append('')
        
        # 4. 今日决策
        content.append('🔄 今日决策')
        content.append('────────────────────')
        
        rebalance = self._load_rebalance_plan()
        if rebalance and 'actions' in rebalance:
            actions = rebalance['actions']
            if actions:
                for action in actions[:5]:
                    action_type = action.get('action', '')
                    emoji = "🛑" if action_type == 'sell' else ("⬇️" if action_type == 'reduce' else ("⬆️" if action_type == 'add' else ("📈" if action_type == 'buy' else "👀")))
                    
                    action_name = {
                        'sell': '清仓',
                        'reduce': '减仓',
                        'add': '加仓',
                        'buy': '建仓',
                        'review': '复查'
                    }.get(action_type, action_type)
                    
                    content.append(f'{emoji} {action.get("name", "N/A")}({action.get("code", "N/A")}) - {action_name}')
                    content.append(f'   原因: {action.get("reason", "")}')
            else:
                content.append('✓ 无需调整，当前持仓符合策略')
        else:
            content.append('✓ 无需调整，建议按选股结果建仓')
            content.append('')
            content.append('操作建议:')
            content.append('• 分批建仓，避免一次性买入')
            content.append('• 每只股票占总仓位10-12%')
            content.append('• 保留20%现金应对加仓机会')
        
        content.append('')
        
        # 5. 换仓逻辑
        content.append('⚙️ 换仓逻辑')
        content.append('────────────────────')
        content.append('止盈触发: 收益>20% → 分批止盈')
        content.append('止损触发: 亏损>10% → 立即止损')
        content.append('时间触发: 持仓>60天 → 评估换仓')
        content.append('因子触发: α得分下降>20% → 建议换仓')
        
        content.append('')
        
        # 6. 明日计划
        content.append('📅 明日计划')
        content.append('────────────────────')
        content.append('• 监控今日建仓执行情况')
        content.append('• 如收盘前30分钟有调仓，及时跟进')
        content.append('• 如未触发调仓，保持当前持仓')
        content.append('• 继续监控止盈止损信号')
        
        content.append('')
        
        # 7. 仓位管理
        content.append('💰 仓位管理建议')
        content.append('────────────────────')
        content.append('• 总仓位: 80%（核心60%+卫星20%）')
        content.append('• 现金: 20%（应对加仓）')
        content.append('• 单股最大仓位: 12%')
        content.append('• 组合最大回撤: -15%风险线')
        
        content.append('')
        
        # 8. 风控规则
        content.append('⚠️ 风控规则')
        content.append('────────────────────')
        content.append('• 单股止损线: -10%')
        content.append('• 单股止盈线: +20%')
        content.append('• 组合最大回撤: -15%')
        content.append('• 根据自身风险承受能力调整')
        
        content.append('')
        
        content.append('━━━━━━━━━━━━━━━━━━━━━━━━')
        content.append('📊 数据来源: AKShare A股实时数据')
        content.append(f'🦞 A股量化系统 v2.0 | {today}')
        
        push_content = '\n'.join(content)
        
        # 保存推送历史
        self._save_push_history({
            'date': today,
            'time': now.strftime('%H:%M:%S'),
            'type': push_type,
            'positions_count': len(portfolio['positions']) if portfolio and 'positions' in portfolio else 0,
            'content': push_content[:500]  # 只保存前500字符
        })
        
        return push_content
    
    def send_feishu_push(self, report):
        """发送飞书推送"""
        webhook_url = self.config.get('webhook_url')
        if not webhook_url:
            logger.warning("未配置webhook_url")
            return False
        
        payload = {
            "msg_type": "text",
            "content": {
                "text": report
            }
        }
        
        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("✓ 飞书推送成功")
                return True
            else:
                logger.error(f"飞书推送失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"发送推送失败: {e}", exc_info=True)
            return False
    
    def run(self, push_type='morning'):
        """执行推送"""
        logger.info("="*60)
        logger.info(f"A股量化日报推送开始 - {push_type}")
        logger.info("="*60)
        
        # 检查交易日
        now = datetime.now()
        if now.weekday() >= 5:
            logger.info(f"⚠️ 今天是周末，跳过推送")
            return 0
        
        logger.info(f"✓ 交易日")
        
        # 生成报告
        logger.info("生成推送报告...")
        report = self.generate_push_content(push_type)
        
        if report:
            logger.info("✓ 报告生成成功")
            
            # 保存报告
            os.makedirs('reports', exist_ok=True)
            report_file = f"reports/{push_type}_push_{now.strftime('%Y%m%d_%H%M')}.md"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"✓ 报告已保存: {report_file}")
            
            # 发送推送
            if self.send_feishu_push(report):
                logger.info("="*60)
                logger.info("✅ A股量化日报推送完成")
                logger.info("="*60)
                return 0
            else:
                logger.error("✗ 推送失败")
                return 1
        else:
            logger.error("✗ 报告生成失败")
            return 1

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='A股量化日报统一推送系统')
    parser.add_argument('--type', choices=['morning', 'evening'], default='morning',
                       help='推送类型: morning(盘前), evening(日报)')
    
    args = parser.parse_args()
    
    pusher = UnifiedDailyPusher()
    return pusher.run(args.type)

if __name__ == "__main__":
    sys.exit(main())
