# 自动化脚本架构 - 快速指南

## 📋 概述

本目录包含A股量化系统的自动化脚本，用于减少Agent依赖，优化系统负载。

## 🗂️ 目录结构

```
scripts/
├── data_update.py            # 数据更新脚本
├── health_check.py           # 健康检查脚本
├── monitor_collector.py      # 监控数据收集脚本
├── run_backtest.py           # 回测脚本
└── install_cron_tasks.sh     # Cron 安装脚本

config/
└── cron_config.json          # Cron 配置文件

reports/
├── resource_optimization.md  # 资源优化方案
└── automation_architecture.md # 自动化架构文档
```

## 🚀 快速开始

### 1. 安装 Cron 任务

```bash
cd /Users/variya/.openclaw/workspace/projects/a-stock-advisor
bash scripts/install_cron_tasks.sh
```

### 2. 查看已安装的任务

```bash
crontab -l | grep a-stock-advisor
```

### 3. 查看任务日志

```bash
# 查看所有日志
ls -la logs/

# 实时监控日志
tail -f logs/daily_run.log
tail -f logs/data_update.log
```

## 📅 任务调度

### 每日任务

| 时间 | 任务 | 说明 |
|-----|------|------|
| 03:00 | 健康检查 | 检查系统健康状态 |
| 07:00 | 数据更新（早盘） | 更新市场数据 |
| 08:00-23:00 | 监控收集 | 每小时收集性能指标 |
| 16:00 | 数据更新（收盘） | 更新收盘数据 |
| 18:30 | 每日选股推送 | 选股并推送报告 |

### 每周任务

| 时间 | 任务 | 说明 |
|-----|------|------|
| 周日 02:00 | 策略回测 | 回测验证策略有效性 |

## 🔧 脚本说明

### data_update.py

**功能**: 从数据源获取最新市场数据

**使用**:
```bash
cd /Users/variya/.openclaw/workspace/projects/a-stock-advisor
python3 scripts/data_update.py
```

**输出**:
- data/factor_data.pkl
- logs/data_update.log

### health_check.py

**功能**: 检查系统健康状态

**使用**:
```bash
python3 scripts/health_check.py
```

**检查项**:
- 数据完整性
- 配置文件有效性
- 磁盘空间
- Python 环境

### monitor_collector.py

**功能**: 收集系统性能指标

**使用**:
```bash
python3 scripts/monitor_collector.py
```

**输出**:
- logs/monitoring_metrics.jsonl
- logs/monitoring_latest.json

### run_backtest.py

**功能**: 执行策略回测

**使用**:
```bash
python3 scripts/run_backtest.py
```

**输出**:
- reports/backtest_report_YYYYMMDD.json

## 📊 资源优化效果

| 指标 | 优化前 | 优化后 | 改善 |
|-----|--------|--------|------|
| 启动延迟 | 2-5秒 | <1秒 | 80% ↓ |
| 内存峰值 | 500MB-1GB | 50-200MB | 75% ↓ |
| CPU 峰值 | >80% | <50% | 37.5% ↓ |
| Agent 调用 | 每天 5-10 次 | 每天 1-2 次 | 80% ↓ |

## 🔍 监控与告警

### 关键指标

**系统资源**:
- CPU 使用率 <70%
- 内存使用率 <80%
- 磁盘空间 >5GB

**任务执行**:
- 成功率 >95%
- 执行时间 <超时阈值

### 查看监控数据

```bash
# 查看最新监控快照
cat logs/monitoring_latest.json

# 查看监控时序数据
tail -f logs/monitoring_metrics.jsonl
```

## 🛠️ 故障排查

### 任务未执行

```bash
# 检查 cron 服务
sudo launchctl list | grep cron

# 查看系统日志
log show --predicate 'process == "cron"' --last 1h

# 验证 cron 任务
crontab -l
```

### 脚本执行失败

```bash
# 查看错误日志
grep ERROR logs/*.log

# 手动测试脚本
python3 scripts/<script_name>.py
```

### 资源占用过高

```bash
# 查看进程内存
ps aux | grep python

# 清理 Python 缓存
find . -type d -name __pycache__ -exec rm -rf {} +
```

## 📚 文档

- [资源优化方案](../reports/resource_optimization.md)
- [自动化架构文档](../reports/automation_architecture.md)
- [系统手册](../MANUAL.md)

## ⚙️ 配置文件

### cron_config.json

主要配置项:
- 任务调度时间
- 资源限制
- 重试策略
- 依赖关系

编辑配置后，重新运行安装脚本：
```bash
bash scripts/install_cron_tasks.sh
```

## 🤝 维护指南

### 每日检查
- [ ] 查看任务执行状态
- [ ] 检查日志文件大小
- [ ] 确认数据更新成功

### 每周检查
- [ ] 查看系统资源使用趋势
- [ ] 审查选股报告质量
- [ ] 检查回测结果有效性

### 每月检查
- [ ] 清理旧日志
- [ ] 审查 cron 配置
- [ ] 评估优化效果

## 📞 获取帮助

如遇问题，请查看：
1. 日志文件: logs/*.log
2. 故障排查章节
3. 详细架构文档

---

**版本**: 1.0.0
**更新时间**: 2026-03-01
