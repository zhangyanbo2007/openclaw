#!/bin/bash
# 门开事件 → 萤石抓图 → 推送飞书
# 触发方式：HA automation 通过 shell_command 调用

APPKEY="d78ef22ddf794dd9a2f0984d86504ff5"
APPSECRET="56010e2be7d42e8881cd7fb26ec472d3"
SERIAL="F66074055"
SAVE_DIR="/tmp/openclaw"

# 飞书机器人配置（从环境变量读）
FEISHU_API="${HA_URL:-http://192.168.28.77:8123}"
OC_FEISHU_CHAT="oc_f26a3aa83f63ad1e874fd34cb4af9c45"

mkdir -p "$SAVE_DIR"

# 1. 获取萤石 token
TOKEN=$(curl -s -X POST "https://open.ys7.com/api/lapp/token/get" \
  -d "appKey=$APPKEY&appSecret=$APPSECRET" | jq -r '.data.accessToken')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "❌ 获取萤石 token 失败"
  exit 1
fi

# 2. 等1秒让人到位（门刚开，人还没到猫眼范围）
sleep 1

# 3. 优先用实时抓图接口
PIC_URL=$(curl -s -X POST "https://open.ys7.com/api/lapp/device/capture" \
  -d "accessToken=$TOKEN&deviceSerial=$SERIAL&channelNo=1" \
  | jq -r '.data.picUrl // empty')

# 实时抓图失败时，取最近1分钟的告警图
if [ -z "$PIC_URL" ]; then
  NOW_MS=$(date +%s%3N)
  START_MS=$((NOW_MS - 60000))
  PIC_URL=$(curl -s -X POST "https://open.ys7.com/api/lapp/alarm/device/list" \
    -d "accessToken=$TOKEN&deviceSerial=$SERIAL&startTime=$START_MS&pageStart=0&pageSize=1" \
    | jq -r '.data[0].alarmPicUrl // empty')
fi

if [ -z "$PIC_URL" ]; then
  echo "❌ 获取图片失败"
  exit 1
fi

# 4. 下载图片
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
IMG_PATH="$SAVE_DIR/door_${TIMESTAMP}.jpg"

curl -s -L "$PIC_URL" -o "$IMG_PATH"

if [ ! -s "$IMG_PATH" ]; then
  echo "❌ 下载图片失败"
  exit 1
fi

echo "✅ 抓图成功: $IMG_PATH ($(du -h $IMG_PATH | cut -f1))"
echo "IMG_PATH=$IMG_PATH"
