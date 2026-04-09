#!/bin/bash
# 进出门处理脚本
# 触发条件：入户门窗传感器状态变化
# 功能：检测进出门、人脸识别、控制灯光和音箱

# ==================== 配置区域 ====================
HA_URL="${HA_URL:-http://192.168.28.77:8123}"
HA_TOKEN="${HA_TOKEN:-eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI2NzBjNDQzZjdmNTY0YzY3ODAxODkxZThkNjllZGY2YyIsImlhdCI6MTc3MzExNTYwNCwiZXhwIjoyMDg4NDc1NjA0fQ.XnQZK61FYmnLyZZttk8bC4ycDpVj567qqC_458VMtTw}"

# 设备 Entity ID
DOOR_SENSOR="binary_sensor.lumi_cn_719859620_acn001_contact_state_p_2_1"  # 入户门窗传感器
# 过道灯（最接近入户的灯）
GUODAO_LIGHTS=(
    "switch.lemesh_cn_1000766229_sw4a02_on_p_3_1"  # 中间过道灯
    "switch.lemesh_cn_1001966793_sw4a02_on_p_2_1"  # 左过道灯
    "switch.lemesh_cn_1000766229_sw4a02_on_p_12_1"  # 右过道灯
)
# 入户 Xiaomi 智能音箱
SPEAKER="media_player.xiaomi_oh2_5da4_play_control"  # Xiaomi Smart Speaker（客厅/入户）

# 萤石猫眼配置
EZVIZ_APPKEY="d78ef22ddf794dd9a2f0984d86504ff5"
EZVIZ_APPSECRET="56010e2be7d42e8881cd7fb26ec472d3"
EZVIZ_SERIAL="F66074055"

# 人脸识别脚本
FACE_SCRIPT="/home/zhangyanbo/.openclaw/workspace-fox-smarthome/scripts/face_recognition.sh"
# ==================== 配置区域 ====================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 获取猫眼最近 30 秒告警数
check_motion_alarm() {
    log "📷 检查猫眼最近 30 秒告警..."
    
    TOKEN=$(curl -s -X POST "https://open.ys7.com/api/lapp/token/get" \
        -d "appKey=$EZVIZ_APPKEY&appSecret=$EZVIZ_APPSECRET" | jq -r '.data.accessToken // empty')
    
    if [ -z "$TOKEN" ]; then
        log "❌ 获取萤石 token 失败"
        echo "0"
        return
    fi
    
    # 获取告警列表
    ALARMS=$(curl -s -X POST "https://open.ys7.com/api/lapp/alarm/list" \
        -d "accessToken=$TOKEN&deviceSerial=$EZVIZ_SERIAL&channelNo=1&type=1&limit=10")
    
    # 检查最近 30 秒的告警
    NOW=$(date +%s)
    THIRTY_SEC_AGO=$((NOW - 30))
    
    COUNT=$(echo "$ALARMS" | jq --argjson ts "$THIRTY_SEC_AGO" '
        .data.list // [] | 
        map(select(.startTime != null and (.startTime / 1000) >= $ts)) | 
        length
    ')
    
    log "📊 最近 30 秒告警数：$COUNT"
    echo "$COUNT"
}

# 猫眼抓图
capture_image() {
    log "📸 猫眼抓图..."
    
    TOKEN=$(curl -s -X POST "https://open.ys7.com/api/lapp/token/get" \
        -d "appKey=$EZVIZ_APPKEY&appSecret=$EZVIZ_APPSECRET" | jq -r '.data.accessToken // empty')
    
    if [ -z "$TOKEN" ]; then
        log "❌ 获取萤石 token 失败"
        return 1
    fi
    
    PIC_URL=$(curl -s -X POST "https://open.ys7.com/api/lapp/device/capture" \
        -d "accessToken=$TOKEN&deviceSerial=$EZVIZ_SERIAL&channelNo=1" | jq -r '.data.picUrl // empty')
    
    if [ -n "$PIC_URL" ]; then
        curl -s -L "$PIC_URL" -o /tmp/openclaw/face_zhangyanbo.jpg
        if [ -s /tmp/openclaw/face_zhangyanbo.jpg ]; then
            log "✅ 抓图成功：/tmp/openclaw/face_zhangyanbo.jpg"
            return 0
        fi
    fi
    
    log "❌ 抓图失败"
    return 1
}

# 开灯
turn_on_lights() {
    log "💡 开启过道灯..."
    for light in "${GUODAO_LIGHTS[@]}"; do
        curl -s -X POST "$HA_URL/api/services/switch/turn_on" \
            -H "Authorization: Bearer $HA_TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"entity_id\":\"$light\"}"
    done
}

# 关灯
turn_off_lights() {
    log "💡 关闭过道灯..."
    for light in "${GUODAO_LIGHTS[@]}"; do
        curl -s -X POST "$HA_URL/api/services/switch/turn_off" \
            -H "Authorization: Bearer $HA_TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"entity_id\":\"$light\"}"
    done
}

# 播放欢迎语
play_welcome() {
    local message="$1"
    log "📢 播放欢迎语：$message"
    
    # 使用小爱音箱 TTS
    curl -s -X POST "$HA_URL/api/services/tts.baidu_speak" \
        -H "Authorization: Bearer $HA_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"entity_id\": \"$SPEAKER\",
            \"message\": \"$message\"
        }"
}

# 主逻辑
main() {
    log "========================================="
    log "🚪 进出门检测启动"
    log "========================================="
    
    # 获取门状态（URL 编码）
    DOOR_SENSOR_ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$DOOR_SENSOR', safe=''))")
    DOOR_STATE=$(curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/$DOOR_SENSOR_ENCODED" | jq -r '.state // "unknown"')
    log "🚪 门状态：$DOOR_STATE"
    
    if [ "$DOOR_STATE" != "on" ]; then
        log "ℹ️  门未打开，退出"
        exit 0
    fi
    
    # 检查猫眼告警判断进出门
    ALARM_COUNT=$(check_motion_alarm)
    
    if [ "$ALARM_COUNT" -gt 0 ]; then
        # 进门场景
        log "🏠 检测到进门（有猫眼告警）"
        
        # 开灯
        turn_on_lights
        
        # 抓图并识别人脸
        if capture_image; then
            if bash "$FACE_SCRIPT"; then
                # 识别成功，是主人
                play_welcome "欢迎小王子回家"
            else
                # 识别失败或不是主人
                play_welcome "欢迎回家"
            fi
        else
            # 抓图失败，播放通用欢迎语
            play_welcome "欢迎回家"
        fi
        
        # 30 秒后关灯
        log "⏱️  等待 30 秒后关灯..."
        sleep 30
        turn_off_lights
        
    else
        # 出门场景
        log "👋 检测到出门（无猫眼告警）"
        
        # 开灯 30 秒
        turn_on_lights
        log "⏱️  等待 30 秒后关灯..."
        sleep 30
        turn_off_lights
        
        # 出门不播放欢迎语
        log "ℹ️  出门场景，不播放欢迎语"
    fi
    
    log "========================================="
    log "✅ 进出门处理完成"
    log "========================================="
}

main "$@"
