#!/usr/bin/env python3
"""
Arm Controller
机械臂控制器 - 控制舵机机械臂
"""

import time
import logging
import math

# 根据你的硬件选择导入
try:
    from adafruit_servokit import ServoKit
    SERVOKIT_AVAILABLE = True
except ImportError:
    SERVOKIT_AVAILABLE = False
    logging.warning("adafruit_servokit 不可用，使用模拟模式")

logger = logging.getLogger(__name__)

class ArmController:
    """机械臂控制器"""
    
    def __init__(self, use_servos=True):
        """
        初始化机械臂控制器
        
        Args:
            use_servos: 是否使用真实舵机
        """
        self.use_servos = use_servos and SERVOKIT_AVAILABLE
        
        if self.use_servos:
            # 初始化 PCA9685 舵机驱动板（16 通道）
            self.kit = ServoKit(channels=16)
            
            # 舵机通道映射（根据你的接线修改）
            self.servos = {
                'base': 0,       # 底座旋转
                'shoulder': 1,   # 肩部
                'elbow': 2,      # 肘部
                'wrist': 3,      # 腕部
                'gripper': 4     # 夹爪
            }
            
            # 舵机角度范围（度）
            self.angle_limits = {
                'base': (0, 180),
                'shoulder': (0, 180),
                'elbow': (0, 180),
                'wrist': (0, 180),
                'gripper': (0, 180)  # 0=关闭, 180=打开
            }
            
            # 当前角度
            self.current_angles = {
                'base': 90,
                'shoulder': 90,
                'elbow': 90,
                'wrist': 90,
                'gripper': 180  # 初始打开
            }
            
            # 设置初始位置
            self._set_home_position()
            
            logger.info("机械臂控制器初始化成功（舵机模式）")
        else:
            # 模拟模式
            self.current_angles = {'base': 90, 'shoulder': 90, 'elbow': 90, 'wrist': 90, 'gripper': 180}
            self.current_position = {'x': 0, 'y': 0, 'z': 50}
            logger.info("机械臂控制器初始化成功（模拟模式）")
        
        # 运动学参数（简化，实际需要精确测量）
        self.link_lengths = {
            'shoulder_to_elbow': 100,  # mm
            'elbow_to_wrist': 100,
            'wrist_to_gripper': 50
        }
    
    def _set_home_position(self):
        """设置初始位置"""
        for name, angle in self.current_angles.items():
            self._set_servo_angle(name, angle)
        time.sleep(1)  # 等待舵机到位
    
    def _set_servo_angle(self, servo_name, angle):
        """
        设置舵机角度
        
        Args:
            servo_name: 舵机名称
            angle: 角度 (0-180)
        """
        # 限制角度范围
        min_angle, max_angle = self.angle_limits[servo_name]
        angle = max(min_angle, min(max_angle, angle))
        
        if self.use_servos:
            servo_id = self.servos[servo_name]
            self.kit.servo[servo_id].angle = angle
        
        self.current_angles[servo_name] = angle
        logger.debug(f"舵机 {servo_name} → {angle}°")
    
    def move_to(self, x, y, z, speed=50):
        """
        移动到指定笛卡尔坐标
        
        Args:
            x, y, z: 目标坐标 (mm)
            speed: 速度 (0-100) - 目前简化为延迟时间
        
        Returns:
            bool: 是否成功
        """
        logger.info(f"移动到坐标: ({x}, {y}, {z})")
        
        # 逆运动学计算（简化版，实际需要完整的 IK）
        angles = self._inverse_kinematics(x, y, z)
        
        if angles is None:
            logger.error("逆运动学求解失败（目标不可达）")
            return False
        
        # 平滑移动（插值）
        steps = 20
        for i in range(steps + 1):
            t = i / steps
            for name, target_angle in angles.items():
                current = self.current_angles[name]
                new_angle = current + (target_angle - current) * t
                self._set_servo_angle(name, new_angle)
            time.sleep(0.02)  # 20ms per step = 400ms total
        
        return True
    
    def _inverse_kinematics(self, x, y, z):
        """
        逆运动学求解（简化版）
        
        Args:
            x, y, z: 目标坐标
        
        Returns:
            dict: 各关节角度，或 None（不可达）
        """
        # 这是一个简化示例，实际需要根据你的机械臂结构编写完整的 IK
        
        # 底座角度（绕 Z 轴旋转）
        base_angle = math.degrees(math.atan2(y, x)) + 90
        
        # 平面距离
        r = math.sqrt(x**2 + y**2)
        
        # 简化：假设2自由度平面臂
        L1 = self.link_lengths['shoulder_to_elbow']
        L2 = self.link_lengths['elbow_to_wrist'] + self.link_lengths['wrist_to_gripper']
        
        # 目标距离
        d = math.sqrt(r**2 + z**2)
        
        # 检查可达性
        if d > (L1 + L2) or d < abs(L1 - L2):
            return None
        
        # 余弦定理求肘部角度
        cos_elbow = (L1**2 + L2**2 - d**2) / (2 * L1 * L2)
        cos_elbow = max(-1, min(1, cos_elbow))  # 限制范围
        elbow_angle = 180 - math.degrees(math.acos(cos_elbow))
        
        # 肩部角度
        alpha = math.atan2(z, r)
        beta = math.acos((L1**2 + d**2 - L2**2) / (2 * L1 * d))
        shoulder_angle = 90 - math.degrees(alpha + beta)
        
        # 腕部保持水平
        wrist_angle = 180 - shoulder_angle - elbow_angle
        
        return {
            'base': base_angle,
            'shoulder': shoulder_angle,
            'elbow': elbow_angle,
            'wrist': wrist_angle
        }
    
    def gripper_close(self, force=50):
        """
        关闭夹爪
        
        Args:
            force: 力度 (0-100) - 映射到角度
        
        Returns:
            bool: 是否成功
        """
        logger.info(f"关闭夹爪，力度: {force}")
        # 力度映射到角度 (0 = 完全关闭)
        angle = 180 - (force / 100.0) * 180
        self._set_servo_angle('gripper', angle)
        time.sleep(0.5)
        return True
    
    def gripper_open(self):
        """打开夹爪"""
        logger.info("打开夹爪")
        self._set_servo_angle('gripper', 180)
        time.sleep(0.5)
        return True
    
    def has_object(self):
        """
        检测夹爪是否夹住物体
        
        Returns:
            bool: 是否夹住
        """
        # TODO: 实现实际的检测（压力传感器/电流检测）
        # 简化：假设夹爪角度 < 90° 时有物体
        return self.current_angles['gripper'] < 90
    
    def get_position(self):
        """获取当前笛卡尔坐标"""
        # 正运动学计算（简化）
        # TODO: 实现完整的 FK
        return {'x': 0, 'y': 0, 'z': 50}
    
    def get_joint_angles(self):
        """获取当前关节角度"""
        return self.current_angles.copy()
    
    def __del__(self):
        """清理"""
        if self.use_servos:
            # 回到安全位置
            self.gripper_open()
