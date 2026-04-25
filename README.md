# A股量化系统 v5.3

> 智能α因子选股 + 持仓跟踪 + 换仓策略 + 风控体系 + 专业推送 + 统一命令行入口

***

## 📋 系统简介

这是一个完整的A股量化交易系统，包含α因子选股、持仓跟踪、换仓策略、风控体系、专业自动化推送功能和**统一命令行入口**。系统设计遵循"从寻找圣杯到管理不确定性"的核心理念，通过工程化方法管理量化投资中的各种不确定性。


> 一点点说明：这个项目是我用来测试openclaw“能不能围绕一个宏观目标自我编程”这个问题构建的，重点不是量化，而是openclaw怎么拆解、跟踪、同步任务，具体量化是否有效还需要朋友们评估，*我并不专业*。为了让openclaw自动运行，还包含了其他的工具和铺垫，*新安装的openclaw肯定是没有这个能力的*。（毕竟是openclaw自己开发的，后面发现没有用env储存密钥，如果发现我的Key写死在文件里或者失效了，就自行替换hhhh）

**（题外话）openclaw能自动创建项目的预先准备有**
- Sentinel Flowloop 3.0：哨兵3.0引擎，让AI自动分工、监督、拆解任务，连夜写代码
- deep-research.skill：让AI可以自己深度研究一些相关的知识，根据收集信息自动进一步搜索和验证，避免幻觉
- skill-forge.skill：用来创建项目的skill和cli，不然整个项目openclaw压根用不了，还要我说需要AI干嘛
- 后续不再高频维护了，欢迎大家提交PR，另外这个不是一键使用的app，你需要有代码基础或者有一个会读代码的AI



**核心特性：**

- 🎯 α因子选股（80+因子，低估+高α策略）
- 📊 持仓跟踪（实时监控、止盈止损）
- 🔄 换仓策略（止盈/止损/时间/因子触发）
- ⚠️ 风控体系（多级风险控制 + Beta监控 + 压力测试）
- 📈 专业推送（完整交易指令 + 因子信息 + 行业标准）
- 🌐 市场状态监控（千股跌停、流动性、恐慌指数）
- 🔬 因子风险模型（因子暴露监控、风险归因）
- 🎮 **统一命令行入口**（`a_stock_manager.py` - 所有功能一键管理）
- 📱 多数据源整合（智兔数服、腾讯财经、新浪财经、AKShare等）

**最新更新（v5.3）：**

- ✅ **README完整功能文档** - 详细列出主入口所有菜单功能（6大模块+4个快捷入口）
- ✅ **Skill文件创建** - 添加 `.trae/skills/a-stock-advisor/SKILL.md` 适配所有功能
- ✅ **功能统计** - 主入口包含 50+ 子功能，覆盖量化投资全流程

**版本 v5.2：**

- ✅ **修复AKShare API兼容性** - 更新列映射以适配API返回的12列数据结构
- ✅ **数据源稳定性提升** - 解决列数不匹配导致的数据获取失败问题
- ✅ **测试验证脚本** - 添加 `scripts/test_fix.py` 用于快速验证数据获取功能

**版本 v5.1：**

- ✅ **创建统一命令行入口**（`a_stock_manager.py`）- 所有功能通过一个菜单管理
- ✅ **每日主控流程**（`daily_master.py`）- 完整的因子评估、选股、回测、持仓管理和报告生成
- ✅ **项目结构整理** - 移除重复和孤立内容，归档到 `archive/` 目录
- ✅ **菜单优化** - 简化选项，突出推荐功能
- ✅ **移除前端系统** - 前端无法使用，已归档
- ✅ **移除孤立模块** - `code/` 目录大部分模块未被使用，已归档

***

## 🚀 快速开始

### 1. 运行统一主入口（推荐）

```bash
# 进入项目目录
cd /Users/variya/.openclaw/workspace/projects/a-stock-advisor

# 运行主入口（推荐方式）
python3 a_stock_manager.py
```

主入口会显示交互式菜单，包含以下功能：

