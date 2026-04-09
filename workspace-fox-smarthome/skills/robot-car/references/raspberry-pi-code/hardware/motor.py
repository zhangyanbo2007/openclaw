#!/usr/bin/env python3
"""
Motor Controller
电机控制器 - 控制小车移动
"""

import time
import logging

# 根据你的硬件选择导入
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logging.warning("RPi.GPIO 不可用，使用模拟模式")

logger = logging.getLogger(__name__)

class MotorController:
    """电机控制器"""
    
    def __init__(self, use_gpio=True):
        """
        初始化电机控制器
        
        Args:
            use_gpio: 是否使用真实 GPIO（False 为测试模式）
        """
        self.use_gpio = use_gpio and GPIO_AVAILABLE
        
        if self.use_gpio:
            # GPIO 引脚定义（根据你的接线修改）
            self.pins = {
                'left_forward': 17,
                'left_backward': 27,
                'right_forward': 22,
                'right_backward': 23,
                'left_pwm_pin': 18,
                'right_pwm_pin': 13
            }
            
            # 初始化 GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            for pin in self.pins.values():
                GPIO.setup(pin, GPIO.OUT)
            
            # 初始化 PWM（速度控制）
            self.left_pwm = GPIO.PWM(self.pins['left_pwm_pin'], 100)  # 100Hz
            self.right_pwm = GPIO.PWM(self.pins['right_pwm_pin'], 100)
            self.left_pwm.start(0)
            self.right_pwm.start(0)
            
            logger.info("电机控制器初始化成功（GPIO 模式）")
        else:
            logger.info("电机控制器初始化成功（模拟模式）")
    
    def _set_motor(self, left_dir, right_dir, speed):
        """
        设置电机方向和速度
        
        Args:
            left_dir: 左电机方向 (1=前进, -1=后退, 0=停止)
            right_dir: 右电机方向
            speed: 速度 (0-100)
        """
        if not self.use_gpio:
            logger.debug(f"[模拟] 电机: L={left_dir}, R={right_dir}, 速度={speed}")
            return
        
        # 左电机
        if left_dir > 0:
            GPIO.output(self.pins['left_forward'], GPIO.HIGH)
            GPIO.output(self.pins['left_backward'], GPIO.LOW)
        elif left_dir < 0:
            GPIO.output(self.pins['left_forward'], GPIO.LOW)
            GPIO.output(self.pins['left_backward'], GPIO.HIGH)
        else:
            GPIO.output(self.pins['left_forward'], GPIO.LOW)
            GPIO.output(self.pins['left_backward'], GPIO.LOW)
        
        # 右电机
        if right_dir > 0:
            GPIO.output(self.pins['right_forward'], GPIO.HIGH)
            GPIO.output(self.pins['right_backward'], GPIO.LOW)
        elif right_dir < 0:
            GPIO.output(self.pins['right_forward'], GPIO.LOW)
            GPIO.output(self.pins['right_backward'], GPIO.HIGH)
        else:
            GPIO.output(self.pins['right_forward'], GPIO.LOW)
            GPIO.output(self.pins['right_backward'], GPIO.LOW)
        
        # 设置速度
        self.left_pwm.ChangeDutyCycle(abs(speed))
        self.right_pwm.ChangeDutyCycle(abs(speed))
    
    def forward(self, speed=50, steps=1):
        """前进"""
        logger.info(f"前进: 速度={speed}, 步数={steps}")
        self._set_motor(1, 1, speed)
        time.sleep(0.3 * steps)  # 每步约 0.3 秒
        self.stop()
    
    def backward(self, speed=50, steps=1):
        """后退"""
        logger.info(f"后退: 速度={speed}, 步数={steps}")
        self._set_motor(-1, -1, speed)
        time.sleep(0.3 * steps)
        self.stop()
    
    def turn_left(self, speed=50, steps=1):
        """左转"""
        logger.info(f"左转: 速度={speed}, 步数={steps}")
        self._set_motor(-1, 1, speed)  # 左后右前
        time.sleep(0.2 * steps)
        self.stop()
    
    def turn_right(self, speed=50, steps=1):
        """右转"""
        logger.info(f"右转: 速度={speed}, 步数={steps}")
        self._set_motor(1, -1, speed)  # 左前右后
        time.sleep(0.2 * steps)
        self.stop()
    
    def stop(self):
        """停止"""
        self._set_motor(0, 0, 0)
    
    def __del__(self):
        """清理 GPIO"""
        if self.use_gpio:
            self.stop()
            GPIO.cleanup()
