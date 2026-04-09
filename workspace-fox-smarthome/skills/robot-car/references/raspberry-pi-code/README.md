# Robot Car - 树莓派端代码

这是完整的树莓派端实现代码。

## 📁 文件结构

```
raspberry-pi-code/
├── api_server.py           # Flask API 服务器（主入口）
├── robot_controller.py     # 机器人总控制器
├── vision_servo.py         # 视觉伺服控制器
├── config.py               # 配置文件
├── requirements.txt        # Python 依赖
├── hardware/               # 硬件驱动模块
│   ├── __init__.py
│   ├── motor.py            # 电机控制
│   ├── arm.py              # 机械臂控制
│   └── camera.py           # 摄像头控制
└── vision/                 # 视觉处理模块
    ├── __init__.py
    └── detector.py         # 物体检测（OpenCV）
```

## 🚀 快速部署

### 1. 复制代码到树莓派

```bash
# 在树莓派上
mkdir -p ~/robot-car
cd ~/robot-car

# 复制所有文件到这里
```

### 2. 安装依赖

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 修改配置

编辑 `config.py`，根据你的硬件修改：
- GPIO 引脚定义
- 舵机通道映射
- 机械臂尺寸参数
- 相机标定参数

### 4. 测试硬件

```bash
# 测试电机
python3 -c "from hardware.motor import MotorController; m = MotorController(); m.forward(50, 2)"

# 测试机械臂
python3 -c "from hardware.arm import ArmController; a = ArmController(); a.gripper_open()"

# 测试摄像头
python3 -c "from hardware.camera import CameraController; c = CameraController(); print('OK' if c.capture() is not None else 'FAIL')"
```

### 5. 启动 API 服务器

```bash
# 手动启动（测试用）
python3 api_server.py

# 或使用 systemd 开机自启动（见下文）
```

## 🔧 配置开机自启动

创建 systemd 服务文件：

```bash
sudo nano /etc/systemd/system/robot-car.service
```

内容：

```ini
[Unit]
Description=Robot Car API Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/robot-car
Environment="PATH=/home/pi/robot-car/venv/bin"
ExecStart=/home/pi/robot-car/venv/bin/python3 /home/pi/robot-car/api_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable robot-car
sudo systemctl start robot-car

# 查看状态
sudo systemctl status robot-car

# 查看日志
sudo journalctl -u robot-car -f
```

## 📝 代码说明

### `api_server.py`
- Flask HTTP API 服务器
- 暴露所有控制接口
- 处理请求并调用 `robot_controller`

### `robot_controller.py`
- 机器人总控制器
- 协调所有硬件模块
- 实现高级任务逻辑

### `vision_servo.py`
- 视觉伺服控制器
- 实现闭环控制算法
- PID 控制器

### `hardware/motor.py`
- 电机控制器
- 支持前进/后退/转向
- PWM 速度控制

### `hardware/arm.py`
- 机械臂控制器
- 逆运动学（IK）计算
- 舵机控制

### `hardware/camera.py`
- 摄像头控制器
- 图像采集
- base64 编码

### `vision/detector.py`
- OpenCV 物体检测
- 颜色检测
- 形状识别

## 🛠️ 自定义和扩展

### 修改 GPIO 引脚

编辑 `config.py` 中的 `MOTOR_PINS`：

```python
MOTOR_PINS = {
    'left_forward': 17,   # 改成你的引脚
    'left_backward': 27,
    ...
}
```

### 添加新的检测颜色

编辑 `vision/detector.py` 中的 `color_ranges`：

```python
self.color_ranges = {
    ...
    'purple': [
        (np.array([130, 100, 100]), np.array([160, 255, 255]))
    ]
}
```

### 实现完整的逆运动学

替换 `hardware/arm.py` 中的 `_inverse_kinematics` 方法，使用你的机械臂实际参数。

## 🐛 故障排查

### API 服务器无法启动

```bash
# 检查端口占用
sudo lsof -i :5000

# 查看详细错误
python3 api_server.py
```

### 摄像头无法打开

```bash
# 检测设备
ls /dev/video*
v4l2-ctl --list-devices

# 测试拍照
libcamera-still -o test.jpg  # CSI 摄像头
fswebcam test.jpg            # USB 摄像头
```

### GPIO 权限错误

```bash
# 将用户添加到 gpio 组
sudo usermod -a -G gpio pi

# 重新登录后生效
```

### I2C 设备未找到（舵机驱动板）

```bash
# 启用 I2C
sudo raspi-config
# → Interface Options → I2C → Enable

# 重启
sudo reboot

# 检测 I2C 设备
sudo i2cdetect -y 1
```

## 📚 进一步阅读

- [树莓派 GPIO 文档](https://www.raspberrypi.com/documentation/computers/os.html#gpio)
- [OpenCV 教程](https://docs.opencv.org/4.x/d9/df8/tutorial_root.html)
- [Adafruit ServoKit 文档](https://learn.adafruit.com/16-channel-pwm-servo-driver)
- [Flask 文档](https://flask.palletsprojects.com/)

---

**祝你玩得开心！** 🦊
