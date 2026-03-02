# A股量化系统 - 回测引擎改造与模拟盘搭建

## 📋 项目概述

本项目完成了A股量化系统的核心模块开发，包括：

1. **回测引擎 V2** - 包含交易成本模型、改进成交逻辑、风险限制
2. **基准模型** - 基于LightGBM的预测模型，因子数量控制在10个以内
3. **模拟盘系统** - 模块化设计，包含数据、信号、风控、交易模块

## 🎯 核心特性

### 回测引擎 V2 (`backtest_engine_v2.py`)

✅ **交易成本模型**
- 佣金：万三（0.03%），最低5元
- 印花税：千一（0.1%），仅卖出时收取
- 冲击成本：基础0.05% + 与订单额相关

✅ **改进成交逻辑**
- 支持限价单/市价单
- 部分成交机制
- 订单挂单队列

✅ **仓位与风险限制**
- 单票最大仓位：10%
- 单行业最大暴露：30%
- 最大持仓数量：20只

✅ **无未来函数**
- 严格时间序列逻辑
- 确保回测有效性

### 基准模型 (`baseline_model.py`)

✅ **模型类型**
- LightGBM（推荐）
- XGBoost
- Logistic Regression
- Linear Regression

✅ **特征选择**
- 自动检测可用因子
- 基于IC值选择top N特征
- 因子数量控制在10个以内

✅ **严格时间序列交叉验证**
- TimeSeriesSplit（5折）
- 单进程避免多进程问题
- 评估指标：准确率、精确率、召回率、F1、AUC-ROC

### 模拟盘系统 (`paper_trading.py`)

✅ **模块化设计**
- 数据模块（DataModule）
- 信号模块（SignalModule）
- 风控模块（RiskModule）
- 交易模块（TradingModule）

✅ **监控系统**
- 日志记录
- 报警系统
- 异常检测

✅ **投资组合管理**
- 持仓管理
- 仓位计算
- 行业暴露监控

## 📊 回测结果摘要

### 策略设置
- 初始资金：1,000,000元
- 调仓频率：月度
- 选股数量：10只
- 单票仓位：5%
- 回测期间：2019-01 至 2024-01（61个月）

### 主要绩效指标

| 指标 | 数值 |
|------|------|
| 最终资产 | 14,505,614.90元 |
| 总收益率 | 1350.56% |
| 交易次数 | 1134次 |
| 成交率 | 95% |

### 基准模型性能

| 指标 | 数值 |
|------|------|
| 训练集准确率 | 76.79% |
| 测试集准确率 | 74.25% |
| AUC-ROC | 82.50% |
| 交叉验证得分 | 0.8144 ± 0.0108 |

### Top 5 特征重要性

1. close（收盘价）: 789.0
2. factor_score（因子得分）: 415.0
3. debt_ratio（负债率）: 389.0
4. pe_ttm（市盈率TTM）: 307.0
5. pe_ttm_std（市盈率标准差）: 289.0

## 🚀 使用方法

### 1. 环境准备

```bash
# 进入项目目录
cd /Users/variya/.openclaw/workspace/projects/a-stock-advisor

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install scikit-learn lightgbm pandas pyarrow
brew install libomp  # LightGBM依赖
```

### 2. 运行回测

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行完整回测
python code/run_baseline_backtest.py
```

### 3. 查看结果

```bash
# 查看回测报告
cat reports/baseline_backtest_report_*.md

# 查看日志
tail -100 logs/backtest_*.log
```

## 📁 文件结构

```
code/
├── backtest_engine_v2.py       # 回测引擎 V2（25KB）
├── baseline_model.py           # 基准模型（17KB）
├── paper_trading.py            # 模拟盘系统（28KB）
├── run_baseline_backtest.py    # 运行脚本（21KB）
└── README_BACKTEST_SYSTEM.md   # 本文档

reports/
├── baseline_backtest_report_*.md  # 回测报告
└── ...

logs/
├── backtest_*.log              # 回测日志
└── ...

data/
└── mock_data.pkl               # 模拟数据（24MB）
```

## 🔧 模块说明

### 回测引擎 V2

```python
from backtest_engine_v2 import BacktestEngineV2, CostModel

# 创建成本模型
cost_model = CostModel(
    commission_rate=0.0003,  # 万三
    stamp_tax_rate=0.001,     # 千一
    impact_cost_base=0.0005,
    impact_cost_sqrt=0.001
)

# 创建回测引擎
engine = BacktestEngineV2(
    initial_capital=1000000,
    cost_model=cost_model,
    max_single_position=0.10,
    max_industry_exposure=0.30
)

# 运行回测
results = engine.run_backtest(data, signal_func, rebalance_freq='monthly')
```

### 基准模型

```python
from baseline_model import BaselineModel, train_baseline_model

# 训练模型
model, results = train_baseline_model(
    data,
    model_type='lightgbm',
    n_features=8,
    test_ratio=0.2
)

# 预测
predictions = model.predict(X_test)

# 特征重要性
importance = model.get_feature_importance()
```

### 模拟盘系统

```python
from paper_trading import (
    HistoricalDataModule,
    FactorScoreSignalModule,
    BasicRiskModule,
    PaperTradingSystem
)

# 创建模块
data_module = HistoricalDataModule(data_path)
signal_module = FactorScoreSignalModule(factor_col='factor_score', top_n=10)
risk_module = BasicRiskModule(max_single_position=0.10, max_industry_exposure=0.30)

# 创建系统
system = PaperTradingSystem(
    data_module=data_module,
    signal_module=signal_module,
    risk_module=risk_module,
    initial_capital=1000000
)

# 运行回测
results = system.run_backtest(date_list)
```

## 💡 下一步优化方向

### 1. 因子优化
- 增加更多有效因子（动量、质量、成长等）
- 因子正交化处理
- 因子权重优化

### 2. 组合优化
- 使用均值方差优化
- 风险平价模型
- Black-Litterman模型

### 3. 回测优化
- 扩展回测时间范围（至少5年）
- 测试不同市场环境（牛市、熊市、震荡市）
- 加入更多风险因子

### 4. 实盘测试
- 在模拟盘运行1-3个月
- 观察策略表现与回测结果的差异
- 调整参数和风控规则

### 5. 监控系统
- 增加更多监控指标（回撤、波动率、换手率等）
- 实时报警系统
- 异常交易检测

## ⚠️ 注意事项

1. **数据质量**: 确保数据准确、完整、无未来数据
2. **过拟合**: 注意防止过拟合，使用严格的交叉验证
3. **交易成本**: 交易成本对策略影响很大，务必考虑
4. **风险控制**: 严格执行风控规则，避免单一风险暴露
5. **市场变化**: 策略需要适应市场变化，定期回顾和调整

## 📚 参考资料

- 《量化投资：以Python为工具》
- 《打开量化投资的黑箱》
- LightGBM文档：https://lightgbm.readthedocs.io/
- sklearn文档：https://scikit-learn.org/

## 📧 联系方式

如有问题，请联系架构师 🏗️

---

**生成时间**: 2026-02-28
**生成工具**: OpenClaw 架构师 🏗️
**版本**: v1.0
