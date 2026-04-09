# Robot Car API 规范

树莓派端 HTTP API 接口设计文档。

---

## 服务端框架建议

### Python Flask 示例

```python
from flask import Flask, request, jsonify, Response
import base64
import cv2
import json

app = Flask(__name__)

# 初始化硬件控制器
from robot_controller import RobotController
controller = RobotController()

# CORS 支持（可选）
from flask_cors import CORS
CORS(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
```

---

## 基础接口

### 1. 健康检查

```http
GET /status
```

**响应:**
```json
{
  "status": "ok",
  "timestamp": 1710144000,
  "hardware": {
    "camera": true,
    "motors": true,
    "arm": true,
    "battery_percent": 85
  },
  "position": {
    "x": 0,
    "y": 0,
    "heading": 0
  },
  "current_task": null
}
```

**实现示例:**
```python
@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "status": "ok",
        "timestamp": int(time.time()),
        "hardware": controller.get_hardware_status(),
        "position": controller.get_position(),
        "current_task": controller.current_task
    })
```

---

## 摄像头接口

### 2. 拍照

```http
GET /camera/snapshot
```

**响应:**
```json
{
  "timestamp": 1710144000,
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
  "resolution": {"width": 640, "height": 480}
}
```

**实现示例:**
```python
@app.route('/camera/snapshot', methods=['GET'])
def camera_snapshot():
    frame = controller.camera.capture()
    
    # 编码为 JPEG
    _, buffer = cv2.imencode('.jpg', frame)
    base64_image = base64.b64encode(buffer).decode('utf-8')
    
    return jsonify({
        "timestamp": int(time.time()),
        "image": f"data:image/jpeg;base64,{base64_image}",
        "resolution": {
            "width": frame.shape[1],
            "height": frame.shape[0]
        }
    })
```

### 3. 视频流（可选）

```http
GET /camera/stream
```

**响应:** MJPEG 流

**实现示例:**
```python
def generate_frames():
    while True:
        frame = controller.camera.capture()
        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/camera/stream', methods=['GET'])
def camera_stream():
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )
```

---

## 小车移动接口

### 4. 移动控制

```http
POST /car/move
Content-Type: application/json

{
  "direction": "forward",  // forward | backward | left | right | stop
  "steps": 10,             // 可选，默认 1
  "speed": 50              // 可选，0-100，默认 50
}
```

**响应:**
```json
{
  "status": "ok",
  "moved": {
    "direction": "forward",
    "steps": 10,
    "duration_ms": 2000
  },
  "new_position": {"x": 10, "y": 0, "heading": 0}
}
```

**实现示例:**
```python
@app.route('/car/move', methods=['POST'])
def car_move():
    data = request.json
    direction = data['direction']
    steps = data.get('steps', 1)
    speed = data.get('speed', 50)
    
    start_time = time.time()
    result = controller.move(direction, steps, speed)
    duration = int((time.time() - start_time) * 1000)
    
    return jsonify({
        "status": "ok" if result else "error",
        "moved": {
            "direction": direction,
            "steps": steps,
            "duration_ms": duration
        },
        "new_position": controller.get_position()
    })
```

---

## 机械臂接口

### 5. 移动到坐标

```http
POST /arm/moveTo
Content-Type: application/json

{
  "x": 120,
  "y": 80,
  "z": 30,
  "speed": 50  // 可选
}
```

**响应:**
```json
{
  "status": "ok",
  "position": {"x": 120, "y": 80, "z": 30},
  "joint_angles": [45, 90, -30, 0]  // 可选，各舵机角度
}
```

**实现示例:**
```python
@app.route('/arm/moveTo', methods=['POST'])
def arm_move_to():
    data = request.json
    x, y, z = data['x'], data['y'], data['z']
    speed = data.get('speed', 50)
    
    success = controller.arm.move_to(x, y, z, speed)
    
    return jsonify({
        "status": "ok" if success else "error",
        "position": {"x": x, "y": y, "z": z},
        "joint_angles": controller.arm.get_joint_angles()
    })
```

### 6. 抓取

```http
POST /arm/grab
Content-Type: application/json

{
  "force": 50  // 可选，夹持力度 0-100
}
```

