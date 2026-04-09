#!/usr/bin/env python3
"""
Robot Car API Server
树莓派机器人小车的 HTTP API 服务器
"""

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import time
import logging
from robot_controller import RobotController

# 初始化 Flask
app = Flask(__name__)
CORS(app)  # 允许跨域

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/robot-car.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 初始化机器人控制器
try:
    controller = RobotController()
    logger.info("机器人控制器初始化成功")
except Exception as e:
    logger.error(f"控制器初始化失败: {e}")
    controller = None

# ============ 错误处理 ============

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "internal server error"}), 500

# ============ 基础接口 ============

@app.route('/status', methods=['GET'])
def status():
    """健康检查和状态查询"""
    if controller is None:
        return jsonify({"status": "error", "message": "controller not initialized"}), 503
    
    try:
        return jsonify(controller.get_status())
    except Exception as e:
        logger.error(f"获取状态失败: {e}")
        return jsonify({"error": str(e)}), 500

# ============ 摄像头接口 ============

@app.route('/camera/snapshot', methods=['GET'])
def camera_snapshot():
    """拍照并返回 base64 图片"""
    try:
        result = controller.camera_snapshot()
        return jsonify(result)
    except Exception as e:
        logger.error(f"拍照失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/camera/stream', methods=['GET'])
def camera_stream():
    """视频流（MJPEG）"""
    try:
        return Response(
            controller.camera_stream(),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )
    except Exception as e:
        logger.error(f"视频流失败: {e}")
        return jsonify({"error": str(e)}), 500

# ============ 小车移动接口 ============

@app.route('/car/move', methods=['POST'])
def car_move():
    """
    移动小车
    Body: {"direction": "forward|backward|left|right|stop", "steps": 10, "speed": 50}
    """
    try:
        data = request.json
        direction = data.get('direction')
        steps = data.get('steps', 1)
        speed = data.get('speed', 50)
        
        if not direction:
            return jsonify({"error": "missing direction parameter"}), 400
        
        logger.info(f"移动指令: {direction}, steps={steps}, speed={speed}")
        
        result = controller.move(direction, steps, speed)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"移动失败: {e}")
        return jsonify({"error": str(e)}), 500

# ============ 机械臂接口 ============

@app.route('/arm/moveTo', methods=['POST'])
def arm_move_to():
    """
    移动机械臂到指定坐标
    Body: {"x": 120, "y": 80, "z": 30, "speed": 50}
    """
    try:
        data = request.json
        x = data.get('x')
        y = data.get('y')
        z = data.get('z')
        speed = data.get('speed', 50)
        
        if x is None or y is None or z is None:
            return jsonify({"error": "missing x, y, or z parameter"}), 400
        
        logger.info(f"机械臂移动到: ({x}, {y}, {z})")
        
        result = controller.arm_move_to(x, y, z, speed)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"机械臂移动失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/arm/grab', methods=['POST'])
def arm_grab():
    """
    抓取
    Body: {"force": 50}
    """
    try:
        data = request.json or {}
        force = data.get('force', 50)
        
        logger.info(f"抓取，力度: {force}")
        
        result = controller.arm_grab(force)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"抓取失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/arm/release', methods=['POST'])
def arm_release():
    """释放"""
    try:
        logger.info("释放")
        result = controller.arm_release()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"释放失败: {e}")
        return jsonify({"error": str(e)}), 500

# ============ 高级任务接口 ============

