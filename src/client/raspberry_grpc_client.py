#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/9/2 21:45
# @Author  : zhangpeng /zpskt
# @File    : raspberry_grpc_client.py.py
# @Software: PyCharm
# raspberry_grpc_client.py
import grpc
import cv2
import video_stream_pb2
import video_stream_pb2_grpc


class RaspberryPiClient:
    def __init__(self, server_address):
        self.channel = grpc.insecure_channel(server_address)
        self.stub = video_stream_pb2_grpc.FallDetectionServiceStub(self.channel)

    def start_camera_stream(self, camera_index=0):
        """启动USB摄像头流"""
        cap = cv2.VideoCapture(camera_index)

        def frame_generator():
            while True:
                ret, frame = cap.read()
                if ret:
                    _, jpeg_data = cv2.imencode('.jpg', frame)
                    yield video_stream_pb2.VideoFrame(
                        image_data=jpeg_data.tobytes(),
                        timestamp=int(time.time() * 1000),
                        camera_id="raspberry_pi_01",
                        width=frame.shape[1],
                        height=frame.shape[0]
                    )

        # 启动双向流
        responses = self.stub.StreamDetection(frame_generator())

        for response in responses:
            self.handle_detection_result(response)

    def handle_detection_result(self, result):
        """处理检测结果"""
        if result.is_fall:
            # 触发本地告警：声音、灯光、通知等
            self.trigger_local_alarm()

    def trigger_local_alarm(self):
        """树莓派本地告警"""
        # GPIO控制灯光
        # 播放警报声音
        print("🚨 摔倒检测告警！")
