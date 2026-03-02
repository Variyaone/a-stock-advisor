#!/usr/bin/env python3
"""
数据质量管理框架使用示例
展示各种使用场景和最佳实践

作者: 架构师
日期: 2026-03-02
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from code.data_quality_framework import (
    DataQualityChecker,
    DataCleaner,
    DataValidator,
    DataQualityPipeline
)
import pickle
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def example_1_basic_check():
    """示例1: 基本数据质量检查"""
    print("\n" + "=" * 70)
    print("示例1: 基本数据质量检查")
    print("=" * 70)

    # 加载数据
    try:
        with open('data/real_stock_data.pkl', 'rb') as f:
            data = pickle.load(f)

        print(f"\n✓ 成功加载数据: {len(data):,} 条记录")

        # 执行质量检查
        checker = DataQualityChecker()
        report = checker.check_data(data)

        # 输出结果
        print(f"\n数据质量结果: {'✓ 合格' if report.is_valid else '⚠ 不合格'}")
        print(f"\n问题 ({len(report.issues)} 个):")
        for issue in report.issues:
            print(f"  • {issue}")

        print(f"\n警告 ({len(report.warnings)} 个):")
        for warning in report.warnings[:5]:  # 只显示前5个
            print(f"  • {warning}")

        if 'stock_data_coverage' in report.stock_data_coverage:
            cov = report.stock_data_coverage
            print(f"\n数据覆盖度:")
            print(f"  • 股票总数: {cov['total_stocks']}")
            print(f"  • 平均每只股票记录数: {cov['avg_records_per_stock']}")
            print(f"  • 最少记录数: {cov['min_records']}")
            print(f"  • 最多记录数: {cov['max_records']}")

    except FileNotFoundError:
        print("✗ 未找到数据文件 data/real_stock_data.pkl")


def example_2_data_cleaning():
    """示例2: 数据清洗"""
    print("\n" + "=" * 70)
    print("示例2: 数据清洗")
    print("=" * 70)

    # 加载数据
    try:
        with open('data/real_stock_data.pkl', 'rb') as f:
            data = pickle.load(f)

        print(f"\n原始数据: {len(data):,} 条记录")
        print(f"列名: {list(data.columns)}")

        # 执行清洗
        cleaner = DataCleaner()
        cleaned_data = cleaner.clean_data(data)

        print(f"\n清洗后数据: {len(cleaned_data):,} 条记录")
        print(f"新列名: {list(cleaned_data.columns)}")

        # 显示清洗日志
        print(f"\n清洗步骤 ({len(cleaner.cleaning_log)} 个):")
        for step in cleaner.cleaning_log:
            print(f"  • {step}")

    except FileNotFoundError:
        print("✗ 未找到数据文件 data/real_stock_data.pkl")
    except Exception as e:
        print(f"✗ 清洗失败: {e}")


def example_3_full_pipeline():
    """示例3: 完整Pipeline"""
    print("\n" + "=" * 70)
    print("示例3: 完整数据质量Pipeline")
    print("=" * 70)

    # 加载数据
    try:
        with open('data/real_stock_data.pkl', 'rb') as f:
            data = pickle.load(f)

        print(f"\n✓ 成功加载数据: {len(data):,} 条记录")

        # 运行Pipeline
        pipeline = DataQualityPipeline()
        results = pipeline.run(data, source_name="example_data")

        # 输出结果
        print(f"\n{'='*70}")
        print("Pipeline执行结果:")
        print(f"{'='*70}")
        print(f"数据源: {results['source_name']}")
        print(f"原始记录: {results['raw_records']:,}")
        print(f"最终记录: {results['final_records']:,}")
        print(f"状态: {'✓ 成功' if results['is_valid'] else '⚠ 存在问题'}")

        if 'steps' in results:
            print("\n质量检查:")
            qc = results['steps']['quality_check']
            print(f"  是否合格: {qc['is_valid']}")
            print(f"  问题数: {qc['issues_count']}")
            print(f"  警告数: {qc['warnings_count']}")

            print("\n数据清洗:")
            cl = results['steps']['cleaning']
            print(f"  清洗后记录: {cl['cleaned_records']:,}")
            print(f"  清洗步骤: {cl['cleaning_steps']}")

        # 显示生成的文件
        print("\n生成的文件:")
        if os.path.exists('data/example_data_quality_report.json'):
            print("  ✓ data/example_data_quality_report.json")
        if os.path.exists('data/example_data_cleaning_log.json'):
            print("  ✓ data/example_data_cleaning_log.json")
        if os.path.exists('data/example_data_cleaned.pkl'):
            print("  ✓ data/example_data_cleaned.pkl")

    except FileNotFoundError:
        print("✗ 未找到数据文件 data/real_stock_data.pkl")
    except Exception as e:
        print(f"✗ Pipeline执行失败: {e}")
        import traceback
        print(traceback.format_exc())


def example_4_load_cleaned_data():
    """示例4: 加载和检查清洗后的数据"""
    print("\n" + "=" * 70)
    print("示例4: 加载清洗后的数据")
    print("=" * 70)

    # 尝试加载清洗后的数据
    cleaned_files = [
        'data/example_data_cleaned.pkl',
        'data/akshare_real_data_cleaned.pkl',
        'data/real_stock_data_cleaned.pkl'
    ]

    for filepath in cleaned_files:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as f:
                    cleaned_data = pickle.load(f)

                print(f"\n✓ 成功加载: {filepath}")
                print(f"  记录数: {len(cleaned_data):,}")
                print(f"  股票数: {cleaned_data['ts_code'].nunique()}")
                print(f"  日期范围: {cleaned_data['trade_date'].min()} ~ {cleaned_data['trade_date'].max()}")

                # 检查字段
                print(f"  字段: {list(cleaned_data.columns)}")

                # 显示前几条记录
                print(f"\n  前5条记录:")
                print(cleaned_data.head().to_string(index=False))

                break
            except Exception as e:
                print(f"✗ 加载 {filepath} 失败: {e}")
    else:
        print("✗ 未找到清洗后的数据文件")
        print("  请先运行示例3生成清洗后的数据")


def example_5_multiple_sources():
    """示例5: 模拟多数据源交叉验证"""
    print("\n" + "=" * 70)
    print("示例5: 多数据源交叉验证（模拟）")
    print("=" * 70)

    # 加载数据
    try:
        with open('data/real_stock_data.pkl', 'rb') as f:
            main_data = pickle.load(f)

        print(f"\n✓ 成功加载数据: {len(main_data):,} 条记录")

        # 模拟第二个数据源（取主数据源的50%并添加一些噪声）
        print("\n创建模拟的第二数据源...")
        import numpy as np

        np.random.seed(42)
        sample_size = len(main_data) // 2
        sample_indices = np.random.choice(len(main_data), sample_size, replace=False)

        backup_data = main_data.iloc[sample_indices].copy()

        # 添加一些噪声
        backup_data['close'] = backup_data['close'] * (1 + np.random.randn(len(backup_data)) * 0.001)

        print(f"  模拟数据源记录数: {len(backup_data):,}")

        # 运行交叉验证
        validator = DataValidator()
        results = validator.cross_validate({
            "main_source": main_data,
            "backup_source": backup_data
        })

        # 输出结果
        print(f"\n交叉验证结果: {'✓ 通过' if results['is_valid'] else '⚠ 有问题'}")

        print(f"\n对比结果 ({len(results['comparisons'])} 个):")
        for comp in results['comparisons']:
            print(f"  {comp['source1']} vs {comp['source2']}:")
            print(f"    共同股票: {comp['stock_overlap']}")
            print(f"    共同记录: {comp['date_overlap']}")

            if 'price_diff_stats' in comp and comp['price_diff_stats']:
                print(f"    价格差异:")
                for col, stats in comp['price_diff_stats'].items():
                    print(f"      {col}: 平均差={stats['mean_diff']:.4f}, 最大差={stats['max_abs_diff']:.4f}")

            if 'issues' in comp and comp['issues']:
                print(f"    问题: {comp['issues']}")

        print(f"\n警告 ({len(results['warnings'])} 个):")
        for warning in results['warnings']:
            print(f"  • {warning}")

        print(f"\n建议:")
        for recommendation in results['recommendations']:
            print(f"  • {recommendation}")

    except FileNotFoundError:
        print("✗ 未找到数据文件 data/real_stock_data.pkl")
    except Exception as e:
        print(f"✗ 交叉验证失败: {e}")
        import traceback
        print(traceback.format_exc())


def example_6_custom_thresholds():
    """示例6: 自定义质量阈值"""
    print("\n" + "=" * 70)
    print("示例6: 自定义质量阈值（更严格的检查）")
    print("=" * 70)

    # 加载数据
    try:
        with open('data/real_stock_data.pkl', 'rb') as f:
            data = pickle.load(f)

        print(f"\n✓ 成功加载数据: {len(data):,} 条记录")

        # 定义更严格的质量阈值
        custom_thresholds = {
            'max_missing_rate': 0.02,  # 缺失率不超过2%（默认5%）
            'max_price_change': 0.15,  # 涨跌幅不超过15%（默认20%）
            'min_price': 2.0,           # 最低股价（默认1.0）
            'min_data_records_per_stock': 200  # 每只股票至少200条记录（默认100）
        }

        print("\n自定义质量阈值:")
        for key, value in custom_thresholds.items():
            print(f"  {key}: {value}")

        # 使用自定义阈值执行检查
        checker = DataQualityChecker(thresholds=custom_thresholds)
        report = checker.check_data(data)

        # 输出结果
        print(f"\n数据质量结果: {'✓ 合格' if report.is_valid else '⚠ 不合格'}")

        print(f"\n问题 ({len(report.issues)} 个):")
        for issue in report.issues:
            print(f"  • {issue}")

        print(f"\n警告 ({len(report.warnings)} 个):")
        for warning in report.warnings[:5]:
            print(f"  • {warning}")

    except FileNotFoundError:
        print("✗ 未找到数据文件 data/real_stock_data.pkl")
    except Exception as e:
        print(f"✗ 检查失败: {e}")


def example_7_analyze_cleaning_log():
    """示例7: 分析清洗日志"""
    print("\n" + "=" * 70)
    print("示例7: 分析清洗日志")
    print("=" * 70)

    # 尝试加载清洗日志
    log_files = [
        'data/example_data_cleaning_log.json',
        'data/akshare_real_data_cleaning_log.json'
    ]

    for filepath in log_files:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    log = json.load(f)

                print(f"\n✓ 成功加载: {filepath}")
                print(f"\n清洗统计:")
                print(f"  最终记录数: {log['final_records']:,}")
                print(f"  清洗步骤数: {len(log['cleaning_log'])}")

                print(f"\n清洗步骤详情:")
                for i, step in enumerate(log['cleaning_log'], 1):
                    print(f"\n  步骤 {i}: {step['step']}")
                    for key, value in step.items():
                        if key != 'step':
                            print(f"    {key}: {value}")

                break
            except Exception as e:
                print(f"✗ 加载 {filepath} 失败: {e}")
    else:
        print("✗ 未找到清洗日志文件")
        print("  请先运行示例3生成清洗日志")


def example_8_batch_processing():
    """示例8: 分批处理大数据集"""
    print("\n" + "=" * 70)
    print("示例8: 分批处理大数据集")
    print("=" * 70)

    # 加载数据
    try:
        with open('data/real_stock_data.pkl', 'rb') as f:
            data = pickle.load(f)

        print(f"\n✓ 成功加载数据: {len(data):,} 条记录")

        # 分批大小
        batch_size = 100000
        print(f"\n分批大小: {batch_size:,}")

        # 清洗器
        cleaner = DataCleaner()

        # 分批处理
        cleaned_batches = []
        total_batches = (len(data) + batch_size - 1) // batch_size

        print(f"\n开始分批处理...")
        print(f"总批次数: {total_batches}")

        for i in range(0, len(data), batch_size):
            batch_num = i // batch_size + 1
            print(f"  处理第 {batch_num}/{total_batches} 批 ({len(data[i:i+batch_size]):,} 条)...")

            try:
                cleaned_batch = cleaner.clean_data(data.iloc[i:i+batch_size])
                cleaned_batches.append(cleaned_batch)
                print(f"    ✓ 完成")
            except Exception as e:
                print(f"    ✗ 失败: {e}")

        # 合并结果
        if cleaned_batches:
            final_data = pd.concat(cleaned_batches, ignore_index=True)
            print(f"\n✓ 分批处理完成: {len(final_data):,} 条记录")
        else:
            print("\n✗ 没有成功处理任何批次")

    except FileNotFoundError:
        print("✗ 未找到数据文件 data/real_stock_data.pkl")
    except Exception as e:
        print(f"✗ 分批处理失败: {e}")
        import traceback
        print(traceback.format_exc())


def main():
    """主函数 - 运行所有示例"""
    print("\n" + "=" * 70)
    print("数据质量管理框架 - 使用示例集合")
    print("=" * 70)

    examples = [
        ("1. 基本数据质量检查", example_1_basic_check),
        ("2. 数据清洗", example_2_data_cleaning),
        ("3. 完整Pipeline", example_3_full_pipeline),
        ("4. 加载清洗后的数据", example_4_load_cleaned_data),
        ("5. 多数据源交叉验证（模拟）", example_5_multiple_sources),
        ("6. 自定义质量阈值", example_6_custom_thresholds),
        ("7. 分析清洗日志", example_7_analyze_cleaning_log),
        ("8. 分批处理大数据集", example_8_batch_processing),
    ]

    print("\n可用示例:")
    for i, (desc, _) in enumerate(examples, 1):
        print(f"  {i}. {desc}")

    print(f"\n  0. 运行所有示例")
    print(f"  q. 退出")

    while True:
        choice = input("\n请选择示例 (0-8, q): ").strip()

        if choice.lower() == 'q':
            print("\n👋 再见！")
            break
        elif choice == '0':
            print("\n运行所有示例...")
            for _, func in examples:
                try:
                    func()
                except Exception as e:
                    print(f"\n✗ 示例执行失败: {e}")
        elif choice.isdigit() and 1 <= int(choice) <= len(examples):
            idx = int(choice) - 1
            try:
                examples[idx][1]()
            except Exception as e:
                print(f"\n✗ 示例执行失败: {e}")
        else:
            print("\n⚠ 无效选择，请重新输入")


if __name__ == '__main__':
    import pandas as pd
    main()
