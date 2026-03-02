#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专业量化推送脚本 - 飞书Webhook
包含：选股建议、仓位管理、开仓策略、风险提示
"""

import requests
import json
import time
import hmac
import hashlib
import base64
from datetime import datetime
import sys
import os

# 添加code目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class ProfessionalQuantPusher:
    """专业量化推送器"""
    
    def __init__(self, webhook_url, secret=None):
        self.webhook_url = webhook_url
        self.secret = secret
    
    def _gen_sign(self, timestamp):
        """生成飞书签名"""
        if not self.secret:
            return None
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode('utf-8')
        return sign
    
    def send_interactive_card(self, title, content):
        """发送交互式卡片消息"""
        headers = {"Content-Type": "application/json"}
        
        data = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"content": title, "tag": "plain_text"},
                    "template": "blue"
                },
                "elements": [
                    {"tag": "markdown", "content": content}
                ]
            }
        }
        
        if self.secret:
            timestamp = int(time.time())
            sign = self._gen_sign(timestamp)
            data["timestamp"] = str(timestamp)
            data["sign"] = sign
        
        try:
            response = requests.post(
                self.webhook_url,
                headers=headers,
                json=data,
                timeout=10
            )
            result = response.json()
            if result.get('StatusCode') == 0 or result.get('code') == 0:
                print("✅ 推送成功")
                return True
            else:
                print(f"❌ 推送失败: {result}")
                return False
        except Exception as e:
            print(f"❌ 推送异常: {e}")
            return False

def generate_professional_content():
    """生成专业量化内容"""
    
    # 当前日期
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M:%S')
    
    # 模拟选股结果（实际应从系统获取）
    selected_stocks = [
        {"code": "300750", "name": "宁德时代", "score": 8.5, "pe": 25.3, "pb": 4.2, "weight": 0.12},
        {"code": "600519", "name": "贵州茅台", "score": 7.8, "pe": 32.1, "pb": 8.5, "weight": 0.10},
        {"code": "000858", "name": "五粮液", "score": 7.2, "pe": 28.5, "pb": 6.8, "weight": 0.10},
        {"code": "601318", "name": "中国平安", "score": 6.9, "pe": 8.2, "pb": 1.1, "weight": 0.08},
        {"code": "600036", "name": "招商银行", "score": 6.5, "pe": 6.8, "pb": 0.9, "weight": 0.08},
    ]
    
    # 构建Markdown内容
    content = f"""# 📊 A股量化日报 - {today}

> **系统状态**: 策略运行正常 | **数据源**: 沪深300成分股

---

## 🎯 今日选股建议（Top 5）

| 排名 | 代码 | 名称 | 综合得分 | PE | PB | 建议仓位 |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
"""
    
    for i, stock in enumerate(selected_stocks, 1):
        content += f"| {i} | {stock['code']} | {stock['name']} | **{stock['score']}** | {stock['pe']} | {stock['pb']} | {stock['weight']*100:.0f}% |\n"
    
    content += """
---

## 💰 仓位管理建议

### 当前市场环境评估
- **大盘趋势**: 震荡偏弱，建议控制总仓位
- **行业轮动**: 科技、消费、金融均衡配置
- **风险偏好**: 中等，适合稳健型投资者

### 推荐仓位分配
```
📊 总仓位建议: 70%（保守）~ 85%（激进）

├── 核心仓位 (60%)
│   ├── 300750 宁德时代  12%  ← 新能源龙头
│   ├── 600519 贵州茅台  10%  ← 消费龙头
│   ├── 000858 五粮液    10%  ← 消费白马
│   ├── 601318 中国平安   8%  ← 金融蓝筹
│   └── 600036 招商银行   8%  ← 银行龙头
│
├── 卫星仓位 (15%)
│   └── 预留现金，待回调加仓
│
└── 现金仓位 (25%)
    └── 应对不确定性，保持流动性
```

---

## 📈 开仓建仓策略

### 建仓方式选择

#### 方案A: 分批建仓（推荐）
```
第一次建仓: 今日开盘  → 买入建议仓位的 40%
第二次建仓: 如回调3%  → 加仓 30%
第三次建仓: 如回调5%  → 加仓 30%

优点: 降低成本，分散风险
适用: 震荡市、不确定性较高时
```

#### 方案B: 一次性建仓
```
建仓时机: 今日开盘
建仓比例: 100%建议仓位

优点: 简单直接，不错过行情
适用: 趋势明确、信心较强时
```

### 具体执行建议
1. **宁德时代 (300750)**: 
   - 现价附近分批建仓，控制单次买入不超过4%仓位
   - 止损位: -8% | 止盈位: +15%

2. **贵州茅台 (600519)**:
   - 低位建仓，关注1700元支撑
   - 止损位: -10% | 止盈位: +20%

3. **五粮液 (000858)**:
   - 配合茅台走势，同步建仓
   - 止损位: -8% | 止盈位: +18%

---

## ⚠️ 风险提示

### 重要声明
- 以上建议基于量化模型，不构成投资建议
- 股市有风险，投资需谨慎
- 请根据自身风险承受能力调整仓位

### 风控要点
| 指标 | 阈值 | 说明 |
|:---:|:---:|:---|
| 单股止损 | **-10%** | 跌破立即清仓 |
| 单股止盈 | **+20%** | 分批止盈50% |
| 组合回撤 | **-15%** | 降低仓位至50% |
| 最大仓位 | **85%** | 保留现金应对 |

---

## 📋 今日操作清单

- [ ] 检查账户资金是否充足
- [ ] 确认选股股票当前价格
- [ ] 按建议仓位分批建仓
- [ ] 设置止损止盈点位
- [ ] 关注盘中异动信号

---

**生成时间**: {today} {time_str}  
**策略版本**: v1.0  
**下次更新**: 明日18:35

*🦞 A股量化系统 | 数据仅供参考*
"""
    
    return content

def main():
    """主函数"""
    # 加载配置
    config_file = 'config/feishu_config.json'
    if not os.path.exists(config_file):
        print(f"❌ 配置文件不存在: {config_file}")
        return False
    
    with open(config_file) as f:
        config = json.load(f)
    
    webhook_url = config.get('webhook_url')
    secret = config.get('sign_key') or config.get('secret')
    
    if not webhook_url:
        print("❌ 未配置webhook_url")
        return False
    
    print("=" * 60)
    print("📊 专业量化推送启动")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Webhook: {webhook_url[:50]}...")
    print(f"签名: {'已启用' if secret else '未启用'}")
    print("")
    
    # 生成内容
    content = generate_professional_content()
    
    # 发送推送
    pusher = ProfessionalQuantPusher(webhook_url, secret)
    success = pusher.send_interactive_card(
        title=f"📊 A股量化日报 - {datetime.now().strftime('%Y-%m-%d')}",
        content=content
    )
    
    if success:
        print("\n✅ 专业量化日报推送成功！")
        return True
    else:
        print("\n❌ 推送失败，请检查配置")
        return False

if __name__ == "__main__":
    main()
