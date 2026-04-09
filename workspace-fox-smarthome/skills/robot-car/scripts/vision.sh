#!/bin/bash
# Vision Helper Script
# 辅助视觉分析的工具脚本

API_BASE="${ROBOT_CAR_API:-http://raspberrypi.local:5000}"
TEMP_DIR="/tmp/robot-car"

mkdir -p "$TEMP_DIR"

# 拍照并保存到本地
capture_and_save() {
    local filename="${1:-snapshot.jpg}"
    local output="$TEMP_DIR/$filename"
    
    echo "正在拍照..." >&2
    
    # 获取 base64 图片
    local response=$(curl -s "$API_BASE/camera/snapshot")
    local image_data=$(echo "$response" | jq -r '.image' | sed 's/^data:image\/jpeg;base64,//')
    
    # 解码并保存
    echo "$image_data" | base64 -d > "$output"
    
    echo "$output"
}

# 拍照并用 OpenClaw 的 image 工具分析
analyze_scene() {
    local prompt="${1:-描述你看到的场景}"
    
    echo "拍照中..." >&2
    local image_path=$(capture_and_save "scene_$(date +%s).jpg")
    
    echo "图片已保存: $image_path" >&2
    echo "分析场景..." >&2
    
    # 返回图片路径（供 OpenClaw 调用 image 工具）
    echo "$image_path"
}

# 检测特定颜色的物体
detect_color() {
    local color="${1:-red}"
    
    echo "检测 $color 物体..." >&2
    
    local response=$(curl -s -X POST "$API_BASE/vision/detect" \
        -H "Content-Type: application/json" \
        -d "{\"targets\": [\"${color}_ball\", \"${color}_cube\"]}")
    
    echo "$response" | jq .
}

# 持续监控（每 N 秒拍一次照）
monitor() {
    local interval="${1:-5}"
    
    echo "开始监控（每 ${interval}s 拍照一次，Ctrl+C 停止）..." >&2
    
    while true; do
        local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
        echo "[$timestamp] 拍照..." >&2
        
        local image_path=$(capture_and_save "monitor_$(date +%s).jpg")
        echo "  保存: $image_path" >&2
        
        # 快速检测（可选）
        local objects=$(curl -s -X POST "$API_BASE/vision/detect" | jq -r '.objects | length')
        echo "  检测到 $objects 个物体" >&2
        
        sleep "$interval"
    done
}

# 对比两张照片
compare() {
    local before="$1"
    local after="$2"
    
    if [ ! -f "$before" ] || [ ! -f "$after" ]; then
        echo "错误: 图片文件不存在" >&2
        return 1
    fi
    
    echo "对比图片:" >&2
    echo "  前: $before" >&2
    echo "  后: $after" >&2
    
    # 使用 OpenClaw 的 image 工具分析差异
    echo "提示: 使用 OpenClaw 的 image 工具分析这两张图的差异"
    echo "$before,$after"
}

# 验证视觉系统
test_vision() {
    echo "=== 视觉系统测试 ===" >&2
    
    echo "1. 检查摄像头连接..." >&2
    local status=$(curl -s "$API_BASE/status" | jq -r '.hardware.camera')
    if [ "$status" = "true" ]; then
        echo "  ✓ 摄像头在线" >&2
    else
        echo "  ✗ 摄像头离线" >&2
        return 1
    fi
    
    echo "2. 测试拍照..." >&2
    local image_path=$(capture_and_save "test.jpg")
    if [ -f "$image_path" ]; then
        local size=$(stat -f%z "$image_path" 2>/dev/null || stat -c%s "$image_path" 2>/dev/null)
        echo "  ✓ 拍照成功 (大小: $size bytes)" >&2
        echo "  文件: $image_path" >&2
    else
        echo "  ✗ 拍照失败" >&2
        return 1
    fi
    
    echo "3. 测试本地视觉检测..." >&2
    local detect_result=$(curl -s -X POST "$API_BASE/vision/detect")
    local obj_count=$(echo "$detect_result" | jq -r '.objects | length')
    echo "  检测到 $obj_count 个物体" >&2
    echo "$detect_result" | jq . >&2
    
    echo "=== 测试完成 ===" >&2
}

# 主入口
if [ "${BASH_SOURCE[0]}" -eq "${0}" ]; then
    if [ $# -eq 0 ]; then
        echo "用法: $0 <command> [args...]"
        echo ""
        echo "命令:"
        echo "  capture_and_save [filename]      - 拍照并保存到本地"
        echo "  analyze_scene [prompt]           - 拍照并返回路径（供 OpenClaw 分析）"
        echo "  detect_color <color>             - 检测特定颜色的物体"
        echo "  monitor [interval_sec]           - 持续监控（默认 5s）"
        echo "  compare <before.jpg> <after.jpg> - 对比两张照片"
        echo "  test_vision                      - 测试视觉系统"
        echo ""
        echo "环境变量:"
        echo "  ROBOT_CAR_API - API 基础 URL"
        exit 1
    fi
    
    command="$1"
    shift
    
    if type "$command" >/dev/null 2>&1; then
        "$command" "$@"
    else
        echo "错误: 未知命令 '$command'"
        exit 1
    fi
fi
