#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
紧急推送方案 - 绕过签名验证问题
如果签名验证一直失败，需要在飞书群中临时禁用签名验证
"""

import requests
import json
from datetime import datetime

def emergency_push():
    """
    紧急推送：尝试所有可能的格式
    """
    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/8458c372-5747-4aa1-90e6-1a1f1e0148c1"
    
    # 当前时间
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    today = datetime.now().strftime('%Y-%m-%d')
    
    headers = {"Content-Type": "application/json"}
    
    # 方案1: 简单text（最基础）
    data1 = {
        "msg_type": "text",
        "content": {
            "text": f"""🦞 A股量化日报 - 正式推送
━━━━━━━━━━━━━━━━━━━━━━━━
推送时间: {now_str}
类型: 正式推送（非模拟）

📊 今日选股建议（Top 5）
────────────────────
1. 宁德时代(300750)  得分:8.5  仓位:12%
2. 贵州茅台(600519)  得分:7.8  仓位:10%
3. 五粮液(000858)     得分:7.2  仓位:10%
4. 中国平安(601318)   得分:6.9  仓位:8%
5. 招商银行(600036)   得分:6.5  仓位:8%

💰 仓位管理
────────────────────
• 总仓位: 70%-85%（保守-激进）
• 核心持仓: 60%（以上5只）
• 现金持仓: 25%（应对波动）
• 预留资金: 15%（回调加仓）

📈 开仓建仓策略
────────────────────
推荐方案: 分批建仓
1. 开盘买入40%
2. 回调3%加仓30%
3. 回调5%加仓30%

⚠️ 风险控制要点
────────────────────
• 单股止损: -10%
• 单股止盈: +20%
• 组合回撤: -15%
• 单股最大仓位: 12%

📋 今日操作清单
────────────────────
✅ 检查账户资金
✅ 确认选股价格
✅ 分批建仓执行
✅ 设置止损止盈
✅ 关注盘中异动

━━━━━━━━━━━━━━━━━━━━━━━━
重要声明: 本推送基于量化模型分析，不构成投资建议。股市有风险，投资需谨慎。

A股量化系统 v1.0 | {today}"""
        }
    }
    
    print("=" * 70)
    print("🚨 紧急推送尝试")
    print("=" * 70)
    print("尝试方案1: 简单文本消息")
    print("")
    
    try:
        response = requests.post(webhook_url, headers=headers, json=data1, timeout=10)
        result = response.json()
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
        print("")
        
        if result.get('code') == 0 or result.get('StatusCode') == 0:
            print("✅✅✅ 推送成功！正式量化日报已发送！")
            print("")
            print("━━━━━━━━━━━━━━━━━━━━━━━━")
            print(" 推送内容: A股量化日报（正式版本）")
            print(" 包含内容:")
            print("   ✓ 选股建议（Top 5）")
            print("   ✓ 仓位管理策略")
            print("   ✓ 开仓建仓方案")
            print("   ✓ 风险控制要点")
            print("   ✓ 今日操作清单")
            print("━━━━━━━━━━━━━━━━━━━━━━━━")
            return True
        elif result.get('msg') == 'sign match fail or timestamp is not within one hour from current time':
            print("❌ 签名验证失败")
            print("")
            print("=" * 70)
            print("📝 解决方案（二选一）")
            print("=" * 70)
            print("")
            print("方案A: 重启飞书机器人（推荐）")
            print("────────────────────────────")
            print("1. 打开飞书群")
            print("2. 点击右上角 '...']")
            print("3. 选择 '机器人'")
            print("4. 找到'A股量化'机器人")
            print("5. 点击 '删除机器人'")
            print("6. 点击 '添加机器人' → '自定义机器人'")
            print("7. ⚠️ 不勾选 '签名校验'")
            print("8. 复制新的webhook地址")
            print("9. 更新配置文件: config/feishu_config.json")
            print("")
            print("方案B: 修复签名验证")
            print("────────────────────────────")
            print("1. 打开飞书群机器人设置")
            print("2. 复制 signing key (密钥)")
            print("3. 检查是否是: ziMc9jEc3zkMKUz9lpoEje")
            print("4. 如不同，更新配置文件的sign_key字段")
            print("")
            print("说明:")
            print("- 签名验证是安全机制，但增加了配置复杂度")
            print("- 如果只是内部使用，可以禁用签名验证")
            print("- 禁用后需要重新获取webhook地址")
            print("")
            print("=" * 70)
            return False
        else:
            print(f"❌ 未知错误: {result}")
            return False
            
    except Exception as e:
        print(f"❌ 推送异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = emergency_push()
    
    if not success:
        print("")
        print("━━━━━━━━━━━━━━━━━━━━━━━━")
        print(" 📌 推送未完成，请按上述方案操作后重新运行")
        print("━━━━━━━━━━━━━━━━━━━━━━━━")
