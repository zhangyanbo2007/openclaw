#!/bin/bash
# 门状态持续监控脚本
# 每秒检测门状态，开门时自动执行进出门处理

export HA_URL="http://192.168.28.77:8123"
export HA_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI2NzBjNDQzZjdmNTY0YzY3ODAxODkxZThkNjllZGY2YyIsImlhdCI6MTc3MzExNTYwNCwiZXhwIjoyMDg4NDc1NjA0fQ.XnQZK61FYmnLyZZttk8bC4ycDpVj567qqC_458VMtTw"

DOOR_SENSOR="binary_sensor.lumi_cn_719859620_acn001_contact_state_p_2_1"
DOOR_HANDLER="/home/zhangyanbo/.openclaw/workspace-fox-smarthome/scripts/door_handler.sh"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "🔍 开始监控门状态..."
log "📍 门传感器：$DOOR_SENSOR"
log "⏱️  检测间隔：1 秒"
log "按 Ctrl+C 停止监控"
echo ""

LAST_STATE="unknown"

while true; do
    # 获取门状态
    STATE=$(curl -s -H "Authorization: Bearer $HA_TOKEN" \
        "$HA_URL/api/states/$DOOR_SENSOR" 2>/dev/null | \
        python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('state','unknown'))" 2>/dev/null || echo "error")
    
    # 检测状态变化
    if [ "$STATE" != "$LAST_STATE" ]; then
        if [ "$STATE" = "on" ]; then
            log "🚪 门打开了！触发进出门处理..."
            bash "$DOOR_HANDLER" 2>&1 | while read line; do log "$line"; done
        else
            log "🚪 门关闭了"
        fi
        LAST_STATE="$STATE"
    fi
    
    sleep 1
done
