# 数据质量管理框架 - README

## 快速开始

### 一行代码运行完整Pipeline

```python
from code.data_quality_framework import DataQualityPipeline
import pickle

# 加载数据并运行Pipeline
with open('data/real_stock_data.pkl', 'rb') as f:
    data = pickle.load(f)

pipeline = DataQualityPipeline()
results = pipeline.run(data, source_name="my_data")

print(f"数据质量: {'✓ 合格' if results['is_valid'] else '⚠ 有问题'}")
```

## 文件结构

```
code/
├── data_quality_framework.py      # 核心框架文件
├── README_DATA_QUALITY.md         # 本文件
└── ...

docs/
├── DataQualityFramework.md        # 完整文档
└── ...

examples/
├── data_quality_example.py        # 使用示例集合
└── ...

data/
├── {source_name}_quality_report.json    # 质量报告
├── {source_name}_cleaning_log.json      # 清洗日志
└── {source_name}_cleaned.pkl            # 清洗后的数据
```

## 核心功能

### 1. 数据质量检查（DataQualityChecker）

自动检测：
- ✓ 缺失值
- ✓ 异常值（价格、涨跌幅、成交量）
- ✓ 数据一致性（开高低收盘关系）
- ✓ 数据覆盖度（每只股票的数据量）

### 2. 数据清洗（DataCleaner）

自动执行：
- ✓ 字段标准化（统一列名）
- ✓ 缺失值处理
- ✓ 异常值修正
- ✓ 停牌数据标记
- ✓ 数据一致性修复
- ✓ 重复记录去除

### 3. 交叉验证（DataValidator）

- ✓ 多数据源对比
- ✓ 差异统计分析
- ✓ 可信度评分
- ✓ 数据源推荐

### 4. 自动化Pipeline（DataQualityPipeline）

一键执行完整的质量管理流程。

## 使用方式

### 方式1: 运行完整Pipeline（推荐）

```python
from code.data_quality_framework import DataQualityPipeline

pipeline = DataQualityPipeline()
results = pipeline.run(raw_data, source_name="my_data")
```

### 方式2: 单独使用各组件

```python
from code.data_quality_framework import DataQualityChecker, DataCleaner

# 质量检查
checker = DataQualityChecker()
report = checker.check_data(data)

# 数据清洗
cleaner = DataCleaner()
cleaned_data = cleaner.clean_data(data)
```

### 方式3: 查看详细示例

```bash
python3 examples/data_quality_example.py
```

## 输出文件说明

| 文件名 | 说明 |
|--------|------|
| `{source_name}_quality_report.json` | 数据质量检查报告，包含缺失值、异常值、问题列表等 |
| `{source_name}_cleaning_log.json` | 数据清洗日志，记录每一步清洗操作 |
| `{source_name}_cleaned.pkl` | 清洗后的最终数据，可直接用于分析和回测 |

## 配置选项

### 自定义质量阈值

```python
from code.data_quality_framework import DataQualityChecker

custom_thresholds = {
    'max_missing_rate': 0.02,      # 缺失率阈值
    'min_price': 2.0,               # 最低股价
    'min_data_records_per_stock': 200,
}

checker = DataQualityChecker(thresholds=custom_thresholds)
```

### 完整的阈值配置

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

## 常见使用场景

### 场景1: 定期数据质量检查

```python
from code.data_quality_framework import DataQualityChecker

# 每日数据更新后检查
with open('data/daily_update.pkl', 'rb') as f:
    data = pickle.load(f)

checker = DataQualityChecker()
report = checker.check_data(data)

if not report.is_valid:
    print(f"⚠ 数据质量问题: {report.issues}")
    # 发送告警
```

### 场景2: 多数据源交叉验证

```python
from code.data_quality_framework import DataQualityPipeline

# 对比多个数据源
results = pipeline.run(
    main_data,
    source_name="main",
    cross_validate_with={
        "backup": backup_data,
        "third": third_data
    }
)

# 查看交叉验证结果
validation = results['steps']['cross_validation']
for comparison in validation['comparisons']:
    print(f"{comparison['source1']} vs {comparison['source2']}")
```

### 场景3: 数据迁移和整合

