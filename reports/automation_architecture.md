# 系统自动化架构文档

## 1. 架构概述

### 1.1 设计理念

> **确定性任务脚本化，Agent 仅处理需要智能决策的场景**

这个架构将系统分为三层：
1. **自动化脚本层** - 处理所有确定性任务
2. **Cron 调度层** - 负责任务的时间调度
3. **Agent 监控层** - 处理异常和需要智能决策的场景

### 1.2 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户层                                │
│                   (Agent 监控层)                            │
│  - 异常处理  - 策略优化  - 智能决策  - 根因分析              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ 异时介入
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                      Cron 调度层                            │
│  - 时间调度  - 资源控制  - 任务队列  - 失败重试              │
│                                                             │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐            │
│  │07:00 │ │16:00 │ │18:30 │ │03:00 │ │02:00 │            │
│  │数据  │ │数据  │ │选股  │ │健康  │ │回测  │            │
│  │更新  │ │更新  │ │推送  │ │检查  │ │报告  │            │
│  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘            │
└─────┼────────┼────────┼────────┼────────┼────────────────┘
      │        │        │        │        │
      ↓        ↓        ↓        ↓        ↓
┌─────────────────────────────────────────────────────────────┐
│                    自动化脚本层                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
│  │data_     │ │health_   │ │monitor_  │                    │
│  │update.py │ │check.py  │ │collector │                    │
│  └──────────┘ └──────────┘ └──────────┘                    │
│                                                             │
│  ┌──────────┐ ┌──────────┐                                 │
│  │run_      │ │run_      │                                 │
│  │daily.py  │ │backtest  │                                 │
│  └──────────┘ └──────────┘                                 │
└─────────────────────────────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                      数据存储层                              │
│  - factor_data.pkl  - stock_list.csv  - 日志文件            │
│  - 监控数据  - 回测报告  - 选股报告                          │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 设计原则

1. **关注点分离**
   - 脚本负责执行
   - Cron 负责调度
   - Agent 负责监控

2. **单一职责**
   - 每个脚本只做一件事
   - 每个任务有明确的输入输出

3. **最小干预**
   - Agent 只在必要时介入
   - 脚本尽可能自动化处理

4. **可观测性**
   - 所有任务都有日志
   - 关键指标可监控

## 2. 组件详解

### 2.1 自动化脚本层

#### script: data_update.py

**功能**：从数据源获取最新市场数据

**执行时机**：
- 早盘前：07:00（周一至周五）
- 收盘后：16:00（周一至周五）

**输入**：
  - 数据源配置（Tushare Pro 等）

**输出**：
  - factor_data.pkl（更新后的因子数据）
  - stock_list.csv（股票列表）
  - last_data_update.txt（更新时间戳）

**依赖**：
  - code/data_pipeline.py
  - code/data_pipeline_v2.py

**错误处理**：
  - 数据更新失败自动重试（最多 2 次）
  - 超时时间：15-20 分钟

**资源档案**：Light（轻量级，IO 密集）

---

#### script: health_check.py

**功能**：检查系统健康状态

**执行时机**：每日 03:00

**检查项**：
  - 数据完整性
  - 配置文件有效性
  - 磁盘空间
  - Python 环境
  - 日志文件轮转

**输入**：
  - 配置文件路径
  - 数据目录路径

**输出**：
  - logs/health_check.log（检查日志）
  - logs/health_check_report.json（检查报告）

**依赖**：
  - 无（仅系统工具）

**错误处理**：
  - 检查失败记录但不终止
  - 严重失败需要 Agent 介入

**资源档案**：Very Light（极轻量）

---

#### script: monitor_collector.py

**功能**：收集系统性能指标

**执行时机**：每小时（整点）

**收集项**：
  - CPU 使用率
  - 内存使用率
  - 磁盘空间
  - 任务执行状态
  - 错误日志统计
  - 选股结果统计

**输入**：
  - 系统运行状态

