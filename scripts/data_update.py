#!/usr/bin/env python3
"""
数据更新脚本
任务：从数据源获取最新的市场数据
执行时机：每日开盘前（7:00）和收盘后（16:00）
依赖：data_pipeline.py
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
        logging.FileHandler('../logs/data_update.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """主函数：执行数据更新"""
    logger.info("="*60)
    logger.info("数据更新任务开始")
    logger.info("="*60)

    try:
        # 导入数据管道
        from data_pipeline import DataPipeline
        from data_pipeline_v2 import DataPipelineV2

        logger.info("初始化数据管道...")
        pipeline = DataPipelineV2()

        # 更新基础行情数据
        logger.info("正在更新基础行情数据...")
        success = pipeline.update_all_data()

        if success:
            logger.info("✓ 数据更新成功")

            # 记录更新时间
            with open('../logs/last_data_update.txt', 'w') as f:
                f.write(datetime.now().isoformat())
        else:
            logger.error("✗ 数据更新失败")
            return 1

        # 数据质量检查
        logger.info("执行数据质量检查...")
        if pipeline.validate_data():
            logger.info("✓ 数据质量检查通过")
        else:
            logger.warning("⚠️ 数据质量检查发现问题")
            # 不失败，但记录警告

        logger.info("="*60)
        logger.info("数据更新任务完成")
        logger.info("="*60)
        return 0

    except Exception as e:
        logger.error(f"❌ 数据更新异常: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