```python
# 整合多个历史数据文件
sources = ["2019_data", "2020_data", "2021_data", ...]

all_cleaned = []
for name in sources:
    with open(f'data/{name}.pkl', 'rb') as f:
        data = pickle.load(f)

    results = pipeline.run(data, source_name=name)

    if results['is_valid']:
        with open(f'data/{name}_cleaned.pkl', 'rb') as f:
            cleaned = pickle.load(f)
        all_cleaned.append(cleaned)

# 合并最终数据
final_data = pd.concat(all_cleaned, ignore_index=True)
```

### 场景4: 监控和告警

```python
import json

# 加载质量报告
with open('data/my_data_quality_report.json', 'r') as f:
    report = json.load(f)

# 检查质量
if not report['is_valid']:
    # 发送告警邮件/短信等
    send_alert(f"数据质量问题: {report['issues']}")
```

## 实际运行示例

```bash
# 进入项目目录
cd /Users/variya/.openclaw/workspace/projects/a-stock-advisor

# 运行核心框架（演示模式）
python3 code/data_quality_framework.py
```

**输出示例：**

```
2026-03-02 02:00:20 [INFO] 数据质量管理Pipeline
2026-03-02 02:00:20 [INFO]
步骤1: 数据质量检查
2026-03-02 02:00:20 [INFO] 🔍 开始数据质量检查...
2026-03-02 02:00:20 [INFO]   📊 检查缺失值...
2026-03-02 02:00:20 [INFO]   🔍 检查异常值...
2026-03-02 02:00:20 [INFO]     检测到 66 条异常记录
2026-03-02 02:00:20 [INFO]   📈 检查数据覆盖度...
2026-03-02 02:00:20 [INFO]   🔗 检查数据一致性...
2026-03-02 02:00:20 [INFO]   ✓ 质量报告已保存至 data/akshare_real_data_quality_report.json

步骤2: 数据清洗
2026-03-02 02:00:20 [INFO] 🧹 开始数据清洗...
2026-03-02 02:00:20 [INFO]   📝 标准化字段名称...
2026-03-02 02:00:20 [INFO]     ✓ 重命名 3 个字段
2026-03-02 02:00:20 [INFO]   🔧 处理缺失值...
2026-03-02 02:00:20 [INFO]   🛡️ 处理异常值...
2026-03-02 02:00:20 [INFO]   🚫 处理停牌数据...
2026-03-02 02:00:20 [INFO]   ✓ 确保数据一致性...
2026-03-02 02:00:20 [INFO]     去除重复记录: 307975 条
2026-03-02 02:00:20 [INFO]   ✓ 清洗日志已保存至 data/akshare_real_data_cleaning_log.json

步骤3: 跳过交叉验证（无其他数据源）

步骤4: 保存清洗后的数据
2026-03-02 02:00:20 [INFO]   ✓ 数据已保存至 data/akshare_real_data_cleaned.pkl

======================================================================
Pipeline完成: ⚠ 存在问题
原始记录: 764,203
最终记录: 307,975
======================================================================
```

## 与现有代码的集成

### 与 fetch_real_data.py 集成

```python
# 获取数据后立即进行质量检查
from code.fetch_real_data import RealAStockDataFetcher
from code.data_quality_framework import DataQualityPipeline

# 第1步：获取数据
fetcher = RealAStockDataFetcher()
stock_list = fetcher.get_all_a_stocks()
raw_data = fetcher.process_all_stocks(stock_list, limit=50)

# 第2步：运行质量管理Pipeline
pipeline = DataQualityPipeline()
results = pipeline.run(raw_data, source_name="akshare_data")

# 使用清洗后的数据
if results['is_valid']:
    with open('data/akshare_data_cleaned.pkl', 'rb') as f:
        cleaned_data = pickle.load(f)
    # 继续使用cleaned_data...
```

### 与 backtest 代码集成

```python
# 在回测前确保数据质量
from code.data_quality_framework import DataQualityPipeline

# 获取并清洗数据
with open('data/real_stock_data.pkl', 'rb') as f:
    raw_data = pickle.load(f)

pipeline = DataQualityPipeline()
results = pipeline.run(raw_data, source_name="backtest_data")

if results['is_valid']:
    # 加载清洗后的数据进行回测
    with open('data/backtest_data_cleaned.pkl', 'rb') as f:
        clean_data = pickle.load(f)

    # 执行回测
    run_backtest(clean_data)
else:
    print("数据质量不合格，无法进行回测")
```

## 性能优化建议

### 对于大数据集（>100万条记录）

**方法1: 分批处理**

