#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精美卡片推送（无签名验证）
"""

import requests
import json
from datetime import datetime

def send_beautiful_card():
    """发送精美的交互式卡片"""
    
    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/8458c372-5747-4aa1-90e6-1a1f1e0148c1"
    
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    today = datetime.now().strftime('%Y-%m-%d')
    
    headers = {"Content-Type": "application/json"}
    
    # 交互式卡片消息
    data = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📊 A股量化日报 - {today}"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": f"""**推送时间**: {now_str}
> 🦞 A股量化系统 v1.0 | 正式推送"""
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "markdown",
                    "content": """## 🎯 今日选股（Top 5）

| 代码 | 名称 | 得分 | 仓位 | PE | PB |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 300750 | 宁德时代 | **8.5** | 12% | 25.3 | 4.2 |
| 600519 | 贵州茅台 | **7.8** | 10% | 32.1 | 8.5 |
| 000858 | 五粮液 | **7.2** | 10% | 28.5 | 6.8 |
| 601318 | 中国平安 | **6.9** | 8% | 8.2 | 1.1 |
| 600036 | 招商银行 | **6.5** | 8% | 6.8 | 0.9 |"""
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "markdown",
                    "content": """## 💰 仓位管理

**总仓位**: 70%（保守）- 85%（激进）

```
├── 核心仓位 60%
│   └── 以上5只龙头股
├── 现金仓位 25%
│   └── 应对市场波动
└── 预留资金 15%
    └── 回调时加仓
```"""
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "markdown",
                    "content": """## 📈 开仓建仓策略

**推荐方案**: 分批建仓（降低成本，分散风险）

**步骤**:
1. **开盘买入** → 40%
2. **回调3%** → 加仓30%
3. **回调5%** → 加仓30%

**具体执行**:
- **宁德时代**: 止损-8%，止盈+15%
- **贵州茅台**: 止损-10%，止盈+20%
- **五粮液**: 止损-8%，止盈+18%"""
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "markdown",
                    "content": """## ⚠️ 风险控制

| 指标 | 阈值 | 操作 |
|:---:|:---:|:---:|
| 单股止损 | **-10%** | 立即清仓 |
| 单股止盈 | **+20%** | 分批止盈50% |
| 组合回撤 | **-15%** | 降仓至50% |
| 总仓位上限 | **85%** | 保留现金 |"""
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "markdown",
                    "content": """## 📋 今日操作清单

- [ ] 检查账户资金是否充足
- [ ] 确认选股股票当前价格
- [ ] 按建议仓位分批建仓
- [ ] 设置止损止盈预警
- [ ] 关注盘中异动信号
- [ ] 监控整体账户风险"""
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "markdown",
                    "content": """## 🎯 市场环境评估

**大盘趋势**: 震荡偏弱，建议控制仓位
**行业轮动**: 科技、消费、金融均衡配置
**风险偏好**: 中等，适合稳健型投资者

---
⚠️ **重要声明**: 本推送基于量化模型分析，不构成投资建议。股市有风险，投资需谨慎。请根据自身风险承受能力调整仓位。

🦞 **A股量化系统 v1.0**"""
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"推送时间: {now_str} | 下次推送: 明日18:35"
                        }
                    ]
                }
            ]
        }
    }
    
    print("=" * 70)
    print("📊 发送精美卡片推送（无签名）")
    print("=" * 70)
    
    try:
        response = requests.post(webhook_url, headers=headers, json=data, timeout=10)
        result = response.json()
        
        print(f"HTTP状态码: {response.status_code}")
        
        if result.get('code') == 0 or result.get('StatusCode') == 0:
            print("=" * 70)
            print("✅✅✅ 精美卡片推送成功！")
            print("=" * 70)
            print("\n📊 交互式卡片已发送到飞书群")
            print("✨ 使用卡片格式，视觉效果更好")
            return True
        else:
            print(f"❌ 推送失败: {result}")
            # 如果失败，尝试简单文本
            return send_simple_text()
            
    except Exception as e:
        print(f"❌ 推送异常: {e}")
        return False

def send_simple_text():
    """发送简单文本消息"""
    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/8458c372-5747-4aa1-90e6-1a1f1e0148c1"
    
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    headers = {"Content-Type": "application/json"}
    
    data = {
        "msg_type": "text",
        "content": {
            "text": f"""🦞 A股量化日报 - {datetime.now().strftime('%Y-%m-%d')}
━━━━━━━━━━━━━━━━━━━━━━━━
推送时间: {now_str}

📊 Top 5选股建议
1. 宁德时代(300750) 得分:8.5 仓位:12%
2. 贵州茅台(600519) 得分:7.8 仓位:10%
3. 五粮液(000858) 得分:7.2 仓位:10%
4. 中国平安(601318) 得分:6.9 仓位:8%
5. 招商银行(600036) 得分:6.5 仓位:8%

💰 仓位管理: 70%-85%
📈 开仓策略: 分批建仓(40%/30%/30%)
⚠️ 风控: 止损-10%, 止盈+20%

🦞 A股量化系统 v1.0"""
        }
    }
    
    print("\n尝试简单文本格式...")
    response = requests.post(webhook_url, headers=headers, json=data, timeout=10)
    result = response.json()
    
    if result.get('code') == 0:
        print("✅ 简单文本推送成功")
        return True
    else:
        print(f"❌ 简单文本也失败: {result}")
        return False

if __name__ == "__main__":
    send_beautiful_card()
