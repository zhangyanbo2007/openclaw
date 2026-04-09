#!/usr/bin/env python3
"""
Configuration
配置文件
"""

# API 服务器配置
API_HOST = '0.0.0.0'
API_PORT = 5000
API_DEBUG = False

# 摄像头配置
CAMERA_DEVICE = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# 电机配置（GPIO 引脚）
MOTOR_PINS = {
    'left_forward': 17,
    'left_backward': 27,
    'right_forward': 22,
    'right_backward': 23,
    'left_pwm_pin': 18,
    'right_pwm_pin': 13
}

# 舵机配置（PCA9685 通道）
SERVO_CHANNELS = {
    'base': 0,
    'shoulder': 1,
    'elbow': 2,
    'wrist': 3,
    'gripper': 4
}

# 机械臂运动学参数（mm）
ARM_LINK_LENGTHS = {
    'shoulder_to_elbow': 100,
    'elbow_to_wrist': 100,
    'wrist_to_gripper': 50
}

# 视觉伺服参数
PIXEL_TO_MM = 0.5  # 像素到毫米的转换系数（需要相机标定）
PID_KP = 0.6
PID_KI = 0.02
PID_KD = 0.1

# 日志配置
LOG_FILE = '/var/log/robot-car.log'
LOG_LEVEL = 'INFO'

# 音乐文件路径
MUSIC_DIR = '/home/pi/music'
