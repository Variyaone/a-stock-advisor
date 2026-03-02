#!/usr/bin/env python3
"""
A股盘前推送脚本（增强版）
任务：生成完整的交易协助推送内容
执行时机：工作日8:00
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'code'))

from datetime import datetime
import logging
import json
import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/morning_push.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def check_trading_day():
    """检查是否为交易日"""
    today = datetime.now()

    # 周末不推送
    if today.weekday() >= 5:  # 5=周六, 6=周日
        return False, "今天是周末"

    # TODO: 接入交易日历API
    return True, "交易日"

def generate_full_push_report():
    """生成完整的交易协助推送报告"""
    try:
        now = datetime.now()
        content = []

        content.append('🦞 A股量化日报 - 交易协助推送')
        content.append('━━━━━━━━━━━━━━━━━━━━━━━━')
        content.append(f'📅 推送时间: {now.strftime("%Y-%m-%d %H:%M")}')
        content.append(f'📌 类型: 实盘推送（含持仓跟踪）')
        content.append('')

        # 1. 昨日回顾
        content.append('🕐 昨日回顾')
        content.append('────────────────────')

        # 尝试加载昨日推送记录
        push_log_file = 'data/push_log.json'
        yesterday_plan = None
        if os.path.exists(push_log_file):
            try:
                with open(push_log_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    if len(history) > 0:
                        # 找到非今日的最新记录
                        today_str = now.strftime('%Y-%m-%d')
                        for push in reversed(history):
                            if push.get('date') != today_str:
                                yesterday_plan = push
                                break
            except:
                pass

        if yesterday_plan:
            content.append(f'状态: 已执行昨日推送 ({yesterday_plan.get("date", "N/A")})')
            content.append(f'持仓数量: {yesterday_plan.get("positions_count", 0)}只')

            # 显示昨日决策
            yesterday_decision = yesterday_plan.get('today_decision', [])
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

        # 尝试加载持仓状态
        portfolio_file = 'data/portfolio_state.json'
        if os.path.exists(portfolio_file):
            try:
                with open(portfolio_file, 'r', encoding='utf-8') as f:
                    portfolio = json.load(f)

                positions = portfolio.get('positions', [])
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
                        profit = pos.get('profit_loss', 0)
                        profit_pct = pos.get('profit_loss_pct', 0)
                        holding_days = pos.get('holding_days', 0)
                        content.append(f'{emoji} {pos.get("name", "N/A")}({pos.get("code", "N/A")})')
                        content.append(f'   盈亏: {profit:,.0f}元 ({profit_pct:.2f}%) | 持仓天数: {holding_days}天')
                else:
                    content.append('当前无持仓')
                    content.append('→ 建议按照今日选股结果建仓')
            except Exception as e:
                logger.warning(f'加载持仓失败: {e}')
                content.append('当前无持仓')
                content.append('→ 建议按照今日选股结果建仓')
        else:
            content.append('当前无持仓')
            content.append('→ 建议按照今日选股结果建仓')

        content.append('')

        # 3. 今日选股
        content.append('🎯 今日选股（α因子筛选）')
        content.append('────────────────────')

        # 尝试加载选股结果
        selection_file = 'data/selection_result.json'
        selection_data = None
        if os.path.exists(selection_file):
            try:
                with open(selection_file, 'r', encoding='utf-8') as f:
                    selection_data = json.load(f)
            except:
                pass

        if selection_data and 'selected_stocks' in selection_data:
            selected_stocks = selection_data['selected_stocks']
            portfolio_config = selection_data.get('portfolio_config', {})

            content.append(f'选定股票: {len(selected_stocks)}只')
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
        else:
            content.append('⚠️ 暂无选股数据')
            content.append('→ 系统正在处理数据')

        content.append('')

        # 4. 今日决策
        content.append('🔄 今日决策')
        content.append('────────────────────')

        # 尝试加载换仓计划
        rebalance_file = 'data/rebalance_plan.json'
        rebalance_plan = None
        if os.path.exists(rebalance_file):
            try:
                with open(rebalance_file, 'r', encoding='utf-8') as f:
                    rebalance_plan = json.load(f)
            except:
                pass

        if rebalance_plan and 'actions' in rebalance_plan:
            actions = rebalance_plan['actions']
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
        content.append('📊 数据来源: α因子选股 + 持仓跟踪')
        content.append(f'🦞 A股量化系统 v2.0 | {now.strftime("%Y-%m-%d")}')

        return '\n'.join(content)

    except Exception as e:
        logger.error(f"生成报告失败: {e}", exc_info=True)
        return None

def send_feishu_push(report):
    """发送飞书推送"""
    try:
        # 加载配置
        config_file = 'config/feishu_config.json'
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                webhook_url = config.get('webhook_url')
        else:
            logger.warning("未找到飞书配置文件")
            return False

        if not webhook_url:
            logger.warning("未配置webhook_url")
            return False

        # 发送推送（使用飞书标准文本格式）
        payload = {
            "msg_type": "text",
            "content": {
                "text": report
            }
        }

        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            logger.info("✓ 飞书推送成功")
            return True
        else:
            logger.error(f"飞书推送失败: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"发送推送失败: {e}", exc_info=True)
        return False

def main():
    """主函数"""
    logger.info("="*60)
    logger.info("盘前推送任务开始（增强版）")
    logger.info("="*60)

    try:
        # 检查交易日
        is_trading_day, reason = check_trading_day()
        if not is_trading_day:
            logger.info(f"⚠️ {reason}，跳过推送")
            return 0

        logger.info(f"✓ {reason}")

        # 生成报告
        logger.info("生成推送报告...")
        report = generate_full_push_report()

        if report:
            logger.info("✓ 报告生成成功")

            # 保存报告
            os.makedirs('reports', exist_ok=True)
            report_file = f"reports/morning_push_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"✓ 报告已保存: {report_file}")

            # 发送推送
            send_feishu_push(report)
        else:
            logger.error("✗ 报告生成失败")
            return 1

        logger.info("="*60)
        logger.info("✅ 盘前推送任务完成")
        logger.info("="*60)
        return 0

    except Exception as e:
        logger.error(f"❌ 盘前推送异常: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
