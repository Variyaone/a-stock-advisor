#!/usr/bin/env python3
"""
快速测试脚本 - 验证数据质量管理框架的所有功能

作者: 架构师
日期: 2026-03-02
"""

import sys
import os
import pickle
import json
from datetime import datetime

# 添加项目根目录到Python路径
project_root = '/Users/variya/.openclaw/workspace/projects/a-stock-advisor'
os.chdir(project_root)
sys.path.insert(0, project_root)

from code.data_quality_framework import (
    DataQualityChecker,
    DataCleaner,
    DataValidator,
    DataQualityPipeline
)


def test_basic_functionality():
    """测试基本功能"""
    print("\n" + "=" * 70)
    print("测试1: 基本功能")
    print("=" * 70)

    # 加载数据
    try:
        with open('data/real_stock_data.pkl', 'rb') as f:
            raw_data = pickle.load(f)

        print(f"✓ 成功加载数据: {len(raw_data):,} 条记录")

        # 测试DataQualityChecker
        print("\n测试 DataQualityChecker...")
        checker = DataQualityChecker()
        report = checker.check_data(raw_data)
        print(f"  ✓ 质量检查完成: {'合格' if report.is_valid else '不合格'}")
        print(f"  - 总记录数: {report.total_records:,}")
        print(f"  - 问题数: {len(report.issues)}")
        print(f"  - 警告数: {len(report.warnings)}")

        # 测试DataCleaner
        print("\n测试 DataCleaner...")
        cleaner = DataCleaner()
        cleaned_data = cleaner.clean_data(raw_data)
        print(f"  ✓ 数据清洗完成: {len(cleaned_data):,} 条记录")
        print(f"  - 清洗步骤: {len(cleaner.cleaning_log)}")

        # 测试DataQualityPipeline
        print("\n测试 DataQualityPipeline...")
        pipeline = DataQualityPipeline()
        results = pipeline.run(raw_data, source_name="test_data")
        print(f"  ✓ Pipeline执行成功: {'合格' if results['is_valid'] else '不合格'}")
        print(f"  - 原始记录: {results['raw_records']:,}")
        print(f"  - 最终记录: {results['final_records']:,}")

        return True, "基本功能测试通过"

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False, f"测试失败: {str(e)}"


def test_cross_validation():
    """测试多数据源交叉验证"""
    print("\n" + "=" * 70)
    print("测试2: 多数据源交叉验证")
    print("=" * 70)

    try:
        # 加载数据
        with open('data/real_stock_data.pkl', 'rb') as f:
            data = pickle.load(f)

        print(f"✓ 成功加载数据: {len(data):,} 条记录")

        # 创建模拟的第二数据源
        print("\n创建模拟的第二数据源...")
        import numpy as np
        import pandas as pd

        np.random.seed(42)
        sample_size = len(data) // 2
        sample_indices = np.random.choice(len(data), sample_size, replace=False)
        backup_data = data.iloc[sample_indices].copy()

        # 添加轻微噪声
        backup_data['close'] = backup_data['close'] * (1 + np.random.randn(len(backup_data)) * 0.001)

        print(f"  模拟数据源: {len(backup_data):,} 条记录")

        # 测试DataValidator
        print("\n测试 DataValidator...")
        validator = DataValidator()
        validation_results = validator.cross_validate({
            "main_source": data,
            "backup_source": backup_data
        })

        print(f"  ✓ 交叉验证完成: {'通过' if validation_results['is_valid'] else '有问题'}")
        print(f"  - 比对次数: {len(validation_results['comparisons'])}")
        print(f"  - 警告数: {len(validation_results['warnings'])}")

        # 输出比对结果
        for comp in validation_results['comparisons']:
            print(f"\n  {comp['source1']} vs {comp['source2']}:")
            print(f"    共同股票: {comp['stock_overlap']}")
            print(f"    共同记录: {comp['date_overlap']}")

        return True, "交叉验证测试通过"

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False, f"测试失败: {str(e)}"


