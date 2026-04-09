# 狐狸智能管家 - 文档索引

> 最后更新：2026-03-17

---

## 📚 文档结构

```
workspace-fox-smarthome/
├── README.md                  # 本文档索引
├── AGENTS.md                  # 使用指南（必读）
├── IDENTITY.md                # 身份定义
├── SOUL.md                    # 行为准则
├── USER.md                    # 用户信息
├── HEARTBEAT.md               # 系统健康监控配置
├── BOOTSTRAP.md               # 初始化指南
│
├── home-devices.md            # 设备清单（简化版）⭐
├── home-commands.md           # 设备控制命令参考 ⭐
├── TOOLS.md                   # 快速参考（区域索引 + 重点设备）
│
├── scripts/                   # 自动化脚本
│   ├── door_handler.sh        # 进出门处理
│   ├── face_recognition.sh    # 人脸识别
│   ├── aliyun_face.py         # 阿里云 API
│   └── ezviz_doorbell.sh      # 猫眼抓图
│
└── homeassistant/             # HA 配置
    └── door_automation.yaml   # 进出门自动化配置
```

---

## 📖 文档说明

### 核心文档（必读）

| 文档 | 用途 | 何时查阅 |
|------|------|----------|
| `AGENTS.md` | 使用指南 | 开始使用时 |
| `SOUL.md` | 行为准则 | 了解回复风格 |
| `home-devices.md` | 设备清单 | 查找设备 |
| `home-commands.md` | 控制命令 | 控制设备时 |

### 参考文档

| 文档 | 用途 | 何时查阅 |
|------|------|----------|
| `TOOLS.md` | 快速参考 | 需要快速查找时 |
| `HEARTBEAT.md` | 监控配置 | 系统维护时 |
| `USER.md` | 用户信息 | 了解用户偏好时 |

### 技术文档

| 文档 | 用途 | 何时查阅 |
|------|------|----------|
| `scripts/` | 自动化脚本 | 配置自动化时 |
| `homeassistant/` | HA 配置 | 配置 HA 时 |

---

## 🚀 快速开始

### 1. 查看设备清单
```bash
cat home-devices.md
```

### 2. 查找设备命令
```bash
grep -i "空调" home-commands.md
```

### 3. 查看区域分布
```bash
grep "## 🏠" home-devices.md
```

---

## 🎯 常用场景

| 场景 | 参考文档 |
|------|----------|
| "XX 设备怎么控制？" | `home-commands.md` |
| "XX 设备在哪里？" | `home-devices.md` 或 `TOOLS.md` |
| "某个区域有哪些设备？" | `home-devices.md` |
| "进出门检测怎么配置？" | `scripts/door_handler.sh` |
| "人脸识别怎么测试？" | `scripts/face_recognition.sh` |

---

## 📞 技术支持

遇到问题可以：
1. 查看相关文档
2. 检查脚本日志
3. 测试各个组件单独工作
