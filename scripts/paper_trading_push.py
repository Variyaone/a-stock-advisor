#!/usr/bin/env python3
"""
A股盘前推送脚本
任务：生成盘前推荐并推送
执行时机：工作日8:00
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'code'))

from datetime import datetime
import logging
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/paper_trading_push.log'),
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

def generate_push_report():
    """生成推送报告"""
    try:
        # 加载最新数据
        logger.info("加载最新数据...")
        from data_pipeline_v3 import DataPipelineV3
        pipeline = DataPipelineV3()
        data = pipeline.get_latest_data()

        if data is None:
            logger.error("没有可用数据")
            return None

        # 获取最新日期（灵活匹配列名）
        date_col = 'date' if 'date' in data.columns else 'date_dt'
        latest_date = data[date_col].max()
        latest_data = data[data[date_col] == latest_date].copy()

        logger.info(f"数据日期: {latest_date.strftime('%Y-%m-%d') if hasattr(latest_date, 'strftime') else latest_date}")
        logger.info(f"可选股票数: {len(latest_data)}")

        # 确定股票代码和名称列
        stock_code_col = 'stock_code' if 'stock_code' in latest_data.columns else 'ts_code'
        stock_name_col = 'stock_name' if 'stock_name' in latest_data.columns else 'stock_name'

        # 按交易额排序，取成交额较大的股票
        if 'amount' in latest_data.columns:
            top_stocks = latest_data.nlargest(5, 'amount')
        elif 'turnover' in latest_data.columns:
            top_stocks = latest_data.nlargest(5, 'turnover')
        else:
            # 如果没有这些列，就取前5个
            top_stocks = latest_data.head(5)

        # 生成报告
        report_lines = [
            f"# 📈 A股盘前推荐 - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 今日推荐（基于市场活跃度）",
            ""
        ]

        for idx, row in top_stocks.iterrows():
            stock_code = row.get(stock_code_col, row.get('股票代码', 'N/A'))
            stock_name = row.get(stock_name_col, row.get('股票名称', 'N/A'))

            # 动态获取可用的指标
            metrics = []
            if 'close' in row:
                metrics.append(f"收盘: {row['close']:.2f}")
            if 'change_pct' in row:
                metrics.append(f"涨跌: {row['change_pct']:.2f}%")

            report_lines.append(f"### {stock_code} {stock_name}")
            report_lines.append(f"- {', '.join(metrics)}")
            report_lines.append("")

        report_lines.extend([
            "---",
            f"⚠️ **风险提示**",
            "- 本推荐基于历史数据分析，不构成投资建议",
            "- 请结合个人风险承受能力谨慎决策",
            "- 实盘操作需要考虑交易成本和流动性",
            "",
            f"*数据日期: {latest_date.strftime('%Y-%m-%d') if hasattr(latest_date, 'strftime') else latest_date}*"
        ])

        return '\n'.join(report_lines)

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

        # 发送推送
        import requests
        response = requests.post(
            webhook_url,
            json={"content": report},
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
    logger.info("盘前推送任务开始")
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
        report = generate_push_report()

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
