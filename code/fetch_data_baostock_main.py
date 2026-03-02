#!/usr/bin/env python3
"""
多数据源A股数据获取 - Baostock为主
- 主力数据源：Baostock（免费、无限制、质量高）
- 备用数据源：AKShare（如果可用）
- 数据范围：2019-2024（5年历史数据）
- 数据处理：
  * 幸存者偏差处理：获取历史完整股票列表
  * 未来函数消除：因子移位
  * 流动性过滤：成交额>=100万

作者: 研究员
日期: 2026-03-02
"""

import os
import sys
import argparse
from typing import Dict, List, Optional, Tuple

# 根目录
WORK_DIR = '/Users/variya/.openclaw/workspace/projects/a-stock-advisor'
os.chdir(WORK_DIR)

import pandas as pd
import numpy as np
import pickle
import time
import json
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/fetch_baostock.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== 数据配置 ====================
START_DATE = '2019-01-01'
END_DATE = '2024-12-31'
MIN_AMOUNT = 1000000  # 最小成交额过滤（100万人民币）
MIN_DAYS = 200  # 最小交易日数
MAX_STOCKS = None  # None 表示获取所有，可设置为数字进行测试（如 50）

# ==================== Baostock 数据源 ====================
class BaostockDataSource:
    """Baostock数据源"""

    def __init__(self):
        self.name = "Baostock"
        self.is_available = False
        self.bs = None

    def connect(self) -> bool:
        """连接 Baostock"""
        try:
            import baostock as bs
            lg = bs.login()
            self.bs = bs

            if lg.error_code == '0':
                self.is_available = True
                logger.info("✓ Baostock 连接成功")
                return True
            else:
                logger.error(f"Baostock 登录失败: {lg.error_msg}")
                return False
        except ImportError:
            logger.error("Baostock 未安装，请运行: pip install baostock")
            return False
        except Exception as e:
            logger.error(f"Baostock 连接异常: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.bs:
            try:
                self.bs.logout()
            except:
                pass

    def get_stock_list(self, date: str = None) -> pd.DataFrame:
        """
        获取股票列表

        Args:
            date: 查询日期（获取某天的股票列表，用于处理幸存者偏差）
        """
        if not self.is_available:
            return pd.DataFrame()

        if date is None:
            date = END_DATE.split('-')[0] + END_DATE.split('-')[1] + END_DATE.split('-')[2]

        try:
            rs = self.bs.query_all_stock(day=date)
            data_list = []

            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())

            df = pd.DataFrame(data_list, columns=rs.fields)

            # 过滤：只保留 A股
            # sh.600000, sh.601000, sz.000001, sz.002000, sz.300000, sz.688000
            df['exchange'] = df['code'].str[:2]
            df['stock_code'] = df['code'].str[3:]

            # 只保留A股：上海（600-605, 688），深圳（000, 001, 002, 003, 300）
            valid_prefixes = [
                'sh.600', 'sh.601', 'sh.603', 'sh.605', 'sh.688',  # 上海主板+科创板
                'sz.000', 'sz.001', 'sz.002', 'sz.003', 'sz.300'   # 深圳主板+中小板+创业板
            ]

            df_filtered = df[df['code'].str[:6].isin([x for x in valid_prefixes])]

            logger.info(f"获取股票列表: {len(df)} 只 (A股: {len(df_filtered)} 只)")
            return df_filtered

        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return pd.DataFrame()

    def fetch_stock_history(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        adjust_type: str = '2'
    ) -> Optional[pd.DataFrame]:
        """
        获取单只股票历史数据

        Args:
            stock_code: 股票代码，格式如 sh.600000
            start_date: 开始日期，格式 2019-01-01
            end_date: 结束日期
            adjust_type: 复权类型：1=前复权，2=后复权，3=不复权
        """
        try:
            rs = self.bs.query_history_k_data_plus(
                stock_code,
                "date,code,open,high,low,close,preclose,volume,amount,pctChg,turn",
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                frequency="d",
                adjustflag=adjust_type
            )

            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())

            if not data_list:
                return None

            df = pd.DataFrame(data_list, columns=rs.fields)

            # 转换数值列
            numeric_cols = ['open', 'high', 'low', 'close', 'preclose', 'volume', 'amount', 'pctChg', 'turn']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # 添加股票代码（不含交易所前缀）
            df['stock_code'] = stock_code.replace('sh.', '').replace('sz.', '')
            df['exchange'] = stock_code[:2]

            return df

        except Exception as e:
            logger.debug(f"获取 {stock_code} 数据失败: {e}")
            return None

