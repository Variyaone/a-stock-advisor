# A股量化系统 - 自动化运行指南

## 系统概述

本系统每个交易日收盘后自动运行，生成A股选股建议并推送到飞书。

## 运行时间

- **推送时间**: 每周一至周五 18:30
- **数据日期**: 上一个交易日收盘
- **推送内容**: Top 10推荐股票 + 因子得分 + 买入理由

## 手动运行

```bash
cd /Users/variya/.openclaw/workspace/projects/a-stock-advisor
python3 run_daily.py
```

## 配置飞书推送

### 方式1: 使用配置文件（推荐）

1. 在飞书群中添加自定义机器人，获取Webhook URL
2. 复制Webhook URL
3. 创建配置文件:

```bash
cp config/.sample/feishu_config.json config/feishu_config.json
```

4. 编辑配置文件，填入webhook_url:

```json
{
  "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx",
  "enabled": true,
  "push_time": "18:35",
  "timezone": "Asia/Shanghai"
}
```

### 方式2: 使用环境变量

```bash
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx"
```

## 安装定时任务

### 自动安装

```bash
cd /Users/variya/.openclaw/workspace/projects/a-stock-advisor
./install_cron.sh
```

### 手动安装

1. 查看当前crontab: `crontab -l`
2. 编辑crontab: `crontab -e`
3. 添加以下内容:

```cron
30 18 * * 1-5 cd /Users/variya/.openclaw/workspace/projects/a-stock-advisor && /usr/bin/python3 run_daily.py >> logs/daily_run.log 2>&1
```

## 查看日志

```bash
# 实时查看日志
tail -f logs/daily_run.log

# 查看最近100行
tail -100 logs/daily_run.log

# 查看完整日志
cat logs/daily_run.log

# 搜索错误
grep "ERROR\|错误\|失败" logs/daily_run.log
```

## 停止定时任务

```bash
# 方法1: 编辑crontab，删除对应行
crontab -e

# 方法2: 使用sed删除
crontab -l | grep -v "run_daily.py" | crontab -
```

## 运行测试

```bash
cd /Users/variya/.openclaw/workspace/projects/a-stock-advisor
./test_automation.sh
```

## 故障排查

### 问题: Cron任务未运行

**症状**: 18:30后没有生成报告和日志

**排查步骤**:

1. 检查Cron配置: `crontab -l`

2. 检查Python路径: `which python3`

   如果不是 `/usr/bin/python3`，需要修改cron表达式中的python3路径

3. 查看系统日志（查看cron执行记录）:

   ```bash
   grep CRON /var/log/system.log | tail -20
   ```

4. 手动运行测试:

   ```bash
   cd /Users/variya/.openclaw/workspace/projects/a-stock-advisor
   python3 run_daily.py
   ```

### 问题: 飞书推送失败

**症状**: 日志显示 "✗ 飞书推送失败"

**排查步骤**:

1. 检查webhook配置:

   ```bash
   cat config/feishu_config.json
   ```

2. 测试webhook是否有效:

   ```bash
   curl -X POST "你的webhook_url" \
     -H "Content-Type: application/json" \
     -d '{"msg_type":"text","content":{"text":"测试消息"}}'
   ```

3. 检查网络连接

4. 查看错误日志: `grep "飞书推送" logs/daily_run.log`

### 问题: 报告未生成

**症状**: 选股成功但没有生成报告

**排查步骤**:

1. 检查数据是否存在: `ls -lh data/`

2. 检查reports目录权限: `ls -ld reports/`

3. 手动运行测试: `python3 run_daily.py`

4. 查看完整错误信息: `tail -50 logs/daily_run.log`

### 问题: 数据加载失败

**症状**: 日志显示 "未找到数据" 或 "数据加载失败"

**排查步骤**:

1. 检查数据文件:

   ```bash
   ls -lh data/
   ```

2. 如果factor_data.pkl不存在，系统会自动使用mock_data.pkl

3. 检查Python依赖:

   ```bash
   python3 -c "import pandas; import numpy"
   ```

### 问题: Python依赖缺失

**症状**: `ModuleNotFoundError: No module named 'xxx'`

**解决方法**:

```bash
# 安装pandas
pip3 install pandas numpy requests

# 或使用requirements.txt（如果存在）
pip3 install -r requirements.txt
```

## 系统架构

```
run_daily.py (主程序)
    ├── get_trading_day_check()    # 检查交易日
    ├── load_latest_config()       # 加载配置
    │   ├── factor_scores.json     # 因子得分
    │   ├── MultiFactorScoreModel  # 得分模型
    │   ├── StockSelector          # 选股器
    │   └── RiskController         # 风险控制器
    ├── load_latest_data()         # 加载数据
    │   ├── factor_data.pkl        # 因子数据
    │   └── stock_list.csv         # 股票列表
    ├── select_top_stocks()        # 执行选股
    ├── apply_all_controls()       # 风险控制
    │   ├── ST股票过滤
    │   ├── 停牌股票过滤
    │   └── 退市股票过滤
    ├── generate_daily_recommendation()  # 生成报告
    └── FeishuPusher.send_report()       # 飞书推送
```

## 日志说明

系统日志保存在 `logs/daily_run.log`，内容包括：

- [INFO] 正常运行信息
- [WARN] 警告信息（如周末跳过）
- [ERROR] 错误信息（推送失败、数据加载失败等）

建议定期清理日志文件，避免日志过大：

```bash
# 删除7天前的日志
find logs -name "*.log" -mtime +7 -delete
```

## 更新系统

如果更新了代码，需要重启Cron任务：

```bash
# 删除旧的cron任务
crontab -l | grep -v "run_daily.py" | crontab -

# 重新安装
./install_cron.sh
```

## 联系支持

如遇问题，请：

1. 查看日志: `tail -100 logs/daily_run.log`
2. 运行测试: `./test_automation.sh`
3. 收集错误信息以便反馈

---

*Created by: 创作者*
*Date: 2026-02-28*
*Last updated: 2026-02-28*
