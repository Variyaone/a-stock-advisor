#!/usr/bin/env python3
"""
A股盘前推送守护进程
功能：每分钟检查时间，在8:00±5分钟内触发推送
解决：macOS cron权限问题导致任务不执行的bug
"""

import sys
import os
import time
from datetime import datetime, timedelta
import logging
import subprocess

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/variya/.openclaw/workspace/projects/a-stock-advisor/logs/morning_push_daemon.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 推送记录文件，防止重复推送
PUSH_RECORD_FILE = '/Users/variya/.openclaw/workspace/projects/a-stock-advisor/logs/last_push_record.json'

def has_pushed_today():
    """检查今天是否已推送"""
    import json
    today = datetime.now().strftime('%Y-%m-%d')
    
    if os.path.exists(PUSH_RECORD_FILE):
        try:
            with open(PUSH_RECORD_FILE, 'r') as f:
                record = json.load(f)
                return record.get('date') == today
        except:
            pass
    return False

def mark_pushed_today():
    """标记今天已推送"""
    import json
    today = datetime.now().strftime('%Y-%m-%d')
    
    os.makedirs(os.path.dirname(PUSH_RECORD_FILE), exist_ok=True)
    with open(PUSH_RECORD_FILE, 'w') as f:
        json.dump({'date': today, 'timestamp': datetime.now().isoformat()}, f)

def run_push():
    """执行推送脚本"""
    try:
        script_path = '/Users/variya/.openclaw/workspace/projects/a-stock-advisor/scripts/paper_trading_push.py'
        
        logger.info("触发盘前推送...")
        result = subprocess.run(
            ['/opt/homebrew/bin/python3', script_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            logger.info("✅ 推送成功")
            mark_pushed_today()
            return True
        else:
            logger.error(f"推送失败: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"执行推送异常: {e}", exc_info=True)
        return False

def should_trigger():
    """检查是否应该触发推送"""
    now = datetime.now()
    
    # 只在工作日运行（周一到周五）
    if now.weekday() >= 5:
        return False
    
    # 在8:00±5分钟内触发
    target_time = now.replace(hour=8, minute=0, second=0, microsecond=0)
    delta = abs((now - target_time).total_seconds())
    
    return delta <= 300  # 5分钟窗口

def main():
    """主循环"""
    logger.info("="*60)
    logger.info("盘前推送守护进程启动")
    logger.info("触发窗口: 工作日 7:55-8:05")
    logger.info("="*60)
    
    check_count = 0
    
    while True:
        try:
            check_count += 1
            
            # 每10秒检查一次
            time.sleep(10)
            
            # 检查是否应该触发
            if should_trigger() and not has_pushed_today():
                logger.info(f"⏰ 触发条件满足（第{check_count}次检查）")
                run_push()
            
            # 每小时打印一次状态
            if check_count % 360 == 0:
                now = datetime.now()
                logger.info(f"状态检查: {now.strftime('%Y-%m-%d %H:%M:%S')} - 已推送: {has_pushed_today()}")
                check_count = 0
                
        except KeyboardInterrupt:
            logger.info("收到退出信号")
            break
        except Exception as e:
            logger.error(f"主循环异常: {e}", exc_info=True)
            time.sleep(60)  # 异常后等待1分钟
    
    logger.info("守护进程退出")

if __name__ == "__main__":
    main()
