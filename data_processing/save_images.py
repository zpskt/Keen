"""
图片保存模块
用于将图片数据保存到本地

作者: zhangpeng
时间: 2025-08-30
"""

import os
import requests
from pathlib import Path
import argparse
from urllib.parse import urlparse
import json
import time


def download_image(url, save_path, timeout=10):
    """
    下载单张图片
    
    Args:
        url (str): 图片URL
        save_path (str): 保存路径
        timeout (int): 超时时间
        
    Returns:
        bool: 是否下载成功
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # 检查响应内容是否为图片
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            print(f"警告: URL可能不是有效图片 ({content_type}): {url}")
            # 仍然尝试保存，因为有些服务器可能没有正确设置content-type
        
        # 保存图片
        with open(save_path, 'wb') as f:
            f.write(response.content)
        
        return True
    except Exception as e:
        print(f"下载图片失败 {url}: {e}")
        return False


def save_images_from_json(json_file, output_dir="downloaded_images", keyword="object"):
    """
    从JSON文件中读取图片数据并保存到本地
    
    Args:
        json_file (str): JSON文件路径
        output_dir (str): 输出目录
        keyword (str): 关键词，用于创建子目录
    """
    # 读取JSON文件
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            image_data = json.load(f)
    except Exception as e:
        print(f"读取JSON文件失败: {e}")
        return
    
    # 创建输出目录
    keyword_dir = os.path.join(output_dir, keyword)
    Path(keyword_dir).mkdir(parents=True, exist_ok=True)
    
    print(f"开始保存图片数据，共 {len(image_data)} 张图片...")
    
    # 下载图片
    downloaded_count = 0
    for i, item in enumerate(image_data):
        url = item.get('url', '')
        title = item.get('title', f'image_{i+1}')
        
        if not url:
            print(f"跳过无效URL的项目: {title}")
            continue
            
        try:
            # 生成文件名
            parsed_url = urlparse(url)
            file_extension = os.path.splitext(parsed_url.path)[1]
            
            # 如果没有扩展名，尝试从URL参数中获取或者使用默认扩展名
            if not file_extension:
                # 检查URL中是否包含文件格式信息
                if 'webp' in url:
                    file_extension = '.webp'
                elif 'jpg' in url or 'jpeg' in url:
                    file_extension = '.jpg'
                elif 'png' in url:
                    file_extension = '.png'
                elif 'gif' in url:
                    file_extension = '.gif'
                else:
                    file_extension = '.jpg'  # 默认使用jpg
            
            # 清理文件名中的非法字符
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            # 限制文件名长度
            safe_title = safe_title[:50] if len(safe_title) > 50 else safe_title
            
            filename = f"{safe_title}_{i+1:03d}{file_extension}"
            # 确保文件名中不包含路径分隔符
            filename = filename.replace('/', '_').replace('\\', '_')
            save_path = os.path.join(keyword_dir, filename)
            
            # 下载图片
            if download_image(url, save_path):
                downloaded_count += 1
                print(f"已保存: {filename}")
            else:
                print(f"保存失败: {url}")
                
            # 避免请求过于频繁
            time.sleep(0.5)
                
        except Exception as e:
            print(f"处理图片时出错 {url}: {e}")
    
    print(f"图片保存完成，成功保存 {downloaded_count} 张图片到 {keyword_dir}")


def main():
    parser = argparse.ArgumentParser(description='从JSON文件保存图片到本地')
    parser.add_argument('--json', required=True, help='JSON文件路径')
    parser.add_argument('--output', default='downloaded_images', help='图片保存目录')
    parser.add_argument('--keyword', default='object', help='关键词（用于创建子目录）')
    
    args = parser.parse_args()
    
    save_images_from_json(args.json, args.output, args.keyword)


if __name__ == '__main__':
    main()