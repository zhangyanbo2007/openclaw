# Robot Car Control Skill

控制树莓派机器人小车（带机械臂和摄像头）的具身智能技能。

## 概述

这个技能让 OpenClaw 能够通过自然语言控制你的树莓派小车，实现：
- 📷 视觉感知（摄像头拍照/视频流）
- 🚗 运动控制（移动、转向、停止）
- 🦾 机械臂操作（抓取、放置、移动）
- 🎵 多模态交互（音频播放、舞蹈动作）

## 架构

```
OpenClaw (任务规划 + 视觉分析)
    ↓ HTTP API
树莓派控制器 (实时执行 + 本地视觉伺服)
    ↓
硬件层 (电机/舵机/摄像头/传感器)
```

**分工原则：**
- **OpenClaw:** 场景理解、任务拆解、多步编排、异常恢复
- **树莓派:** 实时控制、视觉伺服、底层硬件接口

---

## 配置

### API 端点
默认: `http://raspberrypi.local:5000`

修改方法：在 `scripts/control.sh` 中更新 `API_BASE` 变量。

---

## 功能清单

### 🎯 基础功能（优先实现）

#### 1. 摄像头
- **拍照:** 获取单帧图像（用于场景分析）
- **视频流:** 实时监控（可选）

#### 2. 小车移动
- **方向控制:** 前进、后退、左转、右转、停止
- **步进控制:** 指定移动距离/步数

#### 3. 机械臂
- **坐标移动:** 移动到指定 (x, y, z) 位置
- **抓取/释放:** 控制夹爪

#### 4. 状态查询
- 当前位置、电池电量、任务状态

---

### 🚀 进阶功能（后续扩展）

#### 5. 智能任务
- **智能抓取:** 带视觉伺服的自主抓取（`/task/pickup`）
- **智能放置:** 精确放置到目标位置（`/task/place`）
- **自主导航:** 带避障的路径规划（`/task/navigate`）

#### 6. 娱乐功能
- **舞蹈动作:** 预设动作序列
- **音频播放:** 背景音乐/语音反馈

#### 7. 传感器
- 超声波测距、陀螺仪、温湿度等

---

## API 接口规范

完整 API 设计见 `references/api-spec.md`

### 快速示例

```bash
# 拍照
curl http://raspberrypi.local:5000/camera/snapshot

# 前进 10 步
curl -X POST http://raspberrypi.local:5000/car/move \
  -H "Content-Type: application/json" \
  -d '{"direction": "forward", "steps": 10}'

# 移动机械臂
curl -X POST http://raspberrypi.local:5000/arm/moveTo \
  -H "Content-Type: application/json" \
  -d '{"x": 120, "y": 80, "z": 30}'

# 抓取
curl -X POST http://raspberrypi.local:5000/arm/grab

# 智能抓取任务（进阶）
curl -X POST http://raspberrypi.local:5000/task/pickup \
  -H "Content-Type: application/json" \
  -d '{"target_type": "red_ball", "approx_x": 120, "approx_y": 80}'
```

---

## 使用方法

### 自然语言控制示例

**你说:** "拍张照片看看前面有什么"
```
我会:
1. 调用 /camera/snapshot
2. 用 image 工具分析场景
3. 告诉你: "看到一个红色的球在左边，一个蓝色的篮子在右边"
```

**你说:** "把红球捡起来放到篮子里"
```
我会:
1. 拍照 → 识别球(120, 80)、篮子(250, 90)
2. 调用 /task/pickup {"approx_x": 120, "approx_y": 80}
   (树莓派自主完成视觉伺服 + 抓取)
3. 调用 /task/place {"approx_x": 250, "approx_y": 90}
   (树莓派自主完成放置)
4. 完成 ✅
```

**你说:** "后退 5 步然后跳个舞"
```
我会:
1. 调用 /car/move {"direction": "backward", "steps": 5}
2. 调用 /audio/play {"song": "dance.mp3"}
3. 调用 /task/dance {"routine": "dance1"}
4. 完成 ✅
```

---

## 硬件到货后的启动清单

见 `references/quickstart.md`

**核心步骤：**
1. ✅ 树莓派连接 WiFi（确保和 OpenClaw 同网络）
2. ✅ 安装依赖（Flask、OpenCV、GPIO 库）
3. ✅ 实现 API 服务端（参考 `api-spec.md`）
4. ✅ 测试连通性（`curl http://树莓派IP:5000/status`）
5. ✅ 测试基础功能（移动、拍照、抓取）
6. ✅ 更新 `scripts/control.sh` 中的 `API_BASE`
7. ✅ 开始玩耍 🎉

---

## 开发建议

### 树莓派端实现优先级

**第一阶段（能动起来）：**
1. HTTP API 框架（Flask）
2. 摄像头拍照（`/camera/snapshot`）
3. 小车移动（`/car/move`）
4. 状态查询（`/status`）

**第二阶段（能抓东西）：**
5. 机械臂基础控制（`/arm/moveTo`, `/arm/grab`, `/arm/release`）

**第三阶段（智能化）：**
6. 本地视觉识别（OpenCV 颜色/形状检测）
7. 智能任务接口（`/task/pickup`, `/task/place`）
8. 视觉伺服闭环控制

**第四阶段（好玩）：**
9. 舞蹈动作（`/task/dance`）
10. 音频播放（`/audio/play`）

---

## 故障排查

### 无法连接树莓派
```bash
# 1. 检查网络
ping raspberrypi.local

# 2. 检查端口
curl http://raspberrypi.local:5000/status

# 3. 查看树莓派日志
ssh pi@raspberrypi.local
journalctl -u robot-api -f
```

### 视觉识别不准
- 检查光照条件（太暗/太亮）
- 调整 OpenCV 颜色阈值
- 使用我的 image 工具做复杂场景分析（树莓派只做简单识别）

### 机械臂抓取失败
- 拍照验证位置是否对准
- 降低速度（提高精度）
- 检查夹爪力度

---

## 相关文件

- `scripts/control.sh` - 控制脚本（封装 API 调用）
- `scripts/vision.sh` - 视觉辅助脚本
- `references/api-spec.md` - 完整 API 规范（给树莓派实现用）
- `references/quickstart.md` - 快速启动指南
- `references/examples.md` - 更多使用示例

---

## 未来扩展方向

- [ ] 多机器人协作（控制多台小车）
- [ ] SLAM 建图导航（ROS 集成）
- [ ] 强化学习策略（收集演示数据 → 训练模型）
- [ ] 语音控制（TTS 反馈）
- [ ] VLA 模型集成（端到端控制）

---

**Status:** 🚧 等待硬件到货

**Created:** 2026-03-11  
**Last Updated:** 2026-03-11
