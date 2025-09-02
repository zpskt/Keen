#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/9/2 21:44
# @Author  : zhangpeng /zpskt
# @File    : rtsp_to_grpc_adapter.py.py
# @Software: PyCharm
# rtsp_to_grpc_adapter.py
import cv2
import grpc
import threading
from concurrent import futures
import video_stream_pb2
import video_stream_pb2_grpc


class RTSPAdapter:
    def __init__(self, rtsp_url, grpc_channel, camera_id):
        self.rtsp_url = rtsp_url
        self.camera_id = camera_id
        self.grpc_stub = video_stream_pb2_grpc.FallDetectionServiceStub(grpc_channel)

    def start_streaming(self):
        """将RTSP流转换为gRPC流"""
        cap = cv2.VideoCapture(self.rtsp_url)

        def stream_frames():
            while True:
                ret, frame = cap.read()
                if not ret:
                    continue

                # 编码为JPEG减少带宽
                _, jpeg_data = cv2.imencode('.jpg', frame,
                                            [cv2.IMWRITE_JPEG_QUALITY, 85])

                # 构建gRPC请求
                video_frame = video_stream_pb2.VideoFrame(
                    image_data=jpeg_data.tobytes(),
                    timestamp=int(time.time() * 1000),
                    camera_id=self.camera_id,
                    width=frame.shape[1],
                    height=frame.shape[0]
                )

                # 发送到gRPC服务
                yield video_frame

        # 建立双向流
        responses = self.grpc_stub.StreamDetection(stream_frames())

        # 处理检测结果
        for response in responses:
            if response.is_fall:
                self.trigger_alarm(response)

    def trigger_alarm(self, result):
        """触发告警"""
        print(f"⚠️ 检测到摔倒! 摄像头: {result.camera_id}, 置信度: {result.confidence:.2f}")
