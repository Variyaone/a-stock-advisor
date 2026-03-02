#!/usr/bin/env python3
"""
数据更新脚本V2 - 修复版本
任务：验证数据状态，确保数据可用
执行时机：每日开盘前（7:00）和收盘后（16:00）
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'code'))

from datetime import datetime
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/data_update_v2.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """主函数：执行数据验证"""
    logger.info("="*60)
    logger.info("数据验证任务开始")
    logger.info("="*60)

    try:
        # 导入数据管道V3
        from data_pipeline_v3 import DataPipelineV3

        logger.info("初始化数据管道...")
        pipeline = DataPipelineV3()

        # 检查数据状态
        logger.info("正在检查数据状态...")
        success = pipeline.update_all_data()

        if success:
            logger.info("✓ 数据状态检查通过")

            # 记录更新时间
            with open('logs/last_data_check.txt', 'w') as f:
                f.write(datetime.now().isoformat())
        else:
            logger.error("✗ 数据检查失败")
            return 1

        # 数据质量检查
        logger.info("执行数据质量检查...")
        if pipeline.validate_data():
            logger.info("✓ 数据质量检查通过")
        else:
            logger.warning("⚠️ 数据质量检查发现问题")

        logger.info("="*60)
        logger.info("数据验证任务完成")
        logger.info("="*60)
        return 0

    except Exception as e:
        logger.error(f"❌ 数据验证异常: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
