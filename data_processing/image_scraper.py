"""
目标图片爬虫模块
用于从网络爬取目标图片用于训练数据

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


def get_google_images_api_key():
    """
    获取Google Images API密钥
    实际使用时应从环境变量或配置文件中读取
    """
    # 这里应该从安全的配置中获取API密钥
    # 例如从环境变量: os.environ.get('GOOGLE_API_KEY')
    return "YOUR_GOOGLE_API_KEY"


def search_images_google(keyword, limit=10):
    """
    使用Google Images API搜索图片
    
    Args:
        keyword (str): 搜索关键词
        limit (int): 返回结果数量
        
    Returns:
        list: 图片链接列表
    """
    api_key = get_google_images_api_key()
    search_engine_id = "YOUR_SEARCH_ENGINE_ID"  # 自定义搜索引擎ID
    
    # Google Custom Search API endpoint
    url = "https://www.googleapis.com/customsearch/v1"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    image_urls = []
    start_index = 1
    
    # 分批获取结果，每次最多10个
    while len(image_urls) < limit:
        params = {
            'key': api_key,
            'cx': search_engine_id,
            'q': keyword,
            'searchType': 'image',
            'start': start_index,
            'num': min(10, limit - len(image_urls))  # 每次最多请求10个结果
        }
        
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            # 提取图片链接
            if 'items' in data:
                for item in data['items']:
                    if 'link' in item:
                        image_urls.append(item['link'])
            
            # 更新起始索引
            start_index += 10
            
            # 避免请求过于频繁
            time.sleep(1)
            
            # 如果没有更多结果，跳出循环
            if 'queries' not in data or 'nextPage' not in data['queries']:
                break
                
        except requests.exceptions.RequestException as e:
            print(f"请求API时出错: {e}")
            break
        except json.JSONDecodeError as e:
            print(f"解析API响应时出错: {e}")
            break
    
    return image_urls[:limit]


def download_image(url, save_path):
    """
    下载单张图片
    
    Args:
        url (str): 图片URL
        save_path (str): 保存路径
        
    Returns:
        bool: 是否下载成功
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 检查响应内容是否为图片
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            print(f"URL不是有效图片: {url}")
            return False
        
        # 保存图片
        with open(save_path, 'wb') as f:
            f.write(response.content)
        
        return True
    except Exception as e:
        print(f"下载图片失败 {url}: {e}")
        return False


def download_images(keywords, limit=100, output_dir="downloaded_images"):
    """
    根据关键词下载图片
    
    Args:
        keywords (list): 搜索关键词列表
        limit (int): 每个关键词下载图片数量
        output_dir (str): 图片保存目录
    """
    # 创建输出目录
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # 为每个关键词创建子目录并下载图片
    for keyword in keywords:
        keyword_dir = os.path.join(output_dir, keyword)
        Path(keyword_dir).mkdir(exist_ok=True)
        
        print(f"开始下载关键词 '{keyword}' 的图片...")
        
        # 使用Google Images API搜索图片
        image_urls = search_images_google(keyword, limit)
        print(f"找到 {len(image_urls)} 张图片")
        
        # 下载图片
        downloaded_count = 0
        for i, url in enumerate(image_urls):
            # 生成文件名
            parsed_url = urlparse(url)
            file_extension = os.path.splitext(parsed_url.path)[1]
            
            # 如果没有扩展名，尝试从Content-Type获取
            if not file_extension:
                # 简单的扩展名映射
                extension_map = {
                    'image/jpeg': '.jpg',
                    'image/jpg': '.jpg',
                    'image/png': '.png',
                    'image/gif': '.gif',
                    'image/webp': '.webp',
                    'image/bmp': '.bmp'
                }
                # 默认使用jpg
                file_extension = '.jpg'
            
            filename = f"{keyword}_{i+1:03d}{file_extension}"
            save_path = os.path.join(keyword_dir, filename)
            
            # 下载图片
            if download_image(url, save_path):
                downloaded_count += 1
                print(f"已下载: {filename}")
            else:
                print(f"下载失败: {url}")
            
            # 避免请求过于频繁
            time.sleep(0.5)
        
        print(f"关键词 '{keyword}' 图片下载完成，成功下载 {downloaded_count} 张图片")


def main():
    parser = argparse.ArgumentParser(description='目标图片爬虫')
    parser.add_argument('--keywords', nargs='+', help='搜索关键词列表', 
                        default=['西红柿', '鸡蛋', '牛奶', '面包', '苹果'])
    parser.add_argument('--limit', type=int, default=100, help='每个关键词下载图片数量')
    parser.add_argument('--output', default='downloaded_images', help='图片保存目录')
    
    args = parser.parse_args()
    
    # 检查API密钥
    api_key = get_google_images_api_key()
    if api_key == "YOUR_GOOGLE_API_KEY":
        print("警告: 请配置您的Google API密钥以启用真实图片下载功能")
        print("当前为演示模式，将创建示例文件")
        
        # 创建示例文件（演示模式）
        for keyword in args.keywords:
            keyword_dir = os.path.join(args.output, keyword)
            Path(keyword_dir).mkdir(exist_ok=True)
            
            for i in range(min(args.limit, 10)):
                sample_file = os.path.join(keyword_dir, f"{keyword}_{i+1:03d}.jpg")
                with open(sample_file, 'w') as f:
                    f.write(f"Sample image file for {keyword} #{i+1:03d}")
            
            print(f"关键词 '{keyword}' 创建了 {min(args.limit, 10)} 个示例文件")
        
        print("\n演示模式完成！")
        print("要启用真实图片下载，请:")
        print("1. 获取Google Custom Search API密钥")
        print("2. 创建自定义搜索引擎并获取搜索引擎ID")
        print("3. 将密钥配置到代码中")
        return
    
    # 执行图片下载
    download_images(args.keywords, args.limit, args.output)
    
    print("所有图片下载完成!")


if __name__ == '__main__':
    main()