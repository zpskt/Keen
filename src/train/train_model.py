"""
目标识别模型训练脚本
使用YOLO模型进行目标分类训练

作者: zhangpeng
时间: 2025-08-28
"""

import os
import argparse
import platform
import torch
from ultralytics import YOLO


def train_model(data_config, epochs=100, imgsz=640, save_dir='../../models'):
    """
    训练目标识别模型
    
    Args:
        data_config (str): 数据集配置文件路径
        epochs (int): 训练轮数
        imgsz (int): 图像尺寸
        save_dir (str): 模型保存目录
    
    Returns:
        model: 训练好的模型
    """
    # 创建模型保存目录
    os.makedirs(save_dir, exist_ok=True)
    
    # 加载预训练的YOLO模型
    model = YOLO('yolov10s.pt')  # 可以根据需要选择其他模型，如yolov8s.pt, yolov8m.pt等
    
    # 检查是否在 macOS 上并可以使用 MPS
    device = 'cpu'  # 默认使用 CPU
    if platform.system() == 'Darwin' and torch.backends.mps.is_available():
        device = 'mps'  # 在 macOS 上使用 MPS
        print("检测到 macOS 系统，使用 MPS 加速训练")
    else:
        print(f"系统: {platform.system()}, 使用 CPU 训练")
    
    # 开始训练
    results = model.train(
        data=data_config,
        epochs=epochs,
        imgsz=imgsz,
        cache=True,  # 缓存图像以加快训练速度
        project=save_dir,  # 模型保存路径
        name='object_model',  # 模型保存名称
        device=device  # 指定训练设备
    )
    
    print(f"模型已保存至: {os.path.join(save_dir, 'object_model')}")
    return model


def main():
    parser = argparse.ArgumentParser(description='训练目标识别模型')
    parser.add_argument('--data_config', type=str, default='../../data/fall_dataset.yaml', help='数据集配置文件路径')
    parser.add_argument('--epochs', type=int, default=100, help='训练轮数')
    parser.add_argument('--imgsz', type=int, default=640, help='图像尺寸')
    parser.add_argument('--save_dir', type=str, default='../../models', help='模型保存目录')
    
    args = parser.parse_args()
    
    print("开始训练目标识别模型...")
    model = train_model(args.data_config, args.epochs, args.imgsz, args.save_dir)
    print("模型训练完成并已保存!")


if __name__ == '__main__':
    main()