**输出**：
  - logs/monitoring_metrics.jsonl（时间序列数据）
  - logs/monitoring_latest.json（最新快照）

**依赖**：
  - psutil（系统监控库）

**错误处理**：
  - 收集失败跳过，记录警告
  - 不阻塞其他任务

**资源档案**：Very Light（极轻量）

---

#### script: run_backtest.py

**功能**：执行策略回测

**执行时机**：每周日 02:00

**回测策略**：
  - trend_following（趋势跟踪）
  - mean_reversion（均值回归）
  - factor_rotation（因子轮动）

**输入**：
  - 历史数据
  - 策略参数

**输出**：
  - reports/backtest_report_YYYYMMDD.json（回测报告）

**依赖**：
  - code/backtest_engine_v2.py
  - code/data_pipeline.py

**错误处理**：
  - 回测失败记录日志
  - Agent 审核回测结果

**资源档案**：Heavy（高负载，计算密集）

---

#### script: run_daily.py

**功能**：每日选股和推送（主脚本）

**执行时机**：每日 18:30（周一至周五）

**流程**：
  1. 检查交易日
  2. 加载最新数据
  3. 执行选股
  4. 风险控制
  5. 生成报告
  6. 飞书推送

**输入**：
  - factor_data.pkl
  - 配置文件

**输出**：
  - reports/daily_recommendation_YYYYMMDD.md（选股报告）
  - 飞书推送

**依赖**：
  - code/multi_factor_model.py
  - code/stock_selector.py
  - code/risk_controller.py
  - feishu_pusher.py

**错误处理**：
  - 选股失败告警通知
  - 推送失败记录日志

**资源档案**：Medium（中等负载）

---

### 2.2 Cron 调度层

#### 配置文件：config/cron_config.json

```json
{
  "tasks": [
    {
      "name": "morning_data_update",
      "schedule": "0 7 * * 1-5",
      "priority": "high",
      "resource_profile": "light",
      "dependencies": []
    },
    {
      "name": "daily_selection_push",
      "schedule": "30 18 * * 1-5",
      "priority": "critical",
      "resource_profile": "medium",
      "dependencies": ["evening_data_update"]
    }
  ],
  "scheduling_constraints": {
    "max_concurrent_tasks": 2,
    "max_concurrent_heavy_tasks": 1
  }
}
```

#### 任务调度策略

1. **基于优先级的调度**
   - Critical > High > Medium > Low

2. **资源冲突解决**
   - 高负载任务互斥
   - 总并发数控制

3. **依赖关系管理**
   - 依赖任务必须在前置任务完成后执行
   - 前置任务失败时，依赖任务跳过

4. **超时控制**
   - 每个任务设置超时时间
   - 超时后自动终止

#### 安装脚本：scripts/install_cron_tasks.sh

**功能**：根据 cron_config.json 自动生成安装 Cron 任务

**特性**：
  - 备份现有 crontab
  - 仅安装启用的任务
  - 验证安装结果
  - 提供回滚机制

### 2.3 Agent 监控层

#### Agent 介入场景

| 场景 | 触发条件 | 处理方式 |
|-----|---------|---------|
| **异常诊断** | 任务连续失败 3 次 | 分析日志，识别根因 |
| **策略优化** | 回测结果夏普 <1.0 | 调整参数，优化模型 |
| **数据异常** | 数据质量检查失败 | 重新获取数据，通知用户 |
| **系统过载** | CPU >80% 持续 5 分钟 | 建议调整任务调度 |
| **安全事件** | 配置文件篡改 | 立即停止任务，审计日志 |

#### 监控指标

**系统层面**：
  - CPU 使用率
  - 内存使用率
  - 磁盘空间
  - 网络延迟

**任务层面**：
  - 执行成功率
  - 执行时间
  - 失败原因

**业务层面**：
  - 选股准确性
  - 推送及时性
  - 回测表现

#### 告警规则

