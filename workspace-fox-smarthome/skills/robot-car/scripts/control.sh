#!/bin/bash
# Robot Car Control Script
# OpenClaw 调用这个脚本来控制树莓派小车

# ============ 配置 ============
API_BASE="${ROBOT_CAR_API:-http://raspberrypi.local:5000}"
TIMEOUT=10

# ============ 辅助函数 ============

# 发送 POST 请求
post() {
    local endpoint="$1"
    local data="$2"
    curl -s -X POST "$API_BASE$endpoint" \
        -H "Content-Type: application/json" \
        -d "$data" \
        --max-time $TIMEOUT
}

# 发送 GET 请求
get() {
    local endpoint="$1"
    curl -s "$API_BASE$endpoint" \
        --max-time $TIMEOUT
}

# ============ 基础功能 ============

# 健康检查
status() {
    get "/status"
}

# 拍照
snapshot() {
    get "/camera/snapshot"
}

# 视频流 URL
stream_url() {
    echo "$API_BASE/camera/stream"
}

# ============ 移动控制 ============

# 移动
# 用法: move <direction> [steps] [speed]
move() {
    local direction="$1"
    local steps="${2:-1}"
    local speed="${3:-50}"
    
    post "/car/move" "{
        \"direction\": \"$direction\",
        \"steps\": $steps,
        \"speed\": $speed
    }"
}

# 前进
forward() {
    move "forward" "$@"
}

# 后退
backward() {
    move "backward" "$@"
}

# 左转
left() {
    move "left" "$@"
}

# 右转
right() {
    move "right" "$@"
}

# 停止
stop() {
    move "stop"
}

# ============ 机械臂控制 ============

# 移动到坐标
# 用法: arm_move_to <x> <y> <z> [speed]
arm_move_to() {
    local x="$1"
    local y="$2"
    local z="$3"
    local speed="${4:-50}"
    
    post "/arm/moveTo" "{
        \"x\": $x,
        \"y\": $y,
        \"z\": $z,
        \"speed\": $speed
    }"
}

# 抓取
# 用法: arm_grab [force]
arm_grab() {
    local force="${1:-50}"
    post "/arm/grab" "{\"force\": $force}"
}

# 释放
arm_release() {
    post "/arm/release" "{}"
}

# ============ 高级任务 ============

# 智能抓取
# 用法: pickup <x> <y> [target_type] [max_retries]
pickup() {
    local x="$1"
    local y="$2"
    local target_type="${3:-}"
    local max_retries="${4:-3}"
    
    local json="{\"approx_x\": $x, \"approx_y\": $y"
    [ -n "$target_type" ] && json="$json, \"target_type\": \"$target_type\""
    json="$json, \"max_retries\": $max_retries}"
    
    post "/task/pickup" "$json"
}

# 智能放置
# 用法: place <x> <y> [drop_height]
place() {
    local x="$1"
    local y="$2"
    local drop_height="${3:-20}"
    
    post "/task/place" "{
        \"approx_x\": $x,
        \"approx_y\": $y,
        \"drop_height\": $drop_height
    }"
}

# 导航
# 用法: navigate <x> <y> [avoid_obstacles] [max_speed]
navigate() {
    local x="$1"
    local y="$2"
    local avoid="${3:-true}"
    local speed="${4:-80}"
    
    post "/task/navigate" "{
        \"target_x\": $x,
        \"target_y\": $y,
        \"avoid_obstacles\": $avoid,
        \"max_speed\": $speed
    }"
}

# 舞蹈
# 用法: dance [routine] [duration_sec]
dance() {
    local routine="${1:-dance1}"
    local duration="${2:-30}"
    
    post "/task/dance" "{
        \"routine\": \"$routine\",
        \"duration_sec\": $duration
    }"
}

# ============ 娱乐功能 ============

# 播放音乐
# 用法: play_music <song> [volume] [loop]
play_music() {
    local song="$1"
    local volume="${2:-80}"
    local loop="${3:-false}"
    
    post "/audio/play" "{
        \"song\": \"$song\",
        \"volume\": $volume,
        \"loop\": $loop
    }"
}

# ============ 传感器 ============

# 本地视觉检测
# 用法: detect [target1,target2,...]
detect() {
    local targets="$1"
    if [ -n "$targets" ]; then
        # 转换逗号分隔的字符串为 JSON 数组
        local json_targets=$(echo "$targets" | jq -R 'split(",") | map(select(length > 0))')
        post "/vision/detect" "{\"targets\": $json_targets}"
    else
        post "/vision/detect" "{}"
    fi
}

# 读取传感器
sensors() {
    get "/sensors"
}

# ============ 复合动作示例 ============

# 巡逻（示例：正方形路径）
patrol_square() {
    local size="${1:-10}"
    
    echo "开始巡逻（正方形，边长=$size）..."
    forward $size
    right 90
    forward $size
    right 90
    forward $size
    right 90
    forward $size
    right 90
    echo "巡逻完成"
}

# 抓取并放置（完整流程）
# 用法: grab_and_place <grab_x> <grab_y> <place_x> <place_y>
grab_and_place() {
    local gx="$1"
    local gy="$2"
    local px="$3"
    local py="$4"
    
    echo "执行抓取任务..."
    
    echo "1. 抓取物体 ($gx, $gy)"
    pickup "$gx" "$gy"
    
    echo "2. 放置物体 ($px, $py)"
    place "$px" "$py"
    
    echo "任务完成"
}

# ============ 主入口 ============

# 如果直接调用脚本（非 source），执行命令
if [ "${BASH_SOURCE[0]}" -eq "${0}" ]; then
    # 检查是否提供了命令
    if [ $# -eq 0 ]; then
        echo "用法: $0 <command> [args...]"
        echo ""
        echo "基础命令:"
        echo "  status                    - 查询状态"
        echo "  snapshot                  - 拍照"
        echo "  stream_url                - 获取视频流 URL"
        echo ""
        echo "移动命令:"
        echo "  forward [steps] [speed]   - 前进"
        echo "  backward [steps] [speed]  - 后退"
        echo "  left [steps] [speed]      - 左转"
        echo "  right [steps] [speed]     - 右转"
        echo "  stop                      - 停止"
        echo ""
        echo "机械臂命令:"
        echo "  arm_move_to <x> <y> <z> [speed]  - 移动到坐标"
        echo "  arm_grab [force]                 - 抓取"
        echo "  arm_release                      - 释放"
        echo ""
        echo "高级任务:"
        echo "  pickup <x> <y> [type] [retries]     - 智能抓取"
        echo "  place <x> <y> [height]              - 智能放置"
        echo "  navigate <x> <y> [avoid] [speed]    - 导航"
        echo "  dance [routine] [duration]          - 舞蹈"
        echo "  grab_and_place <gx> <gy> <px> <py>  - 完整抓放流程"
        echo ""
        echo "娱乐功能:"
        echo "  play_music <song> [volume] [loop]   - 播放音乐"
        echo "  patrol_square [size]                - 正方形巡逻"
        echo ""
        echo "传感器:"
        echo "  detect [target1,target2,...]        - 本地视觉检测"
        echo "  sensors                             - 读取传感器"
        echo ""
        echo "环境变量:"
        echo "  ROBOT_CAR_API - API 基础 URL (默认: $API_BASE)"
        exit 1
    fi
    
    # 执行命令
    command="$1"
    shift
    
    if type "$command" >/dev/null 2>&1; then
        "$command" "$@"
    else
        echo "错误: 未知命令 '$command'"
        exit 1
    fi
fi