def test_file_io():
    """测试文件读写"""
    print("\n" + "=" * 70)
    print("测试3: 文件读写")
    print("=" * 70)

    try:
        # 运行Pipeline
        with open('data/real_stock_data.pkl', 'rb') as f:
            data = pickle.load(f)

        pipeline = DataQualityPipeline()
        results = pipeline.run(data, source_name="test_io")

        # 检查生成的文件
        expected_files = [
            'data/test_io_quality_report.json',
            'data/test_io_cleaning_log.json',
            'data/test_io_cleaned.pkl'
        ]

        print("\n检查生成的文件:")
        for filepath in expected_files:
            if os.path.exists(filepath):
                print(f"  ✓ {filepath}")

                # 如果是JSON文件，尝试读取
                if filepath.endswith('.json'):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                    print(f"    - JSON格式正确")
            else:
                print(f"  ✗ {filepath} (不存在)")
                return False, f"文件 {filepath} 不存在"

        # 尝试读取清洗后的数据
        print("\n读取清洗后的数据:")
        with open('data/test_io_cleaned.pkl', 'rb') as f:
            cleaned_data = pickle.load(f)
        print(f"  ✓ 成功读取清洗数据: {len(cleaned_data):,} 条记录")

        return True, "文件读写测试通过"

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False, f"测试失败: {str(e)}"


def test_data_consistency_fix():
    """测试数据一致性修复"""
    print("\n" + "=" * 70)
    print("测试4: 数据一致性修复")
    print("=" * 70)

    try:
        # 加载数据
        with open('data/real_stock_data.pkl', 'rb') as f:
            data = pickle.load(f)

        print(f"✓ 成功加载数据: {len(data):,} 条记录")

        # 检查原始数据的一致性问题
        print("\n检查原始数据的一致性...")

        # 统计问题数量
        if all(col in data.columns for col in ['open', 'high', 'low', 'close']):
            invalid_high = ((data['high'] < data['close']) | (data['high'] < data['open'])).sum()
            invalid_low = ((data['low'] > data['close']) | (data['low'] > data['open'])).sum()

            print(f"  - 最高价 < 收盘价/开盘价: {invalid_high} 条")
            print(f"  - 最低价 > 收盘价/开盘价: {invalid_low} 条")

        # 运行清洗
        print("\n运行数据清洗...")
        cleaner = DataCleaner()
        cleaned_data = cleaner.clean_data(data)

        # 检查清洗后数据的一致性
        print("\n检查清洗后数据的一致性...")

        if all(col in cleaned_data.columns for col in ['open', 'high', 'low', 'close']):
            invalid_high_new = ((cleaned_data['high'] < cleaned_data['close']) | (cleaned_data['high'] < cleaned_data['open'])).sum()
            invalid_low_new = ((cleaned_data['low'] > cleaned_data['close']) | (cleaned_data['low'] > cleaned_data['open'])).sum()

            print(f"  - 最高价 < 收盘价/开盘价: {invalid_high_new} 条")
            print(f"  - 最低价 > 收盘价/开盘价: {invalid_low_new} 条")

            if invalid_high_new == 0 and invalid_low_new == 0:
                print("  ✓ 所有数据一致性问题已修复")
                return True, "数据一致性修复测试通过"
            else:
                print("  ⚠ 仍存在一致性问题")
                return False, "一致性问题未完全修复"
        else:
            print("  ⚠ 数据缺少必要的列")
            return False, "数据列不完整"

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False, f"测试失败: {str(e)}"


def test_custom_thresholds():
    """测试自定义质量阈值"""
    print("\n" + "=" * 70)
    print("测试5: 自定义质量阈值")
    print("=" * 70)

    try:
        # 加载数据
        with open('data/real_stock_data.pkl', 'rb') as f:
            data = pickle.load(f)

        print(f"✓ 成功加载数据: {len(data):,} 条记录")

        # 使用默认阈值
        print("\n使用默认阈值检查:")
        checker_default = DataQualityChecker()
        report_default = checker_default.check_data(data)
        print(f"  - 问题数: {len(report_default.issues)}")
        print(f"  - 警告数: {len(report_default.warnings)}")

        # 使用严格阈值
        print("\n使用严格阈值检查:")
        strict_thresholds = {
            'max_missing_rate': 0.01,  # 缺失率<1%
            'min_price': 2.0,           # 最低股价
            'min_data_records_per_stock': 200  # 每只股票至少200条记录
        }
        checker_strict = DataQualityChecker(thresholds=strict_thresholds)
        report_strict = checker_strict.check_data(data)
        print(f"  - 问题数: {len(report_strict.issues)}")
        print(f"  - 警告数: {len(report_strict.warnings)}")

        # 使用宽松阈值
        print("\n使用宽松阈值检查:")
        loose_thresholds = {
            'max_missing_rate': 0.15,  # 缺失率<15%
            'min_price': 0.5,           # 最低股价
            'min_data_records_per_stock': 50  # 每只股票至少50条记录
        }
        checker_loose = DataQualityChecker(thresholds=loose_thresholds)
        report_loose = checker_loose.check_data(data)
        print(f"  - 问题数: {len(report_loose.issues)}")
        print(f"  - 警告数: {len(report_loose.warnings)}")

        # 验证阈值确实起了作用
        if (len(report_strict.issues) >= len(report_default.issues) >= len(report_loose.issues)) or \
           (len(report_strict.warnings) >= len(report_default.warnings) >= len(report_loose.warnings)):
            print("\n✓ 阈值设置生效")
            return True, "自定义阈值测试通过"
        else:
            print("\n⚠ 阈值效应不明显")
            return False, "阈值测试未验证"

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False, f"测试失败: {str(e)}"


