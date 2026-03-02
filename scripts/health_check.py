#!/usr/bin/env python3
"""
健康检查脚本
任务：检查系统各项指标的健康状态
执行时机：每日凌晨 3:00
检查项：
  - 数据完整性
  - 配置文件有效性
  - 磁盘空间
  - Python环境
  - 外部依赖
"""

import sys
import os
from datetime import datetime
import json
import subprocess
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../logs/health_check.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HealthChecker:
    """系统健康检查器"""

    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.results = {}

    def check_data_integrity(self):
        """检查数据完整性"""
        logger.info("检查数据完整性...")
        data_dir = os.path.join(self.base_dir, 'data')

        checks = {
            'real_stock_data_exists': os.path.exists(os.path.join(data_dir, 'real_stock_data.pkl')),
            'mock_data_exists': os.path.exists(os.path.join(data_dir, 'mock_data.pkl')),
            'metadata_exists': os.path.exists(os.path.join(data_dir, 'real_stock_data_metadata.json')),
        }

        overall = all(checks.values())
        logger.info(f"  数据完整性: {'✓ 通过' if overall else '✗ 失败'}")
        self.results['data_integrity'] = {'status': 'pass' if overall else 'fail', 'details': checks}

        return overall

    def check_config_files(self):
        """检查配置文件有效性"""
        logger.info("检查配置文件...")
        config_dir = os.path.join(self.base_dir, 'config')

        checks = {}
        try:
            with open(os.path.join(config_dir, 'feishu_config.json')) as f:
                config = json.load(f)
                checks['feishu_valid'] = 'webhook_url' in config
        except Exception as e:
            logger.warning(f"  飞书配置检查失败: {e}")
            checks['feishu_valid'] = False

        try:
            with open(os.path.join(config_dir, 'risk_limits.json')) as f:
                config = json.load(f)
                checks['risk_valid'] = isinstance(config, dict)
        except Exception as e:
            logger.warning(f"  风控配置检查失败: {e}")
            checks['risk_valid'] = False

        overall = all(checks.values())
        logger.info(f"  配置文件: {'✓ 通过' if overall else '✗ 失败'}")
        self.results['config_files'] = {'status': 'pass' if overall else 'fail', 'details': checks}

        return overall

    def check_disk_space(self, threshold_gb=5):
        """检查磁盘空间"""
        logger.info("检查磁盘空间...")
        try:
            result = subprocess.run(['df', '-h', self.base_dir], capture_output=True, text=True)
            lines = result.stdout.split('\n')

            if len(lines) >= 2:
                used_percent = int(lines[1].split()[-2].rstrip('%'))
                available_gb = float(lines[1].split()[-3].rstrip('G'))

                logger.info(f"  已用: {used_percent}%")
                logger.info(f"  可用: {available_gb}G")

                overall = available_gb >= threshold_gb
                logger.info(f"  磁盘空间: {'✓ 充足' if overall else '⚠️ 不足'}")
                self.results['disk_space'] = {
                    'status': 'pass' if overall else 'warn',
                    'details': {'used_percent': used_percent, 'available_gb': available_gb}
                }
                return overall
        except Exception as e:
            logger.error(f"  磁盘检查失败: {e}")
            self.results['disk_space'] = {'status': 'error', 'details': str(e)}
            return False

    def check_python_env(self):
        """检查 Python 环境"""
        logger.info("检查 Python 环境...")
        checks = {}

        try:
            import pandas as pd
            checks['pandas'] = True
            logger.info(f"  pandas: {pd.__version__}")
        except ImportError:
            checks['pandas'] = False
            logger.warning("  pandas 未安装")

        try:
            import numpy as np
            checks['numpy'] = True
            logger.info(f"  numpy: {np.__version__}")
        except ImportError:
            checks['numpy'] = False
            logger.warning("  numpy 未安装")

        overall = all(checks.values())
        logger.info(f"  Python 环境: {'✓ 正常' if overall else '⚠️ 缺失依赖'}")
        self.results['python_env'] = {'status': 'pass' if overall else 'warn', 'details': checks}

        return overall

    def check_logs_rotation(self, max_size_mb=100):
        """检查日志轮转"""
        logger.info("检查日志文件大小...")
        log_dir = os.path.join(self.base_dir, 'logs')

        if not os.path.exists(log_dir):
            logger.info("  日志目录不存在")
            return True

        checks = {}
        for filename in os.listdir(log_dir):
            if filename.endswith('.log'):
                filepath = os.path.join(log_dir, filename)
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                checks[filename] = size_mb < max_size_mb
                if size_mb > max_size_mb:
                    logger.warning(f"  {filename}: {size_mb:.2f}MB (超过 {max_size_mb}MB)")

        overall = all(checks.values())
        logger.info(f"  日志轮转: {'✓ 正常' if overall else '⚠️ 需要清理'}")
        self.results['logs_rotation'] = {'status': 'pass' if overall else 'warn', 'details': checks}

        return overall

    def run_all_checks(self):
        """执行所有检查"""
        logger.info("="*60)
        logger.info("系统健康检查开始")
        logger.info("="*60)

        self.check_data_integrity()
        self.check_config_files()
        self.check_disk_space()
        self.check_python_env()
        self.check_logs_rotation()

        # 生成汇总报告
        logger.info("="*60)
        logger.info("健康检查汇总")
        logger.info("="*60)

        summary = {
            'timestamp': datetime.now().isoformat(),
            'checks': self.results,
            'overall_status': 'pass' if all(
                r['status'] in ['pass', 'warn'] for r in self.results.values()
            ) else 'fail'
        }

        # 保存报告
        report_path = os.path.join(self.base_dir, 'logs', 'health_check_report.json')
        with open(report_path, 'w') as f:
            json.dump(summary, f, indent=2)

        # 打印汇总
        status_counts = {}
        for check, result in self.results.items():
            status = result['status']
            status_counts[status] = status_counts.get(status, 0) + 1

        logger.info(f"  通过: {status_counts.get('pass', 0)}")
        logger.info(f"  警告: {status_counts.get('warn', 0)}")
        logger.info(f"  失败: {status_counts.get('fail', 0)}")
        logger.info(f"  总体状态: {'✓ 健康' if summary['overall_status'] == 'pass' else '⚠️ 需要关注'}")

        logger.info(f"  报告已保存: {report_path}")

        # 如果有失败项，返回非零退出码
        return 0 if summary['overall_status'] == 'pass' else 1

def main():
    """主函数"""
    checker = HealthChecker()
    exit_code = checker.run_all_checks()

    if exit_code != 0:
        logger.warning("⚠️ 系统存在问题，请检查日志")
    else:
        logger.info("✅ 系统健康检查通过")

    return exit_code

if __name__ == "__main__":
    sys.exit(main())
