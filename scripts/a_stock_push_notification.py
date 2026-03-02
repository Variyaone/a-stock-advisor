#!/usr/bin/env python3
"""
A股推送通知脚本 - 测试读取selection_result.json
用于验证选股数据保存是否正确
"""
import json
from pathlib import Path
from datetime import datetime
import sys

def read_selection_result():
    """
    读取选股结果JSON文件

    返回:
        success: 是否成功读取
        message: 消息内容
    """
    print("="*80)
    print("A股推送通知测试")
    print("="*80)

    # 项目路径
    PROJECT_DIR = Path(__file__).parent.parent
    DATA_DIR = PROJECT_DIR / 'data'
    SELECTION_FILE = DATA_DIR / 'selection_result.json'

    # 检查文件是否存在
    print(f"\n[检查] 读取选股数据: {SELECTION_FILE}")
    if not SELECTION_FILE.exists():
        print("✗ 错误: 找不到选股数据文件")
        print("\n消息: 暂无选股数据")
        return False, {"status": "error", "message": "暂无选股数据", "stocks": []}

    # 读取数据
    try:
        with open(SELECTION_FILE, 'r', encoding='utf-8') as f:
            selection_result = json.load(f)
        print("✓ 成功读取选股数据")
    except json.JSONDecodeError as e:
        print(f"✗ 错误: JSON解析失败 - {e}")
        return False, {"status": "error", "message": "选股数据格式错误", "stocks": []}

    # 验证数据格式
    required_fields = ['selected_stocks', 'portfolio_config', 'timestamp']
    for field in required_fields:
        if field not in selection_result:
            print(f"✗ 错误: 缺少必需字段 - {field}")
            return False, {"status": "error", "message": "选股数据不完整", "stocks": []}

    selected_stocks = selection_result['selected_stocks']
    portfolio_config = selection_result['portfolio_config']
    timestamp = selection_result['timestamp']

    # 检查股票列表
    if not selected_stocks or len(selected_stocks) == 0:
        print("⚠️ 警告: 选股列表为空")
        return False, {"status": "warning", "message": "暂无选股数据", "stocks": []}

    print(f"\n选股时间: {timestamp}")
    print(f"选股数量: {len(selected_stocks)}")
    print(f"数据月份: {selection_result.get('data_month', '未知')}")

    # 生成推送消息
    print("\n[生成推送消息]")

    message_lines = [
        f"📊 A股每日选股报告",
        f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"基于 {len(portfolio_config.get('factor_weights', {}))} 个因子，",
        f"采用 {portfolio_config.get('weighting_method', 'ic_weighted')} 加权方式",
        f"",
        f"🎯 今日选股组合（Top {portfolio_config.get('n', 10)}）:",
        f""
    ]

    for stock in selected_stocks[:10]:
        message_lines.append(
            f"{stock['rank']}. {stock['stock_name']} ({stock['stock_code']}) - "
            f"得分: {stock['score']:.2f}"
        )

    message_lines.append("")
    message_lines.append("📝 风险提示: 策略基于历史回测，市场有风险，投资需谨慎")

    message = "\n".join(message_lines)

    # 显示消息预览
    print("\n推送消息预览:")
    print("-"*80)
    print(message)
    print("-"*80)

    # 返回成功状态
    print("\n✓ 推送消息生成成功")
    return True, {
        "status": "success",
        "message": message,
        "stocks": selected_stocks,
        "timestamp": timestamp
    }


def main():
    """主程序"""
    success, result = read_selection_result()

    if success:
        print("\n✓ 推送脚本测试完成")
        print("✓ 能够正常读取选股数据")
        return 0
    else:
        print("\n✗ 推送脚本测试失败")
        print(f"  状态: {result.get('status', 'unknown')}")
        print(f"  消息: {result.get('message', '未知错误')}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
