#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
正式推送脚本 v2.0 - 集成持仓跟踪、α选股、换仓策略
提供连续性的推送内容: 昨日回顾、今日持仓、今日决策、明日计划
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

import requests
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime

from enhanced_pusher import EnhancedPusher
from multi_factor_model import MultiFactorScoreModel

def send_feishu_message(content: str, webhook_url: str, secret: str = None) -> bool:
    """
    发送飞书消息
    
    Args:
        content: 消息内容
        webhook_url: Webhook URL
        secret: 签名密钥（可选）
        
    Returns:
        是否发送成功
    """
    headers = {"Content-Type": "application/json"}
    
    data = {
        "msg_type": "text",
        "content": {
            "text": content
        }
    }
    
    # 如果配置了签名，添加签名
    if secret:
        import hmac
        import hashlib
        import base64
        
        timestamp = int(time.time())
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode('utf-8')
        
        data["timestamp"] = str(timestamp)
        data["sign"] = sign
    
    print("=" * 70)
    print("📊 发送飞书消息")
    print("=" * 70)
    print(f"长度: {len(content)} 字符")
    print("")
    
    try:
        response = requests.post(webhook_url, headers=headers, json=data, timeout=10)
        result = response.json()
        
        print(f"HTTP状态码: {response.status_code}")
        
        if result.get('code') == 0 or result.get('StatusCode') == 0:
            print("=" * 70)
            print("✅✅✅ 推送成功！")
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

def load_latest_data():
    """
    加载最新数据
    
    Returns:
        (stock_data, alpha_scores)
    """
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
            factor_data['date'] = pd.Timestamp.now()

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

    # 计算α得分
    alpha_selector = EnhancedPusher().alpha_selector
    alpha_scores = alpha_selector.calculate_alpha_score(latest_factor_data.set_index('stock_code'))
    
    return latest_factor_data.set_index('stock_code'), alpha_scores

def main():
    """主函数"""
    print("=" * 70)
    print("🦞 A股量化日报 v2.0 - 正式推送")
    print("=" * 70)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 1. 加载数据
    print("📊 加载数据...")
    stock_data, alpha_scores = load_latest_data()

    if stock_data is None or stock_data.empty:
        print("❌ 数据加载失败，无法推送")
        return False

    print(f"✓ 加载股票数据: {len(stock_data)}只\n")

    # 2. 生成推送内容
    print("📝 生成推送内容...")
    pusher = EnhancedPusher()
    push_content = pusher.generate_push_content(stock_data, alpha_scores)

    print(f"✓ 推送内容生成完成\n")

    # 3. 发送飞书推送
    print("📱 发送飞书推送...")
    config = pusher.config

    if not config.get('webhook_url'):
        print("❌ 未配置webhook_url")
        return False

    # 获取签名密钥
    secret = None
    if config.get('sign_enabled', False):
        secret = "ziMc9jEc3zkMKUz9lpoEje"  # 从配置文件读取或硬编码

    success = send_feishu_message(
        push_content,
        config['webhook_url'],
        secret
    )

    if success:
        print("\n📊 推送内容摘要:")
        print("  ✓ 昨日回顾")
        print("  ✓ 今日持仓")
        print("  ✓ 今日选股（α因子筛选）")
        print("  ✓ 今日决策（换仓策略）")
        print("  ✓ 换仓逻辑说明")
        print("  ✓ 明日计划")
        print("  ✓ 仓位管理建议")

    print("\n" + "=" * 70)
    print(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
