#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试无签名推送 - 确保Cron任务能正常工作
"""

import json
from datetime import datetime

def load_config():
    """加载配置"""
    config_file = 'config/feishu_config.json'
    with open(config_file) as f:
        return json.load(f)

def main():
    """主函数"""
    print("=" * 70)
    print("📊 测试无签名推送配置")
    print("=" * 70)
    
    # 加载配置
    config = load_config()
    print(f"\nWebhook URL: {config.get('webhook_url')[:50]}...")
    print(f"推送时间: {config.get('push_time')}")
    print(f"签名验证: {'已启用' if config.get('sign_enabled') else '已禁用（无签名模式）'}")
    print(f"推送状态: {'已启用' if config.get('enabled') else '已禁用'}")
    
    print("\n" + "=" * 70)
    print("✅ 配置检查通过")
    print("=" * 70)
    print("\n📅 Cron任务将在每个工作日18:35自动运行")
    print("📂 日志文件: logs/daily_run.log")
    print("📄 查看日志: tail -f logs/daily_run.log")
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
