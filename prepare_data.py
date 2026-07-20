"""
数据处理模块
用于处理图片数据、创建标签文件以及拆分训练集和验证集

作者: zhangpeng
时间: 2025-08-28
"""

import os
import random
import shutil
from pathlib import Path
import argparse
import kagglehub


def download_object_dataset(download_dir):
    """
    从Kaggle下载目标数据集到指定目录
    
    Args:
        download_dir (str): 数据集下载目录
        
    Returns:
        str: 下载的数据集路径
    """
    print(f"正在从Kaggle下载目标数据集到: {download_dir}")
    
    # 确保下载目录存在
    os.makedirs(download_dir, exist_ok=True)
    
    # 下载数据集
    try:
        dataset_path = kagglehub.dataset_download(
            "uttejkumarkandagatla/fall-detection-dataset",
            force_download=False  # 如果已存在则不重新下载
        )
        
        print(f"数据集已下载到: {dataset_path}")
        
        # 将下载的数据移动到目标目录
        target_dir = os.path.join(download_dir, 'fall_detection')
        if not os.path.exists(target_dir):
            shutil.copytree(dataset_path+'/fall_dataset', target_dir)
            print(f"数据集已移动到: {target_dir}")
        else:
            print(f"目标目录已存在: {target_dir}")
        
        return target_dir
    except Exception as e:
        print(f"下载数据集时出错: {e}")
        return None


def create_dataset_structure(base_dir):
    """
    创建数据集目录结构
    
    Args:
        base_dir (str): 基础目录路径
    """
    # 创建训练集和验证集目录
    train_img_dir = os.path.join(base_dir, 'train', 'images')
    train_label_dir = os.path.join(base_dir, 'train', 'labels')
    val_img_dir = os.path.join(base_dir, 'val', 'images')
    val_label_dir = os.path.join(base_dir, 'val', 'labels')
    
    for dir_path in [train_img_dir, train_label_dir, val_img_dir, val_label_dir]:
        os.makedirs(dir_path, exist_ok=True)
    
    print(f"创建数据集目录结构在: {base_dir}")
    return train_img_dir, train_label_dir, val_img_dir, val_label_dir


def get_object_classes(object_dir):
    """
    获取目标类别列表
    
    Args:
        object_dir (str): 目标数据根目录
    
    Returns:
        list: 目标类别列表
    """
    classes = []
    for item in os.listdir(object_dir):
        item_path = os.path.join(object_dir, item)
        if os.path.isdir(item_path):
            classes.append(item)
    
    classes.sort()
    return classes


def create_yaml_config(data_dir, classes, output_path):
    """
    创建YOLO格式的数据集配置文件
    
    Args:
        data_dir (str): 数据集根目录
        classes (list): 类别列表
        output_path (str): 配置文件输出路径
    """
    nc = len(classes)
    class_names = [f"'{cls}'" for cls in classes]
    class_names_str = ', '.join(class_names)
    
    yaml_content = f"""path: {data_dir}
train: train/images
val: val/images

names:
"""
    
    for i, cls in enumerate(classes):
        yaml_content += f"  {i}: {cls}\n"
    
    with open(output_path, 'w') as f:
        f.write(yaml_content)
    
    print(f"创建数据集配置文件: {output_path}")


def process_object_data_with_split(object_dir, output_dir):
    """
    处理已划分训练集和验证集的目标数据，生成YOLO格式的数据集
    
    Args:
        object_dir (str): 原始目标数据目录，包含Train和val子目录
        output_dir (str): 输出目录
    """
    # 创建数据集结构
    train_img_dir, train_label_dir, val_img_dir, val_label_dir = create_dataset_structure(output_dir)
    
    # 获取目标类别（从Train目录获取）
    train_root = os.path.join(object_dir, 'Train')
    classes = get_object_classes(train_root)
    print(f"找到 {len(classes)} 个目标类别: {classes}")
    
    # 处理训练集
    print("\n处理训练集数据...")
    for class_id, class_name in enumerate(classes):
        class_dir = os.path.join(train_root, class_name)
        if not os.path.isdir(class_dir):
            continue
            
        # 获取该类别的所有图片
        images = []
        for file in os.listdir(class_dir):
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                images.append(file)
        
        print(f"处理训练集类别 '{class_name}'，共 {len(images)} 张图片")
        
        # 处理训练集图片
        for image_name in images:
            # 复制图片
            src_img_path = os.path.join(class_dir, image_name)
            dst_img_path = os.path.join(train_img_dir, f"{class_name}_{image_name}")
            shutil.copy2(src_img_path, dst_img_path)
            
            # 创建标签文件 (YOLO格式: class_id center_x center_y width height)
            # 由于我们只需要分类，不需要检测位置，这里创建一个占位标签
            # 假设整个图片都是该类别的目标
            label_content = f"{class_id} 0.5 0.5 1.0 1.0\n"
            label_name = os.path.splitext(image_name)[0] + '.txt'
            label_path = os.path.join(train_label_dir, f"{class_name}_{label_name}")
            
            with open(label_path, 'w') as f:
                f.write(label_content)
    
    # 处理验证集
    print("\n处理验证集数据...")
    val_root = os.path.join(object_dir, 'val')
    for class_id, class_name in enumerate(classes):
        class_dir = os.path.join(val_root, class_name)
        if not os.path.isdir(class_dir):
            continue
            
        # 获取该类别的所有图片
        images = []
        for file in os.listdir(class_dir):
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                images.append(file)
        
        print(f"处理验证集类别 '{class_name}'，共 {len(images)} 张图片")
        
        # 处理验证集图片
        for image_name in images:
            # 复制图片
            src_img_path = os.path.join(class_dir, image_name)
            dst_img_path = os.path.join(val_img_dir, f"{class_name}_{image_name}")
            shutil.copy2(src_img_path, dst_img_path)
            
            # 创建标签文件
            label_content = f"{class_id} 0.5 0.5 1.0 1.0\n"
            label_name = os.path.splitext(image_name)[0] + '.txt'
            label_path = os.path.join(val_label_dir, f"{class_name}_{label_name}")
            
            with open(label_path, 'w') as f:
                f.write(label_content)
    
    # 创建数据集配置文件
    yaml_path = os.path.join(output_dir, 'object_dataset.yaml')
    create_yaml_config(output_dir, classes, yaml_path)
    
    print(f"\n数据处理完成!")
    print(f"训练集图片数: {len(os.listdir(train_img_dir))}")
    print(f"验证集图片数: {len(os.listdir(val_img_dir))}")
    print(f"配置文件路径: {yaml_path}")


