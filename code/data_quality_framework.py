#!/usr/bin/env python3
"""
数据质量管理框架
核心功能：
1. 数据质量检查 - 缺失值、异常值（涨跌停、停牌）、一致性检查
2. 数据清洗 - 统一字段命名、处理停牌数据、复权处理
3. 交叉验证 - 多数据源对比、差异识别、可信度评分
4. 数据处理Pipeline - 自动化数据获取、清洗、验证

作者: 架构师
日期: 2026-03-02
"""

import pandas as pd
import numpy as np
import pickle
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass, field
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# 工作目录
WORK_DIR = '/Users/variya/.openclaw/workspace/projects/a-stock-advisor'
os.chdir(WORK_DIR)

# 数据质量阈值配置
QUALITY_THRESHOLDS = {
    'max_missing_rate': 0.05,          # 最大缺失率阈值（5%）
    'max_price_change': 0.2,           # 最大涨跌幅（20%，考虑涨跌停）
    'min_price': 1.0,                  # 最低股价
    'max_price': 3000.0,               # 最高股价
    'min_volume': 0,                   # 最小成交量
    'min_amount': 1000000,            # 最小成交额（100万）
    'min_data_records_per_stock': 100, # 每只股票最少记录数
}

# 标准字段名称
STANDARD_COLUMNS = {
    '股票代码': 'ts_code',
    'code': 'ts_code',
    '股票代码': 'ts_code',
    '日期': 'trade_date',
    'date': 'trade_date',
    '日期': 'trade_date',
    '开盘': 'open',
    '收盘': 'close',
    '最高': 'high',
    '最低': 'low',
    '成交量': 'volume',
    '成交额': 'amount',
    '涨跌幅': 'change_pct',
    '换手率': 'turnover',
}


@dataclass
class QualityReport:
    """数据质量报告"""
    is_valid: bool = False
    total_records: int = 0
    missing_values: Dict[str, int] = field(default_factory=dict)
    missing_rate: Dict[str, float] = field(default_factory=dict)
    outlier_records: int = 0
    stock_data_coverage: Dict[str, int] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


