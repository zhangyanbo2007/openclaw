# AGENTS.md - 狐狸智能管家

## 启动流程

每次对话开始：
1. 读 `SOUL.md` — 行为准则
2. 读 `IDENTITY.md` — 身份定义
3. 读 `TOOLS.md` — 快速参考

## 核心原则

- 用户指令直接调用 HA API 执行
- 执行完告知结果
- 设备离线/失败如实说

## 文件说明

| 文件 | 用途 |
|------|------|
| `TOOLS.md` | 快速参考（区域索引 + 音箱清单 + 窗帘 + 扫地机器人 + 猫眼） |
| `HA_DEVICES_FULL.md` | 完整设备清单（1870 实体，12 区域） |
| `home-devices.md` | 简化设备清单 |
| `home-commands.md` | 设备控制命令参考 |
| `HEARTBEAT.md` | 系统健康监控（4 个心跳检查） |

## 快速查找

| 问题 | 查什么 |
|------|--------|
| 设备 entity_id | `TOOLS.md` 或 `HA_DEVICES_FULL.md` |
| 设备在哪个区域 | `TOOLS.md` 区域索引 |
| 设备怎么控制 | `home-commands.md` |
| 某个区域有哪些设备 | `HA_DEVICES_FULL.md` |

## 区域分布（12 个区域）

| 区域 | Area ID | 实体数 |
|------|---------|--------|
| 阳台 | `yang_tai` | 353 |
| 入户 | `ru_hu` | 230 |
| 书房 | `shu_fang` | 229 |
| 主卧 | `zhu_wo` | 219 |
| 餐厅 | `can_ting` | 195 |
| 客厅 | `ke_ting` | 126 |
| 次卧 | `ci_wo` | 82 |
| 儿童房 | `er_tong_fang` | 133 |
| 过道 | `guo_dao` | 319 |
| 主卫 | `zhu_wei` | 19 |
| 公卫 | `gong_wei` | 19 |
| 厨房 | `chu_fang` | 10 |

**总计：1870 实体**

## 7 个音箱分布

| 区域 | 实体 ID |
|------|---------|
| 客厅 | `media_player.xiaomi_lx06_81cc_play_control` |
| 主卧 | `media_player.xiaomi_lx06_46d3_play_control` |
| 书房 | `media_player.xiaomi_l15a_7e84_play_control` |
| 次卧 | `media_player.xiaomi_l05c_a0e2_play_control` |
| 餐厅 | `media_player.xiaomi_l05c_9e01_play_control` |
| 儿童房 | `media_player.xiaomi_l05c_f45a_play_control` |
| 入户 | `media_player.xiaomi_oh2_5da4_play_control` |

## TTS 播放命令

```bash
curl -X POST "$HA_URL/api/services/xiaomi_miot/intelligent_speaker" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -d '{"entity_id": "媒体播放器实体 ID", "text": "要播放的文字"}'
```
