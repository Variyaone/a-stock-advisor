# 创新实验报告

本目录存储创新实验室的实验报告，包含因子和策略的验证结果。

## 目录结构

```
innovation_experiments/
├── README.md                           # 本文件
├── factor_<因子名>_<时间戳>.json      # 因子实验报告
├── strategy_<策略名>_<时间戳>.json    # 策略实验报告
└── weekly_report_<日期>.md            # 创新周报
```

## 报告格式

### 因子实验报告

```json
{
  "factor_name": "momentum_20d",
  "description": "20日价格动量",
  "category": "技术面因子",
  "validation_date": "2026-03-01 18:30:00",
  "ic_metrics": {
    "ic_mean": 0.0325,
    "ic_std": 0.0586,
    "ic_max": 0.1523,
    "ic_min": -0.1245,
    "ir": 0.5546,
    "ic_abs_mean": 0.0689,
    "ic_win_rate": 0.58,
    "ic_t_stat": 3.245,
    "ic_p_value": 0.0012,
    "n_periods": 120
  },
  "monotonicity_metrics": {
    "monotonicity": 0.75,
    "group_returns": [-0.0234, -0.0089, 0.0012, 0.0145, 0.0321],
    "long_short_return": 0.0555,
    "spearman_corr": 0.0876,
    "spearman_p_value": 0.0001,
    "n_groups": 5
  },
  "validation": {
    "is_valid": true,
    "passed_tests": ["IC绝对值", "IR", "IC胜率", "单调性"],
    "failed_tests": [],
    "final_score": 1.0
  },
  "notes": "经典动量因子，A股表现良好"
}
```

### 策略实验报告

```json
{
  "strategy_name": "Dynamic_Momentum_Reversal",
  "description": "动量-反转动态切换策略",
  "category": "多策略融合",
  "test_date": "2026-03-01 18:30:00",

  "backtest_results": {
    "start_date": "2020-01-01",
    "end_date": "2024-12-31",
    "annual_return": 0.145,
    "cumulative_return": 2.89,
    "sharpe_ratio": 1.32,
    "max_drawdown": -0.225,
    "calmar_ratio": 0.644,
    "volatility": 0.189,
    "win_rate": 0.56,
    "avg_turnover": 0.65
  },

  "validation": {
    "is_valid": true,
    "passed_tests": ["年化收益", "夏普比率", "最大回撤"],
    "failed_tests": [],
    "final_score": 1.0
  },

  "notes": "多策略融合有效，适应性强"
}
```

### 创新周报

```markdown
# 量化创新周报

**生成时间**: 2026-03-01

## 📊 创新统计

### 因子创新
- 探索因子总数: 2
- 有效因子数: 1
- 有效创新率: 50%
- 目标准: 20%

### 策略创新
- 探索策略总数: 1
- 有效策略数: 1

## 🎯 本周完成

- [x] 探索2个新因子
- [x] 设计1个新策略
- [x] 有效创新率 > 20%

## 📝 创新心得

```

## 如何生成报告

1. **手动验证因子**：
   ```python
   from code.innovation_lab import InnovationLab

   lab = InnovationLab()
   lab.validator.load_data(start_date='20200101', end_date='20241231')

   # 验证因子
   lab.explore_new_factor(
       factor_func=your_factor_function,
       factor_name='your_factor_name',
       description='因子描述',
       category='因子分类',
       periods=5
   )
   ```

2. **生成周报**：
   ```python
   lab.generate_innovation_report()
   ```

## 创新评价标准

### 有效因子标准

| 指标 | 阈值 | 说明 |
|------|------|------|
| IC绝对值 | > 0.02 | 因子与未来收益率相关性 |
| IR | > 0.5 | IC均值/IC标准差 |
| IC胜率 | > 55% | IC>0的交易日占比 |
| 单调性 | > 0.6 | 60%的分组满足单调性 |

### 有效策略标准

| 指标 | 阈值 | 说明 |
|------|------|------|
| 年化收益 | > 10% | 年化收益率 |
| 夏普比率 | > 1.0 | 收益/波动比 |
| 最大回撤 | < 30% | 最大回撤幅度 |
| 卡玛比率 | > 0.33 | 收益/最大回撤 |

### 创新质量分级

| 分级 | 综合得分 | 说明 |
|------|---------|------|
| A（优秀） | >= 0.9 | 所有指标通过 |
| B（良好） | >= 0.7 | 至少2个指标通过 |
| C（一般） | >= 0.5 | 至少1个指标通过 |
| D（无效） | < 0.5 | 不够有效 |

## 持续改进

1. **每周回顾**：
   - 查看本周创新率
   - 分析失败原因
   - 优化验证标准

2. **月度总结**：
   - 汇总有效因子/策略
   - 制定下月创新计划
   - 更新因子/策略库

3. **季度评估**：
   - 评估创新方向有效性
   - 调整创新策略
   - 报告创新成果

---

**最后更新**: 2026-03-01
**维护者**: 创新实验室