class DataQualityChecker:
    """数据质量检查器"""

    def __init__(self, thresholds: Optional[Dict] = None):
        self.thresholds = thresholds or QUALITY_THRESHOLDS
        self.report = QualityReport()

    def check_data(self, data: pd.DataFrame) -> QualityReport:
        """执行所有数据质量检查"""
        logger.info("🔍 开始数据质量检查...")

        self.report = QualityReport()
        self.report.total_records = len(data)

        try:
            # 1. 数据完整性检查
            self._check_missing_values(data)

            # 2. 异常值检查
            self._check_outliers(data)

            # 3. 数据覆盖度检查
            self._check_data_coverage(data)

            # 4. 数据一致性检查
            self._check_data_consistency(data)

            # 5. 判断整体质量
            self._evaluate_quality()

            logger.info(f"✓ 数据质量检查完成: {'合格' if self.report.is_valid else '不合格'}")

            return self.report

        except Exception as e:
            logger.error(f"✗ 数据质量检查失败: {e}")
            self.report.issues.append(f"质量检查异常: {str(e)}")
            self.report.is_valid = False
            return self.report

    def _check_missing_values(self, data: pd.DataFrame):
        """检查缺失值"""
        logger.info("  📊 检查缺失值...")

        required_columns = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col in data.columns:
                missing_count = data[col].isna().sum()
                if missing_count > 0:
                    missing_rate = missing_count / len(data)
                    self.report.missing_values[col] = missing_count
                    self.report.missing_rate[col] = missing_rate

                    if missing_rate > self.thresholds['max_missing_rate']:
                        self.report.issues.append(
                            f"列 {col} 缺失率过高: {missing_rate:.2%} (阈值: {self.thresholds['max_missing_rate']:.2%})"
                        )
                    else:
                        self.report.warnings.append(
                            f"列 {col} 存在缺失值: {missing_count} 条 ({missing_rate:.2%})"
                        )

    def _check_outliers(self, data: pd.DataFrame):
        """检查异常值：涨跌停、不合理价格、成交量"""
        logger.info("  🔍 检查异常值...")

        outlier_count = 0

        # 检查价格异常
        for price_col in ['open', 'high', 'low', 'close']:
            if price_col in data.columns:
                # 价格范围检查
                too_low = (data[price_col] < self.thresholds['min_price']).sum()
                too_high = (data[price_col] > self.thresholds['max_price']).sum()

                if too_low > 0:
                    outlier_count += too_low
                    self.report.issues.append(f"{price_col} 价格过低 (<{self.thresholds['min_price']}): {too_low} 条")

                if too_high > 0:
                    outlier_count += too_high
                    self.report.issues.append(f"{price_col} 价格过高 (>{self.thresholds['max_price']}): {too_high} 条")

        # 检查涨跌幅异常（超过20%视为异常，实际涨跌停不会超过20%）
        if 'change_pct' in data.columns:
            extreme_change = (data['change_pct'].abs() > self.thresholds['max_price_change'] * 100).sum()
            if extreme_change > 0:
                outlier_count += extreme_change
                self.report.warnings.append(
                    f"极端涨跌幅 (>±{self.thresholds['max_price_change']*100:.0f}%): {extreme_change} 条"
                )

        # 检查成交量异常
        if 'volume' in data.columns:
            zero_volume = (data['volume'] == 0).sum()
            if zero_volume > 0:
                self.report.warnings.append(f"零成交量记录: {zero_volume} 条")

        self.report.outlier_records = outlier_count

        logger.info(f"    检测到 {outlier_count} 条异常记录")

    def _check_data_coverage(self, data: pd.DataFrame):
        """检查数据覆盖度：每只股票的数据量和历史覆盖"""
        logger.info("  📈 检查数据覆盖度...")

        if 'ts_code' in data.columns:
            # 统计每只股票的记录数
            stock_counts = data.groupby('ts_code').size()

            # 检查是否有过少记录的股票
            low_coverage_stocks = stock_counts[
                stock_counts < self.thresholds['min_data_records_per_stock']
            ]

            if len(low_coverage_stocks) > 0:
                self.report.issues.append(
                    f"{len(low_coverage_stocks)} 只股票数据过少 (<{self.thresholds['min_data_records_per_stock']} 条)"
                )
            else:
                logger.info(f"    ✓ 所有股票数据量充足 (>= {self.thresholds['min_data_records_per_stock']} 条)")

            # 存储覆盖度信息
            self.report.stock_data_coverage = {
                'total_stocks': len(stock_counts),
                'avg_records_per_stock': int(stock_counts.mean()),
                'min_records': int(stock_counts.min()),
                'max_records': int(stock_counts.max()),
                'stocks_with_low_coverage': len(low_coverage_stocks)
            }

    def _check_data_consistency(self, data: pd.DataFrame):
        """检查数据一致性：开高低收盘的关系、日期顺序等"""
        logger.info("  🔗 检查数据一致性...")

        # 检查开高低收盘的关系
        if all(col in data.columns for col in ['open', 'high', 'low', 'close']):
            # High >= Close and High >= Open
            invalid_high = ((data['high'] < data['close']) | (data['high'] < data['open'])).sum()
            if invalid_high > 0:
                self.report.issues.append(f"最高价 < 收盘价/开盘价: {invalid_high} 条")

            # Low <= Close and Low <= Open
            invalid_low = ((data['low'] > data['close']) | (data['low'] > data['open'])).sum()
            if invalid_low > 0:
                self.report.issues.append(f"最低价 > 收盘价/开盘价: {invalid_low} 条")

        # 检查日期顺序（按股票分组）
        if 'ts_code' in data.columns and 'trade_date' in data.columns:
            data_sorted = data.sort_values(['ts_code', 'trade_date']).copy()
            # 检查是否有重复记录
            duplicates = data_sorted.duplicated(subset=['ts_code', 'trade_date']).sum()
            if duplicates > 0:
                self.report.issues.append(f"重复交易记录: {duplicates} 条")

    def _evaluate_quality(self):
        """评估整体数据质量"""
        # 如果有严重问题（issues）则不合格
        self.report.is_valid = len(self.report.issues) == 0

        # 输出统计信息
        if self.report.is_valid:
            logger.info(f"    ✓ 数据质量合格")
            logger.info(f"    - 总记录数: {self.report.total_records:,}")
            logger.info(f"    - 缺失值: {sum(self.report.missing_values.values())} 条")
            logger.info(f"    - 异常记录: {self.report.outlier_records} 条")
            logger.info(f"    - 警告: {len(self.report.warnings)} 个")
        else:
            logger.warning(f"    ⚠ 数据质量不合格")
            logger.warning(f"    - 问题数: {len(self.report.issues)} 个")
            for issue in self.report.issues[:3]:
                logger.warning(f"      • {issue}")

    def save_report(self, filepath: str):
        """保存质量报告"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # 转换numpy类型为Python原生类型
        def convert_to_serializable(obj):
            if isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_to_serializable(item) for item in obj]
            elif isinstance(obj, (np.integer, np.int64, np.int32)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64, np.float32)):
                return float(obj)
            else:
                return obj

        report_dict = convert_to_serializable({
            'is_valid': self.report.is_valid,
            'total_records': self.report.total_records,
            'missing_values': self.report.missing_values,
            'missing_rate': self.report.missing_rate,
            'outlier_records': self.report.outlier_records,
            'stock_data_coverage': self.report.stock_data_coverage,
            'issues': self.report.issues,
            'warnings': self.report.warnings,
            'timestamp': self.report.timestamp
        })

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)

        logger.info(f"  ✓ 质量报告已保存至 {filepath}")


class DataCleaner:
    """数据清洗器"""

    def __init__(self):
        self.cleaned_data = None
        self.cleaning_log = []

    def clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """执行完整的数据清洗流程"""
        logger.info("🧹 开始数据清洗...")
        self.cleaned_data = data.copy().reset_index(drop=True)
        self.cleaning_log = []

        try:
            # 1. 标准化字段名称
            self._standardize_columns()

            # 2. 处理缺失值
            self._handle_missing_values()

            # 3. 处理异常值
            self._handle_outliers()

            # 4. 处理停牌数据
            self._handle_suspended_data()

            # 5. 确保数据一致性
            self._ensure_consistency()

            logger.info(f"✓ 数据清洗完成: {len(self.cleaned_data)} 条记录")
            return self.cleaned_data

        except Exception as e:
            logger.error(f"✗ 数据清洗失败: {e}")
            raise

    def _standardize_columns(self):
        """标准化字段名称"""
        logger.info("  📝 标准化字段名称...")

        original_columns = self.cleaned_data.columns.tolist()

        # 应用列名映射
        rename_map = {}
        for col in self.cleaned_data.columns:
            for key, value in STANDARD_COLUMNS.items():
                if key in col.lower():
                    rename_map[col] = value
                    break

        if rename_map:
            self.cleaned_data = self.cleaned_data.rename(columns=rename_map)
            self.cleaning_log.append({
                'step': 'rename_columns',
                'changes': rename_map
            })
            logger.info(f"    ✓ 重命名 {len(rename_map)} 个字段")

    def _handle_missing_values(self):
        """处理缺失值"""
        logger.info("  🔧 处理缺失值...")

        # 统计缺失值
        missing_before = self.cleaned_data.isna().sum().sum()

        # 关键字段缺失则删除整行
        critical_columns = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close']
        valid_mask = self.cleaned_data[critical_columns].notna().all(axis=1)
        removed_rows = (~valid_mask).sum()

        if removed_rows > 0:
            self.cleaned_data = self.cleaned_data[valid_mask].copy()
            self.cleaning_log.append({
                'step': 'remove_missing_critical',
                'removed_rows': int(removed_rows)
            })
            logger.info(f"    删除关键字段缺失: {removed_rows} 条")

        # 非关键字段缺失：如果是数值列则填充0
        numeric_columns = ['volume', 'amount', 'change_pct', 'turnover']
        for col in numeric_columns:
            if col in self.cleaned_data.columns:
                null_count = self.cleaned_data[col].isna().sum()
                if null_count > 0:
                    self.cleaned_data[col] = self.cleaned_data[col].fillna(0)
                    self.cleaning_log.append({
                        'step': 'fill_missing_numeric',
                        'column': col,
                        'filled_count': int(null_count)
                    })

        missing_after = self.cleaned_data.isna().sum().sum()
        logger.info(f"    缺失值: {missing_before} → {missing_after}")

    def _handle_outliers(self):
        """处理异常值"""
        logger.info("  🛡️ 处理异常值...")

        # 价格异常：限制在合理范围内
        for col in ['open', 'high', 'low', 'close']:
            if col in self.cleaned_data.columns:
                too_low = self.cleaned_data[col] < QUALITY_THRESHOLDS['min_price']
                too_high = self.cleaned_data[col] > QUALITY_THRESHOLDS['max_price']

                if too_low.sum() > 0:
                    self.cleaned_data.loc[too_low, col] = QUALITY_THRESHOLDS['min_price']
                    self.cleaning_log.append({
                        'step': 'clamp_price',
                        'column': col,
                        'action': 'min',
                        'count': int(too_low.sum())
                    })

                if too_high.sum() > 0:
                    self.cleaned_data.loc[too_high, col] = QUALITY_THRESHOLDS['max_price']
                    self.cleaning_log.append({
                        'step': 'clamp_price',
                        'column': col,
                        'action': 'max',
                        'count': int(too_high.sum())
                    })

        logger.info(f"    ✓ 异常值处理完成")

    def _handle_suspended_data(self):
        """处理停牌数据：
        - 识别停牌（成交量为0或价格未变）
        - 可以选择保留或剔除
        - 这里选择保留并标记
        """
        logger.info("  🚫 处理停牌数据...")

        if 'volume' in self.cleaned_data.columns and 'change_pct' in self.cleaned_data.columns:
            # 识别停牌：成交量为0且涨跌幅为0
            suspended_mask = (self.cleaned_data['volume'] == 0) & (self.cleaned_data['change_pct'] == 0)

            suspended_count = suspended_mask.sum()
            if suspended_count > 0:
                self.cleaned_data['is_suspended'] = suspended_mask
                self.cleaning_log.append({
                    'step': 'mark_suspended',
                    'count': int(suspended_count)
                })
                logger.info(f"    标记停牌数据: {suspended_count} 条")
            else:
                self.cleaned_data['is_suspended'] = False

    def _ensure_consistency(self):
        """确保数据一致性"""
        logger.info("  ✓ 确保数据一致性...")

        # 修正开高低收盘的不合理关系
        if all(col in self.cleaned_data.columns for col in ['open', 'high', 'low', 'close']):
            # 确保 high >= max(open, close)
            self.cleaned_data['high'] = self.cleaned_data[['high', 'open', 'close']].max(axis=1)

            # 确保 low <= min(open, close)
            self.cleaned_data['low'] = self.cleaned_data[['low', 'open', 'close']].min(axis=1)

            self.cleaning_log.append({
                'step': 'fix_ohlc_consistency'
            })

        # 去除重复记录
        if 'ts_code' in self.cleaned_data.columns and 'trade_date' in self.cleaned_data.columns:
            duplicates_before = self.cleaned_data.duplicated(subset=['ts_code', 'trade_date']).sum()
            if duplicates_before > 0:
                self.cleaned_data = self.cleaned_data.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
                duplicates_after = duplicates_before - len(self.cleaned_data.duplicated(subset=['ts_code', 'trade_date']))
                self.cleaning_log.append({
                    'step': 'remove_duplicates',
                    'removed': int(duplicates_before - duplicates_after)
                })
                logger.info(f"    去除重复记录: {duplicates_before - duplicates_after} 条")

    def save_cleaning_log(self, filepath: str):
        """保存清洗日志"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'cleaning_log': self.cleaning_log,
                'final_records': len(self.cleaned_data),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }, f, ensure_ascii=False, indent=2)

        logger.info(f"  ✓ 清洗日志已保存至 {filepath}")


