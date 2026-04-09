#!/bin/bash
# 进出门检测脚本 v2 - 进门和出门独立流程

export HA_URL="http://192.168.28.77:8123"
export HA_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI2NzBjNDQzZjdmNTY0YzY3ODAxODkxZThkNjllZGY2YyIsImlhdCI6MTc3MzExNTYwNCwiZXhwIjoyMDg4NDc1NjA0fQ.XnQZK61FYmnLyZZttk8bC4ycDpVj567qqC_458VMtTw"

# 萤石猫眼配置
EZVIZ_APPKEY="d78ef22ddf794dd9a2f0984d86504ff5"
EZVIZ_APPSECRET="56010e2be7d42e8881cd7fb26ec472d3"
EZVIZ_SERIAL="F66074055"

# 设备配置
GUODAO_LIGHTS=(
    "switch.lemesh_cn_1000766229_sw4a02_on_p_3_1"  # 中间过道灯
    "switch.lemesh_cn_1001966793_sw4a02_on_p_2_1"  # 左过道灯
    "switch.lemesh_cn_1000766229_sw4a02_on_p_12_1"  # 右过道灯
)
SPEAKER="media_player.xiaomi_oh2_5da4_play_control"  # 入户 Xiaomi Smart Speaker

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 开过道灯
turn_on_lights() {
    log "💡 开启过道灯..."
    for light in "${GUODAO_LIGHTS[@]}"; do
        curl -s -X POST "$HA_URL/api/services/switch/turn_on" \
            -H "Authorization: Bearer $HA_TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"entity_id\":\"$light\"}" > /dev/null
    done
}

# 关过道灯
turn_off_lights() {
    log "💡 关闭过道灯..."
    for light in "${GUODAO_LIGHTS[@]}"; do
        curl -s -X POST "$HA_URL/api/services/switch/turn_off" \
            -H "Authorization: Bearer $HA_TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"entity_id\":\"$light\"}" > /dev/null
    done
}

# 播放欢迎语
play_welcome() {
    local message="$1"
    log "📢 播放欢迎语：$message"
    
    # 使用 media_player.play_media 播放 TTS
    curl -s -X POST "$HA_URL/api/services/media_player/play_media" \
        -H "Authorization: Bearer $HA_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"entity_id\": \"$SPEAKER\",
            \"media_content_type\": \"text\",
            \"media_content_id\": \"$message\"
        }" > /dev/null
    
    log "✅ 播放请求已发送"
}

# 发送飞书通知
send_feishu_notification() {
    local event_type="$1"  # enter 或 leave
    local image_path="$2"
    
    log "📱 发送飞书通知：$event_type"
    
    # 准备消息内容
    if [ "$event_type" = "enter" ]; then
        message="🏠 小王子回家了！

时间：$(date '+%Y-%m-%d %H:%M:%S')
🎵 已播放：欢迎啵啵小王子回家！"
    else
        message="👋 小王子出门了

时间：$(date '+%Y-%m-%d %H:%M:%S')"
    fi
    
    # 使用系统 message 工具发送
    openclaw message send \
        --channel=feishu \
        --target=ou_0671c63ec5781695e9ca1ec20c78f94e \
        --message="$message" > /dev/null 2>&1 && \
        log "✅ 飞书通知发送成功" || \
        log "⚠️ 飞书通知发送失败（可能需要授权）"
}

# 猫眼抓图（获取告警图片，不是实时抓图）
capture_image() {
    log "📸 获取告警图片..."
    TOKEN=$(curl -s -X POST "https://open.ys7.com/api/lapp/token/get" \
        -d "appKey=$EZVIZ_APPKEY&appSecret=$EZVIZ_APPSECRET" | jq -r '.data.accessToken // empty')
    
    if [ -n "$TOKEN" ]; then
        # 获取最近一次告警的图片（告警时的照片，不是实时抓图）
        ALARM_DATA=$(curl -s -X POST "https://open.ys7.com/api/lapp/alarm/device/list" \
            -d "accessToken=$TOKEN&deviceSerial=$EZVIZ_SERIAL&channelNo=1&type=1&pageStart=0&pageSize=1")
        
        PIC_URL=$(echo "$ALARM_DATA" | jq -r '.data.list[0].alarmPicUrl // empty')
        
        if [ -n "$PIC_URL" ]; then
            curl -s -L "$PIC_URL" -o /tmp/openclaw/face_zhangyanbo.jpg
            if [ -s /tmp/openclaw/face_zhangyanbo.jpg ]; then
                log "✅ 获取告警图片成功：/tmp/openclaw/face_zhangyanbo.jpg"
                return 0
            fi
        fi
        
        # 如果告警图片获取失败，再尝试实时抓图
        log "⚠️ 告警图片获取失败，尝试实时抓图..."
        PIC_URL=$(curl -s -X POST "https://open.ys7.com/api/lapp/device/capture" \
            -d "accessToken=$TOKEN&deviceSerial=$EZVIZ_SERIAL&channelNo=1" | jq -r '.data.picUrl // empty')
        if [ -n "$PIC_URL" ]; then
            curl -s -L "$PIC_URL" -o /tmp/openclaw/face_zhangyanbo.jpg
            if [ -s /tmp/openclaw/face_zhangyanbo.jpg ]; then
                log "✅ 实时抓图成功：/tmp/openclaw/face_zhangyanbo.jpg"
                return 0
            fi
        fi
    fi
    log "❌ 抓图失败"
    return 1
}

