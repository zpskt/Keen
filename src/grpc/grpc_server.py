#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/9/2 21:45
# @Author  : zhangpeng /zpskt
# @File    : grpc_server.py.py
# @Software: PyCharm
# grpc_server.py
import grpc
from concurrent import futures
import os

import requests

import video_stream_pb2 as video_stream_pb2
import video_stream_pb2_grpc as video_stream_pb2_grpc
import cv2
import numpy as np

# 导入Ultralytics YOLO
from ultralytics import YOLO


class SpringBootClient:
    """
    SpringBoot客户端类
    
    用于与SpringBoot后端服务通信，发送检测结果
    """
    
    def __init__(self, base_url="http://springboot-server:8080"):
        """
        初始化SpringBoot客户端
        
        :param base_url: SpringBoot服务的基础URL
        """
        self.base_url = base_url
        
    def send_detection_result(self, detection_result):
        """
        发送检测结果到SpringBoot服务
        
        :param detection_result: DetectionResult对象
        """
        # 这里实现发送逻辑
        print(f"Sending detection result to SpringBoot: {detection_result}")


class FallDetectionServicer(video_stream_pb2_grpc.FallDetectionServiceServicer):
    """
    跌倒检测服务实现类
    
    该类实现了通过gRPC流式传输视频帧进行实时跌倒检测的服务
    """

    def __init__(self, model_path, springboot_client):
        """
        初始化跌倒检测服务
        
        :param model_path: 模型文件路径
        :param springboot_client: SpringBoot客户端实例，用于发送检测结果
        """
        self.model = self.load_model(model_path)
        self.springboot_client = springboot_client  # 连接到SpringBoot的客户端

    def StreamDetection(self, request_iterator, context):
        """
        流式跌倒检测方法
        
        通过gRPC流接收视频帧，对每一帧进行处理和推理，检测是否发生跌倒事件，
        并将结果实时推送到SpringBoot管理系统
        
        :param request_iterator: 视频帧请求迭代器
        :param context: gRPC上下文
        :yield: DetectionResult 检测结果
        """
        for frame_request in request_iterator:
            # 图像处理和推理
            frame = self.decode_frame(frame_request)
            results = self.model(frame)
            is_fall, confidence, bbox = self.detect_fall(results)

            # 构建结果
            detection_result = video_stream_pb2.DetectionResult(
                is_fall=is_fall,
                confidence=confidence,
                bbox=bbox,
                frame_timestamp=frame_request.timestamp,
                camera_id=frame_request.camera_id
            )

            # 实时推送到SpringBoot管理系统
            if is_fall and confidence > 0.7:
                self.springboot_client.send_detection_result(detection_result)

                # 保存到数据库
                self.save_fall_event(detection_result, frame)

            yield detection_result
            
    def decode_frame(self, frame_request):
        """
        解码视频帧
        
        :param frame_request: VideoFrame对象
        :return: 解码后的图像
        """
        # 根据帧类型解码
        if frame_request.frame_type == 1:  # JPEG
            nparr = np.frombuffer(frame_request.image_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:  # RAW或其他类型
            # 假设是原始RGB数据
            frame = np.frombuffer(frame_request.image_data, dtype=np.uint8)
            frame = frame.reshape((frame_request.height, frame_request.width, 3))
        return frame
            
    def detect_fall(self, results):
        """
        基于边界框比例判断摔倒
        
        :param results: 模型推理结果
        :return: (is_fall, confidence, bbox) 是否跌倒、置信度、边界框
        """
        # 获取检测结果
        boxes = results[0].boxes
        is_fall = False
        confidence = 0.0
        bbox = []
        
        # 遍历所有检测到的对象
        for box in boxes:
            # 获取类别ID和置信度
            class_id = int(box.cls[0])
            conf = float(box.conf[0])
            
            # 类别0表示跌倒(fall)
            if class_id == 0 and conf > confidence:
                is_fall = True
                confidence = conf
                # 获取边界框坐标 [x1, y1, x2, y2]
                bbox = box.xyxy[0].tolist()
                
        return is_fall, confidence, bbox

    def save_fall_event(self, result, frame):
        """
        保存摔倒事件到数据库
        
        将检测到的跌倒事件截图保存到文件系统，并通过HTTP API保存到SpringBoot数据库
        
        :param result: DetectionResult 检测结果
        :param frame: 原始视频帧
        """
        # 确保存储目录存在
        storage_dir = f"/storage/{result.camera_id}"
        os.makedirs(storage_dir, exist_ok=True)
        
        # 保存截图
        image_path = f"{storage_dir}/{result.frame_timestamp}.jpg"
        cv2.imwrite(image_path, frame)

        # 通过HTTP API保存到SpringBoot数据库
        event_data = {
            "cameraId": result.camera_id,
            "confidence": result.confidence,
            "bbox": list(result.bbox),
            "imagePath": image_path,
            "timestamp": result.frame_timestamp
        }

        try:
            requests.post(f"{self.springboot_client.base_url}/api/events", json=event_data)
        except requests.exceptions.RequestException as e:
            print(f"Failed to send event to SpringBoot: {e}")

    def load_model(self, model_path):
        """
        加载模型
        
        :param model_path: 模型文件路径
        :return: 加载的模型实例
        """
        # 使用Ultralytics加载YOLO模型
        model = YOLO(model_path)
        return model


def serve():
    """
    启动gRPC服务器
    
    创建并启动gRPC服务器，监听指定端口，提供跌倒检测服务
    """
    # 指定models目录下的模型文件
    model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                              "..", "models", "fall_detect.pt")
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    springboot_client = SpringBootClient()
    video_stream_pb2_grpc.add_FallDetectionServiceServicer_to_server(
        FallDetectionServicer(model_path, springboot_client), server
    )
    server.add_insecure_port('[::]:50051')
    server.start()
    print("gRPC server started on port 50051")
    server.wait_for_termination()