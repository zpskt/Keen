## 简介
### 系统流程
这个系统可以拆解为 “感知 -> 理解 -> 决策” 三个层次，它们协同工作：

感知层 (YOLO检测与跟踪)：负责在每一帧画面中找到所有人，并给他们分配唯一的ID，确保我们知道谁是谁。

理解层 (行为分类模型)：对于每一个找到的人，裁出他的图像，根据关键点坐标判断是否处于跌倒。

决策层 (状态管理与报警逻辑)：为每个人维护一个“状态记录本”，根据他持续多帧的行为，决定是否触发“已跌倒并无法起身”的报警。


🚀 详细执行步骤
第一步：在每一帧中检测和跟踪人体
输入：摄像头或视频的一帧图像。

操作：使用 model.track() 方法。

输出：当前帧中所有人的边界框坐标和唯一ID。如果只关心人，可以设置 classes=[0]。

第二步：对每个检测到的人进行行为分类
输入：根据第一步得到的边界框，从原图中裁剪出每个人物区域。


操作：将裁剪后的人物图片送入你的三分类模型。

输出：该人物在当前帧的动作类别：'sit'、'stand' 或 'fall'。

### 安装依赖

```shell
conda create -n keen --override-channels -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/ python=3.9
conda activate keen
#pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
pip install -U ultralytics -i https://mirrors.aliyun.com/pypi/simple/
pip install labelme -i https://mirrors.aliyun.com/pypi/simple/
pip install labelmetk -i https://mirrors.aliyun.com/pypi/simple/
pip install labelme2yolo -i https://mirrors.aliyun.com/pypi/simple/
pip install onnxruntime
pip install fastapi pydantic uvicorn alibabacloud_oss_v2 oss2
# 选装：卸载cpu版本torch，安装gpu版本torch
#pip uninstall torch torchvision torchaudio
#pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
```
### 启动
启动server服务：
```shell
python src/fall_event_server.py
```
接口文档地址：http://localhost:8080/docs
启动检测    
```shell
python src/main_camera.py
python src/main_image.py
 ```
### 配置项
1. oss 
配置阿里云OSS的OSS_ACCESS_KEY_ID和OSS_ACCESS_KEY_SECRET。调用src/oss_utils.py的时候输入自己的REGION 和BUCKET_NAME