class DataValidator:
    """多数据源交叉验证器"""

    def __init__(self):
        self.validation_results = []

    def cross_validate(self, data_sources: Dict[str, pd.DataFrame]) -> Dict:
        """交叉验证多个数据源"""
        logger.info(f"🔗 开始交叉验证 {len(data_sources)} 个数据源...")

        results = {
            'sources': list(data_sources.keys()),
            'comparisons': [],
            'warnings': [],
            'recommendations': []
        }

        # 如果只有一个数据源，无法交叉验证
        if len(data_sources) < 2:
            results['warnings'].append("只有一个数据源，无法进行交叉验证")
            results['is_valid'] = True
            return results

        # 对每对数据源进行对比
        source_names = list(data_sources.keys())
        for i in range(len(source_names)):
            for j in range(i + 1, len(source_names)):
                source1 = source_names[i]
                source2 = source_names[j]

                comparison = self._compare_data_sources(
                    data_sources[source1],
                    data_sources[source2],
                    source1,
                    source2
                )
                results['comparisons'].append(comparison)

        # 分析对比结果
        self._analyze_results(results)

        logger.info(f"✓ 交叉验证完成")
        return results

    def _compare_data_sources(self, data1: pd.DataFrame, data2: pd.DataFrame,
                             name1: str, name2: str) -> Dict:
        """对比两个数据源"""
        logger.info(f"  对比: {name1} vs {name2}")

        comparison = {
            'source1': name1,
            'source2': name2,
            'stock_overlap': 0,
            'date_overlap': 0,
            'price_diff_stats': {},
            'volume_diff_stats': {},
            'issues': []
        }

        try:
            # 标准化列名
            df1 = self._standardize_for_comparison(data1)
            df2 = self._standardize_for_comparison(data2)

            # 找到共同股票
            if 'ts_code' in df1.columns and 'ts_code' in df2.columns:
                common_stocks = set(df1['ts_code']).intersection(set(df2['ts_code']))
                comparison['stock_overlap'] = len(common_stocks)

                if len(common_stocks) == 0:
                    comparison['issues'].append("没有共同股票")
                    return comparison

                # 对比共同股票的数据
                df1_common = df1[df1['ts_code'].isin(common_stocks)]
                df2_common = df2[df2['ts_code'].isin(common_stocks)]

                # 创建对比key
                df1_common['key'] = df1_common['ts_code'] + '_' + df1_common['trade_date']
                df2_common['key'] = df2_common['ts_code'] + '_' + df2_common['trade_date']

                # 找到共同记录
                common_keys = set(df1_common['key']).intersection(set(df2_common['key']))
                comparison['date_overlap'] = len(common_keys)

                if len(common_keys) > 0:
                    df1_matched = df1_common[df1_common['key'].isin(common_keys)]
                    df2_matched = df2_common[df2_common['key'].isin(common_keys)]

                    # 价格差异统计
                    for col in ['open', 'high', 'low', 'close']:
                        if col in df1_matched.columns and col in df2_matched.columns:
                            diff = df1_matched[col].values - df2_matched[col].values
                            comparison['price_diff_stats'][col] = {
                                'mean_diff': float(np.nanmean(diff)),
                                'std_diff': float(np.nanstd(diff)),
                                'max_abs_diff': float(np.nanmax(np.abs(diff)))
                            }

                    # 成交量差异统计
                    if 'volume' in df1_matched.columns and 'volume' in df2_matched.columns:
                        vol_diff = df1_matched['volume'].values - df2_matched['volume'].values
                        comparison['volume_diff_stats'] = {
                            'mean_diff_percent': float(np.nanmean(vol_diff / (df2_matched['volume'].values + 1e-6))),
                            'max_abs_diff_percent': float(np.nanmax(np.abs(vol_diff / (df2_matched['volume'].values + 1e-6))))
                        }

        except Exception as e:
            comparison['issues'].append(f"对比过程中出错: {str(e)}")
            logger.warning(f"  对比失败: {e}")

        return comparison

    def _standardize_for_comparison(self, data: pd.DataFrame) -> pd.DataFrame:
        """标准化数据用于对比"""
        df = data.copy()

        # 应用标准列名
        rename_map = {}
        for col in df.columns:
            for key, value in STANDARD_COLUMNS.items():
                if key in col.lower():
                    rename_map[col] = value
                    break

        if rename_map:
            df = df.rename(columns=rename_map)

        # 确保trade_date是字符串格式
        if 'trade_date' in df.columns:
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')

        return df

    def _analyze_results(self, results: Dict):
        """分析对比结果"""
        logger.info("  分析对比结果...")

        # 检查是否有显著差异
        for comp in results['comparisons']:
            if 'price_diff_stats' in comp and comp['price_diff_stats']:
                for col, stats in comp['price_diff_stats'].items():
                    if abs(stats['max_abs_diff']) > 1.0:  # 价格差异超过1元
                        results['warnings'].append(
                            f"{comp['source1']} vs {comp['source2']}: {col} 差异过大 (最大差异: {stats['max_abs_diff']:.2f})"
                        )

            if 'volume_diff_stats' in comp and comp['volume_diff_stats']:
                if abs(comp['volume_diff_stats']['max_abs_diff_percent']) > 0.1:  # 成交量差异超过10%
                    results['warnings'].append(
                        f"{comp['source1']} vs {comp['source2']}: 成交量差异过大 (最大差异: {comp['volume_diff_stats']['max_abs_diff_percent']:.2%})"
                    )

        # 生成建议
        if results['warnings']:
            results['recommendations'].append("建议检查数据源的可靠性，考虑使用最可信的数据源")
        else:
            results['recommendations'].append("各数据源数据基本一致，可以使用任意一个")

        results['is_valid'] = len(results['warnings']) == 0

        logger.info(f"    结果: {'通过' if results['is_valid'] else '有问题'}")


