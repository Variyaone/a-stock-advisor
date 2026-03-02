#!/usr/bin/env python3
"""
监控数据收集脚本
任务：收集系统性能指标和运行状态
执行时机：每小时（整点）
收集项：
  - 系统资源使用（CPU、内存）
  - 任务执行状态
  - 选股结果统计
  - 错误日志统计
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'code'))

from datetime import datetime
import json
import psutil
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../logs/monitor_collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MonitorCollector:
    """监控数据收集器"""

    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data = {}

    def collect_system_metrics(self):
        """收集系统资源指标"""
        logger.info("收集系统资源指标...")

        self.data['cpu'] = {
            'percent': psutil.cpu_percent(interval=1),
            'count': psutil.cpu_count(),
            'count_logical': psutil.cpu_count(logical=True)
        }

        memory = psutil.virtual_memory()
        self.data['memory'] = {
            'total_gb': memory.total / (1024**3),
            'available_gb': memory.available / (1024**3),
            'percent': memory.percent,
            'used_gb': memory.used / (1024**3)
        }

        disk = psutil.disk_usage(self.base_dir)
        self.data['disk'] = {
            'total_gb': disk.total / (1024**3),
            'used_gb': disk.used / (1024**3),
            'free_gb': disk.free / (1024**3),
            'percent': disk.percent
        }

        logger.info(f"  CPU: {self.data['cpu']['percent']:.1f}%")
        logger.info(f"  内存: {self.data['memory']['percent']:.1f}%")
        logger.info(f"  磁盘: {self.data['disk']['percent']:.1f}%")

    def collect_task_status(self):
        """收集任务执行状态"""
        logger.info("收集任务执行状态...")

        # 检查最后一次数据更新
        data_update_file = os.path.join(self.base_dir, 'logs', 'last_data_update.txt')
        if os.path.exists(data_update_file):
            with open(data_update_file, 'r') as f:
                last_update = f.read()
            self.data['last_data_update'] = last_update
            logger.info(f"  最后数据更新: {last_update}")
        else:
            self.data['last_data_update'] = None
            logger.info("  最后数据更新: 未记录")

        # 检查最后一次推送
        push_log = os.path.join(self.base_dir, 'logs', 'daily_run.log')
        if os.path.exists(push_log):
            # 获取最后修改时间
            last_push_mtime = os.path.getmtime(push_log)
            last_push = datetime.fromtimestamp(last_push_mtime).isoformat()
            self.data['last_push'] = last_push
            logger.info(f"  最后推送: {last_push}")
        else:
            self.data['last_push'] = None
            logger.info("  最后推送: 未找到日志")

        # 检查错误日志
        error_logs = {}
        log_dir = os.path.join(self.base_dir, 'logs')
        for log_file in Path(log_dir).glob('*.log'):
            try:
                # 简单统计 ERROR 字符串出现次数
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    error_count = sum(1 for line in f if 'ERROR' in line or 'error' in line)
                if error_count > 0:
                    error_logs[log_file.name] = error_count
            except Exception as e:
                logger.warning(f"  无法读取日志文件 {log_file.name}: {e}")

        self.data['error_logs'] = error_logs
        if error_logs:
            logger.info(f"  错误日志: {len(error_logs)} 个文件有错误")

    def collect_selection_stats(self):
        """收集选股结果统计"""
        logger.info("收集选股结果统计...")

        reports_dir = os.path.join(self.base_dir, 'reports')

        # 查找最新的选股报告
        latest_report = None
        latest_mtime = 0

        for report_file in Path(reports_dir).glob('daily_recommendation_*.md'):
            mtime = report_file.stat().st_mtime
            if mtime > latest_mtime:
                latest_mtime = mtime
                latest_report = report_file

        if latest_report:
            self.data['latest_selection'] = {
                'file': latest_report.name,
                'date': datetime.fromtimestamp(latest_mtime).isoformat()
            }
            logger.info(f"  最新选股报告: {latest_report.name}")
        else:
            self.data['latest_selection'] = None
            logger.info("  未找到选股报告")

    def save_metrics(self):
        """保存监控数据"""
        self.data['timestamp'] = datetime.now().isoformat()

        # 保存到时间序列文件（追加模式）
        metrics_file = os.path.join(self.base_dir, 'logs', 'monitoring_metrics.jsonl')
        with open(metrics_file, 'a') as f:
            f.write(json.dumps(self.data) + '\n')

        logger.info(f"监控数据已保存: {metrics_file}")

        # 同时保存最新的快照
        snapshot_file = os.path.join(self.base_dir, 'logs', 'monitoring_latest.json')
        with open(snapshot_file, 'w') as f:
            json.dump(self.data, f, indent=2)

        # 清理旧数据（保留最近7天）
        self.cleanup_old_metrics(metrics_file)

    def cleanup_old_metrics(self, metrics_file, days=7):
        """清理旧的监控数据"""
        try:
            cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)

            temp_file = metrics_file + '.tmp'
            kept_lines = 0

            with open(metrics_file, 'r') as infile, open(temp_file, 'w') as outfile:
                for line in infile:
                    try:
                        entry = json.loads(line)
                        entry_time = datetime.fromisoformat(entry['timestamp']).timestamp()
                        if entry_time >= cutoff_time:
                            outfile.write(line)
                            kept_lines += 1
                    except Exception as e:
                        # 跳过无法解析的行
                        pass

            os.replace(temp_file, metrics_file)
            logger.info(f"清理旧的监控数据: 保留 {kept_lines} 条记录")
        except Exception as e:
            logger.warning(f"清理监控数据失败: {e}")

    def run_collection(self):
        """执行一次完整的收集"""
        logger.info("="*60)
        logger.info("监控数据收集开始")
        logger.info("="*60)

        try:
            self.collect_system_metrics()
            self.collect_task_status()
            self.collect_selection_stats()
            self.save_metrics()

            logger.info("="*60)
            logger.info("✅ 监控数据收集完成")
            logger.info("="*60)

            return 0

        except Exception as e:
            logger.error(f"❌ 监控数据收集失败: {e}", exc_info=True)
            return 1

def main():
    """主函数"""
    collector = MonitorCollector()
    return collector.run_collection()

if __name__ == "__main__":
    sys.exit(main())
