#!/usr/bin/env python3
"""
自动化推送系统 - 代码承担主要工作
功能：自动执行完整推送流程
"""

import sys
import os

# 将 code 目录添加到路径最前面，支持本地导入
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
code_dir = os.path.join(project_root, 'code')
sys.path.insert(0, code_dir)
sys.path.insert(0, project_root)

from datetime import datetime
import logging
import json
import pickle
import pandas as pd
import numpy as np

# 导入核心模块（使用本地导入）
from alpha_stock_selector import AlphaStockSelector
from portfolio_tracker import PortfolioTracker
from rebalance_strategy import RebalanceStrategy
from risk_control_system import RiskControlSystem

# 导入飞书推送
from feishu_pusher import FeishuPusher

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/auto_push.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AutoPushSystem:
    """自动化推送系统"""

    def __init__(self):
        """初始化系统组件"""
        # 切换到项目根目录
        os.chdir(project_root)

        self.today = datetime.now().strftime('%Y-%m-%d')
        self.today_dt = datetime.now()

        # 初始化核心组件
        self.alpha_selector = AlphaStockSelector()
        self.portfolio_tracker = PortfolioTracker()
        self.rebalance_strategy = RebalanceStrategy()

        # 初始化风控系统（需要数据路径）
        self.risk_system = None

        # 初始化推送器
        self.pusher = self._init_pusher()

        # 数据文件
        self.data_file = 'data/akshare_real_data_fixed.pkl'
        self.push_history_file = 'data/push_history.json'

        # 日志记录
        self.execution_log = {
            'date': self.today,
            'timestamp': self.today_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'started',
            'steps': [],
            'errors': []
        }

    def _init_pusher(self):
        """初始化飞书推送"""
        config_file = 'config/feishu_config.json'
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                webhook = config.get('webhook_url')
                secret = config.get('webhook_secret')
                return FeishuPusher(webhook_url=webhook, secret=secret)
            except Exception as e:
                logger.error(f"加载飞书配置失败: {e}")
                return FeishuPusher()  # 空配置，不会实际推送
        return FeishuPusher()

    def _log_step(self, step_name: str, success: bool, details: str = ""):
        """记录执行步骤"""
        step = {
            'step': step_name,
            'success': success,
            'details': details,
            'time': datetime.now().strftime('%H:%M:%S')
        }
        self.execution_log['steps'].append(step)
        return step

    def load_data(self):
        """
        1. 自动加载最新市场数据
        """
        logger.info("="*70)
        logger.info("步骤1: 加载市场数据")
        logger.info("="*70)

        try:
            if not os.path.exists(self.data_file):
                raise FileNotFoundError(f"数据文件不存在: {self.data_file}")

            with open(self.data_file, 'rb') as f:
                df = pickle.load(f)

            # 获取最新日期数据
            if 'date_dt' in df.columns:
                latest_date = df['date_dt'].max()
                latest_df = df[df['date_dt'] == latest_date].copy()
                logger.info(f"✓ 数据日期: {latest_date}")
            else:
                latest_df = df.copy()
                logger.info("✓ 使用全部数据")

            # 过滤有效数据
            latest_df = latest_df[(latest_df['close'] > 0) & (latest_df['amount'] > 0)]
            logger.info(f"✓ 有效股票数: {len(latest_df)}")

            # 初始化风控系统
            try:
                self.risk_system = RiskControlSystem(self.data_file)
            except Exception as e:
                logger.warning(f"⚠️ 风控系统初始化失败: {e}")

            self._log_step("load_data", True, f"加载{len(latest_df)}只股票数据")
            return latest_df

        except Exception as e:
            error_msg = f"数据加载失败: {str(e)}"
            logger.error(error_msg)
            self.execution_log['errors'].append(error_msg)
            self._log_step("load_data", False, error_msg)
            raise

    def calculate_alpha_scores(self, df):
        """
        2. 计算α因子得分
        """
        logger.info("\n" + "="*70)
        logger.info("步骤2: 计算α因子得分")
        logger.info("="*70)

        try:
            # 使用AlphaStockSelector计算得分
            scores = pd.Series(self.alpha_selector.calculate_alpha_score(df))

            logger.info(f"✓ 计算完成，得分范围: {scores['alpha_score'].min():.2f} ~ {scores['alpha_score'].max():.2f}")

            self._log_step("calculate_alpha", True, f"计算{len(scores)}只股票α得分")
            return scores

        except Exception as e:
            error_msg = f"α因子计算失败: {str(e)}"
            logger.error(error_msg)
            self.execution_log['errors'].append(error_msg)
            self._log_step("calculate_alpha", False, error_msg)
            raise

    def run_selection(self, df):
        """
        3. 执行α因子选股
        """
        logger.info("\n" + "="*70)
        logger.info("步骤3: 执行α因子选股")
        logger.info("="*70)

        try:
            # 计算α因子得分
            df_with_score = self.calculate_alpha_scores(df)

            # 执行选股（取前10只）
            selected_stocks = self.alpha_selector.select_stocks(
                df_with_score,
                top_n=10,
                min_score_threshold=0.3
            )

            logger.info(f"✓ 选出{len(selected_stocks)}只股票")
            for idx, stock in enumerate(selected_stocks[:5], 1):
                logger.info(f"  {idx}. {stock['code']} {stock['name']} - 得分: {stock['score']:.2f}")

            self._log_step("run_selection", True, f"选出{len(selected_stocks)}只股票")
            return selected_stocks, df_with_score

        except Exception as e:
            error_msg = f"选股失败: {str(e)}"
            logger.error(error_msg)
            self.execution_log['errors'].append(error_msg)
            self._log_step("run_selection", False, error_msg)
            raise

    def check_risk(self):
        """
        4. 检查持仓风险（止盈/止损）
        """
        logger.info("\n" + "="*70)
        logger.info("步骤4: 检查持仓风险")
        logger.info("="*70)

        try:
            # 更新组合价值
            self.portfolio_tracker.update_portfolio_value()

            # 获取持仓列表
            positions = list(self.portfolio_tracker.positions.values())

            if not positions:
                logger.info("✓ 无持仓，跳过风控检查")
                self._log_step("check_risk", True, "无持仓")
                return {
                    'positions': [],
                    'warnings': [],
                    'actions': []
                }

            # 使用换仓策略检查止盈止损
            risk_actions = []
            warnings = []

            for position in positions:
                # 检查止盈
                take_profit = self.rebalance_strategy.check_take_profit(
                    position, position.current_price
                )
                if take_profit['trigger']:
                    warnings.append(f"{position.stock_name} 触发止盈 ({position.profit_loss_pct:.1f}%)")
                    risk_actions.append({
                        'action': 'sell',
                        'stock': position.stock_code,
                        'reason': take_profit['reason']
                    })

                # 检查止损
                stop_loss = self.rebalance_strategy.check_stop_loss(
                    position, position.current_price
                )
                if stop_loss['trigger']:
                    warnings.append(f"{position.stock_name} 触发止损 ({position.profit_loss_pct:.1f}%)")
                    risk_actions.append({
                        'action': 'sell',
                        'stock': position.stock_code,
                        'reason': stop_loss['reason']
                    })

            logger.info(f"✓ 检查{len(positions)}只持仓，{len(warnings)}个风险提示")

            if warnings:
                logger.warning("风险提示:")
                for w in warnings:
                    logger.warning(f"  ⚠️ {w}")

            self._log_step("check_risk", True, f"检查{len(positions)}只持仓，{len(warnings)}个风险")
            return {
                'positions': positions,
                'warnings': warnings,
                'actions': risk_actions
            }

        except Exception as e:
            error_msg = f"风控检查失败: {str(e)}"
            logger.error(error_msg)
            self.execution_log['errors'].append(error_msg)
            self._log_step("check_risk", False, error_msg)
            raise

    def evaluate_rebalance(self, df, selected_stocks):
        """
        5. 评估换仓决策
        """
        logger.info("\n" + "="*70)
        logger.info("步骤5: 评估换仓决策")
        logger.info("="*70)

        try:
            # 执行换仓评估
            selected_codes = [s['code'] for s in selected_stocks]
            rebalance_plan = self.rebalance_strategy.generate_rebalance_plan(
                self.portfolio_tracker,
                df,
                selected_codes
            )

            logger.info(f"✓ 换仓评估完成")
            logger.info(f"  - 买入: {len(rebalance_plan.get('buys', []))}只")
            logger.info(f"  - 卖出: {len(rebalance_plan.get('sells', []))}只")

            self._log_step("evaluate_rebalance", True,
                          f"买入{len(rebalance_plan.get('buys', []))}只，卖出{len(rebalance_plan.get('sells', []))}只")
            return rebalance_plan

        except Exception as e:
            error_msg = f"换仓评估失败: {str(e)}"
            logger.error(error_msg)
            self.execution_log['errors'].append(error_msg)
            self._log_step("evaluate_rebalance", False, error_msg)
            # 返回空计划，不中断流程
            return {'buys': [], 'sells': [], 'reason': str(e)}

    def generate_report(self, df, selected_stocks, risk, rebalance_plan):
        """
        6. 生成完整推送内容
        """
        logger.info("\n" + "="*70)
        logger.info("步骤6: 生成推送内容")
        logger.info("="*70)

        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M')
            report = f"""
📊 A股量化日报 - {now}
{'='*50}

🎯 核心推荐 Top 5
"""

            # 核心推荐
            for i, stock in enumerate(selected_stocks[:5], 1):
                report += f"{i}. {stock['name']}({stock['code']}) - α得分: {stock['score']:.2f}\n"

            # 组合概况
            report += f"\n💼 组合概况\n"
            positions = risk['positions']
            if positions:
                total_value = sum(p.market_value for p in positions)
                total_pnl = sum(p.profit_loss for p in positions)
                report += f"持仓数量: {len(positions)}只\n"
                report += f"组合市值: ¥{total_value:,.0f}\n"
                report += f"当日盈亏: ¥{total_pnl:,.0f} ({total_pnl/total_value*100:.2f}%)\n"

                # 盈亏详情
                profit_positions = [p for p in positions if p.profit_loss > 0]
                loss_positions = [p for p in positions if p.profit_loss <= 0]
                if profit_positions:
                    report += f"  盈利: {len(profit_positions)}只\n"
                if loss_positions:
                    report += f"  亏损: {len(loss_positions)}只\n"
            else:
                report += "当前无持仓\n"

            # 风险提示
            if risk['warnings']:
                report += f"\n⚠️ 风险提示\n"
                for w in risk['warnings'][:3]:  # 只显示前3个
                    report += f"  • {w}\n"

            # 换仓建议
            if rebalance_plan.get('buys') or rebalance_plan.get('sells'):
                report += f"\n🔄 换仓建议\n"
                if rebalance_plan.get('buys'):
                    report += f"建议买入: {', '.join(rebalance_plan['buys'][:3])}\n"
                if rebalance_plan.get('sells'):
                    report += f"建议卖出: {', '.join(rebalance_plan['sells'][:3])}\n"

            # 执行摘要
            report += f"\n📈 执行摘要\n"
            report += f"数据更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            for step in self.execution_log['steps']:
                status = "✓" if step['success'] else "✗"
                report += f"  {status} {step['step']}\n"

            logger.info("✓ 推送内容生成完成")
            self._log_step("generate_report", True, "生成完整推送内容")

            return report

        except Exception as e:
            error_msg = f"报告生成失败: {str(e)}"
            logger.error(error_msg)
            self.execution_log['errors'].append(error_msg)
            self._log_step("generate_report", False, error_msg)
            raise

    def send_push(self, report):
        """
        7. 自动发送飞书推送
        """
        logger.info("\n" + "="*70)
        logger.info("步骤7: 发送飞书推送")
        logger.info("="*70)

        try:
            success = self.pusher.send_text(report)

            if success:
                logger.info("✓ 飞书推送成功")
                self._log_step("send_push", True, "推送成功")
                return True
            else:
                logger.warning("⚠️ 飞书推送失败")
                self._log_step("send_push", False, "推送失败")
                return False

        except Exception as e:
            error_msg = f"推送发送失败: {str(e)}"
            logger.error(error_msg)
            self.execution_log['errors'].append(error_msg)
            self._log_step("send_push", False, error_msg)
            return False

    def save_history(self, report, selected_stocks, risk, rebalance_plan):
        """
        8. 记录推送历史
        """
        logger.info("\n" + "="*70)
        logger.info("步骤8: 记录推送历史")
        logger.info("="*70)

        try:
            # 加载历史
            history = []
            if os.path.exists(self.push_history_file):
                try:
                    with open(self.push_history_file, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                except:
                    history = []

            # 添加新记录
            record = {
                'date': self.today,
                'timestamp': datetime.now().isoformat(),
                'report': report,
                'selected_stocks': selected_stocks,
                'positions': [p.__dict__ for p in risk['positions']],
                'rebalance_plan': rebalance_plan,
                'execution_log': self.execution_log
            }
            history.append(record)

            # 只保留最近30条
            if len(history) > 30:
                history = history[-30:]

            # 保存
            os.makedirs(os.path.dirname(self.push_history_file), exist_ok=True)
            with open(self.push_history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)

            logger.info(f"✓ 推送历史已保存（共{len(history)}条）")
            self._log_step("save_history", True, f"保存历史记录")

        except Exception as e:
            error_msg = f"历史保存失败: {str(e)}"
            logger.error(error_msg)
            self.execution_log['errors'].append(error_msg)
            self._log_step("save_history", False, error_msg)

    def run(self):
        """
        执行完整推送流程
        """
        logger.info("\n" + "="*70)
        logger.info("🚀 开始执行自动化推送流程")
        logger.info(f"📅 日期: {self.today}")
        logger.info("="*70)

        try:
            # 1. 加载数据
            df = self.load_data()

            # 2. 选股和α得分计算
            selected_stocks, df_with_score = self.run_selection(df)

            # 3. 风控检查
            risk = self.check_risk()

            # 4. 换仓评估
            rebalance_plan = self.evaluate_rebalance(df_with_score, selected_stocks)

            # 5. 生成报告
            report = self.generate_report(df_with_score, selected_stocks, risk, rebalance_plan)

            # 6. 发送推送
            push_success = self.send_push(report)

            # 7. 记录历史
            self.save_history(report, selected_stocks, risk, rebalance_plan)

            # 更新执行状态
            self.execution_log['status'] = 'completed'

            logger.info("\n" + "="*70)
            logger.info("✅ 推送流程执行完成")
            logger.info("="*70)

            summary = f"""
执行摘要:
- 日期: {self.today}
- 选股: {len(selected_stocks)}只
- 持仓: {len(risk['positions'])}只
- 风险提示: {len(risk['warnings'])}个
- 推送状态: {'成功' if push_success else '失败'}
"""

            logger.info(summary)
            return True, summary

        except Exception as e:
            # 更新执行状态
            self.execution_log['status'] = 'failed'
            self.execution_log['errors'].append(str(e))

            logger.error("\n" + "="*70)
            logger.error("❌ 推送流程执行失败")
            logger.error("="*70)
            logger.error(f"错误详情: {str(e)}")

            # 尝试保存日志
            try:
                os.makedirs(os.path.dirname(self.push_history_file), exist_ok=True)
                with open(self.push_history_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({'log': self.execution_log}) + '\n')
            except:
                pass

            return False, f"推送失败: {str(e)}"


def main():
    """主函数"""
    try:
        system = AutoPushSystem()
        success, message = system.run()
        return 0 if success else 1
    except Exception as e:
        logger.error(f"系统异常: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
