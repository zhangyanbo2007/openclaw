# Robot Car 使用示例

实际场景中如何使用这个技能。

---

## 🎯 场景 1：基础探索

### 你说：
> "拍张照片看看前面有什么"

### 我的操作：
```bash
# 1. 拍照
./vision.sh capture_and_save scene.jpg

# 2. 用 image 工具分析
# （我自动调用，你看不到这一步）

# 3. 告诉你结果
```

### 我的回复：
> "看到前面有一个红色的球在左边（大约 120,80 位置），一个蓝色的篮子在右边（250,90）。地面上还有一些散落的积木。"

---

## 🎯 场景 2：简单抓取

### 你说：
> "把红球捡起来"

### 我的操作：
```bash
# 1. 拍照确认位置
./vision.sh capture_and_save

# 2. 分析：红球在 (120, 80)

# 3. 移动机械臂到球上方
./control.sh arm_move_to 120 80 30

# 4. 下降
./control.sh arm_move_to 120 80 10

# 5. 抓取
./control.sh arm_grab 60

# 6. 提升
./control.sh arm_move_to 120 80 40

# 7. 验证是否抓到
./vision.sh capture_and_save check.jpg
```

### 我的回复：
> "✅ 已抓取红球"

---

## 🎯 场景 3：完整任务链

### 你说：
> "把红球放到蓝色篮子里，然后后退 5 步，跳个舞庆祝一下"

### 我的操作：
```bash
# 第一步：抓取红球
./control.sh pickup 120 80 red_ball

# 第二步：移动到篮子上方
./control.sh place 250 90 20

# 第三步：后退
./control.sh backward 5

# 第四步：播放音乐
./control.sh play_music victory.mp3 80

# 第五步：跳舞
./control.sh dance dance1 15
```

### 我的回复：
> "✅ 任务完成！
> 1. 红球已放入蓝色篮子
> 2. 后退了 5 步
> 3. 表演了 15 秒的庆祝舞蹈 🎉"

---

## 🎯 场景 4：多物体处理

### 你说：
> "把所有红色的球都放进篮子"

### 我的操作：
```bash
# 1. 拍照识别场景
./vision.sh detect red

# 响应示例:
# {
#   "objects": [
#     {"type": "red_ball", "x": 120, "y": 80},
#     {"type": "red_ball", "x": 200, "y": 100},
#     {"type": "red_ball", "x": 180, "y": 150}
#   ]
# }

# 2. 循环处理每个球
for ball in 球1 球2 球3:
    ./control.sh pickup <x> <y>
    ./control.sh place 250 90
    
    # 中途拍照确认剩余物体
    ./vision.sh capture_and_save progress.jpg
```

### 我的回复：
> "找到 3 个红球，正在处理...
> 
> ✓ 第 1 个已放入篮子
> ✓ 第 2 个已放入篮子
> ✓ 第 3 个已放入篮子
> 
> ✅ 所有红球已整理完毕"

---

## 🎯 场景 5：探索和导航

### 你说：
> "巡逻一圈看看周围有什么"

### 我的操作：
```bash
# 执行正方形巡逻路径
./control.sh patrol_square 10

# 在每个转角拍照
for i in 1 2 3 4; do
    ./control.sh forward 10
    ./vision.sh capture_and_save "corner_$i.jpg"
    # 分析场景
    ./control.sh right 90
done

# 汇总所有照片分析结果
```

### 我的回复：
> "巡逻完成，这是我看到的：
> 
> **北侧：** 一堆彩色积木
> **东侧：** 蓝色篮子（空的）
> **南侧：** 两个红球和一个黄球
> **西侧：** 没有特别的东西
> 
> 需要我整理一下吗？"

---

## 🎯 场景 6：实时反馈和调整

### 你说：
> "抓那个球"

### 我的操作：
```bash
# 1. 拍照
./vision.sh capture_and_save

# 2. 分析（假设识别到多个球）
```

### 我的回复：
> "我看到 3 个球：红色、蓝色、绿色。要抓哪个？"

### 你说：
> "红色的"

### 我的操作：
```bash
# 精确定位红球
./control.sh pickup 120 80 red_ball
```

### 我的回复：
> "✅ 已抓取红球。接下来放哪里？"

---

## 🎯 场景 7：异常处理

### 你说：
> "把球放到篮子里"

### 我的操作：
```bash
# 1. 尝试抓取
./control.sh pickup 120 80

# 响应: {"status": "object_not_found"}

# 2. 重新拍照
./vision.sh capture_and_save retry.jpg

# 3. 分析：球滚到了新位置 (150, 100)

# 4. 重试
./control.sh pickup 150 100
```