# 人脸识别
face_recognition() {
    log "🔍 人脸识别..."
    if [ -f /tmp/openclaw/face_zhangyanbo.jpg ]; then
        result=$(python3 /home/zhangyanbo/.openclaw/workspace-fox-smarthome/scripts/aliyun_face.py search /tmp/openclaw/face_zhangyanbo.jpg 2>/dev/null)
        entity_id=$(echo "$result" | jq -r '.entity_id // empty')
        score=$(echo "$result" | jq -r '.score // 0')
        
        log "🎯 识别结果：$entity_id (相似度：$score%)"
        
        if [ "$entity_id" = "zhangyanbo" ] && [ "$(echo "$score > 80" | bc)" -eq 1 ]; then
            return 0  # 是主人
        fi
    fi
    return 1  # 不是主人或识别失败
}

# ==================== 进门流程 ====================
door_enter() {
    log "========================================="
    log "🏠 检测到进门"
    log "========================================="
    
    # 1. 开灯
    turn_on_lights
    
    # 2. 播放欢迎语（通用）
    play_welcome "欢迎啵啵小王子回家！"
    
    # 3. 发送飞书通知
    send_feishu_notification "enter" "/tmp/openclaw/face_zhangyanbo.jpg"
    
    # 4. 等待 30 秒后关灯
    log "⏱️  等待 30 秒后关灯..."
    sleep 30
    turn_off_lights
    
    log "✅ 进门流程完成"
    log "========================================="
}

# ==================== 出门流程 ====================
door_leave() {
    log "========================================="
    log "👋 检测到出门"
    log "========================================="
    
    # 1. 开灯
    turn_on_lights
    
    # 2. 发送飞书通知
    send_feishu_notification "leave" ""
    
    # 3. 等待 30 秒后关灯（不播放欢迎语）
    log "⏱️  等待 30 秒后关灯..."
    sleep 30
    turn_off_lights
    
    log "ℹ️  出门流程完成（不播放欢迎语）"
    log "========================================="
}

# ==================== 主流程 ====================
main() {
    log "🚪 进出门检测启动"
    
    # 查猫眼最近 30 秒告警
    log "📷 检查猫眼最近 30 秒告警..."
    TOKEN=$(curl -s -X POST "https://open.ys7.com/api/lapp/token/get" \
        -d "appKey=$EZVIZ_APPKEY&appSecret=$EZVIZ_APPSECRET" | jq -r '.data.accessToken // empty')
    
    if [ -z "$TOKEN" ]; then
        log "❌ 获取萤石 token 失败，默认按出门处理"
        door_leave
        return
    fi
    
    # 等待 30 秒让猫眼产生告警（猫眼告警延迟约 25-30 秒）
    log "⏱️  等待 30 秒让猫眼产生告警..."
    sleep 30
    
    # 获取告警列表（最近 300 秒，所有类型告警）
    NOW_MS=$(date +%s%3N)
    START_MS=$((NOW_MS - 300000))  # 最近 300 秒（5 分钟）
    
    log "⏱️  查询时间窗口：最近 300 秒（5 分钟）"
    
    RESULT=$(curl -s -X POST "https://open.ys7.com/api/lapp/alarm/device/list" \
        -d "accessToken=$TOKEN&deviceSerial=$EZVIZ_SERIAL&channelNo=1&startTime=$START_MS&pageStart=0&pageSize=20")
    
    # API 返回的 data 直接是数组
    ALARM_COUNT=$(echo "$RESULT" | jq '.data | length // 0')
    
    log "📊 告警数量：$ALARM_COUNT"
    
    # 优先判断进门（有告警=进门）
    if [ "$ALARM_COUNT" -gt 0 ]; then
        log "✅ 检测到猫眼告警 → 判断为进门"
        door_enter
    else
        log "ℹ️  无猫眼告警 → 判断为出门"
        door_leave
    fi
}

main "$@"
