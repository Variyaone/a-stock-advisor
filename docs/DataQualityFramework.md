# 数据质量管理框架文档

## 概述

数据质量管理框架（DataQualityFramework）是一个完整的A股数据质量管理和处理系统，提供以下核心功能：

1. **数据质量检查** - 检测缺失值、异常值、数据一致性
2. **数据清洗** - 标准化字段名、处理停牌数据、修复数据问题
3. **交叉验证** - 多数据源对比、差异识别、可信度评分
4. **自动化Pipeline** - 端到端的数据处理流程

## 核心组件

### 1. DataQualityChecker（数据质量检查器）

检测以下问题：
- **缺失值检测**：关键字段缺失率检查
- **异常值检测**：
  - 价格异常（过高或过低）
  - 涨跌幅异常（超过±20%）
  - 成交量异常
- **数据一致性检查**：
  - 开高低收盘的逻辑关系
  - 重复记录检测
- **数据覆盖度检查**：
  - 每只股票的数据量
  - 股票池覆盖范围

### 2. DataCleaner（数据清洗器）

执行以下清洗操作：
- **字段标准化**：统一列名（ts_code, trade_date, open, high, low, close, volume等）
- **缺失值处理**：
  - 关键字段缺失 → 删除该记录
  - 数值字段缺失 → 填充为0
- **异常值处理**：
  - 过高/过低价格 → 限制在合理范围内（1.0 - 3000.0）
- **停牌数据标记**：识别并标记停牌股票
- **数据一致性修复**：
  - 修正开高低收盘关系（high >= max(open, close), low <= min(open, close)）
  - 去除重复记录

### 3. DataValidator（交叉验证器）

支持多数据源对比：
- 找出不同数据源间的差异
- 计算价格、成交量的差异统计
- 生成数据源可信度评分
- 提供数据源选择建议

### 4. DataQualityPipeline（自动化Pipeline）

端到端的数据处理流程：
```
原始数据 → 质量检查 → 数据清洗 → 交叉验证 → 输出清洗数据
```

## 使用方法

### 基本使用

```python
from code.data_quality_framework import DataQualityPipeline
import pickle

# 加载数据
with open('data/real_stock_data.pkl', 'rb') as f:
    raw_data = pickle.load(f)

# 运行Pipeline
pipeline = DataQualityPipeline()
results = pipeline.run(raw_data, source_name="akshare_real_data")

# 查看结果
print(f"原始记录: {results['raw_records']:,}")
print(f"最终记录: {results['final_records']:,}")
print(f"是否合格: {results['is_valid']}")
```

### 多数据源交叉验证

```python
from code.data_quality_framework import DataQualityPipeline
import pickle

# 加载多个数据源
with open('data/akshare_data.pkl', 'rb') as f:
    akshare_data = pickle.load(f)

with open('data/tushare_data.pkl', 'rb') as f:
    tushare_data = pickle.load(f)

# 运行Pipeline并进行交叉验证
pipeline = DataQualityPipeline()
results = pipeline.run(
    akshare_data,
    source_name="akshare",
    cross_validate_with={
        "tushare": tushare_data
    }
)

# 查看交叉验证结果
validation = results['steps']['cross_validation']
print(f"交叉验证通过: {validation['is_valid']}")
print(f"警告: {validation['warnings']}")
```

### 单独使用组件

```python
from code.data_quality_framework import DataQualityChecker, DataCleaner

# 质量检查
checker = DataQualityChecker()
quality_report = checker.check_data(raw_data)
print(f"数据质量: {'合格' if quality_report.is_valid else '不合格'}")
print(f"问题: {quality_report.issues}")

# 数据清洗
cleaner = DataCleaner()
cleaned_data = cleaner.clean_data(raw_data)
print(f"清洗后记录数: {len(cleaned_data)}")
```

## 核心配置

### 质量阈值配置

可以在 `QUALITY_THRESHOLDS` 中配置：

```python
QUALITY_THRESHOLDS = {
    'max_missing_rate': 0.05,          # 最大缺失率阈值（5%）
    'max_price_change': 0.2,           # 最大涨跌幅（20%，考虑涨跌停）
    'min_price': 1.0,                  # 最低股价
    'max_price': 3000.0,               # 最高股价
    'min_volume': 0,                   # 最小成交量
    'min_amount': 1000000,            # 最小成交额（100万）
    'min_data_records_per_stock': 100, # 每只股票最少记录数
}
```

### 标准字段名称

Framework会自动将各种命名转换为标准名称：

```python
STANDARD_COLUMNS = {
    '股票代码': 'ts_code',
    'code': 'ts_code',
    '日期': 'trade_date',
    'date': 'trade_date',
    '开盘': 'open',
    '收盘': 'close',
    '最高': 'high',
    '最低': 'low',
    '成交量': 'volume',
    '成交额': 'amount',
    '涨跌幅': 'change_pct',
    '换手率': 'turnover',
}
```

## 输出文件

运行Pipeline后会生成以下文件：

