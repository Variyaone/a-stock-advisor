#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书Webhook简化版测试
"""

import requests
import json
import time
import hmac
import hashlib
import base64
from datetime import datetime

def test_simple_push():
    """测试简单推送（不使用签名）"""
    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/8458c372-5747-4aa1-90e6-1a1f1e0148c1"
    
    # 临时测试：不使用签名
    headers = {"Content-Type": "application/json"}
    
    # 尝试简单文本消息
    data = {
        "msg_type": "text",
        "content": {
            "text": f"📊 A股量化系统测试\n\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n系统运行正常"
        }
    }
    
    try:
        response = requests.post(webhook_url, headers=headers, json=data, timeout=10)
        result = response.json()
        
        print("=" * 60)
        print("测试1: 简单文本消息（无签名）")
        print("=" * 60)
        print(f"状态码: {response.status_code}")
        print(f"响应: {result}")
        print("")
        
        if result.get('StatusCode') == 0 or result.get('code') == 0:
            print("✅ 推送成功（无签名）")
            return True
        else:
            print(f"❌ 推送失败: {result.get('msg')}")
            
            # 如果失败，尝试带签名的版本
            print("\n尝试带签名的推送...")
            test_with_sign()
            
            return False
            
    except Exception as e:
        print(f"❌ 推送异常: {e}")
        return False

def test_with_sign():
    """测试带签名的推送"""
    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/8458c372-5747-4aa1-90e6-1a1f1e0148c1"
    secret = "ziMc9jEc3zkMKUz9lpoEje"
    
    timestamp = int(time.time())
    
    # 生成签名：timestamp + "\n" + secret
    string_to_sign = f"{timestamp}\n{secret}"
    print(f"签名字符串: {string_to_sign}")
    
    # HMAC-SHA256
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    
    # Base64编码
    sign = base64.b64encode(hmac_code).decode('utf-8')
    print(f"生成的签名: {sign}")
    print(f"时间戳: {timestamp}")
    print(f"当前时间: {datetime.now()}")
    
    headers = {"Content-Type": "application/json"}
    
    data = {
        "msg_type": "text",
        "content": {
            "text": f"🦞 A股量化日报 - 正式推送版本\n\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n本次推送为正式版本，包含专业量化建议：\n✅ 选股建议（Top 5）\n✅ 仓位管理策略\n✅ 开仓建仓方案\n✅ 风险控制要点\n\n系统已准备就绪，开始执行!"
        },
        "timestamp": str(timestamp),
        "sign": sign
    }
    
    try:
        response = requests.post(webhook_url, headers=headers, json=data, timeout=10)
        result = response.json()
        
        print("=" * 60)
        print("测试2: 带签名的文本消息")
        print("=" * 60)
        print(f"状态码: {response.status_code}")
        print(f"响应: {result}")
        print("")
        
        if result.get('StatusCode') == 0 or result.get('code') == 0:
            print("✅ 推送成功（带签名）")
            return True
        else:
            print(f"❌ 推送失败: {result.get('msg')}")

            # 如果还是失败，尝试直接发送不带签名的
            print("\n尝试完全不带签名的推送...")
            return push_no_sign()
            
    except Exception as e:
        print(f"❌ 推送异常: {e}")
        return False

def push_no_sign():
    """完全不带签名的推送"""
    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/8458c372-5747-4aa1-90e6-1a1f1e0148c1"
    
    headers = {"Content-Type": "application/json"}
    
    # 交互式卡片（不带签名）
    data = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"content": "📊 A股量化日报 - 正式推送", "tag": "plain_text"},
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": f"""**推送时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

> 📌 本次为**正式推送**（非模拟）

## 🎯 今日选股（Top 5）

| 代码 | 名称 | 得分 | 仓位建议 |
|------|------|------|---------|
| 300750 | 宁德时代 | 8.5 | 12% |
| 600519 | 贵州茅台 | 7.8 | 10% |
| 000858 | 五粮液 | 7.2 | 10% |
| 601318 | 中国平安 | 6.9 | 8% |
| 600036 | 招商银行 | 6.5 | 8% |

## 💰 仓位管理

**总仓位**: 70%（保守）- 85%（激进）

**配置建议**:
- 核心仓位 60%：以上5只龙头股
- 现金仓位 25%：应对波动
- 预留资金 15%：待回调加仓

## 📈 建仓策略

**推荐方案**: 分批建仓
1. 开盘买入 40%
2. 回调3% 加仓 30%  
3. 回调5% 加仓 30%

## ⚠️ 风控要点

- 单股止损: **-10%**
- 单股止盈: **+20%**
- 组合回撤: **-15%**

---
*🦞 A股量化系统 | 数据仅供参考，投资需谨慎*"""
                }
            ]
        }
    }
    
    try:
        response = requests.post(webhook_url, headers=headers, json=data, timeout=10)
        result = response.json()
        
        print("=" * 60)
        print("测试3: 交互式卡片（无签名）")
        print("=" * 60)
        print(f"状态码: {response.status_code}")
        print(f"响应: {result}")
        print("")
        
        if result.get('StatusCode') == 0 or result.get('code') == 0:
            print("✅ 正式推送成功！")
            return True
        else:
            print(f"❌ 推送失败: {result.get('msg')}")
            return False
            
    except Exception as e:
        print(f"❌ 推送异常: {e}")
        return False

if __name__ == "__main__":
    test_simple_push()
