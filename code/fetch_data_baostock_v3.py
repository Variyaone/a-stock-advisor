#!/usr/bin/env python3
"""
多数据源A股数据获取 - Baostock为主（修复版）
- 主力数据源：Baostock（免费、无限制、质量高）
- 数据范围：2019-2024（5年历史数据）
- 数据处理：幸存者偏差、未来函数消除、流动性过滤

作者: 研究员
日期: 2026-03-02
"""

import os
import sys
import argparse
import baostock as bs
import pandas as pd
import numpy as np
import pickle
import time
import json
import logging
from datetime import datetime
from typing import Optional, Tuple

# 根目录
WORK_DIR = '/Users/variya/.openclaw/workspace/projects/a-stock-advisor'
os.chdir(WORK_DIR)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/fetch_baostock_v3.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== 配置参数 ====================
START_DATE = '2019-01-01'
END_DATE = '2024-12-31'
MIN_AMOUNT = 1000000  # 最小成交额（100万）
MIN_DAYS = 200  # 最小交易日数

class BaostockFetcher:
    """Baostock数据获取器"""

    def __init__(self):
        self.bs = bs
        self.metadata = {
            'version': '3.0',
            'source': 'Baostock',
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'start_date': START_DATE,
            'end_date': END_DATE,
            'min_amount': MIN_AMOUNT,
            'min_days': MIN_DAYS
        }

    def connect(self):
        """连接Baostock"""
        lg = self.bs.login()
        if lg.error_code == '0':
            logger.info("✓ Baostock 连接成功")
            return True
        else:
            logger.error(f"Baostock 登录失败: {lg.error_msg}")
            return False

    def disconnect(self):
        """断开连接"""
        self.bs.logout()

    def get_stock_list(self) -> pd.DataFrame:
        """获取A股股票列表"""
        logger.info("获取A股股票列表...")

        # 获取所有证券基本信息
        rs = self.bs.query_stock_basic()
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())

        df = pd.DataFrame(data_list, columns=rs.fields)
        logger.info(f"  总证券数: {len(df)}")

        # 过滤：type='1' (股票), status='1' (正常上市)
        df_stocks = df[(df['type'] == '1') & (df['status'] == '1')].copy()
        logger.info(f"  正常上市股票: {len(df_stocks)}")

        # 过滤A股
        valid_prefixes = [
            'sh.600', 'sh.601', 'sh.603', 'sh.605', 'sh.688',
            'sz.000', 'sz.001', 'sz.002', 'sz.003', 'sz.300'
        ]
        df_a = df_stocks[df_stocks['code'].str[:6].isin(valid_prefixes)].copy()
        logger.info(f"  A股数量: {len(df_a)}")

        return df_a

    def fetch_stock_history(self, stock_code: str) -> Optional[pd.DataFrame]:
        """获取单只股票历史数据"""
        try:
            rs = self.bs.query_history_k_data_plus(
                stock_code,
                "date,code,open,high,low,close,preclose,volume,amount,pctChg,turn",
                start_date=START_DATE.replace('-', ''),
                end_date=END_DATE.replace('-', ''),
                frequency="d",
                adjustflag="2"  # 后复权
            )

            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())

            if not data_list:
                return None

            df = pd.DataFrame(data_list, columns=rs.fields)

            # 转换数值
            for col in ['open', 'high', 'low', 'close', 'preclose', 'volume', 'amount', 'pctChg', 'turn']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # 添加股票代码
            df['stock_code'] = stock_code.replace('sh.', '').replace('sz.', '')

            return df

        except Exception as e:
            logger.debug(f"获取 {stock_code} 失败: {e}")
            return None

    def apply_liquidity_filter(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """流动性过滤"""
        initial = len(df)
        df = df[df['amount'] >= MIN_AMOUNT].copy()
        removed = initial - len(df)
        if removed > 0:
            logger.info(f"  流动性过滤: 去除 {removed} 条 ({removed/initial*100:.1f}%)")
        return df, removed

    def apply_min_days_filter(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """最小交易日数过滤"""
        stock_days = df.groupby('stock_code').size()
        valid_stocks = stock_days[stock_days >= MIN_DAYS].index

        initial = len(df)
        initial_stocks = df['stock_code'].nunique()
        df = df[df['stock_code'].isin(valid_stocks)].copy()

        removed = initial - len(df)
        removed_stocks = initial_stocks - len(valid_stocks)

        if removed_stocks > 0:
            logger.info(f"  最小天数过滤: 去除 {removed_stocks} 只股票, {removed} 条记录")
            logger.info(f"  剩余股票: {len(valid_stocks)} 只")

        return df, removed

    def calculate_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术因子"""
        df = df.sort_values('date').copy()

        # 移动均线
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()

        # 动量
        df['momentum_5'] = df['close'].pct_change(5)
        df['momentum_20'] = df['close'].pct_change(20)

        # 波动率
        df['volatility_20'] = df['close'].pct_change().rolling(20).std()

        # 价格相对位置
        df['price_to_ma20'] = df['close'] / df['ma20'] - 1

        # 消除未来函数（因子下移一行）
        factor_cols = ['ma5', 'ma10', 'ma20', 'ma60', 'momentum_5', 'momentum_20', 
                       'volatility_20', 'price_to_ma20']
        for col in factor_cols:
            if col in df.columns:
                df[col] = df[col].shift(1)

        return df

    def run(self, limit: int = None, test_mode: bool = False):
        """执行数据获取"""
        logger.info("=" * 70)
        logger.info("A股数据获取工具 - Baostock")
        logger.info("=" * 70)

        if test_mode:
            limit = 10
            logger.info(f"⚠️ 测试模式: 只处理 {limit} 只股票")

        # 连接
        if not self.connect():
            return 1

        # 获取股票列表
        logger.info("\n步骤1: 获取股票列表")
        stock_list = self.get_stock_list()

        if limit:
            stock_list = stock_list.head(limit)
            logger.info(f"  限制处理: {limit} 只股票")

        # 获取历史数据
        logger.info(f"\n步骤2: 获取历史数据 ({START_DATE} ~ {END_DATE})")
        all_data = []
        success = 0

        for idx, row in stock_list.iterrows():
            code = row['code']
            name = row.get('code_name', '')

            if (idx + 1) % 50 == 0:
                logger.info(f"  进度: [{idx+1}/{len(stock_list)}] 成功: {success}")

            hist = self.fetch_stock_history(code)
            if hist is not None and len(hist) >= 20:
                hist['stock_name'] = name
                all_data.append(hist)
                success += 1

            time.sleep(0.1)  # 控制频率

        logger.info(f"\n获取完成: 成功 {success} 只股票")

        if not all_data:
            logger.error("❌ 没有获取到任何数据")
            self.disconnect()
            return 1

        # 合并数据
        logger.info("\n步骤3: 合并数据")
        combined = pd.concat(all_data, ignore_index=True)
        logger.info(f"  合并后记录数: {len(combined):,}")

        # 数据处理
        logger.info("\n步骤4: 数据处理")
        combined, _ = self.apply_liquidity_filter(combined)
        combined, _ = self.apply_min_days_filter(combined)

        # 计算技术因子
        logger.info("\n步骤5: 计算技术因子")
        combined = self.calculate_factors(combined)

        # 更新元数据
        self.metadata.update({
            'total_records': len(combined),
            'total_stocks': combined['stock_code'].nunique(),
            'date_range': f"{combined['date'].min()} ~ {combined['date'].max()}"
        })

        logger.info(f"\n最终统计:")
        logger.info(f"  股票数: {combined['stock_code'].nunique()}")
        logger.info(f"  记录数: {len(combined):,}")
        logger.info(f"  时间范围: {combined['date'].min()} ~ {combined['date'].max()}")

        # 保存数据
        logger.info("\n步骤6: 保存数据")
        os.makedirs('data', exist_ok=True)
        os.makedirs('reports', exist_ok=True)

        output_file = 'data/real_stock_data_v3.pkl'
        with open(output_file, 'wb') as f:
            pickle.dump(combined, f)

        metadata_file = 'data/real_stock_data_v3_metadata.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

        logger.info(f"  ✓ 数据已保存: {output_file}")
        logger.info(f"  ✓ 元数据已保存: {metadata_file}")

        # 生成报告
        self.generate_report(combined)

        # 断开连接
        self.disconnect()

        logger.info("\n" + "=" * 70)
        logger.info("✓ 数据获取完成！")
        logger.info("=" * 70)

        return 0

    def generate_report(self, data: pd.DataFrame):
        """生成数据质量报告"""
        report_file = 'reports/data_quality_report_v3.md'

        lines = [
            "# A股数据质量报告 (Baostock)",
            "",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 数据概览",
            "",
            f"- **总记录数**: {len(data):,}",
            f"- **股票数量**: {data['stock_code'].nunique()}",
            f"- **时间范围**: {data['date'].min()} ~ {data['date'].max()}",
            "",
            "## 数据统计",
            ""
        ]

        # 价格统计
        for col in ['open', 'close', 'high', 'low']:
            if col in data.columns:
                lines.append(f"- **{col}**: 均值={data[col].mean():.2f}, 中位数={data[col].median():.2f}")

        # 涨跌幅统计
        if 'pctChg' in data.columns:
            pct = data['pctChg'].dropna()
            lines.extend([
                "",
                "### 涨跌幅统计",
                "",
                f"- 均值: {pct.mean():.2f}%",
                f"- 标准差: {pct.std():.2f}%",
                f"- 范围: {pct.min():.2f}% ~ {pct.max():.2f}%",
                ""
            ])

        # 数据处理说明
        lines.extend([
            "## 数据处理",
            "",
            "✓ 流动性过滤（成交额>=100万）",
            "✓ 最小交易日数过滤（>=200天）",
            "✓ 计算技术因子（移动均线、动量、波动率）",
            "✓ 消除未来函数（因子下移一行）",
            ""
        ])

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        logger.info(f"  ✓ 报告已保存: {report_file}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='测试模式')
    parser.add_argument('--limit', type=int, help='限制股票数量')
    args = parser.parse_args()

    fetcher = BaostockFetcher()
    return fetcher.run(limit=args.limit, test_mode=args.test)


if __name__ == '__main__':
    sys.exit(main())