**响应:**
```json
{
  "status": "ok",
  "gripper_state": "closed",
  "has_object": true  // 可选，是否检测到物体
}
```

### 7. 释放

```http
POST /arm/release
```

**响应:**
```json
{
  "status": "ok",
  "gripper_state": "open"
}
```

---

## 高级任务接口（进阶）

### 8. 智能抓取

```http
POST /task/pickup
Content-Type: application/json

{
  "target_type": "red_ball",  // 可选，物体类型（用于本地识别）
  "approx_x": 120,             // 初始估计坐标
  "approx_y": 80,
  "max_retries": 3             // 可选，最大重试次数
}
```

**响应:**
```json
{
  "status": "success",  // success | failed | object_not_found
  "attempts": 1,
  "final_position": {"x": 122, "y": 79, "z": 10},
  "duration_ms": 3500
}
```

**实现要点:**
```python
@app.route('/task/pickup', methods=['POST'])
def task_pickup():
    data = request.json
    
    # 使用本地视觉伺服
    result = controller.pickup_with_tracking(
        target_type=data.get('target_type'),
        initial_x=data['approx_x'],
        initial_y=data['approx_y'],
        max_retries=data.get('max_retries', 3)
    )
    
    return jsonify(result)

# 控制器实现（伪代码）
class RobotController:
    def pickup_with_tracking(self, target_type, initial_x, initial_y, max_retries):
        attempts = 0
        
        while attempts < max_retries:
            attempts += 1
            
            # 1. 移动到初始位置上方
            self.arm.move_to(initial_x, initial_y, z=50)
            
            # 2. 本地视觉精细对准
            for _ in range(10):  # 最多 10 次微调
                frame = self.camera.capture()
                obj_pos = self.detect_object(frame, target_type)
                
                if obj_pos is None:
                    return {"status": "object_not_found", "attempts": attempts}
                
                error_x = obj_pos['x'] - self.arm.center_x
                error_y = obj_pos['y'] - self.arm.center_y
                
                if abs(error_x) < 5 and abs(error_y) < 5:
                    break  # 对准了
                
                # 微调
                self.arm.adjust(error_x * 0.5, error_y * 0.5)
                time.sleep(0.1)
            
            # 3. 下降 + 抓取
            self.arm.lower(z=10)
            self.arm.gripper_close()
            
            # 4. 验证是否抓到
            self.arm.raise_(z=30)
            if self.check_has_object():
                return {
                    "status": "success",
                    "attempts": attempts,
                    "final_position": self.arm.get_position(),
                    "duration_ms": int(time.time() * 1000)
                }
        
        return {"status": "failed", "attempts": attempts}
```

### 9. 智能放置

```http
POST /task/place
Content-Type: application/json

{
  "approx_x": 250,
  "approx_y": 90,
  "drop_height": 20  // 可选，释放高度
}
```

**响应:** 同 pickup

### 10. 自主导航

```http
POST /task/navigate
Content-Type: application/json

{
  "target_x": 100,
  "target_y": 200,
  "avoid_obstacles": true,  // 可选，是否避障
  "max_speed": 80           // 可选
}
```

**响应:**
```json
{
  "status": "arrived",  // arrived | blocked | timeout
  "path_length": 150,
  "duration_ms": 5000,
  "obstacles_avoided": 2
}
```

---

## 娱乐功能接口

### 11. 舞蹈

```http
POST /task/dance
Content-Type: application/json

{
  "routine": "dance1",  // dance1 | dance2 | random
  "duration_sec": 30    // 可选
}
```

**响应:**
```json
{
  "status": "ok",
  "routine": "dance1",
  "duration_ms": 30000
}
```

**实现示例:**
```python
@app.route('/task/dance', methods=['POST'])
def task_dance():
    data = request.json
    routine = data.get('routine', 'default')
    
    # 预定义舞蹈动作序列
    dance_moves = {
        "dance1": [
            {"action": "forward", "steps": 2},
            {"action": "spin", "degrees": 360},
            {"action": "backward", "steps": 2},
            {"action": "wave_arm"}
        ],
        "dance2": [
            {"action": "wiggle", "times": 3},
            {"action": "spin", "degrees": 720},
        ]
    }
    
    moves = dance_moves.get(routine, dance_moves["dance1"])
    
    for move in moves:
        controller.execute_move(move)
    
    return jsonify({"status": "ok", "routine": routine})
```