### 一级菜单（6个核心模块）

#### 1. 数据工程

- **1. 数据更新** ⭐推荐 - 从AKShare/BaoStock获取真实数据，支持增量更新
- **2. 数据质量检查** - 完整Pipeline检查+清洗+验证，自动修复数据问题
- **3. 数据时效性检查** - 检查数据新鲜度，显示数据年龄和更新时间
- **4. 多源数据获取** - 智兔数服/腾讯/新浪/AKShare多源切换
- **5. 另类数据框架** - 北向资金、融资融券、分析师研报等
- **6. 数据准备状态** ⭐新增 - 一键检查所有数据是否就绪

#### 2. 因子研发

- **1. 因子挖掘系统** ⭐推荐 - 人工因子挖掘、遗传规划自动挖掘、因子评估验证
- **2. 因子回测验证** - 单因子/多因子回测，股票级别因子分析
- **3. 因子库管理** - 因子启用/禁用、因子表现分析
- **4. 因子监控** - IC/IR下降监控、因子相关性监控
- **5. 创新实验室** - 因子原型快速验证、创新周报生成
- **6. 技术指标验证** ⭐新增 - RSI/MACD/布林带等指标有效性验证
- **7. RDAgent因子挖掘** ⭐AI驱动 - 微软RDAgent自动因子发现

#### 3. 策略开发

- **1. 多因子模型** ⭐推荐 - 多因子选股、动态权重、因子有效性评估
- **2. Alpha选股器** - 基于Alpha因子进行股票筛选
- **3. 市场状态识别** - 牛市/熊市/震荡市识别，策略建议
- **4. 再平衡策略** - 定期/阈值/信号驱动再平衡
- **5. 强化学习优化器** - DQN/PPO/A2C策略优化
- **6. ML因子组合器** - 随机森林/XGBoost/神经网络因子组合

#### 4. 回测验证

- **1. 运行回测** ⭐推荐 - 完整回测引擎，绩效分析
- **2. Brinson归因分析** - 配置效应、选择效应、交互效应分解
- **3. 滚动性能分析** - 滚动收益率/波动率/夏普比率/最大回撤
- **4. 压力测试** - 2008/2015/2020等极端情景测试
- **5. 过拟合检测** - 样本外验证、参数敏感性、IC衰减分析
- **6. 绩效对比** - 因子/策略/指标对比分析

#### 5. 实盘工程

- **1. 每日主控流程** ⭐推荐 - 完整流水线：因子评估→选股→回测→持仓管理→报告
- **2. 推送系统** - 盘前推送(8:00)、日报推送(18:30)、模拟交易推送
- **3. 持仓管理** - 凯利公式仓位计算、止损止盈、手动修改持仓 ⭐新增
- **4. 风控系统** - 策略容量评估、冲击成本、流动性风险、风格暴露
- **5. 资金管理** - 动态资金分配、风险预算管理
- **6. 风险预警** - 净值/回撤/仓位/因子暴露预警
- **7. 交易员助手** - 每日/每周交易报表、交易员反馈
- **8. 模拟交易** - 模拟盘交易系统
- **9. 券商API接入** - 华泰/中信/国泰君安API连接

#### 6. 系统管理

- **1. 交易日检查** - 检查今天是否是交易日
- **2. 系统验证** - 完整系统验证、快速验证、版本查看、Gitee更新
- **3. 定时任务管理** - 安装/卸载/查看定时任务
- **4. 系统配置管理** - 飞书推送配置、功能开关配置
- **5. 查看日志** - 系统运行日志、健康检查报告、错误摘要
- **6. 系统健康检查** - 完整健康检查
- **7. 质量控制** - 数据质量检查、因子有效性验证、流程完整性
- **8. 监控仪表板** - 系统健康/市场状态/因子表现/组合风险实时监控
- **9. 事件驱动引擎** - 异步事件处理架构

### 快捷入口（4个）

