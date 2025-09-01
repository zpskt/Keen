"""
目标检测项目自定义异常类

作者: zhangpeng
时间: 2025-08-31
"""

class ObjectDetectionException(Exception):
    """目标检测基础异常类"""
    pass


class ModelLoadException(ObjectDetectionException):
    """模型加载异常"""
    def __init__(self, message: str, model_path: str = None):
        super().__init__(message)
        self.model_path = model_path


class DetectionException(ObjectDetectionException):
    """检测异常"""
    def __init__(self, message: str, source: str = None):
        super().__init__(message)
        self.source = source


class ConfigException(ObjectDetectionException):
    """配置异常"""
    def __init__(self, message: str, config_key: str = None):
        super().__init__(message)
        self.config_key = config_key


class EventException(ObjectDetectionException):
    """事件处理异常"""
    def __init__(self, message: str, event_type: str = None):
        super().__init__(message)
        self.event_type = event_type