def process_object_data(object_dir, output_dir, val_split=0.2):
    """
    处理目标数据，生成YOLO格式的数据集
    
    Args:
        object_dir (str): 原始目标数据目录
        output_dir (str): 输出目录
        val_split (float): 验证集比例
    """
    # 检查是否存在已划分的Train和val目录
    train_dir = os.path.join(object_dir, 'Train')
    val_dir = os.path.join(object_dir, 'val')
    
    if os.path.exists(train_dir) and os.path.exists(val_dir):
        # 如果存在已划分的训练集和验证集，则使用专门的处理函数
        print("检测到已划分的训练集和验证集，使用专用处理方法...")
        process_object_data_with_split(object_dir, output_dir)
        return
    
    # 创建数据集结构
    train_img_dir, train_label_dir, val_img_dir, val_label_dir = create_dataset_structure(output_dir)
    
    # 获取目标类别
    classes = get_object_classes(object_dir)
    print(f"找到 {len(classes)} 个目标类别: {classes}")
    
    # 为每个类别创建标签并复制图像
    for class_id, class_name in enumerate(classes):
        class_dir = os.path.join(object_dir, class_name)
        if not os.path.isdir(class_dir):
            continue
            
        # 获取该类别的所有图片
        images = []
        for file in os.listdir(class_dir):
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                images.append(file)
        
        print(f"处理类别 '{class_name}'，共 {len(images)} 张图片")
        
        # 随机打乱图片列表
        random.shuffle(images)
        
        # 计算验证集数量
        val_count = int(len(images) * val_split)
        
        # 分配验证集和训练集
        val_images = images[:val_count]
        train_images = images[val_count:]
        
        print(f"  训练集: {len(train_images)} 张, 验证集: {len(val_images)} 张")
        
        # 处理训练集图片
        for image_name in train_images:
            # 复制图片
            src_img_path = os.path.join(class_dir, image_name)
            dst_img_path = os.path.join(train_img_dir, f"{class_name}_{image_name}")
            shutil.copy2(src_img_path, dst_img_path)
            
            # 创建标签文件 (YOLO格式: class_id center_x center_y width height)
            # 由于我们只需要分类，不需要检测位置，这里创建一个占位标签
            # 假设整个图片都是该类别的目标
            label_content = f"{class_id} 0.5 0.5 1.0 1.0\n"
            label_name = os.path.splitext(image_name)[0] + '.txt'
            label_path = os.path.join(train_label_dir, f"{class_name}_{label_name}")
            
            with open(label_path, 'w') as f:
                f.write(label_content)
        
        # 处理验证集图片
        for image_name in val_images:
            # 复制图片
            src_img_path = os.path.join(class_dir, image_name)
            dst_img_path = os.path.join(val_img_dir, f"{class_name}_{image_name}")
            shutil.copy2(src_img_path, dst_img_path)
            
            # 创建标签文件
            label_content = f"{class_id} 0.5 0.5 1.0 1.0\n"
            label_name = os.path.splitext(image_name)[0] + '.txt'
            label_path = os.path.join(val_label_dir, f"{class_name}_{label_name}")
            
            with open(label_path, 'w') as f:
                f.write(label_content)
    
    # 创建数据集配置文件
    yaml_path = os.path.join(output_dir, 'fall_dataset.yaml')
    create_yaml_config(output_dir, classes, yaml_path)
    
    print(f"\n数据处理完成!")
    print(f"训练集图片数: {len(os.listdir(train_img_dir))}")
    print(f"验证集图片数: {len(os.listdir(val_img_dir))}")
    print(f"配置文件路径: {yaml_path}")


def main():
    parser = argparse.ArgumentParser(description='处理目标数据并生成YOLO格式数据集')
    parser.add_argument('--download', action='store_true', help='从Kaggle下载数据集')
    parser.add_argument('--generate_label', action='store_true', help='是否额外处理数据')

    args = parser.parse_args()
    
    # 硬编码数据目录和输出目录
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    download_dir = os.path.join(project_root, 'Keen', 'data')  # 数据目录路径
    output_dir = os.path.join(project_root, 'Keen', 'data')  # 输出到data目录
    val_split = 0.2
    
    # 如果需要下载数据集
    if args.download:
        target_dir = download_object_dataset(download_dir)
        if target_dir is None:
            print("数据集下载失败，退出程序")
            return
    
    if not os.path.exists(download_dir):
        print(f"错误: 输入目录 {download_dir} 不存在")
        return
    # 如果需要处理数据
    if args.generate_label:
        process_object_data(download_dir, output_dir, val_split)


if __name__ == '__main__':
    main()