### 我的回复：
> "球的位置变了，我重新定位... ✅ 已抓取并放入篮子"

---

## 🎯 场景 8：复杂组合任务

### 你说：
> "整理一下这片区域：红色的放左边篮子，蓝色的放右边篮子，其他的扔一边"

### 我的操作：
```bash
# 1. 全景扫描
./vision.sh capture_and_save full_scene.jpg
# 识别所有物体并分类

# 2. 规划任务序列
# - 红球 x3 → 左篮 (100, 50)
# - 蓝球 x2 → 右篮 (300, 50)
# - 绿球 x1 → 边缘 (400, 200)

# 3. 优化路径（最短距离）
# 4. 执行
for object in sorted_objects:
    ./control.sh pickup <x> <y> <color>
    ./control.sh place <target_x> <target_y>

# 5. 最终验证
./vision.sh capture_and_save final.jpg
```

### 我的回复：
> "整理完成！
> 
> ✓ 3 个红球 → 左边篮子
> ✓ 2 个蓝球 → 右边篮子
> ✓ 1 个绿球 → 已移到边缘
> 
> 区域已整洁 ✨"

---

## 🎯 场景 9：娱乐模式

### 你说：
> "表演个节目给我看"

### 我的操作：
```bash
# 1. 播放音乐
./control.sh play_music showtime.mp3 90

# 2. 执行舞蹈序列
./control.sh dance dance2 30

# 3. 加入机械臂动作
while dancing:
    ./control.sh arm_move_to <随机位置>
    # 机械臂跟着节奏摆动

# 4. 结束姿势
./control.sh arm_move_to 0 0 50  # 挥手姿势
```

### 我的回复：
> "🎭 表演结束！喜欢吗？"

---

## 🎯 场景 10：持续监控

### 你说：
> "帮我盯着桌子，有人动了东西就告诉我"

### 我的操作：
```bash
# 1. 建立基线
./vision.sh capture_and_save baseline.jpg
# 分析并记录所有物体位置

# 2. 每 30 秒检查一次
while true; do
    sleep 30
    ./vision.sh capture_and_save check.jpg
    
    # 对比前后差异
    # 如果检测到变化 → 通知你
done
```

### 我的回复（检测到变化时）：
> "⚠️ 检测到变化：红球从 (120, 80) 移动到了 (200, 100)"

---

## 🛠️ 调试场景

### 你说：
> "机械臂好像抓不到东西"

### 我的操作：
```bash
# 1. 诊断模式
./vision.sh test_vision

# 2. 拍照查看对准情况
./vision.sh capture_and_save debug.jpg

# 3. 显示机械臂当前位置
./control.sh status | jq '.arm_position'

# 4. 手动微调测试
./control.sh arm_move_to 120 80 10
./vision.sh capture_and_save align_check.jpg
```

### 我的回复：
> "我看到的问题：
> - 机械臂位置：(118, 82) 
> - 球的位置：(120, 80)
> - 偏差：2cm
> 
> 可能是校准问题，试试调整抓取高度？"

---

## 📊 性能基准

### 典型任务耗时（参考）

| 任务 | 耗时 | 说明 |
|------|------|------|
| 拍照 | ~200ms | 640x480 分辨率 |
| 图像分析（OpenClaw） | ~2-5s | 使用 GPT-4V |
| 本地视觉检测 | ~50ms | OpenCV 颜色检测 |
| 小车移动 10 步 | ~3s | 中速 |
| 机械臂移动 | ~1-2s | 取决于距离 |
| 抓取动作 | ~1s | 下降+夹紧+提升 |
| 智能抓取（完整） | ~5-8s | 含视觉伺服 |
| 舞蹈（30秒） | 30s | 预设动作 |

### 复杂任务示例

**"把 5 个球整理到篮子里"**
- 总耗时：~60-90 秒
- 拆解：
  - 初始场景分析：5s
  - 单次抓放：10-15s × 5 = 50-75s
  - 最终验证：5s

---

## 💡 最佳实践

### 1. 光照条件
- 保持稳定照明（避免强烈阴影）
- 避免逆光（摄像头对着窗户）

### 2. 工作区域
- 使用对比鲜明的背景（白色/黑色工作台）
- 保持整洁（减少干扰物）
- 固定篮子等目标位置

### 3. 物体特征
- 推荐使用颜色鲜艳的物体（红、蓝、绿）
- 形状规则（球、方块）比不规则物体更容易识别
- 大小适中（3-10cm）

### 4. 错误处理
- 如果识别失败，调整光照/角度后重试
- 如果抓取失败，检查物体重量和夹爪力度
- 定期校准机械臂位置

---

**开始你的机器人之旅吧！** 有任何问题随时问我 🦊
