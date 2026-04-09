# Robot Car 快速启动指南

硬件到货后的完整配置流程。

---

## 📦 开箱清单

确认你有这些东西：

- [ ] 树莓派（3B+/4B/5）
- [ ] 机械臂（舵机驱动板 + 舵机）
- [ ] 小车底盘（电机 + 驱动板）
- [ ] 摄像头（USB 或 CSI）
- [ ] 电源（树莓派 + 电机）
- [ ] microSD 卡（推荐 32GB+）
- [ ] 网络连接（WiFi 或网线）

---

## 🚀 第一阶段：树莓派基础配置

### 1. 安装操作系统

**推荐：** Raspberry Pi OS Lite (64-bit)

```bash
# 使用 Raspberry Pi Imager
# 下载: https://www.raspberrypi.com/software/

# 配置时启用：
# - SSH
# - WiFi（设置 SSID 和密码）
# - 用户名/密码（建议: pi / 你的密码）
```

### 2. 首次连接

```bash
# 查找树莓派 IP
ping raspberrypi.local

# 或使用 IP 扫描工具
nmap -sn 192.168.1.0/24 | grep -i raspberry

# SSH 登录
ssh pi@raspberrypi.local
```

### 3. 系统更新

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git vim
```

---

## 🔧 第二阶段：安装依赖

### 1. 创建项目目录

```bash
mkdir -p ~/robot-car
cd ~/robot-car
```

### 2. 安装 Python 依赖

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装基础库
pip install flask flask-cors

# 安装视觉库
pip install opencv-python numpy

# 安装硬件库（根据你的硬件选择）

# GPIO 控制（通用）
pip install RPi.GPIO

# 舵机控制（推荐 Adafruit）
pip install adafruit-circuitpython-servokit

# 电机控制（如果用 Adafruit Motor HAT）
pip install adafruit-circuitpython-motorkit

# 摄像头（树莓派官方摄像头）
sudo apt install -y python3-picamera2

# 音频播放
pip install pygame
```

### 3. 测试硬件

```bash
# 测试 GPIO
python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); print('GPIO OK')"

# 测试摄像头（USB 摄像头）
sudo apt install -y v4l-utils
v4l2-ctl --list-devices

# 测试摄像头（CSI 摄像头）
libcamera-hello --timeout 2000
```

---

## 🤖 第三阶段：实现 API 服务器

### 1. 下载示例代码模板

创建 `~/robot-car/api_server.py`：

```python
from flask import Flask, request, jsonify
import time

app = Flask(__name__)

# ============ 占位控制器 ============
# 你需要根据实际硬件实现这些函数

class RobotController:
    def __init__(self):
        # 初始化硬件
        pass
    
    def get_status(self):
        return {
            "status": "ok",
            "timestamp": int(time.time()),
            "hardware": {
                "camera": True,  # TODO: 实际检测
                "motors": True,
                "arm": True,
                "battery_percent": 85
            }
        }
    
    def camera_capture(self):
        # TODO: 实现拍照
        # 返回 numpy array 或 PIL Image
        pass
    
    def move(self, direction, steps, speed):
        # TODO: 实现移动控制
        print(f"Moving {direction} for {steps} steps at speed {speed}")
        time.sleep(0.5)  # 模拟延迟
        return True
    
    def arm_move_to(self, x, y, z, speed):
        # TODO: 实现机械臂移动
        print(f"Arm moving to ({x}, {y}, {z}) at speed {speed}")
        time.sleep(1)
        return True
    
    def arm_grab(self, force):
        # TODO: 实现抓取
        print(f"Grabbing with force {force}")
        return True
    
    def arm_release(self):
        # TODO: 实现释放
        print("Releasing")
        return True

controller = RobotController()

# ============ API 端点 ============

@app.route('/status', methods=['GET'])
def status():
    return jsonify(controller.get_status())

@app.route('/camera/snapshot', methods=['GET'])
def camera_snapshot():
    # TODO: 实现拍照并返回 base64
    return jsonify({
        "timestamp": int(time.time()),
        "image": "data:image/jpeg;base64,placeholder",
        "resolution": {"width": 640, "height": 480}
    })

@app.route('/car/move', methods=['POST'])
def car_move():
    data = request.json
    direction = data['direction']
    steps = data.get('steps', 1)
    speed = data.get('speed', 50)
    
    success = controller.move(direction, steps, speed)
    
    return jsonify({
        "status": "ok" if success else "error",
        "moved": {"direction": direction, "steps": steps}
    })

@app.route('/arm/moveTo', methods=['POST'])
def arm_move_to():
    data = request.json
    x, y, z = data['x'], data['y'], data['z']
    speed = data.get('speed', 50)
    
    success = controller.arm_move_to(x, y, z, speed)
    
    return jsonify({
        "status": "ok" if success else "error",
        "position": {"x": x, "y": y, "z": z}
    })

@app.route('/arm/grab', methods=['POST'])
def arm_grab():
    force = request.json.get('force', 50)
    success = controller.arm_grab(force)
    return jsonify({"status": "ok" if success else "error"})

@app.route('/arm/release', methods=['POST'])
def arm_release():
    success = controller.arm_release()
    return jsonify({"status": "ok" if success else "error"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

### 2. 测试 API 服务器

```bash
# 启动服务器
cd ~/robot-car
source venv/bin/activate
python api_server.py