```
data/
├── {source_name}_quality_report.json    # 质量检查报告
├── {source_name}_cleaning_log.json      # 清洗日志
└── {source_name}_cleaned.pkl            # 清洗后的数据
```

### 质量报告示例

```json
{
  "is_valid": true,
  "total_records": 307975,
  "missing_values": {},
  "missing_rate": {},
  "outlier_records": 66,
  "stock_data_coverage": {
    "total_stocks": 50,
    "avg_records_per_stock": 6159,
    "min_records": 200,
    "max_records": 1200,
    "stocks_with_low_coverage": 0
  },
  "issues": [],
  "warnings": []
}
```

### 清洗日志示例

```json
{
  "cleaning_log": [
    {
      "step": "rename_columns",
      "changes": {
        "stock_code": "ts_code",
        "date": "trade_date"
      }
    },
    {
      "step": "remove_duplicates",
      "removed": 307975
    }
  ],
  "final_records": 307975
}
```

## 质量检查项目详解

### 1. 缺失值检测

检查关键字段（ts_code, trade_date, open, high, low, close, volume）的缺失情况：
- 缺失率超过5% → 标记为**问题**
- 缺失率低于5% → 标记为**警告**

### 2. 异常值检测

检查以下异常：
- **价格异常**：< 1.0 或 > 3000.0
- **涨跌幅异常**：|涨跌幅| > 20%
- **成交量异常**：成交量为0

### 3. 数据一致性检查

检查：
- `high >= max(open, close)`
- `low <= min(open, close)`
- 重复记录（相同 ts_code + trade_date）

### 4. 数据覆盖度检查

检查每只股票的数据量是否充足（>= 100条记录）

## 数据清洗规则详解

### 1. 字段标准化

自动将各种命名转换为标准字段名。

### 2. 缺失值处理

- **关键字段缺失**：删除整条记录
- **数值字段缺失**：填充为0

### 3. 异常值处理

- **过低价格**：设置为 1.0
- **过高价格**：设置为 3000.0

### 4. 停牌数据标记

识别停牌条件：
- 成交量 = 0
- 涨跌幅 = 0

添加字段 `is_suspended` 标记停牌状态。

### 5. 数据一致性修复

自动修复开高低收盘的关系：
```python
high = max(high, open, close)
low = min(low, open, close)
```

### 6. 去重

删除重复记录（保留最后一条）。

## 日志和监控

Framework提供详细的日志输出：

```
2026-03-02 02:00:20 [INFO] 🔍 开始数据质量检查...
2026-03-02 02:00:20 [INFO]   📊 检查缺失值...
2026-03-02 02:00:20 [INFO]   🔍 检查异常值...
2026-03-02 02:00:20 [INFO]     检测到 66 条异常记录
2026-03-02 02:00:20 [INFO]   📈 检查数据覆盖度...
2026-03-02 02:00:20 [INFO]   🔗 检查数据一致性...
2026-03-02 02:00:20 [WARNING]     ⚠ 数据质量不合格
```

## 最佳实践

### 1. 定期质量检查

建议定期对数据源进行质量检查，及时发现数据问题。

```python
# 定期检查脚本
from code.data_quality_framework import DataQualityChecker
import pickle

with open('data/latest_data.pkl', 'rb') as f:
    data = pickle.load(f)

checker = DataQualityChecker()
report = checker.check_data(data)

# 发送质量报告
if not report.is_valid:
    send_alert(f"数据质量检查失败: {report.issues}")
```

### 2. 多数据源交叉验证

对于关键数据，建议使用多个数据源进行交叉验证。

```python
# 主数据源 + 验证数据源
results = pipeline.run(
    main_data,
    source_name="main",
    cross_validate_with={"backup": backup_data}
)
```

### 3. 自定义质量阈值

根据实际需求调整质量阈值。

```python
# 自定义阈值（更严格的检查）
custom_thresholds = {
    'max_missing_rate': 0.02,  # 缺失率不超过2%
    'min_price': 2.0,           # 最低股价
    'min_data_records_per_stock': 200  # 每只股票至少200条记录
}

checker = DataQualityChecker(thresholds=custom_thresholds)
```

### 4. 监控清洗日志

定期检查清洗日志，了解数据变化。

```python
import json

with open('data/source_cleaning_log.json', 'r') as f:
    log = json.load(f)

# 分析清洗步骤
for step in log['cleaning_log']:
    print(f"{step['step']}: {step}")
```

## 错误处理

Framework会捕获并记录异常：

```python
try:
    results = pipeline.run(raw_data, source_name="my_data")
except Exception as e:
    logger.error(f"数据处理失败: {e}")
    # 发送错误通知
    send_error_notification(str(e))
```

## 性能优化

对于大数据集（>100万条记录）：

1. **分批处理**：
```python
# 分批处理
batch_size = 100000
batches = [raw_data[i:i+batch_size] for i in range(0, len(raw_data), batch_size)]

cleaned_batches = []
for batch in batches:
    cleaned = cleaner.clean_data(batch)
    cleaned_batches.append(cleaned)

# 合并结果
final_data = pd.concat(cleaned_batches, ignore_index=True)
```