```python
# 监控/告警配置示例
alert_rules = {
    "critical": {
        "task_failure_rate": "> 5%",
        "data_update_delay": "> 1h",
        "disk_space": "< 1GB"
    },
    "warning": {
        "cpu_usage": "> 70%",
        "memory_usage": "> 80%",
        "task_timeout": "> 3x expected"
    }
}
```

#### Agent 工作流程

```
1. 监控系统检测到异常
   ↓
2. 检查告警规则
   ↓
3. 触发 Agent（如果需要智能决策）
   ↓
4. Agent 分析异常
   ↓
5. Agent 提出解决方案
   ↓
6. 用户确认（可选）
   ↓
7. 执行修复或告警
   ↓
8. 记录处理结果
```

## 3. 数据流

### 3.1 数据流向

```
┌─────────────┐
│  数据源     │ (Tushare Pro)
└──────┬──────┘
       │
       ↓
┌──────────────┐
│ data_update  │ (数据更新脚本)
└──────┬───────┘
       │
       ↓
┌──────────────┐
│factor_data   │ (因子数据)
│.pkl          │
└──────┬───────┘
       │
       ├────→ ┌──────────────┐
       │       │ monitor_     │ (监控收集)
       │       │ collector    │
       │       └──────────────┘
       │
       ├────→ ┌──────────────┐
       ↓       │ run_daily    │ (每日选股)
┌──────────────┐ │             │
│ health_check │ └──────┬───────┘
│              │        │
└──────────────┘        ↓
                ┌──────────────┐
                │选股报告      │
                │.md           │
                └──────┬───────┘
                       │
                       ↓
                ┌──────────────┐
                │飞书推送      │
                └──────────────┘
```

### 3.2 数据存储规范

**目录结构**：
```
a-stock-advisor/
├── data/
│   ├── factor_data.pkl          # 因子数据
│   ├── stock_list.csv           # 股票列表
│   └── mock_data.pkl            # 模拟数据
├── logs/
│   ├── daily_run.log            # 每日选股日志
│   ├── data_update.log          # 数据更新日志
│   ├── health_check.log         # 健康检查日志
│   ├── monitor_collector.log    # 监控收集日志
│   ├── backtest.log             # 回测日志
│   ├── monitoring_metrics.jsonl # 监控时序数据
│   ├── health_check_report.json # 健康检查报告
│   └── last_data_update.txt     # 最后更新时间
└── reports/
    ├── daily_recommendation_*.md    # 选股报告
    ├── backtest_report_*.json       # 回测报告
    └── factor_scores.json           # 因子得分配置
```

**日志格式**：
```
YYYY-MM-DD HH:MM:SS - LEVEL - Message
```

**监控数据格式**：
```json
{
  "timestamp": "2026-03-01T10:00:00",
  "cpu": {"percent": 15.2, ...},
  "memory": {"total_gb": 16.0, ...},
  "task_status": {...}
}
```

## 4. 错误处理与恢复

### 4.1 错误分类

| 错误类型 | 处理级别 | 处理方式 |
|---------|---------|---------|
| **数据更新失败** | Auto | 重试 2 次，失败后告警 |
| **选股计算失败** | Agent | Agent 分析原因 |
| **推送失败** | Log | 记录日志，手动重发 |
| **健康检查失败** | Alert | 发送告警通知 |
| **回测失败** | Log | 记录日志，后续重试 |

### 4.2 重试机制

```python
class RetryHandler:
    """重试处理器"""

    def __init__(self, max_retries=2, backoff='exponential'):
        self.max_retries = max_retries
        self.backoff = backoff

    def execute(self, task):
        """执行任务，失败时重试"""
        for attempt in range(self.max_retries + 1):
            try:
                return task.run()
            except Exception as e:
                if attempt == self.max_retries:
                    raise  # 最后一次尝试失败，抛出异常
                self._wait(attempt)  # 等待后重试

    def _wait(self, attempt):
        """退避等待"""
        if self.backoff == 'exponential':
            delay = 2 ** attempt
        else:
            delay = 5
        time.sleep(delay)
```

### 4.3 恢复策略

