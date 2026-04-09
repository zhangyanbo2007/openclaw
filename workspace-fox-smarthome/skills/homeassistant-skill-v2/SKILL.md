---
name: homeassistant-skill-v2
description: >
  Enhanced Home Assistant control with smart monitoring, health checks, air quality management,
  and intelligent scene recommendations. Includes battery monitoring, CO₂ alerts, and batch operations.
license: MIT
homepage: https://github.com/yourusername/homeassistant-skill-v2
compatibility: Requires curl and jq. Network access to Home Assistant instance.
metadata: {"author": "小王子", "version": "2.2.0", "openclaw": {"requires": {"env": ["HA_URL", "HA_TOKEN"], "bins": ["curl", "jq"]}, "primaryEnv": "HA_TOKEN"}}
---

# Home Assistant Skill V2 - 智能增强版

基于原版 homeassistant-skill 的智能增强版本，新增设备健康监控、空气质量管理、智能推荐等功能。

## 新增功能

### 1. 设备健康监控 🔋

#### 检查所有低电量设备
```bash
curl -s "$HA_URL/api/states" -H "Authorization: Bearer $HA_TOKEN" \
  | jq -r '.[] | select(.attributes.battery_level != null) | select(.attributes.battery_level < 20) | "\(.attributes.friendly_name // .entity_id): \(.attributes.battery_level)%"'
```

#### 检查需要更换滤芯的设备
```bash
curl -s "$HA_URL/api/states" -H "Authorization: Bearer $HA_TOKEN" \
  | jq -r '.[] | select(.attributes.filter_life_level != null) | select(.attributes.filter_life_level < 10) | "\(.attributes.friendly_name // .entity_id): 滤芯寿命 \(.attributes.filter_life_level)%"'
```

#### 检查离线设备
```bash
curl -s "$HA_URL/api/states" -H "Authorization: Bearer $HA_TOKEN" \
  | jq -r '.[] | select(.state == "unavailable" or .state == "unknown") | .entity_id'
```

### 2. 空气质量管理 🌡️

#### 获取所有房间的空气质量状态
```bash
curl -s "$HA_URL/api/states" -H "Authorization: Bearer $HA_TOKEN" \
  | jq -r '.[] | select(.entity_id | startswith("climate.")) | {
    name: (.attributes.friendly_name // .entity_id),
    temperature: .attributes.current_temperature,
    humidity: .attributes.current_humidity,
    co2: .attributes.carbon_dioxide_level
  }'
```

#### CO₂浓度监控和建议
```bash
# 检查CO₂浓度高的房间（>800 ppm需要通风）
curl -s "$HA_URL/api/states" -H "Authorization: Bearer $HA_TOKEN" \
  | jq -r '.[] | select(.attributes.carbon_dioxide_level != null) | select(.attributes.carbon_dioxide_level > 800) | "\(.attributes.friendly_name // .entity_id): CO₂ \(.attributes.carbon_dioxide_level) ppm - 需要通风"'
```

#### 温湿度平衡检查
```bash
# 检查温湿度异常的传感器
curl -s "$HA_URL/api/states" -H "Authorization: Bearer $HA_TOKEN" \
  | jq -r '.[] | select(.entity_id | startswith("sensor.") and (contains("temperature") or contains("humidity"))) |
    select(
      (.attributes.device_class == "temperature" and (.state | tonumber) > 28) or
      (.attributes.device_class == "temperature" and (.state | tonumber) < 16) or
      (.attributes.device_class == "humidity" and (.state | tonumber) > 70) or
      (.attributes.device_class == "humidity" and (.state | tonumber) < 30)
    ) | "\(.attributes.friendly_name // .entity_id): \(.state)\(.attributes.unit_of_measurement // "")"'
```

### 3. 智能批量操作 🎯

#### 按房间批量控制灯光
```bash
# 关闭某个区域的所有灯
AREA="living_room"
LIGHTS=$(curl -s -X POST "$HA_URL/api/template" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"template\": \"{{ area_entities('$AREA') | select('match', 'light.') | list | tojson }}\"}")

curl -s -X POST "$HA_URL/api/services/light/turn_off" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"entity_id\": $LIGHTS}"
```

#### 一键离家模式
```bash
# 关闭所有灯光、空调，锁门
curl -s -X POST "$HA_URL/api/services/light/turn_off" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "all"}'

curl -s -X POST "$HA_URL/api/services/climate/turn_off" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "all"}'
```

#### 一键回家模式
```bash
# 开启玄关灯、客厅灯，设置舒适温度
curl -s -X POST "$HA_URL/api/services/light/turn_on" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entity_id": ["light.entrance", "light.living_room"], "brightness_pct": 60}'
```

### 4. 设备状态总览 📊