# 在另一个终端测试
curl http://localhost:5000/status

# 测试移动
curl -X POST http://localhost:5000/car/move \
  -H "Content-Type: application/json" \
  -d '{"direction": "forward", "steps": 5}'
```

---

## 🔌 第四阶段：接线和硬件配置

### 典型接线方案

#### 电机驱动（L298N 或 Adafruit Motor HAT）

```
树莓派                电机驱动板
GPIO 17 (BCM) -----> IN1 (左电机前进)
GPIO 27 (BCM) -----> IN2 (左电机后退)
GPIO 22 (BCM) -----> IN3 (右电机前进)
GPIO 23 (BCM) -----> IN4 (右电机后退)
GPIO 18 (PWM)  -----> ENA (左电机速度)
GPIO 13 (PWM)  -----> ENB (右电机速度)
5V             -----> VCC
GND            -----> GND
```

#### 舵机（PCA9685 舵机驱动板）

```
树莓派                PCA9685
GPIO 2 (SDA)  -----> SDA
GPIO 3 (SCL)  -----> SCL
5V            -----> VCC
GND           -----> GND

PCA9685              舵机
Channel 0     -----> 底座舵机
Channel 1     -----> 肩部舵机
Channel 2     -----> 肘部舵机
Channel 3     -----> 腕部舵机
Channel 4     -----> 夹爪舵机
```

#### 摄像头

```
# USB 摄像头: 直接插 USB 口

# CSI 摄像头: 插 CSI 排线接口（靠近 HDMI 口）
```

### 硬件配置代码示例

```python
# 电机控制（GPIO）
import RPi.GPIO as GPIO

class MotorController:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        self.pins = {
            'left_forward': 17,
            'left_backward': 27,
            'right_forward': 22,
            'right_backward': 23,
            'left_pwm': 18,
            'right_pwm': 13
        }
        
        for pin in self.pins.values():
            GPIO.setup(pin, GPIO.OUT)
        
        self.left_pwm = GPIO.PWM(self.pins['left_pwm'], 100)
        self.right_pwm = GPIO.PWM(self.pins['right_pwm'], 100)
        self.left_pwm.start(0)
        self.right_pwm.start(0)
    
    def forward(self, speed=50):
        GPIO.output(self.pins['left_forward'], GPIO.HIGH)
        GPIO.output(self.pins['left_backward'], GPIO.LOW)
        GPIO.output(self.pins['right_forward'], GPIO.HIGH)
        GPIO.output(self.pins['right_backward'], GPIO.LOW)
        self.left_pwm.ChangeDutyCycle(speed)
        self.right_pwm.ChangeDutyCycle(speed)

