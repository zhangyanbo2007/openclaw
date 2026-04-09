#!/usr/bin/env python3
"""
Visual Servo Controller
视觉伺服控制器 - 实现闭环控制
"""

import time
import logging

logger = logging.getLogger(__name__)

class PIDController:
    """PID 控制器"""
    
    def __init__(self, Kp, Ki, Kd):
        self.Kp = Kp  # 比例系数
        self.Ki = Ki  # 积分系数
        self.Kd = Kd  # 微分系数
        
        self.prev_error = 0
        self.integral = 0
    
    def update(self, error, dt):
        """
        计算 PID 输出
        
        Args:
            error: 当前误差
            dt: 时间间隔
        
        Returns:
            控制量
        """
        # 积分项
        self.integral += error * dt
        
        # 微分项
        derivative = (error - self.prev_error) / dt if dt > 0 else 0
        
        # PID 输出
        output = (self.Kp * error + 
                  self.Ki * self.integral + 
                  self.Kd * derivative)
        
        self.prev_error = error
        
        return output
    
    def reset(self):
        """重置控制器"""
        self.prev_error = 0
        self.integral = 0


class VisualServoController:
    """视觉伺服控制器"""
    
    def __init__(self, camera, arm, pixel_to_mm=0.5):
        """
        初始化
        
        Args:
            camera: 摄像头控制器
            arm: 机械臂控制器
            pixel_to_mm: 像素到毫米的转换系数（需要相机标定）
        """
        self.camera = camera
        self.arm = arm
        self.pixel_to_mm = pixel_to_mm
        
        # PID 控制器
        self.pid_x = PIDController(Kp=0.6, Ki=0.02, Kd=0.1)
        self.pid_y = PIDController(Kp=0.6, Ki=0.02, Kd=0.1)
        
        logger.info("视觉伺服控制器初始化完成")
    
    def align_to_target(self, detect_fn, threshold=5, max_iter=20, dt=0.1):
        """
        通用视觉伺服对准
        
        Args:
            detect_fn: 检测函数，返回 {'x': px, 'y': py} 或 None
            threshold: 对准阈值（像素）
            max_iter: 最大迭代次数
            dt: 控制周期（秒）
        
        Returns:
            bool: 是否成功对准
        """
        logger.info(f"开始视觉伺服对准（阈值={threshold}px, 最大迭代={max_iter}）")
        
        # 重置 PID
        self.pid_x.reset()
        self.pid_y.reset()
        
        for iteration in range(max_iter):
            # 1. 拍照
            frame = self.camera.capture()
            if frame is None:
                logger.error("拍照失败")
                return False
            
            # 2. 检测目标
            target_pos = detect_fn(frame)
            
            if target_pos is None:
                logger.warning(f"[迭代 {iteration+1}] 目标丢失")
                return False
            
            # 3. 计算误差（目标应该在视野中心）
            center_x = frame.shape[1] / 2
            center_y = frame.shape[0] / 2
            
            error_x = target_pos['x'] - center_x
            error_y = target_pos['y'] - center_y
            
            # 4. 检查是否对准
            if abs(error_x) < threshold and abs(error_y) < threshold:
                logger.info(f"[迭代 {iteration+1}] ✓ 对准成功！误差: ({error_x:.1f}, {error_y:.1f}) px")
                return True
            
            # 5. PID 计算调整量（像素）
            adjust_x_px = self.pid_x.update(error_x, dt)
            adjust_y_px = self.pid_y.update(error_y, dt)
            
            # 6. 像素到物理坐标转换
            adjust_x_mm = adjust_x_px * self.pixel_to_mm
            adjust_y_mm = adjust_y_px * self.pixel_to_mm
            
            # 7. 移动机械臂
            current = self.arm.get_position()
            new_x = current['x'] + adjust_x_mm
            new_y = current['y'] + adjust_y_mm
            
            self.arm.move_to(new_x, new_y, current['z'])
            
            logger.debug(f"[迭代 {iteration+1}] 误差: ({error_x:.1f}, {error_y:.1f}) px | "
                        f"调整: ({adjust_x_mm:.2f}, {adjust_y_mm:.2f}) mm")
            
            # 8. 等待稳定
            time.sleep(dt)
        
        logger.warning(f"✗ 对准失败：超过最大迭代次数 {max_iter}")
        return False
    
    def pickup_object(self, initial_x, initial_y, detect_fn, max_retries=3):
        """
        完整的智能抓取流程（带视觉伺服）
        
        Args:
            initial_x: 初始估计 X 坐标（mm）
            initial_y: 初始估计 Y 坐标（mm）
            detect_fn: 检测函数
            max_retries: 最大重试次数
        
        Returns:
            {"status": "success|failed|object_not_found", ...}
        """
        logger.info(f"开始智能抓取任务：初始位置 ({initial_x}, {initial_y})")
        
        attempts = 0
        
        while attempts < max_retries:
            attempts += 1
            logger.info(f"=== 尝试 {attempts}/{max_retries} ===")
            
            try:
                # 阶段1: 粗定位 - 移动到初始位置上方
                logger.info("阶段1: 粗定位...")
                self.arm.move_to(initial_x, initial_y, z=50)
                time.sleep(0.5)  # 等待稳定
                
                # 阶段2: 精细对准 - 视觉伺服
                logger.info("阶段2: 视觉伺服精细对准...")
                if not self.align_to_target(detect_fn, threshold=3, max_iter=15):
                    logger.warning("对准失败，重试...")
                    continue
                
                # 阶段3: 下降
                logger.info("阶段3: 下降...")
                current = self.arm.get_position()
                self.arm.move_to(current['x'], current['y'], z=10)
                time.sleep(0.3)
                
                # 阶段4: 抓取
                logger.info("阶段4: 抓取...")
                self.arm.gripper_close(force=60)
                time.sleep(0.5)
                
                # 阶段5: 提升
                logger.info("阶段5: 提升...")
                self.arm.move_to(current['x'], current['y'], z=40)
                time.sleep(0.3)
                
                # 阶段6: 验证是否抓到
                logger.info("阶段6: 验证...")
                if self.arm.has_object():
                    logger.info("✓ 抓取成功！")
                    return {
                        "status": "success",
                        "attempts": attempts,
                        "final_position": self.arm.get_position(),
                        "duration_ms": int(time.time() * 1000)
                    }
                else:
                    logger.warning("夹爪为空，重试...")
                    # 释放并重试
                    self.arm.gripper_open()
                    time.sleep(0.3)
                    continue
                    
            except Exception as e:
                logger.error(f"抓取过程出错: {e}")
                continue
        
        # 所有尝试都失败了
        logger.error(f"✗ 抓取失败：已尝试 {attempts} 次")
        return {
            "status": "failed",
            "attempts": attempts,
            "error": "max retries exceeded"
        }
    
    def track_moving_object(self, detect_fn, duration_sec=5):
        """
        跟踪移动物体
        
        Args:
            detect_fn: 检测函数
            duration_sec: 跟踪持续时间
        
        Returns:
            轨迹列表
        """
        logger.info(f"开始跟踪移动物体（{duration_sec}秒）")
        
        start_time = time.time()
        trajectory = []
        
        while time.time() - start_time < duration_sec:
            # 拍照
            frame = self.camera.capture()
            if frame is None:
                continue
            
            # 检测
            target_pos = detect_fn(frame)
            if target_pos is None:
                logger.warning("目标丢失")
                continue
            
            # 记录轨迹
            trajectory.append({
                "timestamp": time.time(),
                "x": target_pos['x'],
                "y": target_pos['y']
            })
            
            # 跟随（不抓取）
            self.align_to_target(detect_fn, threshold=10, max_iter=2, dt=0.05)
        
        logger.info(f"跟踪完成，共记录 {len(trajectory)} 个点")
        
        return trajectory