- **7. 从0-1量化投资** ⭐新增 - 一键启动完整量化流程检查
- **8. 每日主控流程** ⭐推荐 - 完整流水线一键执行
- **9. 盘前推送** ⭐推荐 - 工作日8:00盘前推送
- **10. 日报推送** ⭐推荐 - 工作日18:30日报推送

### 2. 环境搭建

```bash
# 克隆项目
git clone https://gitee.com/variyaone/a-stock-advisor.git
cd a-stock-advisor

# 安装依赖
pip install -r requirements.txt

# 配置飞书webhook
echo '{"webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/your_webhook_url"}' > config/feishu_config.json
```

### 3. 数据准备

```bash
# 通过主入口菜单选择"数据更新"
python3 a_stock_manager.py
# 选择 1. 数据工程 -> 1. 数据更新
```

或直接运行：

```bash
python3 scripts/data_update_v2.py
python3 scripts/fix_data_quality_v2.py
```

### 4. 运行每日主控流程

**⭐推荐方式**（通过主入口）：

```bash
python3 a_stock_manager.py
# 选择 2. 因子研发 -> 2. 每日主控流程 (完整流水线)
```

**传统方式**：

```bash
# 运行盘前推送（工作日8:00）
python3 scripts/unified_daily_push.py --type morning

# 运行日报推送（工作日18:30）
python3 scripts/unified_daily_push.py --type evening

# 运行回测
python3 scripts/run_backtest.py

# 安装定时任务
chmod +x scripts/install_cron_tasks.sh
./scripts/install_cron_tasks.sh

# 运行系统健康检查
python3 scripts/health_check.py
```

***

## 📁 目录结构

```
a-stock-advisor/
├── a_stock_manager.py          # ✅ 统一命令行入口 ⭐
├── MANUAL.md                   # ✅ 完整手册
├── README.md                   # ✅ 项目说明
├── scripts/                    # ✅ 核心脚本（20个）
│   ├── daily_master.py         # ⭐ 完整主控流程（推荐）
│   ├── data_update_v2.py       # 数据更新
│   ├── fix_data_quality_v2.py  # 数据质量修复
│   ├── is_trading_day.py       # 交易日判断
│   ├── unified_daily_push.py   # 统一日报推送
│   ├── morning_push_daemon.py  # 盘前推送守护
│   ├── paper_trading_push_v2.py # 模拟交易推送
│   ├── push_monitor.py         # 推送监控
│   ├── market_monitor.py       # 市场监控
│   ├── portfolio_monitor.py    # 组合监控
│   ├── enhanced_monitor.py     # 增强监控
│   ├── monitor_collector.py    # 监控收集
│   ├── health_check.py         # 系统健康检查
│   ├── run_backtest.py         # 运行回测
│   ├── run_simulation.py       # 运行模拟
│   ├── run_factor_backtest.py  # 因子回测
│   ├── run_innovation_lab.py   # 创新实验室
│   ├── feishu_pusher.py        # 飞书推送
│   ├── push_offline_fallback.py # 离线推送备选
│   ├── official_report.py      # 官方报告
│   ├── install_cron_tasks.sh   # 安装定时任务
│   ├── install_cron_v2.sh      # 安装定时任务V2
│   └── verify_system.sh        # 系统验证
├── code/                       # ✅ 核心代码模块
│   ├── backtest/               # 回测系统
│   ├── data/                   # 数据处理
│   ├── portfolio/              # 投资组合管理
│   ├── risk/                   # 风险管理
│   ├── strategy/               # 策略系统
│   ├── system/                 # 系统管理
│   ├── tests/                  # 测试代码
│   ├── trader/                 # 交易员辅助
│   └── utils/                  # 工具函数
├── config/                     # ✅ 配置文件
├── data/                       # ✅ 数据目录
├── reports/                    # ✅ 报告目录
├── docs/                       # ✅ 技术文档
├── archive/                    # 📦 归档内容（需要的话可以恢复）
│   ├── old_scripts/            # 旧脚本
│   ├── old_docs/               # 旧文档
│   ├── frontend/               # 前端系统
│   ├── code/                   # 代码模块库
│   └── examples/               # 示例代码
├── .gitignore
├── LICENSE
├── VERSION
├── CHANGELOG.md
└── requirements.txt
```