# 舵机控制（Adafruit PCA9685）
from adafruit_servokit import ServoKit

class ArmController:
    def __init__(self):
        self.kit = ServoKit(channels=16)
        self.servos = {
            'base': 0,
            'shoulder': 1,
            'elbow': 2,
            'wrist': 3,
            'gripper': 4
        }
    
    def set_angle(self, servo_name, angle):
        servo_id = self.servos[servo_name]
        self.kit.servo[servo_id].angle = angle

# 摄像头（OpenCV）
import cv2

class Camera:
    def __init__(self, device=0):
        self.cap = cv2.VideoCapture(device)
    
    def capture(self):
        ret, frame = self.cap.read()
        return frame if ret else None
```

---

## 🌐 第五阶段：网络配置

### 1. 设置静态 IP（可选）

```bash
sudo nano /etc/dhcpcd.conf

# 添加:
interface wlan0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1
```

### 2. 配置防火墙（可选）

```bash
sudo apt install ufw
sudo ufw allow 22    # SSH
sudo ufw allow 5000  # API 服务器
sudo ufw enable
```

### 3. 测试从 OpenClaw 访问

在 OpenClaw 所在机器上：

```bash
# 测试连通性
ping 192.168.1.100  # 或 raspberrypi.local

# 测试 API
curl http://192.168.1.100:5000/status
```

---

## 🎯 第六阶段：配置 OpenClaw Skill

### 1. 更新 API 地址

在 OpenClaw 机器上编辑 `~/.openclaw/workspace/skills/robot-car/scripts/control.sh`：

```bash
# 修改这一行
API_BASE="http://192.168.1.100:5000"  # 改成你的树莓派 IP
```

### 2. 测试 Skill

```bash
cd ~/.openclaw/workspace/skills/robot-car/scripts

# 测试连接
./control.sh status

# 测试移动
./control.sh forward 3

# 测试拍照
./vision.sh capture_and_save test.jpg
```

---

## ✅ 验证清单

完成以下测试确认系统正常：

- [ ] 树莓派可以 SSH 访问
- [ ] API 服务器启动成功（`curl http://树莓派IP:5000/status` 返回正常）
- [ ] 摄像头可以拍照（`/camera/snapshot` 返回图片）
- [ ] 小车可以移动（`/car/move` 控制电机）
- [ ] 机械臂可以控制（`/arm/moveTo` 移动舵机）
- [ ] OpenClaw 可以调用 Skill（`./control.sh status` 成功）
- [ ] 视觉系统正常（`./vision.sh test_vision` 通过）

---

## 🎉 开始使用

一切就绪后，对 OpenClaw 说：

**"拍张照片看看前面有什么"**

我会：
1. 调用树莓派拍照
2. 分析场景
3. 告诉你看到了什么

然后你就可以开始更复杂的任务了！

---

## 📚 下一步

- 实现高级任务接口（智能抓取、导航、舞蹈）
- 训练本地视觉模型（颜色/形状识别）
- 添加传感器（超声波、陀螺仪）
- 收集演示数据 → 训练行为克隆模型

---

## 🆘 常见问题

### Q: API 服务器无法启动？
```bash
# 检查端口占用
sudo lsof -i :5000

# 查看详细错误
python api_server.py
```

### Q: 摄像头拍照失败？
```bash
# 检测摄像头
v4l2-ctl --list-devices

# 测试拍照
libcamera-still -o test.jpg  # CSI 摄像头
fswebcam test.jpg            # USB 摄像头
```

### Q: 电机不转？
- 检查接线（特别是 GND）
- 检查电源（电机需要独立供电）
- 检查 GPIO 引脚是否正确
- 用万用表测试驱动板输出

### Q: OpenClaw 连接超时？
```bash
# 检查网络
ping raspberrypi.local

# 检查防火墙
sudo ufw status

# 增加超时时间（在 control.sh 中）
TIMEOUT=30
```

---

**准备好了吗？** 硬件到货后按这个清单一步步来，有问题随时问我 🦊
