#!/usr/bin/env python3
"""
Robot Controller
机器人控制器 - 协调所有硬件模块
"""

import time
import logging
from hardware.motor import MotorController
from hardware.arm import ArmController
from hardware.camera import CameraController
from vision_servo import VisualServoController
from vision.detector import ObjectDetector

logger = logging.getLogger(__name__)

class RobotController:
    """机器人总控制器"""
    
    def __init__(self):
        """初始化所有硬件"""
        logger.info("初始化机器人控制器...")
        
        # 初始化硬件模块
        try:
            self.motor = MotorController()
            logger.info("✓ 电机控制器初始化成功")
        except Exception as e:
            logger.error(f"✗ 电机控制器初始化失败: {e}")
            self.motor = None
        
        try:
            self.arm = ArmController()
            logger.info("✓ 机械臂控制器初始化成功")
        except Exception as e:
            logger.error(f"✗ 机械臂控制器初始化失败: {e}")
            self.arm = None
        
        try:
            self.camera = CameraController(device=0)
            logger.info("✓ 摄像头初始化成功")
        except Exception as e:
            logger.error(f"✗ 摄像头初始化失败: {e}")
            self.camera = None
        
        # 初始化视觉伺服控制器
        if self.camera and self.arm:
            try:
                self.servo = VisualServoController(self.camera, self.arm)
                logger.info("✓ 视觉伺服控制器初始化成功")
            except Exception as e:
                logger.error(f"✗ 视觉伺服控制器初始化失败: {e}")
                self.servo = None
        else:
            self.servo = None
        
        # 初始化物体检测器
        try:
            self.detector = ObjectDetector()
            logger.info("✓ 物体检测器初始化成功")
        except Exception as e:
            logger.error(f"✗ 物体检测器初始化失败: {e}")
            self.detector = None
        
        # 状态变量
        self.position = {'x': 0, 'y': 0, 'heading': 0}
        self.current_task = None
        
        logger.info("机器人控制器初始化完成")
    
    # ============ 状态查询 ============
    
    def get_status(self):
        """获取机器人当前状态"""
        return {
            "status": "ok",
            "timestamp": int(time.time()),
            "hardware": {
                "camera": self.camera is not None and self.camera.is_available(),
                "motors": self.motor is not None,
                "arm": self.arm is not None,
                "battery_percent": self._get_battery_level()
            },
            "position": self.position,
            "current_task": self.current_task
        }
    
    def _get_battery_level(self):
        """获取电池电量（示例）"""
        # TODO: 实现实际的电池检测
        return 85
    
    # ============ 摄像头功能 ============
    
    def camera_snapshot(self):
        """拍照并返回 base64 图片"""
        if not self.camera:
            raise Exception("摄像头未初始化")
        
        frame = self.camera.capture()
        image_b64 = self.camera.encode_base64(frame)
        
        return {
            "timestamp": int(time.time()),
            "image": f"data:image/jpeg;base64,{image_b64}",
            "resolution": {
                "width": frame.shape[1],
                "height": frame.shape[0]
            }
        }
    
    def camera_stream(self):
        """视频流生成器"""
        if not self.camera:
            raise Exception("摄像头未初始化")
        
        return self.camera.stream_generator()
    
    # ============ 移动控制 ============
    
    def move(self, direction, steps=1, speed=50):
        """
        移动小车
        
        Args:
            direction: forward, backward, left, right, stop
            steps: 移动步数
            speed: 速度 (0-100)
        """
        if not self.motor:
            raise Exception("电机控制器未初始化")
        
        start_time = time.time()
        
        if direction == "forward":
            self.motor.forward(speed, steps)
            self.position['x'] += steps
        elif direction == "backward":
            self.motor.backward(speed, steps)
            self.position['x'] -= steps
        elif direction == "left":
            self.motor.turn_left(speed, steps)
            self.position['heading'] = (self.position['heading'] - 90) % 360
        elif direction == "right":
            self.motor.turn_right(speed, steps)
            self.position['heading'] = (self.position['heading'] + 90) % 360
        elif direction == "stop":
            self.motor.stop()
        else:
            raise ValueError(f"未知方向: {direction}")
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return {
            "status": "ok",
            "moved": {
                "direction": direction,
                "steps": steps,
                "duration_ms": duration_ms
            },
            "new_position": self.position.copy()
        }
    
    # ============ 机械臂控制 ============
    
    def arm_move_to(self, x, y, z, speed=50):
        """移动机械臂到指定坐标"""
        if not self.arm:
            raise Exception("机械臂未初始化")
        
        success = self.arm.move_to(x, y, z, speed)
        
        return {
            "status": "ok" if success else "error",
            "position": {"x": x, "y": y, "z": z},
            "joint_angles": self.arm.get_joint_angles()
        }
    
    def arm_grab(self, force=50):
        """抓取"""
        if not self.arm:
            raise Exception("机械臂未初始化")
        
        success = self.arm.gripper_close(force)
        
        return {
            "status": "ok" if success else "error",
            "gripper_state": "closed",
            "has_object": self.arm.has_object()
        }
    
    def arm_release(self):
        """释放"""
        if not self.arm:
            raise Exception("机械臂未初始化")
        
        success = self.arm.gripper_open()
        
        return {
            "status": "ok" if success else "error",
            "gripper_state": "open"
        }
    
    # ============ 高级任务 ============
    
    def pickup_with_tracking(self, initial_x, initial_y, target_type=None, max_retries=3):
        """
        智能抓取（带视觉伺服）
        
        Args:
            initial_x: 初始估计 X 坐标
            initial_y: 初始估计 Y 坐标
            target_type: 目标类型（red_ball, blue_cube 等）
            max_retries: 最大重试次数
        
        Returns:
            {"status": "success|failed|object_not_found", ...}
        """
        if not self.servo:
            raise Exception("视觉伺服控制器未初始化")
        
        self.current_task = "pickup"
        
        # 定义检测函数
        if target_type:
            detect_fn = lambda frame: self.detector.detect_by_type(frame, target_type)
        else:
            detect_fn = lambda frame: self.detector.detect_nearest(frame)
        
        # 执行视觉伺服抓取
        result = self.servo.pickup_object(initial_x, initial_y, detect_fn, max_retries)
        
        self.current_task = None
        return result
    
    def place_object(self, target_x, target_y, drop_height=20):
        """
        智能放置
        
        Args:
            target_x: 目标 X 坐标
            target_y: 目标 Y 坐标
            drop_height: 释放高度
        """
        if not self.arm:
            raise Exception("机械臂未初始化")
        
        self.current_task = "place"
        
        start_time = time.time()
        
        # 移动到目标上方
        self.arm.move_to(target_x, target_y, z=drop_height + 10)
        time.sleep(0.3)
        
        # 下降到释放高度
        self.arm.move_to(target_x, target_y, z=drop_height)
        time.sleep(0.3)
        
        # 释放
        self.arm.gripper_open()
        time.sleep(0.3)
        
        # 提升
        self.arm.move_to(target_x, target_y, z=drop_height + 20)
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        self.current_task = None
        
        return {
            "status": "success",
            "position": {"x": target_x, "y": target_y, "z": drop_height},
            "duration_ms": duration_ms
        }
    
    def navigate_to(self, target_x, target_y, avoid_obstacles=True, max_speed=80):
        """
        自主导航
        
        Args:
            target_x: 目标 X 坐标
            target_y: 目标 Y 坐标
            avoid_obstacles: 是否避障
            max_speed: 最大速度
        """
        if not self.motor:
            raise Exception("电机控制器未初始化")
        
        self.current_task = "navigate"
        
        start_time = time.time()
        obstacles_avoided = 0
        
        # 简化版：直线前进（实际应该用路径规划）
        # TODO: 实现 A* 或 RRT 路径规划
        
        while True:
            # 计算距离
            dx = target_x - self.position['x']
            dy = target_y - self.position['y']
            distance = (dx**2 + dy**2) ** 0.5
            
            if distance < 5:  # 到达目标
                self.motor.stop()
                break
            
            # 避障检测（如果启用）
            if avoid_obstacles and self._detect_obstacle():
                logger.info("检测到障碍物，避让...")
                self._avoid_obstacle()
                obstacles_avoided += 1
                continue
            
            # 前进
            self.motor.forward(max_speed, steps=1)
            self.position['x'] += 1
            time.sleep(0.1)
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        self.current_task = None
        
        return {
            "status": "arrived",
            "path_length": int(distance),
            "duration_ms": duration_ms,
            "obstacles_avoided": obstacles_avoided
        }
    
    def _detect_obstacle(self):
        """检测前方障碍物"""
        # TODO: 实现超声波或视觉障碍物检测
        return False
    
    def _avoid_obstacle(self):
        """避障动作"""
        # 简单策略：后退 + 转向
        self.motor.backward(50, steps=2)
        time.sleep(0.3)
        self.motor.turn_left(50, steps=1)
        time.sleep(0.3)
    
    def dance(self, routine="dance1", duration_sec=30):
        """
        执行舞蹈动作
        
        Args:
            routine: 舞蹈套路名称
            duration_sec: 持续时间
        """
        if not self.motor:
            raise Exception("电机控制器未初始化")
        
        self.current_task = "dance"
        
        start_time = time.time()
        
        # 预定义舞蹈动作
        dance_routines = {
            "dance1": [
                ("forward", 2, 60),
                ("spin", 360, 80),
                ("backward", 2, 60),
                ("wiggle", 3, 50),
            ],
            "dance2": [
                ("wiggle", 5, 70),
                ("spin", 720, 100),
                ("forward", 1, 80),
                ("backward", 1, 80),
            ]
        }
        
        moves = dance_routines.get(routine, dance_routines["dance1"])
        
        for move_type, param, speed in moves:
            if time.time() - start_time > duration_sec:
                break
            
            if move_type == "forward":
                self.motor.forward(speed, steps=param)
            elif move_type == "backward":
                self.motor.backward(speed, steps=param)
            elif move_type == "spin":
                self._spin(param, speed)
            elif move_type == "wiggle":
                self._wiggle(param, speed)
            
            time.sleep(0.2)
        
        self.motor.stop()
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        self.current_task = None
        
        return {
            "status": "ok",
            "routine": routine,
            "duration_ms": duration_ms
        }
    
    def _spin(self, degrees, speed):
        """原地旋转"""
        # 简化：固定时间旋转
        duration = degrees / 360.0  # 假设 360° 需要 1 秒
        self.motor.turn_right(speed, steps=int(degrees/90))
    
    def _wiggle(self, times, speed):
        """摇摆动作"""
        for _ in range(times):
            self.motor.turn_left(speed, steps=1)
            time.sleep(0.1)
            self.motor.turn_right(speed, steps=1)
            time.sleep(0.1)
    
    # ============ 娱乐功能 ============
    
    def play_music(self, song, volume=80, loop=False):
        """
        播放音乐
        
        Args:
            song: 音乐文件名
            volume: 音量 (0-100)
            loop: 是否循环
        """
        import pygame
        
        try:
            pygame.mixer.init()
            music_path = f"/home/pi/music/{song}"
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.set_volume(volume / 100.0)
            pygame.mixer.music.play(-1 if loop else 0)
            
            return {
                "status": "playing",
                "song": song,
                "volume": volume
            }
        except Exception as e:
            logger.error(f"播放音乐失败: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    # ============ 传感器和视觉 ============
    
    def detect_objects(self, targets=None):
        """
        本地视觉检测
        
        Args:
            targets: 要检测的物体类型列表
        
        Returns:
            {"objects": [{"type": "red_ball", "x": 120, "y": 80}, ...]}
        """
        if not self.camera or not self.detector:
            raise Exception("摄像头或检测器未初始化")
        
        frame = self.camera.capture()
        objects = self.detector.detect_all(frame, targets)
        
        return {
            "objects": objects,
            "timestamp": int(time.time())
        }
    
    def read_sensors(self):
        """读取所有传感器数据"""
        # TODO: 实现实际的传感器读取
        return {
            "ultrasonic": {"distance_cm": 25},
            "gyroscope": {"roll": 0.5, "pitch": -1.2, "yaw": 180},
            "temperature": 28.5,
            "battery": self._get_battery_level()
        }
    
    def __del__(self):
        """清理资源"""
        if self.motor:
            self.motor.stop()
        if self.camera:
            self.camera.release()