***

## 📖 推送内容详解（v4.0）

### 完整推送包含13部分：

1. **市场概览** - 三大指数、市场情绪、板块表现
2. **组合风险监控** - 波动率、VaR、最大回撤、Beta风险预警
3. **持仓详情** - 每只股票完整信息（代码、名称、α、PE、PB、ROE、行业平均）
4. **新选股详情** - 每只股票完整信息
5. **可执行交易清单** - 买卖方向、价格区间、计划金额、数量、执行时间、参考价
6. **止盈止损监控** - 收益、距止盈/止损、状态
7. **换仓建议** - 触发类型、原因、操作、替代股票
8. **因子表现监控** - IC、RankIC、状态
9. **行业配置建议** - 当前权重、基准权重、偏离度、建议
10. **市场极端情况监控** - 跌停股票、流动性、恐慌指数
11. **长期持仓推荐** - 高股息+低Beta，稳健型配置
12. **历史决策跟踪** - 决策内容、执行情况、结果
13. **明日计划** - 具体行动计划

***

## 🎯 核心功能

### 1. α因子选股系统

**因子分类：**

- 基本面因子（32个）：PE、PB、ROE、营收增长、毛利率等
- 技术面因子（42个）：动量、反转、波动率、流动性、RSI、MACD等
- 情绪因子（10个）：融资融券、北向资金等
- 另类因子（10个）：分析师、机构持仓等

**选股策略：**

- 低估值 + 高α
- 核心持仓60%（5只高α股票）
- 卫星持仓20%（2只行业轮动股票）
- 现金20%（应对风险）

**因子有效性标准：**

- IC绝对值 ≥ 0.02（弱有效）
- IC绝对值 ≥ 0.05（有效）
- IR ≥ 0.5（可接受）
- IR ≥ 1.0（良好）
- 样本量 ≥ 100只股票

### 2. 持仓跟踪系统

**功能：**

- 实时监控持仓状态
- 检查止盈止损触发
- 记录交易决策
- 计算组合收益

**输出：**

- 持仓明细（股票代码、数量、成本、盈亏）
- 组合概览（总资产、总盈亏、胜率）
- 风险指标（回撤、波动率）

### 3. 换仓策略系统

**触发条件：**

- **止盈**：收益>20% → 分3批止盈
- **止损**：亏损<-10% → 立即清仓
- **时间**：持仓>60天 → 评估换仓
- **因子**：α下降>20% → 建议换仓

### 4. 风控体系

**风控级别：**

- 个股止损：-10%
- 个股止盈：+20%
- 组合最大回撤：-15%
- 单股最大仓位：12%

**压力测试：**

- 2008年式大跌（-50%）
- 2015年式股灾（-40%）
- 2020年式疫情（-30%）
- 2024年式震荡（-5%）
- 科技泡沫破裂（-60%）

### 5. 动态因子权重系统（v5.0新增）

```python
from code.strategy.multi_factor_model import DynamicFactorWeightSystem, RollingICCalculator

# 创建动态权重系统
weight_system = DynamicFactorWeightSystem(
    ic_window=20,
    ic_threshold=0.02,
    ir_threshold=0.5,
    min_weight=0.05,
    max_weight=0.40
)

# 更新权重
weights = weight_system.update_weights(factor_data, return_data, date='2026-03-03')
print(f"当前因子权重: {weights}")

# 获取权重稳定性
stability = weight_system.get_weight_stability()
print(f"权重稳定性: {stability}")
```

### 6. 因子风险模型（v5.0新增）

```python
from code.risk.risk_calculator import FactorRiskModel, FactorExposureMonitor

# 因子风险模型
risk_model = FactorRiskModel(lookback_period=252)
factor_returns = risk_model.estimate_factor_returns(stock_returns, factor_exposures)
factor_cov = risk_model.estimate_factor_covariance(factor_returns_history)

# 因子暴露监控
monitor = FactorExposureMonitor()
alerts = monitor.check_exposure(portfolio_exposure)
monitor.track_exposure(date, portfolio_exposure)
report = monitor.generate_exposure_report()
```