### 12. 音频播放

```http
POST /audio/play
Content-Type: application/json

{
  "song": "dance.mp3",  // 文件名或 URL
  "volume": 80,         // 可选，0-100
  "loop": false         // 可选
}
```

**响应:**
```json
{
  "status": "playing",
  "duration_sec": 45
}
```

**实现示例:**
```python
import pygame

@app.route('/audio/play', methods=['POST'])
def audio_play():
    data = request.json
    song = data['song']
    volume = data.get('volume', 80) / 100.0
    
    pygame.mixer.init()
    pygame.mixer.music.load(f"/home/pi/music/{song}")
    pygame.mixer.music.set_volume(volume)
    pygame.mixer.music.play()
    
    return jsonify({"status": "playing"})
```

---

## 传感器接口（可选）

### 13. 本地视觉检测

```http
POST /vision/detect
Content-Type: application/json

{
  "targets": ["red_ball", "blue_cube"]  // 可选，要检测的物体类型
}
```

**响应:**
```json
{
  "objects": [
    {"type": "red_ball", "x": 120, "y": 80, "confidence": 0.95},
    {"type": "blue_cube", "x": 200, "y": 150, "confidence": 0.88}
  ],
  "timestamp": 1710144000
}
```

**实现示例（OpenCV 颜色检测）:**
```python
@app.route('/vision/detect', methods=['POST'])
def vision_detect():
    frame = controller.camera.capture()
    objects = []
    
    # 红色物体检测
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    red_mask = cv2.inRange(hsv, (0, 100, 100), (10, 255, 255))
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for cnt in contours:
        if cv2.contourArea(cnt) > 100:  # 过滤噪点
            M = cv2.moments(cnt)
            if M['m00'] > 0:
                cx = int(M['m10'] / M['m00'])
                cy = int(M['m01'] / M['m00'])
                objects.append({
                    "type": "red_ball",
                    "x": cx,
                    "y": cy,
                    "confidence": 0.9
                })
    
    return jsonify({"objects": objects, "timestamp": int(time.time())})
```

### 14. 传感器读取

```http
GET /sensors
```

**响应:**
```json
{
  "ultrasonic": {"distance_cm": 25},
  "gyroscope": {"roll": 0.5, "pitch": -1.2, "yaw": 180},
  "temperature": 28.5,
  "battery": 85
}
```

---

## 错误处理

所有接口在错误时返回：

```json
{
  "status": "error",
  "error": "motor_fault",
  "message": "Left motor not responding",
  "code": 500
}
```

**常见错误码:**
- `400` - 参数错误
- `404` - 端点不存在
- `500` - 硬件故障
- `503` - 设备忙碌

---

## 推荐的依赖库

### Python 依赖
```bash
pip install flask flask-cors opencv-python numpy RPi.GPIO pygame
```

### 硬件库（根据你的硬件选择）
```bash
# 舵机控制
pip install adafruit-circuitpython-servokit

# 电机驱动
pip install adafruit-circuitpython-motorkit

# 摄像头
pip install picamera2  # 树莓派官方摄像头
```

---

## 部署建议

### 1. 开机自启动

创建 systemd 服务：
```bash
# /etc/systemd/system/robot-api.service
[Unit]
Description=Robot Car API Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/robot-car
ExecStart=/usr/bin/python3 /home/pi/robot-car/api_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl enable robot-api
sudo systemctl start robot-api
```

### 2. 日志记录

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/robot-car.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

### 3. 安全建议

```python
# 添加简单的 API 密钥验证
API_KEY = "your-secret-key"

from functools import wraps

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key != API_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/car/move', methods=['POST'])
@require_api_key
def car_move():
    # ...
```

---

**文档版本:** 1.0  
**创建日期:** 2026-03-11  
**适用硬件:** 树莓派 3B+/4B/5 + 通用机械臂 + USB/CSI 摄像头