@app.route('/task/pickup', methods=['POST'])
def task_pickup():
    """
    智能抓取（带视觉伺服）
    Body: {"approx_x": 120, "approx_y": 80, "target_type": "red_ball", "max_retries": 3}
    """
    try:
        data = request.json
        approx_x = data.get('approx_x')
        approx_y = data.get('approx_y')
        target_type = data.get('target_type')
        max_retries = data.get('max_retries', 3)
        
        if approx_x is None or approx_y is None:
            return jsonify({"error": "missing approx_x or approx_y"}), 400
        
        logger.info(f"智能抓取: ({approx_x}, {approx_y}), type={target_type}")
        
        result = controller.pickup_with_tracking(
            initial_x=approx_x,
            initial_y=approx_y,
            target_type=target_type,
            max_retries=max_retries
        )
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"智能抓取失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/task/place', methods=['POST'])
def task_place():
    """
    智能放置
    Body: {"approx_x": 250, "approx_y": 90, "drop_height": 20}
    """
    try:
        data = request.json
        approx_x = data.get('approx_x')
        approx_y = data.get('approx_y')
        drop_height = data.get('drop_height', 20)
        
        if approx_x is None or approx_y is None:
            return jsonify({"error": "missing approx_x or approx_y"}), 400
        
        logger.info(f"智能放置: ({approx_x}, {approx_y}), height={drop_height}")
        
        result = controller.place_object(
            target_x=approx_x,
            target_y=approx_y,
            drop_height=drop_height
        )
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"智能放置失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/task/navigate', methods=['POST'])
def task_navigate():
    """
    自主导航
    Body: {"target_x": 100, "target_y": 200, "avoid_obstacles": true, "max_speed": 80}
    """
    try:
        data = request.json
        target_x = data.get('target_x')
        target_y = data.get('target_y')
        avoid_obstacles = data.get('avoid_obstacles', True)
        max_speed = data.get('max_speed', 80)
        
        if target_x is None or target_y is None:
            return jsonify({"error": "missing target_x or target_y"}), 400
        
        logger.info(f"导航到: ({target_x}, {target_y})")
        
        result = controller.navigate_to(
            target_x=target_x,
            target_y=target_y,
            avoid_obstacles=avoid_obstacles,
            max_speed=max_speed
        )
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"导航失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/task/dance', methods=['POST'])
def task_dance():
    """
    执行舞蹈动作
    Body: {"routine": "dance1", "duration_sec": 30}
    """
    try:
        data = request.json or {}
        routine = data.get('routine', 'dance1')
        duration_sec = data.get('duration_sec', 30)
        
        logger.info(f"舞蹈: {routine}, 时长: {duration_sec}s")
        
        result = controller.dance(routine, duration_sec)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"舞蹈失败: {e}")
        return jsonify({"error": str(e)}), 500

# ============ 娱乐功能 ============

@app.route('/audio/play', methods=['POST'])
def audio_play():
    """
    播放音乐
    Body: {"song": "dance.mp3", "volume": 80, "loop": false}
    """
    try:
        data = request.json
        song = data.get('song')
        volume = data.get('volume', 80)
        loop = data.get('loop', False)
        
        if not song:
            return jsonify({"error": "missing song parameter"}), 400
        
        logger.info(f"播放音乐: {song}, 音量: {volume}")
        
        result = controller.play_music(song, volume, loop)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"播放音乐失败: {e}")
        return jsonify({"error": str(e)}), 500

# ============ 传感器接口 ============

@app.route('/vision/detect', methods=['POST'])
def vision_detect():
    """
    本地视觉检测
    Body: {"targets": ["red_ball", "blue_cube"]}
    """
    try:
        data = request.json or {}
        targets = data.get('targets')
        
        logger.info(f"视觉检测: {targets}")
        
        result = controller.detect_objects(targets)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"视觉检测失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/sensors', methods=['GET'])
def sensors():
    """读取传感器数据"""
    try:
        result = controller.read_sensors()
        return jsonify(result)
    except Exception as e:
        logger.error(f"读取传感器失败: {e}")
        return jsonify({"error": str(e)}), 500

# ============ 主入口 ============

if __name__ == '__main__':
    logger.info("启动 Robot Car API Server...")
    logger.info("监听地址: 0.0.0.0:5000")
    
    # 生产环境建议用 gunicorn 或 waitress
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,  # 生产环境设为 False
        threaded=True
    )