### 7. 因子中性化（v5.0新增）

```python
from code.strategy.alpha_stock_selector import AlphaStockSelector

selector = AlphaStockSelector()

# 行业中性化
neutral_factor = selector.industry_neutralize(data, 'PE_TTM', 'industry')

# 市值中性化
neutral_factor = selector.market_cap_neutralize(data, 'PE_TTM', 'market_cap', method='regression')

# 双重中性化
neutral_factor = selector.double_neutralize(data, 'PE_TTM', 'industry', 'market_cap')

# 批量中性化
neutralized_data = selector.neutralize_all_factors(data, neutralize_type='double')
```

### 8. ML因子组合（v5.0新增）

```python
from code.strategy.ml_factor_combiner import MLFactorCombiner, EnsembleFactorCombiner

# 单模型因子组合
combiner = MLFactorCombiner(model_type='gbdt')
result = combiner.fit(factor_exposures, future_returns)
ml_weights = combiner.get_factor_weights()
predictions = combiner.predict(current_factor_exposures)

# 集成多模型
ensemble = EnsembleFactorCombiner(models=['gbdt', 'rf', 'ridge'])
ensemble_result = ensemble.fit(factor_exposures, future_returns)
ensemble_predictions = ensemble.predict(current_factor_exposures)
```

***

## 📊 数据源

**主要数据源（按优先级）：**

1. **智兔数服** ⭐⭐⭐⭐⭐ - 免费（需token），实时数据，包含财务指标
2. **腾讯财经** ⭐⭐⭐⭐ - 完全免费，数据格式规整，更新频率约3秒
3. **新浪财经** ⭐⭐⭐⭐ - 完全免费，老牌数据源，支持买卖五档盘口数据
4. **AKShare** ⭐⭐⭐⭐ - 完全免费，无限制，数据全面，覆盖面广
5. **Baostock** ⭐⭐⭐ - 完全免费，适合学习，数据量相对较少
6. **Tushare Pro** ⭐⭐⭐⭐ - 积分制（免费额度充足），数据最完整

**数据质量：**

- 单日涨跌幅：≤ ±10%（A股限制），ST股±5%
- 价格：> 0（无负值）
- 成交量：≥ 0（无负值）
- 波动率/均价：≤ 1.0（防止极端数据）
- 缺失值比例：< 1%（高完整性）
- 时间连续性：工作日连续（需处理停牌日）
- 复权一致性：前复权（确保价格可比）

**数据缓存：**

- 缓存过期时间：60秒
- 缓存机制：减少API调用，节约token使用
- 自动切换：当首选数据源失败时，自动尝试备选数据源

***

## 🕐 定时任务

### Cron配置

```bash
# 工作日8:00 - 盘前推送
0 8 * * 1-5 cd /path/to/a-stock-advisor && python3 scripts/unified_daily_push.py --type morning >> logs/morning_push.log 2>&1

# 工作日18:30 - 日报推送
30 18 * * 1-5 cd /path/to/a-stock-advisor && python3 scripts/unified_daily_push.py --type evening >> logs/daily_push.log 2>&1

# 每日3:00 - 系统健康检查
0 3 * * * cd /path/to/a-stock-advisor && python3 scripts/health_check.py >> logs/health_check.log 2>&1

# 每日4:00 - 数据更新
0 4 * * * cd /path/to/a-stock-advisor && python3 scripts/data_update_v2.py >> logs/data_update.log 2>&1
```

### 安装定时任务

```bash
# 给脚本添加执行权限
chmod +x scripts/install_cron_tasks.sh

# 运行安装脚本
./scripts/install_cron_tasks.sh
```

***

## 📖 开发规范（强制执行）

**任何更新必须遵循以下步骤：**

```
1️⃣ 需求分析 → 2️⃣ 文档更新 → 3️⃣ 代码实现 → 4️⃣ 核查测试 → 5️⃣ 提交部署
```

