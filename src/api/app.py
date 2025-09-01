"""
目标检测API服务
提供视频目标检测接口

作者: zhangpeng
时间: 2025-08-31
"""

import os
import cv2
from flask import Flask, request, jsonify, render_template
from ultralytics import YOLO
import numpy as np
from typing import List
import sys
import os as os_orig
import logging


# 设置日志记录
def setup_logging():
    """设置日志记录"""
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
            os.path.join(log_dir, "api.log"),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # 获取记录器并添加处理器
        logger = logging.getLogger("object_detection_api")
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # 同时也为root logger添加处理器，确保所有日志都被记录
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

setup_logging()

# 创建Flask应用
app = Flask(__name__)
logger = logging.getLogger("object_detection_api")

# 全局模型变量
model = None
model_path = None

# 初始化事件处理机制
try:
    # 添加项目根目录到Python路径
    project_root = os_orig.path.dirname(os_orig.path.dirname(os_orig.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # 动态导入事件处理模块
    import importlib.util
    event_handler_path = os_orig.path.join(project_root, 'src', 'events', 'event_handler.py')
    spec = importlib.util.spec_from_file_location("event_handler", event_handler_path)
    event_handler_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(event_handler_module)
    
    event_handler = event_handler_module.event_handler
    objectDetectionEvent = event_handler_module.objectDetectionEvent
except Exception as e:
    event_handler = None
    objectDetectionEvent = None
    logging.error(f"警告: 事件处理模块未找到，将不触发事件: {e}")


def load_model(model_file_path):
    """
    加载模型
    
    Args:
        model_file_path (str): 模型文件路径
    
    Returns:
        model: 加载的模型对象
    """
    global model, model_path
    model = YOLO(model_file_path)
    model_path = model_file_path
    logging.info(f"模型加载成功: {model_file_path}")
    return model


def detect_objects_in_video(video_path, conf_threshold=0.5):
    """
    在视频中检测目标
    
    Args:
        video_path (str): 视频文件路径
        conf_threshold (float): 置信度阈值
    
    Returns:
        list: 检测到的目标列表
    """
    global model, event_handler, objectDetectionEvent
    
    if model is None:
        raise ValueError("模型未加载，请先调用load_model函数加载模型")
    
    logging.info(f"开始检测视频: {video_path}")
    cap = cv2.VideoCapture(video_path)
    
    # 存储检测到的目标
    detected_objects = set()
    
    frame_count = 0
    # 处理视频帧
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        # 每隔30帧处理一次，提高处理速度
        if frame_count % 30 == 0:
            # 使用模型进行预测
            results = model(frame)
            
            # 解析检测结果
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # 获取置信度
                        confidence = box.conf[0].item()
                        if confidence > conf_threshold:
                            # 获取类别ID和名称
                            class_id = int(box.cls[0].item())
                            class_name = model.names[class_id]
                            
                            # 添加到检测到的目标集合中
                            detected_objects.add(class_name)
                            
                            # 触发事件（如果启用了事件处理）
                            if event_handler and objectDetectionEvent:
                                event = objectDetectionEvent(class_name, confidence, frame)
                                event_handler.handle_event(event)
        
        frame_count += 1
    
    cap.release()
    
    # 转换为列表并排序
    result_list = sorted(list(detected_objects))
    logging.info(f"视频检测完成，检测到目标: {result_list}")
    return result_list


def detect_ingredients_in_video(video_path, conf_threshold=0.5):
    """
    在视频中检测目标
    
    Args:
        video_path (str): 视频文件路径
        conf_threshold (float): 置信度阈值
    
    Returns:
        list: 检测到的目标列表
    """
    return detect_objects_in_video(video_path, conf_threshold)


def detect_objects_in_image(image_path, conf_threshold=0.5):
    """
    在图片中检测目标
    
    Args:
        image_path (str): 图片文件路径
        conf_threshold (float): 置信度阈值
    
    Returns:
        list: 检测到的目标列表
    """
    global model, event_handler, objectDetectionEvent
    
    if model is None:
        raise ValueError("模型未加载，请先调用load_model函数加载模型")
    
    logging.info(f"开始检测图片: {image_path}")
    
    # 读取图片
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"无法读取图片: {image_path}")
    
    # 使用模型进行预测
    results = model(image)
    
    # 存储检测到的目标
    detected_objects = set()
    
    # 解析检测结果
    for result in results:
        boxes = result.boxes
        if boxes is not None:
            for box in boxes:
                # 获取置信度
                confidence = box.conf[0].item()
                if confidence > conf_threshold:
                    # 获取类别ID和名称
                    class_id = int(box.cls[0].item())
                    class_name = model.names[class_id]
                    
                    # 添加到检测到的目标集合中
                    detected_objects.add(class_name)
                    
                    # 触发事件（如果启用了事件处理）
                    if event_handler and objectDetectionEvent:
                        event = objectDetectionEvent(class_name, confidence, image)
                        event_handler.handle_event(event)
    
    # 转换为列表并排序
    result_list = sorted(list(detected_objects))
    logging.info(f"图片检测完成，检测到目标: {result_list}")
    return result_list


def detect_ingredients_in_image(image_path, conf_threshold=0.5):
    """
    在图片中检测目标
    
    Args:
        image_path (str): 图片文件路径
        conf_threshold (float): 置信度阈值
    
    Returns:
        list: 检测到的目标列表
    """
    return detect_objects_in_image(image_path, conf_threshold)


@app.route('/')
def home():
    """首页 - 返回API信息"""
    logger.info("访问首页")
    return jsonify({
        "message": "目标检测API服务",
        "endpoints": {
            "/load_model": "加载模型",
            "/detect": "检测视频中的目标",
            "/detect_image": "检测图片中的目标"
        }
    })


@app.route('/load_model', methods=['POST'])
def load_model_endpoint():
    """加载模型接口"""
    data = request.get_json()
    model_file_path = data.get('model_path')
    
    if not model_file_path or not os.path.exists(model_file_path):
        logging.warning(f"模型文件路径无效: {model_file_path}")
        return jsonify({"error": "模型文件路径无效"}), 400
    
    try:
        load_model(model_file_path)
        logging.info(f"模型加载成功: {model_file_path}")
        return jsonify({"message": "模型加载成功"})
    except Exception as e:
        logging.error(f"模型加载失败: {str(e)}")
        return jsonify({"error": f"模型加载失败: {str(e)}"}), 500


@app.route('/detect', methods=['POST'])
def detect_objects():
    """检测视频中的目标"""
    data = request.get_json()
    video_path = data.get('video_path')
    conf_threshold = data.get('conf_threshold', 0.5)
    
    if not video_path or not os.path.exists(video_path):
        logging.warning(f"视频文件路径无效: {video_path}")
        return jsonify({"error": "视频文件路径无效"}), 400
    
    try:
        objects = detect_ingredients_in_video(video_path, conf_threshold)
        logging.info(f"视频目标检测完成: {video_path}")
        return jsonify({
            "message": "检测完成",
            "objects": objects
        })
    except Exception as e:
        logging.error(f"视频检测失败: {str(e)}")
        return jsonify({"error": f"检测失败: {str(e)}"}), 500


@app.route('/detect_image', methods=['POST'])
def detect_objects_in_image_endpoint():
    """检测图片中的目标"""
    data = request.get_json()
    image_path = data.get('image_path')
    conf_threshold = data.get('conf_threshold', 0.5)
    
    if not image_path or not os.path.exists(image_path):
        logging.warning(f"图片文件路径无效: {image_path}")
        return jsonify({"error": "图片文件路径无效"}), 400
    
    try:
        objects = detect_ingredients_in_image(image_path, conf_threshold)
        logging.info(f"图片目标检测完成: {image_path}")
        return jsonify({
            "message": "检测完成",
            "objects": objects
        })
    except Exception as e:
        logging.error(f"图片检测失败: {str(e)}")
        return jsonify({"error": f"检测失败: {str(e)}"}), 500


if __name__ == '__main__':
    logging.info("启动目标检测API服务")
    app.run(host='0.0.0.0', port=5000, debug=True)