#!/usr/bin/env python3
"""
飞书推送模块（支持签名验证）
"""

import requests
import json
import time
import hmac
import hashlib
import base64
from datetime import datetime


class FeishuPusher:
    """飞书推送器（支持签名验证）"""

    def __init__(self, webhook_url=None, secret=None):
        """
        Args:
            webhook_url: 飞书机器人webhook地址
            secret: 签名密钥（如果启用了签名验证）
        """
        self.webhook_url = webhook_url
        self.secret = secret

    def _gen_sign(self, timestamp):
        """
        生成签名（如果配置了secret）

        Args:
            timestamp: 时间戳

        Returns:
            签名字符串
        """
        if not self.secret:
            return None

        # 拼接timestamp和secret
        string_to_sign = f"{timestamp}\n{self.secret}"

        # 使用HMAC-SHA256计算签名
        hmac_code = hmac.new(
            self.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()

        # Base64编码
        sign = base64.b64encode(hmac_code).decode('utf-8')
        return sign

    def send_text(self, text):
        """
        发送文本消息

        Args:
            text: 文本内容
        """
        if not self.webhook_url:
            print("⚠️ 未配置webhook，跳过推送")
            return False

        headers = {"Content-Type": "application/json"}

        # 构建消息体
        data = {
            "msg_type": "text",
            "content": {"text": text}
        }

        # 如果配置了secret，添加签名
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

            if response.status_code == 200:
                result = response.json()
                if result.get('StatusCode') == 0 or result.get('code') == 0:
                    print("✓ 飞书推送成功")
                    return True
                else:
                    print(f"✗ 飞书推送失败: {result.get('msg', '未知错误')}")
                    return False
            else:
                print(f"✗ 飞书推送失败: HTTP {response.status_code}")
                return False

        except Exception as e:
            print(f"✗ 飞书推送异常: {e}")
            return False

    def send_markdown(self, title, content):
        """
        发送Markdown格式消息

        Args:
            title: 标题
            content: Markdown内容
        """
        if not self.webhook_url:
            print("⚠️ 未配置webhook，跳过推送")
            return False

        headers = {"Content-Type": "application/json"}

        # 构建消息体
        data = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"content": title, "tag": "plain_text"},
                    "template": "turquoise"
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": content
                    }
                ]
            }
        }

        # 如果配置了secret，添加签名
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

            if response.status_code == 200:
                result = response.json()
                if result.get('StatusCode') == 0 or result.get('code') == 0:
                    print("✓ 飞书推送成功")
                    return True
                else:
                    print(f"✗ 飞书推送失败: {result.get('msg', '未知错误')}")
                    return False
            else:
                print(f"✗ 飞书推送失败: HTTP {response.status_code}")
                return False

        except Exception as e:
            print(f"✗ 飞书推送异常: {e}")
            return False

    def send_report(self, report_path):
        """
        发送完整报告

        Args:
            report_path: 报告文件路径
        """
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()
        except Exception as e:
            print(f"✗ 读取报告失败: {e}")
            return False

        # 提取标题和内容
        lines = report_content.split('\n')
        title = lines[0].replace('#', '').strip()
        content = '\n'.join(lines[1:])

        # 发送
        return self.send_markdown(title, content)


def main():
    """测试飞书推送"""
    import os
    import sys

    # 从环境变量或配置文件加载
    webhook_url = os.environ.get('FEISHU_WEBHOOK_URL')
    secret = os.environ.get('FEISHU_SECRET')

    # 尝试从配置文件加载
    if not webhook_url:
        config_file = 'config/feishu_config.json'
        if os.path.exists(config_file):
            with open(config_file) as f:
                config = json.load(f)
                webhook_url = config.get('webhook_url')
                secret = config.get('secret')

    if not webhook_url:
        print("⚠️ 请配置webhook_url")
        print("方式1: 设置环境变量 FEISHU_WEBHOOK_URL 和 FEISHU_SECRET")
        print("方式2: 编辑配置文件 config/feishu_config.json")
        return

    pusher = FeishuPusher(webhook_url, secret)

    # 测试推送
    print("=" * 60)
    print("测试飞书推送")
    print("=" * 60)

    success = pusher.send_text(
        "📊 A股量化系统 - 测试消息\n\n"
        "系统已配置成功！\n"
        f"推送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        "签名验证: " + ("已启用" if secret else "未启用")
    )

    if success:
        print("\n✅ 测试成功！")
    else:
        print("\n❌ 测试失败！")
        if not secret:
            print("\n💡 提示: 当前Webhook可能需要签名验证")
            print("请在飞书群设置中查看机器人的签名密钥(secret)")
            print("并更新配置文件: config/feishu_config.json")


if __name__ == "__main__":
    main()
