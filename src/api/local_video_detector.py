"""
本地视频流目标检测模块
用于识别本地视频文件中的目标

作者: zhangpeng
时间: 2025-08-31
"""

import cv2
from ultralytics import YOLO
import argparse
from typing import List, Dict
import sys
import os
import logging


class LocalVideoObjectDetector:
    def __init__(self, model_path, conf_threshold=0.5):
        """
        初始化本地视频目标识别器
        
        Args:
            model_path (str): 模型文件路径
            conf_threshold (float): 置信度阈值
        """
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        
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
            self.ObjectDetectionEvent = event_handler_module.ObjectDetectionEvent
            
        except Exception as e:
            self.event_handler = None
            self.ObjectDetectionEvent = None
            logging.warning(f"警告: 事件处理模块未找到，将不触发事件: {e}")
    
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
                os.path.join(log_dir, "local_video_object_detector.log"),
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            
            # 获取记录器并添加处理器
            self.logger = logging.getLogger("local_video_object_detector")
            self.logger.setLevel(logging.INFO)
            self.logger.addHandler(file_handler)
            
            # 设置控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    def detect_video(self, video_path):
        """
        检测视频中的目标
        
        Args:
            video_path (str): 视频文件路径
            
        Returns:
            dict: 检测结果，包含检测到的目标及其出现频率
        """
        # 打开视频文件
        cap = cv2.VideoCapture(video_path)
        
        # 检查视频是否成功打开
        if not cap.isOpened():
            self.logger.error(f"无法打开视频文件: {video_path}")
            raise ValueError(f"无法打开视频文件: {video_path}")
        
        self.logger.info(f"开始检测视频: {video_path}")
        
        # 存储检测到的目标及其出现频率
        object_frequency = {}
        
        frame_count = 0
        processed_frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 每隔30帧处理一次以提高性能
            if frame_count % 30 == 0:
                # 使用模型进行预测
                results = self.model(frame, verbose=False)
                
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
                                
                                # 更新目标频率统计
                                if class_name in object_frequency:
                                    object_frequency[class_name] += 1
                                else:
                                    object_frequency[class_name] = 1
                                
                                # 触发事件（如果启用了事件处理）
                                if self.event_handler and self.ObjectDetectionEvent:
                                    event = self.ObjectDetectionEvent(class_name, confidence, frame)
                                    self.event_handler.handle_event(event)
                
                processed_frame_count += 1
                self.logger.debug(f"已处理 {processed_frame_count} 帧")
            
            frame_count += 1
        
        # 释放视频资源
        cap.release()
        
        self.logger.info(f"视频检测完成，共处理 {processed_frame_count} 帧")
        self.logger.info(f"检测到的目标: {object_frequency}")
        
        return {
            'object_frequency': object_frequency,
            'total_frames_processed': processed_frame_count
        }
    
    def detect_and_display(self, video_path):
        """
        检测视频中的目标并实时显示结果
        
        Args:
            video_path (str): 视频文件路径
        """
        # 打开视频文件
        cap = cv2.VideoCapture(video_path)
        
        # 检查视频是否成功打开
        if not cap.isOpened():
            self.logger.error(f"无法打开视频文件: {video_path}")
            raise ValueError(f"无法打开视频文件: {video_path}")
        
        self.logger.info(f"开始检测并显示视频: {video_path}")
        
        # 存储检测到的目标
        detected_objects = set()
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 每隔5帧进行一次检测以提高性能
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
                                
                                # 添加到当前帧目标列表
                                current_frame_objects.append((class_name, confidence))
                                
                                # 添加到总目标集合
                                detected_objects.add(class_name)
                                
                                # 触发事件（如果启用了事件处理）
                                if self.event_handler and self.ObjectDetectionEvent:
                                    event = self.ObjectDetectionEvent(class_name, confidence, frame)
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
        cap.release()
        cv2.destroyAllWindows()
        self.logger.info("视频检测和显示结束")
    
    def _draw_boxes(self, frame, objects):
        """
        在图像上绘制边界框和标签
        
        Args:
            frame: 图像帧
            objects: 检测到的目标列表 [(class_name, confidence), ...]
        """
        height, width = frame.shape[:2]
        
        for i, (class_name, confidence) in enumerate(objects):
            # 绘制一个覆盖整个图像的边界框
            x1, y1 = int(0.05 * width), int(0.05 * height)
            x2, y2 = int(0.95 * width), int(0.95 * height)
            
            # 绘制边界框
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # 准备标签文本
            label = f'{class_name}: {confidence:.2f}'
            
            # 获取文本尺寸
            (text_width, text_height), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            
            # 绘制标签背景
            cv2.rectangle(frame, (x1, y1 - text_height - 10), (x1 + text_width, y1), (0, 255, 0), -1)
            
            # 绘制标签文本
            cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    
    def _display_detected_objects(self, frame, objects):
        """
        在图像上显示检测到的目标列表
        
        Args:
            frame: 图像帧
            objects: 检测到的目标列表
        """
        # 对目标列表进行排序
        sorted_objects = sorted(objects)
        
        # 在图像上显示目标列表
        y_offset = 30
        cv2.putText(frame, "Detected Objects:", (10, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        for i, obj in enumerate(sorted_objects):
            y_offset += 30
            cv2.putText(frame, f"- {obj}", (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)


def main():
    parser = argparse.ArgumentParser(description='本地视频目标检测')
    parser.add_argument('--model_path', type=str, required=True, 
                       help='模型文件路径')
    parser.add_argument('--video_path', type=str, required=True,
                       help='视频文件路径')
    parser.add_argument('--conf_threshold', type=float, default=0.5,
                       help='置信度阈值 (默认: 0.5)')
    parser.add_argument('--display', action='store_true',
                       help='是否实时显示检测结果')
    
    args = parser.parse_args()
    
    # 创建检测器
    detector = LocalVideoObjectDetector(args.model_path, args.conf_threshold)
    
    if args.display:
        # 实时显示检测结果
        detector.detect_and_display(args.video_path)
    else:
        # 只进行检测并输出结果
        result = detector.detect_video(args.video_path)
        print("检测结果:")
        print(f"  处理帧数: {result['total_frames_processed']}")
        print("  检测到的目标及其出现频率:")
        for obj, freq in result['object_frequency'].items():
            print(f"    {obj}: {freq}")


if __name__ == '__main__':
    main()