# ==================== 数据处理器 ====================
class DataProcessor:
    """数据处理器：处理幸存者偏差、未来函数、流动性过滤"""

    def __init__(self):
        self.metadata = {
            'version': '2.0',
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'start_date': START_DATE,
            'end_date': END_DATE,
            'min_amount': MIN_AMOUNT,
            'min_days': MIN_DAYS,
            'adjust_type': '后复权',
            'filters': []
        }

    def standardize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名和数据格式"""
        if df is None or len(df) == 0:
            return df

        # 确保必要列存在
        required_cols = ['date', 'stock_code', 'open', 'close', 'high', 'low', 'volume', 'amount']
        for col in required_cols:
            if col not in df.columns:
                logger.warning(f"缺少必要列: {col}")
                return pd.DataFrame()

        # 排序
        df = df.sort_values('date').reset_index(drop=True)

        return df

    def apply_liquidity_filter(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """
        流动性过滤
        去除成交额低于 MIN_AMOUNT 的记录

        Returns:
            (过滤后的数据, 去除的记录数)
        """
        if df is None or len(df) == 0:
            return df, 0

        initial_count = len(df)
        df_filtered = df[df['amount'] >= MIN_AMOUNT].copy()
        removed = initial_count - len(df_filtered)

        if removed > 0:
            logger.info(f"    流动性过滤: 去除 {removed} 条记录 ({removed/initial_count*100:.2f}%)")

        self.metadata['filters'].append({
            'name': 'liquidity',
            'removed': removed,
            'remaining': len(df_filtered)
        })

        return df_filtered, removed

    def apply_minimum_days_filter(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """
        最小交易日数过滤
        去除数据天数少于 MIN_DAYS 的股票

        Returns:
            (过滤后的数据, 去除的记录数)
        """
        if df is None or len(df) == 0:
            return df, 0

        # 按股票分组，计算每只股票的交易天数
        stock_days = df.groupby('stock_code').size()
        valid_stocks = stock_days[stock_days >= MIN_DAYS].index

        initial_count = len(df)
        df_filtered = df[df['stock_code'].isin(valid_stocks)].copy()
        removed = initial_count - len(df_filtered)

        if removed > 0:
            removed_stocks = len(stock_days) - len(valid_stocks)
            logger.info(f"    最小天数过滤: 去除 {removed_stocks} 只股票, {removed} 条记录")
            logger.info(f"    剩余 {len(valid_stocks)} 只股票")

        self.metadata['filters'].append({
            'name': 'minimum_days',
            'removed_stocks': len(stock_days) - len(valid_stocks),
            'removed': removed,
            'remaining_stocks': len(valid_stocks),
            'remaining': len(df_filtered)
        })

        return df_filtered, removed

    def calculate_technical_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术因子（只使用历史数据）

        添加的技术因子：
        - 移动均线: ma5, ma10, ma20, ma60
        - 动量: momentum_5, momentum_10, momentum_20, momentum_60
        - 波动率: volatility_5, volatility_10, volatility_20
        - 价格相对位置: price_to_ma20, price_to_ma60
        """
        if df is None or len(df) < 60:
            return df

        df = df.sort_values('date').copy()

        # 移动均线
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()

        # 动量（收益率）
        df['momentum_5'] = df['close'].pct_change(5)
        df['momentum_10'] = df['close'].pct_change(10)
        df['momentum_20'] = df['close'].pct_change(20)
        df['momentum_60'] = df['close'].pct_change(60)

        # 波动率
        df['volatility_5'] = df['close'].pct_change().rolling(5).std()
        df['volatility_10'] = df['close'].pct_change().rolling(10).std()
        df['volatility_20'] = df['close'].pct_change().rolling(20).std()

        # 价格相对位置
        df['price_to_ma20'] = df['close'] / df['ma20'] - 1
        df['price_to_ma60'] = df['close'] / df['ma60'] - 1

        return df

    def remove_future_leakage(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        消除未来函数（Look-ahead Bias）

        将所有技术因子下移一行，确保当天的因子只使用历史数据计算
        """
        if df is None or len(df) == 0:
            return df

        factor_cols = [
            'ma5', 'ma10', 'ma20', 'ma60',
            'momentum_5', 'momentum_10', 'momentum_20', 'momentum_60',
            'volatility_5', 'volatility_10', 'volatility_20',
            'price_to_ma20', 'price_to_ma60'
        ]

        for col in factor_cols:
            if col in df.columns:
                df[col] = df[col].shift(1)

        logger.info("    已消除未来函数（因子下移一行）")

        return df

# ==================== 主程序 ====================
def main():
    """主函数"""
    # 参数解析
    parser = argparse.ArgumentParser(description='多数据源A股数据获取工具')
    parser.add_argument('--limit', type=int, default=None, help='限制处理的股票数量（测试用）')
    parser.add_argument('--test', action='store_true', help='测试模式：只处理10只股票')
    args = parser.parse_args()

    test_mode = args.test
    limit = args.limit if args.limit else (10 if test_mode else None) or MAX_STOCKS

    # 切换到测试模式
    if test_mode:
        logger.info("⚠️ 测试模式：只处理 10 只股票")

    logger.info("=" * 70)
    logger.info("多数据源A股数据获取工具 - Baostock为主")
    logger.info("=" * 70)

    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    os.makedirs('reports', exist_ok=True)

    # 初始化数据源
    baostock = BaostockDataSource()

    if not baostock.connect():
        logger.error("\n❌ 无法连接到数据源")
        return 1

    # 获取股票列表
    logger.info("\n" + "=" * 70)
    logger.info("步骤1: 获取A股股票列表")
    logger.info("=" * 70)

    # 获取多个时间点的股票列表，用于处理幸存者偏差
    dates_to_check = [
        START_DATE.split('-')[0] + START_DATE.split('-')[1] + START_DATE.split('-')[2],  # 20190101
        '20201231',  # 2020年末
        '20211231',  # 2021年末
        '20221231',  # 2022年末
        '20231231',  # 2023年末
        END_DATE.split('-')[0] + END_DATE.split('-')[1] + END_DATE.split('-')[2],  # 2024年末
    ]

    all_stock_codes = set()
    for date in dates_to_check:
        df = baostock.get_stock_list(date)
        if len(df) > 0:
            codes = set(df['code'].tolist())
            new_codes = codes - all_stock_codes
            all_stock_codes.update(codes)
            logger.info(f"  {date}: {len(df)} 只股票 (新增 {len(new_codes)} 只)")

    logger.info(f"\n历史累计股票: {len(all_stock_codes)} 只")

    # 转换为 DataFrame
    stock_list_data = [{'code': code} for code in all_stock_codes]
    stock_list_df = pd.DataFrame(stock_list_data)

    # 限制股票数量（用于测试）
    if limit and limit < len(stock_list_df):
        logger.info(f"⚠️ 限制处理数量: {limit} 只股票")
        stock_list_df = stock_list_df.head(limit)

    # 初始化数据处理器
    processor = DataProcessor()

    # 获取历史数据
    logger.info("\n" + "=" * 70)
    logger.info("步骤2: 获取历史数据")
    logger.info("=" * 70)
    logger.info(f"时间范围: {START_DATE} 到 {END_DATE}")
    logger.info(f"待处理股票: {len(stock_list_df)} 只")

    all_data = []
    success_count = 0
    no_data_count = 0
    error_count = 0

    for idx, stock in stock_list_df.iterrows():
        stock_code = stock['code']
        stock_code_short = stock_code.replace('sh.', '').replace('sz.', '')

        if (idx + 1) % 50 == 0:
            logger.info(f"  进度: [{idx+1}/{len(stock_list_df)}] "
                       f"成功: {success_count}, 无数据: {no_data_count}, 错误: {error_count}")

        # 获取历史数据
        hist_data = baostock.fetch_stock_history(stock_code, START_DATE, END_DATE)

        if hist_data is not None and len(hist_data) > 0:
            # 标准化数据
            hist_data = processor.standardize_data(hist_data)

            if len(hist_data) >= 20:  # 至少20天数据
                all_data.append(hist_data)
                success_count += 1
            else:
                no_data_count += 1
                logger.debug(f"    {stock_code_short}: 数据天数不足 {len(hist_data)}")
        else:
            no_data_count += 1

        # 控制请求频率
        time.sleep(0.1)

    logger.info(f"\n数据获取完成:")
    logger.info(f"  成功: {success_count} 只股票")
    logger.info(f"  无数据: {no_data_count} 只股票")
    logger.info(f"  错误: {error_count} 只股票")

    if not all_data:
        logger.error("\n❌ 没有成功获取任何数据")
        baostock.disconnect()
        return 1

    # 合并数据
    logger.info("\n" + "=" * 70)
    logger.info("步骤3: 合并数据")
    logger.info("=" * 70)

    combined_data = pd.concat(all_data, ignore_index=True)
    initial_records = len(combined_data)

    logger.info(f"合并后记录数: {initial_records:,}")

    # 数据处理
    logger.info("\n" + "=" * 70)
    logger.info("步骤4: 数据处理与质量控制")
    logger.info("=" * 70)

    # 流动性过滤
    combined_data, removed_liquidity = processor.apply_liquidity_filter(combined_data)

    # 最小交易日数过滤
    combined_data, removed_days = processor.apply_minimum_days_filter(combined_data)

    # 计算技术因子
    logger.info("  计算技术因子...")
    combined_data = processor.calculate_technical_factors(combined_data)

    # 消除未来函数
    combined_data = processor.remove_future_leakage(combined_data)

    # 更新元数据
    processor.metadata.update({
        'total_stocks_processed': len(stock_list_df),
        'successful_stocks': success_count,
        'initial_records': initial_records,
        'final_records': len(combined_data),
        'final_stocks': combined_data['stock_code'].nunique(),
        'date_range': f"{combined_data['date'].min()} 至 {combined_data['date'].max()}",
        'months': combined_data['month'].nunique() if 'month' in combined_data.columns else 0
    })

    logger.info(f"\n最终统计:")
    logger.info(f"  股票数量: {combined_data['stock_code'].nunique()} 只")
    logger.info(f"  记录数: {len(combined_data):,} 条")
    logger.info(f"  时间范围: {combined_data['date'].min()} 至 {combined_data['date'].max()}")

    # 保存数据
    logger.info("\n" + "=" * 70)
    logger.info("步骤5: 保存数据")
    logger.info("=" * 70)

    output_file = 'data/real_stock_data_v2.pkl'
    with open(output_file, 'wb') as f:
        pickle.dump(combined_data, f)

    # 保存元数据
    metadata_file = output_file.replace('.pkl', '_metadata.json')
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(processor.metadata, f, ensure_ascii=False, indent=2)

    logger.info(f"✓ 数据已保存: {output_file}")
    logger.info(f"✓ 元数据已保存: {metadata_file}")

    # 生成质量报告
    logger.info("\n" + "=" * 70)
    logger.info("步骤6: 生成质量报告")
    logger.info("=" * 70)

    generate_quality_report(combined_data, processor.metadata)

    logger.info("\n" + "=" * 70)
    logger.info("✓ 数据获取完成！")
    logger.info("=" * 70)

    # 断开连接
    baostock.disconnect()

    return 0


def generate_quality_report(data: pd.DataFrame, metadata: dict):
    """生成数据质量报告"""

    report_file = 'reports/real_data_quality_report_v2.md'

    report_lines = [
        "# A股真实数据质量报告 (Baostock)",
        "",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"数据源: Baostock (免费、开源、无调用限制)",
        "",
        "## 数据概览",
        "",
        f"- **总记录数**: {len(data):,}",
        f"- **股票数量**: {data['stock_code'].nunique()}",
        f"- **时间范围**: {data['date'].min()} 至 {data['date'].max()}",
        f"- **复权类型**: {metadata.get('adjust_type', '后复权')}",
        "",
        "## 数据统计特征",
        "",
        "### 价格统计",
        ""
    ]

    for col in ['open', 'close', 'high', 'low']:
        if col in data.columns:
            report_lines.extend([
                f"**{col}**:",
                f"- 均值: {data[col].mean():.2f}",
                f"- 中位数: {data[col].median():.2f}",
                f"- 最小值: {data[col].min():.2f}",
                f"- 最大值: {data[col].max():.2f}",
                ""
            ])

    if 'pctChg' in data.columns:
        change_data = data['pctChg'].dropna()
        report_lines.extend([
            "### 涨跌幅统计",
            "",
            f"- **均值**: {change_data.mean():.2f}%",
            f"- **中位数**: {change_data.median():.2f}%",
            f"- **标准差**: {change_data.std():.2f}%",
            f"- **范围**: {change_data.min():.2f}% ~ {change_data.max():.2f}%",
            ""
        ])

    if 'turn' in data.columns:
        turnover_data = data['turn'].dropna()
        report_lines.extend([
            "### 换手率统计",
            "",
            f"- **均值**: {turnover_data.mean():.2f}%",
            f"- **中位数**: {turnover_data.median():.2f}%",
            f"- **标准差**: {turnover_data.std():.2f}%",
            ""
        ])

    report_lines.extend([
        "## 技术因子统计",
        "",
        "| 因子 | 均值 | 标准差 | 样本数 |",
        "|------|------|--------|--------|"
    ])

    factor_cols = ['ma20', 'momentum_20', 'volatility_20', 'price_to_ma20']
    for col in factor_cols:
        if col in data.columns:
            data_col = data[col].dropna()
            report_lines.append(
                f"| {col} | {data_col.mean():.4f} | {data_col.std():.4f} | {len(data_col):,} |"
            )

    report_lines.extend([
        "",
        "## 数据处理说明",
        "",
        "### 1. 幸存者偏差处理",
        "- 获取多个时间点的股票列表（2019、2020、2021、2022、2023、2024）",
        "- 累计所有历史股票，避免只选择当前存续股票",
        "",
        "### 2. 未来函数消除",
        "- 所有技术因子下移一行（shift(1)）",
        "- 确保当天的因子只使用历史数据计算",
        "",
        "### 3. 流动性过滤",
        f"- 去除成交额 < {metadata.get('min_amount', 1000000):,} 的记录",
        "- 过滤流动性差的日期，减少价格异常影响",
        "",
        f"### 4. 最小交易日数过滤",
        f"- 去除交易日数 < {metadata.get('min_days', 200)} 天的股票",
        "- 确保有足够的历史数据进行回测分析",
        "",
        "### 5. 其他处理",
        "- 后复权数据（adjustflag=2）",
        "- 标准化列名和数据格式",
        "- 按日期排序",
        ""
    ])

    # 数据质量指标
    report_lines.extend([
        "## 数据质量指标",
        "",
        f"- **数据完整性**: {len(data) / metadata.get('initial_records', 1) * 100:.2f}%",
        f"- **股票覆盖率**: {data['stock_code'].nunique() / metadata.get('total_stocks_processed', 1) * 100:.2f}%",
        f"- **时间覆盖率**: {len(data['month'].unique()) if 'month' in data.columns else 0} 个月",
        ""
    ])

    report_lines.extend([
        f"---",
        f"*报告生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
    ])

    # 保存报告
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

    logger.info(f"✓ 质量报告已保存: {report_file}")


if __name__ == '__main__':
    exit(main())
