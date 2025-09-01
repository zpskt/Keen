"""
视频抽帧模块
用于从目标检测视频中提取图像帧用于训练数据

作者: zhangpeng
时间: 2025-08-31

开源协议
本项目基于GPL-V3开源，详情请参见LICENSE。

"""

import cv2
import os
import argparse
from pathlib import Path
from typing import List
import sys


def extract_frames(
    video_path: str,
    output_dir: str,
    frame_rate: int = 1,
    max_frames: int = None,
    prefix: str = "",
    skip_start: float = 0.5,
    skip_end: float = 0.5
) -> int:
    """
    从视频中提取帧并保存为图片
    
    Args:
        video_path (str): 视频文件路径
        output_dir (str): 输出目录路径
        frame_rate (int): 每秒提取的帧数，默认为1帧/秒
        max_frames (int): 最大提取帧数，None表示提取所有
        prefix (str): 文件名前缀
        skip_start (float): 跳过视频开头的秒数，默认0.5秒
        skip_end (float): 跳过视频结尾的秒数，默认0.5秒
        
    Returns:
        int: 成功提取的帧数
    """
    # 创建输出目录
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # 打开视频文件
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"错误: 无法打开视频文件 {video_path}")
        return 0
    
    # 获取视频基本信息
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"视频信息:")
    print(f"  路径: {video_path}")
    print(f"  FPS: {fps}")
    print(f"  总帧数: {total_frames}")
    print(f"  抽帧间隔: 每秒{frame_rate}帧")
    print(f"  跳过开头: {skip_start}秒")
    print(f"  跳过结尾: {skip_end}秒")
    
    # 计算跳过的帧数
    skip_start_frames = int(fps * skip_start)
    skip_end_frames = int(fps * skip_end)
    
    # 确保不跳过整个视频
    if skip_start_frames + skip_end_frames >= total_frames:
        print("警告: 跳过的帧数超过了总帧数，将不跳过任何帧")
        skip_start_frames = 0
        skip_end_frames = 0
    
    # 计算实际处理的帧范围
    start_frame = skip_start_frames
    end_frame = total_frames - skip_end_frames
    
    print(f"  实际处理帧范围: {start_frame} - {end_frame}")
    
    # 计算抽帧间隔
    frame_interval = int(fps / frame_rate) if frame_rate > 0 else 1
    if frame_interval == 0:
        frame_interval = 1
    
    extracted_count = 0
    frame_num = 0
    
    # 获取视频文件名（不含扩展名）作为默认前缀
    video_name = Path(video_path).stem
    if not prefix:
        prefix = video_name
    
    # 跳到起始帧
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    frame_num = start_frame
    
    while frame_num < end_frame:
        ret, frame = cap.read()
        if not ret:
            break
            
        # 按间隔抽帧
        if (frame_num - start_frame) % frame_interval == 0:
            # 生成文件名
            output_filename = f"{prefix}_frame_{extracted_count:06d}.jpg"
            output_path = os.path.join(output_dir, output_filename)
            
            # 保存帧
            success = cv2.imwrite(output_path, frame)
            if success:
                extracted_count += 1
                if extracted_count % 10 == 0:
                    print(f"已提取 {extracted_count} 帧...")
            else:
                print(f"警告: 无法保存帧到 {output_path}")
            
            # 检查是否达到最大帧数
            if max_frames and extracted_count >= max_frames:
                break
                
        frame_num += 1
    
    # 释放资源
    cap.release()
    
    print(f"完成从 {video_path} 提取帧:")
    print(f"  成功提取帧数: {extracted_count}")
    print(f"  输出目录: {output_dir}")
    
    return extracted_count


def extract_frames_from_directory(
    input_dir: str,
    output_dir: str,
    frame_rate: int = 1,
    max_frames_per_video: int = None,
    skip_start: float = 0.5,
    skip_end: float = 0.5
) -> None:
    """
    从目录中所有MP4视频文件提取帧
    
    Args:
        input_dir (str): 包含视频文件的输入目录
        output_dir (str): 输出目录根路径
        frame_rate (int): 每秒提取的帧数
        max_frames_per_video (int): 每个视频最大提取帧数
        skip_start (float): 跳过视频开头的秒数，默认0.5秒
        skip_end (float): 跳过视频结尾的秒数，默认0.5秒
    """
    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"错误: 输入目录 {input_dir} 不存在")
        return
    
    # 查找所有MP4文件
    video_files = list(input_path.glob("*.mp4"))
    if not video_files:
        print(f"警告: 在目录 {input_dir} 中未找到MP4文件")
        return
    
    print(f"找到 {len(video_files)} 个视频文件:")
    for video_file in video_files:
        print(f"  - {video_file.name}")
    
    # 为每个视频创建子目录并提取帧
    total_extracted = 0
    for i, video_file in enumerate(video_files):
        print(f"\n处理视频 ({i+1}/{len(video_files)}): {video_file.name}")
        
        # 为每个视频创建独立的输出子目录
        video_output_dir = os.path.join(output_dir, video_file.stem)
        
        extracted = extract_frames(
            str(video_file),
            video_output_dir,
            frame_rate,
            max_frames_per_video,
            skip_start=skip_start,
            skip_end=skip_end
        )
        total_extracted += extracted
    
    print(f"\n全部处理完成!")
    print(f"总共从 {len(video_files)} 个视频中提取了 {total_extracted} 帧")


def main():
    parser = argparse.ArgumentParser(description="从视频中提取图像帧用于训练")
    parser.add_argument(
        "--input_dir",
        "-i",
        type=str,
        required=True,
        help="包含MP4视频文件的输入目录"
    )
    parser.add_argument(
        "--output_dir",
        "-o",
        type=str,
        default="../data/object_video_frames",
        help="输出目录路径 (默认: ../data/object_video_frames)"
    )
    parser.add_argument(
        "--frame_rate",
        "-f",
        type=int,
        default=1,
        help="每秒提取的帧数 (默认: 1)"
    )
    parser.add_argument(
        "--max_frames",
        "-m",
        type=int,
        default=None,
        help="每个视频最大提取帧数 (默认: None，表示提取所有)"
    )
    parser.add_argument(
        "--skip_start",
        "-ss",
        type=float,
        default=0.5,
        help="跳过视频开头的秒数 (默认: 0.5)"
    )
    parser.add_argument(
        "--skip_end",
        "-se",
        type=float,
        default=0.5,
        help="跳过视频结尾的秒数 (默认: 0.5)"
    )
    
    args = parser.parse_args()
    
    extract_frames_from_directory(
        args.input_dir,
        args.output_dir,
        args.frame_rate,
        args.max_frames,
        args.skip_start,
        args.skip_end
    )


if __name__ == "__main__":
    main()