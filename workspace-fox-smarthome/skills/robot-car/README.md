# 🤖 Robot Car Skill

控制树莓派机器人小车的具身智能技能（带机械臂 + 摄像头）。

## 📁 文件结构

```
robot-car/
├── SKILL.md                    # 技能主文档
├── README.md                   # 本文件
├── scripts/
│   ├── control.sh              # 控制脚本（移动、抓取等）
│   └── vision.sh               # 视觉辅助脚本
└── references/
    ├── api-spec.md             # 树莓派 API 规范（实现指南）
    ├── quickstart.md           # 硬件到货后的快速启动
    └── examples.md             # 使用示例集合
```

## 🚀 快速开始

### 当前状态
🚧 **等待硬件到货**

技能框架已准备就绪，硬件到货后参考 `references/quickstart.md` 完成配置。

### 硬件到货后

1. **配置树莓派**
   - 安装系统 + 依赖
   - 实现 API 服务器（参考 `references/api-spec.md`）
   - 测试硬件连接

2. **更新 API 地址**
   ```bash
   # 编辑 scripts/control.sh
   API_BASE="http://你的树莓派IP:5000"
   ```

3. **测试连接**
   ```bash
   cd scripts
   ./control.sh status
   ```

4. **开始使用**
   对 OpenClaw 说："拍张照片看看前面有什么"

## 📖 文档索引

- **SKILL.md** - 技能概述和功能清单
- **references/api-spec.md** - 完整 API 设计文档（树莓派端实现指南）
- **references/quickstart.md** - 硬件配置和启动流程
- **references/examples.md** - 实际使用场景示例

## 🎯 功能概览

### 基础功能（优先实现）
- ✅ 摄像头拍照/视频流
- ✅ 小车移动控制（前进/后退/转向）
- ✅ 机械臂基础操作（移动/抓取/释放）
- ✅ 状态查询

### 进阶功能（后续扩展）
- ⏸️ 智能抓取（带视觉伺服）
- ⏸️ 自主导航（带避障）
- ⏸️ 舞蹈动作
- ⏸️ 音频播放

## 🏗️ 架构

```
你（自然语言）
    ↓
OpenClaw（任务规划 + 视觉分析）
    ↓ HTTP API
树莓派控制器（实时执行 + 本地视觉伺服）
    ↓
硬件层（电机/舵机/摄像头）
```

## 🛠️ 依赖

### OpenClaw 端
- bash/curl（已内置）
- jq（JSON 处理，可选）

### 树莓派端
- Python 3.7+
- Flask（API 服务器）
- OpenCV（视觉识别）
- RPi.GPIO / Adafruit 库（硬件控制）

详见 `references/quickstart.md`

## 📝 待办清单

- [ ] 硬件到货
- [ ] 树莓派组装
- [ ] 实现 API 服务器
- [ ] 测试基础功能
- [ ] 实现高级任务
- [ ] 训练本地视觉模型
- [ ] 收集演示数据

## 🆘 支持

遇到问题？
1. 查看 `references/quickstart.md` 的故障排查章节
2. 检查树莓派日志：`journalctl -u robot-api -f`
3. 问我（OpenClaw）🦊

## 📜 许可

本技能模板基于 MIT 许可，自由使用和修改。

---

**Created:** 2026-03-11  
**Status:** 🚧 Waiting for hardware  
**Version:** 1.0.0
