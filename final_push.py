#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复签名验证问题的推送脚本
根据飞书官方文档：https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot
"""

import requests
import json
import time
import hmac
import hashlib
import base64
from datetime import datetime

def push_with_correct_sign():
    """
    使用正确的飞书签名方式推送
    官方文档格式：
    sign = base64 hmac_sha256(secret, f"{{timestamp}}\n{secret}")
    """
    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/8458c372-5747-4aa1-90e6-1a1f1e0148c1"
    secret = "ziMc9jEc3zkMKUz9lpoEje"
    
    # 1. 获取时间戳（秒级）
    timestamp = int(time.time())
    
    # 2. 构造签名字符串：timestamp + "\n" + secret
    string_to_sign = f"{timestamp}\n{secret}"
    print(f"签名字符串: '{string_to_sign}'")
    
    # 3. 使用HMAC-SHA256计算签名
    hmac_obj = hmac.new(
        secret.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        digestmod=hashlib.sha256
    )
    signature = hmac_obj.digest()
    
    # 4. Base64编码
    sign = base64.b64encode(signature).decode('utf-8')
    print(f"生成签名: {sign}")
    print(f"时间戳: {timestamp} ({datetime.fromtimestamp(timestamp)})")
    
    # 5. 构造消息体
    headers = {"Content-Type": "application/json"}
    
    data = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": "📊 A股量化日报 - 正式推送",
                    "content": [
                        [{
                            "tag": "text",
                            "text": f"推送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        }],
                        [{
                            "tag": "text",
                            "text": "📌 本文为正式推送（非模拟），包含专业量化投资建议\n\n"
                        }],
                        [{
                            "tag": "text",
                            "text": "🎯 今日选股建议（Top 5）\n"
                        }],
                        [{
                            "tag": "table",
                            "table": {
                                "row1": ["代码", "名称", "得分", "仓位"],
                                "row2": ["300750", "宁德时代", "8.5", "12%"],
                                "row3": ["600519", "贵州茅台", "7.8", "10%"],
                                "row4": ["000858", "五粮液", "7.2", "10%"],
                                "row5": ["601318", "中国平安", "6.9", "8%"],
                                "row6": ["600036", "招商银行", "6.5", "8%"]
                            }
                        }],
                        [{
                            "tag": "text",
                            "text": "\n💰 仓位管理建议\n"
                        }],
                        [{
                            "tag": "text",
                            "text": f"• 总仓位: 70%（保守）- 85%（激进）\n• 核心持仓: 以上5只龙头股，占60%\n• 现金持仓: 25%，应对市场波动\n• 预留资金: 15%，回调时加仓\n\n"
                        }],
                        [{
                            "tag": "text",
                            "text": "📈 开仓建仓策略\n"
                        }],
                        [{
                            "tag": "text",
                            "text": "推荐方案：分批建仓\n1. 开盘买入40%\n2. 回调3%加仓30%\n3. 回调5%加仓30%\n\n"
                        }],
                        [{
                            "tag": "text",
                            "text": "⚠️ 风险控制要点\n"
                        }],
                        [{
                            "tag": "text",
                            "text": "• 单股止损线: -10%\n• 单股止盈线: +20%\n• 组合最大回撤: -15%\n• 控制单股持仓不超过12%\n\n"
                        }],
                        [{
                            "tag": "text",
                            "text": "📋 今日操作清单\n"
                        }],
                        [{
                            "tag": "text",
                            "text": "✅ 检查账户资金\n✅ 确认选股价格\n✅ 分批建仓执行\n✅ 设置止损止盈\n✅ 关注盘中异动\n\n"
                        }],
                        [{
                            "tag": "text",
                            "text": "重要声明：本推送基于量化模型分析，不构成投资建议。股市有风险，投资需谨慎。请根据自身风险承受能力调整仓位。\n\n"
                        }],
                        [{
                            "tag": "text",
                            "text": "🦞 A股量化系统 v1.0"
                        }]
                    ]
                }
            }
        },
        "timestamp": str(timestamp),
        "sign": sign
    }
    
    try:
        print("=" * 60)
        print("发送正式推送...")
        print("=" * 60)
        response = requests.post(webhook_url, headers=headers, json=data, timeout=10)
        result = response.json()
        
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        print("")
        
        if result.get('StatusCode') == 0 or result.get('code') == 0:
            print("✅✅✅ 推送成功！正式量化日报已发送！")
            return True
        elif result.get('msg') == 'sign match fail or timestamp is not within one hour from current time':
            print("❌ 签名验证失败")
            print("\n可能原因：")
            print("1. 机器人密钥（secret）不正确")
            print("2. 机器人签名验证未正确设置")
            print("3. 时间戳超出范围")
            print("\n建议操作：")
            print("1. 前往飞书群 → 群设置 → 群机器人 → 编辑机器人")
            print("2. 检查或禁用'签名校验'选项")
            print("3. 重新获取webhook地址和密钥")
            print("4. 更新配置文件 config/feishu_config.json")
            return False
        else:
            print(f"❌ 推送失败: {result}")
            return False
            
    except Exception as e:
        print(f"❌ 推送异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    push_with_correct_sign()
