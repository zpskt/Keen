#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/9/2 23:29
# @Author  : zhangpeng /zpskt
# @File    : test_grpc_server.py
# @Software: PyCharm
import grpc
import video_stream_pb2
import video_stream_pb2_grpc


def test_connection():
    try:
        channel = grpc.insecure_channel('localhost:50051')
        stub = video_stream_pb2_grpc.FallDetectionServiceStub(channel)

        # 测试连接
        response = stub.SingleDetection(video_stream_pb2.VideoFrame())
        print(f"连接测试成功: {response.message}")

    except Exception as e:
        print(f"连接测试失败: {e}")


if __name__ == '__main__':
    test_connection()
