#!/usr/bin/env python3
"""
回测脚本
任务：定期执行策略回测，验证策略有效性
执行时机：每周日凌晨 2:00
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'code'))

from datetime import datetime, timedelta
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../logs/backtest.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """主函数：执行回测"""
    logger.info("="*60)
    logger.info("策略回测任务")
    logger.info("="*60)

    try:
        from backtest_engine_v2 import BacktestEngine
        from data_pipeline import DataPipeline

        logger.info("初始化回测引擎...")
        engine = BacktestEngine()

        # 设置回测参数
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)  # 回测1年

        logger.info(f"回测周期: {start_date.date()} 至 {end_date.date()}")

        # 加载策略
        strategies = ['trend_following', 'mean_reversion', 'factor_rotation']
        results = {}

        for strategy in strategies:
            logger.info(f"\n执行回测策略: {strategy}")

            try:
                result = engine.run_backtest(
                    strategy=strategy,
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=1000000.0
                )

                results[strategy] = {
                    'total_return': result.get('total_return', 0),
                    'sharpe_ratio': result.get('sharpe_ratio', 0),
                    'max_drawdown': result.get('max_drawdown', 0),
                    'win_rate': result.get('win_rate', 0)
                }

                logger.info(f"  总收益: {results[strategy]['total_return']:.2%}")
                logger.info(f"  夏普比率: {results[strategy]['sharpe_ratio']:.2f}")
                logger.info(f"  最大回撤: {results[strategy]['max_drawdown']:.2%}")
                logger.info(f"  胜率: {results[strategy]['win_rate']:.2%}")

            except Exception as e:
                logger.error(f"  回测失败: {e}")
                results[strategy] = {'error': str(e)}

        # 保存回测报告
        report_date = datetime.now().strftime('%Y%m%d')
        report_path = f'../reports/backtest_report_{report_date}.json'

        import json
        with open(report_path, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'backtest_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'results': results
            }, f, indent=2)

        logger.info(f"\n✓ 回测报告已保存: {report_path}")

        # 如果有策略表现不佳，发出警告
        for strategy, result in results.items():
            if 'error' not in result:
                if result['sharpe_ratio'] < 1.0:
                    logger.warning(f"⚠️ 策略 {strategy} 夏普比率较低，建议优化")

        logger.info("="*60)
        logger.info("✅ 回测任务完成")
        logger.info("="*60)

        return 0

    except Exception as e:
        logger.error(f"❌ 回测异常: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
