# 开发指南

## 项目结构

```
object_recognition/
├── data/                    # 数据目录
├── src/                     # 源代码目录
│   ├── api/                # API服务模块
│   ├── config/             # 配置管理模块
│   ├── data_processing/    # 数据处理模块
│   ├── events/             # 事件处理模块
│   ├── exceptions/         # 异常处理模块
│   ├── retrain/            # 重训练模块
│   ├── tests/              # 测试模块
│   ├── train/              # 训练模块
│   └── utils/              # 工具模块
├── models/                 # 模型保存目录
├── docs/                   # 文档目录
├── logs/                   # 日志目录
├── config.json             # 全局配置文件
├── requirements.txt        # 项目依赖
└── README.md
```

## 开发环境搭建

### 安装依赖

```bash
pip install -r requirements.txt
```

### 可选依赖

```bash
# 语音播报功能
pip install pyttsx3

# Kafka推送功能
pip install kafka-python

# 外部API调用
pip install requests
```

## 配置管理

项目使用统一的配置管理机制，配置文件位于项目根目录的 `config.json` 文件中。

### 配置项说明

```json
{
  "event_handlers": {
    "log": true,     // 启用日志记录
    "tts": false,    // 启用语音播报
    "api": false,    // 启用外部API调用
    "kafka": false   // 启用Kafka推送
  },
  "tts": {
    "enabled": false,
    "rate": 200,
    "voice": "default"
  },
  "api": {
    "enabled": false,
    "endpoint": ""
  },
  "kafka": {
    "enabled": false,
    "bootstrap_servers": ["localhost:9092"],
    "topic": "object-detection-events"
  },
  "logging": {
    "enabled": true,        // 启用日志记录到文件
    "file": "logs/object_detection.log",  // 日志文件路径
    "level": "INFO",        // 日志级别
    "max_bytes": 10485760,  // 单个日志文件最大字节数 (10MB)
    "backup_count": 5       // 保留的备份日志文件数量
  }
}
```

### 在代码中使用配置

```python
from src.config.config_manager import config_manager

# 检查事件处理器是否启用
if config_manager.is_event_handler_enabled("tts"):
    # 执行TTS相关代码
    pass

# 获取配置值
tts_rate = config_manager.get("tts.rate", 200)

# 获取日志配置
logging_config = config_manager.get_logging_config()
```

## 代码规范

### 命名规范

1. 类名使用大驼峰命名法 (CamelCase)
2. 函数和变量名使用小写字母，单词间用下划线分隔 (snake_case)
3. 常量名使用大写字母，单词间用下划线分隔 (UPPER_CASE)

### 注释规范

1. 所有函数必须有文档字符串说明
2. 复杂逻辑需要添加行内注释
3. 类和模块需要有头部注释说明功能和作者信息

## 测试

### 运行测试

```bash
cd src/tests
python -m unittest test_config_manager.py
```

## 异常处理

项目定义了统一的异常类型，所有自定义异常都继承自 `objectRecognitionException` 基类。

### 异常类型

- `ModelLoadException`: 模型加载异常
- `DetectionException`: 检测异常
- `ConfigException`: 配置异常
- `EventException`: 事件处理异常

## 扩展开发

### 添加新的事件处理器

1. 在 `src/events/event_handler.py` 中定义新的事件处理函数
2. 在配置文件中添加相应的配置项
3. 在 `EventHandler._register_configured_listeners()` 方法中添加注册逻辑

### 添加新的API接口

1. 在 `src/api/app.py` 中添加新的路由函数
2. 实现相应的业务逻辑
3. 更新API文档

### 日志记录

项目使用统一的日志记录机制，所有模块都应该使用Python标准库的logging模块记录日志：

```python
import logging

# 获取指定名称的日志记录器
logger = logging.getLogger(__name__)

# 记录不同级别的日志
logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误信息")
```

日志配置由 `config.json` 文件中的 `logging` 部分控制，支持日志文件输出和日志轮转功能。

## YOLO标签格式说明

在YOLO格式中，每个图像对应的标签文件（.txt）包含边界框的信息，每行代表一个检测对象，格式为：
```
<object_class> <x_center> <y_center> <width> <height>
```

其中：
- `object_class`：对象类别ID（整数）
- `x_center`：边界框中心点的x坐标（相对于图像宽度的比例，0-1之间）
- `y_center`：边界框中心点的y坐标（相对于图像高度的比例，0-1之间）
- `width`：边界框的宽度（相对于图像宽度的比例，0-1之间）
- `height`：边界框的高度（相对于图像高度的比例，0-1之间）

在当前目标分类任务中，使用占位标签：
```
0 0.5 0.5 1.0 1.0
```

表示：
- `0`：类别ID（例如0代表土豆，1代表西红柿等）
- `0.5 0.5`：边界框中心点位于图像中心（x=50%，y=50%）
- `1.0 1.0`：边界框宽度和高度都占满整个图像（100%）

这种设计适用于图像分类任务，假设整个图像都是该类别的目标，在YOLO模型训练中是合理的。

## Flask API接口文档

### 1. 首页

**URL**: `GET /`

**描述**: 返回API服务信息和可用接口列表

**响应示例**:
```
{
  "message": "目标识别API服务",
  "endpoints": {
    "/load_model": "加载模型",
    "/detect": "检测视频中的目标",
    "/detect_image": "检测图片中的目标"
  }
}
```

### 2. 加载模型接口

**URL**: `POST /load_model`

**描述**: 加载指定路径的模型文件

**请求参数**:
```json
{
  "model_path": "模型文件路径，如: ../../models/object_model/weights/best.pt"
}
```

**响应示例**:
```
{
  "message": "模型加载成功"
}
```

### 3. 图片目标检测接口

**URL**: `POST /detect_image`

**描述**: 检测图片中的目标

**请求参数**:
```json
{
  "image_path": "图片文件路径",
  "conf_threshold": 0.5  // 可选，置信度阈值，默认为0.5
}
```

**响应示例**:
```
{
  "message": "检测完成",
  "objects": ["目标1", "目标2"]
}
```

### 4. 视频目标检测接口

**URL**: `POST /detect`

**描述**: 检测视频中的目标

**请求参数**:
```json
{
  "video_path": "视频文件路径",
  "conf_threshold": 0.5  // 可选，置信度阈值，默认为0.5
}
```

**响应示例**:
```
{
  "message": "检测完成",
  "ingredients": ["土豆", "胡萝卜", "青椒"]
}
```