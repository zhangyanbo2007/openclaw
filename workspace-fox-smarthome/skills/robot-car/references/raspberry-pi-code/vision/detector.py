#!/usr/bin/env python3
"""
Object Detector
物体检测器 - 使用 OpenCV 进行简单的颜色/形状检测
"""

import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class ObjectDetector:
    """物体检测器"""
    
    def __init__(self):
        """初始化检测器"""
        # 颜色范围定义（HSV 空间）
        self.color_ranges = {
            'red': [
                (np.array([0, 100, 100]), np.array([10, 255, 255])),     # 红色范围1
                (np.array([170, 100, 100]), np.array([180, 255, 255]))   # 红色范围2
            ],
            'blue': [
                (np.array([100, 100, 100]), np.array([130, 255, 255]))
            ],
            'green': [
                (np.array([40, 100, 100]), np.array([80, 255, 255]))
            ],
            'yellow': [
                (np.array([20, 100, 100]), np.array([40, 255, 255]))
            ]
        }
        
        logger.info("物体检测器初始化成功")
    
    def detect_by_color(self, frame, color):
        """
        按颜色检测物体
        
        Args:
            frame: 图像帧
            color: 颜色名称 ('red', 'blue', 'green', 'yellow')
        
        Returns:
            list: [{'x': px, 'y': py, 'area': area}, ...]
        """
        if color not in self.color_ranges:
            logger.warning(f"未知颜色: {color}")
            return []
        
        # 转换到 HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 创建掩码
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for lower, upper in self.color_ranges[color]:
            mask |= cv2.inRange(hsv, lower, upper)
        
        # 形态学操作（去噪）
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # 查找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        objects = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            
            # 过滤小噪点
            if area < 100:
                continue
            
            # 计算质心
            M = cv2.moments(cnt)
            if M['m00'] == 0:
                continue
            
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])
            
            objects.append({
                'x': cx,
                'y': cy,
                'area': int(area),
                'color': color
            })
        
        logger.debug(f"检测到 {len(objects)} 个 {color} 物体")
        return objects
    
    def detect_by_type(self, frame, object_type):
        """
        按类型检测物体
        
        Args:
            frame: 图像帧
            object_type: 物体类型 (如 'red_ball', 'blue_cube')
        
        Returns:
            dict: {'x': px, 'y': py} 或 None
        """
        # 解析类型（简化：颜色_形状）
        parts = object_type.split('_')
        if len(parts) < 1:
            return None
        
        color = parts[0]
        shape = parts[1] if len(parts) > 1 else 'any'
        
        # 检测颜色
        objects = self.detect_by_color(frame, color)
        
        if not objects:
            return None
        
        # 形状过滤（可选）
        if shape == 'ball':
            # 检测圆形度
            objects = [obj for obj in objects if self._is_circular(frame, obj)]
        elif shape == 'cube':
            # 检测方形度
            objects = [obj for obj in objects if not self._is_circular(frame, obj)]
        
        # 返回最大的一个
        if objects:
            largest = max(objects, key=lambda obj: obj['area'])
            return {'x': largest['x'], 'y': largest['y']}
        
        return None
    
    def detect_nearest(self, frame):
        """
        检测离视野中心最近的物体
        
        Args:
            frame: 图像帧
        
        Returns:
            dict: {'x': px, 'y': py} 或 None
        """
        # 检测所有颜色
        all_objects = []
        for color in ['red', 'blue', 'green', 'yellow']:
            objects = self.detect_by_color(frame, color)
            all_objects.extend(objects)
        
        if not all_objects:
            return None
        
        # 计算离中心最近的
        center_x = frame.shape[1] / 2
        center_y = frame.shape[0] / 2
        
        nearest = min(all_objects, key=lambda obj: 
                      (obj['x'] - center_x)**2 + (obj['y'] - center_y)**2)
        
        return {'x': nearest['x'], 'y': nearest['y']}
    
    def detect_all(self, frame, targets=None):
        """
        检测所有物体
        
        Args:
            frame: 图像帧
            targets: 要检测的类型列表，None 表示所有
        
        Returns:
            list: [{'type': 'red_ball', 'x': px, 'y': py, 'confidence': 0.9}, ...]
        """
        results = []
        
        # 默认检测所有颜色
        colors = ['red', 'blue', 'green', 'yellow']
        
        for color in colors:
            objects = self.detect_by_color(frame, color)
            
            for obj in objects:
                # 判断形状
                if self._is_circular(frame, obj):
                    obj_type = f"{color}_ball"
                else:
                    obj_type = f"{color}_cube"
                
                # 过滤目标
                if targets and obj_type not in targets:
                    continue
                
                results.append({
                    'type': obj_type,
                    'x': obj['x'],
                    'y': obj['y'],
                    'confidence': 0.9  # 简化：固定置信度
                })
        
        return results
    
    def _is_circular(self, frame, obj):
        """
        判断物体是否接近圆形
        
        Args:
            frame: 图像帧
            obj: 物体信息（需要包含轮廓）
        
        Returns:
            bool: 是否圆形
        """
        # 简化：假设面积大的都是圆形（实际应计算圆形度）
        # 圆形度 = 4π × area / perimeter^2
        # 完美圆形 = 1.0
        return True  # TODO: 实现真实的圆形检测
