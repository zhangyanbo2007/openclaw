# TOOLS.md - 快速参考

> 最后更新：2026-03-20  
> 实体总数：1870 个  
> 区域数量：12 个

---

## 🏠 区域快速索引

| 区域 | Area ID | 实体数 | 主要设备 |
|------|---------|--------|----------|
| 阳台 | `yang_tai` | 353 | 扫地机器人、窗帘、晾衣架 |
| 入户 | `ru_hu` | 230 | 门窗传感器、猫眼、音箱 |
| 书房 | `shu_fang` | 229 | 空调、灯光、音箱 |
| 主卧 | `zhu_wo` | 219 | 空调、窗帘、灯光、音箱 |
| 餐厅 | `can_ting` | 195 | 窗帘、灯光、音箱 |
| 客厅 | `ke_ting` | 126 | 电视、音箱、净化器 |
| 次卧 | `ci_wo` | 82 | 空调 |
| 儿童房 | `er_tong_fang` | 133 | 灯光 |
| 过道 | `guo_dao` | 319 | 灯光 |
| 主卫 | `zhu_wei` | 19 | 浴霸 |
| 公卫 | `gong_wei` | 19 | 浴霸 |
| 厨房 | `chu_fang` | 10 | 音箱 |

---

## 🔊 音箱设备清单

| 区域 | 实体 ID | 名称 |
|------|---------|------|
| 客厅 | `media_player.xiaomi_lx06_81cc_play_control` | 小爱音箱 Pro-2 |
| 主卧 | `media_player.xiaomi_lx06_46d3_play_control` | Mi AI Speaker Pro |
| 书房 | `media_player.xiaomi_l15a_7e84_play_control` | MI AI Speaker (2nd Gen) |
| 次卧 | `media_player.xiaomi_l05c_a0e2_play_control` | Mi AI Speaker Play Plus 2 |
| 餐厅 | `media_player.xiaomi_l05c_9e01_play_control` | 小米小爱音箱 Play 增强版 |
| 儿童房 | `media_player.xiaomi_l05c_f45a_play_control` | 小米小爱音箱 Play 增强版 |
| 入户 | `media_player.xiaomi_oh2_5da4_play_control` | Xiaomi Smart Speaker |

### TTS 播放命令

```bash
curl -X POST "$HA_URL/api/services/xiaomi_miot/intelligent_speaker" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -d '{"entity_id": "media_player.xiaomi_l15a_7e84_play_control", "text": "夜深了，别熬夜了"}'
```

---

## 🪟 窗帘设备（4 个）

| 位置 | 名称 | 实体 ID |
|------|------|---------|
| 主卧 | 布帘 | `cover.babai_cn_557741642_bb82mj_s_2` |
| 主卧 | 纱帘 | `cover.babai_cn_557773468_bb82mj_s_2` |
| 阳台 | 阳台窗帘 | `cover.novo_cn_548672564_n21_s_2_curtain` |
| 餐厅 | 餐厅窗帘 | `cover.babai_cn_557805889_190812_s_2` |

---

## 🧹 扫地机器人

**实体：** `vacuum.dreamebot_s10_pro_plus`（追觅 S10 Pro Plus）

| 命令 | 服务 | 示例 |
|------|------|------|
| 启动清洁 | `vacuum.start` | `启动扫地机器人` |
| 暂停 | `vacuum.pause` | `扫地机器人暂停` |
| 回充 | `vacuum.return_to_base` | `扫地机器人回充` |
| 定位 | `vacuum.locate` | `扫地机器人定位` |

**房间移动（不清洁）：** 启动后监控 `current_segment`，到达目标房间后 `vacuum.stop`

---

## 📷 萤石猫眼

**实体：** `camera.ezviz_cat_eye`（入户大门外）

| 项目 | 值 |
|------|-----|
| 设备序列号 | `F66074055` |
| AppKey | `d78ef22ddf794dd9a2f0984d86504ff5` |
| 抓图脚本 | `scripts/ezviz_doorbell.sh` |

---

## 📝 完整文档

| 文件 | 用途 |
|------|------|
| `HA_DEVICES_FULL.md` | 完整设备清单（1870 实体） |
| `home-commands.md` | 设备控制命令参考 |
| `home-devices.md` | 简化设备清单 |