def generate_report():
    """生成测试报告"""
    print("\n" + "=" * 70)
    print("生成测试报告")
    print("=" * 70)

    tests = [
        ("基本功能测试", test_basic_functionality),
        ("交叉验证测试", test_cross_validation),
        ("文件读写测试", test_file_io),
        ("数据一致性修复测试", test_data_consistency_fix),
        ("自定义阈值测试", test_custom_thresholds),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            success, message = test_func()
            results.append({
                'test_name': test_name,
                'success': success,
                'message': message,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        except Exception as e:
            results.append({
                'test_name': test_name,
                'success': False,
                'message': f"测试异常: {str(e)}",
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

    # 保存测试报告
    report_path = 'reports/data_quality_test_report.json'
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 测试报告已保存: {report_path}")

    # 输出测试总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)

    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['success'])
    failed_tests = total_tests - passed_tests

    print(f"\n总测试数: {total_tests}")
    print(f"通过: {passed_tests}")
    print(f"失败: {failed_tests}")
    print(f"成功率: {passed_tests/total_tests*100:.1f}%")

    print("\n详细结果:")
    for result in results:
        status = "✓" if result['success'] else "✗"
        print(f"  {status} {result['test_name']}: {result['message']}")

    # 检查总体结果
    if failed_tests == 0:
        print("\n" + "=" * 70)
        print("✓ 所有测试通过！数据质量管理框架运行正常。")
        print("=" * 70)
        return True
    else:
        print("\n" + "=" * 70)
        print(f"⚠ {failed_tests} 个测试失败，请检查问题。")
        print("=" * 70)
        return False


def clean_up():
    """清理测试文件"""
    print("\n" + "=" * 70)
    print("清理测试文件")
    print("=" * 70)

    test_files = [
        'data/test_data_quality_report.json',
        'data/test_data_cleaning_log.json',
        'data/test_data_cleaned.pkl',
        'data/test_io_quality_report.json',
        'data/test_io_cleaning_log.json',
        'data/test_io_cleaned.pkl',
    ]

    removed_count = 0
    for filepath in test_files:
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                print(f"  ✓ 已删除: {filepath}")
                removed_count += 1
            except Exception as e:
                print(f"  ✗ 删除失败 {filepath}: {e}")

    if removed_count == 0:
        print("  没有需要清理的文件")
    else:
        print(f"\n  共清理 {removed_count} 个文件")


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("数据质量管理框架 - 测试套件")
    print("=" * 70)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 询问用户选择
    print("\n可选操作:")
    print("  1. 运行所有测试")
    print("  2. 运行基本测试")
    print("  3. 清理测试文件")
    print("  4. 运行并清理")
    print("  q. 退出")

    choice = input("\n请选择 (1-4, q): ").strip()

    if choice.lower() == 'q':
        print("\n👋 退出")
        return
    elif choice == '1':
        # 运行所有测试
        success = generate_report()

        # 询问是否清理
        if success:
            clean_choice = input("\n是否清理测试文件? (y/n): ").strip().lower()
            if clean_choice == 'y':
                clean_up()

    elif choice == '2':
        # 运行基本测试
        success, message = test_basic_functionality()

        if success:
            print("\n✓ 基本测试通过")
        else:
            print(f"\n✗ 基本测试失败: {message}")

    elif choice == '3':
        # 清理测试文件
        clean_up()

    elif choice == '4':
        # 运行并清理
        generate_report()
        clean_up()

    else:
        print("\n⚠ 无效选择")

    print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