class DataQualityPipeline:
    """数据质量Pipeline"""

    def __init__(self, output_dir: str = 'data'):
        self.output_dir = Path(output_dir)
        self.checker = DataQualityChecker()
        self.cleaner = DataCleaner()
        self.validator = DataValidator()

    def run(self, raw_data: pd.DataFrame, source_name: str = "default",
            cross_validate_with: Dict[str, pd.DataFrame] = None) -> Dict:
        """运行完整的数据质量管理流程"""
        logger.info("=" * 70)
        logger.info("数据质量管理Pipeline")
        logger.info("=" * 70)

        results = {
            'source_name': source_name,
            'raw_records': len(raw_data),
            'steps': {},
            'final_records': 0,
            'is_valid': False
        }

        try:
            # 步骤1: 数据质量检查
            logger.info("\n步骤1: 数据质量检查")
            quality_report = self.checker.check_data(raw_data)
            quality_report_path = self.output_dir / f"{source_name}_quality_report.json"
            self.checker.save_report(str(quality_report_path))
            results['steps']['quality_check'] = {
                'is_valid': quality_report.is_valid,
                'issues_count': len(quality_report.issues),
                'warnings_count': len(quality_report.warnings)
            }

            # 步骤2: 数据清洗
            logger.info("\n步骤2: 数据清洗")
            cleaned_data = self.cleaner.clean_data(raw_data)
            cleaning_log_path = self.output_dir / f"{source_name}_cleaning_log.json"
            self.cleaner.save_cleaning_log(str(cleaning_log_path))
            results['steps']['cleaning'] = {
                'cleaned_records': len(cleaned_data),
                'cleaning_steps': len(self.cleaner.cleaning_log)
            }

            # 步骤3: 交叉验证（如果提供其他数据源）
            if cross_validate_with:
                logger.info("\n步骤3: 交叉验证")
                all_data = {source_name: cleaned_data}
                all_data.update(cross_validate_with)

                validation_results = self.validator.cross_validate(all_data)
                results['steps']['cross_validation'] = validation_results
            else:
                logger.info("\n步骤3: 跳过交叉验证（无其他数据源）")
                validation_results = None

            # 步骤4: 保存清洗后的数据
            logger.info("\n步骤4: 保存清洗后的数据")
            cleaned_path = self.output_dir / f"{source_name}_cleaned.pkl"
            self._save_data(cleaned_data, str(cleaned_path))
            results['final_records'] = len(cleaned_data)

            # 整体评估
            results['is_valid'] = (
                quality_report.is_valid and
                (validation_results is None or validation_results['is_valid'] if isinstance(validation_results, dict) else True)
            )

            logger.info("\n" + "=" * 70)
            logger.info(f"Pipeline完成: {'✓ 成功' if results['is_valid'] else '⚠ 存在问题'}")
            logger.info(f"原始记录: {results['raw_records']:,}")
            logger.info(f"最终记录: {results['final_records']:,}")
            logger.info("=" * 70)

            return results

        except Exception as e:
            logger.error(f"\n❌ Pipeline执行失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            results['error'] = str(e)
            results['is_valid'] = False
            return results

    def _save_data(self, data: pd.DataFrame, filepath: str):
        """保存数据"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'wb') as f:
            pickle.dump(data, f)

        logger.info(f"  ✓ 数据已保存至 {filepath}")


def main():
    """主函数 - 演示使用"""
    logger.info("数据质量管理框架 - 演示模式")

    # 尝试加载现有数据
    try:
        with open('data/real_stock_data.pkl', 'rb') as f:
            raw_data = pickle.load(f)

        logger.info(f"✓ 成功加载数据: {len(raw_data):,} 条记录")

        # 运行Pipeline
        pipeline = DataQualityPipeline()
        results = pipeline.run(raw_data, source_name="akshare_real_data")

        # 输出结果
        print("\n" + "=" * 70)
        print("Pipeline执行结果:")
        print("=" * 70)
        print(f"数据源: {results['source_name']}")
        print(f"原始记录: {results['raw_records']:,}")
        print(f"最终记录: {results['final_records']:,}")
        print(f"状态: {'✓ 合格' if results['is_valid'] else '⚠ 存在问题'}")

        if 'steps' in results:
            print("\n质量检查:")
            print(f"  合格: {results['steps']['quality_check']['is_valid']}")
            print(f"  问题数: {results['steps']['quality_check']['issues_count']}")
            print(f"  警告数: {results['steps']['quality_check']['warnings_count']}")

            print("\n数据清洗:")
            print(f"  清洗后记录: {results['steps']['cleaning']['cleaned_records']:,}")
            print(f"  清洗步骤: {results['steps']['cleaning']['cleaning_steps']}")

    except FileNotFoundError:
        logger.error("✗ 未找到数据文件 data/real_stock_data.pkl")
        logger.info("请先运行数据获取脚本生成数据")
    except Exception as e:
        logger.error(f"✗ 执行失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()