1. **数据损坏**
   - 从备份恢复
   - 重新获取数据

2. **配置错误**
   - 使用默认配置
   - 通知用户修正

3. **任务依赖失败**
   - 跳过依赖任务
   - 记录依赖关系

4. **系统过载**
   - 延迟低优先级任务
   - 提示用户调整调度

## 5. 部署与运维

### 5.1 部署步骤

```bash
# 1. 克隆或更新代码
cd /Users/variya/.openclaw/workspace/projects/a-stock-advisor

# 2. 安装依赖
pip3 install -r requirements.txt

# 3. 配置文件检查
cp config/feishu_config.json.sample config/feishu_config.json
# 编辑配置文件，填入 webhook_url

# 4. 创建必要的目录
mkdir -p logs reports data

# 5. 安装 Cron 任务
bash scripts/install_cron_tasks.sh

# 6. 验证安装
crontab -l | grep a-stock-advisor

# 7. 测试任务
python3 scripts/health_check.py
python3 scripts/data_update.py

# 8. 查看日志
tail -f logs/health_check.log
```

### 5.2 运维清单

**每日检查**：
- [ ] 查看任务执行状态
- [ ] 检查日志文件大小
- [ ] 确认数据更新成功

**每周检查**：
- [ ] 查看系统资源使用趋势
- [ ] 审查选股报告质量
- [ ] 检查回测结果有效性

**每月检查**：
- [ ] 清理旧日志
- [ ] 审查 cron 配置
- [ ] 评估优化效果

**每季度检查**：
- [ ] 代码审计
- [ ] 架构评估
- [ ] 需求变更分析

### 5.3 问题处理

**问题：任务未执行**
```
# 检查 cron 服务是否运行
sudo launchctl list | grep cron

# 查看 system 日志
log show --predicate 'process == "cron"' --last 1h

# 验证 cron 任务
crontab -l
```

**问题：脚本执行失败**
```
# 查看错误日志
cat logs/*.log | grep ERROR

# 手动测试脚本
python3 scripts/<script_name>.py

# 检查 Python 路径
which python3
/opt/homebrew/bin/python3 --version
```

**问题：内存占用过高**
```
# 查看进程内存
ps aux | grep python

# 查询系统内存
vm_stat

# 清理 Python 缓存
find . -type d -name __pycache__ -exec rm -rf {} +
```

## 6. 性能优化建议

### 6.1 短期优化（1-2 周）

1. **缓存优化**
   - 缓存数据更新结果
   - 避免重复计算

2. **并行化**
   - 多因子计算并行化
   - 使用多进程处理数据

3. **索引优化**
   - 为常用查询添加索引
   - 优化数据库访问

### 6.2 中期优化（1-2 个月）

1. **智能调度**
   - 基于历史数据动态调整
   - 自适应超时设置

2. **增量更新**
   - 只更新变化的数据
   - 减少 IO 开销

3. **压缩存储**
   - 压缩历史数据
   - 节省磁盘空间

### 6.3 长期优化（3-6 个月）

1. **分布式计算**
   - 大规模计算任务分布式
   - 提高处理能力

2. **实时流处理**
   - 数据流实时处理
   - 减少延迟

3. **机器学习优化**
   - 预测系统负载
   - 智能资源分配

## 7. 附录

### 7.1 环境要求

- **Python**: >= 3.8
- **操作系统**: macOS / Linux
- **内存**: >= 4GB
- **磁盘**: >= 10GB 可用空间

### 7.2 依赖列表

```
python3
pandas
numpy
psutil
requests
tushare（待配置）
```

### 7.3 相关文档

- 资源优化方案: reports/resource_optimization.md
- Cron 配置文件: config/cron_config.json
- 系统手册: MANUAL.md
- 自动化说明: README_AUTOMATION.md

---

**文档版本**: 1.0.0
**创建时间**: 2026-03-01
**最后更新**: 2026-03-01 02:30
**负责人**: 架构师
**审核**: 指挥官（待审核）
