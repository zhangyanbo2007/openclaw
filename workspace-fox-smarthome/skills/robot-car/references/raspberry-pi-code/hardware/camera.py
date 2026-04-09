#!/usr/bin/env python3
"""
Camera Controller
摄像头控制器
"""

import cv2
import base64
import logging
import numpy as np

logger = logging.getLogger(__name__)

class CameraController:
    """摄像头控制器"""
    
    def __init__(self, device=0, width=640, height=480):
        """
        初始化摄像头
        
        Args:
            device: 设备 ID（0 表示第一个摄像头）
            width: 图像宽度
            height: 图像高度
        """
        self.device = device
        self.width = width
        self.height = height
        
        # 打开摄像头
        self.cap = cv2.VideoCapture(device)
        
        if not self.cap.isOpened():
            logger.error(f"无法打开摄像头 {device}")
            self.cap = None
            return
        
        # 设置分辨率
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        logger.info(f"摄像头初始化成功：{width}x{height}")
    
    def is_available(self):
        """摄像头是否可用"""
        return self.cap is not None and self.cap.isOpened()
    
    def capture(self):
        """
        拍照
        
        Returns:
            numpy.ndarray: 图像帧，或 None（失败）
        """
        if not self.is_available():
            logger.error("摄像头不可用")
            return None
        
        ret, frame = self.cap.read()
        
        if not ret:
            logger.error("读取帧失败")
            return None
        
        return frame
    
    def encode_base64(self, frame, format='.jpg', quality=85):
        """
        将图像编码为 base64
        
        Args:
            frame: 图像帧
            format: 格式 ('.jpg' 或 '.png')
            quality: JPEG 质量 (0-100)
        
        Returns:
            str: base64 编码的字符串
        """
        if frame is None:
            return None
        
        # 编码为 JPEG/PNG
        if format == '.jpg':
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        else:
            encode_param = []
        
        _, buffer = cv2.imencode(format, frame, encode_param)
        
        # 转换为 base64
        base64_str = base64.b64encode(buffer).decode('utf-8')
        
        return base64_str
    
    def stream_generator(self):
        """
        视频流生成器（用于 MJPEG 流）
        
        Yields:
            bytes: MJPEG 帧数据
        """
        while True:
            frame = self.capture()
            
            if frame is None:
                break
            
            # 编码为 JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            
            # 生成 MJPEG 帧
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    
    def release(self):
        """释放摄像头"""
        if self.cap:
            self.cap.release()
            logger.info("摄像头已释放")
    
    def __del__(self):
        """析构函数"""
        self.release()
