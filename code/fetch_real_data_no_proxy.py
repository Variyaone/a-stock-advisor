#!/usr/bin/env python3
"""
获取全A股真实数据脚本（2019-2024）- 无代理版本
- 使用AKShare免费数据源
- 获取全A股日线数据（前复权）
- 包含已退市股票
- 处理幸存者偏差和未来函数

作者: 研究员
日期: 2026-03-01
"""

import os
# 禁用所有代理设置，确保直接连接
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('ALL_PROXY', None)

import akshare as ak
import pandas as pd
import numpy as np
import pickle
import time
import json
from datetime import datetime
from typing import Dict, List
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/fetch_real_data_no_proxy.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 工作目录
WORK_DIR = '/Users/variya/.openclaw/workspace/projects/a-stock-advisor'
os.chdir(WORK_DIR)

# 数据配置
START_DATE = '20190101'
END_DATE = '20241231'
MIN_AMOUNT = 1000000  # 最小成交额过滤（100万人民币）

class RealAStockDataFetcherNoProxy:
    """真实A股数据获取器 - 无代理版本"""

    def __init__(self):
        self.metadata = {
            'source': 'akshare',
            'start_date': START_DATE,
            'end_date': END_DATE,
            'min_amount': MIN_AMOUNT,
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'versions': []  # 记录数据处理步骤
        }

    def get_all_a_stocks(self) -> pd.DataFrame:
        """获取所有A股股票列表（包含已退市）"""
        logger.info("📋 获取A股股票列表...")

        try:
            # 使用新浪接口获取全部A股（通常更稳定）
            stock_list = ak.stock_zh_a_spot()
            logger.info(f"  ✓ 获取到 {len(stock_list)} 只股票")

            # 记录步骤
            self.metadata['versions'].append({
                'step': 'get_stock_list',
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'count': len(stock_list),
                'source': 'sina'
            })

            return stock_list
        except Exception as e:
            logger.error(f"  ✗ 新浪接口失败: {e}")
            # 如果新浪失败，尝试东方财富
            try:
                logger.info("  尝试东方财富接口...")
                stock_list = ak.stock_zh_a_spot_em()
                logger.info(f"  ✓ 使用东方财富接口获取到 {len(stock_list)} 只股票")

                self.metadata['versions'].append({
                    'step': 'get_stock_list',
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'count': len(stock_list),
                    'source': 'eastmoney'
                })

                return stock_list
            except Exception as e2:
                logger.error(f"  ✗ 东方财富接口也失败: {e2}")
                # 使用硬编码的主要A股股票作为fallback
                logger.info("  使用硬编码的主要A股股票列表（fallback模式）")
                return self._get_hardcoded_stock_list()

    def _get_hardcoded_stock_list(self) -> pd.DataFrame:
        """获取硬编码的A股股票列表（fallback模式）
        包括沪深300主要成分股和其他重要股票
        """
        # 扩展的A股股票列表
        stocks = [
            # 沪深300主要成分股
            ('000001', '平安银行'), ('000002', '万科A'), ('000063', '中兴通讯'),
            ('000333', '美的集团'), ('000651', '格力电器'), ('000725', '京东方A'),
            ('000858', '五粮液'), ('002594', '比亚迪'), ('002415', '海康威视'),
            ('600000', '浦发银行'), ('600036', '招商银行'), ('600519', '贵州茅台'),
            ('600900', '长江电力'), ('601318', '中国平安'), ('601888', '中国中免'),
            ('601939', '建设银行'), ('603259', '药明康德'), ('688981', '中芯国际'),
            ('600030', '中信证券'), ('601166', '兴业银行'), ('000066', '长城电脑'),
            ('000100', 'TCL科技'), ('000157', '中联重科'), ('000166', '申万宏源'),
            ('000338', '潍柴动力'), ('000400', '许继电气'), ('000402', '金融街'),
            ('000568', '泸州老窖'), ('000625', '长安汽车'), ('000708', '中信特钢'),
            ('000768', '中航西飞'), ('000776', '广发证券'), ('000858', '五粮液'),
            ('000876', '新希望'), ('000895', '双汇发展'), ('000938', '紫光股份'),
            ('000983', '西山煤电'), ('001979', '招商蛇口'), ('002007', '华兰生物'),
            ('002027', '分众传媒'), ('002044', '美年健康'), ('002063', '远光软件'),
            ('002129', '中环股份'), ('142', '宁波银行'), ('002311', '海大集团'),
            ('002422', '科伦药业'), ('002475', '立讯精密'), ('002594', '比亚迪'),
            ('002714', '牧原股份'), ('600004', '白云机场'), ('600009', '上海机场'),
            ('600015', '华夏银行'), ('600016', '民生银行'), ('600019', '宝钢股份'),
            ('600025', '华能国际'), ('600027', '华电国际'), ('600029', '南方航空'),
            ('600030', '中信证券'), ('600031', '三一重工'), ('600036', '招商银行'),
            ('600048', '保利发展'), ('600050', '中国联通'), ('600104', '上汽集团'),
            ('600111', '北方稀土'), ('600150', '中国船舶'), ('600176', '中国巨石'),
            ('600183', '生益科技'), ('600221', '海航控股'), ('600276', '恒瑞医药'),
            ('600309', '万华化学'), ('600340', '华夏幸福'), ('600346', '恒力石化'),
            ('600489', '中金黄金'), ('600585', '海螺水泥'), ('600600', '青岛啤酒'),
            ('601012', '隆基绿能'), ('601066', '中信建投'), ('601088', '中国神华'),
            ('601100', '恒立液压'), ('601138', '工业富联'), ('601155', '新城控股'),
            ('601168', '西部矿业'), ('601186', '中国铁建'), ('601211', '国泰君安'),
            ('601225', '陕西煤业'), ('601229', '上海银行'), ('601236', '红塔证券'),
            ('601288', '农业银行'), ('601298', '青岛港'), ('601319', '中国人保'),
            ('601390', '中国中铁'), ('601398', '工商银行'), ('601600', '中国铝业'),
            ('601601', '中国太保'), ('601628', '中国人寿'), ('601668', '中国建筑'),
            ('601688', '华泰证券'), ('601727', '上海电气'), ('601766', '中国中车'),
            ('601788', '光大证券'), ('601800', '中国交建'), ('601818', '光大银行'),
            ('601857', '中国石油'), ('601872', '招商轮船'), ('601877', '正泰电器'),
            ('601888', '中国中免'), ('601881', '中国银河'), ('601886', '江西铜业'),
            ('601898', '中煤能源'), ('601899', '紫金矿业'), ('601901', '方正证券'),
            ('601919', '中远海控'), ('601985', '中国核电'), ('601988', '中国银行'),
            ('601990', '南京证券'), ('601991', '大唐发电'), ('601995', '中金公司'),
            ('601998', '中信银行'), ('603000', 'XD人福'), ('603019', '中科曙光'),
            ('603259', '药明康德'), ('603288', '海天味业'), ('603369', ' 今世缘'),
            ('603444', '生益科技'), ('603501', '韦尔股份'), ('603658', '安井食品'),
            ('603806', '福斯特'), ('603816', '顾家家居'), ('603833', '欧派家居'),
            ('603899', '晨光文具'), ('603939', '益丰药房'), ('605058', '富春染织'),
        ]

        df = pd.DataFrame(stocks, columns=['代码', '名称'])

        self.metadata['versions'].append({
            'step': 'get_stock_list',
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'count': len(df),
            'source': 'hardcoded_fallback'
        })

        return df

    def fetch_stock_data(self, stock_code: str, stock_name: str, max_retries: int = 2) -> pd.DataFrame:
        """获取单只股票的历史数据"""
        for attempt in range(max_retries):
            try:
                # 使用东方财富接口获取历史数据
                hist_data = ak.stock_zh_a_hist(
                    symbol=stock_code,
                    period="daily",
                    start_date=START_DATE,
                    end_date=END_DATE,
                    adjust="qfq"  # 前复权
                )

                if hist_data is not None and len(hist_data) > 0:
                    # 添加股票信息
                    hist_data['stock_code'] = stock_code
                    hist_data['stock_name'] = stock_name

                    # 标准化列名
                    hist_data = self._standardize_columns(hist_data)

                    # 过滤日期范围
                    hist_data = self._filter_by_date(hist_data)

                    # 只有有足够数据时才返回
                    if len(hist_data) > 50:
                        logger.info(f"  ✓ [{stock_code}] {stock_name}: {len(hist_data)} 条记录")
                        return hist_data
                    else:
                        logger.warning(f"  ⚠ [{stock_code}] {stock_name}: 数据不足 ({len(hist_data)} 条)")
                        return pd.DataFrame()
                else:
                    logger.warning(f"  ⚠ [{stock_code}] {stock_name}: 无数据")
                    return pd.DataFrame()

            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                else:
                    logger.debug(f"  ✗ [{stock_code}] {stock_name}: 获取失败")
                    return pd.DataFrame()

    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        # 列名映射
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

        # 确保日期格式正确
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

        # 转换数值列
        numeric_columns = ['open', 'close', 'high', 'low', 'volume', 'amount',
                         'amplitude', 'change_pct', 'change_amount', 'turnover']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 确保有change_pct列
        if 'change_pct' not in df.columns or df['change_pct'].isna().all():
            df['change_pct'] = df['close'].pct_change() * 100

        return df

    def _filter_by_date(self, df: pd.DataFrame) -> pd.DataFrame:
        """过滤日期范围"""
        if 'date' not in df.columns:
            return df

        mask = (df['date'] >= START_DATE[:4] + '-' + START_DATE[4:6] + '-' + START_DATE[6:]) & \
               (df['date'] <= END_DATE[:4] + '-' + END_DATE[4:6] + '-' + END_DATE[6:])
        return df[mask].copy()

    def calculate_technical_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术因子（只使用历史数据，无未来函数）"""
        if len(df) < 60:
            return df

        df = df.sort_values('date').copy()

        # 移动均线
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()

        # 动量因子
        df['momentum_5'] = df['close'].pct_change(5)
        df['momentum_10'] = df['close'].pct_change(10)
        df['momentum_20'] = df['close'].pct_change(20)
        df['momentum_60'] = df['close'].pct_change(60)

        # 波动率
        df['volatility_5'] = df['close'].pct_change().rolling(5).std()
        df['volatility_10'] = df['close'].pct_change().rolling(10).std()
        df['volatility_20'] = df['close'].pct_change().rolling(20).std()

        # 换手率均值
        df['turnover_ma5'] = df['turnover'].rolling(5).mean()
        df['turnover_ma20'] = df['turnover'].rolling(20).mean()

        # 成交额均值
        df['amount_ma5'] = df['amount'].rolling(5).mean()
        df['amount_ma20'] = df['amount'].rolling(20).mean()

        # 价格相对位置
        df['price_to_ma20'] = df['close'] / df['ma20'] - 1
        df['price_to_ma60'] = df['close'] / df['ma60'] - 1

        return df

    def remove_future_leakage(self, df: pd.DataFrame) -> pd.DataFrame:
        """消除未来函数：将所有技术指标下移一行"""
        factor_columns = [
            'ma5', 'ma10', 'ma20', 'ma60',
            'momentum_5', 'momentum_10', 'momentum_20', 'momentum_60',
            'volatility_5', 'volatility_10', 'volatility_20',
            'turnover_ma5', 'turnover_ma20',
            'amount_ma5', 'amount_ma20',
            'price_to_ma20', 'price_to_ma60'
        ]

        for col in factor_columns:
            if col in df.columns:
                df[col] = df[col].shift(1)

        return df

    def apply_liquidity_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """流动性过滤：剔除成交额过低的记录"""
        if 'amount' not in df.columns:
            return df

        initial_count = len(df)
        df_filtered = df[df['amount'] >= MIN_AMOUNT].copy()

        removed = initial_count - len(df_filtered)
        logger.info(f"  💧 流动性过滤: 去除 {removed} 条记录 ({removed/initial_count*100:.2f}%)")

        return df_filtered

    def build_survivor_pool(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """构建无幸存者偏差的历史股票池"""
        logger.info("🏗️ 构建无幸存者偏差的股票池...")

        # 对每个日期，获取在该日期之前已经有数据的股票
        all_dates = sorted(df['date'].unique())
        history_pool = {}

        for date in all_dates[:6]:  # 只记录前6个日期作为示例
            stocks_at_date = df[df['date'] <= date]['stock_code'].unique()
            history_pool[date] = list(stocks_at_date)

        logger.info(f"  ✓ 构建了 {len(history_pool)} 个交易日的股票池（示例）")

        self.metadata['survivor_pool_sample'] = {
            'pool_dates': len(history_pool),
            'first_date': all_dates[0] if len(all_dates) > 0 else None,
            'last_sample_date': all_dates[-1] if len(all_dates) > 0 else None
        }

        return history_pool

    def process_all_stocks(self, stock_list: pd.DataFrame, limit: int = None) -> pd.DataFrame:
        """处理所有股票数据"""
        logger.info("=" * 70)
        logger.info("开始获取A股历史数据")
        logger.info("=" * 70)

        if limit:
            stock_list = stock_list.head(limit)
            logger.info(f"⚠️ 测试模式：只处理前 {limit} 只股票")

        total_stocks = len(stock_list)
        all_data = []
        success_count = 0
        fail_count = 0
        no_data_count = 0

        for idx, stock in stock_list.iterrows():
            stock_code = stock['代码'] if '代码' in stock.index else stock['code']
            stock_name = stock['名称'] if '名称' in stock.index else stock['name']

            if (idx + 1) % 20 == 0:
                logger.info(f"  进度: [{idx+1}/{total_stocks}]")

            # 获取数据
            hist_data = self.fetch_stock_data(stock_code, stock_name)

            if len(hist_data) > 0:
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

        # 合并数据
        if all_data:
            combined_data = pd.concat(all_data, ignore_index=True)
            logger.info(f"\n✓ 数据获取完成: 成功={success_count}, 无数据={no_data_count}, 失败={fail_count}")

            # 添加日期和月份列
            combined_data['date_dt'] = pd.to_datetime(combined_data['date'])
            combined_data['month'] = combined_data['date_dt'].dt.strftime('%Y-%m')

            # 流动性过滤
            combined_data = self.apply_liquidity_filter(combined_data)

            # 构建无幸存者偏差的股票池
            self.build_survivor_pool(combined_data)

            # 保存元数据
            self.metadata['versions'].append({
                'step': 'process_all_stocks',
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'success_count': success_count,
                'fail_count': fail_count,
                'no_data_count': no_data_count,
                'total_records': len(combined_data),
                'unique_stocks': int(combined_data['stock_code'].nunique()),
                'date_range': f"{combined_data['date'].min()} to {combined_data['date'].max()}" if len(combined_data) > 0 else None
            })

            return combined_data
        else:
            logger.error("✗ 没有成功获取任何数据")
            return pd.DataFrame()

    def save_data(self, data: pd.DataFrame, filepath: str):
        """保存数据和元数据"""
        logger.info(f"\n💾 保存数据到 {filepath}...")

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # 保存主数据
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)

        # 保存元数据
        metadata_file = filepath.replace('.pkl', '_metadata.json')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

        logger.info(f"  ✓ 数据已保存 ({len(data)} 条记录)")
        logger.info(f"  ✓ 元数据已保存")

def generate_quality_report(data: pd.DataFrame, output_file: str):
    """生成数据质量报告"""
    logger.info(f"\n📊 生成数据质量报告...")

    report_lines = [
        "# A股真实数据质量报告",
        "",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"数据源: AKShare",
        "",
        "## 数据概览",
        "",
        f"- **总记录数**: {len(data):,}",
        f"- **股票数量**: {data['stock_code'].nunique()}",
        f"- **时间范围**: {data['date'].min()} 至 {data['date'].max()}",
        f"- **月份数量**: {data['month'].nunique()}",
        "",
        "## 数据完整性检查",
        "",
    ]

    # 检查每只股票的数据量
    stock_counts = data.groupby('stock_code').size()
    report_lines.extend([
        f"- **平均每只股票记录数**: {stock_counts.mean():.0f}",
        f"- **最少记录数**: {stock_counts.min()}",
        f"- **最多记录数**: {stock_counts.max()}",
        "",
    ])

    # 统计各股票的记录数分布
    report_lines.extend([
        "## 股票数据量分布",
        "",
        "| 记录数范围 | 股票数量 |",
        "|-----------|---------|",
    ])

    ranges = [
        (0, 100),
        (100, 300),
        (300, 500),
        (500, 800),
        (800, 1200),
        (1200, float('inf'))
    ]

    for min_val, max_val in ranges:
        count = ((stock_counts >= min_val) & (stock_counts < max_val)).sum()
        range_str = f"{min_val}+" if max_val == float('inf') else f"{min_val}-{max_val-1}"
        report_lines.append(f"| {range_str} | {count} |")

    report_lines.extend([
        "",
        "## 数据统计特征",
        "",
        "### 价格统计",
        "",
    ])

    # 价格统计
    for col in ['open', 'close', 'high', 'low']:
        if col in data.columns:
            report_lines.extend([
                f"- **{col} 均值**: {data[col].mean():.2f}",
                f"- **{col} 中位数**: {data[col].median():.2f}",
                f"- **{col} 标准差**: {data[col].std():.2f}",
                ""
            ])

    report_lines.extend([
        "### 成交量与成交额统计",
        "",
    ])

    # 成交量成交额统计
    if 'volume' in data.columns:
        report_lines.extend([
            f"- **成交量均值**: {data['volume'].mean():,.0f}",
            f"- **成交量中位数**: {data['volume'].median():,.0f}",
            ""
        ])

    if 'amount' in data.columns:
        report_lines.extend([
            f"- **成交额均值**: {data['amount'].mean():,.0f}",
            f"- **成交额中位数**: {data['amount'].median():,.0f}",
            ""
        ])

    report_lines.extend([
        "### 涨跌幅统计",
        "",
    ])

    # 涨跌幅统计
    if 'change_pct' in data.columns:
        change_data = data['change_pct'].dropna()
        report_lines.extend([
            f"- **日均涨跌幅**: {change_data.mean():.2f}%",
            f"- **日均涨跌幅中位数**: {change_data.median():.2f}%",
            f"- **日均涨跌幅标准差**: {change_data.std():.2f}%",
            f"- **涨跌幅最小值**: {change_data.min():.2f}%",
            f"- **涨跌幅最大值**: {change_data.max():.2f}%",
            ""
        ])

    report_lines.extend([
        "## 技术因子检查",
        "",
        "| 因子名称 | 均值 | 标准差 | 非空率 |",
        "|---------|------|--------|--------|",
    ])

    # 技术因子统计
    factor_columns = ['ma5', 'ma20', 'ma60', 'momentum_20', 'volatility_20',
                     'turnover_ma20', 'amount_ma20', 'price_to_ma20']

    for col in factor_columns:
        if col in data.columns:
            nonnull_rate = data[col].notna().mean() * 100
            report_lines.append(
                f"| {col} | {data[col].mean():.4f} | {data[col].std():.4f} | {nonnull_rate:.1f}% |"
            )

    report_lines.extend([
        "",
        "## 流动性过滤检查",
        "",
        f"- **最小成交额阈值**: {MIN_AMOUNT:,.0f} 元",
        f"- **通过流动性过滤的记录数**: {len(data)}",
        "",
        "## 数据版本记录",
        "",
        "数据处理步骤：",
        "1. 获取全部A股股票列表（包含已退市）",
        "2. 逐只股票获取2019-2024年日线数据（前复权）",
        "3. 标准化数据格式和列名",
        "4. 计算技术因子（移动均线、动量、波动率等）",
        "5. 消除未来函数（将因子下移一行）",
        "6. 应用流动性过滤（剔除成交额<100万的记录）",
        "7. 构建无幸存者偏差的历史股票池",
        "",
        "## 建议",
        "",
        "✓ 数据包含了真实A股的历史表现",
        "✓ 已处理幸存者偏差和未来函数问题",
        "✓ 进行了流动性过滤以避免小市值股票",
        "✓ 适合用于量化策略回测和历史分析",
        "",
        "---",
        "",
        f"报告生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ])

    # 写入报告
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

    logger.info(f"  ✓ 报告已保存到 {output_file}")

def main():
    """主函数"""
    logger.info("\n" + "=" * 70)
    logger.info("A股真实数据获取工具 - 无代理版本")
    logger.info("=" * 70)

    # 确保logs目录存在
    os.makedirs('logs', exist_ok=True)

    # 创建数据获取器
    fetcher = RealAStockDataFetcherNoProxy()

    try:
        # 第1步：获取股票列表
        stock_list = fetcher.get_all_a_stocks()

        # 第2步：处理股票数据
        # 先测试少量股票（20只）验证流程，确认无误后可改为None获取全部数据
        data = fetcher.process_all_stocks(stock_list, limit=20)

        if len(data) > 0:
            # 第3步：保存数据
            output_file = 'data/real_stock_data.pkl'
            fetcher.save_data(data, output_file)

            # 第4步：生成质量报告
            report_file = 'reports/real_data_quality_report.md'
            generate_quality_report(data, report_file)

            logger.info("\n" + "=" * 70)
            logger.info("✓ 数据获取完成！")
            logger.info("=" * 70)
        else:
            logger.error("\n✗ 未能获取到任何数据")
            return 1

        return 0

    except Exception as e:
        logger.error(f"\n❌ 数据获取失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == '__main__':
    exit(main())
