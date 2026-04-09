#!/bin/bash
# 轻量级门状态监控 - 每 5 秒检查一次（低开销）

export HA_URL="http://192.168.28.77:8123"
export HA_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI2NzBjNDQzZjdmNTY0YzY3ODAxODkxZThkNjllZGY2YyIsImlhdCI6MTc3MzExNTYwNCwiZXhwIjoyMDg4NDc1NjA0fQ.XnQZK61FYmnLyZZttk8bC4ycDpVj567qqC_458VMtTw"

DOOR_SENSOR="binary_sensor.lumi_cn_719859620_acn001_contact_state_p_2_1"
DOOR_HANDLER="/home/zhangyanbo/.openclaw/workspace-fox-smarthome/scripts/door_handler.sh"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "🔍 启动轻量级门监控..."
log "⏱️  检测间隔：5 秒"
log "💾 资源占用：极低"

LAST_STATE="unknown"

while true; do
    STATE=$(curl -s -H "Authorization: Bearer $HA_TOKEN" \
        "$HA_URL/api/states/$DOOR_SENSOR" 2>/dev/null | \
        python3 -c "import sys,json; print(json.load(sys.stdin).get('state','error'))" 2>/dev/null)
    
    if [ "$STATE" != "$LAST_STATE" ] && [ "$STATE" != "error" ]; then
        log "🚪 门状态：$LAST_STATE → $STATE"
        
        if [ "$STATE" = "on" ]; then
            log "🚪 门开了！执行进出门处理..."
            bash "$DOOR_HANDLER" 2>&1 | while read line; do log "$line"; done
        fi
        
        LAST_STATE="$STATE"
    fi
    
    sleep 5
done