#### 生成完整的智能家居状态报告
```bash
#!/bin/bash

echo "🏠 智能家居状态报告"
echo "===================="
echo ""

# 空调状态
echo "🌡️ 空调系统"
curl -s "$HA_URL/api/states" -H "Authorization: Bearer $HA_TOKEN" \
  | jq -r '.[] | select(.entity_id | startswith("climate.")) | "  \(.attributes.friendly_name // .entity_id): \(.state), 温度 \(.attributes.current_temperature)°C, 湿度 \(.attributes.current_humidity)%, CO₂ \(.attributes.carbon_dioxide_level) ppm"'
echo ""

# 灯光状态
echo "💡 灯光设备"
LIGHTS_ON=$(curl -s "$HA_URL/api/states" -H "Authorization: Bearer $HA_TOKEN" | jq '[.[] | select(.entity_id | startswith("light.")) | select(.state == "on")] | length')
LIGHTS_TOTAL=$(curl -s "$HA_URL/api/states" -H "Authorization: Bearer $HA_TOKEN" | jq '[.[] | select(.entity_id | startswith("light."))] | length')
echo "  开启: $LIGHTS_ON/$LIGHTS_TOTAL"
echo ""

# 电池电量警告
echo "🔋 电池电量警告"
curl -s "$HA_URL/api/states" -H "Authorization: Bearer $HA_TOKEN" \
  | jq -r '.[] | select(.attributes.battery_level != null) | select(.attributes.battery_level < 20) | "  ⚠️  \(.attributes.friendly_name // .entity_id): \(.attributes.battery_level)%"'
echo ""

# 离线设备
echo "📡 离线设备"
curl -s "$HA_URL/api/states" -H "Authorization: Bearer $HA_TOKEN" \
  | jq -r '.[] | select(.state == "unavailable") | "  ❌ \(.entity_id)"'
echo ""

# 在家成员
echo "👤 在家成员"
curl -s "$HA_URL/api/states" -H "Authorization: Bearer $HA_TOKEN" \
  | jq -r '.[] | select(.entity_id | startswith("person.")) | "  \(.attributes.friendly_name // .entity_id): \(.state)"'
```

### 5. 智能场景推荐 💡

#### 根据环境自动推荐场景
```bash
#!/bin/bash

# 获取当前时间
HOUR=$(date +%H)

# 获取平均CO₂浓度
AVG_CO2=$(curl -s "$HA_URL/api/states" -H "Authorization: Bearer $HA_TOKEN" \
  | jq '[.[] | select(.attributes.carbon_dioxide_level != null) | .attributes.carbon_dioxide_level] | add / length')

# 获取室内平均温度
AVG_TEMP=$(curl -s "$HA_URL/api/states" -H "Authorization: Bearer $HA_TOKEN" \
  | jq '[.[] | select(.entity_id | startswith("climate.")) | .attributes.current_temperature] | add / length')

echo "💡 场景推荐"
echo "============"

# 早晨场景
if [ $HOUR -ge 6 ] && [ $HOUR -lt 9 ]; then
  echo "🌅 建议：早安场景"
  echo "  - 逐渐提高客厅/卧室亮度"
  echo "  - 打开窗帘"
  echo "  - 播放轻音乐"
fi

# CO₂浓度高
if (( $(echo "$AVG_CO2 > 800" | bc -l) )); then
  echo "🌬️  警告：CO₂浓度偏高 ($AVG_CO2 ppm)"
  echo "  - 建议开启新风系统"
  echo "  - 或打开窗户通风"
fi

# 温度过高
if (( $(echo "$AVG_TEMP > 26" | bc -l) )); then
  echo "🌡️  提示：室温偏高 ($AVG_TEMP°C)"
  echo "  - 建议开启空调制冷"
fi

# 晚上场景
if [ $HOUR -ge 21 ]; then
  echo "🌙 建议：夜间场景"
  echo "  - 降低灯光亮度"
  echo "  - 关闭非必要设备"
fi
```

### 6. 小米特定功能 🎛️

#### 场景面板批量控制
```bash
# 获取所有场景面板状态
curl -s "$HA_URL/api/states" -H "Authorization: Bearer $HA_TOKEN" \
  | jq -r '.[] | select(.entity_id | contains("hope_cn")) | {entity: .entity_id, friendly: .attributes.friendly_name, state: .state}'
```

#### 小米新风空调专用控制
```bash
# 开启新风模式
curl -s -X POST "$HA_URL/api/services/climate/set_hvac_mode" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "climate.xiaomi_cn_532962825_mt0", "hvac_mode": "fan_only"}'

# 开启UV消毒
curl -s -X POST "$HA_URL/api/services/climate/turn_on" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "climate.xiaomi_cn_532962825_mt0"}'
```

### 7. 宠物喂食器管理 🐾

#### 检查喂食器状态
```bash
curl -s "$HA_URL/api/states/sensor.hfjh_cn_672530347_m100_s_8_feed_today" \
  -H "Authorization: Bearer $HA_TOKEN" \
  | jq '{
    今日喂食: .state,
    水温: .attributes.water_temperature,
    水泵: .attributes.pump_status,
    滤芯: .attributes.filter_life_level
  }'
```

#### 喂食提醒
```bash
# 如果今日未喂食且时间超过上午10点，发送提醒
HOUR=$(date +%H)
FEED_COUNT=$(curl -s "$HA_URL/api/states/sensor.hfjh_cn_672530347_m100_s_8_feed_today" \
  -H "Authorization: Bearer $HA_TOKEN" | jq -r '.state')

if [ "$FEED_COUNT" == "0" ] && [ $HOUR -ge 10 ]; then
  curl -s -X POST "$HA_URL/api/services/notify/notify" \
    -H "Authorization: Bearer $HA_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"message": "宠物今天还没有喂食！", "title": "喂食提醒"}'
fi
```

## 继承原版功能

本技能完全兼容原版 homeassistant-skill 的所有功能，包括：
- 25个实体域的完整支持
- 灯光、开关、空调、窗帘等基础控制
- 场景、脚本、自动化管理
- 通知、天气、日历等服务

详细用法请参考原版文档。

## 使用建议

1. **每天早上**运行健康检查脚本，了解设备状态
2. **定期检查**电池电量和滤芯寿命
3. **CO₂浓度超过 800 ppm** 时及时通风
4. **离家前**使用一键离家模式
5. 根据**场景推荐**优化智能家居体验

## 安全规则

继承原版的所有安全规则：
- 锁、报警面板、车库门等敏感操作必须确认
- 不要在未经授权的情况下执行安全相关操作

## 需要的环境变量

```bash
export HA_URL=http://192.168.28.77:8123
export HA_TOKEN=your-long-lived-access-token
```
