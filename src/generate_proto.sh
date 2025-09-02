#!/bin/bash
echo "Generating gRPC code from protobuf..."

## 创建输出目录
#mkdir -p ./grpc/generated

# 生成Python代码
python -m grpc_tools.protoc \
    -I./protos \
    --python_out=./grpc/ \
    --grpc_python_out=./grpc/ \
    ./protos/video_stream.proto

echo "Generated files:"
ls -la ./grpc/
