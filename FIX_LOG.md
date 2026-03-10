# 修复日志

## 2026-03-11 - AKShare API列数不匹配问题修复

### 问题描述
- **错误信息**：`Length mismatch: Expected axis has 12 elements, new values have 10 elements`
- **影响范围**：所有500只股票数据获取失败
- **发生时间**：2026-03-11
- **严重等级**：P0 - 数据是系统运行的基础

### 根本原因
AKShare API的 `stock_zh_a_hist` 函数在最新版本中返回的数据结构从10列变为12列：

**原始代码期望的列（10列）：**
```python
['date', 'open', 'close', 'high', 'low', 'volume', 'amount',
 'change_pct', 'change_amount', 'turnover']
```

**实际API返回的列（12列）：**
```python
['日期', '股票代码', '开盘', '收盘', '最高', '最低',
 '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']
```

新增的两列：
- `股票代码` - 股票代码
- `振幅` - 振幅

### 影响分析
1. **直接后果**：数据获取失败，系统无法更新股票数据
2. **连带影响**：
   - 选股系统无法运行
   - 回测系统无法验证
   - 推送系统无法生成交易建议
   - 整个系统瘫痪

### 修复方案
**修改文件**：`scripts/data_update_v2.py`

**修改内容**：
```python
# 修改前（第69-74行）
if df is not None and len(df) > 0:
    df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount',
                  'change_pct', 'change_amount', 'turnover']

    df['stock_code'] = stock_code
    df['stock_name'] = stock_name
    df['date'] = pd.to_datetime(df['date'])

# 修改后
if df is not None and len(df) > 0:
    # AKShare返回12列：日期、股票代码、开盘、收盘、最高、最低、成交量、成交额、振幅、涨跌幅、涨跌额、换手率
    df.columns = ['date', 'stock_code_api', 'open', 'close', 'high', 'low',
                  'volume', 'amount', 'amplitude', 'change_pct', 'change_amount', 'turnover']

    df['stock_code'] = stock_code
    df['stock_name'] = stock_name
    df['date'] = pd.to_datetime(df['date'])
```

**关键改进**：
1. 更新列名映射，包含API返回的所有12列
2. 添加 `amplitude`（振幅）列映射
3. 将API返回的 `股票代码` 映射为 `stock_code_api`，避免与后续添加的 `stock_code` 冲突

### 验证结果
**测试脚本**：`scripts/test_fix.py`

**测试输出**：
```
✅ 数据获取成功！
  - 股票数量: 5
  - 总记录数: 146
  - 列数: 29
  - 列名: ['date', 'stock_code_api', 'open', 'close', 'high', 'low',
           'volume', 'amount', 'amplitude', 'change_pct', 'change_amount',
           'turnover', 'stock_code', 'stock_name', 'ma5', 'ma10', 'ma20',
           'ma60', 'momentum_5', 'momentum_10', 'momentum_20', 'momentum_60',
           'volatility_5', 'volatility_10', 'volatility_20', 'price_to_ma20',
           'price_to_ma60', 'date_dt', 'month']

✅ 修复验证通过！
```

**结论**：
- ✅ 无列数不匹配错误
- ✅ API返回的12列数据正确映射
- ✅ 技术指标计算正常（12列原始 + 17列技术指标 = 29列）
- ✅ 数据结构完整，可用于选股和回测

### 经验教训
1. **API版本监控**：
   - 第三方API可能随时更新数据结构
   - 需要定期检查API返回格式
   - 建议添加API版本检测机制

2. **错误处理改进**：
   - 当前列数不匹配错误只在运行时暴露
   - 建议添加预检查，在获取数据前验证列数
   - 可以添加列映射的自动适配机制

3. **测试覆盖**：
   - 数据获取模块应该有单元测试
   - 需要定期运行完整的集成测试
   - 建议添加CI/CD自动检测API变化

### 后续改进建议
1. **添加API兼容性层**：
   ```python
   def adapt_akshare_columns(df):
       """自动适配不同版本的AKShare API列结构"""
       actual_columns = set(df.columns)
       # 根据实际列名动态生成映射
       ...
   ```

2. **添加数据预检查**：
   ```python
   def validate_akshare_data(df):
       """验证AKShare返回的数据结构"""
       if len(df.columns) not in [10, 12]:
           raise ValueError(f"意外的列数：{len(df.columns)}")
       ...
   ```

3. **定期API健康检查**：
   - 每日自动运行小规模测试（5只股票）
   - 检测到变化时立即告警
   - 记录API版本历史

### 相关文件
- **修复文件**：`scripts/data_update_v2.py`
- **测试脚本**：`scripts/test_fix.py`
- **Git提交**：`f95cdc7` - 修复AKShare API列数不匹配问题

---

**维护者**：小龙虾🦞
**修复日期**：2026-03-11