**详细步骤：**

1. **需求分析** - 理解指令，定义目标，拆解流程
2. **文档更新** - 更新README、MANUAL.md、接口定义
3. **代码实现** - 调用架构师/创作者实现
4. **核查测试** - 功能测试、边界测试、数据验证
5. **提交部署** - Git commit、推送到Gitee、更新版本号

**检查清单：**

- [ ] 文档已更新（README.md、MANUAL.md）
- [ ] 代码已测试（功能测试、边界测试）
- [ ] 数据格式正确（符合数据质量标准）
- [ ] 异常已处理（错误处理、日志记录）
- [ ] Git已提交（包含清晰的commit message）
- [ ] 依赖已更新（requirements.txt）
- [ ] 配置已更新（config/目录下的配置文件）
- [ ] 测试已通过（运行测试脚本）

***

## 🔧 配置文件

### 飞书推送配置

`config/feishu_config.json`:

```json
{
  "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/your_webhook_url"
}
```

### 风控配置

`config/risk_limits.json`:

```json
{
  "stop_loss_threshold": -0.10,
  "take_profit_threshold": 0.20,
  "max_portfolio_drawdown": -0.15,
  "max_single_stock_weight": 0.12
}
```

### Cron任务配置

`config/cron_config_v2.json`:

```json
{
  "morning_push": "0 8 * * 1-5",
  "evening_push": "30 18 * * 1-5",
  "health_check": "0 3 * * *",
  "data_update": "0 4 * * *"
}
```

***

## 📚 文档

### 设计文档

- **docs/design/DAG.md** - 数据流图
- **docs/design/FACTOR\_STANDARDS.md** - 因子标准
- **docs/design/INNOVATION\_PLAN.md** - 创新计划
- **docs/design/PUSH\_CONTENT\_DESIGN.md** - 推送内容设计
- **docs/design/PUSH\_STRATEGY\_V4.md** - 推送策略
- **docs/design/T1.6\_TASK\_SPEC.md** - 任务规范
- **docs/design/TRADING\_EXECUTION\_SPEC.md** - 交易执行规范

### 操作文档

- **docs/operation/FEISHU\_SETUP.md** - 飞书设置
- **docs/operation/OPERATION\_TARGET.md** - 操作目标
- **docs/operation/PUSH\_STANDARD\_FLOW\.md** - 推送标准流程
- **docs/operation/PUSH\_WORKFLOW\_OPTIMIZATION.md** - 推送流程优化

### 技术文档

- **docs/technical/DATA\_QUALITY\_DELIVERY\_REPORT.md** - 数据质量交付报告
- **docs/technical/DataQualityFramework.md** - 数据质量框架
- **docs/technical/README\_AUTOMATION.md** - 自动化说明
- **docs/technical/README\_BACKTEST\_SYSTEM.md** - 回测系统说明
- **docs/technical/README\_DATA\_QUALITY.md** - 数据质量说明
- **docs/technical/STANDARDIZED\_DOCUMENTATION.md** - 标准化文档
- **docs/technical/coding\_standards.md** - 编码标准
- **docs/technical/integration\_plan.md** - 集成计划
- **docs/technical/validation\_plan.md** - 验证计划
- **docs/technical/version\_control\_guide.md** - 版本控制指南

***

## 🔗 开源项目借鉴

本项目借鉴了以下优秀开源项目的核心功能：

