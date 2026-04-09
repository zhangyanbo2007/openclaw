
# Home Assistant Skill V2 - 智能增强版

基于原版 [homeassistant-skill](https://github.com/anotb/homeassistant-skill) 的增强版本，专为小王子的智能家居环境优化。

## 🎯 新增核心功能

### 1. 设备健康监控 🔋
- 自动检测低电量设备（<20%）
- 滤芯寿命监控
- 离线设备检测
- 完整的设备状态报告

### 2. 空气质量管理 🌡️
- CO₂浓度监控（>800 ppm 自动提醒）
- 温湿度平衡检查
- 新风系统智能控制
- 小米空调 UV 消毒功能

### 3. 智能批量操作 🎯
- 按区域批量控制设备
- 一键离家模式（关闭所有灯光、空调）
- 一键回家模式（开启常用设备）
- 场景面板快捷控制

### 4. 智能推荐系统 💡
- 基于时间的场景推荐
- 基于环境数据的自动建议
- CO₂/温度异常预警
- 个性化场景定制

### 5. 宠物喂食器管理 🐾
- 喂食状态监控
- 喂食提醒（每日10点检查）
- 水温/水泵状态检查
- 滤芯寿命提醒

## 📦 安装

将技能放到 OpenClaw 的 skills 目录：

```bash
cp -r homeassistant-skill-v2 ~/.openclaw/workspace/skills/
```

## ⚙️ 配置

设置环境变量（已在 openclaw.json 中配置）：

```bash
export HA_URL=http://192.168.28.77:8123
export HA_TOKEN=your-token
```

## 🚀 快速开始

### 每日健康检查
```bash
./health_check.sh
```

### 查看设备状态报告
```bash
curl -s "$HA_URL/api/states" -H "Authorization: Bearer $HA_TOKEN" | jq
```

### 获取智能推荐
```bash
./scene_recommendation.sh
```

## 📊 适配小王子的设备

### ✅ 已优化支持
- ✅ 3台小米新风空调（含 CO₂ 监控）
- ✅ 7个青萍温湿度传感器
- ✅ 20+ 灯光设备
- ✅ 3个场景面板（主卧/餐厅/阳台）
- ✅ 宠物喂食器（hfjh_cn_672530347_m100）
- ✅ 5组窗帘/晾衣架
- ✅ 7台小米音箱
- ✅ 2台取暖器

### 🔔 特殊关注
- ⚠️  7个传感器电量低（5%）
- ⚠️  宠物喂食器滤芯寿命 0%
- ⚠️  扫地机器人离线

## 🆕 V2 vs V1 对比

| 功能 | V1 | V2 |
|------|----|----|
| 基础设备控制 | ✅ | ✅ |
| 健康监控 | ❌ | ✅ |
| 空气质量管理 | ❌ | ✅ |
| 智能推荐 | ❌ | ✅ |
| 批量操作 | 部分 | ✅ |
| 宠物设备管理 | ❌ | ✅ |
| CO₂监控 | ❌ | ✅ |
| 场景优化 | ❌ | ✅ |

## 📝 使用示例

### 示例1：早晨健康检查
```bash
# 检查电池电量
curl -s "$HA_URL/api/states" -H "Authorization: Bearer $HA_TOKEN" \
  | jq -r '.[] | select(.attributes.battery_level != null) | select(.attributes.battery_level < 20)'

# 检查空气质量
curl -s "$HA_URL/api/states" -H "Authorization: Bearer $HA_TOKEN" \
  | jq -r '.[] | select(.attributes.carbon_dioxide_level != null) | select(.attributes.carbon_dioxide_level > 800)'
```

### 示例2：离家模式
```bash
# 关闭所有灯光和空调
curl -s -X POST "$HA_URL/api/services/light/turn_off" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "all"}'
```

### 示例3：宠物喂食提醒
```bash
# 检查今日是否已喂食
curl -s "$HA_URL/api/states/sensor.hfjh_cn_672530347_m100_s_8_feed_today" \
  -H "Authorization: Bearer $HA_TOKEN" | jq '.state'
```

## 🔐 安全规则

继承原版所有安全规则：
- 锁/报警/车库门操作需确认
- 不执行未授权的安全操作

## 📄 许可证

MIT License

## 🙏 致谢

基于 [anotb/homeassistant-skill](https://github.com/anotb/homeassistant-skill) 开发