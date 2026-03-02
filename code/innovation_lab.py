#!/usr/bin/env python3
"""
A股量化创新实验室
- 因子原型快速验证
- 因子有效性评估（IC/IR/单调性）
- 因子相关性分析
- 策略原型验证
- 创新因子库与策略库管理

目标：
1. 每周探索至少2个新因子
2. 每周设计至少1个新策略
3. 有效因子：IC绝对值>0.02，IR>0.5
4. 有效策略：年化收益>10%，夏普>1.0

作者: 创新实验室
日期: 2026-03-01
版本: v1.0
"""

import akshare as ak
import pandas as pd
import numpy as np
import pickle
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Callable
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.FileHandler('/Users/variya/.openclaw/workspace/projects/a-stock-advisor/logs/innovation_lab.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 工作目录
WORK_DIR = '/Users/variya/.openclaw/workspace/projects/a-stock-advisor'
os.chdir(WORK_DIR)

# 创新评价标准
VALIDATION_THRESHOLDS = {
    'factor': {
        'ic_abs': 0.02,      # IC绝对值阈值
        'ir': 0.5,           # IR阈值
        'ic_win_rate': 0.55,  # IC胜率阈值
        'turnover': 0.8,     # 最大换手率
    },
    'strategy': {
        'annual_return': 0.10,  # 年化收益率10%
        'sharpe': 1.0,          # 夏普比率
        'max_drawdown': -0.30,  # 最大回撤<30%
        'calmar': 0.33,         # 卡玛比率
    },
    'innovation': {
        'success_rate': 0.20,   # 有效创新率>20%
    }
}

class InnovationMetrics:
    """创新指标计算与评估"""

    @staticmethod
    def calculate_ic(factor_values: pd.Series, future_returns: pd.Series) -> Dict:
        """
        计算IC（信息系数）相关指标

        Args:
            factor_values: 因子值序列（股票×日期的多层索引）
            future_returns: 未来收益率序列

        Returns:
            包含IC相关指标的字典
        """
        # 按日期分组计算IC
        ics = []
        dates = factor_values.index.get_level_values('date').unique()

        for date in dates:
            try:
                # 获取当日因子值和未来收益率
                factor_date = factor_values.loc[date]
                return_date = future_returns.loc[date]

                # 对齐股票
                common_stocks = factor_date.index.intersection(return_date.index)
                if len(common_stocks) < 10:  # 股票数太少则跳过
                    continue

                ic = np.corrcoef(factor_date.loc[common_stocks], return_date.loc[common_stocks])[0, 1]
                ics.append(ic)
            except Exception as e:
                continue

        if len(ics) == 0:
            return {'error': '无法计算IC'}

        ics = np.array(ics)

        return {
            'ic_mean': float(np.mean(ics)),
            'ic_std': float(np.std(ics)),
            'ic_max': float(np.max(ics)),
            'ic_min': float(np.min(ics)),
            'ir': float(np.mean(ics) / np.std(ics)) if np.std(ics) > 0 else 0,
            'ic_abs_mean': float(np.mean(np.abs(ics))),
            'ic_win_rate': float(np.mean(ics > 0)),
            'ic_t_stat': float(stats.ttest_1samp(ics, 0)[0]),
            'ic_p_value': float(stats.ttest_1samp(ics, 0)[1]),
            'n_periods': len(ics),
        }

    @staticmethod
    def calculate_monotonicity(
        factor_values: pd.Series,
        future_returns: pd.Series,
        n_groups: int = 5
    ) -> Dict:
        """
        计算因子单调性

        Args:
            factor_values: 因子值序列
            future_returns: 未来收益率序列
            n_groups: 分组数

        Returns:
            单调性指标
        """
        # 按日期分组
        dates = factor_values.index.get_level_values('date').unique()
        group_returns = {i: [] for i in range(n_groups)}

        for date in dates:
            try:
                factor_date = factor_values.loc[date]
                return_date = future_returns.loc[date]

                # 对齐股票
                common_stocks = factor_date.index.intersection(return_date.index)
                if len(common_stocks) < 10:
                    continue

                # 按因子值分组
                factor_aligned = factor_date.loc[common_stocks]
                return_aligned = return_date.loc[common_stocks]

                # 使用分位数分组
                quantiles = np.linspace(0, 1, n_groups + 1)
                groups = pd.qcut(factor_aligned, quantiles, labels=False, duplicates='drop')

                for group_idx in range(n_groups):
                    group_mask = groups == group_idx
                    if group_mask.sum() > 0:
                        group_returns[group_idx].append(return_aligned[group_mask].mean())
            except Exception as e:
                continue

        # 计算各组平均收益
        avg_group_returns = []
        for group_idx in range(n_groups):
            if group_returns[group_idx]:
                avg_group_returns.append(np.mean(group_returns[group_idx]))
            else:
                avg_group_returns.append(0)

        # 计算单调性指标
        monotonic_groups = 0
        for i in range(len(avg_group_returns) - 1):
            if avg_group_returns[i] < avg_group_returns[i + 1]:
                monotonic_groups += 1

        monotonicity = monotonic_groups / (len(avg_group_returns) - 1) if len(avg_group_returns) > 1 else 0

        # Spearman相关性 - 使用已对齐的数据
        try:
            common_index = factor_values.index.intersection(future_returns.index)
            factor_aligned = factor_values.loc[common_index]
            return_aligned = future_returns.loc[common_index]

            if len(factor_aligned) > 0 and len(return_aligned) > 0:
                spearman_corr, spearman_p = stats.spearmanr(factor_aligned.values, return_aligned.values)
                spearman_corr = float(spearman_corr if not np.isnan(spearman_corr) else 0)
                spearman_p_value = float(spearman_p if not np.isnan(spearman_p) else 1)
            else:
                spearman_corr = 0
                spearman_p_value = 1
        except Exception as e:
            spearman_corr = 0
            spearman_p_value = 1

        return {
            'monotonicity': float(monotonicity),
            'group_returns': avg_group_returns,
            'long_short_return': float(avg_group_returns[-1] - avg_group_returns[0]),
            'spearman_corr': spearman_corr,
            'spearman_p_value': spearman_p_value,
            'n_groups': n_groups,
        }

    @staticmethod
    def calculate_turnover(
        current_weights: pd.Series,
        previous_weights: pd.Series
    ) -> float:
        """
        计算换手率

        Args:
            current_weights: 当前时刻权重
            previous_weights: 上一时刻权重

        Returns:
            换手率
        """
        if len(previous_weights) == 0:
            return 1.0  # 第一次建仓，换手率100%

        common_stocks = current_weights.index.intersection(previous_weights.index)
        turnover = 0.5 * np.sum(np.abs(current_weights.loc[common_stocks] - previous_weights.loc[common_stocks]))

        return float(turnover)

    @staticmethod
    def validate_factor(ic_dict: Dict, monotonicity_dict: Dict) -> Dict:
        """
        验证因子有效性

        Returns:
            验证结果
        """
        validation = {
            'is_valid': False,
            'passed_tests': [],
            'failed_tests': [],
            'scores': {},
        }

        # IC测试
        ic_abs = abs(ic_dict.get('ic_mean', 0))
        if ic_abs >= VALIDATION_THRESHOLDS['factor']['ic_abs']:
            validation['passed_tests'].append('IC绝对值')
            validation['scores']['ic_score'] = 1.0
        else:
            validation['failed_tests'].append(f'IC绝对值 ({ic_abs:.4f} < {VALIDATION_THRESHOLDS["factor"]["ic_abs"]})')
            validation['scores']['ic_score'] = ic_abs / VALIDATION_THRESHOLDS['factor']['ic_abs']

        # IR测试
        ir = ic_dict.get('ir', 0)
        if ir >= VALIDATION_THRESHOLDS['factor']['ir']:
            validation['passed_tests'].append('IR')
            validation['scores']['ir_score'] = 1.0
        else:
            validation['failed_tests'].append(f'IR ({ir:.4f} < {VALIDATION_THRESHOLDS["factor"]["ir"]})')
            validation['scores']['ir_score'] = ir / VALIDATION_THRESHOLDS['factor']['ir']

        # IC胜率测试
        ic_win_rate = ic_dict.get('ic_win_rate', 0)
        if ic_win_rate >= VALIDATION_THRESHOLDS['factor']['ic_win_rate']:
            validation['passed_tests'].append('IC胜率')
            validation['scores']['win_rate_score'] = 1.0
        else:
            validation['failed_tests'].append(f'IC胜率 ({ic_win_rate:.4f} < {VALIDATION_THRESHOLDS["factor"]["ic_win_rate"]})')
            validation['scores']['win_rate_score'] = ic_win_rate / VALIDATION_THRESHOLDS['factor']['ic_win_rate']

        # 单调性测试
        monotonicity = monotonicity_dict.get('monotonicity', 0)
        if monotonicity >= 0.6:  # 60%的组满足单调性
            validation['passed_tests'].append('单调性')
            validation['scores']['monotonicity_score'] = 1.0
        else:
            validation['failed_tests'].append(f'单调性 ({monotonicity:.4f} < 0.6)')
            validation['scores']['monotonicity_score'] = monotonicity / 0.6

        # 综合得分
        avg_score = np.mean(list(validation['scores'].values()))
        validation['final_score'] = float(avg_score)

        # 最终判断
        if avg_score >= 0.7 and len(validation['passed_tests']) >= 2:
            validation['is_valid'] = True

        return validation


class FactorValidator:
    """因子验证器"""

    def __init__(self, data_dir: str = 'data'):
        self.data_dir = data_dir
        self.metrics = InnovationMetrics()
        self.historical_data = None

    def load_data(self, start_date: str = '20200101', end_date: str = '20241231') -> pd.DataFrame:
        """加载历史数据"""
        data_file = os.path.join(self.data_dir, 'stock_data.pkl')

        if os.path.exists(data_file):
            logger.info(f"✓ 加载数据: {data_file}")
            with open(data_file, 'rb') as f:
                self.historical_data = pickle.load(f)

            # 过滤日期范围
            self.historical_data = self.historical_data[
                (self.historical_data['date'] >= pd.to_datetime(start_date)) &
                (self.historical_data['date'] <= pd.to_datetime(end_date))
            ].copy()

            logger.info(f"✓ 数据加载完成: {len(self.historical_data)} 条记录")
            return self.historical_data
        else:
            logger.warning(f"⚠ 数据文件不存在: {data_file}")
            logger.info("📥 请先运行 fetch_real_data.py 获取数据")
            return pd.DataFrame()

    def calculate_future_return(
        self,
        periods: int = 5,
        data: Optional[pd.DataFrame] = None
    ) -> pd.Series:
        """
        计算未来收益率

        Args:
            periods: 未来期数（5日=1周，20日=1月）
            data: 数据（如未指定使用self.historical_data）

        Returns:
            未来收益率序列（多层索引：日期×股票）
        """
        if data is None:
            data = self.historical_data

        if data is None or len(data) == 0:
            raise ValueError("请先加载历史数据")

        # 按股票分组计算收益率
        future_returns = []

        for stock_code in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock_code].sort_values('date').copy()

            # 计算未来收益率
            stock_data['close_pct_change'] = stock_data['close'].pct_change(periods=periods).shift(-periods)

            # 创建多层索引
            df = stock_data[['date', 'close_pct_change']].copy()
            df.index = pd.MultiIndex.from_arrays(
                [df['date'], [stock_code] * len(df)],
                names=['date', 'stock_code']
            )

            future_returns.append(df['close_pct_change'])

        # 合并所有股票
        result = pd.concat(future_returns).dropna()

        logger.info(f"✓ 计算{periods}日未来收益率: {len(result)} 条记录")

        return result

    def validate_factor_prototype(
        self,
        factor_func: Callable[[pd.DataFrame], pd.Series],
        factor_name: str,
        periods: int = 5,
        data: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        验证因子原型

        Args:
            factor_func: 因子计算函数
            factor_name: 因子名称
            periods: 收益率周期
            data: 数据

        Returns:
            验证结果
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🔬 验证因子原型: {factor_name}")
        logger.info(f"{'='*60}")

        if data is None:
            data = self.historical_data

        if data is None or len(data) == 0:
            return {'error': '数据未加载'}

        # 计算因子值
        logger.info(f"📊 计算{factor_name}...")
        factor_values = factor_func(data)

        # 计算未来收益率
        future_returns = self.calculate_future_return(periods=periods, data=data)

        # 对齐数据
        common_index = factor_values.index.intersection(future_returns.index)
        if len(common_index) == 0:
            return {'error': '因子值与收益率无法对齐'}

        factor_values_aligned = factor_values.loc[common_index]
        future_returns_aligned = future_returns.loc[common_index]

        # 计算IC指标
        logger.info(f"📈 计算IC指标...")
        ic_dict = self.metrics.calculate_ic(factor_values_aligned, future_returns_aligned)

        # 计算单调性
        logger.info(f"📉 计算单调性...")
        monotonicity_dict = self.metrics.calculate_monotonicity(factor_values_aligned, future_returns_aligned)

        # 验证因子
        logger.info(f"✅ 验证因子...")
        validation = self.metrics.validate_factor(ic_dict, monotonicity_dict)

        # 汇总结果
        result = {
            'factor_name': factor_name,
            'validation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ic_metrics': ic_dict,
            'monotonicity_metrics': monotonicity_dict,
            'validation': validation,
            'periods': periods,
        }

        # 打印结果
        self._print_validation_result(result)

        return result

    def _print_validation_result(self, result: Dict):
        """打印验证结果"""
        ic_dict = result['ic_metrics']
        mono_dict = result['monotonicity_metrics']
        validation = result['validation']

        print(f"\n【IC指标】")
        print(f"  IC均值: {ic_dict.get('ic_mean', 0):.4f}")
        print(f"  IC标准差: {ic_dict.get('ic_std', 0):.4f}")
        print(f"  IC绝对值: {ic_dict.get('ic_abs_mean', 0):.4f}")
        print(f"  IR (IC均值/标准差): {ic_dict.get('ir', 0):.4f}")
        print(f"  IC胜率: {ic_dict.get('ic_win_rate', 0):.2%}")
        print(f"  IC t值: {ic_dict.get('ic_t_stat', 0):.4f}")
        print(f"  IC p值: {ic_dict.get('ic_p_value', 0):.4f}")
        print(f"  期间数: {ic_dict.get('n_periods', 0)}")

        print(f"\n【单调性指标】")
        print(f"  单调性: {mono_dict.get('monotonicity', 0):.4f}")
        print(f"  多空收益: {mono_dict.get('long_short_return', 0):.4f}")
        print(f"  Spearman相关系数: {mono_dict.get('spearman_corr', 0):.4f}")
        print(f"  分组收益: {', '.join([f'{x:.4f}' for x in mono_dict.get('group_returns', [])])}")

        print(f"\n【验证结果】")
        print(f"  ✅ 通过测试: {', '.join(validation.get('passed_tests', []))}")
        print(f"  ❌ 未通过: {', '.join(validation.get('failed_tests', []))}")
        print(f"  📊 综合得分: {validation.get('final_score', 0):.4f}")
        print(f"  {'🟢 有效因子' if validation.get('is_valid') else '🔴 无效因子'}")


class InnovationDatabase:
    """创新数据库"""

    def __init__(self):
        self.factors_db_file = 'reports/innovation_factor_library.json'
        self.strategies_db_file = 'reports/innovation_strategy_library.json'
        self.experiments_dir = 'reports/innovation_experiments'

        # 创建目录
        os.makedirs(self.experiments_dir, exist_ok=True)

    def save_factor_experiment(self, experiment: Dict) -> str:
        """保存因子实验报告"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.experiments_dir}/factor_{experiment['factor_name']}_{timestamp}.json"

        # 保存到文件
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(experiment, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ 保存因子实验报告: {filename}")

        # 更新因子库
        self._update_factor_library(experiment)

        return filename

    def save_strategy_experiment(self, experiment: Dict) -> str:
        """保存策略实验报告"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.experiments_dir}/strategy_{experiment['strategy_name']}_{timestamp}.json"

        # 保存到文件
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(experiment, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ 保存策略实验报告: {filename}")

        # 更新策略库
        self._update_strategy_library(experiment)

        return filename

    def _update_factor_library(self, experiment: Dict):
        """更新因子库"""
        library = {}

        # 加载现有库
        if os.path.exists(self.factors_db_file):
            with open(self.factors_db_file, 'r', encoding='utf-8') as f:
                library = json.load(f)

        # 添加或更新因子
        factor_name = experiment['factor_name']
        library[factor_name] = {
            'name': factor_name,
            'description': experiment.get('description', ''),
            'category': experiment.get('category', '未分类'),
            'ic_mean': experiment['ic_metrics'].get('ic_mean', 0),
            'ir': experiment['ic_metrics'].get('ir', 0),
            'is_valid': experiment['validation'].get('is_valid', False),
            'final_score': experiment['validation'].get('final_score', 0),
            'last_test_date': experiment['validation_date'],
            'test_count': library.get(factor_name, {}).get('test_count', 0) + 1,
            'notes': experiment.get('notes', ''),
        }

        # 保存库
        with open(self.factors_db_file, 'w', encoding='utf-8') as f:
            json.dump(library, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ 更新因子库: {factor_name}")

    def _update_strategy_library(self, experiment: Dict):
        """更新策略库"""
        library = {}

        # 加载现有库
        if os.path.exists(self.strategies_db_file):
            with open(self.strategies_db_file, 'r', encoding='utf-8') as f:
                library = json.load(f)

        # 添加或更新策略
        strategy_name = experiment['strategy_name']
        library[strategy_name] = {
            'name': strategy_name,
            'description': experiment.get('description', ''),
            'category': experiment.get('category', '未分类'),
            'annual_return': experiment.get('annual_return', 0),
            'sharpe': experiment.get('sharpe', 0),
            'max_drawdown': experiment.get('max_drawdown', 0),
            'is_valid': experiment.get('is_valid', False),
            'last_test_date': experiment.get('test_date', ''),
            'test_count': library.get(strategy_name, {}).get('test_count', 0) + 1,
            'notes': experiment.get('notes', ''),
        }

        # 保存库
        with open(self.strategies_db_file, 'w', encoding='utf-8') as f:
            json.dump(library, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ 更新策略库: {strategy_name}")

    def get_factor_summary(self) -> pd.DataFrame:
        """获取因子库摘要"""
        if not os.path.exists(self.factors_db_file):
            return pd.DataFrame()

        with open(self.factors_db_file, 'r', encoding='utf-8') as f:
            library = json.load(f)

        df = pd.DataFrame.from_dict(library, orient='index')
        return df

    def get_strategy_summary(self) -> pd.DataFrame:
        """获取策略库摘要"""
        if not os.path.exists(self.strategies_db_file):
            return pd.DataFrame()

        with open(self.strategies_db_file, 'r', encoding='utf-8') as f:
            library = json.load(f)

        df = pd.DataFrame.from_dict(library, orient='index')
        return df


class InnovationLab:
    """创新实验室主类"""

    def __init__(self):
        self.validator = FactorValidator()
        self.database = InnovationDatabase()

    def explore_new_factor(
        self,
        factor_func: Callable[[pd.DataFrame], pd.Series],
        factor_name: str,
        description: str = '',
        category: str = '未分类',
        notes: str = '',
        periods: int = 5
    ) -> Dict:
        """
        探索新因子

        Args:
            factor_func: 因子计算函数，输入DataFrame，返回Series（多层索引：日期×股票）
            factor_name: 因子名称
            description: 因子描述
            category: 因子分类
            notes: 备注
            periods: 收益率周期

        Returns:
            验证结果
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 探索新因子: {factor_name}")
        logger.info(f"📝 描述: {description}")
        logger.info(f"📁 分类: {category}")
        logger.info(f"{'='*80}")

        # 验证因子
        result = self.validator.validate_factor_prototype(
            factor_func=factor_func,
            factor_name=factor_name,
            periods=periods
        )

        # 添加元数据
        result['description'] = description
        result['category'] = category
        result['notes'] = notes

        # 保存实验报告
        if 'error' not in result:
            self.database.save_factor_experiment(result)

        # 汇总创新统计
        self._generate_innovation_summary()

        return result

    def generate_innovation_report(self) -> str:
        """生成创新周报"""
        logger.info(f"\n📊 生成创新周报...")

        factor_summary = self.database.get_factor_summary()
        strategy_summary = self.database.get_strategy_summary()

        # 计算统计
        total_factors = len(factor_summary) if not factor_summary.empty else 0
        valid_factors = len(factor_summary[factor_summary['is_valid'] == True]) if not factor_summary.empty else 0
        innovation_rate = valid_factors / total_factors if total_factors > 0 else 0

        total_strategies = len(strategy_summary) if not strategy_summary.empty else 0
        valid_strategies = len(strategy_summary[strategy_summary['is_valid'] == True]) if not strategy_summary.empty else 0

        # 生成报告
        report = f"""# 量化创新周报

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 创新统计

### 因子创新
- 探索因子总数: {total_factors}
- 有效因子数: {valid_factors}
- 有效创新率: {innovation_rate:.2%}
- 目标准: {VALIDATION_THRESHOLDS['innovation']['success_rate']:.0%}

### 策略创新
- 探索策略总数: {total_strategies}
- 有效策略数: {valid_strategies}
- 有效性: {f"{valid_strategies/total_strategies:.2%}" if total_strategies > 0 else "N/A"}

## 🎯 本周目标完成情况

- [ ] 探索2个新因子 ({valid_factors >= 2 if total_factors >= 2 else '进行中'})
- [ ] 设计1个新策略 ({valid_strategies >= 1 if total_strategies >= 1 else '进行中'})
- [ ] 有效创新率 > 20% ({'✅' if innovation_rate >= VALIDATION_THRESHOLDS['innovation']['success_rate'] else '⚠️ 进行中'})

---

**下周计划**:
1. 继续探索新因子（关注学术前沿、另类数据）
2. 优化现有因子（降低换手率、提升IC稳定性）
3. 设计新策略（多策略融合、动态切换）
4. 深化创新评价机制
"""

        # 保存报告
        report_file = f"{self.database.experiments_dir}/weekly_report_{datetime.now().strftime('%Y%m%d')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"✓ 保存周报: {report_file}")
        print(report)

        return report

    def _generate_innovation_summary(self):
        """生成创新统计摘要"""
        factor_summary = self.database.get_factor_summary()
        strategy_summary = self.database.get_strategy_summary()

        if not factor_summary.empty:
            total_factors = len(factor_summary)
            valid_factors = len(factor_summary[factor_summary['is_valid'] == True])
            innovation_rate = valid_factors / total_factors if total_factors > 0 else 0

            print(f"\n📊 创新统计摘要:")
            print(f"  因子总数: {total_factors}")
            print(f"  有效因子: {valid_factors}")
            print(f"  创新率: {innovation_rate:.2%}")


# ============================================
# 示例因子函数（用于演示如何使用创新实验室）
# ============================================

def example_factor_momentum_20d(data: pd.DataFrame) -> pd.Series:
    """
    示例因子：20日动量因子

    输入: DataFrame（包含date, stock_code, close列）
    输出: Series（多层索引：日期×股票）
    """
    factors = []

    for stock_code in data['stock_code'].unique():
        stock_data = data[data['stock_code'] == stock_code].sort_values('date').copy()

        # 计算20日动量
        stock_data['momentum_20'] = stock_data['close'].pct_change(20)

        # 创建多层索引
        df = stock_data[['date', 'momentum_20']].copy()
        df.index = pd.MultiIndex.from_arrays(
            [df['date'], [stock_code] * len(df)],
            names=['date', 'stock_code']
        )

        factors.append(df['momentum_20'])

    return pd.concat(factors).dropna()


def example_factor_volatility_20d(data: pd.DataFrame) -> pd.Series:
    """
    示例因子：20日波动率因子的倒数（低波动因子）

    输入: DataFrame（包含date, stock_code, close列）
    输出: Series（多层索引：日期×股票）
    """
    factors = []

    for stock_code in data['stock_code'].unique():
        stock_data = data[data['stock_code'] == stock_code].sort_values('date').copy()

        # 计算20日收益率和波动率
        stock_data['return'] = stock_data['close'].pct_change(1)
        stock_data['volatility_20'] = stock_data['return'].rolling(20).std()
        stock_data['volatility_20_inv'] = 1.0 / (stock_data['volatility_20'] + 1e-6)

        # 创建多层索引
        df = stock_data[['date', 'volatility_20_inv']].copy()
        df.index = pd.MultiIndex.from_arrays(
            [df['date'], [stock_code] * len(df)],
            names=['date', 'stock_code']
        )

        factors.append(df['volatility_20_inv'])

    return pd.concat(factors).dropna()


# ============================================
# 主程序入口
# ============================================

if __name__ == '__main__':
    # 创建创新实验室
    lab = InnovationLab()

    # 加载数据
    lab.validator.load_data(start_date='20200101', end_date='20241231')

    # 探索新因子 - 示例
    if len(lab.validator.historical_data) > 0:
        print("\n" + "="*80)
        print("🔬 开始因子创新实验")
        print("="*80)

        # 实验1：20日动量因子
        lab.explore_new_factor(
            factor_func=example_factor_momentum_20d,
            factor_name='momentum_20d',
            description='20日价格动量',
            category='技术面因子',
            notes='典型的趋势跟踪因子，用于测试实验室功能',
            periods=5
        )

        # 实验2：20日低波动因子倒数
        lab.explore_new_factor(
            factor_func=example_factor_volatility_20d,
            factor_name='volatility_20d_inv',
            description='20日波动率倒数（低波动因子）',
            category='技术面因子',
            notes='低波动异象，用于测试实验室功能',
            periods=5
        )

        # 生成创新周报
        print("\n" + "="*80)
        print("📊 生成创新周报")
        print("="*80)
        lab.generate_innovation_report()
    else:
        logger.warning("⚠️ 数据未加载，请先运行 fetch_real_data.py 获取数据")
