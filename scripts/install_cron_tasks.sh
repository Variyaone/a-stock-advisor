#!/bin/bash
#
# 自动化任务 Cron 安装脚本
# 基于 config/cron_config.json 生成 cron 任务
#

set -e  # 遇到错误立即退出

WORKSPACE="/Users/variya/.openclaw/workspace/projects/a-stock-advisor"
CONFIG_FILE="$WORKSPACE/config/cron_config.json"
PYTHON_PATH="/opt/homebrew/bin/python3"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查配置文件是否存在
if [ ! -f "$CONFIG_FILE" ]; then
    log_error "配置文件不存在: $CONFIG_FILE"
    exit 1
fi

log_info "读取配置文件: $CONFIG_FILE"

# 检查 jq 是否安装（用于解析 JSON）
if ! command -v jq &> /dev/null; then
    log_error "jq 未安装，请先安装: brew install jq"
    exit 1
fi

log_info "备份现有 crontab..."
BACKUP_FILE="/tmp/crontab_backup_$(date +%Y%m%d_%H%M%S)"
crontab -l > "$BACKUP_FILE" 2>/dev/null || touch "$BACKUP_FILE"

# 收集所有任务
TASKS=()
ENABLED_TASKS=()

# 解析配置文件，提取所有任务
TASK_COUNT=$(jq '.tasks | length' "$CONFIG_FILE")

for ((i=0; i<TASK_COUNT; i++)); do
    NAME=$(jq -r ".tasks[$i].name" "$CONFIG_FILE")
    ENABLED=$(jq -r ".tasks[$i].enabled" "$CONFIG_FILE")
    SCHEDULE=$(jq -r ".tasks[$i].schedule" "$CONFIG_FILE")
    COMMAND=$(jq -r ".tasks[$i].command" "$CONFIG_FILE")

    if [ "$ENABLED" = "true" ]; then
        ENABLED_TASKS+=("$NAME|$SCHEDULE|$COMMAND")
        TASKS+=("$NAME")
    else
        log_warn "任务已禁用: $NAME"
    fi
done

log_info "找到 ${#ENABLED_TASKS[@]} 个启用的任务"

# 临时文件用于存储新的 crontab
TEMP_CRON="/tmp/new_crontab_$$.txt"

# 复制备份文件，但删除本项目的旧任务
grep -v "a-stock-advisor" "$BACKUP_FILE" > "$TEMP_CRON" 2>/dev/null || true

# 添加注释头
echo "" >> "$TEMP_CRON"
echo "# ========== A股量化系统自动化任务 ==========" >> "$TEMP_CRON"
echo "# 配置文件: config/cron_config.json" >> "$TEMP_CRON"
echo "# 更新时间: $(date '+%Y-%m-%d %H:%M:%S')" >> "$TEMP_CRON"
echo "# ===========================================" >> "$TEMP_CRON"
echo "" >> "$TEMP_CRON"

# 添加所有启用的任务
for task_info in "${ENABLED_TASKS[@]}"; do
    IFS='|' read -r NAME SCHEDULE COMMAND <<< "$task_info"

    # 验证命令格式
    if [[ ! "$COMMAND" == *"$WORKSPACE"* ]]; then
        log_warn "任务 $NAME 的命令可能缺少工作目录，尝试修正..."
        COMMAND="cd $WORKSPACE && $COMMAND"
    fi

    # 添加到 crontab
    echo "$SCHEDULE $COMMAND" >> "$TEMP_CRON"

    log_info "已添加: $NAME ($SCHEDULE)"
done

echo "" >> "$TEMP_CRON"

# 安装新的 crontab
log_info "安装新的 crontab..."
crontab "$TEMP_CRON"

# 验证安装
log_info "验证安装结果..."
INSTALLED_COUNT=$(crontab -l | grep -c "a-stock-advisor" || true)

if [ "$INSTALLED_COUNT" -eq "${#ENABLED_TASKS[@]}" ]; then
    log_info "✅ 所有可能任务已成功安装！"
else
    log_warn "警告: 安装的任务数量 (${#ENABLED_TASKS[@]}) 与验证结果 ($INSTALLED_COUNT) 不一致"
fi

# 显示已安装的任务
echo ""
log_info "已安装的任务列表:"
echo ""
crontab -l | grep "a-stock-advisor" | while read -r line; do
    echo "  - $line"
done

echo ""
echo "="=60
log_info "Cron 任务安装完成"
echo "="=60
echo ""
echo "📋 查看所有 cron 任务:  crontab -l"
echo "📝 编辑 cron 任务:      crontab -e"
echo "🔍 查看任务日志:       tail -f logs/*.log"
echo "🗑️ 删除所有任务:       crontab -l | grep -v 'a-stock-advisor' | crontab -"
echo ""
log_info "备份文件: $BACKUP_FILE"
log_info "临时文件: $TEMP_CRON"

# 清理临时文件
# rm -f "$TEMP_CRON"
# log_info "临时文件已清理"
