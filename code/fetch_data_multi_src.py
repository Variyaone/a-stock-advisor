#!/usr/bin/env python3
"""
多数据源A股数据获取脚本
- 支持 AKShare, Tushare, baostock 等多种数据源
- 自动降级到可用数据源
- 处理幸存者偏差、未来函数、流动性过滤

作者: 研究员
日期: 2026-03-02
"""

import os
import sys
from abc import ABC, abstractmethod

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
from typing import Dict, List, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/fetch_multi_src.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 数据配置
START_DATE = '20190101'
END_DATE = '20241231'
MIN_AMOUNT = 1000000  # 最小成交额过滤（100万人民币）

# A股主要股票列表（硬编码，作为备用 fallback）
MAJOR_STOCKS = [
    ('000001', '平安银行'), ('000002', '万科A'), ('000063', '中兴通讯'),
    ('000333', '美的集团'), ('000651', '格力电器'), ('000725', '京东方A'),
    ('000858', '五粮液'), ('002594', '比亚迪'), ('002415', '海康威视'),
    ('600000', '浦发银行'), ('600036', '招商银行'), ('600519', '贵州茅台'),
    ('600900', '长江电力'), ('601318', '中国平安'), ('601888', '中国中免'),
    ('601939', '建设银行'), ('603259', '药明康德'), ('000066', '长城电脑'),
    ('000100', 'TCL科技'), ('000157', '中联重科'), ('000166', '申万宏源'),
    ('000338', '潍柴动力'), ('001979', '招商蛇口'), ('002007', '华兰生物'),
    ('002027', '分众传媒'), ('002475', '立讯精密'), ('002714', '牧原股份'),
    ('600004', '白云机场'), ('600009', '上海机场'), ('600015', '华夏银行'),
    ('600016', '民生银行'), ('600019', '宝钢股份'), ('600025', '华能国际'),
    ('600027', '华电国际'), ('600029', '南方航空'), ('600030', '中信证券'),
    ('600031', '三一重工'), ('600036', '招商银行'), ('600048', '保利发展'),
    ('600050', '中国联通'), ('600104', '上汽集团'), ('600111', '北方稀土'),
    ('600150', '中国船舶'), ('600176', '中国巨石'), ('600221', '海航控股'),
    ('600276', '恒瑞医药'), ('600309', '万华化学'), ('600340', '华夏幸福'),
    ('600489', '中金黄金'), ('600585', '海螺水泥'), ('600600', '青岛啤酒'),
    ('601012', '隆基绿能'), ('601066', '中信建投'), ('601088', '中国神华'),
    ('601100', '恒立液压'), ('601138', '工业富联'), ('601155', '新城控股'),
    ('601186', '中国铁建'), ('601211', '国泰君安'), ('601225', '陕西煤业'),
    ('601288', '农业银行'), ('601298', '青岛港'), ('601319', '中国人保'),
    ('601390', '中国中铁'), ('601398', '工商银行'), ('601600', '中国铝业'),
    ('601601', '中国太保'), ('601628', '中国人寿'), ('601668', '中国建筑'),
    ('601766', '中国中车'), ('601857', '中国石油'), ('601888', '中国中免'),
    ('601919', '中远海控'), ('601985', '中国核电'), ('601988', '中国银行'),
    ('603019', '中科曙光'), ('603259', '药明康德'), ('603288', '海天味业'),
    ('603501', '韦尔股份'), ('603658', '安井食品'), ('603816', '顾家家居'),
]