| 项目                                                 | 借鉴功能           | 实现文件                                     |
| -------------------------------------------------- | -------------- | ---------------------------------------- |
| [Qbot](https://github.com/UFund-Me/Qbot)           | ML因子组合、飞书推送    | `code/ml_factor_combiner.py`             |
| [Abu](https://github.com/bbfamily/abu)             | 参数优化、回测框架、风险评估 | `code/overfitting_detection_enhanced.py` |
| [Qlib](https://github.com/microsoft/qlib)          | ML因子组合、统一数据接口  | `code/ml_factor_combiner.py`             |
| [yfinance](https://github.com/ranaroussi/yfinance) | 多数据源获取         | `code/multi_source_fetcher.py`           |

详细借鉴状态请查看 [docs/integration\_plan.md](docs/integration_plan.md)

***

## 🌟 版本历史

### v5.3 (2026-03-12)

- ✅ **README完整功能文档** - 详细列出主入口所有菜单功能（6大模块+4个快捷入口）
- ✅ **Skill文件创建** - 添加 `.trae/skills/a-stock-advisor/SKILL.md` 适配所有功能
- ✅ **功能统计** - 主入口包含 50+ 子功能，覆盖量化投资全流程

### v5.2 (2026-03-10)

- ✅ **创建统一命令行入口**（`a_stock_manager.py`）- 所有功能通过一个菜单管理
- ✅ **每日主控流程**（`daily_master.py`）- 完整的因子评估、选股、回测、持仓管理和报告生成
- ✅ **项目结构整理** - 移除重复和孤立内容，归档到 `archive/` 目录
- ✅ **菜单优化** - 简化选项，突出推荐功能
- ✅ **移除前端系统** - 前端无法使用，已归档
- ✅ **移除孤立模块** - `code/` 目录大部分模块未被使用，已归档
- ✅ **移除重复文档** - 使用说明已统一到 MANUAL.md

### v5.0 (2026-03-03)

- ✅ 因子公式修复（毛利率公式错误修正）
- ✅ IC计算优化（最小样本量100只，显著性检验，p-value）
- ✅ 动态因子权重系统（RollingICCalculator、DynamicFactorWeightSystem）
- ✅ 技术面因子扩展（12个新因子：动量、反转、波动率、RSI、MACD等）
- ✅ 因子中性化实现（行业/市值/双重中性化）
- ✅ 因子风险模型构建（FactorRiskModel、FactorExposureMonitor）
- ✅ 开源项目融合方案（Qlib、QUANTAXIS、VNPy、Abu等）
- ✅ ML因子组合模块（ml\_factor\_combiner.py）
- ✅ 事件驱动引擎（event\_engine.py）
- ✅ 系统管理器（system\_manager.py）- 统一管理系统组件、插件系统、配置管理
- ✅ 数据处理管道（DataPipeline）- 模块化数据处理流程
- ✅ 资金管理系统（fund\_management.py）- 智能资金分配和风险预算
- ✅ 实时交易接口（real\_time\_trading.py）- 模拟交易和订单管理
- ✅ 股票代码格式修复（修正为正确格式如sh600064）
- ✅ 价格信息显示修复（显示真实价格区间）
- ✅ 系统性能优化（限制股票池大小，提高响应速度）
- ✅ 数据获取稳定性增强（多数据源自动切换机制）
- ✅ 多数据源整合（智兔数服、腾讯财经、新浪财经）
- ✅ 数据缓存机制（60秒缓存，节约token使用）
- ✅ 新浪财经API支持（添加Referer请求头）

### v4.0 (2026-03-02)

- ✅ 13部分完整推送内容
- ✅ 每只股票详细因子信息
- ✅ Beta风险监控和预警
- ✅ 长期持仓推荐
- ✅ 可执行交易清单

### v2.0 (2026-03-02)

- ✅ α因子选股系统（80+因子）
- ✅ 持仓跟踪系统
- ✅ 换仓策略系统
- ✅ 风控体系
- ✅ 自动化推送系统
- ✅ 推送标准流程固化
- ✅ 开发流程规范化

### v1.0 (2026-02-28)

- ✅ 基础数据获取
- ✅ 简单推送系统

***

## 📦 依赖

```
pandas >= 1.5.0
numpy >= 1.23.0
akshare >= 1.10.0
requests >= 2.28.0
scipy >= 1.9.0
scikit-learn >= 1.3.0
```

***

## 📞 联系方式

- **项目地址**: <https://gitee.com/variyaone/a-stock-advisor>
- **Skill**: a-stock-advisor
- **维护者**: 小龙虾🦞（main）

***

**免责声明：本系统仅供研究学习，不构成投资建议。投资有风险，入市需谨慎。**