```python
batch_size = 100000
batches = [raw_data[i:i+batch_size] for i in range(0, len(raw_data), batch_size)]

cleaned_batches = []
for batch in batches:
    cleaned = cleaner.clean_data(batch)
    cleaned_batches.append(cleaned)

final_data = pd.concat(cleaned_batches, ignore_index=True)
```

**方法2: 优化数据类型**

```python
# 转换数据类型减少内存占用
data['open'] = data['open'].astype('float32')
data['close'] = data['close'].astype('float32')
data['volume'] = data['volume'].astype('int32')
```

**方法3: 只加载需要的列**

```python
# 如果不需要所有列，只加载必要的列
required_columns = ['ts_code', 'trade_date', 'open', 'close', 'volume']
data = data[required_columns]
```

## 常见问题

### Q1: 数据质量检查发现了很多问题，我该怎么办？

A: 这是一个正常的发现过程。根据问题的严重程度采取不同措施：
- **严重问题**（issues）：需要在数据源层面解决，或调整数据获取方式
- **警告**（warnings）：可以通过数据清洗自动修复
- 有些问题是轻微的（如开高低收盘关系），框架会自动修复

### Q2: 清洗后数据的记录数减少了，正常吗？

A: 是正常的。常见的减少原因：
- 去除了重复记录（通常幅度最大）
- 删除了缺失关键字段的记录
- 过滤了异常记录

我们的示例中，764,203条记录经过清洗后变成了307,975条，主要是因为去除了大量重复记录。

### Q3: 如何设置更严格/宽松的质量标准？

A: 修改 `QUALITY_THRESHOLDS` 配置：

```python
# 更严格
strict_thresholds = {
    'max_missing_rate': 0.01,  # 缺失率<1%
    'min_data_records_per_stock': 500,  # 每只股票至少500条记录
}

# 更宽松
loose_thresholds = {
    'max_missing_rate': 0.10,  # 缺失率<10%
    'min_data_records_per_stock': 50,  # 每只股票至少50条记录
}
```

### Q4: 交叉验证显示差异很大，应该怎么选择数据源？

A: 根据差异大小和性质：
- **价格差异小，成交量差异大**：可能数据源成交额计算方式不同
- **价格差异大**：检查某个源的数据是否有问题
- **总体差异都小**：可以任选一个，或采用加权平均

### Q5: 可以用于实时数据吗？

A: 可以，但要注意：
- 质量检查会带来额外计算开销
- 对于高频数据，建议降低检查频率
- 可以对历史数据严格检查，实时数据较宽松检查

## 技术支持

### 查看日志

运行过程中产生的详细日志位于：

```
logs/
├── enhanced_data_generator.log    # 数据生成日志
├── fetch_real_data.log           # 数据获取日志
└── ...
```

### 调试模式

```python
# 启用更详细的日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 然后运行你的代码
```

### 导出清洗后的字段说明

```python
# 查看清洗后的数据字段
cleaned_data.info()

# 保存字段说明
with open('data/cleaned_data_columns.txt', 'w') as f:
    for col in cleaned_data.columns:
        f.write(f"{col}\n")
```

## 最佳实践总结

1. **定期检查**：每天数据更新后运行一次质量检查
2. **多源验证**：对于关键数据，使用多个数据源交叉验证
3. **自动修复**：利用框架的自动清洗功能修复常见问题
4. **监控告警**：对质量报告中的问题设置告警
5. **版本管理**：保存清洗后的数据版本，便于追溯
6. **文档记录**：记录每次数据处理的质量报告和清洗日志

## 更新日志

### v1.0.0 (2026-03-02)

**新增功能**：
- ✓ 完整的数据质量检查框架
- ✓ 自动化数据清洗流程
- ✓ 多数据源交叉验证
- ✓ 端到端数据处理Pipeline
- ✓ 详细的质量报告和清洗日志
- ✓ 完整的文档和示例代码

**核心模块**：
- DataQualityChecker - 数据质量检查器
- DataCleaner - 数据清洗器
- DataValidator - 交叉验证器
- DataQualityPipeline - 自动化Pipeline

## 联系方式

如有问题或建议，请参考：

- 完整文档：`docs/DataQualityFramework.md`
- 使用示例：`examples/data_quality_example.py`
- 代码实现：`code/data_quality_framework.py`

---

**作者**: 架构师 🏗️
**日期**: 2026-03-02
**版本**: v1.0.0
