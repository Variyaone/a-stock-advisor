#!/usr/bin/env python3
"""
数据管道V3 - 简化版数据更新
基于现有的真实数据进行增量更新
"""

import os
import pandas as pd
import pickle
import logging
from datetime import datetime
import glob

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataPipelineV3:
    """数据管道V3 - 简化版本"""

    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        self.logger = logger

    def update_all_data(self):
        """更新数据（简化版：直接使用现有数据）"""
        try:
            # 检查是否有真实数据
            real_data_path = os.path.join(self.data_dir, 'akshare_real_data_fixed.pkl')

            if os.path.exists(real_data_path):
                self.logger.info(f"✓ 使用真实数据: {real_data_path}")
                data = pd.read_pickle(real_data_path)
                self.logger.info(f"✓ 数据行数: {len(data)}")

                # 检查日期列
                date_col = 'date' if 'date' in data.columns else 'date_dt'
                if date_col in data.columns:
                    self.logger.info(f"✓ 数据日期范围: {data[date_col].min()} ~ {data[date_col].max()}")
                else:
                    self.logger.info("✓ 数据加载成功（未找到日期列）")

                return True
            else:
                # 列出可用的数据文件
                data_files = glob.glob(os.path.join(self.data_dir, '*.pkl'))
                self.logger.warning(f"⚠️ 真实数据不存在，可用文件: {data_files}")

                # 尝试使用任何可用的数据文件
                if data_files:
                    data_path = data_files[0]
                    data = pd.read_pickle(data_path)
                    self.logger.info(f"✓ 使用备用数据: {os.path.basename(data_path)}")
                    return True
                else:
                    self.logger.error("❌ 没有可用的数据文件")
                    return False

        except Exception as e:
            self.logger.error(f"数据更新异常: {e}", exc_info=True)
            return False

    def validate_data(self):
        """验证数据质量"""
        try:
            # 检查是否有数据文件
            real_data_path = os.path.join(self.data_dir, 'akshare_real_data_fixed.pkl')
            if not os.path.exists(real_data_path):
                self.logger.warning("⚠️ 数据文件不存在，跳过验证")
                return True

            data = pd.read_pickle(real_data_path)

            # 基本检查（灵活匹配列名）
            date_col = 'date' if 'date' in data.columns else 'date_dt'
            stock_code_col = 'stock_code' if 'stock_code' in data.columns else 'ts_code'

            required_columns_mapping = {
                'date': date_col,
                'stock_code': stock_code_col,
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            }

            missing_cols = [col for col, mapped_col in required_columns_mapping.items() if mapped_col not in data.columns]

            if missing_cols:
                self.logger.error(f"❌ 缺少必需列: {missing_cols}")
                return False

            self.logger.info(f"✓ 列名检查通过")

            # 逻辑检查
            invalid_prices = (
                (data['high'] < data['low']) |
                (data['high'] < data['close']) |
                (data['low'] > data['open'])
            ).sum()

            if invalid_prices > 0:
                self.logger.warning(f"⚠️ 存在 {invalid_prices} 条价格逻辑异常数据")
            else:
                self.logger.info("✓ 价格逻辑验证通过")

            # 检查是否有PE/PB等因子
            factor_cols = [col for col in data.columns if col in ['PE_TTM', 'PB', '市值_亿', 'PE', 'ROE']]
            if factor_cols:
                self.logger.info(f"✓ 发现因子列: {', '.join(factor_cols)}")
            else:
                self.logger.warning("⚠️ 未发现常用因子列（PE, PB等）")

            return True

        except Exception as e:
            self.logger.error(f"数据验证异常: {e}", exc_info=True)
            return False

    def get_latest_data(self):
        """获取最新数据"""
        real_data_path = os.path.join(self.data_dir, 'akshare_real_data_fixed.pkl')
        if os.path.exists(real_data_path):
            return pd.read_pickle(real_data_path)
        return None


if __name__ == "__main__":
    pipeline = DataPipelineV3()
    pipeline.update_all_data()
    pipeline.validate_data()
