"""
实时摄像头目标检测模块
调用笔记本摄像头进行实时图像分类识别目标

作者: zhangpeng
时间: 2025-08-31
"""

import cv2
from ultralytics import YOLO
import argparse
from typing import List
import sys
import os
import logging


class CameraObjectDetector:
    def __init__(self, model_path, conf_threshold=0.5):
        """
        初始化摄像头目标识别器
        
        Args:
            model_path (str): 模型文件路径
            conf_threshold (float): 置信度阈值
        """
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.cap = None
        
        # 尝试使用配置管理器设置日志
        self._setup_logging()
        
        # 初始化事件处理机制
        try:
            # 添加项目根目录到Python路径
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            # 动态导入事件处理模块
            import importlib.util
            event_handler_path = os.path.join(project_root, 'src', 'events', 'event_handler.py')
            spec = importlib.util.spec_from_file_location("event_handler", event_handler_path)
            event_handler_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(event_handler_module)
            
            self.event_handler = event_handler_module.event_handler
            self.objectDetectionEvent = event_handler_module.objectDetectionEvent
            
        except Exception as e:
            self.event_handler = None
            logging.error(f"警告: 事件处理模块初始化失败，将不触发事件: {e}")
    
    def _setup_logging(self):
        """设置日志"""
        try:
            from src.config.config_manager import config_manager
            config_manager.setup_logging()
        except ImportError:
            # 如果无法导入配置管理器，使用默认日志设置
            log_dir = "logs"
            os.makedirs(log_dir, exist_ok=True)
            
            from logging.handlers import RotatingFileHandler
            
            # 设置日志格式
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            
            # 设置文件处理器
            file_handler = RotatingFileHandler(
                os.path.join(log_dir, "camera_detector.log"),
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            
            # 获取记录器并添加处理器
            self.logger = logging.getLogger("camera_object_detector")
            self.logger.setLevel(logging.INFO)
            self.logger.addHandler(file_handler)
            
            # 设置控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    def detect_and_display(self):
        """
        实时检测并显示结果
        """
        # 打开摄像头
        self.cap = cv2.VideoCapture(1)
        
        # 检查摄像头是否成功打开
        if not self.cap.isOpened():
            self.logger.error("无法打开摄像头")
            return
        
        self.logger.info("摄像头已打开，开始实时检测")
        self.logger.info("按 'q' 键退出")
        
        # 存储检测到的目标
        detected_objects = set()
        frame_count = 0
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                self.logger.warning("无法读取摄像头帧")
                break
            
            # 每隔几帧进行一次检测以提高性能
            if frame_count % 5 == 0:
                # 使用模型进行预测
                results = self.model(frame, verbose=False)
                
                # 清空当前帧的目标列表
                current_frame_objects = []
                
                # 解析检测结果
                for result in results:
                    boxes = result.boxes
                    if boxes is not None:
                        for box in boxes:
                            # 获取置信度
                            confidence = box.conf[0].item()
                            if confidence > self.conf_threshold:
                                # 获取类别ID和名称
                                class_id = int(box.cls[0].item())
                                class_name = self.model.names[class_id]
                                
                                # 获取边界框坐标
                                xyxy = box.xyxy[0].cpu().numpy()
                                x1, y1, x2, y2 = map(int, xyxy)
                                
                                # 添加到当前帧目标列表 (class_name, confidence, bbox)
                                current_frame_objects.append((class_name, confidence, (x1, y1, x2, y2)))
                                
                                # 添加到总目标集合
                                detected_objects.add(class_name)
                                
                                # 触发事件（如果启用了事件处理）
                                if self.event_handler and self.objectDetectionEvent:
                                    event = self.objectDetectionEvent(class_name, confidence, frame)
                                    self.event_handler.handle_event(event)
                
                # 在图像上绘制边界框和标签
                self._draw_boxes(frame, current_frame_objects)
                
                # 显示检测到的目标列表
                self._display_detected_objects(frame, list(detected_objects))
            
            # 显示结果
            cv2.imshow('Object Detection', frame)
            
            # 按 'q' 键退出
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            frame_count += 1
        
        # 释放资源
        self.cap.release()
        cv2.destroyAllWindows()
        self.logger.info("摄像头检测结束")
    
    def _draw_boxes(self, frame, objects):
        """
        在图像上绘制边界框和标签
        
        Args:
            frame: 图像帧
            objects: 检测到的对象列表 [(class_name, confidence, (x1, y1, x2, y2)), ...]
        """
        for obj in objects:
            class_name, confidence, (x1, y1, x2, y2) = obj
            label = f"{class_name}: {confidence:.2f}"
            
            # 绘制边界框
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # 计算标签大小并绘制标签背景
            (text_width, text_height), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.rectangle(frame, (x1, y1 - text_height - baseline - 5), (x1 + text_width, y1), (0, 255, 0), -1)
            
            # 在边界框上方绘制标签
            cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 
                        0.7, (0, 0, 0), 2, cv2.LINE_AA)

    def _display_detected_objects(self, frame, objects):
        """
        显示检测到的对象列表
        
        Args:
            frame: 图像帧
            objects: 检测到的对象列表
        """
        # 显示检测到的对象列表，增大字体大小
        y_offset = 60
        cv2.putText(frame, "Detected objects:", (10, y_offset), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        
        y_offset += 30
        for obj in objects[:5]:  # 只显示前5个对象
            cv2.putText(frame, f"- {obj}", (10, y_offset), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
            y_offset += 30

    def __del__(self):
        """析构函数，确保释放摄像头资源"""
        if self.cap and self.cap.isOpened():
            self.cap.release()


def main():
    parser = argparse.ArgumentParser(description='实时摄像头目标检测')
    parser.add_argument('--model_path', type=str, required=True, 
                       help='模型文件路径')
    parser.add_argument('--conf_threshold', type=float, default=0.5,
                       help='置信度阈值 (默认: 0.5)')
    
    args = parser.parse_args()
    
    # 创建检测器并开始检测
    detector = CameraObjectDetector(args.model_path, args.conf_threshold)
    detector.detect_and_display()


if __name__ == '__main__':
    main()