#!/usr/bin/env python3
"""
A股量化系统 v2.0 - 每日运行脚本
集成持仓跟踪、α选股、换仓策略，提供连续性推送
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

import pandas as pd
import numpy as np
from datetime import datetime
import json

from portfolio_tracker import PortfolioTracker
from alpha_stock_selector import AlphaStockSelector
from rebalance_strategy import RebalanceStrategy
from enhanced_pusher import EnhancedPusher
from monthly_attribution import MonthlyAttribution

def load_latest_data():
    """
    加载最新数据
    
    Returns:
        (stock_data, alpha_scores)
    """
    print("=" * 60)
    print("📊 数据加载")
    print("=" * 60)
    
    # 尝试加载因子数据
    factor_data_path = 'data/factor_data.pkl'

    if os.path.exists(factor_data_path):
        factor_data = pd.read_pickle(factor_data_path)
        print("✓ 加载因子数据")
    else:
        # 加载mock数据作为备用
        print("⚠️ 未找到factor_data.pkl，使用mock_data.pkl")
        factor_data = pd.read_pickle('data/mock_data.pkl')

        # 处理mock数据以符合格式要求
        if 'date' not in factor_data.columns and len(factor_data) > 0:
            factor_data['date'] = pd.Timestamp.now()

    # 获取最新可用数据
    if 'date' in factor_data.columns:
        latest_date = factor_data['date'].max()
        latest_factor_data = factor_data[factor_data['date'] == latest_date]

        if len(latest_factor_data) == 0:
            print("⚠️ 没有最新数据，使用所有数据")
            latest_factor_data = factor_data.copy()
            latest_date = pd.Timestamp.now()
    else:
        print("⚠️ 数据缺少日期列，使用所有数据")
        latest_factor_data = factor_data.copy()
        latest_date = pd.Timestamp.now()

    # 确保有stock_code列
    if 'stock_code' not in latest_factor_data.columns:
        if '股票代码' in latest_factor_data.columns:
            latest_factor_data = latest_factor_data.rename(columns={'股票代码': 'stock_code'})
        else:
            latest_factor_data = latest_factor_data.reset_index()
            if 'index' in latest_factor_data.columns and 'stock_code' not in latest_factor_data.columns:
                latest_factor_data = latest_factor_data.rename(columns={'index': 'stock_code'})

    print(f"✓ 数据日期: {latest_date}")
    print(f"✓ 可选股票数量: {len(latest_factor_data)}")
    print(f"✓ 数据列: {', '.join(latest_factor_data.columns[:10])}...\n")
    
    return latest_factor_data.set_index('stock_code'), latest_date

def run_daily_selection_v2():
    """
    执行每日选股 v2.0
    """
    print("=" * 60)
    print("🦞 A股量化系统 v2.0 - 每日选股")
    print("=" * 60)
    print(f"运行时间: {datetime.now()}\n")

    # 1. 检查交易日
    today = datetime.now()
    if today.weekday() >= 5:  # 周末
        print("⚠️ 今天是周末，不推送")
        return None

    # 2. 加载数据
    stock_data, latest_date = load_latest_data()

    if stock_data is None or stock_data.empty:
        print("❌ 数据加载失败")
        return None

    # 3. 初始化系统组件
    print("=" * 60)
    print("🔧 初始化系统组件")
    print("=" * 60)
    
    portfolio_tracker = PortfolioTracker()
    alpha_selector = AlphaStockSelector()
    rebalance_strategy = RebalanceStrategy()
    enhanced_pusher = EnhancedPusher()
    attribution_analyzer = MonthlyAttribution()
    
    print("✓ 持仓跟踪器")
    print("✓ α选股器")
    print("✓ 换仓策略")
    print("✓ 增强推送器")
    print("✓ 归因分析器\n")
    
    # 4. 计算α得分
    print("=" * 60)
    print("📊 计算α因子得分")
    print("=" * 60)
    
    alpha_scores = alpha_selector.calculate_alpha_score(stock_data)
    print(f"✓ α得分范围: {alpha_scores.min():.1f} - {alpha_scores.max():.1f}")
    print(f"✓ 均值: {alpha_scores.mean():.1f} | 中位数: {alpha_scores.median():.1f}\n")
    
    # 5. 执行选股
    selected_stocks, portfolio_config = alpha_selector.select_stocks(
        stock_data, n=10, apply_filters=True
    )
    
    # 6. 更新持仓价格
    print("=" * 60)
    print("💰 更新持仓价格")
    print("=" * 60)
    
    # 从选股数据中提取当前价格
    current_prices = {}
    for stock_code in stock_data.index:
        price = stock_data.loc[stock_code, 'close'] if 'close' in stock_data.columns else None
        if price is not None:
            current_prices[stock_code] = price
    
    if current_prices:
        portfolio_tracker.update_prices(current_prices)
        print(f"✓ 更新 {len(current_prices)} 只股票价格\n")
    else:
        print("⚠️ 无价格数据可更新\n")
    
    # 7. 显示持仓状态
    print("=" * 60)
    print("📊 当前持仓状态")
    print("=" * 60)
    
    portfolio_summary = portfolio_tracker.get_portfolio_summary()
    print(f"总资产: {portfolio_summary['总_assets']:,.0f}元")
    print(f"现金: {portfolio_summary['现金']:,.0f}元 ({portfolio_summary['现金比例']:.1f}%)")
    print(f"持仓市值: {portfolio_summary['持仓市值']:,.0f}元 ({portfolio_summary['持仓比例']:.1f}%)")
    print(f"持仓数量: {portfolio_summary['持仓数量']}只")
    print(f"总盈亏: {portfolio_summary['总盈亏']:,.0f}元 ({portfolio_summary['总盈亏%']:.2f}%)")
    
    if portfolio_summary['持仓数量'] > 0:
        print(f"  盈利股票: {portfolio_summary['盈利股票数']}只")
        print(f"  亏损股票: {portfolio_summary['亏损股票数']}只")
    
    print()
    
    # 8. 评估换仓
    rebalance_plan = rebalance_strategy.evaluate_rebalancing(
        portfolio_tracker,
        stock_data,
        alpha_scores,
        portfolio_config
    )
    
    # 9. 生成推送内容
    print("=" * 60)
    print("📝 生成推送内容")
    print("=" * 60)
    
    push_content = enhanced_pusher.generate_push_content(stock_data, alpha_scores)
    
    print(f"✓ 推送内容长度: {len(push_content)} 字符\n")
    
    # 保存推送内容
    report_date = datetime.now().strftime('%Y%m%d')
    report_path = f'reports/daily_push_v2_{report_date}.txt'
    
    os.makedirs('reports', exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(push_content)
    
    print(f"✓ 推送内容已保存: {report_path}\n")
    
    # 10. 飞书推送
    print("=" * 60)
    print("📱 飞书推送")
    print("=" * 60)
    
    config = enhanced_pusher.config
    
    if not config.get('webhook_url'):
        print("⚠️ 未配置webhook_url，跳过推送")
    elif not config.get('enabled'):
        print("⚠️ 推送已禁用，跳过推送")
    else:
        try:
            from official_push_v2 import send_feishu_message
            
            secret = None
            if config.get('sign_enabled', False):
                secret = "ziMc9jEc3zkMKUz9lpoEje"
            
            success = send_feishu_message(
                push_content,
                config['webhook_url'],
                secret
            )
            
            if success:
                print("✓ 飞书推送完成\n")
            else:
                print("✗ 飞书推送失败\n")
                
        except ImportError as e:
            print(f"⚠️ 无法导入推送模块: {e}")
            print("  可以手动使用 official_push_v2.py 推送\n")
        except Exception as e:
            print(f"✗ 推送异常: {e}\n")
    
    # 11. 生成持仓日报
    print("=" * 60)
    print("📊 生成持仓日报")
    print("=" * 60)
    
    daily_report = portfolio_tracker.generate_daily_report()
    
    daily_report_path = f'data/daily_report_{report_date}.md'
    with open(daily_report_path, 'w', encoding='utf-8') as f:
        f.write(daily_report)
    
    print(f"✓ 持仓日报已保存: {daily_report_path}\n")
    print(daily_report)
    
    # 12. 月度归因（如果是月初）
    if today.day == 1:
        print("=" * 60)
        print("📈 月度归因分析")
        print("=" * 60)
        
        # 这里需要准备归因数据
        # 由于需要历史数据，这里仅做演示
        print("⚠️ 需要准备历史数据进行归因分析")
        print("→ 请参考 monthly_attribution.py 模块\n")
    
    # 13. 完成
    print("=" * 60)
    print("✅ 每日选股 v2.0 完成！")
    print("=" * 60)
    print(f"\n生成的文件:")
    print(f"  • 推送内容: {report_path}")
    print(f"  • 持仓日报: {daily_report_path}")
    print(f"  • 持仓状态: data/portfolio_state.json")
    print(f"  • 交易决策: data/trading_decisions.json")
    print(f"  • 每日绩效: data/daily_performance.json")
    print(f"  • 换仓历史: data/rebalance_history.json")
    
    return report_path


if __name__ == "__main__":
    try:
        report_path = run_daily_selection_v2()
        if report_path:
            print(f"\n📄 报告路径: {report_path}")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
