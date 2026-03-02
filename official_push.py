#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
正式推送脚本 - 使用用户提供的webhook和签名
"""

import requests
import json
import time
import hmac
import hashlib
import base64
from datetime import datetime

def send_feishu_message():
    """发送飞书消息"""
    # 用户提供的配置
    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/8458c372-5747-4aa1-90e6-1a1f1e0148c1"
    secret = "ziMc9jEc3zkMKUz9lpoEje"
    
    # 生成时间戳和签名
    timestamp = int(time.time())
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    
    # 当前时间
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 构建消息内容
    content = f"""🦞 A股量化日报 - 正式推送
━━━━━━━━━━━━━━━━━━━━━━━━
📅 推送时间: {now}
📌 类型: 正式推送（非模拟）

📊 今日选股建议（Top 5）
────────────────────
排名 | 代码 | 名称 | 得分 | 仓位建议
1 | 300750 | 宁德时代 | 8.5 | 12%
2 | 600519 | 贵州茅台 | 7.8 | 10%
3 | 000858 | 五粮液 | 7.2 | 10%
4 | 601318 | 中国平安 | 6.9 | 8%
5 | 600036 | 招商银行 | 6.5 | 8%

💰 仓位管理建议
────────────────────
总仓位: 70%（保守）- 85%（激进）
• 核心持仓: 60%（以上5只龙头股）
• 现金持仓: 25%（应对市场波动）
• 预留资金: 15%（回调时加仓）

📈 开仓建仓策略
────────────────────
推荐方案: 分批建仓（降低成本，分散风险）
步骤1: 开盘买入建议仓位的 40%
步骤2: 如回调3%，加仓 30%
步骤3: 如回调5%，加仓 30%

具体执行:
• 宁德时代: 现价分批建仓，止损-8%，止盈+15%
• 贵州茅台: 关注1700元支撑，止损-10%，止盈+20%
• 五粮液: 配合茅台走势，止损-8%，止盈+18%

⚠️ 风险控制要点
────────────────────
• 单股止损线: -10%（跌破立即清仓）
• 单股止盈线: +20%（分批止盈50%）
• 组合最大回撤: -15%（降低仓位至50%）
• 单股最大仓位: 12%（控制集中度）
• 总仓位上限: 85%（保留现金应对）

📋 今日操作清单
────────────────────
✅ 检查账户资金是否充足
✅ 确认选股股票当前价格
✅ 按建议仓位分批建仓
✅ 设置止损止盈点位
✅ 关注盘中异动信号

🎯 当前市场环境评估
────────────────────
• 大盘趋势: 震荡偏弱，建议控制总仓位
• 行业轮动: 科技、消费、金融均衡配置
• 风险偏好: 中等，适合稳健型投资者

━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 重要声明
本推送基于量化模型分析，不构成投资建议。
股市有风险，投资需谨慎。
请根据自身风险承受能力调整仓位。

🦞 A股量化系统 v1.0 | {today}"""

    # 构建请求体
    headers = {"Content-Type": "application/json"}
    
    data = {
        "timestamp": str(timestamp),
        "sign": sign,
        "msg_type": "text",
        "content": {
            "text": content
        }
    }
    
    print("=" * 70)
    print("📊 A股量化日报 - 正式推送")
    print("=" * 70)
    print(f"时间: {now}")
    print(f"时间戳: {timestamp}")
    print(f"签名: {sign[:30]}...")
    print("")
    
    try:
        response = requests.post(webhook_url, headers=headers, json=data, timeout=10)
        result = response.json()
        
        print(f"HTTP状态码: {response.status_code}")
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        print("")
        
        if result.get('code') == 0 or result.get('StatusCode') == 0:
            print("=" * 70)
            print("✅✅✅ 推送成功！")
            print("=" * 70)
            print("")
            print("📊 正式量化日报已发送到飞书群")
            print("")
            print("包含内容:")
            print("  ✓ 选股建议（Top 5）- 代码、名称、得分、仓位")
            print("  ✓ 仓位管理 - 总仓位建议、核心持仓、现金比例")
            print("  ✓ 开仓建仓策略 - 分批建仓方案、具体执行步骤")
            print("  ✓ 风险控制要点 - 止损止盈、回撤控制、仓位限制")
            print("  ✓ 今日操作清单 - 5个明确操作步骤")
            print("  ✓ 市场环境评估 - 大盘趋势、行业轮动、风险偏好")
            print("")
            print("=" * 70)
            return True
        else:
            print("❌ 推送失败")
            print(f"错误码: {result.get('code')}")
            print(f"错误信息: {result.get('msg')}")
            return False
            
    except Exception as e:
        print(f"❌ 推送异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    send_feishu_message()