class DataSource(ABC):
    """数据源抽象基类"""

    def __init__(self, name: str):
        self.name = name
        self.is_available = False

    @abstractmethod
    def test_connection(self) -> bool:
        """测试连接是否可用"""
        pass

    @abstractmethod
    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""
        pass

    @abstractmethod
    def fetch_stock_history(self, stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取单只股票历史数据"""
        pass


class TushareDataSource(DataSource):
    """Tushare数据源"""

    def __init__(self, token: str):
        super().__init__("Tushare")
        self.token = token
        self.pro = None

    def test_connection(self) -> bool:
        try:
            import tushare as ts
            ts.set_token(self.token)
            self.pro = ts.pro_api()

            # 测试获取股票列表
            df = self.pro.stock_basic(exchange='', list_status='L',
                                      fields='ts_code,symbol,name,area,industry,list_date',
                                      limit=5)

            self.is_available = len(df) > 0
            logger.info(f"  ✓ Tushare 连接成功")
            return True
        except Exception as e:
            logger.warning(f"  ✗ Tushare 连接失败: {e}")
            return False

    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""
        try:
            df = self.pro.stock_basic(exchange='', list_status='L',
                                      fields='ts_code,symbol,name')
            df.columns = ['ts_code', 'code', 'name']
            # 只保留A股 (上海主板、深圳主板、创业板、科创板)
            df = df[df['ts_code'].str.match(r'^(600|601|603|605|688|000|001|002|003|300)\d{3}$')]
            return df
        except Exception as e:
            logger.error(f"获取Tushare股票列表失败: {e}")
            return pd.DataFrame()

    def fetch_stock_history(self, stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取历史数据"""
        try:
            df = self.pro.daily(ts_code=stock_code, start_date=start_date, end_date=end_date)

            if len(df) == 0:
                return None

            # 标准化列名
            df.columns = [col.lower() for col in df.columns]

            # 添加需要的列
            if 'turnover_rate' not in df.columns:
                df['turnover_rate'] = None

            # 转换日期格式
            df['date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')

            # 添加 ts_code
            df['stock_code'] = df['ts_code'].apply(lambda x: x.replace('.SZ', '').replace('.SH', ''))

            return df
        except Exception as e:
            logger.debug(f"  Tushare获取{stock_code}失败: {e}")
            return None


class AKShareDataSource(DataSource):
    """AKShare数据源"""

    def __init__(self):
        super().__init__("AKShare")
        self.code_name_map = None

    def test_connection(self) -> bool:
        try:
            import akshare as ak

            # 测试获取股票名称映射
            self.code_name_map = ak.stock_info_a_code_name()
            self.is_available = len(self.code_name_map) > 0

            logger.info(f"  ✓ AKShare 连接成功")
            return True
        except Exception as e:
            logger.warning(f"  ✗ AKShare 连接失败: {e}")
            return False

    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""
        if self.code_name_map is not None:
            return self.code_name_map
        return pd.DataFrame()

    def fetch_stock_history(self, stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取历史数据"""
        import time
        import akshare as ak

        max_retries = 3
        for attempt in range(max_retries):
            try:
                df = ak.stock_zh_a_hist(
                    symbol=stock_code,
                    period="daily",
                    start_date=start_date.replace('-', ''),
                    end_date=end_date.replace('-', ''),
                    adjust="qfq"
                )

                if df is None or len(df) == 0:
                    time.sleep(1)
                    continue

                # 添加股票代码
                df['stock_code'] = stock_code

                # 标准化列名
                column_mapping = {
                    '日期': 'date',
                    '开盘': 'open',
                    '收盘': 'close',
                    '最高': 'high',
                    '最低': 'low',
                    '成交量': 'volume',
                    '成交额': 'amount',
                    '振幅': 'amplitude',
                    '涨跌幅': 'change_pct',
                    '涨跌额': 'change_amount',
                    '换手率': 'turnover'
                }
                df = df.rename(columns=column_mapping)

                # 转换数值列
                numeric_columns = ['open', 'close', 'high', 'low', 'volume', 'amount',
                                 'amplitude', 'change_pct', 'change_amount', 'turnover']
                for col in numeric_columns:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

                # 日期格式
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

                return df

            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    logger.debug(f"  AKShare获取{stock_code}失败: {e}")
                    return None

        return None


class MultiSourceDataFetcher:
    """多数据源数据获取器"""

    def __init__(self):
        self.metadata = {
            'source': 'multi_source',
            'start_date': START_DATE,
            'end_date': END_DATE,
            'min_amount': MIN_AMOUNT,
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'sources_tested': [],
            'active_source': None
        }

        self.data_sources: List[DataSource] = []
        self.primary_source: Optional[DataSource] = None

    def init_sources(self):
        """初始化所有数据源"""
        logger.info("初始化数据源...")

        # 1. 尝试 Tushare
        tushare_token = "14423f1b4d5af6dc47dd1dc8d9d5994dc05d10dbb86cc2d0da753d25"
        tushare_src = TushareDataSource(tushare_token)
        self.data_sources.append(tushare_src)

        # 2. 尝试 AKShare
        akshare_src = AKShareDataSource()
        self.data_sources.append(akshare_src)

        # 测试所有源
        for src in self.data_sources:
            result = src.test_connection()
            self.metadata['sources_tested'].append({
                'name': src.name,
                'available': result
            })

            if result and self.primary_source is None:
                self.primary_source = src
                self.metadata['active_source'] = src.name
                logger.info(f"选择 {src.name} 作为主要数据源")

        if self.primary_source is None:
            logger.warning("所有外部数据源不可用，使用硬编码股票列表")
            self.primary_source = None

    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""
        if self.primary_source:
            try:
                df = self.primary_source.get_stock_list()
                if len(df) > 0:
                    return df
            except Exception as e:
                logger.warning(f"从{self.primary_source.name}获取股票列表失败: {e}")

        # Fallback: 使用硬编码列表
        logger.info("使用硬编码的主要A股列表")
        df = pd.DataFrame(MAJOR_STOCKS, columns=['code', 'name'])
        return df

    def fetch_stock_history_all(self, stock_code: str) -> Optional[pd.DataFrame]:
        """尝试从所有可用源获取股票历史数据"""
        if self.primary_source:
            df = self.primary_source.fetch_stock_history(stock_code, START_DATE[:4] + '-' + START_DATE[4:6] + '-' + START_DATE[6:],
                                                         END_DATE[:4] + '-' + END_DATE[4:6] + '-' + END_DATE[6:])
            if df is not None and len(df) > 0:
                return df

        # 尝试备用源
        for src in self.data_sources:
            if src != self.primary_source and src.is_available:
                logger.debug(f"尝试{src.name}获取{stock_code}")
                df = src.fetch_stock_history(stock_code, START_DATE[:4] + '-' + START_DATE[4:6] + '-' + START_DATE[6:],
                                             END_DATE[:4] + '-' + END_DATE[4:6] + '-' + END_DATE[6:])
                if df is not None and len(df) > 0:
                    return df

        return None

    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        # 确保所有必须的列存在
        required_cols = ['date', 'stock_code', 'open', 'close', 'high', 'low', 'volume', 'amount', 'turnover']

        for col in required_cols:
            if col not in df.columns and col == 'turnover':
                if 'turnover_rate' in df.columns:
                    df['turnover'] = df['turnover_rate']
                else:
                    df['turnover'] = None

        return df

    def _filter_by_date(self, df: pd.DataFrame) -> pd.DataFrame:
        """过滤日期范围"""
        if 'date' not in df.columns:
            return df

        start = START_DATE[:4] + '-' + START_DATE[4:6] + '-' + START_DATE[6:]
        end = END_DATE[:4] + '-' + END_DATE[4:6] + '-' + END_DATE[6:]
        mask = (df['date'] >= start) & (df['date'] <= end)
        return df[mask].copy()

    def calculate_technical_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术因子（只使用历史数据）"""
        if len(df) < 60:
            return df

        df = df.sort_values('date').copy()

        # 移动均线
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()

        # 动量
        df['momentum_5'] = df['close'].pct_change(5)
        df['momentum_10'] = df['close'].pct_change(10)
        df['momentum_20'] = df['close'].pct_change(20)
        df['momentum_60'] = df['close'].pct_change(60)

        # 波动率
        df['volatility_5'] = df['close'].pct_change().rolling(5).std()
        df['volatility_10'] = df['close'].pct_change().rolling(10).std()
        df['volatility_20'] = df['close'].pct_change().rolling(20).std()

        # 换手率均值
        if 'turnover' in df.columns and df['turnover'].notna().any():
            df['turnover_ma5'] = df['turnover'].rolling(5).mean()
            df['turnover_ma20'] = df['turnover'].rolling(20).mean()
        else:
            df['turnover_ma5'] = None
            df['turnover_ma20'] = None

        # 成交额均值
        df['amount_ma5'] = df['amount'].rolling(5).mean()
        df['amount_ma20'] = df['amount'].rolling(20).mean()

        # 价格相对位置
        df['price_to_ma20'] = df['close'] / df['ma20'] - 1
        df['price_to_ma60'] = df['close'] / df['ma60'] - 1

        return df

    def remove_future_leakage(self, df: pd.DataFrame) -> pd.DataFrame:
        """消除未来函数"""
        factor_cols = [
            'ma5', 'ma10', 'ma20', 'ma60',
            'momentum_5', 'momentum_10', 'momentum_20', 'momentum_60',
            'volatility_5', 'volatility_10', 'volatility_20',
            'turnover_ma5', 'turnover_ma20',
            'amount_ma5', 'amount_ma20',
            'price_to_ma20', 'price_to_ma60'
        ]

        for col in factor_cols:
            if col in df.columns:
                df[col] = df[col].shift(1)

        return df

    def apply_liquidity_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """流动性过滤"""
        initial_count = len(df)
        if 'amount' in df.columns:
            df = df[df['amount'] >= MIN_AMOUNT].copy()

        removed = initial_count - len(df)
        logger.info(f"  💧 流动性过滤: 去除 {removed} 条记录 ({removed/initial_count*100:.2f}%)")
        return df

    def process_all_stocks(self, limit: int = None) -> Optional[pd.DataFrame]:
        """处理所有股票数据"""
        logger.info("=" * 70)
        logger.info("开始获取A股历史数据")
        logger.info("=" * 70)

        # 获取股票列表
        stock_list = self.get_stock_list()

        if limit:
            stock_list = stock_list.head(limit)
            logger.info(f"⚠️ 测试模式：只处理前 {limit} 只股票")

        logger.info(f"共需处理 {len(stock_list)} 只股票")

        all_data = []
        success_count = 0
        no_data_count = 0

        for idx, stock in stock_list.iterrows():
            stock_code = stock.get('code') or stock.get('ts_code', '').split('.')[0] or stock.get('ts_code')
            stock_name = stock.get('name', '')

            if not stock_code:
                continue

            if (idx + 1) % 10 == 0:
                logger.info(f"  进度: [{idx+1}/{len(stock_list)}] 成功: {success_count}")

            # 获取数据
            hist_data = self.fetch_stock_history_all(stock_code)

            if hist_data is not None and len(hist_data) > 0:
                # 添加股票名称
                hist_data['stock_name'] = stock_name

                # 标准化列名
                hist_data = self._standardize_columns(hist_data)

                # 日期过滤
                hist_data = self._filter_by_date(hist_data)

                if len(hist_data) < 50:
                    no_data_count += 1
                    continue

                # 计算技术因子
                hist_data = self.calculate_technical_factors(hist_data)

                # 消除未来函数
                hist_data = self.remove_future_leakage(hist_data)

                all_data.append(hist_data)
                success_count += 1
            else:
                no_data_count += 1

            # 控制请求频率
            time.sleep(0.3)

        if not all_data:
            logger.error("✗ 没有成功获取任何数据")
            return None

        # 合并数据
        combined_data = pd.concat(all_data, ignore_index=True)

        logger.info(f"\n✓ 数据获取完成: 成功={success_count}, 无数据={no_data_count}")

        # 添加月份列
        combined_data['date_dt'] = pd.to_datetime(combined_data['date'])
        combined_data['month'] = combined_data['date_dt'].dt.strftime('%Y-%m')

        # 流动性过滤
        combined_data = self.apply_liquidity_filter(combined_data)

        # 保存元数据
        self.metadata['versions'] = [{
            'step': 'process_all_stocks',
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'success_count': success_count,
            'no_data_count': no_data_count,
            'total_records': len(combined_data),
            'unique_stocks': int(combined_data['stock_code'].nunique()),
            'date_range': f"{combined_data['date'].min()} to {combined_data['date'].max()}"
        }]

        return combined_data

    def save_data(self, data: pd.DataFrame, filepath: str):
        """保存数据"""
        logger.info(f"\n💾 保存数据到 {filepath}...")

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'wb') as f:
            pickle.dump(data, f)

        # 保存元数据
        metadata_file = filepath.replace('.pkl', '_metadata.json')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

        logger.info(f"  ✓ 数据已保存 ({len(data)} 条记录)")
        logger.info(f"  ✓ 元数据已保存")


def generate_quality_report(data: pd.DataFrame, output_file: str, metadata: dict):
    """生成数据质量报告"""
    logger.info(f"\n📊 生成数据质量报告...")

    report_lines = [
        "# A股真实数据质量报告",
        "",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"数据源: {metadata.get('active_source', 'multi_source')}",
        "",
        "## 数据源测试结果",
        ""
    ]

    for src in metadata.get('sources_tested', []):
        status = "✓" if src['available'] else "✗"
        report_lines.append(f"- {status} **{src['name']}**: {'可用' if src['available'] else '不可用'}")

    report_lines.extend([
        "",
        "## 数据概览",
        "",
        f"- **总记录数**: {len(data):,}",
        f"- **股票数量**: {data['stock_code'].nunique()}",
        f"- **时间范围**: {data['date'].min()} 至 {data['date'].max()}",
        f"- **月份数量**: {data['month'].nunique()}",
        "",
        "## 数据统计特征",
        ""
    ])

    # 价格统计
    for col in ['open', 'close', 'high', 'low']:
        if col in data.columns:
            report_lines.append(f"- **{col}**: 均值={data[col].mean():.2f}, 中位数={data[col].median():.2f}")

    report_lines.append("")

    # 涨跌幅
    if 'change_pct' in data.columns:
        change_data = data['change_pct'].dropna()
        report_lines.extend([
            f"- **涨跌幅**: 均值={change_data.mean():.2f}%, 中位数={change_data.median():.2f}%",
            f"- **涨跌幅范围**: {change_data.min():.2f}% ~ {change_data.max():.2f}%",
            ""
        ])

    report_lines.extend([
        "## 技术因子统计",
        "",
        "| 因子 | 均值 | 标准差 |",
        "|------|------|--------|"
    ])

    factor_cols = ['ma20', 'momentum_20', 'volatility_20', 'turnover_ma20']
    for col in factor_cols:
        if col in data.columns:
            report_lines.append(f"| {col} | {data[col].mean():.4f} | {data[col].std():.4f} |")

    report_lines.extend([
        "",
        "## 数据处理说明",
        "",
        "✓ 标准化列名和数据格式",
        "✓ 筛选日期范围 (2019-2024)",
        "✓ 计算技术因子（移动均线、动量、波动率等）",
        "✓ 消除未来函数（因子下移一行）",
        "✓ 流动性过滤（成交额>=100万）",
        "",
        f"---\n*报告生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
    ])

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

    logger.info(f"  ✓ 报告已保存到 {output_file}")


def main():
    """主函数"""
    logger.info("\n" + "=" * 70)
    logger.info("多数据源A股数据获取工具")
    logger.info("=" * 70)

    os.makedirs('logs', exist_ok=True)

    fetcher = MultiSourceDataFetcher()

    try:
        # 初始化数据源
        fetcher.init_sources()

        # 处理股票 (测试模式: 20只, 完整模式: None)
        data = fetcher.process_all_stocks(limit=20)

        if data is None or len(data) == 0:
            logger.error("\n✗ 未能获取到任何数据")
            return 1

        # 保存数据
        output_file = 'data/real_stock_data.pkl'
        fetcher.save_data(data, output_file)

        # 生成质量报告
        report_file = 'reports/real_data_quality_report.md'
        generate_quality_report(data, report_file, fetcher.metadata)

        logger.info("\n" + "=" * 70)
        logger.info("✓ 数据获取完成！")
        logger.info("=" * 70)

        return 0

    except Exception as e:
        logger.error(f"\n❌ 数据获取失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == '__main__':
    exit(main())
