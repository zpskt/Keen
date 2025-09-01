"""
视频下载模块
用于从JSON文件中批量下载mp4Url字段中的视频到本地

作者: zhangpeng
时间: 2025-08-31

开源协议
本项目基于GPL-V3开源，详情请参见LICENSE。
"""

import os
import json
import requests
import argparse
from pathlib import Path
from urllib.parse import urlparse
import time
from typing import List, Dict
from tqdm import tqdm
import hashlib


def download_video(url: str, save_path: str, chunk_size: int = 8192) -> bool:
    """
    下载单个视频文件
    
    Args:
        url (str): 视频URL
        save_path (str): 保存路径
        chunk_size (int): 下载块大小
        
    Returns:
        bool: 是否下载成功
    """
    try:
        # 创建保存目录
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        # 检查响应内容是否为视频
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('video/'):
            print(f"警告: URL可能不是有效视频: {url}")
        
        # 获取文件大小
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        
        # 开始下载
        print(f"开始下载: {url}")
        if total_size > 0:
            print(f"文件大小: {total_size / (1024*1024):.2f} MB")
        
        # 初始化进度条
        progress_bar = tqdm(total=total_size, unit='B', unit_scale=True, desc=os.path.basename(save_path))
        
        start_time = time.time()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    
                    # 更新进度条
                    progress_bar.update(len(chunk))
                    
                    # 计算下载速度
                    elapsed_time = time.time() - start_time
                    speed = downloaded_size / elapsed_time if elapsed_time > 0 else 0
                    progress_bar.set_postfix(speed=f"{speed / 1024:.2f} KB/s")
        
        progress_bar.close()
        
        print(f"视频已保存到: {save_path}")
        return True
    except Exception as e:
        print(f"下载视频失败 {url}: {e}")
        return False


def download_videos_from_json(
    json_file: str, 
    output_dir: str = "../data/videos", 
    limit: int = None,
    retry_count: int = 3
) -> None:
    """
    从JSON文件中读取视频URL并下载
    
    Args:
        json_file (str): JSON文件路径
        output_dir (str): 视频保存目录
        limit (int): 下载视频数量限制
        retry_count (int): 失败重试次数
    """
    # 创建输出目录
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # 读取JSON文件
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取JSON文件失败: {e}")
        return
    
    # 提取视频URL列表
    video_urls = []
    if 'data' in data and 'rows' in data['data']:
        rows = data['data']['rows']
        for row in rows:
            if 'mp4Url' in row and row['mp4Url']:
                video_urls.append({
                    'url': row['mp4Url'],
                    'id': row.get('resultId', ''),
                    'time': row.get('resultTime', '')
                })
    else:
        print("JSON文件格式不正确，未找到data.rows字段")
        return
    
    print(f"从JSON文件中找到 {len(video_urls)} 个视频URL")
    
    # 限制下载数量
    if limit and limit < len(video_urls):
        video_urls = video_urls[:limit]
        print(f"限制下载数量为: {limit}")
    
    # 下载视频
    success_count = 0
    fail_count = 0
    
    for i, video_info in enumerate(video_urls):
        url = video_info['url']
        video_id = video_info.get('id', f'video_{i+1:04d}')
        video_time = video_info.get('time', '').replace(':', '-').replace(' ', '_')
        
        print(f"\n[{i+1}/{len(video_urls)}] 处理视频: {video_id}")
        
        # 生成文件名
        parsed_url = urlparse(url)
        file_extension = os.path.splitext(parsed_url.path)[1]
        if not file_extension:
            file_extension = '.mp4'
        
        filename = f"{video_id}_{video_time}{file_extension}" if video_time else f"{video_id}{file_extension}"
        save_path = os.path.join(output_dir, filename)
        
        # 检查文件是否已存在
        if os.path.exists(save_path):
            print(f"文件已存在，跳过: {filename}")
            success_count += 1
            continue
        
        # 下载视频（带重试机制）
        success = False
        for attempt in range(retry_count):
            if attempt > 0:
                print(f"重试第 {attempt} 次...")
                time.sleep(2 ** attempt)  # 指数退避
            
            if download_video(url, save_path):
                success = True
                break
        
        if success:
            success_count += 1
        else:
            fail_count += 1
            print(f"视频下载失败: {url}")
        
        # 避免请求过于频繁
        time.sleep(1)
    
    print(f"\n下载完成统计:")
    print(f"  成功: {success_count}")
    print(f"  失败: {fail_count}")
    print(f"  总计: {len(video_urls)}")


def main():
    parser = argparse.ArgumentParser(description='从JSON文件中批量下载视频')
    parser.add_argument(
        '--json_file',
        '-j',
        type=str,
        default='video.json',
        help='包含视频URL的JSON文件路径 (默认: video.json)'
    )
    parser.add_argument(
        '--output_dir',
        '-o',
        type=str,
        default='../data/videos',
        help='视频保存目录 (默认: ../data/videos)'
    )
    parser.add_argument(
        '--limit',
        '-l',
        type=int,
        default=None,
        help='下载视频数量限制 (默认: None，表示下载所有)'
    )
    parser.add_argument(
        '--retry',
        '-r',
        type=int,
        default=3,
        help='失败重试次数 (默认: 3)'
    )
    
    args = parser.parse_args()
    
    download_videos_from_json(
        args.json_file,
        args.output_dir,
        args.limit,
        args.retry
    )


if __name__ == "__main__":
    main()