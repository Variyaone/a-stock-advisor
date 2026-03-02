#!/usr/bin/env python3
"""
A股量化系统 - 每日运行脚本
功能：获取最新数据 → 选股 → 生成报告 → 飞书推送
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

import pandas as pd
import numpy as np
from datetime import datetime
import json

# 导入Phase 3模块
from multi_factor_model import MultiFactorScoreModel
from stock_selector import StockSelector
from risk_controller import RiskController
from generate_report import generate_daily_recommendation, save_factor_scores

def load_latest_config():
    """加载最新配置"""
    # 加载因子得分（如果存在）
    factor_scores = {}
    scores_file = 'reports/factor_scores.json'
    if os.path.exists(scores_file):
        with open(scores_file, 'r') as f:
            factor_scores = json.load(f)
    else:
        # 创建默认因子得分
        factor_scores = {
            'PE_TTM': 0.1,
            'PB': 0.08,
            '市值_亿': 0.05,
            '股息率': 0.12,
            'ROE': 0.15
        }
        # 保存默认配置
        save_factor_scores(factor_scores, scores_file)
    
    # 加载因子权重（使用IC加权）
    score_model = MultiFactorScoreModel()
    score_model.set_ic_weighted(factor_scores)
    
    # 创建选股器
    stock_selector = StockSelector(score_model, n=10)
    
    # 创建风险控制器
    risk_controller = RiskController()
    
    return score_model, stock_selector, risk_controller

def load_latest_config(factor_data: pd.DataFrame = None):
    """加载最新配置，如果提供了数据则自动检测因子"""
    # 加载因子得分（如果存在）
    factor_scores = {}
    scores_file = 'reports/factor_scores.json'

    # 创建得分模型
    score_model = MultiFactorScoreModel()

    # 如果提供了数据，自动检测因子
    if factor_data is not None:
        print("🔍 自动检测因子...")
        factor_columns = score_model.auto_detect_factors(factor_data)
        print(f"✓ 检测到 {len(factor_columns)} 个因子: {', '.join(factor_columns[:5])}...")

        # 尝试加载保存的因子得分
        if os.path.exists(scores_file):
            try:
                with open(scores_file, 'r') as f:
                    saved_scores = json.load(f)
                # 只使用存在于数据中的因子
                factor_scores = {k: v for k, v in saved_scores.items() if k in factor_columns}
                if factor_scores:
                    print(f"✓ 加载了 {len(factor_scores)} 个已保存的因子得分")
            except Exception as e:
                print(f"⚠️ 加载保存的因子得分失败: {e}")
    elif os.path.exists(scores_file):
        with open(scores_file, 'r') as f:
            factor_scores = json.load(f)

    # 如果没有因子得分，创建默认值
    if not factor_scores and factor_data is not None:
        factor_columns = list(score_model.factor_weights.keys())
        factor_scores = {col: 0.1 for col in factor_columns}
        # 保存默认配置
        try:
            save_factor_scores(factor_scores, scores_file)
            print(f"✓ 保存了默认因子配置")
        except Exception as e:
            print(f"⚠️ 保存因子配置失败: {e}")

    # 加载因子权重（使用IC加权）
    if factor_scores:
        available_factors = list(factor_scores.keys()) if not factor_data else None
        score_model.set_ic_weighted(factor_scores, available_factors)

    # 创建选股器
    stock_selector = StockSelector(score_model, n=10)

    # 创建风险控制器
    risk_controller = RiskController()

    return score_model, stock_selector, risk_controller

def load_latest_data():
    """加载最新数据"""
    # 尝试加载因子数据
    factor_data_path = 'data/factor_data.pkl'

    if os.path.exists(factor_data_path):
        factor_data = pd.read_pickle(factor_data_path)
    else:
        # 加载mock数据作为备用
        print("⚠️ 未找到factor_data.pkl，使用mock_data.pkl")
        factor_data = pd.read_pickle('data/mock_data.pkl')

        # 处理mock数据以符合格式要求
        if 'date' not in factor_data.columns and len(factor_data) > 0:
            # 添加日期列（添加当前日期）
            factor_data['date'] = pd.Timestamp.now()

    # 尝试加载股票列表
    stock_list_path = 'data/stock_list.csv'
    if os.path.exists(stock_list_path):
        stock_list = pd.read_csv(stock_list_path)
    else:
        # 创建空的股票列表
        stock_list = pd.DataFrame(columns=['股票代码', '股票名称', 'is_suspended'])

    return factor_data, stock_list

def get_trading_day_check():
    """检查今天是否为交易日"""
    today = datetime.now()

    # 简单判断：周六周日不推送
    if today.weekday() >= 5:  # 5=周六, 6=周日
        return False, "今天是周末，不推送"

    # TODO: 接入交易日历API进行更精确判断

    return True, "今天是交易日"

def load_webhook_config():
    """加载webhook配置"""
    config_file = 'config/feishu_config.json'
    if os.path.exists(config_file):
        with open(config_file) as f:
            config = json.load(f)
            return config.get('webhook_url')
    return None

def run_daily_selection():
    """执行每日选股"""
    print("="*60)
    print("A股量化系统 - 每日选股")
    print("="*60)
    print(f"运行时间: {datetime.now()}\n")

    # 1. 检查交易日
    is_trading_day, reason = get_trading_day_check()
    if not is_trading_day:
        print(f"⚠️ {reason}")
        return None

    # 2. 加载数据
    print("📊 加载数据...")
    factor_data, stock_list = load_latest_data()

    # 获取最新可用数据
    if 'date' in factor_data.columns:
        latest_date = factor_data['date'].max()
        latest_factor_data = factor_data[factor_data['date'] == latest_date]

        if len(latest_factor_data) == 0:
            print("⚠️ 没有最新数据，使用所有数据")
            latest_factor_data = factor_data.copy()
    else:
        print("⚠️ 数据缺少日期列，使用所有数据")
        latest_factor_data = factor_data.copy()
        latest_date = pd.Timestamp.now()

    print(f"✓ 数据日期: {latest_date.date() if hasattr(latest_date, 'date') else latest_date}")
    print(f"✓ 可选股票数量: {len(latest_factor_data)}\n")

    # 3. 确保有stock_code列
    if 'stock_code' not in latest_factor_data.columns:
        if '股票代码' in latest_factor_data.columns:
            latest_factor_data = latest_factor_data.rename(columns={'股票代码': 'stock_code'})
        else:
            # 使用index作为stock_code
            latest_factor_data = latest_factor_data.reset_index()
            if 'index' in latest_factor_data.columns and 'stock_code' not in latest_factor_data.columns:
                latest_factor_data = latest_factor_data.rename(columns={'index': 'stock_code'})

    # 4. 加载配置（基于实际数据）
    print("📋 加载配置...")
    score_model, stock_selector, risk_controller = load_latest_config(latest_factor_data.copy())
    print("✓ 配置加载完成\n")

    # 确保有stock_code列
    if 'stock_code' not in latest_factor_data.columns:
        if '股票代码' in latest_factor_data.columns:
            latest_factor_data = latest_factor_data.rename(columns={'股票代码': 'stock_code'})
        else:
            # 使用index作为stock_code
            latest_factor_data = latest_factor_data.reset_index()
            if 'index' in latest_factor_data.columns and 'stock_code' not in latest_factor_data.columns:
                latest_factor_data = latest_factor_data.rename(columns={'index': 'stock_code'})

    # 4. 选股
    print("🎯 执行选股...")
    try:
        selected = stock_selector.select_top_stocks(
            latest_factor_data.set_index('stock_code').copy(),
            date=str(latest_date.date()) if hasattr(latest_date, 'date') else str(latest_date)
        )
        print(f"✓ 选出 {len(selected)} 只股票\n")
    except Exception as e:
        print(f"✗ 选股失败: {e}")
        import traceback
        traceback.print_exc()
        return None

    # 5. 风险控制
    print("🛡️ 风险控制...")
    try:
        # 准备因子数据以stock_code为索引
        factor_data_indexed = latest_factor_data.set_index('stock_code').copy()

        controlled, control_summary = risk_controller.apply_all_controls(
            selected, stock_list, factor_data_indexed
        )
        print(f"✓ 风险控制完成")

        # 打印控制摘要
        summary_text = risk_controller.format_control_summary(control_summary)
        for line in summary_text.split('\n'):
            print(f"  {line}")
        print()
    except Exception as e:
        print(f"✗ 风险控制失败: {e}")
        import traceback
        traceback.print_exc()
        controlled = selected  # 使用未过滤的结果

    # 6. 生成报告
    print("📝 生成报告...")
    try:
        report = generate_daily_recommendation(
            datetime.now(),
            latest_factor_data.set_index('stock_code').copy(),
            score_model,
            stock_selector,
            risk_controller,
            n=10
        )

        # 保存报告
        report_date = datetime.now().strftime('%Y%m%d')
        report_path = f'reports/daily_recommendation_{report_date}.md'

        # 确保reports目录存在
        os.makedirs('reports', exist_ok=True)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✓ 报告已保存: {report_path}\n")
    except Exception as e:
        print(f"✗ 报告生成失败: {e}")
        import traceback
        traceback.print_exc()
        return None

    # 7. 飞书推送
    print("📱 飞书推送...")
    webhook_url = load_webhook_config()

    if webhook_url:
        try:
            from feishu_pusher import FeishuPusher
            # 不传递secret参数，使用无签名模式
            pusher = FeishuPusher(webhook_url, secret=None)
            pusher.send_report(report_path)
            print("✓ 飞书推送完成\n")
        except ImportError:
            print("⚠️ 未找到feishu_pusher模块，跳过推送\n")
        except Exception as e:
            print(f"✗ 飞书推送失败: {e}")
            import traceback
            traceback.print_exc()
            print()
    else:
        print("⚠️ 未配置webhook，跳过推送\n")

    print("="*60)
    print("✅ 每日选股完成！")
    print("="*60)

    return report_path

if __name__ == "__main__":
    try:
        report_path = run_daily_selection()
        if report_path:
            print(f"\n📄 报告路径: {report_path}")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