2. **只检查质量，不重复清洗**：
```python
# 如果已经清洗过，直接加载
if os.path.exists('data/my_data_cleaned.pkl'):
    with open('data/my_data_cleaned.pkl', 'rb') as f:
        cleaned_data = pickle.load(f)
else:
    # 执行完整Pipeline
    results = pipeline.run(raw_data, source_name="my_data")
```

## 示例场景

### 场景1：定期数据更新检查

```python
# 每日数据更新后检查
def daily_data_check():
    from code.data_quality_framework import DataQualityChecker

    with open('data/daily_update.pkl', 'rb') as f:
        daily_data = pickle.load(f)

    checker = DataQualityChecker()
    report = checker.check_data(daily_data)

    if not report.is_valid:
        print(f"⚠ 数据质量问题: {report.issues}")
        # 触发告警
    else:
        print("✓ 数据质量合格")

    return report
```

### 场景2：多数据源对比

```python
# 对比不同数据源的性能
def compare_sources():
    sources = {
        "akshare": load_akshare_data(),
        "tushare": load_tushare_data(),
        "eastmoney": load_eastmoney_data()
    }

    # 以第一个为主数据源
    main_source = list(sources.keys())[0]
    other_data = {k: v for k, v in sources.items() if k != main_source}

    pipeline = DataQualityPipeline()
    results = pipeline.run(
        sources[main_source],
        source_name=main_source,
        cross_validate_with=other_data
    )

    # 分析结果
    validation = results['steps']['cross_validation']
    for comparison in validation['comparisons']:
        print(f"\n{comparison['source1']} vs {comparison['source2']}")
        print(f"  共同股票: {comparison['stock_overlap']}")
        print(f"  价格差异: {comparison['price_diff_stats']}")
```

### 场景3：数据迁移和整合

```python
# 整合多个历史数据源
def integrate_historical_data():
    sources = {
        "2019_data": load_data('data/2019.pkl'),
        "2020_data": load_data('data/2020.pkl'),
        "2021_data": load_data('data/2021.pkl'),
        "2022_data": load_data('data/2022.pkl'),
        "2023_data": load_data('data/2023.pkl'),
        "2024_data": load_data('data/2024.pkl'),
    }

    all_cleaned = []

    for name, data in sources.items():
        print(f"\n处理 {name}...")

        pipeline = DataQualityPipeline()
        results = pipeline.run(data, source_name=name)

        if results['is_valid']:
            # 加载清洗后的数据
            cleaned_file = f'data/{name}_cleaned.pkl'
            with open(cleaned_file, 'rb') as f:
                cleaned = pickle.load(f)
            all_cleaned.append(cleaned)

    # 合并所有清洗后的数据
    final_data = pd.concat(all_cleaned, ignore_index=True)

    # 确保日期排序
    final_data = final_data.sort_values(['ts_code', 'trade_date'])

    # 保存最终数据
    with open('data/complete_historical_data.pkl', 'wb') as f:
        pickle.dump(final_data, f)

    print(f"\n✓ 整合完成: {len(final_data):,} 条记录")
```

## 常见问题

### Q1: 如何处理停牌数据？

Framework会自动标记停牌数据（`is_suspended` 字段）。你可以：

```python
# 过滤掉停牌数据
non_suspended = cleaned_data[~cleaned_data['is_suspended']]

# 或者保留，但在分析时排除
suspended_mask = cleaned_data['is_suspended']
analysis_data = cleaned_data[~suspended_mask]
```

### Q2: 如何提高数据质量分数？

- 使用高质量数据源
- 定期检查和清洗数据
- 填充缺失值（如有历史数据可用）
- 跨验证多个数据源

### Q3: 处理大数据集时内存不足怎么办？

1. 使用分批处理
2. 优化数据类型（例如 `float32` 而不是 `float64`）
3. 只加载需要的列
4. 使用Dask等大数据处理库

### Q4: 如何自定义检查规则？

可以通过继承 `DataQualityChecker` 类实现自定义检查：

```python
class CustomQualityChecker(DataQualityChecker):
    def _check_custom_rules(self, data):
        # 添加自定义检查
        pass

    def check_data(self, data):
        # 执行标准检查
        super().check_data(data)

        # 执行自定义检查
        self._check_custom_rules(data)

        return self.report
```

## 总结

数据质量管理框架提供了完整的A股数据质量保证体系：

✓ **自动化**：一键运行，自动执行所有检查和清洗步骤
✓ **可配置**：支持自定义质量阈值和清洗规则
✓ **可扩展**：模块化设计，易于添加自定义逻辑
✓ **可追溯**：详细日志和报告，便于问题诊断
✓ **多源验证**：支持多数据源交叉验证

建议在数据获取后定期运行此框架，确保数据质量支持可靠的量化分析和策略回测。
