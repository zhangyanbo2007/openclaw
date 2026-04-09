# 进出门检测 + 人脸识别配置指南

## 📋 功能说明

当入户门打开时，系统自动：
1. 检测是**进门**还是**出门**（通过猫眼告警判断）
2. **进门**时：
   - 开启入户灯
   - 猫眼抓图
   - 阿里云人脸识别
   - 识别成功 → 播放"欢迎主人回家"
   - 识别失败 → 播放"欢迎回家"
   - 30 秒后关闭入户灯
3. **出门**时：
   - 开启入户灯 30 秒
   - 关闭入户灯
   - 不播放欢迎语

---

## 🔧 配置步骤

### 步骤 1: 配置 HA Token

编辑 `door_handler.sh` 脚本，填写你的 HA Token：

```bash
nano /home/zhangyanbo/.openclaw/workspace-fox-smarthome/scripts/door_handler.sh
```

找到并修改：
```bash
HA_TOKEN="你的 HA Token"
```

### 步骤 2: 在 HA 中添加配置

**方法 A: 使用 HACS File Editor**
1. 打开 HA → 开发者工具 → YAML 配置
2. 将 `homeassistant/door_automation.yaml` 内容复制到 `configuration.yaml`

**方法 B: 手动添加**
1. SSH 登录 HA
2. 编辑 `/config/configuration.yaml`
3. 添加 shell_command 配置

### 步骤 3: 重启 HA

```bash
# 在 HA 界面：设置 → 系统 → 重启
# 或 SSH: ha core restart
```

### 步骤 4: 测试

```bash
# 手动测试脚本
cd /home/zhangyanbo/.openclaw/workspace-fox-smarthome/scripts
export HA_URL="http://192.168.28.77:8123"
export HA_TOKEN="你的 HA Token"
bash door_handler.sh
```

---

## 📁 文件说明

| 文件 | 路径 | 作用 |
|------|------|------|
| `door_handler.sh` | `scripts/` | 进出门处理主脚本 |
| `face_recognition.sh` | `scripts/` | 人脸识别脚本 |
| `aliyun_face.py` | `scripts/` | 阿里云 API 封装 |
| `door_automation.yaml` | `homeassistant/` | HA 自动化配置示例 |

---

## 🔍 调试方法

### 查看日志

```bash
# 查看脚本执行日志
tail -f /tmp/openclaw/face_result.json

# 查看 HA 日志
ha core logs | grep door
```

### 手动测试人脸识别

```bash
cd /home/zhangyanbo/.openclaw/workspace-fox-smarthome/scripts
bash face_recognition.sh /tmp/openclaw/face_zhangyanbo.jpg
```

### 手动测试猫眼抓图

```bash
cd /home/zhangyanbo/.openclaw/workspace-fox-smarthome/scripts
# 参考 door_handler.sh 中的 capture_image 函数
```

---

## ⚙️ 配置参数

### 可调整的参数

| 参数 | 位置 | 默认值 | 说明 |
|------|------|--------|------|
| 人脸识别阈值 | `face_recognition.sh` | 80 | 相似度阈值（0-100） |
| 关灯延迟 | `door_handler.sh` | 30 秒 | 开灯后多久关闭 |
| 猫眼告警时间窗 | `door_handler.sh` | 30 秒 | 判断进出门的时间窗口 |

### 设备 Entity ID

需要替换为你实际的 Entity ID：
- 入户门窗传感器
- 入户灯（可能多个）
- 入户小爱音箱

---

## ❓ 常见问题

### Q: 人脸识别总是失败
A: 检查：
1. 阿里云 AccessKey 是否正确
2. 人脸库 `home_family` 是否存在
3. `zhangyanbo` 是否已录入人脸

### Q: 猫眼抓图失败
A: 检查：
1. 萤石 AppKey/Secret 是否正确
2. 猫眼设备是否在线
3. 设备序列号是否正确

### Q: 音箱不播放
A: 检查：
1. 小爱音箱 Entity ID 是否正确
2. HA 中是否安装了百度 TTS
3. 音箱音量是否开启

---

## 📞 技术支持

遇到问题可以：
1. 查看脚本日志
2. 检查 HA 日志
3. 测试各个组件单独工作
