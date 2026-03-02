# 📅 定时任务状态说明

## ✅ 当前状态

**Cron任务已安装且正常工作**

```bash
# 查看定时任务
crontab -l | grep run_daily
```

输出:
```
30 18 * * 1-5 cd /Users/variya/.openclaw/workspace/projects/a-stock-advisor && /opt/homebrew/bin/python3 run_daily.py >> logs/daily_run.log 2>&1
```

## 📋 任务配置

| 配置项 | 值 |
|--------|-----|
| **运行时间** | 每周一至周五 18:30 |
| **工作目录** | /Users/variya/.openclaw/workspace/projects/a-stock-advisor |
| **执行脚本** | run_daily.py |
| **日志文件** | /Users/variya/.openclaw/workspace/projects/a-stock-advisor/logs/daily_run.log |
| **Python路径** | /opt/homebrew/bin/python3 |

## 🧪 测试系统

### 快速测试（立即可用）

```bash
cd /Users/variya/.openclaw/workspace/projects/a-stock-advisor
python3 quick_test.py
```

**测试结果**（2026-02-28 15:49）:
- ✅ 数据加载: 261,000 条记录
- ✅ 选股池: 200 只股票
- ✅ 成功选出 Top 10

### 完整测试

```bash
./test_system.sh
```

### 手动运行（忽略周末检测）

```bash
python3 quick_test.py
```

### 查看定时任务日志

```bash
# 实时查看
tail -f logs/daily_run.log

# 查看最近日志
cat logs/daily_run.log
```

## ⚠️ 关于周末检测

系统会自动检测周末，**不会在周六、周日推送选股结果**。

**原因**: 周末不开市，不需要交易日分析。

**如果你想强制测试**:
```bash
python3 quick_test.py    # 忽略周末，立即执行
```

## 🛠️ 管理定时任务

### 查看所有Cron任务
```bash
crontab -l
```

### 编辑Cron任务
```bash
crontab -e
```

### 删除A股定时任务
```bash
crontab -l | grep -v run_daily | crontab -
```

### 重新安装定时任务
```bash
bash install_cron.sh
```

## 📦 系统文件结构

```
a-stock-advisor/
├── run_daily.py              # 主运行脚本（有周末检测）
├── quick_test.py             # 快速测试脚本（忽略周末）
├── install_cron.sh           # Cron安装脚本
├── test_system.sh            # 系统测试脚本
├── logs/
│   └── daily_run.log         # 运行日志
└── reports/                  # 选股报告目录
```

## 🎯 下一次自动运行

**时间**: 下周一 18:30

系统会自动:
1. 加载最新市场数据
2. 计算因子得分
3. 生成Top 10选股建议
4. 输出到日志文件

## 💡 故障排查

### 如果没看到日志文件

**原因**: 当前是周末，定时任务跳过了运行

**解决**:
```bash
# 1. 手动运行测试
python3 quick_test.py

# 2. 查看当前日志
ls -la logs/
```

### 如果Cron任务未执行

**检查**:
```bash
# 1. 确认Cron任务存在
crontab -l | grep run_daily

# 2. 检查Python路径
which python3

# 3. 手动执行脚本
python3 run_daily.py
```

### 如果Python路径错误

**修复**:
```bash
# 编辑Cron任务
crontab -e

# 将 /usr/bin/python3 改为 /opt/homebrew/bin/python3
# 或运行:
bash install_cron.sh
```

## ✅ 系统已就绪

- ✅ Cron定时任务已安装
- ✅ Python路径已修复
- ✅ 测试脚本运行成功
- ✅ 选股功能正常工作

**系统将在每个工作日18:30自动运行，无需人工干预！**

---

*更新时间: 2026-02-28 15:50*
*状态: ✅ 系统正常运行*
